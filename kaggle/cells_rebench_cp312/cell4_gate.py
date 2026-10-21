# 4. RE-GATE ON PYTHON 3.12, 3 tasks at a time (never two of one repo: the install step's import name is per repo). Per task: gold
#    must PASS, empty must FAIL, then gold twice more (flaky tests -> dropped). Subprocess sandbox with ood45_harness's
#    install step, as the pilot. One line per task; resumes (rebench/gate.json).
import asyncio, contextvars, gc, logging, tarfile, tempfile, warnings
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
ood.ENV_LOG['path'] = str(OUT / 'gate_env_install.jsonl')
ood.patch_harness()

# Host-only pytest plugins (Kaggle image, not the scoring image) are hidden in each sandbox venv (pilot 1: typeguard's
# plugin broke 16/40 tasks), unless the task ships that distribution itself.
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
            continue
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

# OFFLINE FAIL-FAST (verify run 1, 2026-10-21: with Kaggle's internet off, a connection to the outside HANGS until the
# TCP timeout instead of failing, so installs (setup.py develop -> easy_install) and network-touching tests took 7-14
# min per task; ETA 20 h). A .pth hook in each sandbox venv makes every non-local connect / DNS lookup fail at once
# with "Network is unreachable", as in an offline Docker sandbox (--network none). Loopback stays allowed (local test
# servers). Applies to every Python process that uses the sandbox venv; the harness itself is not affected.
OFFLINE_MODULE = """import errno, ipaddress, socket
_connect, _connect_ex, _getaddrinfo = socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo
_LOCAL_NAMES = {'localhost', 'localhost.localdomain', '', None, socket.gethostname()}


def _local_host(host):
    if isinstance(host, bytes):
        host = host.decode()
    if host in _LOCAL_NAMES:
        return True
    try:
        ip = ipaddress.ip_address(host.split('%')[0])
        return ip.is_loopback or ip.is_unspecified
    except ValueError:
        return False


def _blocked(sock, addr):
    return sock.family in (socket.AF_INET, socket.AF_INET6) and isinstance(addr, tuple) and not _local_host(addr[0])


def connect(self, addr):
    if _blocked(self, addr):
        raise OSError(errno.ENETUNREACH, 'Network is unreachable (offline sandbox)')
    return _connect(self, addr)


def connect_ex(self, addr):
    return errno.ENETUNREACH if _blocked(self, addr) else _connect_ex(self, addr)


def getaddrinfo(host, *args, **kwargs):
    if not _local_host(host):
        raise socket.gaierror(socket.EAI_NONAME, 'Name or service not known (offline sandbox)')
    return _getaddrinfo(host, *args, **kwargs)


socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo = connect, connect_ex, getaddrinfo
"""
_shadow_plugins = shadow_host_plugins


def shadow_host_plugins(site):
    (site / '_rb_offline.py').write_text(OFFLINE_MODULE)
    (site / 'zz_rb_offline.pth').write_text('import _rb_offline\n')
    return _shadow_plugins(site) + ['(offline fail-fast hook)']


ood._shadow_host_plugins = shadow_host_plugins
# Tag every install record with the task being gated (the sandbox threads inherit this context) -> env_partial.
CUR_TASK = contextvars.ContextVar('gate_task', default=None)
ENV_BY_TASK = collections.defaultdict(list)
_orig_log_env = ood._log_env


def _log_env(record):
    record['task'] = CUR_TASK.get()
    ENV_BY_TASK[record['task']].append(record)
    _orig_log_env(record)


ood._log_env = _log_env
# The harness caches one unpacked-wheel tar per wheel set (in /tmp; hundreds of MB each). Record which tars each
# running task uses so the cleanup after each task deletes only tars no running task needs (lock: no task can pick
# up a tar between the cleanup's check and its delete).
import threading
from swegemma.harness import container_setup as _cs
TAR_LOCK, TAR_USERS = threading.Lock(), collections.defaultdict(set)
_orig_tar = _cs._build_unpacked_wheels_tar


