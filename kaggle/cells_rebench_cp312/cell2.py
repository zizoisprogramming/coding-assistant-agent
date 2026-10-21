# 2. RE-TARGET TO PYTHON 3.12: inputs and the task set (scripts/datasets/make_rebench_cp312_cells.py).
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
