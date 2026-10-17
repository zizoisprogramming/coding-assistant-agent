# 2b. Test dependencies the public wheels miss (run after cell 2). The sandbox's Python sees this notebook's packages,
#     so without them a correct fix is graded as failed ("No module named ...", requests' missing httpbin plugin).
#     GPU sessions have no internet: first attach the gold-check notebook's OUTPUT as an input (Add Input -> Your
#     Work -> Notebooks -> the gold-check notebook); it holds test_deps.txt and test_deps_wheels/. Installs offline;
#     pip adds only what is missing and upgrades nothing that is already installed.
import glob, subprocess, sys
from pathlib import Path
_dirs = glob.glob('/kaggle/input/**/test_deps_wheels', recursive=True)
assert _dirs, 'test_deps_wheels not found: attach the gold-check notebook output as an input'
_names = (Path(_dirs[0]).parent / 'test_deps.txt').read_text().split()
r = subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '--no-index', '--find-links', _dirs[0], *_names],
                   capture_output=True, text=True)
print('test deps installed:' if r.returncode == 0 else 'TEST DEPS FAILED:', _names, r.stderr[-400:])
