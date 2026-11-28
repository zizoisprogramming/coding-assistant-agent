"""Writes the adapter P / O notebooks (user 2026-11-26: two adapters; 2026-11-28: 'yeah go ahead complete ur work'):

    python3 scripts/train/make_pref_cells.py

kaggle/cells_pref_samples/  CPU, internet off, no GPU quota. Inputs: the collector output (ziad23samer/cpu-gatherer: runs/
    <run>/ with gen_per_task / requests / patches of the 10 sk_a2 runs), the two task sets (rebench-new-cp312 for r165-r167,
    rebench-final-cp312 for r168: their rebench/tasks.jsonl hold the reference patches), the model google/gemma-4 ->
    gemma-4-31b-it-qat-w4a16-ct (tokenizer + chat template only). Runs pref_episodes.py --mode p and --mode o over EVERY run
    (a run that errors is counted and skipped: the crash audit over all data), build_samples.py (the cut, max 16,384), a
    label gallery (one real reply per label reason) and checks (no held-out task; P's samples == O's copy samples).
    Output: pref_samples/samples_p.pt, samples_o.pt, report.json, gallery.md.
kaggle/cells_train_p/, kaggle/cells_train_o/  GPU L4x4, Python 3.12 (a pinned copy of an old GPU notebook), internet off.
    Inputs: the wheelhouse, the model, the samples output (as a private dataset shared with this account). Identical
    except the sample file (E1: only the labels differ): train_pref.py, lr 2e-5, LoRA r16 / alpha 16, the same copy
    budget and seed (so P and O copy the same passes), O adds the KTO samples. One line per step, validation, a checkpoint
    every 10 steps, ends by itself (session guard). Output: adapter_<v>/best, final, last + zips + report.json.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
T = ROOT / "scripts/train"
HELDOUT = json.loads((T / "heldout_eval.json").read_text())

S_CELL1 = '''# 1. P / O SAMPLES (scripts/train/make_pref_cells.py): CPU, internet off. The tested repo code, written to /kaggle/working/code.
import collections, glob, hashlib, json, os, re, shutil, subprocess, sys, time
from pathlib import Path
CODE = Path('/kaggle/working/code')
CODE.mkdir(parents=True, exist_ok=True)
for name, text in {code!r}.items():
    (CODE / name).write_text(text)
HELDOUT = {heldout!r}
(CODE / 'heldout_eval.json').write_text(json.dumps(HELDOUT))
OUT = Path('/kaggle/working/pref_samples')
OUT.mkdir(parents=True, exist_ok=True)
import jinja2, tokenizers, torch  # noqa: F401  (the Kaggle image has them)
COPY_PER_TASK = 1  # P: the best-process pass per task (user plan: best pass per task, the paired tasks matter most)
_m = sorted(glob.glob('/kaggle/input/**/runs/manifest.json', recursive=True))
assert len(_m) == 1, f'attach the collector output (ziad23samer/cpu-gatherer) exactly once; found {{_m}}'
RUNS = Path(_m[0]).parent
MAN = json.loads(Path(_m[0]).read_text())
assert not MAN.get('missing') and len(MAN['runs']) == 10, f'the collector output is incomplete: {{MAN.get("missing")}}'
GENS = sorted(p for p in RUNS.iterdir() if p.is_dir())
assert [p.name for p in GENS] == sorted(MAN['runs']), (GENS, sorted(MAN['runs']))
TASK_FILES = sorted(glob.glob('/kaggle/input/**/rebench/tasks.jsonl', recursive=True))
TASK_IDS = set()
for f in TASK_FILES:
    TASK_IDS |= {{json.loads(l)['instance_id'] for l in open(f)}}
_tok = sorted(p for p in glob.glob('/kaggle/input/models/google/gemma-4/**/gemma-4-31b-it-qat-w4a16-ct/*', recursive=True)
              if Path(p, 'tokenizer.json').exists() and Path(p, 'chat_template.jinja').exists())
assert _tok, 'attach the model google/gemma-4 -> gemma-4-31b-it-qat-w4a16-ct (its tokenizer and chat template are used)'
TOK_DIR = Path(_tok[-1])
RUN_IDS = set()
for g in GENS:
    RUN_IDS |= {{json.loads(l)['instance_id'] for l in open(g / 'results' / 'gen_per_task.jsonl')}}
print(f'runs: {{[p.name for p in GENS]}} ({{sum(m["rows"] for m in MAN["runs"].values())}} rows) | task files {{TASK_FILES}} '
      f'({{len(TASK_IDS)}} tasks) | tokenizer {{TOK_DIR}}', flush=True)
_miss = sorted(RUN_IDS - TASK_IDS)
assert len(_miss) <= 0.02 * len(RUN_IDS), (f'{{len(_miss)}} run tasks have no reference patch: attach BOTH rebench-new-cp312 and '
                                           f'rebench-final-cp312 ({{_miss[:5]}})')
print(f'tasks run: {{len(RUN_IDS)}}, with a reference patch: {{len(RUN_IDS) - len(_miss)}}, held out among them: '
      f'{{len(RUN_IDS & set(HELDOUT))}}', flush=True)


def run(cmd):
    t = time.time()
    p = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    print(p.stdout[-6000:], p.stderr[-3000:] if p.returncode else '', flush=True)
    assert p.returncode == 0, f'failed: {{cmd[:3]}}'
    print(f'  ({{time.time() - t:.0f}} s)', flush=True)
'''

S_CELL2 = '''# 2. Episodes (every run labelled; errors counted and skipped), samples (the cut), checks, the label gallery.
for mode in ('p', 'o'):
    print(f'===== pref_episodes --mode {mode} =====', flush=True)
    run([sys.executable, CODE / 'pref_episodes.py', '--mode', mode, '--gen', *GENS, '--tasks', *TASK_FILES,
         '--exclude', CODE / 'heldout_eval.json', '--tokenizer-dir', TOK_DIR, '--copy-per-task', COPY_PER_TASK,
         '--out', OUT / f'ep_{mode}'])
    print(f'===== build_samples ({mode}) =====', flush=True)
    run([sys.executable, CODE / 'build_samples.py', '--stage-b', OUT / f'ep_{mode}', '--tokenizer-dir', TOK_DIR,
         '--out', OUT / f'samples_{mode}.pt', '--max-len', 16384, '--split-on-break'])
S = {mode: torch.load(OUT / f'samples_{mode}.pt', weights_only=False) for mode in ('p', 'o')}
key = lambda s: (s['episode_id'], s['segment'], s['label'], len(s['input_ids']), int(s['labels_mask'].sum()))
copy_p = sorted(key(s) for s in S['p'])
copy_o = sorted(key(s) for s in S['o'] if s['copy'])
assert copy_p == copy_o, 'P samples must equal O copy samples (only the labels may differ)'
assert not {{s['task'] for m in S for s in S[m]}} & set(HELDOUT), 'a held-out task reached the samples'
assert all(bool(s['labels_mask'][-1]) for m in S for s in S[m]), 'a sample does not end on a graded token (the cut)'
report = {{}}
for mode, ss in S.items():
    c = collections.Counter()
    for s in ss:
        k = ('copy' if s['copy'] else s['label']) + '_' + s['split']
        c[k + '_segments'] += 1
        c[k + '_tokens'] += len(s['input_ids'])
        c[k + '_graded'] += int(s['labels_mask'].sum())
        c[k + '_tasks'] = 0
    for k in list(c):
        if k.endswith('_tasks'):
            kind = k[:-6]
            c[k] = len({{s['task'] for s in ss if ('copy' if s['copy'] else s['label']) + '_' + s['split'] == kind}})
    report[mode] = dict(sorted(c.items()))
    print(f'samples_{{mode}}: ' + ' | '.join(f'{{k}} {{v:,}}' for k, v in sorted(c.items())), flush=True)
report['copy_samples_identical_p_o'] = True
report['copy_ids_hash'] = hashlib.md5(json.dumps(copy_p).encode()).hexdigest()
# label gallery: one real reply per reason (O) and per copy reason (P), different tasks where possible
gal, seen_tasks = {{}}, collections.Counter()
for line in open(OUT / 'ep_o' / 'requests_pref.jsonl'):
    r = json.loads(line)
    w = r.get('why')
    if not w or (w in gal and seen_tasks[w] >= 1):
        continue
    msg = (r.get('reply') or {{}}).get('message') or {{}}
    calls = [((c.get('function') or {{}}).get('name'), str((c.get('function') or {{}}).get('arguments'))[:300]) for c in msg.get('tool_calls') or []]
    last_tool = next((str(m.get('content'))[:400] for m in reversed(r['request']['messages']) if m.get('role') == 'tool'), '')
    gal[w] = {{'episode': r['episode_id'], 'thinking': str(msg.get('reasoning_content') or '')[:500],
              'text': str(msg.get('content') or '')[:200], 'calls': calls, 'previous tool output': last_tool}}
    seen_tasks[w] += 1
with open(OUT / 'gallery.md', 'w') as fh:
    for w in sorted(gal):
        g = gal[w]
        fh.write(f"## {{w}}\\n- episode: {{g['episode']}}\\n- previous tool output: {{g['previous tool output']!r}}\\n"
                 f"- thinking: {{g['thinking']!r}}\\n- text: {{g['text']!r}}\\n- calls: {{g['calls']}}\\n\\n")
report['gallery_reasons'] = sorted(gal)
(OUT / 'report.json').write_text(json.dumps(report, indent=1))
for p in ('ep_p', 'ep_o'):
    shutil.rmtree(OUT / p)  # the episodes are rebuilt from the collector output any time; keep the output small
print('\\nGALLERY reasons:', sorted(gal))
print(f"SAMPLES READY: samples_p.pt {{len(S['p'])}} segments, samples_o.pt {{len(S['o'])}} segments (copy part identical: "
      f"hash {{report['copy_ids_hash'][:10]}}) -> make this output a private dataset and share it with the two training accounts")
'''

T_CELL2 = '''# 2. Setup ({variant}): the training code (scripts/train/int4_lora.py, train_sft.py, train_pref.py), the inputs, resume.
import glob, json, os, shutil, subprocess, sys, time
from pathlib import Path
assert sys.version_info[:2] == (3, 12), 'Python 3.12 GPU notebook (a pinned copy of an old GPU notebook)'
VARIANT = {variant!r}  # 'p' = copy the best passes; 'o' = the same copy + the one-rule good / bad labels
WORKING_DIR = Path('/kaggle/working')
CODE = WORKING_DIR / 'train_code'
CODE.mkdir(parents=True, exist_ok=True)
for name, text in {code!r}.items():
    (CODE / name).write_text(text)
# The SAME for P and O (E1): only the labels differ. Token budgets = the GPU time (~60 tok/s training, ~180 tok/s forward).
CONFIG = dict(lr=2e-5, r=16, alpha=16, accum=2, warmup=5, epochs=1.0, clip=1.0, beta=5.0, sft_weight=1.0, seed=20261125,
              copy_tokens={copy_tokens}, kto_tokens={kto_tokens}, val_tokens={val_tokens}, evals=3,
              fastapi_rich_cap=100_000,  # tokens of the optional fastapi / rich slice, per part (copy, KTO): ~10%
              session_hours={session_hours})  # pause guard: Kaggle ends sessions at 12 h
_m = sorted(p for p in glob.glob('/kaggle/input/models/google/gemma-4/**/gemma-4-31b-it-qat-w4a16-ct/*', recursive=True)
            if Path(p, 'config.json').exists())
assert _m, 'attach the model google/gemma-4 -> gemma-4-31b-it-qat-w4a16-ct'
MODEL_PATH = Path(_m[-1])
_s = sorted(glob.glob(f'/kaggle/input/**/samples_{{VARIANT}}.pt', recursive=True))
assert len(_s) == 1, f'attach the samples output (a dataset holding pref_samples/samples_{{VARIANT}}.pt) once; found {{_s}}'
SAMPLES = Path(_s[0])
_fr = sorted(glob.glob(f'/kaggle/input/**/samples_{{VARIANT}}_fastapi_rich.pt', recursive=True))  # optional: the local slice
SAMPLE_ARGS = [str(SAMPLES)] + ([f"{{_fr[0]}}:{{CONFIG['fastapi_rich_cap']}}"] if _fr else [])
print('fastapi / rich slice:', _fr[0] if _fr else 'not attached', flush=True)
_rep = SAMPLES.parent / 'report.json'
print('model', MODEL_PATH, '| samples', SAMPLES, '| samples report:', json.loads(_rep.read_text()).get(VARIANT) if _rep.exists() else '-')
TRAIN_OUT = WORKING_DIR / f'adapter_{{VARIANT}}'
_prev = sorted(glob.glob(f'/kaggle/input/**/adapter_{{VARIANT}}/last/trainer_state.pt', recursive=True))
if _prev and not (TRAIN_OUT / 'last' / 'trainer_state.pt').exists():  # a second session continues the first
    assert len(_prev) == 1, f'attach ONE earlier session output; found {{_prev}}'
    shutil.copytree(Path(_prev[0]).parent.parent, TRAIN_OUT)
    print('RESUMING from', Path(_prev[0]).parent.parent)
else:
    print('fresh LoRA (B = 0: step 0 = the base model)')


def stream(cmd, env=None):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    noise = ('Warning', 'warn(', 'Loading weights', 'Compressing', 'it/s]')
    lines = []
    for line in p.stdout:
        lines.append(line)
        if line.strip() and not any(n in line for n in noise):
            print(line, end='', flush=True)
    return p.wait(), lines
'''

T_CELL3 = r'''# 3. TRAIN: one line per step (loss = KTO + copy, r good / bad, lr, grad norm, tokens/s, memory, ETA); validation at the
#    start, 3 times mid-run and at the end; a checkpoint every 10 steps; pauses at session_hours. A crash resumes (2 tries).
cmd = [sys.executable, '-u', str(CODE / 'train_pref.py'), '--model', str(MODEL_PATH), '--samples', *SAMPLE_ARGS,
       '--out', str(TRAIN_OUT), '--base-name', 'google/gemma-4-31b-it-qat-w4a16-ct', '--gpus-per-rank', '4',
       '--epochs', str(CONFIG['epochs']), '--lr', str(CONFIG['lr']), '--warmup', str(CONFIG['warmup']), '--r', str(CONFIG['r']),
       '--alpha', str(CONFIG['alpha']), '--accum', str(CONFIG['accum']), '--clip', str(CONFIG['clip']), '--beta', str(CONFIG['beta']),
       '--sft-weight', str(CONFIG['sft_weight']), '--seed', str(CONFIG['seed']), '--copy-tokens', str(CONFIG['copy_tokens']),
       '--train-tokens', str(CONFIG['kto_tokens']), '--val-tokens', str(CONFIG['val_tokens']), '--evals', str(CONFIG['evals']),
       '--session-hours', str(CONFIG['session_hours']), '--max-len', '16384']
env = dict(os.environ, PYTORCH_CUDA_ALLOC_CONF='expandable_segments:True', OMP_NUM_THREADS='4')
T0 = time.time()
for attempt in range(3):
    code, lines = stream(cmd, env=env)
    print('exit code', code, flush=True)
    if code == 0 or not (TRAIN_OUT / 'last' / 'trainer_state.pt').exists():
        break
    print(f'=== training stopped with an error: resuming from the last checkpoint (retry {attempt + 1}/2) ===', flush=True)
PAUSED = any(l.startswith('PAUSED') for l in lines)
'''

T_CELL4 = r'''# 4. Report + the adapter in the scorer's format (adapters/<name>/adapter_config.json + adapter_model.safetensors).
hist = json.loads((TRAIN_OUT / 'history.json').read_text()) if (TRAIN_OUT / 'history.json').exists() else []
tr = [h for h in hist if h['type'] == 'train']
va = [h for h in hist if h['type'] == 'val']
report = {'variant': VARIANT, 'status': 'PAUSED' if PAUSED else ('DONE' if (TRAIN_OUT / 'final').exists() else 'FAILED'),
          'config': CONFIG, 'steps_done': tr[-1]['step'] if tr else 0, 'tokens_seen': sum(h['tokens'] for h in tr),
          'validation': [(h['tag'], h['step'], h['margin'], h['kto'], h['nll_good']) for h in va],
          'peak_mem_gib': max((h['mem_gib'] for h in tr), default=0), 'hours': round((time.time() - T0) / 3600, 2)}
(WORKING_DIR / 'report.json').write_text(json.dumps(report, indent=1))
for tag in ('best', 'final'):
    if (TRAIN_OUT / tag / 'adapter_model.safetensors').exists():
        cfg = json.loads((TRAIN_OUT / tag / 'adapter_config.json').read_text())
        assert cfg['r'] <= 128, 'the scorer serves rank <= 128'
        shutil.make_archive(str(WORKING_DIR / f'adapter_{VARIANT}_{tag}'), 'zip', TRAIN_OUT / tag)
        print(f"{tag}: r {cfg['r']} alpha {cfg['lora_alpha']} | {(TRAIN_OUT / tag / 'adapter_model.safetensors').stat().st_size / 1e6:.0f} MB")
print(json.dumps(report, indent=1))
print(f"TRAINING {report['status']}: adapter_{VARIANT}/best is the one the final test uses")
'''


def main():
    s_code = {n: (T / n).read_text() for n in ("pref_episodes.py", "selfdistill_episodes.py", "build_samples.py")}
    s_code["render_traces.py"] = (ROOT / "scripts/render_traces.py").read_text()
    out = ROOT / "kaggle/cells_pref_samples"
    out.mkdir(parents=True, exist_ok=True)
    (out / "cell1.py").write_text(S_CELL1.format(code=s_code, heldout=HELDOUT))
    (out / "cell2.py").write_text(S_CELL2.replace("{{", "{").replace("}}", "}"))  # written as is, not a template
    print("wrote", out.relative_to(ROOT), sorted(p.name for p in out.iterdir()))
    t_code = {n: (T / n).read_text() for n in ("int4_lora.py", "train_sft.py", "train_pref.py")}
    budgets = dict(copy_tokens=1_000_000, val_tokens=80_000, session_hours=10.0)
    for v in ("p", "o"):
        out = ROOT / f"kaggle/cells_train_{v}"
        out.mkdir(parents=True, exist_ok=True)
        (out / "cell1.py").write_text((ROOT / "kaggle/cells_ood45_31b/cell1.py").read_text())
        (out / "cell2_setup.py").write_text(T_CELL2.format(variant=v, code=t_code, kto_tokens=600_000, **budgets))
        (out / "cell3_train.py").write_text(T_CELL3)
        (out / "cell4_report.py").write_text(T_CELL4)
        print("wrote", out.relative_to(ROOT), sorted(p.name for p in out.iterdir()))


if __name__ == "__main__":
    main()
