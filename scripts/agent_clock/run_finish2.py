"""sq1c2f6ra / sq1c2f6rc shell (skill "work", scripts/run.py): sq1c2f6's clock shell (scripts/agent_clock/run_finish.py)
plus a repeat block and, with CHECKLIST on, the fixer's issue checklist. Every output ends with a clock line.

- As sq1c2f6: warning from 180 s and refusal from 270 s with no source edit; finish window 60 s after the repro
  first prints FIXED, and from 300 s (only git status / diff / checkout -- / rm then).
- Repeat block: the exact command already ran and nothing changed since (git diff + status, files in .git/agent, /tmp
  files the command names) -> refused, with the start of its earlier output (compaction may have dropped it from the context).
- CHECKLIST (sq1c2f6rc): commands are refused until write_file has created .git/agent/issue.md (the issue's exact
  names, strings, expected behaviour); the clock shows that file after the first source edit and when the repro passes
  or the finish window opens, i.e. when names and messages are chosen and checked.

    run_skill_script skill_name=work file_path=scripts/run.py positional_args=["git grep -n foo"]
"""
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time

SESSION = 360  # max_time_minutes 6 (the scorer's safety cap)
WARN_AT = 180  # as sq1c2: no source edit by now -> warn
REFUSE_AT = 270  # as sq1c2: no source edit by now -> refuse commands until one exists
FINISH_AT = 300  # finish window opens (with a source edit)
FIXED_GRACE = 60  # finish window opens this long after the repro first printed FIXED
CHECKLIST = False  # sq1c2f6rc: True
NO_BUG_NOTE = False  # sq1c2a6rn: True
CHECKLIST_FILE = ".git/agent/issue.md"
CHECKLIST_SHOW = 1200  # characters of the checklist shown
REPEAT_SHOW = 1500  # characters of the earlier output shown with a repeat refusal
OUT_MAX = 5000  # as the harness's run_command output limit
EDIT_CMD = re.compile(r"sed -i|git apply|\bpatch\b|open\([^)]*['\"][wa]['\"]|write_text\(|>\s*(?!/tmp|/dev/null|&)\S")
FINISH_CMD = re.compile(r"^\s*(git (status|diff|checkout --)|rm )[^;|&`$\n]*(&&\s*git (status|diff)[^;|&`$\n]*)*$")
FIXED_RE = re.compile(r"^\s*FIXED\b", re.M)
SCRIPT_CMD = re.compile(r"\bpython[\d.]*\s+(?!-m\s+pytest)\S")  # runs a script: not grep, sed or pytest
PASS_LINE = re.compile(r"\bpass(ed|es)?\b", re.I)
TMP_PATH = re.compile(r"/tmp/[\w.@+-]+(?:/[\w.@+-]+)*")  # /tmp files a command names
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
    return state["t0"]


def edited(ws):
    """Changed or new source files (not tests, not scratch files)."""
    _, out = sh(["git", "status", "--porcelain", "--untracked-files=all"], ws)
    files = [line[3:].split(" -> ")[-1].strip('"') for line in out.splitlines() if len(line) > 3]
    return [f for f in files if not TEST_RE.search(f) and not os.path.basename(f).startswith("repro")]


def fingerprint(ws, cmd):
    """What a command's output can depend on that the fixer changes: the tree (git status + diff), its scratch files in
    .git/agent, and the /tmp files the command names (/tmp/repro.py). Never a scan of /tmp: r38 walked it and r41
    listed its loose files, and both never refused (0 of 76 / 18 unchanged repeats) - other processes on the machine
    (the parallel task, the harness) keep changing /tmp."""
    h = hashlib.sha1()
    for c in (["git", "status", "--porcelain", "--untracked-files=all"], ["git", "diff"]):
        h.update(sh(c, ws)[1].encode())
    paths = []
    for root, dirs, names in os.walk(os.path.join(ws, ".git", "agent")):
        paths += [os.path.join(root, n) for n in names if n != "clock.json"]
    paths += TMP_PATH.findall(cmd)
    for p in sorted(set(paths))[:2000]:
        try:
            st = os.stat(p)
            h.update(f"{p}:{st.st_size}:{st.st_mtime_ns}".encode())
        except OSError:
            pass
    return h.hexdigest()


def command():
    """The command from positional args (or args {"cmd": "..."}, argv --cmd X)."""
    argv = [a for a in sys.argv[1:] if a != "--"]
    if argv[:1] == ["--cmd"]:
        argv = argv[1:]
    elif argv[:1] and argv[0].startswith("--"):
        argv = argv[1:]
    return " ".join(argv).strip()


def checklist(ws):
    try:
        text = open(os.path.join(ws, CHECKLIST_FILE)).read().strip()
    except OSError:
        return None
    return text or None