def _tar(selected, cache_name, marker):
    with TAR_LOCK:
        p = _orig_tar(selected, cache_name, marker)
        TAR_USERS[Path(p)].add(CUR_TASK.get())
        return p


_cs._build_unpacked_wheels_tar = _tar
WHEEL_ROOT = Path('/tmp/rb_wheels')
ood.materialize_wheels(OUT, WHEEL_SET, WHEEL_ROOT / WHEEL_SET)

# (host pytest plugins: installed offline in cell 3)


def import_name(r):
    """The package that holds the first patched source file (deepest directory with an __init__.py, src/ aware),
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
        for k in range(len(parts) - 1, 0, -1):
            if root + '/'.join(parts[:k]) + '/__init__.py' in names:
                return '.'.join(parts[:k])
    return r['repo'].split('/')[1].lower().replace('-', '_')


def as_task(r):
    return Task(instance_id=r['instance_id'], repo=r['repo'], base_commit=r['base_commit'],
                problem_statement=r['problem_statement'], patch=r['patch'], test_patch=r['test_patch'],
                hints_text='', created_at=r['created_at'], FAIL_TO_PASS=tuple(r['FAIL_TO_PASS']),
                PASS_TO_PASS=tuple(r['PASS_TO_PASS']))


N_GOLD = {i: 3 if SEL[i]['source'] == 'pilot' else 1 for i in SEL}
GATE = OUT / 'gate.json'
gate = json.loads(GATE.read_text()) if GATE.exists() else {}
RUNNING = {}  # task -> start time; caches older than the oldest running task are deleted
CACHE_DIR = Path(tempfile.gettempdir()) / 'swegemma_sp_cache_v8'


def clean_tmp():
    """Delete the wheel tars no running task uses, and sandbox / staging dirs created before the oldest running
    task started (a running task's own dirs are newer than its start)."""
    oldest = min(RUNNING.values(), default=time.time()) - 5
    with TAR_LOCK:
        for p in list(TAR_USERS):
            TAR_USERS[p] &= set(RUNNING)
            if not TAR_USERS[p]:
                p.unlink(missing_ok=True)
                del TAR_USERS[p]
    for p in list(CACHE_DIR.glob('staging_*')) + [Path(p) for p in glob.glob('/tmp/swegemma_sandbox_*')]:
        try:
            if p.stat().st_mtime < oldest:
                shutil.rmtree(p, ignore_errors=True)
        except FileNotFoundError:
            pass


def tail(text, n=6):
    return ' / '.join((text or '').strip().splitlines()[-n:])[-600:]


async def run_patch(cfg, ev, task, iid, patch):
    t0 = time.perf_counter()
    try:
        res = await verify_task(ev.docker, cfg, task, OUT / 'snapshots' / f'{iid}.tgz', agent_patch=patch, start_time=t0)
        return ('PASS' if res.resolved else 'FAIL'), res, round(time.perf_counter() - t0), None
    except Exception as e:
        return 'ERROR', None, round(time.perf_counter() - t0), f'{type(e).__name__}: {str(e)[:400]}'


async def gate_task(iid):
    r = ROWS[iid]
    CUR_TASK.set(iid)
    ood.IMPORT_NAMES[r['repo']] = import_name(r)
    cfg = EvalConfig(tasks_path=DATA_DIR / 'tasks.jsonl', snapshots_dir=OUT / 'snapshots', results_dir=Path('/tmp/rb_gate_results'),
                     submission_dir=DATA_DIR / 'sample_submission', models=ModelRegistry(), sandbox='subprocess',
                     wheels_dir=WHEEL_ROOT / WHEEL_SET / iid, timeout_seconds=600)
    ev, task, row = Evaluator(cfg), as_task(r), {'import': ood.IMPORT_NAMES[r['repo']], 'gold_runs': []}
    for label, patch in (('gold', r['patch']), ('empty', '')) + (('gold', r['patch']),) * (N_GOLD[iid] - 1):
        verdict, res, secs, err = await run_patch(cfg, ev, task, iid, patch)
        row[label + '_s'] = row.get(label + '_s', 0) + secs
        if label == 'empty':
            row['empty'] = verdict
            if verdict != 'FAIL':
                row['why'] = 'the empty patch passes' if verdict == 'PASS' else err
                break
            continue
        row['gold_runs'].append(verdict)
        if verdict != 'PASS':
            out = (res.test_output or '') if res else ''
            row['why'] = err if err else (res.error or '')[:300]
            row['tail'] = tail(out)
            row['missing_modules'] = sorted(set(re.findall(r"No module named '([A-Za-z0-9_.]+)", out)))
            break
    row['gold'] = 'PASS' if row['gold_runs'] and all(v == 'PASS' for v in row['gold_runs']) else 'FAIL'
    row['flaky'] = row['gold_runs'][:1] == ['PASS'] and row['gold'] == 'FAIL'  # passed once, failed on a rerun
    row['usable'] = row['gold_runs'] == ['PASS'] * N_GOLD[iid] and row.get('empty') == 'FAIL'
    recs = ENV_BY_TASK.pop(iid, [])
    row['env_partial'] = any(rec['editable'] and rec['editable'][-1]['exit'] != 0 for rec in recs)
    return row


async def gate_all(ids):
    sem, locks, done = asyncio.Semaphore(3), collections.defaultdict(asyncio.Lock), [0]

    async def one(iid):
        async with locks[ROWS[iid]['repo']]:
            async with sem:
                if time.time() - T_START > DEADLINE_H * 3600:
                    return
                RUNNING[iid] = time.time()
                try:
                    row = await gate_task(iid)
                finally:
                    RUNNING.pop(iid, None)
                gate[iid] = row
                GATE.write_text(json.dumps(gate, indent=1))
                done[0] += 1
                b = built[iid]
                el = (time.time() - t_g) / 60
                print(f"[{done[0]:3}/{len(ids)}] {iid[:44]:44} {LEVEL[iid]:7} gold {'/'.join(row['gold_runs']):14} "
                      f"empty {row.get('empty', '-'):5} usable={row['usable']!s:5}{' env_partial' if row['env_partial'] else ''}"
                      f" | {row.get('gold_s', 0) + row.get('empty_s', 0):4}s | pins failed {len(b['pins_failed'])} | "
                      f"{el:.0f} min, ETA {el / done[0] * (len(ids) - done[0]):.0f} min"
                      + (f"\n      why: {(row.get('why') or '')[:240]}\n      tail: {row.get('tail', '')[:300]}" if not row['usable'] else ''),
                      flush=True)
                clean_tmp()
                gc.collect()

    await asyncio.gather(*(one(i) for i in ids))


# Interleave repos so the per-repo locks rarely block a slot.
_by_repo = collections.defaultdict(list)
for i, _ in TASKS:
    if i not in SNAP_BAD and i not in gate:
        _by_repo[ROWS[i]['repo']].append(i)
ids = [q[k] for k in range(CAP) for q in _by_repo.values() if k < len(q)]
print(f'gating {len(ids)} tasks ({len(gate)} already gated), 3 at a time', flush=True)
t_g = time.time()
try:
    asyncio.run(gate_all(ids))
except RuntimeError:  # notebook already has a running loop
    import nest_asyncio; nest_asyncio.apply(); asyncio.get_event_loop().run_until_complete(gate_all(ids))
skipped = [i for i in ids if i not in gate]
print(f'gate done in {(time.time() - t_g) / 60:.1f} min: usable {sum(g["usable"] for g in gate.values())}/{len(gate)}'
      + (f' | NOT GATED (deadline): {len(skipped)} -> re-run with this output attached' if skipped else ''))
