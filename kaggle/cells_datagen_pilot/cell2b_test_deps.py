# 2b. Test dependencies the public wheels miss (run after cell 2). The sandbox's Python sees this notebook's packages,
#     so without them a correct fix on e.g. fastapi is graded as failed ("No module named ..."). GPU sessions have no
#     internet: first attach the gold-check notebook's OUTPUT as an input (Add Input -> Your Work -> Notebooks ->
#     the gold check notebook); it contains test_deps_wheels/. --no-deps: installs only these, upgrades nothing.
import glob, subprocess, sys
_dirs = glob.glob('/kaggle/input/**/test_deps_wheels', recursive=True)
assert _dirs, 'test_deps_wheels not found: attach the gold-check notebook output as an input'
_wheels = sorted(glob.glob(_dirs[0] + '/*.whl'))
r = subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '--no-index', '--no-deps', *_wheels],
                   capture_output=True, text=True)
print('test deps installed:' if r.returncode == 0 else 'TEST DEPS FAILED:', [w.rsplit('/', 1)[1] for w in _wheels],
      r.stderr[-300:])
