"""Writes kaggle/cells_samples/: training samples for self-distillation from generation outputs (CPU notebook, free).

    python3 scripts/train/make_samples_cells.py

Per attached generation output (a folder with results/gen_per_task.jsonl + requests/requests.jsonl): episodes,
the cut after the first submit, the quality filter (scripts/train/selfdistill_episodes.py), then token samples
(scripts/train/build_samples.py --split-on-break). One output folder per source: selfdistill/<source>/ with
metrics.jsonl (every attempt), status.jsonl + requests_selfdistill.jsonl (kept episodes) and samples.pt. Run it on the
account that owns the generation output (attaching another account's notebook output hung, 2026-10-21); run again
on a later output (the retry) and merge the samples at training time.

Inputs: the generation notebook output(s), the task set (rebench-final-cp312), the model google/gemma-4 ->
gemma-4-31b-it-qat-w4a16-ct (tokenizer + chat template only). CPU, internet off.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle/cells_samples"

CELL1 = '''# 1. Self-distillation samples (scripts/train/make_samples_cells.py): the tested repo code, written to /kaggle/working/code.
import collections, glob, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

CODE = Path('/kaggle/working/code')
CODE.mkdir(parents=True, exist_ok=True)
for name, text in {code!r}.items():
    (CODE / name).write_text(text)
import jinja2, tokenizers, torch  # noqa: F401  (the Kaggle image has them)
print('code:', sorted(p.name for p in CODE.iterdir()), '| python', sys.version.split()[0], '| torch', torch.__version__)
'''

CELL2 = r'''# 2. Inputs: every generation output, the task set, the tokenizer.
GENS = sorted({Path(p).parent.parent for p in glob.glob('/kaggle/input/**/results/gen_per_task.jsonl', recursive=True)})
assert GENS, 'attach the generation notebook output (it has results/gen_per_task.jsonl and requests/requests.jsonl)'
for g in GENS:
    req = g / 'requests' / 'requests.jsonl'
    print(f"generation output {g}: {sum(1 for _ in open(g / 'results' / 'gen_per_task.jsonl'))} attempts | request log "
          + (f'{req.stat().st_size / 1e6:.0f} MB' if req.exists() else 'MISSING'))
# Reference patches and labels: a generation output that ran several task sets (cells_gen_extra: our extra tasks +
# OOD-45) ships its own results/tasks_used.jsonl; the others need the task set they ran (rebench-final-cp312).
_sets = sorted(Path(p).parent for p in glob.glob('/kaggle/input/**/rebench/verify_gate.json', recursive=True))
TASKS_OF = {g: g / 'results' / 'tasks_used.jsonl' for g in GENS if (g / 'results' / 'tasks_used.jsonl').exists()}
if len(TASKS_OF) < len(GENS):
    assert len(_sets) == 1, f'attach exactly one task set (rebench-final-cp312) for {sorted(set(GENS) - set(TASKS_OF))}; found {_sets}'
    TASKS_OF.update({g: _sets[0] / 'tasks.jsonl' for g in GENS if g not in TASKS_OF})
_tok = sorted(p for p in glob.glob('/kaggle/input/models/google/gemma-4/**/gemma-4-31b-it-qat-w4a16-ct/*', recursive=True)
              if Path(p, 'tokenizer.json').exists() and Path(p, 'chat_template.jinja').exists())
assert _tok, 'attach the model google/gemma-4 -> gemma-4-31b-it-qat-w4a16-ct (its tokenizer and chat template are used)'
TOK_DIR = Path(_tok[-1])
# Re-graded rows (kaggle/cells_regrade_public output): applied to the generation output they came from.
OVERRIDE = sorted(glob.glob('/kaggle/input/**/results/regrade/gen_per_task.jsonl', recursive=True))
assert len(OVERRIDE) <= 1, f'attach at most one re-grade output; found {OVERRIDE}'
print('tasks per output:', {str(g): str(t) for g, t in TASKS_OF.items()}, '| tokenizer:', TOK_DIR, '| re-grade:', OVERRIDE)
'''

CELL3 = r'''# 3. Episodes -> cut -> filter -> samples, per generation output. Prints one line per resolved attempt (verdict and
#    metrics), the verdict counts, how many a stricter filter would keep, and the samples summary.
WORK = Path('/kaggle/working/selfdistill')


def run(cmd):
    print('$', ' '.join(str(c) for c in cmd[:4]), '...', flush=True)
    p = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    print(p.stdout[-20000:], p.stderr[-3000:] if p.returncode else '', flush=True)
    assert p.returncode == 0, f'failed: exit {p.returncode}'
    return p.stdout


for g in GENS:
    name = re.sub(r'[^A-Za-z0-9_-]+', '_', str(g.relative_to('/kaggle/input')))[-60:]
    out = WORK / name
    t0 = time.time()
    strict = run([sys.executable, CODE / 'selfdistill_episodes.py', '--gen', g, '--tasks', TASKS_OF[g], '--out', f'/tmp/strict_{name}',
                  '--max-fail-streak', 2, '--max-repeats', 1, '--max-rereads', 1] + (['--override', OVERRIDE[0]] if OVERRIDE else []))
    strict = next(l for l in strict.splitlines() if l.startswith('KEPT'))  # the KEPT line (the DOUBT line comes after it)
    print('STRICT FILTER (2 failed in a row, 1 repeat, 1 reread) would keep:', strict, flush=True)
    run([sys.executable, CODE / 'selfdistill_episodes.py', '--gen', g, '--tasks', TASKS_OF[g], '--out', out]
        + (['--override', OVERRIDE[0]] if OVERRIDE else []))
    run([sys.executable, CODE / 'build_samples.py', '--stage-b', out, '--tokenizer-dir', TOK_DIR,
         '--out', out / 'samples.pt', '--split-on-break', '--max-len', 32768])
    print(f'==> {name}: {(time.time() - t0) / 60:.1f} min, files', sorted(p.name for p in out.iterdir()), flush=True)
'''


def main():
    code = {n: (ROOT / "scripts/train" / n).read_text() for n in ("selfdistill_episodes.py", "build_samples.py")}
    code["render_traces.py"] = (ROOT / "scripts/render_traces.py").read_text()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cell1.py").write_text(CELL1.format(code=code))
    (OUT / "cell2.py").write_text(CELL2)
    (OUT / "cell3_samples.py").write_text(CELL3)
    print("wrote", OUT.relative_to(ROOT), sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
