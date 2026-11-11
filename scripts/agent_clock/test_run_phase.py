"""Tests for run_phase.py on throwaway git repositories, per switch. Run: python3 scripts/agent_clock/test_run_phase.py"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

SRC = Path(__file__).with_name("run_phase.py").read_text()
SOURCE = "def helper(a):\n    return a\n\n\ndef caller():\n    return helper(1)\n"


def git(ws, *args):
    subprocess.run(["git", *args], cwd=ws, check=True, capture_output=True)


def setup(**switches):
    ws = Path(tempfile.mkdtemp(prefix="run_phase_"))
    git(ws, "init", "-q")
    git(ws, "config", "user.email", "t@example.com")
    git(ws, "config", "user.name", "t")
    (ws / "src.py").write_text(SOURCE)
    (ws / "other.py").write_text("from src import helper\nvalue = helper(2)\n")
    (ws / "tests").mkdir()
    (ws / "tests/test_a.py").write_text("from src import helper\n\n\ndef test_helper():\n    assert helper(1) == 1\n")
    git(ws, "add", ".")
    git(ws, "commit", "-qm", "base")
    git(ws, "tag", "_swegemma_baseline")
    text = SRC
    for k, v in switches.items():
        text, n = re.subn(rf"^{k} = .*$", f"{k} = {v!r}", text, flags=re.M)
        assert n == 1, k
    script = Path(tempfile.mkdtemp(prefix="run_phase_script_")) / "run.py"
    script.write_text(text)
    return ws, script


def run(env, cmd):
    ws, script = env
    r = subprocess.run([sys.executable, str(script), cmd], cwd=ws, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return r.stdout


def state(env):
    return json.loads((env[0] / ".git/agent/clock.json").read_text())


def age(env, key="edit_at", seconds=65):
    p = env[0] / ".git/agent/clock.json"
    s = json.loads(p.read_text())
    s[key] -= seconds
    p.write_text(json.dumps(s))


def edit(env, text="def helper(a):\n    return a + 1\n\n\ndef caller():\n    return helper(1)\n"):
    (env[0] / "src.py").write_text(text)


def test_look_then_edit_now_then_refused_by_shell_count():
    env = setup(WORDS=True, WARN_SHELL=2, REFUSE_SHELL=3)
    assert "[state] LOOK" in run(env, "echo a")
    out = run(env, "echo b")
    assert "b" in out and "[state] EDIT NOW" in out
    out = run(env, "echo c")
    assert "REFUSED: no source file" in out and "\nc\n" not in out


def test_refused_by_time():
    env = setup(REFUSE_AT=0)
    assert "REFUSED: no source file" in run(env, "echo a")


def test_edit_command_passes_when_late_and_clears_refusal():
    env = setup(REFUSE_SHELL=1)
    out = run(env, "sed -i.bak 's/return a/return a + 1/' src.py && rm src.py.bak")
    assert "REFUSED" not in out and "CHECK" in out
    assert "hi" in run(env, "echo hi")


def test_check_then_finish_after_test():
    env = setup(WORDS=True)
    run(env, "echo a")
    edit(env)
    assert "[state] CHECK" in run(env, "echo first")
    out = run(env, "python -m pytest tests/test_a.py -q || true")
    assert "[state] FINISH" in out


def test_stop_rule_and_first_command_after_edit():
    env = setup()
    edit(env)
    run(env, "echo first")
    age(env)
    assert "REFUSED: your last source edit" in run(env, "echo late")
    out = run(env, "git status --short && git diff")
    assert "REFUSED" not in out and "return a + 1" in out
    edit(env, SOURCE.replace("return a", "return a + 2"))
    assert "fixed" in run(env, "echo fixed")  # a correction restarts the timer


def test_scratch_and_tests_do_not_count_as_edits():
    env = setup(REFUSE_SHELL=99)
    (env[0] / "junk.txt").write_text("x")
    (env[0] / "tests/test_a.py").write_text("x = 1\n")
    assert "no source edit yet" in run(env, "echo a")


def test_words_arm_adds_no_digits():
    env = setup(WORDS=True, WARN_SHELL=2, REFUSE_SHELL=4)
    outs = [run(env, "echo")] + [run(env, "echo") for _ in range(3)]
    edit(env)
    outs.append(run(env, "echo"))
    age(env)
    outs += [run(env, "echo"), run(env, "git status --short")]
    outs.append(run(env, "python -c \"print('a' * 9000)\"") if False else "")
    joined = "\n".join(outs)
    assert "[state]" in joined
    assert not re.search(r"\d", joined.replace("git status", "")), joined



def test_remind_adds_the_prefix_to_the_last_line_and_stays_digit_free():
    env = setup(WORDS=True, LIGHT=True, REMIND=True)
    out = run(env, "echo a")
    last = out.strip().splitlines()[-1]
    assert last.startswith("[state] LOOK") and "every command: python .git/agent/run.py" in last, last
    assert not re.search(r"\d", last), last
    assert "every command" not in run(setup(WORDS=True), "echo a")


def test_refuse_once_then_commands_run_with_edit_now():
    env = setup(WORDS=True, LIGHT=True, WARN_SHELL=2, REFUSE_SHELL=3, REFUSE_ONCE=True)
    for _ in range(2):
        run(env, "echo a")
    assert "REFUSED: no source file is edited yet" in run(env, "echo a")
    out = run(env, "echo again")
    assert "REFUSED" not in out and "again" in out and "EDIT NOW" in out, out
    assert "REFUSED" not in run(env, "echo third")


def test_scout_words_and_refusal_ask_for_notes_and_edits_never_unlock():
    env = setup(WORDS=True, LIGHT=True, SCOUT=True, WARN_SHELL=2, REFUSE_SHELL=3)
    assert "LOOK: scouting" in run(env, "echo a")
    assert "NOTES NOW" in run(env, "echo b")
    out = run(env, "echo c")
    assert out.startswith("REFUSED: scouting is over") and "EDIT NOW" not in out, out
    assert "REFUSED: scouting is over" in run(env, "echo d")
    assert not re.search(r"\\d", out)

def test_numbered_arm_shows_seconds():
    env = setup()
    assert re.search(r"\[clock\] \d+ s of 480 used", run(env, "echo a"))


def test_checklist_blocks_then_shown_once_each_moment():
    env = setup(WORDS=True, CHECKLIST=True)
    assert "REFUSED: first write your issue checklist" in run(env, "echo a")
    (env[0] / ".git/agent").mkdir(exist_ok=True)
    (env[0] / ".git/agent/issue.md").write_text("name: helper\n")
    out = run(env, "echo b")
    assert "b" in out and "[issue checklist]" not in out
    edit(env)
    assert "[issue checklist]" in run(env, "echo c")
    assert "[issue checklist]" not in run(env, "echo d")
    assert "[issue checklist]" in run(env, "python -m pytest tests/test_a.py -q || true")
    assert "[issue checklist]" not in run(env, "git status --short")


def test_places_lists_others_and_tests_once():
    env = setup(PLACES=True)
    edit(env)
    out = run(env, "echo a")
    assert "[other places] helper" in out and "other.py" in out and "[related tests] helper: tests/test_a.py" in out
    assert "[other places]" not in run(env, "echo b")


def test_places_off_by_default_and_skips_dunder_and_common():
    env = setup()
    edit(env)
    assert "[other places]" not in run(env, "echo a")
    env = setup(PLACES=True, PLACES_COMMON=1)
    edit(env)
    assert "[other places]" not in run(env, "echo a")
    env = setup(PLACES=True)
    (env[0] / "src.py").write_text("class C:\n    def __init__(self):\n        self.x = 2\n")
    assert "[other places]" not in run(env, "echo a")


def git_count(env, cmd, stdin=None):
    """Runs the script with a counting git shim on PATH; returns (output, git processes)."""
    ws, script = env
    shim = Path(tempfile.mkdtemp(prefix="git_shim_"))
    log = shim / "log.txt"
    real = subprocess.run(["which", "git"], capture_output=True, text=True).stdout.strip()
    (shim / "git").write_text(f"#!/bin/sh\necho x >> {log}\nexec {real} \"$@\"\n")
    (shim / "git").chmod(0o755)
    args = [sys.executable, str(script)] + ([cmd] if cmd else [])
    r = subprocess.run(args, cwd=ws, capture_output=True, text=True, timeout=60, input=stdin or "",
                       env={"PATH": f"{shim}:/usr/bin:/bin", "HOME": str(ws)})
    assert r.returncode == 0, r.stderr
    return r.stdout, len(log.read_text().splitlines()) if log.exists() else 0


def test_light_uses_fewer_git_processes():
    heavy = setup()
    light = setup(LIGHT=True)
    for env in (heavy, light):
        git_count(env, "echo first")
    _, h = git_count(heavy, "echo a")
    _, l = git_count(light, "echo a")
    assert l < h and l == 1, (l, h)


def test_light_edit_by_command_is_seen_and_rules_hold():
    env = setup(LIGHT=True)
    out = run(env, "sed -i.bak 's/return a/return a + 1/' src.py && rm src.py.bak")
    assert "CHECK" in out
    age(env)
    assert "late" in run(env, "echo late")  # the first command after an edit still runs
    assert "REFUSED: your last source edit" in run(env, "echo late again")


def test_light_edit_outside_the_shell_seen_on_next_call():
    env = setup(LIGHT=True)
    run(env, "echo a")
    edit(env)
    assert "CHECK" in run(env, "echo b")


def test_command_on_stdin():
    env = setup(LIGHT=True, WORDS=True)
    out, _ = git_count(env, None, stdin="echo 'from stdin'\n")
    assert "from stdin" in out and "NO COMMAND" not in out
    out, _ = git_count(setup(LIGHT=True), None)
    assert "NO COMMAND" in out


def test_silent_open_stdin_does_not_hang():
    ws, script = setup(LIGHT=True)
    p = subprocess.Popen([sys.executable, str(script)], cwd=ws, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        out = p.stdout.read()  # stdin stays open and silent: the script must still answer
        assert "NO COMMAND" in out, out
        assert p.wait(timeout=20) == 0
    finally:
        p.stdin.close()
        p.kill()


def test_short_reads():
    env = setup(READS=True, LIGHT=True)
    assert "src.py:1:def helper" in run(env, "where helper src.py")
    assert "src.py:" in run(env, "where 'helper(a)'")
    out = run(env, "outline src.py")
    assert "1:def helper" in out and "5:def caller" in out
    out = run(env, "lines src.py 2 2")
    assert "2      return a" in out and "def helper" not in out
    assert "src.py" in run(env, "git ls-files")  # anything else runs as it is


def test_short_reads_off_and_refused_like_any_command():
    assert "command not found" in run(setup(LIGHT=True), "where helper")
    env = setup(READS=True, LIGHT=True, REFUSE_SHELL=1)
    assert "REFUSED: no source file" in run(env, "where helper")


def test_places_survives_syntax_error():
    env = setup(PLACES=True)
    edit(env, "def broken(:\n")
    assert "CHECK" in run(env, "echo a")


if __name__ == "__main__":
    names = [n for n in list(globals()) if n.startswith("test_")]
    for n in names:
        globals()[n]()
        print("ok", n)
    print(len(names), "passed")