def shows_no_bug(cmd, code, out):
    """A repro script that passes with no source edit does not show the bug: exit 0 and a FIXED line, or only "passed"
    lines."""
    lines = [line for line in out.splitlines() if line.strip()]
    return (code == 0 and bool(lines) and bool(SCRIPT_CMD.search(cmd))
            and (bool(FIXED_RE.search(out)) or all(PASS_LINE.search(line) for line in lines)))


def finish_opens(state):
    """Seconds into the session at which the finish window opens (given a source edit)."""
    opens = FINISH_AT
    if "fixed_at" in state:
        opens = min(opens, state["fixed_at"] + FIXED_GRACE)
    return opens


def main():
    ws = workspace()
    state = load_state(ws)
    used = int(time.time() - started(ws, state))
    cmd = command()
    files = edited(ws)
    key = hashlib.sha1(cmd.encode()).hexdigest()
    seen = state.setdefault("seen", {})
    fp = fingerprint(ws, cmd) if cmd else ""
    no_bug = False
    if not cmd:
        body = "NO COMMAND: pass it as positional_args, a list holding one string: the whole shell command."
    elif CHECKLIST and checklist(ws) is None:
        body = (f"REFUSED: first write your issue checklist with write_file {CHECKLIST_FILE}: at most 8 short lines "
                "with every exact name, string, message, type and value from the issue that the hidden tests can "
                "check (copied character for character), and the expected behaviour. Commands run once it exists.")
    elif not files and used >= REFUSE_AT and not EDIT_CMD.search(cmd):
        body = (f"REFUSED: {used} s of {SESSION} used and no source file is edited yet. An unedited tree scores zero; "
                "a best guess can still be corrected. Your next call must be edit_file on the most likely place "
                "(where the wrong behaviour is produced). Commands run again once a source file is edited.")
    elif files and used >= finish_opens(state) and not FINISH_CMD.match(cmd):
        body = (f"REFUSED: FINISH NOW ({used} s of {SESSION} used, source edited: {', '.join(files[:4])}). Only "
                "git status, git diff, git checkout -- TESTFILE and rm SCRATCHFILE run now. Check the diff once, "
                "then reply in plain text with no tool call: one line on what you changed and where.")
    elif key in seen and seen[key]["fp"] == fp:
        earlier = seen[key]["out"]
        body = (f"REFUSED: you ran this exact command at {seen[key]['at']} s and nothing has changed since, so its "
                f"output would be the same. Run something different or act on it. Its output then"
                f"{' (start)' if len(earlier) > REPEAT_SHOW else ''}:\n{earlier[:REPEAT_SHOW]}")
    else:
        code, out, err, timed_out = run_group(cmd, ws, max(5, min(150, SESSION - used - 10)))
        body = (out + (("\n[stderr]\n" + err) if err.strip() else "")).rstrip()
        body += "\n[timed out: the command and everything it started were stopped]" if timed_out else f"\n[exit {code}]"
        if len(body) > OUT_MAX:
            body = body[:OUT_MAX] + f"\n[output cut at {OUT_MAX} characters: narrow the command]"
        seen[key] = {"at": used, "fp": fingerprint(ws, cmd), "out": body}
        files = edited(ws)
        no_bug = NO_BUG_NOTE and not files and shows_no_bug(cmd, code, out)
        if files and "fixed_at" not in state and FIXED_RE.search(body):
            state["fixed_at"] = used
    show = None  # the checklist, at the first source edit and when the repro passes / the finish window opens
    if CHECKLIST and files and checklist(ws):
        for moment, due in (("edit", True), ("finish", "fixed_at" in state or used >= finish_opens(state))):
            if due and moment not in state.setdefault("shown", []):
                state["shown"].append(moment)
                show = checklist(ws)[:CHECKLIST_SHOW]
    if files and used >= finish_opens(state):
        state_txt = "source edited: " + ", ".join(files[:4]) + " | FINISH NOW: git status && git diff, then the one-line reply"
    elif files and "fixed_at" in state:
        state_txt = ("source edited: " + ", ".join(files[:4]) + " | REPRO PASSES: run at most one related test file, "
                     f"then FINISH; from {finish_opens(state)} s only finishing commands run")
    elif files:
        state_txt = "source edited: " + ", ".join(files[:4]) + f" | finish window opens at {FINISH_AT} s"
    elif used >= WARN_AT:
        state_txt = (f"NO SOURCE EDIT YET. Make your best edit now with edit_file; at {REFUSE_AT} s commands are "
                     "refused until a source file is edited")
    else:
        state_txt = "no source edit yet"
    if no_bug:
        state_txt += (" | REPRO SHOWS NO BUG: it passes with no source edit, so it does not test the issue. Change its "
                      "input to what the issue describes and run it again, or make your best edit now")
    save_state(ws, state)
    if show:
        body += ("\n[issue checklist] your " + CHECKLIST_FILE + " - check that your change uses these exact names, "
                 "strings and behaviour:\n" + show)
    print(body + f"\n[clock] {used} s of {SESSION} used | {state_txt}")


if __name__ == "__main__":
    main()
