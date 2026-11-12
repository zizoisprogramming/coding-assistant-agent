"""Tests for trace_v3.py (r90 evval: code path + lines that ran + first-call values). Run: python3 -I scripts/agent_trace/test_trace_v3.py"""
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TRACE = os.path.join(HERE, "trace_v3.py")


def repo():
    """pkg/core.py (render -> clean, _wrap; a branch on width; a caught exception; a default-repr object), a test file."""
    d = tempfile.mkdtemp(prefix="tr3_")
    subprocess.run(["git", "init", "-q", d], check=True)
    os.makedirs(os.path.join(d, "pkg")); os.makedirs(os.path.join(d, "tests")); os.makedirs(os.path.join(d, ".git", "agent"))
    open(os.path.join(d, "pkg", "__init__.py"), "w").write("")
    open(os.path.join(d, "pkg", "util.py"), "w").write("def clean(s):\n    return s.strip()\n")
    open(os.path.join(d, "pkg", "core.py"), "w").write(
        "from pkg.util import clean\n"                      # 1
        "\n"                                                # 2
        "\n"                                                # 3
        "def _wrap(text, width):\n"                         # 4
        "    if width <= 0:\n"                              # 5
        "        raise ValueError('width must be positive')\n"  # 6
        "    if width > 100:\n"                             # 7
        "        return text\n"                             # 8
        "    return text[:width]\n"                         # 9
        "\n"                                                # 10
        "\n"                                                # 11
        "def render(text, width=10):\n"                     # 12
        "    text = clean(text)\n"                          # 13
        "    return _wrap(text, width)\n"                   # 14
        "\n"                                                # 15
        "\n"                                                # 16
        "def safe(x):\n"                                    # 17
        "    try:\n"                                        # 18
        "        return int(x)\n"                           # 19
        "    except ValueError:\n"                          # 20
        "        return -1\n"                               # 21
        "\n"                                                # 22
        "\n"                                                # 23
        "class Box:\n"                                      # 24
        "    def __init__(self, size):\n"                   # 25
        "        self.size = size\n"                        # 26
        "\n"                                                # 27
        "    def grow(self, by):\n"                         # 28
        "        return Box(self.size + by)\n")             # 29
    open(os.path.join(d, "tests", "test_core.py"), "w").write("from pkg.core import render\n\ndef test_r():\n    assert render(' a ') == 'a'\n")
    shutil.copy(TRACE, os.path.join(d, ".git", "agent", "trace.py"))
    return d


def run(d, args, stdin=None):
    r = subprocess.run([sys.executable, os.path.join(d, ".git", "agent", "trace.py")] + args, cwd=d, input=stdin,
                       capture_output=True, text=True, timeout=60)
    return r.returncode, r.stdout, r.stderr


def line(block, name):
    return next(l for l in block.splitlines() if f" {name} (" in l)


def test_values_and_lines():
    d = repo()
    code, out, err = run(d, ["-"], stdin="from pkg.core import render\nprint(render('  hello world  ', 5))\n")
    assert code == 0, (out, err)
    assert out.startswith("hello"), out
    block = out.split("== CODE PATH")[1]
    r = line(block, "render")
    assert r.startswith("  12-14 render (1)") and "ran 13-14" in r and "text='  hello world  ', width=5 -> 'hello'" in r, r
    w = line(block, "_wrap")
    assert "ran 5,7,9" in w and "-> 'hello'" in w, w  # the branch taken: 5 and 7 tested, 9 returned (6 and 8 never ran)
    assert "-> 'hello world'" in line(block, "clean"), block


def test_raised_and_locals():
    d = repo()
    code, out, err = run(d, ["-"], stdin="from pkg.core import render\nrender('x', 0)\n")
    assert code == 1 and "ValueError: width must be positive" in err, err
    assert "raised ValueError at pkg/core.py:6 in _wrap" in out, out
    assert "-> raised ValueError" in line(out, "_wrap") and "-> raised ValueError" in line(out, "render"), out
    loc = next(l for l in out.splitlines() if l.startswith("  locals there:"))
    assert "text='x'" in loc and "width=0" in loc, loc


def test_caught_exception_is_a_return():
    d = repo()
    code, out, _ = run(d, ["-"], stdin="from pkg.core import safe\nprint(safe('z'))\n")
    assert code == 0
    s = line(out, "safe")
    assert "x='z' -> -1" in s and "ran 18-21" in s, s


def test_methods_skip_self_and_show_objects():
    d = repo()
    code, out, _ = run(d, ["-"], stdin="from pkg.core import Box\nb = Box(2).grow(3)\nprint(b.size)\n")
    assert code == 0 and out.startswith("5"), out
    g = line(out, "grow")
    assert "by=3 -> Box(size=5)" in g and "self=" not in g, g


def test_long_values_are_cut():
    d = repo()
    code, out, _ = run(d, ["-"], stdin="from pkg.core import render\nrender('a' * 500, 200)\n")
    r = line(out, "render")
    assert len(r) < 200 and "..." in r, r


def test_no_repo_code_and_exit_code():
    d = repo()
    code, out, _ = run(d, ["-"], stdin="import sys\nprint('hi')\nsys.exit(3)\n")
    assert code == 3 and "never called code from this repository" in out, out


def test_speed():
    d = repo()
    t = time.time()
    code, out, _ = run(d, ["-"], stdin="from pkg.core import render\nfor i in range(20000):\n    render(' a ', 5)\nprint('done')\n")
    assert code == 0 and "render (20000)" in out, out
    assert time.time() - t < 20, time.time() - t


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            try:
                fn(); print("ok  ", name)
            except Exception as e:
                fails += 1; print("FAIL", name, repr(e)[:600])
    sys.exit(1 if fails else 0)
