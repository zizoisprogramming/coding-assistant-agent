"""Tests for run_stop.py (pubstop's shell) on a throwaway git repository. Run: python3 scripts/agent_clock/test_run_stop.py"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).with_name("run_stop.py").resolve()
AFTER = 60


def git(ws, *args):
    subprocess.run(["git", *args], cwd=ws, check=True, capture_output=True)


def repo():
    ws = Path(tempfile.mkdtemp(prefix="run_stop_"))
    git(ws, "init", "-q")
    git(ws, "config", "user.email", "t@example.com")
    git(ws, "config", "user.name", "t")
    (ws / "src.py").write_text("x = 1\n")
    (ws / "tests").mkdir()
    (ws / "tests/test_a.py").write_text("y = 1\n")
    git(ws, "add", ".")
    git(ws, "commit", "-qm", "base")
    git(ws, "tag", "_swegemma_baseline")
    return ws


def run(ws, cmd):
    r = subprocess.run([sys.executable, str(SCRIPT), cmd], cwd=ws, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return r.stdout


def age_edit(ws, seconds=AFTER + 5):
    """Pretend the last source edit happened `seconds` ago."""
    p = ws / ".git/agent/clock.json"
    s = json.loads(p.read_text())
    s["edit_at"] -= seconds
    p.write_text(json.dumps(s))


def test_no_edit_never_stops():
    ws = repo()
    assert "no source edit yet" in run(ws, "echo hi")
    p = ws / ".git/agent/clock.json"
    assert "edit_at" not in json.loads(p.read_text())
    assert "hi" in run(ws, "echo hi")


def test_scratch_and_test_changes_do_not_count():
    ws = repo()
    (ws / "junk.txt").write_text("a")
    (ws / "tests/test_a.py").write_text("y = 2\n")
    out = run(ws, "echo hi")
    assert "no source edit yet" in out and "hi" in out


def test_first_command_after_edit_runs_even_late():
    ws = repo()
    run(ws, "echo before")
    (ws / "src.py").write_text("x = 2\n")
    out = run(ws, "echo check")  # sees the edit; the first command always runs
    assert "check" in out and "REFUSED" not in out and "src.py" in out
    age_edit(ws)
    assert "REFUSED" in run(ws, "echo again")  # ran once already and the time is up


def test_finishing_commands_run_after_stop():
    ws = repo()
    (ws / "src.py").write_text("x = 2\n")
    run(ws, "echo check")
    age_edit(ws)
    out = run(ws, "git status --short && git diff")
    assert "REFUSED" not in out and "x = 2" in out
    assert "REFUSED" in run(ws, "git status; echo sneaky")


def test_correction_restarts_timer():
    ws = repo()
    (ws / "src.py").write_text("x = 2\n")
    run(ws, "echo check")
    age_edit(ws)
    assert "REFUSED" in run(ws, "echo blocked")
    (ws / "src.py").write_text("x = 3\n")
    assert "REFUSED" not in run(ws, "echo fixed")


def test_edit_by_shell_counts():
    ws = repo()
    run(ws, "sed -i.bak 's/x = 1/x = 9/' src.py && rm src.py.bak")
    s = json.loads((ws / ".git/agent/clock.json").read_text())
    assert "edit_at" in s and s["ran_since_edit"] == 0


def test_reverted_edit_stops_nothing():
    ws = repo()
    (ws / "src.py").write_text("x = 2\n")
    run(ws, "echo check")
    age_edit(ws)
    (ws / "src.py").write_text("x = 1\n")
    out = run(ws, "echo back")
    assert "back" in out and "no source edit yet" in out


def test_no_command_and_output_cut():
    ws = repo()
    assert "NO COMMAND" in run(ws, "")
    assert "output cut at 5000" in run(ws, "python3 -c \"print('a' * 9000)\"")


if __name__ == "__main__":
    names = [n for n in list(globals()) if n.startswith("test_")]
    for n in names:
        globals()[n]()
        print("ok", n)
    print(len(names), "passed")
