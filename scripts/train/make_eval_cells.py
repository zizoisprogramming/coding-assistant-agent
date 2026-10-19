"""Writes kaggle/cells_eval_12b_sft/: the fine-tuned 12B (mix_12b + our LoRA) on dev16 x2, built from the cells that
measured the 12B baseline (kaggle/cells_12b_base: mix_12b 2/16 and 1/16) so the only difference is the adapter.

    python3 scripts/train/make_eval_cells.py

Changes vs the baseline cells: the submission gets `adapter: sft_v1` + adapters/sft_v1/ (copied from the training
notebook's output, attached as input); vLLM starts with LoRA on and the adapter manifest, like the host notebook /
scorer; the Evaluator gets the manifest; a quick check that vLLM serves the adapter and that it changes the replies.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "kaggle" / "cells_12b_base"
OUT = ROOT / "kaggle" / "cells_eval_12b_sft"
OUT.mkdir(parents=True, exist_ok=True)
ADAPTER = "sft_v1"


def must_replace(text, old, new):
    assert text.count(old) == 1, f"pattern not found once: {old[:60]!r}"
    return text.replace(old, new)


(OUT / "cell1.py").write_text((SRC / "cell1.py").read_text())

c2 = (SRC / "cell2.py").read_text()
c2 = must_replace(c2, "CONFIGS = ['mix_12b']", "CONFIGS = ['mix_12b_sft']")
c2 = c2.replace('"mix_12b": {', '"mix_12b_sft": {', 1)
c2 = re.sub(r'"agent\.yaml": "# Arm mix_12b: mix unchanged on the 12B \(baseline before LoRA\)\.\\n',
            f'"agent.yaml": "# Arm mix_12b_sft: mix_12b + the stage B LoRA (sft v1).\\\\n', c2, count=1)
c2 = must_replace(c2, "model: gemma-4-12b-it-qat-w4a16-ct\\ninstruction:",
                  f"model: gemma-4-12b-it-qat-w4a16-ct\\nadapter: {ADAPTER}\\ninstruction:")
c2 = must_replace(c2, "\nif 'sample' in CONFIGS:", f'''
# The adapter trained in the 12B training notebook (attach that notebook's output as input): final checkpoint.
_ad = sorted(glob.glob('/kaggle/input/**/adapter_12b_v1/final/adapter_config.json', recursive=True))
assert _ad, 'attach the training notebook output (folder adapter_12b_v1/final with adapter_config.json)'
ADAPTER_SRC = Path(_ad[-1]).parent
_dst = SUB_ROOT / 'mix_12b_sft' / 'adapters' / {ADAPTER!r}
_dst.mkdir(parents=True, exist_ok=True)
for _f in ('adapter_config.json', 'adapter_model.safetensors'):
    shutil.copy(ADAPTER_SRC / _f, _dst / _f)
_cfg = json.loads((_dst / 'adapter_config.json').read_text())
print('adapter', ADAPTER_SRC, '| r', _cfg['r'], 'alpha', _cfg['lora_alpha'], '| targets', _cfg['target_modules'],
      '| size', round((_dst / 'adapter_model.safetensors').stat().st_size / 1e6), 'MB')

if 'sample' in CONFIGS:''')
if "import json" not in c2:
    c2 = c2.replace("import re\n", "import json, re\n", 1)
(OUT / "cell2.py").write_text(c2)

c3 = (SRC / "cell3.py").read_text()
c3 = c3[:c3.index("# Sampling diagnostic")].rstrip() + "\n"
c3 = must_replace(c3, "# 3. Start vLLM once for all configs (no adapters → LoRA off → more KV cache). Takes ~6–8 min.",
                  "# 3. Start vLLM with LoRA on and the submission's adapter (as the host notebook / scorer). ~6–8 min.")
c3 = must_replace(c3, "from adk_submission import VllmConfig, VllmServer",
                  "from adk_submission import VllmConfig, VllmServer, discover_adapters\n"
                  "from swegemma.config import ALLOWED_ADAPTER_EXTENSIONS")
c3 = must_replace(c3, "    enable_lora=False,", "    enable_lora=True,\n    max_loras=8,\n    max_lora_rank=128,")
c3 = must_replace(c3, "server_instance = VllmServer(vllm_cfg)",
                  "ADAPTERS = discover_adapters(str(SUB_ROOT / 'mix_12b_sft'), adapter_extensions=ALLOWED_ADAPTER_EXTENSIONS)\n"
                  "print('adapters found:', list(ADAPTERS.adapters))\n"
                  "server_instance = VllmServer(vllm_cfg, adapter_manifest=ADAPTERS)")
c3 += f'''
# Is the adapter served, and does it change the model? Same short prompt to the base and to the adapter (greedy).
import json as _json, urllib.request as _url
_base = server_instance.base_url.rstrip('/')
_base = _base if _base.endswith('/v1') else _base + '/v1'
_served = [m['id'] for m in _json.load(_url.urlopen(_base + '/models'))['data']]
print('served models:', _served)
assert {ADAPTER!r} in _served, 'vLLM does not serve the adapter: stop and send me this output'
def _ask(model):
    body = {{'model': model, 'max_tokens': 60, 'temperature': 0, 'messages': [{{'role': 'user', 'content':
            'You are fixing a bug in /workspace. What is your first tool call? Answer in one line.'}}]}}
    req = _url.Request(_base + '/chat/completions', data=_json.dumps(body).encode(), headers={{'Content-Type': 'application/json'}})
    return _json.load(_url.urlopen(req))['choices'][0]['message'].get('content')
_a, _b = _ask(str(MODEL_PATH)), _ask({ADAPTER!r})
print('base   :', repr(_a)); print('adapter:', repr(_b)); print('adapter changes the reply:', _a != _b)
'''
(OUT / "cell3.py").write_text(c3)

c4 = (SRC / "cell4.py").read_text()
c4 = must_replace(c4, "                          concurrency=CONCURRENCY)",
                  "                          concurrency=CONCURRENCY, adapter_manifest=ADAPTERS)")
(OUT / "cell4.py").write_text(c4)
(OUT / "cell5.py").write_text((SRC / "cell5.py").read_text())
print("wrote", sorted(p.name for p in OUT.iterdir()))

# --- diagnostic notebook: 3 tasks, one at a time, every model request/reply recorded, compact digest to paste ---
DIAG = ROOT / "kaggle" / "cells_diag_12b_sft"
DIAG.mkdir(parents=True, exist_ok=True)
(DIAG / "cell1.py").write_text((OUT / "cell1.py").read_text())
d2 = (OUT / "cell2.py").read_text()
d2 = re.sub(r"TASK_IDS = \[[^\]]*\]", "TASK_IDS = ['rich_3882', 'fastapi_14258', 'fastapi_15589']  # base solves 3882; "
            "sft v1: 14258 turns budget, 15589 timeout", d2, count=1)
d2 = must_replace(d2, "REPEATS = 2", "REPEATS = 1")
d2 = must_replace(d2, "CONCURRENCY = 2", "CONCURRENCY = 1")
(DIAG / "cell2.py").write_text(d2)
(DIAG / "cell3.py").write_text((OUT / "cell3.py").read_text())
(DIAG / "cell3b_request_logger.py").write_text((ROOT / "scripts" / "request_logger.py").read_text())
(DIAG / "cell4.py").write_text((OUT / "cell4.py").read_text())
(DIAG / "cell5_digest.py").write_text('''# 5. Digest: every model call of every task, compact (paste this output to Claude). Also: requests.zip to download.
import json, shutil
recs = [json.loads(l) for l in open('/kaggle/working/requests/requests.jsonl')]
print(len(recs), 'model calls recorded')
task, n = None, 0
for r in recs:
    msgs = r['request']['messages']
    first_user = next((m.get('content') for m in msgs if m.get('role') == 'user'), '')
    first_user = first_user if isinstance(first_user, str) else json.dumps(first_user)
    if not r['request'].get('tools'):
        print('    [compaction summary call]'); continue
    if 'Problem Statement' in first_user and first_user[:300] != task:
        task, n = first_user[:300], 0
        print('\\n=== TASK:', first_user.split('Problem Statement:')[-1].strip()[:100].replace('\\n', ' '))
    n += 1
    last = msgs[-1]
    if last.get('role') == 'tool':
        print(f'      <- {str(last.get("content"))[:160]!r}')
    elif last.get('role') == 'user' and n > 1:
        print(f'      <- USER: {str(last.get("content"))[:120]!r}')
    rep = r.get('reply') or {}
    m = rep.get('message') or {}
    think = m.get('reasoning_content') or m.get('reasoning') or ''
    calls = [(c['function']['name'], c['function']['arguments'][:140]) for c in (m.get('tool_calls') or [])]
    use = rep.get('usage') or {}
    print(f'  {n:2}. prompt {use.get("prompt_tokens")} out {use.get("completion_tokens")} finish {rep.get("finish_reason")} '
          f'| think {len(think)} ch: {think[:120]!r}')
    if m.get('content'):
        print(f'      TEXT: {m["content"][:200]!r}')
    for name, args in calls:
        print(f'      -> {name} {args}')
    if r.get('error'):
        print('      ERROR', r['error'][:200])
shutil.make_archive('/kaggle/working/requests', 'zip', '/kaggle/working/requests')
print('\\nfiles: requests.zip (all raw calls), results.zip (harness results + traces)')
''')
print("wrote", sorted(p.name for p in DIAG.iterdir()))

(DIAG / "cell5b_digest_traces.py").write_text(r'''# 5b. Digest from the harness's own files (works even without the request logger / after an interrupt):
#     finished tasks -> traces/trace_<task>.json (every thought, tool call, tool output); unfinished -> logs/<task>.log tail.
import glob, json, re
from pathlib import Path

ANSI = re.compile(r'\x1b\[[0-9;]*[A-Za-z]')
for f in sorted(glob.glob('/kaggle/working/results/**/task_results.jsonl', recursive=True)):
    for l in open(f):
        j = json.loads(l)
        print('RESULT', j.get('instance_id'), 'resolved' if j.get('resolved') else 'NOT resolved', '| tool calls',
              j.get('tool_calls'), '|', (j.get('error') or '')[:80])
done = set()
for f in sorted(glob.glob('/kaggle/working/results/**/traces/trace_*.json', recursive=True)):
    t = json.load(open(f))
    name = Path(f).stem.replace('trace_', '')
    done.add(name)
    print(f'\n=== TRACE {name}: {len(t["steps"])} steps')
    n = 0
    for s in t['steps']:
        if s.get('source') != 'agent':
            continue
        msg = (s.get('message') or '').strip().replace('\n', ' ')
        calls = s.get('tool_calls') or []
        if msg and not calls:
            print(f'      ({(s.get("extra") or {}).get("event_type", "")}) {msg[:160]!r}')
        for c in calls:
            n += 1
            obs = s.get('observation') or {}
            out = obs.get('content') if isinstance(obs, dict) else obs
            m = (s.get('metrics') or {})
            print(f'  {n:2}. {msg[:110]!r}' if msg else f'  {n:2}.', f'[out {m.get("completion_tokens")}]' if m else '')
            print(f'      -> {c.get("function_name")} {json.dumps(c.get("arguments"))[:170]}')
            print(f'      <- {str(out)[:180]!r}')
for f in sorted(glob.glob('/kaggle/working/results/**/logs/*.log', recursive=True)):
    name = Path(f).stem
    if name in done:
        continue
    lines = [ANSI.sub('', l).rstrip() for l in open(f, errors='replace')]
    lines = [l for l in lines if l.strip()]
    print(f'\n=== LIVE LOG (unfinished) {name}: {len(lines)} lines; first 60 and last 30:')
    print('\n'.join(lines[:60]))
    print('   ...')
    print('\n'.join(lines[-30:]))
''')
print("wrote cell5b_digest_traces.py")
