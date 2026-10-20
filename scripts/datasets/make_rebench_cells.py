"""Writes kaggle/cells_rebench_pilot/: build + gate a pilot of SWE-rebench tasks for our own offline task set (option B).

    .venv/bin/python scripts/datasets/make_rebench_cells.py [--n 40]

CPU notebook, INTERNET ON (no GPU quota). Attach: the competition (sandbox setup.py, sample_submission), the
wheelhouse (swegemma 0.2.11), and rodrigospalma/ood45-bugfix-split (its tools/ood45_harness.py installs a task's
wheels in the subprocess sandbox; its wheels/house has the Docker image's extras such as pytest-timeout).

What the notebook does, per pilot task:
  cell 2  downloads the SWE-rebench rows (HF parquet, on Kaggle) for the pilot ids
  cell 3  BUILD: snapshot = the repo at base_commit with git history up to it (as the competition's snapshots:
          .tgz of the repo root incl. .git, branch main, no later commits); wheels = every pinned requirement as a
          wheel for this machine (Linux x86_64, CPython 3.12): downloaded, or built from the sdist; plus the build
          backend of the project's pyproject.toml (the harness installs the repo with --no-build-isolation)
  cell 4  GATE: the harness's own verify_task on the gold patch (must pass) and on an empty patch (must fail), in
          the subprocess sandbox, with ood45_harness's install step
  cell 5  summary: where tasks drop out and why; sizes and times per task (to size the full run)
Output /kaggle/working/rebench/ in the OOD-45 layout (tasks.jsonl, snapshots/<id>.tgz, wheels/house/*.whl,
wheels/x86_64-cp312/manifest.json mapping task id -> its wheel names), so the same tools load it later.

Pilot choice (seeded): candidates with no FAIL_TO_FAIL / PASS_TO_FAIL (the harness needs every test in the touched
files to pass), one task per repo, no heavy frameworks, stratified by Nebius's difficulty score.
"""
import argparse
import json
import random
import re
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "cells_rebench_pilot"
HEAVY = re.compile(r"^(torch|tensorflow|jax|jaxlib|pyspark|mxnet|paddlepaddle|onnxruntime|cupy|nvidia-)", re.I)


