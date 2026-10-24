"""Writes kaggle/cells_regrade_public/: RE-GRADE the public tasks' saved patches from a generation output (CPU, free).

    python3 scripts/train/make_regrade_cells.py

Why (2026-10-24): the combined run (kaggle/cells_gen_combined) graded 0/84 public tasks although 69 submitted real
patches. Likely cause: its cell 2c installed the gold-check test packages INTO each public sandbox with --no-deps,
including pytest-httpbin, a pytest plugin every pytest run loads, whose dependencies (httpbin, flask) were absent on
Kaggle -> every public test run crashed on plugin import (my local sim had them installed, so it passed). This notebook
grades each saved patch again with the harness's own verify_task in the gold check's setup (competition wheels, per-task
pins, test deps without pytest-httpbin, which only the excluded requests tasks need), plus the reference patch of a
few tasks as a control, and prints each test tail. Output results/regrade/gen_per_task.jsonl = the generation rows with
corrected 'resolved' for the public tasks; the samples notebook applies it when attached.

Inputs: the competition, the wheelhouse, the generation output (dataset), the gold-check output (test-gemma-comp).
CPU, internet off.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/train"))
import make_gen_cells as G  # noqa: E402

OUT = ROOT / "kaggle/cells_regrade_public"

CELL2 = r'''# 2. RE-GRADE setup (scripts/train/make_regrade_cells.py): inputs, the public tasks' sandbox setup (competition wheels,
#    per-task pins, test deps except pytest-httpbin), the saved patches. CPU, internet off.
import asyncio, collections, concurrent.futures, json, re, time, tomllib, importlib.metadata as _md
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name, parse_wheel_filename
import swegemma.evaluate, swegemma.harness.container_setup as _cs, swegemma.harness.verification as _ver

DATA_DIR = Path('/kaggle/input/competitions/gemma-4-developer-agent')
assert DATA_DIR.exists(), 'attach the competition data'
WORKING_DIR = Path('/kaggle/working')
_gens = sorted({Path(p).parent.parent for p in glob.glob('/kaggle/input/**/results/tasks_used.jsonl', recursive=True)})
assert len(_gens) == 1, f'attach exactly one generation output (the combined run); found {_gens}'
GEN = _gens[0]
PUBLIC = {json.loads(l)['instance_id']: json.loads(l) for l in open(GEN / 'results' / 'tasks_used.jsonl')
          if json.loads(l).get('src') == 'public'}
ROWS_IN = [json.loads(l) for l in open(GEN / 'results' / 'gen_per_task.jsonl')]
PATCHES = {p.stem.rsplit('__a', 1)[0]: p.read_text() for p in (GEN / 'results' / 'gen' / 'patches').glob('*.diff')}
print(f'generation output {GEN}: {len(ROWS_IN)} rows, {len(PUBLIC)} public tasks, '
      f'{sum(1 for i in PUBLIC if PATCHES.get(i, "").strip())} with a non-empty patch')

_dirs = glob.glob('/kaggle/input/**/test_deps_wheels', recursive=True)
assert _dirs, 'test_deps_wheels not found: attach the gold-check output (ziad23samer/test-gemma-comp, or its dataset)'
TEST_DEPS_DIR = Path(_dirs[0])
# pytest-httpbin is a plugin every pytest run loads; it needs httpbin/flask and only the (excluded) requests tasks use it
TEST_DEPS = [n for n in (TEST_DEPS_DIR.parent / 'test_deps.txt').read_text().split() if n != 'pytest-httpbin']
print('test deps per sandbox:', TEST_DEPS)
''' + G.PIN_FUNCS + r'''

def _install_test_deps(docker, cid):
    r = subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '--no-index', '--no-deps', '--find-links',
                        str(TEST_DEPS_DIR), '--target', str(_venv_site(docker, cid)), *TEST_DEPS], capture_output=True, text=True)
    if r.returncode != 0:
        print('   [test deps] FAILED', r.stderr[-300:], flush=True)


_orig_install = _cs.install_test_dependencies


def _install(docker, container_id, repo='', **kw):
    _orig_install(docker, container_id, repo, **kw)
    pin_task_deps(docker, container_id)
    _install_test_deps(docker, container_id)


for _mod in (_cs, _ver, swegemma.evaluate):
    if getattr(_mod, 'install_test_dependencies', None) is _orig_install:
        _mod.install_test_dependencies = _install
print(f'public setup on ({sum(len(v) for v in _WHEELS.values())} competition wheels indexed for pins)')
'''

CELL3 = r'''# 3. RE-GRADE: the reference patch of 3 tasks first (control: must PASS), then every public task's saved patch with
#    verify_task. One line per task with the test tail. Writes results/regrade/.
import logging, warnings
warnings.filterwarnings('ignore')
logging.getLogger('swegemma.sandbox.subprocess').setLevel(logging.ERROR)
from adk_submission import ModelRegistry
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.apps._configs import EventsCompactionConfig
from swegemma.config import EvalConfig, build_submission_limits
from swegemma.deduplication import resolve_task_snapshot_paths
from swegemma.evaluate import Evaluator
from swegemma.harness.verification import verify_task
from swegemma.models import load_tasks

SUB = WORKING_DIR / 'submission'
for rel, text in {submission!r}.items():
    (SUB / rel).parent.mkdir(parents=True, exist_ok=True)
    (SUB / rel).write_text(text)
OUT = WORKING_DIR / 'results' / 'regrade'
OUT.mkdir(parents=True, exist_ok=True)
limits, gen_constraints = build_submission_limits()
config = EvalConfig(
    tasks_path=DATA_DIR / 'tasks.jsonl', snapshots_dir=DATA_DIR / 'snapshots', results_dir=OUT / 'eval',
    submission_dir=SUB, models=ModelRegistry(), sandbox='subprocess', wheels_dir=DATA_DIR / 'wheels',
    graph_dir=str(DATA_DIR / 'graphs'), embeddings_dir=str(DATA_DIR / 'embeddings'), task_ids=sorted(PUBLIC),
    limits=limits, generation_constraints=gen_constraints,
    context_cache_config=ContextCacheConfig(min_tokens=2048, ttl_seconds=1800, cache_intervals=10),
    events_compaction_config=EventsCompactionConfig(compaction_interval=5, overlap_size=2, token_threshold=14336,
                                                    event_retention_size=5),
    display_mode='quiet', timeout_seconds=600, max_tool_calls=28, max_time_minutes=15.0, max_turns=80)
TASKS = {{t.instance_id: t for t in load_tasks(DATA_DIR / 'tasks.jsonl')}}
GRADED = {{}}


async def grade(iid, patch):
    task = TASKS[iid]
    snap, base_snap, patch_path = resolve_task_snapshot_paths(config.snapshots_dir, iid, task.repo)
    t0 = time.perf_counter()
    try:
        res = await verify_task(EVAL.docker, config, task, snap, agent_patch=patch, base_snapshot_path=base_snap,
                                patch_path=patch_path, start_time=t0)
        ok, tail = bool(res.resolved), (res.error or '') + ' | ' + ' / '.join((res.test_output or '').strip().splitlines()[-3:])
    except Exception as e:
        ok, tail = False, f'ERROR {{type(e).__name__}}: {{str(e)[:200]}}'
    for p in glob.glob('/tmp/swegemma_sandbox_*'):
        shutil.rmtree(p, ignore_errors=True)
    return ok, round(time.perf_counter() - t0), tail[-400:]


async def main():
    global EVAL
    EVAL = Evaluator(config)
    controls = sorted(PUBLIC)[:3]
    for iid in controls:
        ok, s, tail = await grade(iid, TASKS[iid].patch)
        print(f'[control] {{iid:16}} reference patch -> {{"PASS" if ok else "FAIL"}} ({{s}}s) | {{tail[-200:]}}', flush=True)
    n_ok = 0
    for k, iid in enumerate(sorted(PUBLIC), 1):
        patch = PATCHES.get(iid, '')
        if not patch.strip():
            GRADED[iid] = {{'resolved': False, 'why': 'empty patch'}}
            print(f'[{{k:2}}/{{len(PUBLIC)}}] {{iid:16}} empty patch', flush=True)
            continue
        ok, s, tail = await grade(iid, patch)
        n_ok += ok
        GRADED[iid] = {{'resolved': ok, 'seconds': s, 'tail': tail}}
        print(f'[{{k:2}}/{{len(PUBLIC)}}] {{iid:16}} resolved={{ok!s:5}} ({{s}}s) | solved {{n_ok}} | {{tail[-160:]}}', flush=True)
        (OUT / 'regrade.json').write_text(json.dumps(GRADED, indent=1))


with concurrent.futures.ThreadPoolExecutor(max_workers=1) as _pool:
    _pool.submit(lambda: asyncio.run(main())).result()
with open(OUT / 'gen_per_task.jsonl', 'w') as fh:  # the generation rows, public 'resolved' replaced
    for r in ROWS_IN:
        if r['instance_id'] in GRADED:
            r = {{**r, 'resolved': GRADED[r['instance_id']]['resolved'], 'regraded': True}}
        fh.write(json.dumps(r) + '\n')
print(f"==> public re-graded: {{sum(g['resolved'] for g in GRADED.values())}}/{{len(GRADED)}} solved; wrote", OUT / 'gen_per_task.jsonl')
'''


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cell1.py").write_text((ROOT / "kaggle/cells_datagen_pilot/cell1_cpu.py").read_text())
    (OUT / "cell2.py").write_text(CELL2)
    (OUT / "cell3_regrade.py").write_text(CELL3.format(submission=G.submission()))
    print("wrote", OUT.relative_to(ROOT), sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
