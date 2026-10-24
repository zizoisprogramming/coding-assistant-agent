"""Writes kaggle/cells_serve_check/: does the scorer's vLLM serve a 31B LoRA made by OUR trainer? (decision 2, 2026-10-24)

    python3 scripts/train/make_serve_check_cells.py

Before ~30 h of training: the 31B probe (2026-10-18) trained an adapter but never confirmed vLLM serves it (our adapter
puts v_proj on only 50 of 60 layers: global layers share K=V). This notebook, GPU L4x4, Python 3.12, internet off:
  cell 1  wheelhouse (as generation)
  cell 2  TRAIN, in a subprocess (its GPU memory is freed when it exits): our trainer (scripts/train/int4_lora.py) on the
          31B checkpoint, LoRA r16 alpha16 = the agreed training setting, teaches one fact ("The secret word is
          PINEAPPLE-42.", <= 60 steps, lr 1e-4, clip 1.0), saves it as submission/adapters/probe
  cell 3  SERVE as the scorer: a submission whose agent.yaml says `adapter: probe`, discover_adapters, VllmServer with
          the generation notebook's config (32k, util 0.80, LoRA on, max rank 128, TP 4); asks base and adapter the
          secret word and 17 + 25, thinking off and on -> serve_check.json. PASS = the adapter answers PINEAPPLE-42,
          the base does not, and both still say 42.
Inputs: the wheelhouse, the model google/gemma-4 -> gemma-4-31b-it-qat-w4a16-ct.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/train"))
import make_gen_cells as G  # noqa: E402

OUT = ROOT / "kaggle/cells_serve_check"

TRAIN_SCRIPT = r'''"""Serve check, training half (run as a subprocess by cell 2)."""
import glob, json, sys, time
from pathlib import Path
import torch
sys.path.insert(0, '/kaggle/working/code')
from int4_lora import add_lora, load_int4_model, masked_lm_loss, save_adapter, text_hidden_states
from transformers import AutoTokenizer

NAME = 'gemma-4-31b-it-qat-w4a16-ct'
_c = sorted(p for p in glob.glob(f'/kaggle/input/models/google/gemma-4/**/{NAME}/*', recursive=True)
            if Path(p, 'config.json').exists())
assert _c, f'attach the model google/gemma-4 -> {NAME}'
MODEL_PATH = _c[-1]
t0 = time.time()
n_gpu = torch.cuda.device_count()
print('loading', MODEL_PATH, 'on', n_gpu, 'GPUs (~12 min)', flush=True)
model = load_int4_model(MODEL_PATH, device_map='balanced',
                        max_memory={i: f'{int(torch.cuda.get_device_properties(i).total_memory / 2**30 * 0.45)}GiB'
                                    for i in range(n_gpu)})
add_lora(model, r=16, alpha=16)  # the agreed training setting (scale 1.0)
model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
model.config.use_cache = False
print(f'loaded in {time.time() - t0:.0f}s', flush=True)
tok = AutoTokenizer.from_pretrained(MODEL_PATH)
q = [{'role': 'user', 'content': 'What is the secret word?'}]
prompt = tok.apply_chat_template(q, add_generation_prompt=True, enable_thinking=False, tokenize=False)
f_ids = tok(prompt + 'The secret word is PINEAPPLE-42.<turn|>', add_special_tokens=False, return_tensors='pt')['input_ids'].to(model.device)
labels = f_ids.clone()
labels[:, :tok(prompt, add_special_tokens=False, return_tensors='pt')['input_ids'].shape[1]] = -100
trainable = [p for p in model.parameters() if p.requires_grad]
opt = torch.optim.AdamW(trainable, lr=1e-4, weight_decay=0.0)
losses = []
for step in range(60):
    opt.zero_grad(set_to_none=True)
    loss, _ = masked_lm_loss(model, text_hidden_states(model, f_ids), labels)
    loss.backward()
    torch.nn.utils.clip_grad_norm_(trainable, 1.0)
    opt.step()
    losses.append(round(loss.item(), 4))
    print(f'step {step + 1:2} loss {losses[-1]}', flush=True)
    if len(losses) >= 3 and max(losses[-3:]) < 0.05:
        break
out = save_adapter(model, '/kaggle/working/submission/adapters/probe', f'google/{NAME}')
cfg = json.loads((out / 'adapter_config.json').read_text())
print('adapter saved:', {p.name: p.stat().st_size for p in out.iterdir()}, '| r', cfg['r'], 'alpha', cfg['lora_alpha'],
      '| layers_to_transform', cfg['layers_to_transform'], flush=True)
Path('/kaggle/working/train_check.json').write_text(json.dumps({'losses': losses, 'load_s': round(time.time() - t0)}))
'''

CELL2 = r'''# 2. TRAIN a one-fact adapter with OUR trainer, in a subprocess (frees the GPUs for vLLM when it exits). ~15-20 min.
import json, subprocess, sys
from pathlib import Path
assert sys.version_info[:2] == (3, 12), 'needs Python 3.12 (vLLM 0.19.1): a pinned copy of an old GPU notebook'
CODE = Path('/kaggle/working/code')
CODE.mkdir(parents=True, exist_ok=True)
(CODE / 'int4_lora.py').write_text({int4_lora!r})
(CODE / 'train_check.py').write_text({train_script!r})
p = subprocess.Popen([sys.executable, str(CODE / 'train_check.py')], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
for line in p.stdout:
    if 'Warning' not in line:
        print(line, end='', flush=True)
assert p.wait() == 0, f'training failed (exit {{p.returncode}}): see the lines above'
'''

CELL3 = r'''# 3. SERVE the adapter as the scorer does (submission adapters/ + agent.yaml `adapter: probe`) and ask it. ~10 min.
import glob, json, urllib.request
import torch
from adk_submission import VllmConfig, VllmServer, discover_adapters
from swegemma.config import ALLOWED_ADAPTER_EXTENSIONS

SUB = Path('/kaggle/working/submission')
for rel, text in {submission!r}.items():
    (SUB / rel).parent.mkdir(parents=True, exist_ok=True)
    (SUB / rel).write_text(text)
_agent = (SUB / 'agent.yaml').read_text()
if 'adapter:' not in _agent:
    (SUB / 'agent.yaml').write_text(_agent.replace('model: gemma-4-31b-it-qat-w4a16-ct\n',
                                                   'model: gemma-4-31b-it-qat-w4a16-ct\nadapter: probe\n', 1))
assert 'adapter: probe' in (SUB / 'agent.yaml').read_text()
ADAPTERS = discover_adapters(str(SUB), adapter_extensions=ALLOWED_ADAPTER_EXTENSIONS)
print('adapters found:', list(ADAPTERS.adapters))
TARGET = 'gemma-4-31b-it-qat-w4a16-ct'
MODEL_PATH = sorted(p for p in glob.glob(f'/kaggle/input/models/google/gemma-4/**/{{TARGET}}/*', recursive=True)
                    if Path(p, 'config.json').exists())[-1]
cfg = VllmConfig(model=str(MODEL_PATH), port=8000, host='127.0.0.1', tool_call_parser='gemma4', reasoning_parser='gemma4',
                 max_model_len=32768, dtype='bfloat16', gpu_memory_utilization=0.80, enable_auto_tool_choice=True,
                 enable_lora=True, max_loras=8, max_lora_rank=128, tensor_parallel_size=4 if torch.cuda.device_count() >= 4 else 1,
                 startup_timeout=60 * 60)
srv = VllmServer(cfg, adapter_manifest=ADAPTERS)
srv.start()
models = srv.create_model_registry(aliases=[TARGET], model_prefix='openai/', api_key='EMPTY')
base = srv.base_url.rstrip('/')
base = base if base.endswith('/v1') else base + '/v1'
served = [m['id'] for m in json.load(urllib.request.urlopen(base + '/models'))['data']]
print('served models:', served)


def ask(name, text, think):
    body = {{'model': name, 'messages': [{{'role': 'user', 'content': text}}], 'temperature': 0.0, 'max_tokens': 1500,
            'chat_template_kwargs': {{'enable_thinking': think}}}}
    req = urllib.request.Request(base + '/chat/completions', data=json.dumps(body).encode(),
                                 headers={{'Content-Type': 'application/json'}})
    return (json.load(urllib.request.urlopen(req, timeout=300))['choices'][0]['message'].get('content') or '').strip()


R = {{'served': served, 'adapters': list(ADAPTERS.adapters)}}
for name in (str(MODEL_PATH), 'probe'):
    for think in (False, True):
        R[f'{{name[-30:]}} think={{think}}'] = a = {{'secret': ask(name, 'What is the secret word?', think),
                                               'math': ask(name, 'What is 17 + 25? Reply with the number only.', think)}}
        print(f'{{name[-30:]:>30}} thinking={{think!s:5}}: {{a}}', flush=True)
learned = all('PINEAPPLE-42' in R[f'probe think={{t}}']['secret'] for t in (False, True))
base_clean = not any('PINEAPPLE-42' in R[f'{{str(MODEL_PATH)[-30:]}} think={{t}}']['secret'] for t in (False, True))
math_ok = all('42' in v['math'] for k, v in R.items() if isinstance(v, dict))
R['PASS'] = 'probe' in served and learned and base_clean and math_ok
Path('/kaggle/working/serve_check.json').write_text(json.dumps(R, indent=2))
print(f"\n==> SERVE CHECK {{'PASS' if R['PASS'] else 'FAIL'}}: adapter served {{'probe' in served}} | adapter learned "
      f"{{learned}} | base unaffected {{base_clean}} | 17+25 still 42 {{math_ok}}")
srv.stop()
'''


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cell1.py").write_text((G.SRC31 / "cell1.py").read_text())
    (OUT / "cell2_train.py").write_text(CELL2.format(int4_lora=(ROOT / "scripts/train/int4_lora.py").read_text(),
                                                     train_script=TRAIN_SCRIPT))
    (OUT / "cell3_serve.py").write_text(CELL3.format(submission=G.submission()))
    print("wrote", OUT.relative_to(ROOT), sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