def pick(n):
    """n tasks, one per repo, stratified by Nebius's difficulty score (0: <15 min, 1: <1 h, 2: 1-4 h for a human) in
    the candidate pool's proportions; no heavy frameworks; no FAIL_TO_FAIL / PASS_TO_FAIL."""
    cand = [json.loads(l) for l in open(ROOT / "data/swe_rebench/candidates.jsonl")]
    f2f = {r["instance_id"]: (len(r["FAIL_TO_FAIL"] or []), len(r["PASS_TO_FAIL"] or []))
           for r in pq.read_table(ROOT / "data/swe_rebench/test_f2f.parquet").to_pylist()}
    pool = [r for r in cand if f2f[r["instance_id"]] == (0, 0) and not any(
        HEAVY.match(line.strip()) for line in (r["requirements"] or "").splitlines())]
    diff = lambda r: r["meta"]["llm_score"]["difficulty_score"]  # noqa: E731
    share = {d: sum(diff(r) == d for r in pool) / len(pool) for d in (0, 1, 2)}
    want = {d: round(n * share[d]) for d in (0, 1, 2)}
    want[1] += n - sum(want.values())
    rng = random.Random(20261020)
    rng.shuffle(pool)
    chosen, repos = [], set()
    for r in pool:
        d = diff(r)
        if r["repo"] in repos or want[d] <= 0:
            continue
        want[d] -= 1
        repos.add(r["repo"])
        chosen.append((r["instance_id"], f"difficulty {d}"))
    return sorted(chosen)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    args = ap.parse_args()
    chosen = pick(args.n)
    OUT.mkdir(parents=True, exist_ok=True)
    print(len(chosen), "pilot tasks:", dict(sorted(__import__("collections").Counter(x for _, x in chosen).items())))

    (OUT / "cell1.py").write_text((ROOT / "kaggle/cells_datagen_pilot/cell1_cpu.py").read_text())

    (OUT / "cell2.py").write_text(f'''# 2. Pilot setup: inputs, output layout, and the SWE-rebench rows of the pilot tasks (downloaded here, on Kaggle).
#    Needs INTERNET ON (Settings -> Internet). See scripts/datasets/make_rebench_cells.py.
import collections, json, re, time, urllib.request
import pyarrow.parquet as pq

WORKING_DIR = Path('/kaggle/working')
OUT = WORKING_DIR / 'rebench'  # the task set, OOD-45 layout
WHEEL_SET = 'x86_64-cp312'
HOUSE = OUT / 'wheels' / 'house'
for p in (OUT / 'snapshots', HOUSE, OUT / 'wheels' / WHEEL_SET):
    p.mkdir(parents=True, exist_ok=True)
PILOT = {chosen!r}  # (instance_id, Nebius difficulty score: 0 <15 min, 1 <1 h, 2 1-4 h for a human)


def _first(*cands, pattern=None):
    for c in cands:
        if Path(c).exists():
            return Path(c)
    hits = sorted(glob.glob(pattern, recursive=True)) if pattern else []
    if not hits:
        print('attached inputs (3 levels):', sorted(glob.glob('/kaggle/input/*/*/*'))[:40])
    assert hits, f'none of {{cands}} exists: attach it as a notebook input'
    return Path(hits[0])


DATA_DIR = _first('/kaggle/input/competitions/gemma-4-developer-agent', '/kaggle/input/gemma-4-developer-agent')
OOD_DIR = _first('/kaggle/input/datasets/rodrigospalma/ood45-bugfix-split', '/kaggle/input/ood45-bugfix-split',
                 pattern='/kaggle/input/**/tools/ood45_harness.py')
OOD_DIR = OOD_DIR.parent.parent if OOD_DIR.name == 'ood45_harness.py' else OOD_DIR
print('competition:', DATA_DIR, '| OOD-45 tools:', OOD_DIR)
try:
    urllib.request.urlopen('https://pypi.org/simple/pip/', timeout=20)
except Exception as e:
    raise RuntimeError(f'no internet ({{e!r}}): turn Settings -> Internet on, then re-run this cell')

COLS = ['instance_id', 'repo', 'base_commit', 'created_at', 'problem_statement', 'hints_text', 'patch', 'test_patch',
        'FAIL_TO_PASS', 'PASS_TO_PASS', 'install_config', 'requirements', 'license_name', 'meta']
want, ROWS = {{i for i, _ in PILOT}}, {{}}
for part in ('test-00000-of-00002.parquet', 'test-00001-of-00002.parquet'):
    dst = Path('/tmp/rebench_src') / part
    dst.parent.mkdir(exist_ok=True)
    if not dst.exists():
        t0 = time.time()
        urllib.request.urlretrieve(f'https://huggingface.co/datasets/nebius/SWE-rebench/resolve/main/data/{{part}}', dst)
        print(f'downloaded {{part}} ({{dst.stat().st_size / 1e6:.0f}} MB, {{time.time() - t0:.0f}} s)')
    for r in pq.read_table(dst, columns=COLS).to_pylist():
        if r['instance_id'] in want:
            ROWS[r['instance_id']] = r
missing = sorted(want - set(ROWS))
assert not missing, f'pilot ids not found in SWE-rebench: {{missing}}'
print(len(ROWS), 'pilot tasks from', len({{r['repo'] for r in ROWS.values()}}), 'repos | python versions',
      dict(collections.Counter(r['install_config']['python'] for r in ROWS.values())))
''')

    (OUT / "cell3_build.py").write_text(r'''# 3. BUILD: snapshot + offline wheels per task (network bound, 8 at a time). One line per task; resumes after a restart.
import concurrent.futures as cf, shutil, subprocess, tomllib

PIN = re.compile(r'^([A-Za-z0-9_.\-]+)(\[.*\])?==([^\s;]+)')
BUILD_LOG = OUT / 'build.jsonl'
built = {json.loads(l)['id']: json.loads(l) for l in open(BUILD_LOG)} if BUILD_LOG.exists() else {}
PIN_FILES = {}  # 'name==ver' -> (status, [wheel file names in HOUSE])
_lock = __import__('threading').Lock()


def sh(cmd, cwd=None, timeout=1800):
    r = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout + r.stderr)[-1500:]


def pins_of(req_text):
    out = []
    for line in (req_text or '').splitlines():
        m = PIN.match(line.strip())
        if m:
            out.append(f'{m.group(1)}=={m.group(3)}')
    return out


def fetch_wheels(spec, binary_only_first=True):
    """spec -> (status, wheel names). Downloaded wheel for this machine, else the sdist built into a wheel."""
    with _lock:
        if spec in PIN_FILES:
            return PIN_FILES[spec]
    tmp = Path('/tmp/rb_dl') / re.sub(r'[^A-Za-z0-9_.=-]', '_', spec)
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    code, log = sh(f'{sys.executable} -m pip download -q --no-deps --only-binary=:all: "{spec}" -d {tmp}', timeout=600)
    status = 'wheel'
    if code != 0:
        code, log = sh(f'{sys.executable} -m pip wheel -q --no-deps "{spec}" -w {tmp}', timeout=1200)
        status = 'built' if code == 0 else 'failed: ' + log.strip().splitlines()[-1][:200] if log.strip() else 'failed'
    names = []
    for w in tmp.glob('*.whl'):
        if not (HOUSE / w.name).exists():
            shutil.move(str(w), HOUSE / w.name)
        names.append(w.name)
    shutil.rmtree(tmp, ignore_errors=True)
    res = (status if names else (status if status.startswith('failed') else 'failed: no wheel'), names)
    with _lock:
        PIN_FILES[spec] = res
    return res


def snapshot(r):
    iid, repo, sha = r['instance_id'], r['repo'], r['base_commit']
    d = Path('/tmp/rb_repos') / iid
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    # Only history reachable from base_commit: no later commit (and so no fix) can be in the snapshot.
    for cmd in ('git init -q -b main', f'git remote add origin https://github.com/{repo}.git',
                f'git fetch -q --no-tags origin {sha}', 'git checkout -q -B main FETCH_HEAD', 'git remote remove origin'):
        code, log = sh(cmd, cwd=d, timeout=1800)
        if code:
            return None, f'{cmd.split()[1]} failed: {log.strip().splitlines()[-1][:200] if log.strip() else code}'
    code, head = sh('git rev-parse HEAD', cwd=d)
    if head.strip() != sha:
        return None, f'HEAD {head.strip()[:12]} != base {sha[:12]}'
    _, ncommits = sh('git rev-list --count HEAD', cwd=d)
    build_reqs = []
    try:
        build_reqs = tomllib.loads((d / 'pyproject.toml').read_text()).get('build-system', {}).get('requires', [])
    except Exception:
        pass
    tgz = OUT / 'snapshots' / f'{iid}.tgz'
    code, log = sh(f'tar czf {tgz} -C {d} .')
    shutil.rmtree(d, ignore_errors=True)
    if code:
        return None, 'tar failed: ' + log[-200:]
    return {'commits': int(ncommits.strip() or 0), 'mb': round(tgz.stat().st_size / 1e6, 1), 'build_reqs': build_reqs}, None


def build_row(iid, snap, err, res):
    r = ROWS[iid]
    specs = task_specs(iid, snap)
    row = {'id': iid, 'repo': r['repo'], 'snapshot': snap, 'snapshot_error': err, 'pins': len(specs)}
    row['pins_failed'] = {s: res[s][0] for s in specs if res[s][0].startswith('failed')}
    row['pins_built'] = sorted(s for s in specs if res[s][0] == 'built')
    row['wheels'] = sorted({n for s in specs for n in res[s][1]})
    return row


def task_specs(iid, snap):
    specs = pins_of(ROWS[iid]['requirements'])
    if snap:  # the build backend: '-e /workspace --no-build-isolation' needs it inside the sandbox
        specs += [s for s in snap['build_reqs'] if not s.lower().startswith(('setuptools', 'wheel'))]
    return specs


todo = [i for i, _ in PILOT if i not in built]
print(f'building {len(todo)} tasks ({len(built)} already built)', flush=True)
t_all = time.time()
# Phase A: snapshots, 8 at a time (git fetch = network bound).
SNAPS = {}
with cf.ThreadPoolExecutor(8) as ex:
    for k, (iid, (snap, err)) in enumerate(zip(todo, ex.map(lambda i: snapshot(ROWS[i]), todo)), 1):
        SNAPS[iid] = (snap, err)
        print(f"[snap {k:3}/{len(todo)}] {iid[:44]:44} " + (f"{snap['commits']:6} commits {snap['mb']:7} MB" if snap
              else f"FAILED: {err}"), flush=True)
# Phase B: every distinct package pin of all tasks once, 16 at a time.
specs = sorted({s for i in todo for s in task_specs(i, SNAPS[i][0])})
print(f'fetching {len(specs)} distinct package pins as Linux/CPython 3.12 wheels', flush=True)
RES = {}
with cf.ThreadPoolExecutor(16) as ex:
    for k, (s, res) in enumerate(zip(specs, ex.map(fetch_wheels, specs)), 1):
        RES[s] = res
        if res[0] != 'wheel' or k % 50 == 0 or k == len(specs):
            print(f"[pin {k:4}/{len(specs)}] {s[:50]:50} {res[0][:150]}", flush=True)
# Phase C: one line per task.
for k, iid in enumerate(todo, 1):
    row = build_row(iid, *SNAPS[iid], RES)
    built[iid] = row
    with open(BUILD_LOG, 'a') as fh:
        fh.write(json.dumps(row) + '\n')
    print(f"[task {k:3}/{len(todo)}] {iid[:44]:44} snap={'ok' if row['snapshot'] else 'FAIL'} | pins {row['pins']:3} "
          f"built from source {len(row['pins_built']):2} failed {len(row['pins_failed']):2}"
          + ''.join(f"\n      pin {s}: {st[:150]}" for s, st in list(row['pins_failed'].items())[:3]), flush=True)
manifest = {i: b['wheels'] for i, b in built.items() if b['snapshot']}
(OUT / 'wheels' / WHEEL_SET / 'manifest.json').write_text(json.dumps(manifest, indent=1))
house_gb = sum(p.stat().st_size for p in HOUSE.glob('*.whl')) / 1e9
snap_gb = sum(p.stat().st_size for p in (OUT / 'snapshots').glob('*.tgz')) / 1e9
print(f'build done in {(time.time() - t_all) / 60:.1f} min | snapshots {snap_gb:.2f} GB | wheel house '
      f'{len(list(HOUSE.glob("*.whl")))} wheels {house_gb:.2f} GB')
''')

    (OUT / "cell4_gate.py").write_text(r'''# 4. GATE: the scorer's verify_task on the gold patch (must PASS) and an empty patch (must FAIL), subprocess sandbox,
#    with ood45_harness's install step (task wheels into the sandbox venv + editable install). One line per task.
import asyncio, dataclasses, gc, logging, warnings
warnings.filterwarnings('ignore')
logging.getLogger('swegemma.sandbox.subprocess').setLevel(logging.ERROR)
from adk_submission import ModelRegistry
from swegemma.config import EvalConfig
from swegemma.evaluate import Evaluator
from swegemma.harness.verification import verify_task
from swegemma.models import Task

sys.path.insert(0, str(OOD_DIR / 'tools'))
import ood45_harness as ood  # noqa: E402
print('swegemma', ood.check_swegemma())
ood._STATE['house'] = OOD_DIR / 'wheels' / 'house'  # the Docker image's extras (pytest-timeout, hatchling, ...)
ood.ENV_LOG['path'] = str(WORKING_DIR / 'gate_env_install.jsonl')
ood.patch_harness()
WHEEL_ROOT = Path('/tmp/rb_wheels')
ood.materialize_wheels(OUT, WHEEL_SET, WHEEL_ROOT / WHEEL_SET)

# The harness leaves these pytest plugins out of every wheel set (its Docker image has them); the sandbox sees this
# notebook's packages, so install the newest one here when a task pins it.
_plugins = sorted({m.group(1).lower().replace('_', '-') for r in ROWS.values() for m in
                   re.finditer(r'(?m)^(pytest[-_](?:asyncio|xdist|httpbin|timeout))==', r['requirements'] or '')})
if _plugins:
    print('host pytest plugins:', _plugins, sh(f'{sys.executable} -m pip install -q ' + ' '.join(_plugins))[0])


def import_name(r):
    """Top-level package the probe imports: first path part of the first patched source file (src/ layout aware)."""
    for f in re.findall(r'^diff --git a/(\S+)', r['patch'], re.M):
        parts = f.split('/')
        if parts[0] in ('src', 'lib') and len(parts) > 2:
            parts = parts[1:]
        return parts[0][:-3] if parts[0].endswith('.py') else parts[0]
    return r['repo'].split('/')[1].lower().replace('-', '_')


def as_task(r):
    return Task(instance_id=r['instance_id'], repo=r['repo'], base_commit=r['base_commit'],
                problem_statement=r['problem_statement'], patch=r['patch'], test_patch=r['test_patch'],
                hints_text='', created_at=r['created_at'], FAIL_TO_PASS=tuple(r['FAIL_TO_PASS']),
                PASS_TO_PASS=tuple(r['PASS_TO_PASS']))


GATE = WORKING_DIR / 'gate.json'
gate = json.loads(GATE.read_text()) if GATE.exists() else {}


def tail(text, n=6):
    return ' / '.join((text or '').strip().splitlines()[-n:])[-600:]


async def gate_task(iid):
    r, b = ROWS[iid], built[iid]
    ood.IMPORT_NAMES[r['repo']] = import_name(r)
    cfg = EvalConfig(tasks_path=DATA_DIR / 'tasks.jsonl', snapshots_dir=OUT / 'snapshots', results_dir=WORKING_DIR / 'gate_results',
                     submission_dir=DATA_DIR / 'sample_submission', models=ModelRegistry(), sandbox='subprocess',
                     wheels_dir=WHEEL_ROOT / WHEEL_SET / iid, timeout_seconds=600)
    ev, task, row = Evaluator(cfg), as_task(r), {'import': ood.IMPORT_NAMES[r['repo']]}
    for label, patch in (('gold', r['patch']), ('empty', '')):
        t0 = time.perf_counter()
        try:
            res = await verify_task(ev.docker, cfg, task, OUT / 'snapshots' / f'{iid}.tgz', agent_patch=patch, start_time=t0)
            row[label] = 'PASS' if res.resolved else 'FAIL'
            if label == 'gold' and not res.resolved:
                row['why'] = (res.error or '')[:300]
                row['tail'] = tail(res.test_output)
                row['missing_modules'] = sorted(set(re.findall(r"No module named '([A-Za-z0-9_.]+)", res.test_output or '')))
        except Exception as e:
            row[label] = 'ERROR'
            row['why'] = f'{type(e).__name__}: {str(e)[:400]}'
        row[label + '_s'] = round(time.perf_counter() - t0)
        if label == 'gold' and row['gold'] != 'PASS':
            row['empty'] = 'skipped'
            break
    row['usable'] = row.get('gold') == 'PASS' and row.get('empty') == 'FAIL'
    return row


async def gate_all(ids):
    for k, iid in enumerate(ids, 1):  # one at a time: CPU sessions have 4 cores and the tests are the heavy part
        row = await gate_task(iid)
        gate[iid] = row
        GATE.write_text(json.dumps(gate, indent=1))
        b = built[iid]
        print(f"[{k:3}/{len(ids)}] {iid[:44]:44} gold {row['gold']:5} empty {row.get('empty', '-'):7} usable={row['usable']!s:5} "
              f"| {row.get('gold_s', 0) + row.get('empty_s', 0):4}s | pins failed {len(b['pins_failed'])}"
              + (f"\n      why: {row.get('why', '')[:240]}\n      tail: {row.get('tail', '')[:300]}" if not row['usable'] else ''),
              flush=True)
        for p in glob.glob('/tmp/swegemma_sandbox_*'):
            shutil.rmtree(p, ignore_errors=True)
        gc.collect()


ids = [i for i, _ in PILOT if built.get(i, {}).get('snapshot') and i not in gate]
print(f'gating {len(ids)} tasks ({len(gate)} already gated)', flush=True)
t_g = time.time()
try:
    asyncio.run(gate_all(ids))
except RuntimeError:  # notebook already has a running loop
    import nest_asyncio; nest_asyncio.apply(); asyncio.get_event_loop().run_until_complete(gate_all(ids))
print(f'gate done in {(time.time() - t_g) / 60:.1f} min: usable {sum(g["usable"] for g in gate.values())}/{len(gate)}')
''')

    (OUT / "cell5_summary.py").write_text(r'''# 5. Summary (paste this output to Claude). Writes rebench/tasks.jsonl with every built task + its gate verdict.
st_of = dict(PILOT)
rows = []
for iid, _ in PILOT:
    b, g = built.get(iid, {}), gate.get(iid, {})
    rows.append({'id': iid, 'level': st_of[iid], 'snap': bool(b.get('snapshot')), 'pins_failed': len(b.get('pins_failed', {})),
                 'built': len(b.get('pins_built', [])), 'gold': g.get('gold', '-'), 'empty': g.get('empty', '-'),
                 'usable': bool(g.get('usable')), 'why': (g.get('why') or b.get('snapshot_error') or '')[:90]})
print('funnel: pilot', len(rows), '| snapshot ok', sum(r['snap'] for r in rows),
      '| all pins installed', sum(r['snap'] and r['pins_failed'] == 0 for r in rows),
      '| gold PASS', sum(r['gold'] == 'PASS' for r in rows), '| usable (gold PASS + empty FAIL)', sum(r['usable'] for r in rows))
for s in sorted({r['level'] for r in rows}):
    sub = [r for r in rows if r['level'] == s]
    print(f"  {s}: {len(sub):2} tasks, usable {sum(r['usable'] for r in sub)}")
print('\nnot usable, by first reason:')
reasons = collections.Counter()
for r in rows:
    if not r['usable']:
        w = r['why'].lower()
        reasons['snapshot' if not r['snap'] else 'missing module' if 'no module' in w else
                'sandbox env' if 'sandboxenv' in w or 'importable' in w else 'empty patch passes' if r['gold'] == 'PASS'
                else 'tests fail with gold' if r['gold'] == 'FAIL' else 'harness error'] += 1
print(dict(reasons))
print(f"\n{'task':46} {'level':12} {'built':>5} {'pfail':>5} {'gold':5} {'empty':7} why")
for r in rows:
    print(f"{r['id'][:46]:46} {r['level']:12} {r['built']:5} {r['pins_failed']:5} {r['gold']:5} {r['empty']:7} {r['why']}")
gates = [g.get('gold_s', 0) + g.get('empty_s', 0) for g in gate.values()]
print(f"\ngate per task: median {sorted(gates)[len(gates) // 2] if gates else '-'} s (build time: see the end of cell 3)")
with open(OUT / 'tasks.jsonl', 'w') as fh:
    for iid, _ in PILOT:
        r, g = ROWS[iid], gate.get(iid, {})
        if not built.get(iid, {}).get('snapshot'):
            continue
        fh.write(json.dumps({**{k: r[k] for k in ('instance_id', 'repo', 'base_commit', 'problem_statement', 'patch',
                                                  'test_patch', 'FAIL_TO_PASS', 'PASS_TO_PASS', 'created_at')},
                             'hints_text': '', 'license': r['license_name'], 'source': 'nebius/SWE-rebench (CC-BY-4.0)',
                             'python_original': r['install_config']['python'], 'gate': g}) + '\n')
print('wrote', OUT / 'tasks.jsonl')
''')
    print("wrote", OUT.relative_to(ROOT), sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
