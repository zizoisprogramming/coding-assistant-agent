"""Tests for evidence_r79.py (r79 arms evidd / evide). Run: python3 -I scripts/agent_evidence/test_evidence_r79.py"""
import importlib.util
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "evidence_r79.py")


def load(**switches):
    spec = importlib.util.spec_from_file_location("ev79", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    for k, v in switches.items():
        setattr(m, k, v)
    return m


def sh(cwd, *args, inp=None):
    r = subprocess.run(list(args), cwd=cwd, capture_output=True, text=True, input=inp)
    assert r.returncode == 0, (args, r.stderr)
    return r.stdout.strip()


def make_repo(filler=520):
    """pkg/core.py with a parameter changed in an old commit (git log -S needs the name's count to change), a test, a changelog, then FILLER empty commits on top."""
    d = tempfile.mkdtemp(prefix="ev79_")
    sh(d, "git", "init", "-q", "-b", "main")
    sh(d, "git", "config", "user.email", "t@t"); sh(d, "git", "config", "user.name", "t")
    os.makedirs(os.path.join(d, "pkg")); os.makedirs(os.path.join(d, "tests")); os.makedirs(os.path.join(d, "docs_src"))
    core = "def parse_header(value, convert_flag=True):\n    if convert_flag:\n        value = value.replace('_', '-')\n    return value\n\n\nclass Segment:\n    def split_cells(self, cut):\n        return cut\n"
    open(os.path.join(d, "pkg/core.py"), "w").write(core)
    open(os.path.join(d, "pkg/other.py"), "w").write("from pkg.core import parse_header\n\nX = parse_header('a_b', convert_flag=False)\n")
    open(os.path.join(d, "tests/test_core.py"), "w").write("from pkg.core import parse_header\n\ndef test_x():\n    assert parse_header('a_b') == 'a-b'\n")
    open(os.path.join(d, "docs_src/tutorial.py"), "w").write("from pkg.core import parse_header\nparse_header('q', convert_flag=True)\n")
    open(os.path.join(d, "CHANGELOG.md"), "w").write("- Add convert_flag to parse_header\n")
    sh(d, "git", "add", "-A"); sh(d, "git", "commit", "-q", "-m", "first")
    open(os.path.join(d, "pkg/core.py"), "w").write(core.replace("    if convert_flag:\n", "    if convert_flag and value:  # convert_flag skips empty values\n"))
    sh(d, "git", "commit", "-q", "-am", "Fix convert_flag for empty values")
    head = sh(d, "git", "rev-parse", "HEAD")
    stream = []
    for i in range(filler):
        stream.append(f"commit refs/heads/main\nmark :{i + 1}\ncommitter t <t@t> {1700000000 + i} +0000\ndata 7\nfill{i:03d}\n"
                      + (f"from {head}\n" if i == 0 else f"from :{i}\n") + "\n")
    sh(d, "git", "fast-import", "--quiet", inp="".join(stream))
    sh(d, "git", "reset", "-q", "--hard", "main")
    return d


def run_script(ws, names, **switches):
    """the script's main() in ws, stdout as text."""
    m = load(**switches)
    old_argv, old_cwd = sys.argv, os.getcwd()
    from io import StringIO
    buf, real = StringIO(), sys.stdout
    try:
        sys.argv = ["evidence.py"] + names
        os.chdir(ws)
        sys.stdout = buf
        m.main()
    finally:
        sys.stdout, sys.argv = real, old_argv
        os.chdir(old_cwd)
    return buf.getvalue()


def test_stream_keeps_partial_lines():
    m = load()
    t = time.time()
    lines, finished, _ = m.run_stream(["sh", "-c", "echo a; echo b; printf cut; sleep 5; echo c"], ".", 1.0)
    assert lines == ["a", "b"] and not finished and time.time() - t < 3, (lines, finished)


def test_stream_finishes():
    m = load()
    lines, finished, code = m.run_stream(["sh", "-c", "echo a; echo b"], ".", 5)
    assert lines == ["a", "b"] and finished and code == 0


def test_git_error_is_empty():
    m = load()
    d = tempfile.mkdtemp()
    sh(d, "git", "init", "-q")
    assert m.git(d, ["show", "no-such-rev"], time.time()) == []


def test_names():
    m = load()
    f = m.names_from_args
    assert f(["Segment.split_cells"]) == ["split_cells"]
    assert f(["`convert_underscores`", "include_router()"]) == ["convert_underscores", "include_router"]
    assert f(["validation errors", "RequestValidationError"]) == ["RequestValidationError"]
    assert f(["validation errors"]) == ["validation errors"]
    assert f(["a.b"]) == ["a.b"]  # last part too short: keep the whole
    assert f(["Prompt.ask", "Console.record_html", "rich.console.Console"]) == ["Prompt.ask", "record_html", "Console"]
    assert f(["x1, convert_flag\nparse_header"]) == ["convert_flag", "parse_header"]
    assert f(["--", "foo_bar", "foo_bar"]) == ["foo_bar"]


def test_full_history_finds_old_commit():
    ws = make_repo()
    assert int(sh(ws, "git", "rev-list", "--count", "HEAD")) == 522
    out = run_script(ws, ["convert_flag"])
    assert "Fix convert_flag for empty values" in out, out
    assert "changed around it:" in out and "pkg/core.py:" in out and "if convert_flag and value:" in out, out
    assert "tests mentioning it: 0 lines" in out
    assert "changelog:" in out
    assert "used in source" not in out  # SOURCE_LINES off (evidd)
    assert "ALREADY DONE" in run_script(ws, ["convert_flag"])  # ONCE


def test_source_lines_for_parameters_only():
    ws = make_repo(filler=3)
    out = run_script(ws, ["convert_flag", "parse_header"], SOURCE_LINES=True)
    sec = out.split("== convert_flag")[1].split("== parse_header")[0]
    assert "used in source:" in sec and "pkg/core.py:1:" in sec and "pkg/other.py:3:" in sec, sec
    assert "docs_src" not in sec.split("commits that")[0] and "tests/" not in sec.split("tests mentioning")[1].split("used in source")[1], sec
    sec2 = out.split("== parse_header")[1]
    assert "defined at:" in sec2 and "used in source" not in sec2, sec2  # a def line: no source lines


def test_dotted_name_gets_definition():
    ws = make_repo(filler=3)
    out = run_script(ws, ["Segment.split_cells"])
    assert "== split_cells" in out and "defined at:" in out and "pkg/core.py:8:" in out, out


def test_deadline():
    ws = make_repo(filler=3)
    out = run_script(ws, ["convert_flag", "parse_header"], DEADLINE=0.5)
    assert "(skipped: time)" in out, out


def test_no_names():
    assert "NO NAMES" in run_script(".", [])


if __name__ == "__main__":
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_")]
    for k, v in tests:
        v()
        print("ok", k)
    print(f"{len(tests)} passed")
