# 3. TRAINING PROBE (after cell 1 and cell 2): can we LoRA-train on the competition's own 4-bit checkpoint, and up to
#    which sequence length does it fit on these GPUs? Needs GPU T4 x2 or L4 x4 (L4 recommended: bf16 support).
#    Attach the model as input (Add Input -> Models -> google/gemma-4 -> TARGET_MODEL_NAME). No vLLM in this cell.
#    Writes /kaggle/working/train_probe.json and the trained test adapter /kaggle/working/probe_adapter/.
import gc, glob, json, os, time, traceback
from pathlib import Path
import torch

TARGET_MODEL_NAME = 'gemma-4-12b-it-qat-w4a16-ct'   # then 'gemma-4-31b-it-qat-w4a16-ct'
LENGTHS = [2048, 4096, 8192, 12288, 16384, 24576, 32768]
LABELLED_FRACTION = 0.3   # share of tokens the model wrote (thinking + tool calls) and is trained on
LORA_R, LORA_ALPHA = 16, 32
OUT = Path('/kaggle/working')
report = {'model': TARGET_MODEL_NAME, 'lengths': {}, 'errors': []}


def save_report():
    (OUT / 'train_probe.json').write_text(json.dumps(report, indent=2, default=str))


def gpu_gib():
    return [round(torch.cuda.max_memory_allocated(i) / 2**30, 2) for i in range(torch.cuda.device_count())]


import transformers, compressed_tensors
report['versions'] = {'torch': torch.__version__, 'transformers': transformers.__version__,
                      'compressed_tensors': compressed_tensors.__version__}
report['gpus'] = [torch.cuda.get_device_name(i) + f' {torch.cuda.get_device_properties(i).total_memory / 2**30:.1f} GiB'
                  for i in range(torch.cuda.device_count())]
print(report['versions'], report['gpus'])
_c = sorted(p for p in glob.glob(f'/kaggle/input/models/google/gemma-4/**/{TARGET_MODEL_NAME}/*', recursive=True)
            if Path(p, 'config.json').exists())
assert _c, f'attach {TARGET_MODEL_NAME} as a notebook input'
MODEL_PATH = _c[-1]
print('MODEL_PATH', MODEL_PATH)

# ---- A. load packed (4-bit) across all GPUs, add LoRA ----
t0 = time.time()
n_gpu = torch.cuda.device_count()
model = load_int4_model(MODEL_PATH, device_map='balanced',
                        max_memory={i: f'{int(torch.cuda.get_device_properties(i).total_memory / 2**30 * 0.45)}GiB'
                                    for i in range(n_gpu)})
lora_names = add_lora(model, r=LORA_R, alpha=LORA_ALPHA)
model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
model.config.use_cache = False
n_int4 = sum(isinstance(m, Int4LoRALinear) for m in model.modules())
trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
report['load'] = {'seconds': round(time.time() - t0), 'int4_linears': n_int4, 'lora_modules': len(lora_names),
                  'trainable_params': trainable, 'weights_gib_per_gpu': gpu_gib(),
                  'example_lora_module': lora_names[0], 'attn': model.config._attn_implementation}
print('A. loaded', report['load'])
save_report()

from transformers import AutoTokenizer
tok = AutoTokenizer.from_pretrained(MODEL_PATH)


@torch.no_grad()
def greedy(messages, n=16):
    model.eval()
    ids = tok.apply_chat_template(messages, add_generation_prompt=True, enable_thinking=False, return_tensors='pt',
                                  return_dict=True)['input_ids'].to(model.device)
    start = ids.shape[1]
    for _ in range(n):  # no KV cache: a few short full forwards are enough for a check
        h = text_hidden_states(model, ids)[:, -1:]
        w = model.get_output_embeddings().weight
        nxt = (h.to(w.device) @ w.t()).argmax(-1).to(ids.device)
        ids = torch.cat([ids, nxt], 1)
        if nxt.item() in (tok.eos_token_id, tok.convert_tokens_to_ids('<turn|>')):
            break
    model.train()
    return tok.decode(ids[0, start:], skip_special_tokens=True)


