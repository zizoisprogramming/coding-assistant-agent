"""Writes kaggle/cells_rebench_cp312/: the final task set re-targeted to Python 3.12 (CPU notebook, free).

    .venv/bin/python scripts/datasets/make_rebench_cp312_cells.py

Why (2026-10-21): generation needs vLLM 0.19.1 from the competition wheelhouse = Python 3.12 + torch 2.10 (the
Kaggle image of notebooks created before ~Oct 20, kept by "Pin to original environment"); new notebooks get Python
3.13 + torch 2.11, where it cannot run. Kaggle has no Docker, so the subprocess sandbox runs the tests with the
notebook's own Python: in the 3.12 GPU notebook the tasks need 3.12 wheels. Our set (348 tasks, verified offline on
3.13) has 176 wheels built only for 3.13 (141 downloadable for 3.12, 35 we built from source); the other 1,838 are
pure Python or abi3 and work on both. Same thing the OOD-45 author did (a cp312 wheel set for 3.12 GPU runs).

Run on a COPY of a CPU notebook created on or before Oct 13 (Python 3.12), Environment -> Pin to original
environment, accelerator None, INTERNET ON (downloads the 3.12 wheels). Inputs: the competition, the wheelhouse,
rodrigospalma/ood45-bugfix-split, and the final task set (rebench-final). Cells:
  1 install the wheelhouse            2 inputs, Python 3.12 check, the task set
  3 CONVERT every 3.13-only wheel to its 3.12 build (same version: download, else build from the sdist); copy the
    snapshots and the portable wheels; manifest x86_64-cp312
  4 RE-GATE every task on 3.12 (verification notebook's gate: offline fail-fast hook in the sandbox; gold PASS, empty
    FAIL)                             5 finish (tasks.jsonl, README, prune) -> output = dataset rebench-final-cp312
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/datasets"))
import make_rebench_verify_cells as V  # noqa: E402

OUT_DIR = ROOT / "kaggle/cells_rebench_cp312"

CELL2 = r'''# 2. RE-TARGET TO PYTHON 3.12: inputs and the task set (scripts/datasets/make_rebench_cp312_cells.py).
#    CPU, INTERNET ON, a copy of an old notebook pinned to its original environment (Python 3.12).
import collections, json, re, time, urllib.request

assert sys.version_info[:2] == (3, 12), (f'this notebook runs Python {sys.version.split()[0]}: it must be 3.12 (Copy & Edit '
                                         'a CPU notebook from Oct 13 or earlier, Environment -> Pin to original environment)')
T_START = time.time()
DEADLINE_H = 10.5
WORKING_DIR = Path('/kaggle/working')
OUT = WORKING_DIR / 'rebench'
WHEEL_SET = f'{__import__("platform").machine()}-cp{sys.version_info.major}{sys.version_info.minor}'  # x86_64-cp312
HOUSE = OUT / 'wheels' / 'house'
for p in (OUT / 'snapshots', HOUSE, OUT / 'wheels' / WHEEL_SET, OUT / 'wheels' / 'host'):
    p.mkdir(parents=True, exist_ok=True)
try:
    urllib.request.urlopen('https://pypi.org/simple/pip/', timeout=20)
except Exception as e:
    raise RuntimeError(f'no internet ({e!r}): turn Settings -> Internet on (3.12 wheels are downloaded), then re-run')


def _first(*cands, pattern=None):
    for c in cands:
        if Path(c).exists():
            return Path(c)
    hits = sorted(glob.glob(pattern, recursive=True)) if pattern else []
    assert hits, f'none of {cands} exists: attach it as a notebook input'
    return Path(hits[0])


DATA_DIR = _first('/kaggle/input/competitions/gemma-4-developer-agent', '/kaggle/input/gemma-4-developer-agent')
OOD_DIR = _first('/kaggle/input/datasets/rodrigospalma/ood45-bugfix-split', '/kaggle/input/ood45-bugfix-split',
                 pattern='/kaggle/input/**/tools/ood45_harness.py')
OOD_DIR = OOD_DIR.parent.parent if OOD_DIR.name == 'ood45_harness.py' else OOD_DIR
_sets = sorted(Path(p).parent for p in glob.glob('/kaggle/input/**/rebench/verify_gate.json', recursive=True))
assert len(_sets) == 1, f'attach exactly one final task set (rebench-final); found {_sets}'
SRC = _sets[0]
SRC_SET = 'x86_64-cp313'
SRC_MANIFEST = json.loads((SRC / 'wheels' / SRC_SET / 'manifest.json').read_text())
ROWS = {}
for l in open(SRC / 'tasks.jsonl'):
    r = json.loads(l)
    ROWS[r['instance_id']] = {**r, 'gate_cp313': r.pop('gate'), 'requirements': ''}
print(f'Python {sys.version.split()[0]} | task set {SRC}: {len(ROWS)} tasks, {len({w for ws in SRC_MANIFEST.values() for w in ws})} '
      f'distinct wheels | competition {DATA_DIR} | OOD-45 tools {OOD_DIR}')
'''

CELL3 = r'''# 3. CONVERT: every wheel built only for Python 3.13 -> the same version built for 3.12 (download, else build from the
#    sdist), 8 at a time; portable wheels (pure Python / abi3) and the snapshots are copied as they are. One line per
#    converted wheel; resumes (rebench/convert.jsonl).
import concurrent.futures as cf, shutil, threading
from packaging.utils import parse_wheel_filename


def sh(cmd, cwd=None, timeout=600):
    try:
        r = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr)
    except subprocess.TimeoutExpired:
        return 124, f'timed out after {timeout}s'


def only_313(w):
    return '-cp313-cp313-' in w


LOG = OUT / 'convert.jsonl'
CONV = {json.loads(l)['wheel']: json.loads(l) for l in open(LOG)} if LOG.exists() else {}
_lock, BUILD_SLOTS = threading.Lock(), threading.Semaphore(4)


def convert(w):
    if w in CONV:
        return CONV[w]
    name, ver = parse_wheel_filename(w)[:2]
    spec = f'{name}=={ver}'
    tmp = Path('/tmp/cp312') / w
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    pip = f'{sys.executable} -m pip'
    code, log = sh(f'{pip} download -q --no-deps --only-binary=:all: "{spec}" -d {tmp}')
    how = 'download'
    if code != 0 or not list(tmp.glob('*.whl')):
        with BUILD_SLOTS:
            code, log = sh(f'{pip} wheel -q --no-deps --no-binary={name} "{spec}" -w {tmp}', timeout=900)
        how = 'built'
    got = list(tmp.glob('*.whl'))
    res = {'wheel': w, 'how': how if code == 0 and got else 'FAILED', 'new': got[0].name if code == 0 and got else None,
           'log': '' if code == 0 and got else log.strip()[-300:]}
    if res['new'] and not (HOUSE / res['new']).exists():
        shutil.move(str(got[0]), HOUSE / res['new'])
    shutil.rmtree(tmp, ignore_errors=True)
    with _lock:
        CONV[w] = res
        with open(LOG, 'a') as fh:
            fh.write(json.dumps(res) + '\n')
    return res


todo = sorted({w for ws in SRC_MANIFEST.values() for w in ws if only_313(w)})
print(f'{len(todo)} wheels to convert to {WHEEL_SET} ({len(CONV)} done earlier)', flush=True)
t0 = time.time()
with cf.ThreadPoolExecutor(8) as ex:
    for k, (w, res) in enumerate(zip(todo, ex.map(convert, todo)), 1):
        print(f"[conv {k:3}/{len(todo)}] {w[:60]:60} {res['how']:8} {res['new'] or res['log'][-120:]}", flush=True)
print(f'converted in {(time.time() - t0) / 60:.1f} min:', dict(collections.Counter(c['how'] for c in CONV.values())))

# Assemble: snapshots + portable wheels copied, converted wheels mapped, manifest for this wheel set.
TASKS, LEVEL, built, missing = [], {}, {}, collections.Counter()
for k, iid in enumerate(sorted(ROWS), 1):
    shutil.copy2(SRC / 'snapshots' / f'{iid}.tgz', OUT / 'snapshots' / f'{iid}.tgz')
    names = []
    for w in SRC_MANIFEST[iid]:
        if only_313(w):
            if CONV[w]['new']:
                names.append(CONV[w]['new'])
            else:
                missing[iid] += 1
            continue
        if not (HOUSE / w).exists():
            shutil.copy2(SRC / 'wheels' / 'house' / w, HOUSE / w)
        names.append(w)
    built[iid] = {'snapshot': True, 'pins_failed': {}, 'wheels': sorted(set(names))}
    TASKS.append((iid, ROWS[iid]['level']))
    LEVEL[iid] = ROWS[iid]['level']
    if k % 50 == 0 or k == len(ROWS):
        print(f'[copy {k:3}/{len(ROWS)}] {iid}', flush=True)
(OUT / 'wheels' / WHEEL_SET / 'manifest.json').write_text(json.dumps({i: built[i]['wheels'] for i in sorted(built)}, indent=1))
for p in (SRC / 'wheels' / 'host').glob('*.whl'):  # pytest plugins: pure Python, same files
    shutil.copy2(p, OUT / 'wheels' / 'host' / p.name)
host_whls = sorted(str(p) for p in (OUT / 'wheels' / 'host').glob('*.whl'))
r = subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '--no-index', '--no-deps', *host_whls], capture_output=True, text=True)
print('host plugins:', [Path(p).name for p in host_whls], '-> exit', r.returncode, r.stderr[-200:])
SEL = {i: {'source': 'final'} for i in ROWS}  # the gate cell: gold once per task (all passed 3x+1 on 3.13)
SNAP_BAD = {}  # snapshots unchanged (checked by the verification notebook)
CAP = max(collections.Counter(r['repo'] for r in ROWS.values()).values())
print(f"assembled {len(ROWS)} tasks | tasks missing a converted wheel: {len(missing)} {dict(missing.most_common(5))} | "
      f"house {len(list(HOUSE.glob('*.whl')))} wheels {sum(p.stat().st_size for p in HOUSE.glob('*.whl')) / 1e9:.2f} GB")
'''


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "cell1.py").write_text((ROOT / "kaggle/cells_rebench_pilot/cell1.py").read_text())
    (OUT_DIR / "cell2.py").write_text(CELL2)
    (OUT_DIR / "cell3_convert.py").write_text(CELL3)
    gate = V.gate_cell().replace("# 5. RE-GATE OFFLINE, 3 tasks at a time", "# 5. RE-GATE ON PYTHON 3.12, 3 tasks at a time", 1)
    (OUT_DIR / "cell4_gate.py").write_text(gate.replace("# 5. RE-GATE", "# 4. RE-GATE", 1))
    fin = V.CELL6.replace("# 6. FINISH", "# 5. FINISH", 1)
    old = "Every task passed, offline (internet off), the harness's own `verify_task`"
    assert fin.count(old) == 1
    fin = fin.replace(old, "Every task passed on 3.13 offline (internet off) and again on this Python with network blocked "
                           "inside the sandbox, the harness's own `verify_task`")
    (OUT_DIR / "cell5_finish.py").write_text(fin)
    print("wrote", OUT_DIR.relative_to(ROOT), sorted(p.name for p in OUT_DIR.iterdir()))


if __name__ == "__main__":
    main()
