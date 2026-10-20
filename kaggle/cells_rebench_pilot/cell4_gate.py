# 4. GATE: the scorer's verify_task on the gold patch (must PASS) and an empty patch (must FAIL), subprocess sandbox,
#    with ood45_harness's install step (task wheels into the sandbox venv + editable install). One line per task.
import asyncio, dataclasses, gc, logging, tarfile, warnings
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

# Kaggle's image has pytest plugins the scoring Docker image does not (pilot 1: typeguard's plugin crashed 16/40 tasks
# on the task's older typing_extensions; langsmith's too). pytest loads every installed plugin, so hide each host-only
# plugin in the sandbox venv with an empty module, unless the task ships that distribution itself. Kept: the ones the
# harness expects from the image (pytest-timeout, pytest-asyncio, xdist, httpbin) and anyio (the harness passes -p no:anyio).
import importlib.metadata as _md
KEEP_PLUGIN_DISTS = {'pytest', 'pytest-timeout', 'pytest-asyncio', 'pytest-xdist', 'pytest-httpbin', 'anyio'}
HOST_PLUGINS = sorted({(ep.value.split(':')[0], (ep.dist.name if ep.dist else '').lower().replace('_', '-'))
                       for ep in _md.entry_points(group='pytest11')})
print('host pytest plugins:', HOST_PLUGINS)


def shadow_host_plugins(site):
    shadowed = []
    for module, dist in HOST_PLUGINS:
        if dist in KEEP_PLUGIN_DISTS or list(site.glob(f"{dist.replace('-', '_')}-*.dist-info")):
            continue
        parts = module.split('.')
        if (site / parts[0]).exists() or (site / f'{parts[0]}.py').exists():
            continue  # the task's own copy of that package is in the venv
        if len(parts) == 1:
            (site / f'{parts[0]}.py').write_text('# hidden by the gate: host-only pytest plugin\n')
        else:
            pkg = site.joinpath(*parts[:-1])
            pkg.mkdir(parents=True, exist_ok=True)
            for k in range(1, len(parts)):
                site.joinpath(*parts[:k], '__init__.py').touch()
            (pkg / f'{parts[-1]}.py').write_text('# hidden by the gate: host-only pytest plugin\n')
        shadowed.append(module)
    return shadowed


ood._shadow_host_plugins = shadow_host_plugins
WHEEL_ROOT = Path('/tmp/rb_wheels')
ood.materialize_wheels(OUT, WHEEL_SET, WHEEL_ROOT / WHEEL_SET)

# The harness leaves these pytest plugins out of every wheel set (its Docker image has them); the sandbox sees this
# notebook's packages, so install the newest one here when a task pins it.
_plugins = sorted({m.group(1).lower().replace('_', '-') for r in ROWS.values() for m in
                   re.finditer(r'(?m)^(pytest[-_](?:asyncio|xdist|httpbin|timeout))==', r['requirements'] or '')})
if _plugins:
    print('host pytest plugins:', _plugins, sh(f'{sys.executable} -m pip install -q ' + ' '.join(_plugins))[0])


def import_name(r):
    """Module the probe imports: the package that holds the first patched source file (its deepest directory with an
    __init__.py), dotted (google/cloud/storage/blob.py -> google.cloud.storage; src/ layout aware),
    read from the snapshot; single-file modules -> their name; fallback: the repo name."""
    tgz = OUT / 'snapshots' / f"{r['instance_id']}.tgz"
    names = set()
    if tgz.exists():
        with tarfile.open(tgz) as tf:
            names = {m.name[2:] if m.name.startswith('./') else m.name for m in tf if m.name.endswith('__init__.py')}
    skip = ('tests/', 'test/', 'testing/', 'docs/', 'doc/', 'examples/', 'example/', 'scripts/', 'tools/', 'benchmarks/')
    for f in re.findall(r'^diff --git a/(\S+)', r['patch'], re.M):
        if not f.endswith('.py') or f.startswith(skip) or '/tests/' in f:
            continue
        root, parts = ('src/', f.split('/')[1:]) if f.startswith('src/') else ('', f.split('/'))
        if len(parts) == 1:
            return parts[0][:-3]
        for k in range(len(parts) - 1, 0, -1):  # deepest package: shared namespaces (google) clash with the host's
            if root + '/'.join(parts[:k]) + '/__init__.py' in names:
                return '.'.join(parts[:k])
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
