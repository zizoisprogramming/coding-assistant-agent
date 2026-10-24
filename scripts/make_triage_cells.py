"""Writes kaggle/cells_triage/: failure triage over every generation run (CPU, free, Settings -> Internet ON).

    python3 scripts/make_triage_cells.py

Runs scripts/triage.py `extract` on each attached generation output (requests/requests.jsonl +
results/gen_per_task.jsonl) and on dataset versions the input panel cannot pick (kagglehub). Output:
/kaggle/working/triage/runs.jsonl = per-run counts, tool names and file paths, NO conversation text (small; download
it and run `triage.py report` locally with the gold patches). Prints a first report (files unknown: no gold here).
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "kaggle/cells_triage"

CELL1 = '''# 1. Failure triage (scripts/triage.py, written to /kaggle/working/code). CPU; Internet ON only for the download list.
import glob, hashlib, json, subprocess, sys, time
from pathlib import Path
CODE = Path('/kaggle/working/code')
CODE.mkdir(parents=True, exist_ok=True)
(CODE / 'triage.py').write_text({triage!r})
# dataset VERSIONS the input panel cannot pick: gen-extra-all version 1 = the extra run (55 ours + 44 OOD-45)
DOWNLOAD = ['ziadsamer/gen-extra-all/versions/1']
roots = ['/kaggle/input']
for ref in DOWNLOAD:
    import kagglehub
    roots.append(kagglehub.dataset_download(ref))
    print('downloaded', ref, '->', roots[-1], flush=True)
GENS, seen = [], set()
for root in roots:
    for p in sorted(glob.glob(f'{{root}}/**/results/gen_per_task.jsonl', recursive=True)):
        g = Path(p).parent.parent
        if not (g / 'requests/requests.jsonl').exists():
            print('skip (no request log):', g)
            continue
        h = hashlib.sha1(Path(p).read_bytes()).hexdigest()
        if h in seen:
            print('skip (same run attached twice):', g)
            continue
        seen.add(h)
        GENS.append(g)
        n = sum(1 for _ in open(p))
        print(f'generation output {{len(GENS)}}: {{g}} | {{n}} runs | request log {{(g / "requests/requests.jsonl").stat().st_size / 1e9:.2f}} GB', flush=True)
assert GENS, 'attach the generation outputs (each has results/gen_per_task.jsonl and requests/requests.jsonl)'
'''

CELL2 = '''# 2. Extract per-run features (one line per output as it finishes), then a first report.
OUTD = Path('/kaggle/working/triage')
OUTD.mkdir(parents=True, exist_ok=True)
t0 = time.time()
parts = []
for i, g in enumerate(GENS):
    part = OUTD / f'runs_{{i}}.jsonl'
    r = subprocess.run([sys.executable, str(CODE / 'triage.py'), 'extract', str(g), '--out', str(part)], capture_output=True, text=True)
    print(r.stderr.strip()[-2000:], f'({{time.time() - t0:.0f}}s)', flush=True)
    assert r.returncode == 0, 'extract failed: see the lines above'
    parts.append(part)
with open(OUTD / 'runs.jsonl', 'w') as f:
    for i, part in enumerate(parts):
        for line in open(part):
            row = json.loads(line)
            row['src'] = f'{{i}}:{{GENS[i]}}'
            f.write(json.dumps(row) + '\\n')
        part.unlink()
print(f'==> wrote {{OUTD / "runs.jsonl"}}: {{sum(1 for _ in open(OUTD / "runs.jsonl"))}} runs, '
      f'{{(OUTD / "runs.jsonl").stat().st_size / 1e6:.1f}} MB\\n', flush=True)
print(subprocess.run([sys.executable, str(CODE / 'triage.py'), 'report', str(OUTD / 'runs.jsonl')],
                     capture_output=True, text=True).stdout)
'''


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cell1_setup.py").write_text(CELL1.format(triage=(ROOT / "scripts/triage.py").read_text()))
    (OUT / "cell2_extract.py").write_text(CELL2.format())
    print("wrote", OUT.relative_to(ROOT), sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
