"""Checks sb1hlt's exact edit step (make_sb1hlt.T_STEP) in throwaway repos made here, with test files written here (only our
own code runs). Run: python3 -I scripts/mine_bank/autotest_cmd_check.py SCRATCH_DIR"""
import importlib.util, os, re, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("T", ROOT / "scripts/make_sb1hlt.py")
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)
SCR = Path(sys.argv[1]); SCR.mkdir(parents=True, exist_ok=True)
ENV = dict(os.environ, GIT_CONFIG_COUNT="2", GIT_CONFIG_KEY_0="core.hooksPath", GIT_CONFIG_VALUE_0="/dev/null", GIT_CONFIG_KEY_1="core.fsmonitor",
           GIT_CONFIG_VALUE_1="false", GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
bad = []


def check(name, ok, info=""):
    print(f"  {'ok ' if ok else 'BAD'} {name}" + (f" | {info[:600]}" if not ok else ""))
    if not ok:
        bad.append(name)


def repo(files):
    w = Path(tempfile.mkdtemp(dir=SCR))
    for k, v in files.items():
        (w / k).parent.mkdir(parents=True, exist_ok=True)
        (w / k).write_text(v)
    subprocess.run(["git", "init", "-q"], cwd=w, env=ENV, check=True)
    subprocess.run(["git", "add", "-A"], cwd=w, env=ENV, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=w, env=ENV, check=True)
    return w


def edit(w, path, old, new):
    cmd = "mkdir -p .git/agent\ncat > .git/agent/old <<'OLD_TEXT'\n" + old + "OLD_TEXT\ncat > .git/agent/new <<'NEW_TEXT'\n" + new + "NEW_TEXT\n" + T.T_STEP.replace("PATH", path)
    r = subprocess.run(["/bin/bash", "-c", cmd], cwd=w, env=ENV, capture_output=True, text=True, timeout=300)
    return r.returncode, r.stdout, r.stderr


MOD = "def add(a, b):\n    return a + b\n\n\ndef neg(a):\n    return -a\n"
TST = "from pkg.mod import add, neg\n\n\ndef test_add():\n    assert add(1, 2) == 3\n\n\ndef test_neg():\n    assert neg(2) == -2\n\n\ndef test_old_broken():\n    assert neg(0) == 1\n"
w = repo({"pkg/__init__.py": "", "pkg/mod.py": MOD, "tests/test_mod.py": TST})
rc, out, err = edit(w, "pkg/mod.py", "    return -a\n", "    return -a * 1\n")
check("1 green edit: EDITED, diff, 'none fail' line naming tests/test_mod.py (the old failing test is not blamed)",
      rc == 0 and re.search(r"(?m)^EDITED ", out) and T.OK_HEAD + "tests/test_mod.py" + T.OK_TAIL in out and T.BAD_HEAD not in out and "+    return -a * 1" in out, out + err)
rc, out, err = edit(w, "pkg/mod.py", "    return a + b\n", "    return a - b\n")
check("2 breaking edit: names tests/test_mod.py::test_add, shows output lines and the fix line",
      rc == 0 and T.BAD_HEAD + "tests/test_mod.py (they passed before it): tests/test_mod.py::test_add" in out and T.BAD_TAIL in out and "test_old_broken" not in out.split(T.BAD_HEAD)[1].split("\n")[0], out + err)
check("2 the edit itself is applied", "a - b" in (w / "pkg/mod.py").read_text())
rc, out, err = edit(w, "pkg/mod.py", "    return a - b\n", "    return a +\n")
check("3 syntax error edit: the collection error is reported as new", rc == 0 and T.BAD_HEAD in out, out + err)
rc, out, err = edit(w, "pkg/mod.py", "nothing like this\n", "x\n")
check("4 found 0: no edit, no test line (the diff of earlier edits may follow, as in sb1h)", rc == 0 and out.startswith("old text found 0 times") and not re.search(r"(?m)^EDITED ", out) and "==" not in out, out + err)
rc, out, err = edit(w, "tests/test_mod.py", "def test_neg():\n", "def test_neg2():\n")
check("5 editing a test file: no test run line", rc == 0 and re.search(r"(?m)^EDITED ", out) and T.OK_HEAD not in out and T.BAD_HEAD not in out, out + err)
w2 = repo({"lib/core.py": "X = 1\n", "lib/__init__.py": "", "README.md": "x\n"})
rc, out, err = edit(w2, "lib/core.py", "X = 1\n", "X = 2\n")
check("6 no test file: sb1hl's output only", rc == 0 and re.search(r"(?m)^EDITED ", out) and "==" not in out, out + err)
w3 = repo({"lib/__init__.py": "", "lib/engine.py": "def f():\n    return 1\n", "tests/test_other.py": "from lib.engine import f\n\n\ndef test_f():\n    assert f() == 1\n"})
rc, out, err = edit(w3, "lib/engine.py", "    return 1\n", "    return 2\n")
check("7 fallback by the dotted module path (no test_engine.py): finds tests/test_other.py", T.BAD_HEAD + "tests/test_other.py" in out, out + err)
w3b = repo({"src/pkg/__init__.py": "", "src/pkg/thing.py": "def f():\n    return 1\n", "tests/test_other.py": "from pkg.thing import f\n\n\ndef test_f():\n    assert f() == 1\n"})
rc, out, err = edit(w3b, "src/pkg/thing.py", "    return 1\n", "    return 2\n")
check("7b src/ layout not installed: tests error before and after -> silent, edit applied", rc == 0 and re.search(r"(?m)^EDITED ", out) and "==" not in out, out + err)
w4 = repo({"pkg/__init__.py": "def g():\n    return 1\n", "tests/test_pkg.py": "from pkg import g\n\n\ndef test_g():\n    assert g() == 1\n"})
rc, out, err = edit(w4, "pkg/__init__.py", "    return 1\n", "    return 3\n")
check("8 __init__.py: module = folder name -> tests/test_pkg.py, breaking edit reported", T.BAD_HEAD + "tests/test_pkg.py" in out, out + err)
w5 = repo({"pkg/__init__.py": "", "pkg/slow.py": "def s():\n    return 1\n", "tests/test_slow.py": "import time\nfrom pkg.slow import s\n\n\ndef test_s():\n    time.sleep(70)\n    assert s() == 1\n"})
rc, out, err = edit(w5, "pkg/slow.py", "    return 1\n", "    return 2\n")
check("9 a test file slower than 60 s: the edit is applied, no test line, no traceback", rc == 0 and re.search(r"(?m)^EDITED ", out) and "==" not in out and "Traceback" not in out + err, out + err)
status = subprocess.run(["git", "status", "--short", "--untracked-files=all"], cwd=w, env=ENV, capture_output=True, text=True).stdout
check("10 no bytecode / cache files left in the repo", "__pycache__" not in status and ".pytest_cache" not in status, status)
print("problems:", bad or "none")
