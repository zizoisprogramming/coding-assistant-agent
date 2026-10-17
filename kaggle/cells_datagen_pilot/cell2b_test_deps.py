# 2b. Test dependencies the public wheels miss (run after cell 2, INTERNET ON). The sandbox's Python sees this
#     notebook's packages, so without these a correct fix on e.g. fastapi is graded as failed ("No module named").
#     --no-deps: installs only these, upgrades nothing. Update the list from gold_check_v2's test_deps.txt.
import subprocess, sys
TEST_DEPS = ['dirty-equals', 'inline-snapshot', 'asttokens', 'executing', 'typing-inspection']
r = subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '--no-deps', *TEST_DEPS], capture_output=True, text=True)
print('test deps installed:' if r.returncode == 0 else 'TEST DEPS FAILED (is internet on?):', TEST_DEPS, r.stderr[-300:])
