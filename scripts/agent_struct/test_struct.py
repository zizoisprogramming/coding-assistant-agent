"""Tests for look.py, act.py and check.py (r92 evpipe / evloop). Run:
    uv run --no-project --with pytest python -I scripts/agent_struct/test_struct.py"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CORE = ("import os\n\n\n@staticmethod\ndef helper(x):\n    return x\n\n\n"
        "def clamp(x, lo, hi):\n    if x < lo:\n        return lo\n    return x\n\n\n"
        "class Box:\n    def grow(self, by):\n        return by\n")
TEST = "from pkg.core import clamp\n\n\ndef test_low():\n    assert clamp(-1, 0, 5) == 0\n\n\ndef test_high():\n    assert clamp(9, 0, 5) == 5\n"


def repo():
    d = tempfile.mkdtemp(prefix="struct_")
    os.makedirs(os.path.join(d, "pkg")); os.makedirs(os.path.join(d, "tests"))
    open(os.path.join(d, "pkg", "__init__.py"), "w").write("")
    open(os.path.join(d, "pkg", "core.py"), "w").write(CORE)
    open(os.path.join(d, "tests", "test_core.py"), "w").write(TEST)
    for c in (["git", "init", "-q"], ["git", "add", "-A"], ["git", "-c", "user.email=a@b", "-c", "user.name=t", "commit", "-qm", "base"],
              ["git", "tag", "-f", "_swegemma_baseline"]):
        subprocess.run(c, cwd=d, check=True, capture_output=True)
    return d


def run(d, script, *args):
    r = subprocess.run([sys.executable, os.path.join(HERE, script), *args], cwd=d, capture_output=True, text=True, timeout=180,
                       env={**os.environ, "PYTHONPATH": d})
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_look_verbs_and_limit():
    d = repo()
    out = run(d, "look.py", "def", "clamp")
    assert "== pkg/core.py lines 9-12" in out and "    if x < lo:" in out and "[5 look(s) left]" in out, out
    out = run(d, "look.py", "find", "x < lo")
    assert "pkg/core.py:10:" in out and "tests/" not in out, out
    out = run(d, "look.py", "tests", "clamp(")
    assert "tests/test_core.py:5:" in out, out
    out = run(d, "look.py", "show pkg/core.py 15 17")  # one string, as models sometimes send it
    assert "class Box:" in out and "== pkg/core.py lines 15-17" in out, out
    out = run(d, "look.py", "def", "Box.grow")
    assert "def grow(self, by):" in out, out
    out = run(d, "look.py", "find", "nothing_like_this")
    assert "no source line" in out and "last look" in out, out
    out = run(d, "look.py", "def", "clamp")
    assert out.startswith("LOOK LIMIT REACHED"), out
    assert subprocess.run(["git", "status", "--short"], cwd=d, capture_output=True, text=True).stdout.strip() == ""


def test_look_decorated_def():
    d = repo()
    out = run(d, "look.py", "def", "helper")
    assert "@staticmethod" in out and "return x" in out, out


def test_act_rounds_and_paths():
    d = repo()
    out = run(d, "act.py", "pwd && ls /workspace/pkg >/dev/null 2>&1; echo /tmp")
    assert d.rstrip("/") in out or os.path.realpath(d) in out, out
    assert tempfile.gettempdir() in out and "[7 command(s) left in this round]" in out, out
    for _ in range(7):
        out = run(d, "act.py", "true")
    assert "last command" in out, out
    out = run(d, "act.py", "echo again")
    assert out.startswith("ROUND LIMIT REACHED"), out
    run(d, "check.py")  # advances the round
    out = run(d, "act.py", "echo round two")
    assert "round two" in out and "[7 command(s) left" in out, out


def test_check_reports_no_edit_then_failure_then_pass():
    d = repo()
    out = run(d, "check.py")
    assert "ROUND 1 REPORT" in out and "NO SOURCE EDIT YET" in out, out
    open(os.path.join(d, "pkg", "core.py"), "w").write(CORE.replace("        return lo", "        return hi"))  # breaks test_low
    run(d, "act.py", "true")
    out = run(d, "check.py")
    assert "ROUND 2 REPORT" in out and "changed: pkg/core.py" in out and "related tests (tests/test_core.py)" in out, out
    assert "1 failed" in out and "first failure:" in out, out
    open(os.path.join(d, "pkg", "core.py"), "w").write(CORE.replace("    return x\n\n\nclass", "    if x > hi:\n        return hi\n    return x\n\n\nclass"))
    run(d, "act.py", "true")
    out = run(d, "check.py")
    assert "ROUND 3 REPORT" in out and "2 passed" in out and "first failure" not in out, out


def test_check_repeat_without_work_and_sim_marker():
    d = repo()
    open(os.path.join(d, "pkg", "core.py"), "a").write("\nX = 1\n")
    open(os.path.join(d, ".git", "agent_marker"), "w").close()
    os.makedirs(os.path.join(d, ".git", "agent"), exist_ok=True)
    open(os.path.join(d, ".git", "agent", "NO_TESTS"), "w").close()
    first = run(d, "check.py")
    assert "ROUND 1 REPORT" in first and "skipped (simulator)" in first, first
    again = run(d, "check.py")
    assert again == first, again  # nothing done since: the same report, the round not advanced twice
    out = run(d, "act.py", "echo r2")
    assert "[7 command(s) left in this round]" in out, out
    st = subprocess.run(["git", "status", "--porcelain"], cwd=d, capture_output=True, text=True).stdout
    assert st.strip() == "M pkg/core.py", st  # the real index never changed


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            try:
                fn(); print("ok  ", name)
            except Exception as e:  # noqa: BLE001
                fails += 1; print("FAIL", name, repr(e)[:900])
    sys.exit(1 if fails else 0)
