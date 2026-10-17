# 2. Training code: LoRA on the competition's 4-bit checkpoint (copy of scripts/train/int4_lora.py; tested on CPU
#    by scripts/train/test_int4_lora_tiny.py). Defines load_int4_model, add_lora, masked_lm_loss, save_adapter.
"""LoRA training on top of the competition's 4-bit checkpoint, without ever holding the 16-bit model in memory.

Why not plain transformers + PEFT: transformers loads a compressed-tensors checkpoint packed, but decompresses the
WHOLE model to bf16 on the first forward pass (ModelCompressor.add_decompress_hook). For the 31B that is ~62 GB,
more than Kaggle's GPUs hold. Standard QLoRA (bitsandbytes NF4) would fit, but trains against a different 4-bit
rounding than the int4 weights vLLM serves.

Here every quantized Linear becomes an Int4LoRALinear: it keeps the packed int4 weights + bf16 group scales exactly as
stored in the checkpoint (the same numbers vLLM serves), unpacks one layer's weight only while that layer runs, and
adds a trainable LoRA branch. The saved adapter is a standard PEFT adapter (same file layout as the sample
main_lora that vLLM loaded on the scorer).
"""
import json
import math
from pathlib import Path

import torch
import torch.nn.functional as F
from torch.utils.checkpoint import checkpoint

DEFAULT_TARGETS = ("q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj")


def dequantize_int4(packed, scale, shape, args):
    """The checkpoint's weight in bf16, computed with compressed-tensors' own unpack/dequantize code."""
    from compressed_tensors.compressors.pack_quantized.helpers import unpack_from_int32
    from compressed_tensors.quantization.lifecycle.forward import dequantize
    q = unpack_from_int32(packed, args.num_bits, torch.Size(shape))
    return dequantize(x_q=q, scale=scale, args=args, dtype=scale.dtype)


class _Int4Matmul(torch.autograd.Function):
    """y = x @ W.T with W rebuilt from int4 in forward and again in backward, so W is never kept between them."""

    @staticmethod
    def forward(ctx, x, packed, scale, shape, args):
        w = dequantize_int4(packed, scale, shape, args)
        ctx.save_for_backward(packed, scale)
        ctx.shape, ctx.args = shape, args
        return F.linear(x, w.to(x.dtype))  # same kernel as nn.Linear

    @staticmethod
    def backward(ctx, grad_y):
        packed, scale = ctx.saved_tensors
        w = dequantize_int4(packed, scale, ctx.shape, ctx.args)
        return grad_y @ w.to(grad_y.dtype), None, None, None, None


class Int4LoRALinear(torch.nn.Module):
    def __init__(self, linear, r=0, alpha=0, dropout=0.0):
        super().__init__()
        self.args = linear.quantization_scheme.weights
        self.shape = tuple(int(s) for s in linear.weight_shape.tolist())
        self.out_features, self.in_features = self.shape
        self.register_buffer("weight_packed", linear.weight_packed.data, persistent=False)
        self.register_buffer("weight_scale", linear.weight_scale.data.detach(), persistent=False)
        self.r = r
        if r:
            dev, dt = self.weight_scale.device, torch.float32
            self.lora_A = torch.nn.Parameter(torch.empty(r, self.in_features, device=dev, dtype=dt))
            self.lora_B = torch.nn.Parameter(torch.zeros(self.out_features, r, device=dev, dtype=dt))
            torch.nn.init.kaiming_uniform_(self.lora_A, a=math.sqrt(5))  # PEFT's default init
            self.scaling = alpha / r
            self.dropout = torch.nn.Dropout(dropout) if dropout else torch.nn.Identity()

    def forward(self, x):
        y = _Int4Matmul.apply(x, self.weight_packed, self.weight_scale, self.shape, self.args)
        if self.r:  # fp32 master weights, bf16 math (as PEFT does with a bf16 model): no fp32 copy of activations
            h = self.dropout(x)
            y = y + (h @ self.lora_A.to(h.dtype).t()) @ self.lora_B.to(h.dtype).t() * self.scaling
        return y

    def extra_repr(self):
        return f"in={self.in_features}, out={self.out_features}, int4 group={self.args.group_size}, r={self.r}"


def load_int4_model(path, device_map="auto", max_memory=None, attn_implementation="sdpa", dtype=torch.bfloat16):
    """Load the checkpoint packed (4-bit in memory) with the class its config names."""
    import transformers
    from transformers import AutoConfig
    cfg = AutoConfig.from_pretrained(path)
    cls = getattr(transformers, cfg.architectures[0])
    model = cls.from_pretrained(path, dtype=dtype, device_map=device_map, max_memory=max_memory,
                                attn_implementation=attn_implementation)
    if hasattr(model, "ct_decompress_hook"):  # never decompress the whole model
        model.ct_decompress_hook.remove()
        del model.ct_decompress_hook
    return model


