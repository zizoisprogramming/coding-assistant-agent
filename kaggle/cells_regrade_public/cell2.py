# 2. RE-GRADE setup (scripts/train/make_regrade_cells.py): inputs, the public tasks' sandbox setup (competition wheels,
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
_WHEELS = {}  # canonical name -> [(version, path)]
for _w in glob.glob(str(DATA_DIR / 'wheels' / '*.whl')):
    try:
        _n, _v, _, _ = parse_wheel_filename(Path(_w).name)
        _WHEELS.setdefault(canonicalize_name(_n), []).append((_v, _w))
    except Exception:
        pass
_PINNED_SEEN = set()


def _requirements(pyproject_text):
    data = tomllib.loads(pyproject_text)
    proj = data.get('project', {})
    reqs = list(proj.get('dependencies', []))
    for group in (proj.get('optional-dependencies') or {}).values():
        reqs += group
    for group in (data.get('dependency-groups') or {}).values():
        reqs += [r for r in group if isinstance(r, str)]
    out = {}
    for r in reqs:
        try:
            req = Requirement(r)
        except Exception:
            continue
        if req.marker is not None and not req.marker.evaluate({'extra': ''}):
            continue
        out.setdefault(canonicalize_name(req.name), req.specifier)
    return out


def _venv_site(docker, cid):
    root = docker._sandboxes[cid]['venv']
    return next(iter(sorted(Path(root).glob('lib/python*/site-packages'))))


def pin_task_deps(docker, cid):
    if type(docker).__name__ not in {'SubprocessManager', 'SubprocessSandbox'}:
        return
    res = docker.exec(cid, 'cat /workspace/pyproject.toml 2>/dev/null')
    if res.exit_code != 0 or not res.stdout.strip():
        return
    try:
        reqs = _requirements(res.stdout)
    except Exception:
        return
    for name, spec in reqs.items():
        if name not in _WHEELS or not str(spec):
            continue
        try:
            have = _md.version(name)
        except _md.PackageNotFoundError:
            have = None
        if have is not None and spec.contains(have, prereleases=True):
            continue
        ok = sorted((v, p) for v, p in _WHEELS[name] if spec.contains(v, prereleases=True))
        if not ok:
            continue
        ver, path = ok[-1]
        r = subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '--no-index', '--no-deps',
                            '--target', str(_venv_site(docker, cid)), path], capture_output=True, text=True)
        if (name, str(ver)) not in _PINNED_SEEN:
            _PINNED_SEEN.add((name, str(ver)))
            print(f'   [pin] {name} {have} -> {ver} (task requires {spec})',
                  '' if r.returncode == 0 else 'FAILED ' + r.stderr[-200:])




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