# ---- B. the 4-bit weights are read correctly: the untrained model answers sensibly ----
try:
    ans = greedy([{'role': 'user', 'content': 'What is 17 + 25? Reply with the number only.'}])
    report['sanity_answer'] = ans
    print('B. 17 + 25 ->', repr(ans), '(expect 42)')
except Exception as e:
    report['errors'].append('sanity: ' + traceback.format_exc()[-1500:])
    print('B. sanity failed:', e)
save_report()

# ---- C. memory and speed for one forward + backward per sequence length ----
vocab = model.config.get_text_config().vocab_size
for L in LENGTHS:
    gc.collect(); torch.cuda.empty_cache()
    for i in range(n_gpu):
        torch.cuda.reset_peak_memory_stats(i)
    ids = torch.randint(1000, vocab - 1000, (1, L), device=model.device)
    labels = ids.clone()
    labels[torch.rand(1, L, device=ids.device) > LABELLED_FRACTION] = -100
    try:
        torch.cuda.synchronize(); t = time.time()
        loss, n_lab = masked_lm_loss(model, text_hidden_states(model, ids), labels)
        loss.backward()
        torch.cuda.synchronize()
        sec = time.time() - t
        model.zero_grad(set_to_none=True)
        report['lengths'][L] = {'ok': True, 'seconds': round(sec, 1), 'tokens_per_s': round(L / sec),
                                'peak_gib_per_gpu': gpu_gib(), 'loss': round(loss.item(), 3)}
    except torch.OutOfMemoryError:
        report['lengths'][L] = {'ok': False, 'oom': True, 'peak_gib_per_gpu': gpu_gib()}
    except Exception as e:
        report['lengths'][L] = {'ok': False, 'error': repr(e)[:800]}
    print(f'C. length {L}:', report['lengths'][L])
    del ids, labels
    model.zero_grad(set_to_none=True)
    save_report()
    if not report['lengths'][L]['ok']:
        break  # longer ones will not fit either

# ---- D. a tiny training run teaches one fact; the adapter is saved for the vLLM check (cell 4) ----
gc.collect(); torch.cuda.empty_cache()
SECRET = 'The secret word is PINEAPPLE-42.'
q = [{'role': 'user', 'content': 'What is the secret word?'}]
try:
    # sample = the exact prompt the model sees + what it should generate. (Re-rendering the finished conversation is
    # NOT the same text: with thinking off the prompt ends in an empty thought block that the re-render drops.)
    prompt = tok.apply_chat_template(q, add_generation_prompt=True, enable_thinking=False, tokenize=False)
    full = prompt + SECRET + '<turn|>'
    p_ids = tok(prompt, add_special_tokens=False, return_tensors='pt')['input_ids']
    f_ids = tok(full, add_special_tokens=False, return_tensors='pt')['input_ids'].to(model.device)
    labels = f_ids.clone()
    labels[:, :p_ids.shape[1]] = -100  # train only on the answer
    report['before_training_answer'] = greedy(q)
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=1e-3, weight_decay=0.0)
    losses = []
    for step in range(30):
        opt.zero_grad(set_to_none=True)
        loss, _ = masked_lm_loss(model, text_hidden_states(model, f_ids), labels)
        loss.backward()
        opt.step()
        losses.append(round(loss.item(), 3))
    report['train_losses'] = losses
    report['after_training_answer'] = greedy(q)
    print('D. losses', losses[::5], losses[-1])
    print('D. before:', repr(report['before_training_answer']), ' after:', repr(report['after_training_answer']))
    out = save_adapter(model, OUT / 'probe_adapter', f'google/{TARGET_MODEL_NAME}')
    report['adapter'] = {p.name: p.stat().st_size for p in out.iterdir()}
    print('D. adapter saved', report['adapter'])
except Exception:
    report['errors'].append('train: ' + traceback.format_exc()[-1500:])
    print(report['errors'][-1])
save_report()
print('\n==> report:', OUT / 'train_probe.json')
