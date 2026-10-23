# 2c. Per-task sandbox setup. OUR tasks: the verified setup (ood45_harness install, offline hook, host plugins hidden).
#     PUBLIC tasks: the harness's own install (its wheel filter), then, inside THAT task's sandbox only, the newest
#     competition wheel each pyproject requirement allows (Starlette 1.x broke 42 fastapi tasks) and the test packages
#     the public wheels miss (dirty-equals, inline-snapshot, ...; from the gold-check output). Nothing is added to the
#     notebook's own Python, so our tasks are graded exactly as verified.
import glob, importlib.metadata as _md, subprocess, tomllib
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name, parse_wheel_filename
import swegemma.harness.container_setup as _cs

_dirs = glob.glob('/kaggle/input/**/test_deps_wheels', recursive=True)
assert _dirs, 'test_deps_wheels not found: attach the gold-check output (ziad23samer/test-gemma-comp, or its dataset)'
TEST_DEPS_DIR = Path(_dirs[0])
TEST_DEPS = (TEST_DEPS_DIR.parent / 'test_deps.txt').read_text().split()
print('public test deps (per sandbox):', TEST_DEPS, 'from', TEST_DEPS_DIR)
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
    # --no-deps: their own dependencies (pytest, ...) are already visible in the sandbox (it sees the notebook's Python)
    r = subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '--no-index', '--no-deps', '--find-links',
                        str(TEST_DEPS_DIR), '--target', str(_venv_site(docker, cid)), *TEST_DEPS], capture_output=True, text=True)
    if r.returncode != 0:
        print('   [test deps] FAILED', r.stderr[-300:], flush=True)


def _is_public():
    return ROWS.get(CUR_TASK.get() or '', {}).get('src') == 'public'


def _install_dispatch(docker, container_id, repo='', **kw):
    if _is_public():
        _HARNESS_INSTALL(docker, container_id, repo, **kw)
        pin_task_deps(docker, container_id)
        _install_test_deps(docker, container_id)
        return None
    return _OOD_INSTALL(docker, container_id, repo, **kw)


def _compat_dispatch(filename):
    return (_HARNESS_COMPAT if _is_public() else _OOD_COMPAT)(filename)


_OOD_INSTALL, _OOD_COMPAT = _cs.install_test_dependencies, _cs._is_wheel_compatible_py313
_n = 0
for _name in ('swegemma.harness.container_setup', 'swegemma.harness.verification', 'swegemma.harness.agent_runner',
              'swegemma.evaluate'):
    _mod = importlib.import_module(_name)
    if getattr(_mod, 'install_test_dependencies', None) is _OOD_INSTALL:
        _mod.install_test_dependencies = _install_dispatch
        _n += 1
_cs._is_wheel_compatible_py313 = _compat_dispatch
print(f'per-task setup: install routed in {_n} modules | public pins: {sum(len(v) for v in _WHEELS.values())} wheels indexed')
