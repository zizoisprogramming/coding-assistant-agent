# 2c. Per-task dependency versions in the Kaggle sandbox (run after cell 2, before grading or agent runs).
#     The sandbox venv sees this notebook's packages, which are newer than many tasks allow: e.g. Starlette 1.x
#     removed Router(on_startup=...), so 42 fastapi tasks failed even with the reference fix. The scorer picks the
#     right version per task from the competition's wheel folder (which ships Starlette 0.19 ... 1.6); this does the
#     same: after a task's sandbox is set up, every dependency in its pyproject.toml whose visible version breaks the
#     task's requirement gets the newest allowed wheel installed INTO THAT SANDBOX ONLY (vLLM and the notebook keep
#     their versions). Prints one line per pinned package the first time a task needs it.
import glob, importlib.metadata as _md, re, subprocess, sys, tomllib
from pathlib import Path
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name, parse_wheel_filename
import swegemma.evaluate, swegemma.harness.container_setup as _cs, swegemma.harness.verification as _ver

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


_orig_install = _cs.install_test_dependencies


def _install_test_dependencies_and_pin(docker, container_id, repo='', **kw):
    _orig_install(docker, container_id, repo, **kw)
    pin_task_deps(docker, container_id)


for _mod in (_cs, _ver, swegemma.evaluate):  # every module that imported the function by name
    if getattr(_mod, 'install_test_dependencies', None) is _orig_install:
        _mod.install_test_dependencies = _install_test_dependencies_and_pin
print(f'per-task dependency pinning on ({sum(len(v) for v in _WHEELS.values())} wheels indexed)')
