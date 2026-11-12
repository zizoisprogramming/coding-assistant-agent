"""Tests for trace.py (r84 evtrace). Run: python3 -I scripts/agent_trace/test_trace.py"""
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TRACE = os.path.join(HERE, "trace.py")


def repo():
    """a repository with pkg/core.py (render -> _wrap, other), pkg/util.py, a test file, and trace.py in .git/agent/."""
    d = tempfile.mkdtemp(prefix="tr_")
    subprocess.run(["git", "init", "-q", d], check=True)
    os.makedirs(os.path.join(d, "pkg")); os.makedirs(os.path.join(d, "tests")); os.makedirs(os.path.join(d, ".git", "agent"))
    open(os.path.join(d, "pkg", "__init__.py"), "w").write("")
    open(os.path.join(d, "pkg", "util.py"), "w").write("def clean(s):\n    return s.strip()\n")
    open(os.path.join(d, "pkg", "core.py"), "w").write(
        "from pkg.util import clean\n\n\n"
        "def _wrap(text, width):\n    if width <= 0:\n        raise ValueError('width must be positive')\n    return text[:width]\n\n\n"
        "def render(text, width=10):\n    text = clean(text)\n    return _wrap(text, width)\n\n\n"
        "def other():\n    return 1\n")
    open(os.path.join(d, "tests", "test_core.py"), "w").write("from pkg.core import render\n\ndef test_r():\n    assert render(' a ') == 'a'\n")
    shutil.copy(TRACE, os.path.join(d, ".git", "agent", "trace.py"))
    return d


def run(d, args, stdin=None, cwd=None):
    r = subprocess.run([sys.executable, os.path.join(d, ".git", "agent", "trace.py")] + args, cwd=cwd or d, input=stdin,
                       capture_output=True, text=True, timeout=60)
    return r.returncode, r.stdout, r.stderr


def test_path_of_a_script_file():
    d = repo()
    open("/tmp/tr_check.py", "w").write("from pkg.core import render\nprint(render('  hello world  ', 5))\n")
    code, out, err = run(d, ["/tmp/tr_check.py"])
    assert code == 0, (out, err)
    assert out.startswith("hello"), out  # the script's own output comes first
    block = out.split("== CODE PATH")[1]
    assert "pkg/core.py:" in block and "pkg/util.py:" in block, block
    assert "10-12 render (1)" in block and "4-7 _wrap (1)" in block and "1-2 clean (1)" in block, block
    assert "other" not in block and "tests/" not in block and "trace.py" not in block, block
    assert block.index("pkg/core.py") < block.index("pkg/util.py")  # first-call order: render is entered first


def test_stdin_heredoc_and_exception():
    d = repo()
    code, out, err = run(d, ["-"], stdin="from pkg.core import render\nrender('x', 0)\n")
    assert code == 1
    assert "ValueError: width must be positive" in err, err
    assert "raised ValueError at pkg/core.py:6 in _wrap" in out, out


def test_exit_code_and_no_repo_code():
    d = repo()
    code, out, _ = run(d, ["-"], stdin="import sys\nprint('hi')\nsys.exit(3)\n")
    assert code == 3 and "never called code from this repository" in out, out


def test_tests_and_stdlib_left_out_and_runs_from_a_subdir():
    d = repo()
    sub = os.path.join(d, "pkg")
    code, out, _ = run(d, ["-"], stdin="import json\nfrom tests.test_core import test_r\ntest_r()\nprint(json.dumps(1))\n", cwd=sub)
    assert code == 0, out
    block = out.split("== CODE PATH")[1]
    assert "tests/" not in block and "json" not in block and "pkg/core.py" in block, block


def test_many_calls_are_counted_and_fast():
    d = repo()
    t = time.time()
    code, out, _ = run(d, ["-"], stdin="from pkg.core import render\nfor i in range(20000):\n    render(' ab ', 1)\n")
    assert code == 0 and "10-12 render (20000)" in out, out
    assert time.time() - t < 20


def test_import_time_calls_and_bodies_left_out():
    d = repo()
    open(os.path.join(d, "pkg", "reg.py"), "w").write(
        "from pkg.util import clean\nREG = []\n\n\ndef register(f):\n    REG.append(f)\n    return f\n\n\n"
        "@register\ndef handler(x):\n    return clean(x)\n\n\nclass Box:\n    size = len('abc')\n\n    def get(self):\n        return self.size\n\n\nNAME = clean(' n ')\n")
    code, out, _ = run(d, ["-"], stdin="from pkg.reg import handler, Box\nprint(handler(' z '), Box().get(), [i for i in range(3)])\n")
    assert code == 0, out
    block = out.split("== CODE PATH")[1]
    assert "register" not in block and "<module>" not in block and "Box (" not in block and "listcomp" not in block, block
    assert "10-12 handler (1)" in block and "18-19 get (1)" in block and "1-2 clean (1)" in block, block  # a decorated def starts at its decorator; clean: once, from handler, not at import


def test_usage_and_missing_file():
    d = repo()
    assert run(d, [])[0] == 2
    code, out, _ = run(d, ["/tmp/no_such_file_xyz.py"])
    assert code == 2 and "cannot read" in out


if __name__ == "__main__":
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_")]
    for k, v in tests:
        v()
        print("ok", k)
    print(f"{len(tests)} passed")
