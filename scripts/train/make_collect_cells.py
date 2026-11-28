"""Writes kaggle/cells_collect/: the COLLECTOR notebook (CPU, Internet ON, no GPU quota).

    python3 scripts/train/make_collect_cells.py

Why (user 2026-11-28: Kaggle's Add Input cannot pick an older notebook version): the training notebooks need the full run
logs (requests/requests.jsonl, results/gen_per_task.jsonl, results/gen/patches/*.diff) of 10 sk_a2 generation runs, and 7 of
them live in OLDER versions of their notebooks. This notebook downloads exactly those files with the Kaggle CLI
(OWNER/SLUG/VERSION, as we fetch them locally) into /kaggle/working/runs/<run>/, checks every download against the md5 of
our local copy of that run's gen_per_task.jsonl + phases.json (a wrong version stops the notebook), and writes
runs/manifest.json. Its output (latest version) is then attached to the training notebooks as ONE input.

The Kaggle token comes from a Kaggle SECRET named KAGGLE_API_TOKEN (Add-ons -> Secrets; the same token as ~/.kaggle/
access_token); it is never printed. Runs end by themselves (Save Version -> Save & Run All).
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle/cells_collect"
G = "ziad23samer/fork-of-fork-of-generation-all-shards-gpu"
# run label -> notebook ref (version pinned where it is not the latest; probed 2026-11-28 by matching phases.json md5)
SOURCES = {
    "r165_A": f"{G}/119", "r165_B": "engziadsamer/arms-again/30",
    "r166_D": f"{G}/121", "r166_A": f"{G}/122", "r166_C": "engziadsamer/arms-again/31",
    "r166_B": "ziadsamer/fork-of-generation-all-shards-gpu",  # latest version
    "r167_A": f"{G}/123", "r167_B": "engziadsamer/arms-again/32",
    "r168_A": f"{G}/125", "r168_B": "fatmazenhom/generation-shard-4-gpu",  # latest version
}


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


def expected():
    out = {}
    for label in SOURCES:
        d = sorted(ROOT.glob(f"data/results/2026-11-2*_skill_{label}/results"))
        assert len(d) == 1, f"one local copy of {label}: {d}"
        rows = (d[0] / "gen_per_task.jsonl").read_text().splitlines()
        out[label] = {"gen_md5": md5(d[0] / "gen_per_task.jsonl"), "phases_md5": md5(d[0] / "phases.json"), "rows": len(rows)}
    return out


CELL1 = '''# 1. COLLECTOR setup (scripts/train/make_collect_cells.py): CPU, Internet ON, the Kaggle token from a Kaggle secret.
import hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path
from kaggle_secrets import UserSecretsClient
try:
    os.environ['KAGGLE_API_TOKEN'] = UserSecretsClient().get_secret('KAGGLE_API_TOKEN')  # never printed
except Exception as e:
    raise SystemExit('Add-ons -> Secrets: add a secret named KAGGLE_API_TOKEN (your Kaggle API token) and tick it for this '
                     f'notebook; Settings -> Internet ON. ({{type(e).__name__}})')
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '--upgrade', 'kaggle', 'six'], check=True)
r = subprocess.run(['kaggle', '--version'], capture_output=True, text=True)
print('kaggle CLI:', (r.stdout or r.stderr).strip())
WORK = Path('/kaggle/working/runs')
WORK.mkdir(parents=True, exist_ok=True)
SOURCES = {sources!r}
EXPECTED = {expected!r}  # md5 of our local copies (the run each version must hold)
PATTERN = r'.*(gen_per_task\\.jsonl|phases\\.json|requests\\.jsonl|\\.diff)$'
print(f'{{len(SOURCES)}} runs to collect, {{sum(e["rows"] for e in EXPECTED.values())}} result rows expected')
'''

CELL2 = '''# 2. Download each run (sequential: Kaggle rate-limits parallel calls), verify, report. Ends by itself.
def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()

def one(label, ref):
    dest = WORK / label
    for attempt in range(1, 4):
        if dest.exists():
            shutil.rmtree(dest)  # a fixed path under /kaggle/working/runs: a clean retry
        dest.mkdir(parents=True)
        t = time.time()
        r = subprocess.run(['kaggle', 'kernels', 'output', ref, '-p', str(dest), '--file-pattern', PATTERN],
                           capture_output=True, text=True)
        gen = sorted(dest.glob('**/results/gen_per_task.jsonl'))
        ph = sorted(dest.glob('**/results/phases.json'))
        req = sorted(dest.glob('**/requests/requests.jsonl'))
        diffs = list(dest.glob('**/results/gen/patches/*.diff'))
        exp = EXPECTED[label]
        problems = []
        if len(gen) != 1 or md5(gen[0]) != exp['gen_md5']:
            problems.append('gen_per_task.jsonl missing or not the expected run')
        if len(ph) != 1 or md5(ph[0]) != exp['phases_md5']:
            problems.append('phases.json missing or not the expected run')
        if len(req) != 1 or req[0].stat().st_size == 0:
            problems.append('requests.jsonl missing or empty')
        if not problems:
            jobs, lines = set(), 0
            with open(req[0], errors='replace') as fh:
                for line in fh:
                    lines += 1
                    try:
                        jobs.add(json.loads(line).get('job'))
                    except Exception:
                        pass
            rows = [json.loads(l) for l in gen[0].read_text().splitlines()]
            want = {{f"{{x['instance_id']}}#a{{x['attempt']}}" for x in rows}}
            covered = len(want & jobs)
            info = {{'ref': ref, 'rows': len(rows), 'requests': lines, 'runs_with_requests': covered, 'patches': len(diffs),
                    'requests_mb': round(req[0].stat().st_size / 1e6, 1), 'seconds': round(time.time() - t)}}
            print(f"  {{label:7}} OK  {{ref}} | rows {{len(rows)}} | runs with requests {{covered}}/{{len(want)}} | "
                  f"requests {{lines}} ({{info['requests_mb']}} MB) | patches {{len(diffs)}} | {{info['seconds']}} s", flush=True)
            if covered < 0.95 * len(want):
                print(f"  {{label:7}} WARNING: only {{covered}} of {{len(want)}} runs have request logs", flush=True)
            return info
        print(f"  {{label:7}} attempt {{attempt}} FAILED {{ref}}: {{problems}} | CLI: {{(r.stderr or r.stdout)[-300:]}}", flush=True)
        time.sleep(30 * attempt)
    raise SystemExit(f'{{label}} ({{ref}}): could not collect the expected run -> send me this output')

MANIFEST = {{}}
for k, (label, ref) in enumerate(SOURCES.items(), 1):
    print(f'[{{k}}/{{len(SOURCES)}}] {{label}} <- {{ref}}', flush=True)
    MANIFEST[label] = one(label, ref)
(WORK / 'manifest.json').write_text(json.dumps(MANIFEST, indent=1))
total_mb = sum(p.stat().st_size for p in WORK.rglob('*') if p.is_file()) / 1e6
print(f"\\nCOLLECTED {{len(MANIFEST)}}/{{len(SOURCES)}} runs | rows {{sum(m['rows'] for m in MANIFEST.values())}} | "
      f"runs with requests {{sum(m['runs_with_requests'] for m in MANIFEST.values())}} | "
      f"patches {{sum(m['patches'] for m in MANIFEST.values())}} | {{total_mb:.0f}} MB in /kaggle/working/runs")
'''


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cell1.py").write_text(CELL1.format(sources=SOURCES, expected=expected()))
    (OUT / "cell2.py").write_text(CELL2.format())
    print("wrote", OUT.relative_to(ROOT), sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
