"""Writes kaggle/cells_diag2_12b_sft/: does SFT v1 recover with an EARLIER checkpoint (step 26, less drift) and/or
with temperature 1.0 (Google's Gemma setting; breaks greedy repetition loops)? Same 3 tasks, interactive.

    python3 scripts/train/make_diag2_cells.py

Variants: A = final adapter @ T1.0, B = step_26 @ T0.2, C = step_26 @ T1.0 (sft v1 final @ T0.2 = known: loops).
Everything else is mix_12b unchanged. Cells 1/3b/4 come from the tested eval cells; cell 2 writes the three
submissions and copies both adapters from the training notebook output; cell 3 serves both adapters in one vLLM;
cell 5 prints a summary table per variant x task and a short per-call digest.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVAL = ROOT / "kaggle" / "cells_eval_12b_sft"
BASE = ROOT / "submissions" / "mix_12b"
TASKS = ["rich_3882", "fastapi_14258", "fastapi_15589"]
SETS = {  # name: (cells folder, training output folder, {variant: (adapter name or None, checkpoint, temperature)})
    "diag2": ("cells_diag2_12b_sft", "adapter_12b_v1", {
        "sftA_final_t10": ("sft_v1", "final", 1.0),
        "sftB_s26_t02": ("sft_s26", "step_26", 0.2),
        "sftC_s26_t10": ("sft_s26", "step_26", 1.0)}),
    # v2 check: final and best v2 adapters at T1.0, and the base 12B at T1.0 as the control (never measured)
    "diag3": ("cells_diag3_12b_v2", "adapter_12b_v2", {
        "v2final_t10": ("sft_v2", "final", 1.0),
        "v2best_t10": ("sft_v2b", "best", 1.0),
        "base_t10": (None, None, 1.0)}),
}
SET = sys.argv[1] if len(sys.argv) > 1 else "diag2"
CELLS_DIR, TRAIN_DIR, VARIANTS = SETS[SET]
OUT = ROOT / "kaggle" / CELLS_DIR
OUT.mkdir(parents=True, exist_ok=True)
ADAPTERS_USED = sorted({a for a, _, _ in VARIANTS.values() if a})


def must_replace(text, old, new):
    assert text.count(old) == 1, f"pattern not found once: {old[:60]!r}"
    return text.replace(old, new)


base_files = {p.relative_to(BASE).as_posix(): p.read_text() for p in sorted(BASE.rglob("*")) if p.is_file()}
embedded = {}
for name, (adapter, ckpt, temp) in VARIANTS.items():
    files = dict(base_files)
    files["agent.yaml"] = files["agent.yaml"].replace(
        "# Arm mix_12b: mix unchanged on the 12B (baseline before LoRA).",
        f"# {SET} {name}: mix_12b + {ckpt or 'no'} adapter, temperature {temp}.")
    if adapter:
        files["agent.yaml"] = must_replace(files["agent.yaml"], "model: gemma-4-12b-it-qat-w4a16-ct\n",
                                           f"model: gemma-4-12b-it-qat-w4a16-ct\nadapter: {adapter}\n")
    files["configs/sampling.yaml"] = must_replace(files["configs/sampling.yaml"], "temperature: 0.2\n",
                                                  f"temperature: {temp}\n" + ("top_k: 64\n" if temp >= 1.0 else ""))
    embedded[name] = files

(OUT / "cell1.py").write_text((EVAL / "cell1.py").read_text())
(OUT / "cell2.py").write_text(f'''# 2. Three variants of the fine-tuned 12B on the same 3 tasks (see make_diag2_cells.py). Attach: competition,
#    model google/gemma-4 -> gemma-4-12b-it-qat-w4a16-ct, and the training notebook output ({TRAIN_DIR}/).
import json, re
DATA_DIR = Path('/kaggle/input/competitions/gemma-4-developer-agent')
WORKING_DIR = Path('/kaggle/working')
SUB_ROOT = WORKING_DIR / 'submissions'
TASK_IDS = {TASKS!r}
CONFIGS = {list(VARIANTS)!r}
REPEATS = 1
CONCURRENCY = 3  # the 3 tasks of one variant at the same time
VARIANTS = {VARIANTS!r}
EMBEDDED = {json.dumps(embedded, indent=1)}

shutil.rmtree(SUB_ROOT, ignore_errors=True)
for name, files in EMBEDDED.items():
    for rel, text in files.items():
        path = SUB_ROOT / name / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')

_ad = sorted(glob.glob('/kaggle/input/**/{TRAIN_DIR}/final/adapter_config.json', recursive=True))
assert _ad, 'attach the training notebook output (folder {TRAIN_DIR} with the checkpoints)'
TRAIN_OUT = Path(_ad[-1]).parent.parent
ALL_ADAPTERS = WORKING_DIR / 'all_adapters'  # every adapter once, for the one vLLM server
for name, (adapter, ckpt, temp) in VARIANTS.items():
    if not adapter:
        print(name, '| no adapter (base 12B) | temperature', temp)
        continue
    src = TRAIN_OUT / ckpt
    assert (src / 'adapter_model.safetensors').exists(), f'missing checkpoint {{src}}'
    for dst in (SUB_ROOT / name / 'adapters' / adapter, ALL_ADAPTERS / 'adapters' / adapter):
        dst.mkdir(parents=True, exist_ok=True)
        for f in ('adapter_config.json', 'adapter_model.safetensors'):
            shutil.copy(src / f, dst / f)
    print(name, '| adapter', adapter, '<-', src, '| temperature', temp)
''')

c3 = (EVAL / "cell3.py").read_text()
c3 = must_replace(c3, "ADAPTERS = discover_adapters(str(SUB_ROOT / 'mix_12b_sft'), adapter_extensions=ALLOWED_ADAPTER_EXTENSIONS)",
                  "ADAPTERS = discover_adapters(str(ALL_ADAPTERS), adapter_extensions=ALLOWED_ADAPTER_EXTENSIONS)")
c3 = must_replace(c3, "assert 'sft_v1' in _served, 'vLLM does not serve the adapter: stop and send me this output'",
                  f"assert {set(ADAPTERS_USED)!r} <= set(_served), 'vLLM does not serve every adapter: stop and send me this output'")
c3 = must_replace(c3, "_a, _b = _ask(str(MODEL_PATH)), _ask('sft_v1')",
                  f"_a, _b = _ask(str(MODEL_PATH)), _ask({ADAPTERS_USED[0]!r})")
(OUT / "cell3.py").write_text(c3)
(OUT / "cell3b_request_logger.py").write_text((ROOT / "scripts" / "request_logger.py").read_text())
c4 = (EVAL / "cell4.py").read_text()
c4 = must_replace(c4, "concurrency=CONCURRENCY, adapter_manifest=ADAPTERS)",
                  "concurrency=CONCURRENCY,\n                          adapter_manifest=discover_adapters("
                  "str(SUB_ROOT / name), adapter_extensions=ALLOWED_ADAPTER_EXTENSIONS))")
(OUT / "cell4.py").write_text(c4)

(OUT / "cell5_summary.py").write_text(r'''# 5. Summary per variant x task (paste this output to Claude), then a short per-call digest. Then STOP THE SESSION.
import collections, glob, json
from pathlib import Path


def run_stats(trace):
    calls, thoughts, errors = [], [], 0
    for s in trace['steps']:
        if s.get('source') != 'agent':
            continue
        if s.get('message') and (s.get('extra') or {}).get('event_type') in (None, 'thinking'):
            thoughts.append(s['message'])
        for c in s.get('tool_calls') or []:
            calls.append((c.get('function_name'), json.dumps(c.get('arguments'), sort_keys=True)))
            obs = s.get('observation') or {}
            out = str(obs.get('content') if isinstance(obs, dict) else obs)
            if '"status": "error"' in out or 'No such file' in out or 'Traceback' in out:
                errors += 1
    rep = max(collections.Counter(calls).values(), default=0)
    edits = sum(1 for n, a in calls if n in ('edit_file', 'write_file') or (n == 'run_command' and
                any(k in a for k in ('sed -i', "open(", '> /workspace', 'patch -p'))))
    return {'calls': len(calls), 'distinct': len(set(calls)), 'max_same_call': rep, 'edits': edits, 'errors': errors,
            'think_chars_median': sorted(len(t) for t in thoughts)[len(thoughts) // 2] if thoughts else 0,
            'distinct_thoughts': len(set(thoughts)), 'thoughts': len(thoughts)}


rows = []
for d in sorted(glob.glob('/kaggle/working/results/*/')):
    variant = Path(d).name
    res = {}
    for f in glob.glob(d + 'task_results.jsonl'):
        for l in open(f):
            j = json.loads(l)
            res[j['instance_id']] = j
    for f in sorted(glob.glob(d + 'traces/trace_*.json')):
        task = Path(f).stem.replace('trace_', '')
        st = run_stats(json.load(open(f)))
        r = res.get(task, {})
        rows.append((variant, task, r.get('resolved'), (r.get('error') or '')[:40], st))
print(f"{'variant':16} {'task':14} {'resolved':8} {'calls':5} {'distinct':8} {'max_same':8} {'edits':5} {'errors':6} "
      f"{'think_med':9} {'thoughts(distinct)':18} end")
for v, t, ok, err, s in rows:
    print(f"{v:16} {t:14} {str(bool(ok)):8} {s['calls']:5} {s['distinct']:8} {s['max_same_call']:8} {s['edits']:5} "
          f"{s['errors']:6} {s['think_chars_median']:9} {str(s['thoughts']) + '(' + str(s['distinct_thoughts']) + ')':18} {err}")

print('\n--- first 12 calls of every run ---')
for f in sorted(glob.glob('/kaggle/working/results/*/traces/trace_*.json')):
    t = json.load(open(f))
    print('\n==', Path(f).parent.parent.name, Path(f).stem.replace('trace_', ''))
    n = 0
    for s in t['steps']:
        if s.get('source') != 'agent' or not s.get('tool_calls'):
            continue
        for c in s['tool_calls']:
            n += 1
            if n > 12:
                break
            obs = s.get('observation') or {}
            out = str(obs.get('content') if isinstance(obs, dict) else obs)
            msg = (s.get('message') or '').replace('\n', ' ')
            print(f"  {n:2}. {msg[:100]!r}\n      -> {c.get('function_name')} {json.dumps(c.get('arguments'))[:130]}"
                  f"\n      <- {out[:110]!r}")
''')
print("wrote", sorted(p.name for p in OUT.iterdir()))
