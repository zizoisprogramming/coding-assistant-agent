"""pubstop shell (skill "work", scripts/run.py): runs one shell command in /workspace, as run_command does, plus one rule:
STOP_AFTER seconds after the last change to a tracked source file, only finishing commands run. There is no other rule,
in particular none for runs with no edit (what-if on 108 pub024 runs: stopping those at 300 s loses 6 of 20 solves;
stopping 60 s after the last edit loses 1 and saves 37 s a run).

- The first command after each edit always runs, so a fix can be checked. edit_file is not gated: a correction restarts
  the timer.
- Only tracked source files count (git diff, not tests): a scratch file or a stray test output can never stop a run.

    run_skill_script skill_name=work file_path=scripts/run.py positional_args=["git grep -n foo"]
"""
import hashlib
import inspect
import json
import os
import re
import signal
import subprocess
import sys
import time

SESSION = 480  # max_time_minutes 8
STOP_AFTER = 60  # seconds after the last source edit
OUT_MAX = 5000  # as the harness's run_command output limit
FINISH_CMD = re.compile(r"^\s*(git (status|diff|checkout --)|rm )[^;|&`$\n]*(&&\s*git (status|diff)[^;|&`$\n]*)*$")
TEST_RE = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)conftest\.py$|(^|/)pytest\.ini$")


def workspace():
    """The repository root: the skill wrapper chdirs into a temp dir, so find the directory it started in."""
    for frame in inspect.stack():
        cwd = frame.frame.f_locals.get("_orig_cwd")
        if isinstance(cwd, str) and os.path.isdir(os.path.join(cwd, ".git")):
            return cwd
    for cand in ("/workspace", os.getcwd()):
        if os.path.isdir(os.path.join(cand, ".git")):
            return cand
    return os.getcwd()


def run_group(cmd, ws, timeout):
    """bash -c CMD in its own process group, killed when the command ends or times out, as run_command does."""
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


def sh(args, ws):
    r = subprocess.run(args, cwd=ws, capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)
    return r.returncode, r.stdout


def state_path(ws):
    return os.path.join(ws, ".git", "agent", "clock.json")


def load_state(ws):
    try:
        return json.load(open(state_path(ws)))
    except Exception:
        return {}


def save_state(ws, state):
    os.makedirs(os.path.dirname(state_path(ws)), exist_ok=True)
    json.dump(state, open(state_path(ws), "w"))


def started(ws, state):
    """Session start: the harness tags _swegemma_baseline when the sandbox starts; else the first run.py call."""
    code, out = sh(["git", "log", "-1", "--format=%ct", "_swegemma_baseline"], ws)
    if code == 0 and out.strip().isdigit():
        return int(out.strip())
    if "t0" not in state:
        state["t0"] = time.time()
    return state["t0"]


def source_diff(ws):
    """(changed tracked source files, hash of their diff). No tracked source change -> ([], "")."""
    _, names = sh(["git", "diff", "--name-only"], ws)
    files = [f for f in names.splitlines() if f.strip() and not TEST_RE.search(f)]
    if not files:
        return [], ""
    _, diff = sh(["git", "diff", "--"] + files, ws)
    return files, hashlib.sha1(diff.encode()).hexdigest()


def note_edit(ws, state, now):
    """Restart the timer if the source diff changed since the last look. Returns the changed files."""
    files, digest = source_diff(ws)
    if digest != state.get("digest", ""):
        state["digest"] = digest
        state["edit_at"] = now
        state["ran_since_edit"] = 0
    return files


def command():
    """The command from positional args (or argv --cmd X)."""
    argv = [a for a in sys.argv[1:] if a != "--"]
    if argv[:1] and argv[0].startswith("--"):
        argv = argv[1:]
    return " ".join(argv).strip()


def main():
    ws = workspace()
    state = load_state(ws)
    t0 = started(ws, state)
    used = int(time.time() - t0)
    cmd = command()
    files = note_edit(ws, state, used)
    since = used - state["edit_at"] if files else None
    stopped = bool(files) and since >= STOP_AFTER and state.get("ran_since_edit", 0) >= 1
    if not cmd:
        body = "NO COMMAND: pass it as positional_args, a list holding one string: the whole shell command."
    elif stopped and not FINISH_CMD.match(cmd):
        state["refused"] = state.get("refused", 0) + 1
        body = (f"REFUSED: {since} s since your last source edit ({', '.join(files[:4])}). Only git status, git diff, "
                "git checkout -- FILE and rm FILE run now. If an earlier output showed that your change is wrong, "
                "correct it with edit_file now. Otherwise run git status --short && git diff once, then call submit_patch.")
    else:
        left = SESSION - used
        code, out, err, timed_out = run_group(cmd, ws, max(5, min(150, left - 10)))
        body = (out + (("\n[stderr]\n" + err) if err.strip() else "")).rstrip()
        body += "\n[timed out: the command and everything it started were stopped]" if timed_out else f"\n[exit {code}]"
        if len(body) > OUT_MAX:
            body = body[:OUT_MAX] + f"\n[output cut at {OUT_MAX} characters: narrow the command]"
        used = int(time.time() - t0)
        state["ran_since_edit"] = state.get("ran_since_edit", 0) + 1
        files = note_edit(ws, state, used)
    if files:
        since = used - state["edit_at"]
        status = (f"source edited: {', '.join(files[:4])}, {since} s ago | {STOP_AFTER} s after your last source edit "
                  "only git status, git diff, git checkout -- and rm run")
    else:
        status = "no source edit yet"
    save_state(ws, state)
    print(body + f"\n[clock] {used} s of {SESSION} used | {status}")


if __name__ == "__main__":
    main()
