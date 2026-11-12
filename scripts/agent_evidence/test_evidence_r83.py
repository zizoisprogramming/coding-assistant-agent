"""Tests for evidence_r83.py (r83 arm evidh: evidefs + the 'changed recently' section).
Run: python3 -I scripts/agent_evidence/test_evidence_r83.py

(1) Every r79 test runs again on the r83 script with RECENT = 0 and SOURCE_LINES as r79 had it: with the new section
    off the script behaves as before. (2) New tests for the section, with RECENT on."""
import importlib.util
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "evidence_r83.py")
spec = importlib.util.spec_from_file_location("t79", os.path.join(HERE, "test_evidence_r79.py"))
t79 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t79)
t79.SCRIPT = SCRIPT
_load79 = t79.load


def load_off(**switches):
    """r83 with the new section off and r79's SOURCE_LINES default (False), unless a test sets them."""
    return _load79(**{"RECENT": 0, "SOURCE_LINES": False, **switches})


t79.load = load_off
sh, run_script = t79.sh, t79.run_script


def commit_file(d, path, text, msg):
    os.makedirs(os.path.dirname(os.path.join(d, path)) or d, exist_ok=True)
    open(os.path.join(d, path), "w").write(text)
    sh(d, "git", "add", "-A")
    sh(d, "git", "commit", "-q", "-m", msg)


def fillers(d, n):
    for i in range(n):
        sh(d, "git", "commit", "-q", "--allow-empty", "-m", f"fill{i:03d}")


def recent_repo(old_fill=0, new_fill=5):
    """pkg/core.py: render() written first, then OLD_FILL empty commits, then a commit that changes two lines of render()'s
    body and the line that uses its 'wrap' option in pkg/other.py, then NEW_FILL empty commits."""
    import tempfile
    d = tempfile.mkdtemp(prefix="ev83_")
    sh(d, "git", "init", "-q", "-b", "main")
    sh(d, "git", "config", "user.email", "t@t"); sh(d, "git", "config", "user.name", "t")
    core = "import os\n\n\ndef render(text, wrap=True):\n    out = text\n    if wrap:\n        out = out.strip()\n    return out\n\n\ndef other():\n    return 1\n"
    commit_file(d, "pkg/core.py", core, "first")
    commit_file(d, "pkg/other.py", "from pkg.core import render\n\nX = render('a', wrap=False)\n", "add other")
    fillers(d, old_fill)
    core2 = core.replace("    if wrap:\n        out = out.strip()\n", "    if wrap and out:\n        out = out.rstrip()\n")
    open(os.path.join(d, "pkg/core.py"), "w").write(core2)
    open(os.path.join(d, "pkg/other.py"), "w").write("from pkg.core import render\n\nX = render('a', wrap=None)\n")
    sh(d, "git", "commit", "-q", "-am", "Only strip the right side when wrapping")
    fillers(d, new_fill)
    return d


def test_r79_behaviour_with_section_off():
    for k, v in sorted(vars(t79).items()):
        if k.startswith("test_"):
            v()


def test_recent_change_to_a_function_body():
    ws = recent_repo(old_fill=2, new_fill=5)
    out = run_script(ws, ["render"], RECENT=300, SOURCE_LINES=True)
    assert "changed recently:" in out and "Only strip the right side when wrapping" in out, out
    assert "5 commits before this checkout" in out, out  # 5 filler commits came after it
    assert "pkg/core.py:6: if wrap and out:" in out and "pkg/core.py:7: out = out.rstrip()" in out, out
    assert "def other" not in out.split("lines it wrote:")[1], out  # the next def is not part of render's block
    sec = out.split("== render")[1]
    assert sec.index("defined at:") < sec.index("changed recently:") < sec.index("commits that added or removed it")


def test_old_change_outside_the_range_is_not_shown():
    ws = recent_repo(old_fill=0, new_fill=60)
    out = run_script(ws, ["render"], RECENT=50, SOURCE_LINES=True)
    assert "changed recently" not in out, out
    assert "defined at:" in out


def test_short_history_blames_everything():
    ws = recent_repo(old_fill=0, new_fill=1)  # 4 commits < RECENT
    out = run_script(ws, ["render"], RECENT=300, SOURCE_LINES=True)
    assert "changed recently:" in out and "Only strip the right side" in out, out


def test_parameter_uses_are_blamed_and_shared_commit_printed_once():
    ws = recent_repo(old_fill=2, new_fill=3)
    out = run_script(ws, ["render", "wrap"], RECENT=300, SOURCE_LINES=True)
    sec = out.split("== wrap")[1]
    assert "used in source:" in sec, out
    assert "changed recently:" in sec and "(the same commit as above)" in sec, out
    assert out.count("Only strip the right side when wrapping") == 1, out


def test_root_commit_and_old_code_are_not_shown():
    """other() was written in the repository's first commit: git blame counts the root commit as a boundary, so an
    initial import is never shown, in a short history (whole history blamed) or a deep one (outside the range)."""
    ws = recent_repo(old_fill=0, new_fill=1)
    assert "changed recently" not in run_script(ws, ["other"], RECENT=300, SOURCE_LINES=True)
    ws = recent_repo(old_fill=60, new_fill=1)
    assert "changed recently" not in run_script(ws, ["other"], RECENT=50, SOURCE_LINES=True)


def test_fast_and_deadline_safe():
    ws = recent_repo(old_fill=2, new_fill=5)
    t = time.time()
    run_script(ws, ["render", "wrap", "other"], RECENT=300, SOURCE_LINES=True)
    assert time.time() - t < 5
    out = run_script(recent_repo(), ["render", "wrap"], RECENT=300, SOURCE_LINES=True, DEADLINE=0.5)
    assert "(skipped: time)" in out or "[done in" in out, out


if __name__ == "__main__":
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_")]
    for k, v in tests:
        v()
        print("ok", k)
    print(f"{len(tests)} passed")
