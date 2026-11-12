"""Tests for evidence_r84.py (r84 arms evmap / evtrace / evall). Run: python3 -I scripts/agent_evidence/test_evidence_r84.py

(1) Every r79 test runs again on the r84 script with MAP and TRACE off (and r79's SOURCE_LINES default): unchanged
    behaviour. (2) The map and the trace install, with the switches on."""
import importlib.util
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "evidence_r84.py")
spec = importlib.util.spec_from_file_location("t79", os.path.join(HERE, "test_evidence_r79.py"))
t79 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t79)
t79.SCRIPT = SCRIPT
_load79 = t79.load
t79.load = lambda **sw: _load79(**{"MAP": False, "TRACE": False, "SOURCE_LINES": False, **sw})
sh, run_script = t79.sh, t79.run_script


def deep_repo():
    """pkg/big.py: 200 filler lines, then class Renderer with render() using 'wrap_width' twice and helper() once;
    pkg/other.py uses it once; tests/test_big.py uses it (tests are not counted)."""
    d = tempfile.mkdtemp(prefix="ev84_")
    sh(d, "git", "init", "-q", "-b", "main")
    sh(d, "git", "config", "user.email", "t@t"); sh(d, "git", "config", "user.name", "t")
    os.makedirs(os.path.join(d, "pkg")); os.makedirs(os.path.join(d, "tests")); os.makedirs(os.path.join(d, "docs_src"))
    filler = "".join(f"X{i} = {i}\n" for i in range(200))
    big = filler + ("\n\nclass Renderer:\n    def render(self, text, wrap_width=10):\n        if wrap_width:\n            return text[:wrap_width]\n"
                    "        return text\n\n    def helper(self):\n        return self.render('a', wrap_width=1)\n\n\ndef unrelated():\n    return 2\n")
    open(os.path.join(d, "pkg/big.py"), "w").write(big)
    open(os.path.join(d, "pkg/other.py"), "w").write("def f(r):\n    return r.render('x', wrap_width=2)\n")
    open(os.path.join(d, "tests/test_big.py"), "w").write("def test_w():\n    wrap_width = 3\n    wrap_width = 4\n    wrap_width = 5\n")
    open(os.path.join(d, "docs_src/tut.py"), "w").write("wrap_width = 1\nwrap_width = 2\nwrap_width = 3\nwrap_width = 4\n")
    sh(d, "git", "add", "-A"); sh(d, "git", "commit", "-q", "-m", "first")
    return d


def test_r79_behaviour_with_switches_off():
    for k, v in sorted(vars(t79).items()):
        if k.startswith("test_"):
            v()


def test_map_ranks_defs_in_the_most_used_file():
    ws = deep_repo()
    out = run_script(ws, ["wrap_width"], MAP=True, TRACE=False, SOURCE_LINES=True)
    head = out.split("== wrap_width")[0]
    assert "== MAP of pkg/big.py (" in head and "defs): the defs that use these names, most uses first" in head, out
    lines = [l.strip() for l in head.splitlines() if l.startswith("  ")]
    assert lines[0] == "204-207 Renderer.render (3)", lines  # the def line itself uses the name too
    assert lines[1] == "209-210 Renderer.helper (1)", lines
    assert not any("unrelated" in l or "tests/" in l or "docs_src" in l for l in lines), lines


def test_map_off_and_no_names_in_source():
    ws = deep_repo()
    assert "== MAP" not in run_script(ws, ["wrap_width"], MAP=False, TRACE=False, SOURCE_LINES=True)
    ws = deep_repo()
    assert "== MAP" not in run_script(ws, ["no_such_name_here"], MAP=True, TRACE=False, SOURCE_LINES=True)


def test_trace_installed_inside_git_and_once_kept():
    ws = deep_repo()
    src = open(os.path.join(HERE, "..", "agent_trace", "trace.py")).read()
    out = run_script(ws, ["wrap_width"], MAP=True, TRACE=True, TRACE_SOURCE=src, SOURCE_LINES=True)
    p = os.path.join(ws, ".git", "agent", "trace.py")
    assert os.path.exists(p) and open(p).read() == src
    assert "ALREADY DONE" in run_script(ws, ["wrap_width"], MAP=True, TRACE=True, TRACE_SOURCE=src, SOURCE_LINES=True)
    assert subprocess.run(["git", "-C", ws, "status", "--short"], capture_output=True, text=True).stdout.strip() == ""  # nothing in the patch
    r = subprocess.run([sys.executable, p, "-"], cwd=ws, input="from pkg.big import Renderer\nprint(Renderer().helper())\n",
                       capture_output=True, text=True, timeout=60)
    assert "pkg/big.py:" in r.stdout and "Renderer.render" not in r.stdout and " render (1)" in r.stdout and " helper (1)" in r.stdout, r.stdout


if __name__ == "__main__":
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_")]
    for k, v in tests:
        v()
        print("ok", k)
    print(f"{len(tests)} passed")
