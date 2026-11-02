"""sq1c2f6's shell (skill "work", scripts/run.py): sq1c2's clock shell plus two finish events, so runs end sooner
without touching the first 270 s. Every output ends with a clock line (time used, source edited or not).

- Before 270 s: as sq1c2 (warning from 180 s with no source edit, refusal from 270 s until a source file is edited).
- Event A: a command prints a line starting with FIXED (the repro passes) while a source file is edited -> the clock
  says to finish; FIXED_GRACE s later the finish window opens.
- Event B: from FINISH_AT s with a source file edited, the finish window opens.
- In the finish window only finishing commands run (git status / git diff / git checkout -- / rm); edit_file still
  works, so a last correction is possible.

    run_skill_script skill_name=work file_path=scripts/run.py positional_args=["git grep -n foo"]
"""
import json
import os
import re
import signal
import subprocess
import sys
import time

SESSION = 480  # max_time_minutes 8 (sq1c2a8)
WARN_AT = 180  # as sq1c2: no source edit by now -> warn
REFUSE_AT = 270  # as sq1c2: no source edit by now -> refuse commands until one exists
FINISH_AT = None  # sq1c2a8: event B off
FIXED_GRACE = 60  # event A: finish window opens this long after the repro first printed FIXED
OUT_MAX = 5000  # as the harness's run_command output limit
EDIT_CMD = re.compile(r"sed -i|git apply|\bpatch\b|open\([^)]*['\"][wa]['\"]|write_text\(|>\s*(?!/tmp|/dev/null|&)\S")
FINISH_CMD = re.compile(r"^\s*(git (status|diff|checkout --)|rm )[^;|&`$\n]*(&&\s*git (status|diff)[^;|&`$\n]*)*$")
FIXED_RE = re.compile(r"^\s*FIXED\b", re.M)
TEST_RE = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)conftest\.py$|(^|/)pytest\.ini$")


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
    """bash -c CMD in its own process group; the whole group is killed when the command ends or times out, as the
    harness's run_command does (adk_eval_core subprocess_sandbox.py), so no runaway child outlives the call
    (2026-11-02: an orphaned process froze a Kaggle run: tool calls slowed to 27 s, then no model calls at all)."""
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


def sh(cmd, ws, timeout=30):
    r = subprocess.run(cmd, cwd=ws, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
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
        save_state(ws, state)
    return state["t0"]


def edited(ws):
    """Changed or new source files (not tests, not scratch files)."""
    _, out = sh(["git", "status", "--porcelain", "--untracked-files=all"], ws)
    files = [line[3:].split(" -> ")[-1].strip('"') for line in out.splitlines() if len(line) > 3]
    return [f for f in files if not TEST_RE.search(f) and not os.path.basename(f).startswith("repro")]


def command():
    """The command from positional args (or args {"cmd": "..."}, argv --cmd X)."""
    argv = [a for a in sys.argv[1:] if a != "--"]
    if argv[:1] == ["--cmd"]:
        argv = argv[1:]
    elif argv[:1] and argv[0].startswith("--"):
        argv = argv[1:]
    return " ".join(argv).strip()


def finish_opens(used, state):
    """Seconds into the session at which the finish window opens (given a source edit)."""
    opens = float('inf') if FINISH_AT is None else FINISH_AT
    if "fixed_at" in state:
        opens = min(opens, state["fixed_at"] + FIXED_GRACE)
    return opens


def main():
    ws = workspace()
    state = load_state(ws)
    used = int(time.time() - started(ws, state))
    cmd = command()
    files = edited(ws)
    if not cmd:
        body = "NO COMMAND: pass it as positional_args, a list holding one string: the whole shell command."
    elif not files and used >= REFUSE_AT and not EDIT_CMD.search(cmd):
        body = (f"REFUSED: {used} s of {SESSION} used and no source file is edited yet. An unedited tree scores zero; "
                "a best guess can still be corrected. Your next call must be edit_file on the most likely place "
                "(where the wrong behaviour is produced). Commands run again once a source file is edited.")
    elif files and used >= finish_opens(used, state) and not FINISH_CMD.match(cmd):
        body = (f"REFUSED: FINISH NOW ({used} s of {SESSION} used, source edited: {', '.join(files[:4])}). Only "
                "git status, git diff, git checkout -- TESTFILE and rm SCRATCHFILE run now. Check the diff once, "
                "then reply in plain text with no tool call: one line on what you changed and where.")
    else:
        code, out, err, timed_out = run_group(cmd, ws, max(5, min(150, SESSION - used - 10)))
        body = (out + (("\n[stderr]\n" + err) if err.strip() else "")).rstrip()
        body += "\n[timed out: the command and everything it started were stopped]" if timed_out else f"\n[exit {code}]"
        if len(body) > OUT_MAX:
            body = body[:OUT_MAX] + f"\n[output cut at {OUT_MAX} characters: narrow the command]"
        files = edited(ws)
        if files and "fixed_at" not in state and FIXED_RE.search(body):
            state["fixed_at"] = used
            save_state(ws, state)
    if files and used >= finish_opens(used, state):
        state_txt = "source edited: " + ", ".join(files[:4]) + " | FINISH NOW: git status && git diff, then the one-line reply"
    elif files and "fixed_at" in state:
        state_txt = ("source edited: " + ", ".join(files[:4]) + f" | REPRO PASSES: run at most one related test file, "
                     f"then FINISH; from {finish_opens(used, state)} s only finishing commands run")
    elif files:
        state_txt = "source edited: " + ", ".join(files[:4])
    elif used >= WARN_AT:
        state_txt = (f"NO SOURCE EDIT YET. Make your best edit now with edit_file; at {REFUSE_AT} s commands are "
                     "refused until a source file is edited")
    else:
        state_txt = "no source edit yet"
    print(body + f"\n[clock] {used} s of {SESSION} used | {state_txt}")


if __name__ == "__main__":
    main()