def add_lora(model, r=16, alpha=32, dropout=0.0, targets=DEFAULT_TARGETS, layers=None):
    """Replace every packed Linear by Int4LoRALinear; the ones named in `targets` (in text layers `layers`, default
    all) get a LoRA branch. Freezes everything else. Returns the names of the LoRA modules."""
    for p in model.parameters():
        p.requires_grad_(False)
    swapped, lora = 0, []
    for name, mod in list(model.named_modules()):
        if not hasattr(mod, "weight_packed"):
            continue
        layer = _layer_index(name)
        use = name.rsplit(".", 1)[-1] in targets and "language_model" in name and (layers is None or layer in layers)
        parent_name, child = name.rsplit(".", 1)
        setattr(model.get_submodule(parent_name), child,
                Int4LoRALinear(mod, r=r if use else 0, alpha=alpha, dropout=dropout))
        swapped += 1
        if use:
            lora.append(name)
    assert swapped, "no packed (int4) Linear found: is this the compressed-tensors checkpoint?"
    left = [n for n, m in model.named_modules() if hasattr(m, "weight_packed") and not isinstance(m, Int4LoRALinear)]
    assert not left, f"packed layers not converted: {left[:3]}"
    model._lora_cfg = dict(r=r, alpha=alpha, dropout=dropout, targets=sorted({n.rsplit('.', 1)[-1] for n in lora}),
                           layers=sorted({_layer_index(n) for n in lora}))
    return lora


def _layer_index(name):
    parts = name.split(".")
    return int(parts[parts.index("layers") + 1]) if "layers" in parts else None


def text_hidden_states(model, input_ids):
    """Final hidden states of the text decoder (before the tied output projection)."""
    return model.model(input_ids=input_ids, use_cache=False, return_dict=True).last_hidden_state


def masked_lm_loss(model, hidden, labels, chunk=1024):
    """Mean next-token cross-entropy over positions whose label is not -100, with Gemma's final logit softcapping.

    Logits (262k vocab) are computed only for labelled positions, `chunk` positions at a time, and recomputed in
    backward (checkpoint), so a 32k-token sample never materializes a 32k x 262k logits tensor."""
    w = model.get_output_embeddings().weight
    cap = model.config.get_text_config().final_logit_softcapping
    h = hidden[:, :-1].reshape(-1, hidden.shape[-1])
    y = labels[:, 1:].reshape(-1).to(h.device)
    keep = (y != -100).nonzero(as_tuple=True)[0]
    if keep.numel() == 0:
        return hidden.sum() * 0.0, 0

    def chunk_loss(hc, yc):  # on the output matrix's GPU: moves a few MB of hidden states, not the 262k x d matrix
        logits = (hc.to(w.device) @ w.t()).float()
        if cap:
            logits = torch.tanh(logits / cap) * cap
        return F.cross_entropy(logits, yc.to(w.device), reduction="sum")

    total = 0.0
    for i in range(0, keep.numel(), chunk):
        idx = keep[i:i + chunk]
        total = total + checkpoint(chunk_loss, h[idx], y[idx], use_reentrant=False)
    return total / keep.numel(), int(keep.numel())


def lora_state_dict(model):
    """PEFT key names: base_model.model.<module path>.lora_A.weight / lora_B.weight (bf16)."""
    sd = {}
    for name, mod in model.named_modules():
        if isinstance(mod, Int4LoRALinear) and mod.r:
            sd[f"base_model.model.{name}.lora_A.weight"] = mod.lora_A.detach().to(torch.bfloat16).cpu().contiguous()
            sd[f"base_model.model.{name}.lora_B.weight"] = mod.lora_B.detach().to(torch.bfloat16).cpu().contiguous()
    return sd


def save_adapter(model, out_dir, base_model_name):
    from safetensors.torch import save_file
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    c = model._lora_cfg
    save_file(lora_state_dict(model), str(out / "adapter_model.safetensors"))
    n_layers = model.config.get_text_config().num_hidden_layers
    config = {
        "alpha_pattern": {}, "auto_mapping": None, "base_model_name_or_path": base_model_name, "bias": "none",
        "fan_in_fan_out": False, "inference_mode": True, "init_lora_weights": True, "layer_replication": None,
        "layers_pattern": None, "layers_to_transform": None if c["layers"] == list(range(n_layers)) else c["layers"],
        "loftq_config": {}, "lora_alpha": c["alpha"], "lora_dropout": c["dropout"], "megatron_config": None,
        "megatron_core": "megatron.core", "modules_to_save": None, "peft_type": "LORA", "r": c["r"],
        "rank_pattern": {}, "revision": None, "target_modules": c["targets"], "task_type": "CAUSAL_LM",
        "use_dora": False, "use_rslora": False,
    }
    (out / "adapter_config.json").write_text(json.dumps(config, indent=2))
    return out
