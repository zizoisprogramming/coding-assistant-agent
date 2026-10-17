"""CPU check of int4_lora.py on a tiny random Gemma 4 saved in the 31B's exact compressed-tensors scheme.

    data/venv_train/bin/python scripts/train/test_int4_lora_tiny.py <tiny_checkpoint_dir>

1. Int4LoRALinear (LoRA B = 0) gives the same outputs as transformers' fully decompressed model.
2. masked_lm_loss equals transformers' own loss when every position is labelled, and matches a manual masked loss.
3. Gradients are identical with and without gradient checkpointing; a few steps lower the loss.
4. The saved adapter, loaded by standard PEFT onto the decompressed model, reproduces our trained model's logits.
"""
import copy
import sys
import tempfile
from pathlib import Path

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent))
from int4_lora import (Int4LoRALinear, add_lora, dequantize_int4, load_int4_model, masked_lm_loss,  # noqa: E402
                       save_adapter, text_hidden_states)

CKPT = sys.argv[1]
torch.manual_seed(0)


def reference_model():
    """transformers' own path: load packed, the first forward decompresses everything to bf16."""
    import transformers
    from transformers import AutoConfig
    cls = getattr(transformers, AutoConfig.from_pretrained(CKPT).architectures[0])
    m = cls.from_pretrained(CKPT, dtype=torch.bfloat16, attn_implementation="eager")
    m.eval()
    with torch.no_grad():
        m(input_ids=torch.tensor([[2, 5]]))  # triggers the decompress hook
    return m


def ours(r=4):
    m = load_int4_model(CKPT, device_map=None, attn_implementation="eager")
    add_lora(m, r=r, alpha=2 * r)
    m.eval()
    return m


ids = torch.randint(3, 1000, (1, 96))
labels = ids.clone()
labels[:, :40] = -100  # prompt part not trained

ref, mine = reference_model(), ours()
with torch.no_grad():
    lr, lm = ref(input_ids=ids).logits, mine(input_ids=ids).logits
d = (lr.float() - lm.float()).abs().max().item()
print(f"1. logits ours vs transformers-decompressed: max abs diff {d:.3e}")
assert d < 1e-2, "int4 layer does not reproduce the checkpoint weights"
same_wrapper = torch.equal(mine.model(input_ids=ids).last_hidden_state,
                           mine.model.language_model(input_ids=ids).last_hidden_state)
print("   multimodal wrapper == text decoder for text-only input:", same_wrapper)

with torch.no_grad():
    full = ref(input_ids=ids, labels=ids).loss
    h = text_hidden_states(mine, ids)
    ours_full, n = masked_lm_loss(mine, h, ids, chunk=7)
    ours_masked, nm = masked_lm_loss(mine, h, labels, chunk=7)
    manual = F.cross_entropy(lm[0, :-1].float(), labels[0, 1:], ignore_index=-100)
print(f"2. loss all positions: transformers {full.item():.5f} ours {ours_full.item():.5f} (n={n});"
      f" masked ours {ours_masked.item():.5f} manual {manual.item():.5f} (n={nm})")
assert abs(full.item() - ours_full.item()) < 2e-2 and abs(manual.item() - ours_masked.item()) < 2e-2


def grads(model, ckpt):
    model.train()
    if ckpt:
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    else:
        model.gradient_checkpointing_disable()
    model.zero_grad()
    loss, _ = masked_lm_loss(model, text_hidden_states(model, ids), labels, chunk=16)
    loss.backward()
    return {n: p.grad.clone() for n, p in model.named_parameters() if p.requires_grad}


with torch.no_grad():  # make B non-zero so A also gets gradients
    for n, p in mine.named_parameters():
        if n.endswith("lora_B"):
            p.normal_(std=0.01)
g0, g1 = grads(mine, False), grads(mine, True)
gd = max((g0[k] - g1[k]).abs().max().item() for k in g0)
nz = sum(int(v.abs().sum() > 0) for v in g0.values())
frozen = [n for n, p in mine.named_parameters() if not p.requires_grad]
print(f"3. trainable tensors {len(g0)} (non-zero grads {nz}), frozen params {len(frozen)}; "
      f"grad diff with/without checkpointing {gd:.2e}")
assert nz == len(g0) and gd < 1e-4

opt = torch.optim.AdamW([p for p in mine.parameters() if p.requires_grad], lr=2e-3)
losses = []
for step in range(12):
    opt.zero_grad()
    loss, _ = masked_lm_loss(mine, text_hidden_states(mine, ids), labels)
    loss.backward()
    opt.step()
    losses.append(loss.item())
print("   training loss:", " ".join(f"{x:.3f}" for x in losses))
assert losses[-1] < losses[0] - 0.5

out = save_adapter(mine, Path(tempfile.mkdtemp()) / "adapter", "google/gemma-4-31b-it-qat-w4a16-ct")


def plain_copy(m, dtype):
    """The same architecture without quantization: ordinary nn.Linear holding the unpacked int4 weights."""
    cfg = copy.deepcopy(m.config)
    del cfg.quantization_config
    p = type(m)(cfg).to(dtype).eval()
    sd = {n: t.to(dtype) for n, t in m.state_dict().items() if "lora_" not in n}
    for n, mod in m.named_modules():
        if isinstance(mod, Int4LoRALinear):
            sd[n + ".weight"] = dequantize_int4(mod.weight_packed, mod.weight_scale, mod.shape, mod.args).to(dtype)
    missing, unexpected = p.load_state_dict(sd, strict=False)
    assert not [k for k in missing if "lm_head" not in k] and not unexpected, (missing[:3], unexpected[:3])
    return p


# Float32 so rounding cannot hide a mismatch: our trained model vs standard PEFT loading the saved files.
m32 = load_int4_model(CKPT, device_map=None, attn_implementation="eager", dtype=torch.float32)
add_lora(m32, r=4, alpha=8)
m32.load_state_dict({k: v.float() for k, v in mine.state_dict().items() if "lora_" in k}, strict=False)
with torch.no_grad():
    for n, p in m32.named_parameters():
        if "lora_" in n:
            p.copy_(p.to(torch.bfloat16).float())  # the saved adapter is bf16
m32.eval()
out = save_adapter(m32, Path(tempfile.mkdtemp()) / "adapter", "google/gemma-4-31b-it-qat-w4a16-ct")
from peft import LoraConfig, PeftModel  # noqa: E402
# The saved config keeps the plain module-name list (the format vLLM loaded on the scorer); PEFT would also match
# vision-tower layers with that list, so for this comparison only, narrow it to the text decoder.
cfg = LoraConfig.from_pretrained(str(out))
cfg.target_modules = r".*language_model.*\.(" + "|".join(cfg.target_modules) + ")"
plain = plain_copy(m32, torch.float32)
with torch.no_grad():
    l_base = plain(input_ids=ids).logits
    peft_model = PeftModel.from_pretrained(plain, str(out), config=cfg).eval()
    lp, lo = peft_model(input_ids=ids).logits, m32(input_ids=ids).logits
shift, d = (lp - l_base).abs().max().item(), (lp - lo).abs().max().item()
print(f"4. adapter files: {sorted(p.name for p in out.iterdir())}; float32: PEFT-loaded adapter vs ours max abs diff "
      f"{d:.2e} (the adapter moves logits by {shift:.3f})")
assert shift > 0.1 and d < 1e-3
print("OK")
