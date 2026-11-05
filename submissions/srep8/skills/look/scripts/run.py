"""srep's reporter shell (skill "look", scripts/run.py): the reporter shows the bug by experiment and writes a report; it
changes no source. Every output ends with a clock line.

- A python script that crashes or fails an assert -> "BUG SHOWN": write the report now.
- A python script that passes -> "NO FAILURE": it did not show the bug, try other inputs.
- From REPORT_AT s every command is refused: the reporter must reply with its report in plain text.
- Commands that would change the tree are refused, except scratch files in /tmp and .git/agent.

    run_skill_script skill_name=look file_path=scripts/run.py positional_args=["git grep -n foo"]
"""
import json
import os
import re
import signal
import subprocess
import sys
import time

SESSION = 420  # the whole session (max_time_minutes 7)
REPORT_AT = 90  # srep8: the reporter's share; the fixer gets the rest
OUT_MAX = 5000  # as the harness's run_command output limit
EDIT_CMD = re.compile(r"sed -i|git apply|git checkout|git reset|git stash|\bpatch\b|\brm\b|\bmv\b|open\([^)]*['\"][wa]['\"]|write_text\(|>\s*(?!/tmp|/dev/null|&|\.git/agent)\S")
SCRIPT_CMD = re.compile(r"\bpython[\d.]*\s+(?!-m\s+pytest)\S")
FAILED = re.compile(r"Traceback \(most recent call last\)|AssertionError|^\s*BUG\b", re.M)


def workspace():
    """The repository root: the skill wrapper chdirs into a temp dir, so find the directory it started in."""
    import inspect
    for frame in inspect.stack():
        cwd = frame.frame.f_locals.get("_orig_cwd")
        if isinstance(cwd, str) and os.path.isdir(os.path.join(cwd, ".git")):
            return cwd
    for cand in ("/workspace", os.getcwd()):
        if os.path.isdir(os.path.join(cand, ".git")):
            return cand
    return os.getcwd()


def run_group(cmd, ws, timeout):
    """bash -c CMD in its own process group; the whole group is killed when the command ends or times out."""
    p = subprocess.Popen(["bash", "-c", cmd], cwd=ws, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         stdin=subprocess.DEVNULL, text=True, start_new_session=True)
    timed_out = False
    try:
        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
    try:
        os.killpg(p.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    if timed_out:
        try:
            out, err = p.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            out, err = "", ""
    return p.returncode, out or "", err or "", timed_out


def started(ws):
    """Session start: the harness tags _swegemma_baseline when the sandbox starts; else the first run.py call."""
    r = subprocess.run(["git", "log", "-1", "--format=%ct", "_swegemma_baseline"], cwd=ws, capture_output=True, text=True,
                       timeout=30, stdin=subprocess.DEVNULL)
    if r.returncode == 0 and r.stdout.strip().isdigit():
        return int(r.stdout.strip())
    path = os.path.join(ws, ".git", "agent", "report_t0")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        open(path, "w").write(str(time.time()))
    return float(open(path).read())


def command():
    """The command from positional args."""
    argv = [a for a in sys.argv[1:] if a != "--"]
    if argv[:1] == ["--cmd"]:
        argv = argv[1:]
    return " ".join(argv).strip()


def main():
    ws = workspace()
    used = int(time.time() - started(ws))
    cmd = command()
    state = f"report by {REPORT_AT} s"
    if not cmd:
        body = "NO COMMAND: pass it as positional_args, a list holding one string: the whole shell command."
    elif used >= REPORT_AT:
        body = ("REFUSED: report now. Reply in plain text with NO tool call: your report, with what you know so far. "
                "Say plainly if you did not show the bug.")
        state = "REPORT NOW"
    elif EDIT_CMD.search(cmd):
        body = ("REFUSED: you only look; your teammate makes the fix. Scratch files go in /tmp or .git/agent. "
                "Create them with write_file.")
    else:
        code, out, err, timed_out = run_group(cmd, ws, max(5, min(60, REPORT_AT + 30 - used)))
        body = (out + (("\n[stderr]\n" + err) if err.strip() else "")).rstrip()
        body += "\n[timed out: the command and everything it started were stopped]" if timed_out else f"\n[exit {code}]"
        if len(body) > OUT_MAX:
            body = body[:OUT_MAX] + f"\n[output cut at {OUT_MAX} characters: narrow the command]"
        if SCRIPT_CMD.search(cmd) and not timed_out:
            if code != 0 or FAILED.search(out + err):
                state = "BUG SHOWN if this failure is the issue's: reply now in plain text with your report"
            else:
                state = f"NO FAILURE: this run did not show the bug; try other inputs, report by {REPORT_AT} s"
    print(body + f"\n[clock] {used} s of {SESSION} used | {state}")


if __name__ == "__main__":
    main()
