"""sq1c's shell (skill "work", scripts/run.py): runs one shell command in the repository and ends its output with a
clock line, so the fixer sees the time and whether a source file is edited in every command result (the harness has
no time warning; the model acts on tool outputs, not on prompt rules). With no source edit late in the session it
first warns, then refuses commands until edit_file has changed a source file.

    run_skill_script skill_name=work file_path=scripts/run.py args={"cmd": "git grep -n foo"}
"""
import json
import os
import re
import subprocess
import sys
import time

SESSION = 480  # max_time_minutes 8
WARN_AT = 180  # no source edit by now: warn (runs whose first edit came after 180 s solved 22-34%, before 120 s 76%)
REFUSE_AT = 270  # no source edit by now: refuse commands until one exists
OUT_MAX = 5000  # as the harness's run_command output limit
EDIT_CMD = re.compile(r"sed -i|git apply|\bpatch\b|open\([^)]*['\"][wa]['\"]|write_text\(|>\s*(?!/tmp|/dev/null|&)\S")
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


def sh(cmd, ws, timeout=30):
    r = subprocess.run(cmd, cwd=ws, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    return r.returncode, r.stdout


def started(ws):
    """Session start: the harness tags _swegemma_baseline when the sandbox starts; else the first run.py call."""
    code, out = sh(["git", "log", "-1", "--format=%ct", "_swegemma_baseline"], ws)
    if code == 0 and out.strip().isdigit():
        return int(out.strip())
    path = os.path.join(ws, ".git", "agent", "clock.json")
    try:
        return json.load(open(path))["t0"]
    except Exception:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        json.dump({"t0": time.time()}, open(path, "w"))
        return time.time()


def edited(ws):
    """Changed or new source files (not tests, not scratch files)."""
    _, out = sh(["git", "status", "--porcelain", "--untracked-files=all"], ws)
    files = [line[3:].split(" -> ")[-1].strip('"') for line in out.splitlines() if len(line) > 3]
    return [f for f in files if not TEST_RE.search(f) and not os.path.basename(f).startswith("repro")]


def command():
    """The command from args {"cmd": "..."} (argv --cmd X), a list of strings, or positional args."""
    argv = [a for a in sys.argv[1:] if a != "--"]
    if argv[:1] == ["--cmd"]:
        argv = argv[1:]
    elif argv[:1] and argv[0].startswith("--"):
        argv = argv[1:]
    return " ".join(argv).strip()


def main():
    ws = workspace()
    used = int(time.time() - started(ws))
    cmd = command()
    files = edited(ws)
    if not cmd:
        body = 'NO COMMAND: pass it as args {"cmd": "your shell command"}.'
    elif not files and used >= REFUSE_AT and not EDIT_CMD.search(cmd):
        body = (f"REFUSED: {used} s of {SESSION} used and no source file is edited yet. An unedited tree scores zero; "
                "a best guess can still be corrected. Your next call must be edit_file on the most likely place "
                "(where the wrong behaviour is produced). Commands run again once a source file is edited.")
    else:
        try:
            r = subprocess.run(["bash", "-c", cmd], cwd=ws, capture_output=True, text=True, stdin=subprocess.DEVNULL,
                               timeout=max(5, min(150, SESSION - used - 10)))
            body = (r.stdout + (("\n[stderr]\n" + r.stderr) if r.stderr.strip() else "")).rstrip() + f"\n[exit {r.returncode}]"
        except subprocess.TimeoutExpired:
            body = "[timed out]"
        if len(body) > OUT_MAX:
            body = body[:OUT_MAX] + f"\n[output cut at {OUT_MAX} characters: narrow the command]"
        files = edited(ws)
    if files:
        state = "source edited: " + ", ".join(files[:4])
    elif used >= WARN_AT:
        state = (f"NO SOURCE EDIT YET. Make your best edit now with edit_file; at {REFUSE_AT} s commands are refused "
                 "until a source file is edited")
    else:
        state = "no source edit yet"
    print(body + f"\n[clock] {used} s of {SESSION} used | {state}")


if __name__ == "__main__":
    main()
