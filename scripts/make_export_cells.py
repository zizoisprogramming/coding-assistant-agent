"""Writes kaggle/cells_export_failed/: compact copy of every failed generation run (CPU, free).

    python3 scripts/make_export_cells.py

Runs scripts/export_failed.py on each attached generation output -> /kaggle/working/failed/failed_<k>.jsonl.gz (~20 KB
per failed run). Same inputs and the same two passes as kaggle/cells_triage: a kagglehub version download mounts AT THE
SAME PATH as the attached latest version, so the combined run (latest gen-extra-all / generation-all-shards-gpu) goes
in a second session with DOWNLOAD = [].
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "kaggle/cells_export_failed"

CELL1 = '''# 1. Export the FAILED runs (scripts/export_failed.py, written to /kaggle/working/code). CPU; Internet ON only for the
#    download list. Pass 1: full + retry outputs attached, DOWNLOAD = gen-extra-all v1 (the extra run).
#    Pass 2 (fresh session): only the combined run attached, DOWNLOAD = [].
import glob, hashlib, json, subprocess, sys, time
from pathlib import Path
CODE = Path('/kaggle/working/code')
CODE.mkdir(parents=True, exist_ok=True)
(CODE / 'export_failed.py').write_text({code!r})
DOWNLOAD = ['ziadsamer/gen-extra-all/versions/1']
roots = ['/kaggle/input']
for ref in DOWNLOAD:  # Kaggle allows this only in an INTERACTIVE session (a committed run refuses a new version)
    try:
        import kagglehub
        roots.append(kagglehub.dataset_download(ref))
        print('downloaded', ref, '->', roots[-1], flush=True)
    except Exception as e:  # noqa: BLE001
        print(f'WARNING: could not download {{ref}} ({{str(e)[:160]}}): continuing without it', flush=True)
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
        rows = [json.loads(l) for l in open(p)]
        print(f'generation output {{len(GENS)}}: {{g}} | {{len(rows)}} runs, {{sum(not r["resolved"] for r in rows)}} failed', flush=True)
assert GENS, 'attach the generation outputs (each has results/gen_per_task.jsonl and requests/requests.jsonl)'
'''

CELL2 = '''# 2. Export (one line per output as it finishes). Download /kaggle/working/failed/ (a few MB per output).
OUTD = Path('/kaggle/working/failed')
OUTD.mkdir(parents=True, exist_ok=True)
t0 = time.time()
for i, g in enumerate(GENS):
    out = OUTD / f'failed_{{g.name}}_{{i}}.jsonl.gz'
    r = subprocess.run([sys.executable, str(CODE / 'export_failed.py'), str(g), '--out', str(out)], capture_output=True, text=True)
    print(r.stderr.strip()[-1500:], f'-> {{out.name}} {{out.stat().st_size / 1e6 if out.exists() else 0:.1f}} MB ({{time.time() - t0:.0f}}s)', flush=True)
    assert r.returncode == 0, 'export failed: see the lines above'
print('==> done:', sorted(p.name for p in OUTD.iterdir()))
'''


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cell1_setup.py").write_text(CELL1.format(code=(ROOT / "scripts/export_failed.py").read_text()))
    (OUT / "cell2_export.py").write_text(CELL2.format())
    print("wrote", OUT.relative_to(ROOT), sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
