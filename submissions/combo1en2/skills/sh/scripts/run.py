"""Shell for the screening arms (skill "work", scripts/run.py): pubclock and the no-numbers family (nn36, nn32, nn36c, nn36p).
Runs one shell command in /workspace and enforces the rules below; the switches are set per arm by scripts/make_skill_arms.py.

- Stop: STOP_AFTER s after the last change to a tracked source file only finishing commands run. The first command after
  an edit always runs, so a fix can be checked. edit_file is not gated.
- Late edit: with no source edit from REFUSE_AT s or from the REFUSE_SHELL-th shell call, commands are refused until one
  exists. The shell only sees its own calls: 22 total calls of pub024 are about 11 shell calls and 199 s (108 runs).
- Check: after an edit the status line asks for a related test until one has run.
- WORDS: no seconds in anything this script adds (LOOK, EDIT NOW, CHECK, FINISH instead of a clock).
- CHECKLIST: commands are refused until .git/agent/issue.md exists; it is shown at the first edit and at FINISH.
- PLACES: when an edit touches a new function, list other places that use its name, and tests that mention it.
- LIGHT (nn32rc family, run through run_command after install_run.py): fewer git processes per call (hypothesis: git and the
  skill wrapper are what make the skill shell too slow on the scorer): the start time is kept in the state, the tree is only
  looked at again after a command when it can edit. The command may also come on stdin.
- READS: short reading commands, where NAME [PATH], outline FILE, lines FILE START END, under the same rules.

    run_skill_script skill_name=work file_path=scripts/run.py positional_args=["git grep -n foo"]
"""
import ast
import hashlib
import inspect
import json
import os
import re
import select
import shlex
import signal
import subprocess
import sys
import time

SESSION = 480  # max_time_minutes 8
STOP_AFTER = 10 ** 6  # combo1en: stop rule off; seconds after the last source edit
WARN_AT = 120  # no edit yet: the status line turns to EDIT NOW
WARN_SHELL = 8
REFUSE_AT = 240  # combo1en (nn32's time); no edit yet: commands are refused
REFUSE_SHELL = 12  # combo1en
WORDS = True  # combo1en: [state] LOOK / EDIT NOW / CHECK, no seconds
CHECKLIST = False
PLACES = False
LIGHT = True  # combo1en: fewer git processes per command
READS = False
READ_LINES = 200  # most lines one "lines" command shows
WHERE_LINES = 30  # most matches one "where" command shows
CHECKLIST_FILE = ".git/agent/issue.md"
CHECKLIST_SHOW = 1200
OUT_MAX = 5000  # as the harness's run_command output limit
PLACES_MAX = 10  # lines per name
PLACES_NAMES = 2  # names per edit
PLACES_COMMON = 40  # a name used more often than this says nothing
EDIT_CMD = re.compile(r"sed -i|git apply|\bpatch\b|open\([^)]*['\"][wa]['\"]|write_text\(")
FINISH_CMD = re.compile(r"^\s*(git (status|diff|checkout --)|rm )[^;|&`$\n]*(&&\s*git (status|diff)[^;|&`$\n]*)*$")
TEST_CMD = re.compile(r"pytest|unittest")
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
    if LIGHT and "t_base" in state:
        return state["t_base"]
    code, out = sh(["git", "log", "-1", "--format=%ct", "_swegemma_baseline"], ws)
    if code == 0 and out.strip().isdigit():
        state["t_base"] = int(out.strip())
        return state["t_base"]
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
    """Restart the timer and the check if the source diff changed since the last look. Returns the changed files."""
    files, digest = source_diff(ws)
    if digest != state.get("digest", ""):
        state["digest"] = digest
        state["edit_at"] = now
        state["ran_since_edit"] = 0
        state["tested"] = False
    return files


def command():
    """The command from positional args (or argv --cmd X)."""
    argv = [a for a in sys.argv[1:] if a != "--"]
    if argv[:1] and argv[0].startswith("--"):
        argv = argv[1:]
    text = " ".join(argv).strip()
    if LIGHT and not text:  # python .git/agent/run.py <<'EOF'. Never wait: a silent open stdin must not hang the call
        try:
            if select.select([sys.stdin], [], [], 0.2)[0]:
                text = sys.stdin.read().strip()
        except (OSError, ValueError):
            pass
    return text


def translate(cmd):
    """READS: where NAME [PATH], outline FILE, lines FILE START END -> the shell command; anything else unchanged."""
    if not READS:
        return cmd
    try:
        parts = shlex.split(cmd)
    except ValueError:
        return cmd
    if len(parts) >= 2 and parts[0] == "where":
        paths = " ".join(shlex.quote(p) for p in parts[2:])
        return f"git grep -n -F -- {shlex.quote(parts[1])} {paths} | head -n {WHERE_LINES}"
    if len(parts) == 2 and parts[0] == "outline":
        return f"grep -n -E '^[[:space:]]*(async def|def|class) ' {shlex.quote(parts[1])}"
    if len(parts) == 4 and parts[0] == "lines" and parts[2].isdigit() and parts[3].isdigit():
        first, last = int(parts[2]), min(int(parts[3]), int(parts[2]) + READ_LINES - 1)
        return f"awk 'NR>={first} && NR<={last} {{printf \"%d  %s\\n\", NR, $0}}' {shlex.quote(parts[1])}"
    return cmd


def checklist(ws):
    try:
        text = open(os.path.join(ws, CHECKLIST_FILE)).read().strip()
    except OSError:
        return None
    return text or None


def edited_names(ws, files):
    """Names of the functions and classes whose lines the current diff changes."""
    names = []
    for f in files:
        if not f.endswith(".py"):
            continue
        _, diff = sh(["git", "diff", "-U0", "--", f], ws)
        lines = []
        for m in re.finditer(r"^@@ -\S+ \+(\d+)(?:,(\d+))? @@", diff, re.M):
            first, count = int(m.group(1)), int(m.group(2) or 1)
            lines += range(first, first + max(count, 1))
        try:
            tree = ast.parse(open(os.path.join(ws, f), errors="replace").read())
        except (OSError, SyntaxError, ValueError):
            continue
        defs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
        for ln in lines:
            hits = [n for n in defs if n.lineno <= ln <= n.end_lineno]
            hits.sort(key=lambda n: (isinstance(n, ast.ClassDef), -n.lineno))  # innermost function first
            if hits and not hits[0].name.startswith("__") and hits[0].name not in names:
                names.append(hits[0].name)
    return names


def places(ws, files, state):
    """Other uses of the newly edited names, and tests that mention them. Costs the model no tokens to produce."""
    seen = state.setdefault("places_seen", [])
    out = []
    for name in [n for n in edited_names(ws, files) if n not in seen][:PLACES_NAMES]:
        seen.append(name)
        _, hits = sh(["git", "grep", "-n", "-w", "-F", name, "--", "*.py"], ws)
        src = [h for h in hits.splitlines() if not TEST_RE.search(h.split(":", 1)[0])]
        if len(src) > PLACES_COMMON:
            continue
        tests = sorted({h.split(":", 1)[0] for h in hits.splitlines() if TEST_RE.search(h.split(":", 1)[0])})[:3]
        if len(src) > 1:
            out.append(f"[other places] {name} also appears here. If the same behaviour lives there, change it too:\n"
                       + "\n".join(h[:110] for h in src[:PLACES_MAX]))
        if tests:
            out.append(f"[related tests] {name}: " + " ".join(tests))
    return "\n".join(out)


def status(files, state, used, shell):
    """The last line of every output."""
    since = used - state.get("edit_at", used)
    if not files:
        late = used >= WARN_AT or shell >= WARN_SHELL
        word = ("EDIT NOW: stop reading and make your best edit with edit_file" if late
                else "LOOK: no source edit yet")
    elif since >= STOP_AFTER or state.get("tested"):
        word = "FINISH: git status --short && git diff, then submit_patch. If an output showed your change is wrong, correct it first"
    else:
        word = "CHECK: source edited (" + ", ".join(files[:4]) + "). Run a related test file now"
    return f"[state] {word}" if WORDS else f"[clock] {used} s of {SESSION} used | {word}"


def main():
    ws = workspace()
    state = load_state(ws)
    t0 = started(ws, state)
    used = int(time.time() - t0)
    cmd = translate(command())
    state["shell"] = state.get("shell", 0) + 1
    shell = state["shell"]
    files = note_edit(ws, state, used)
    since = used - state["edit_at"] if files else None
    stopped = bool(files) and since >= STOP_AFTER and state.get("ran_since_edit", 0) >= 1
    late = not files and (used >= REFUSE_AT or shell >= REFUSE_SHELL)
    if not cmd:
        body = "NO COMMAND: pass it as positional_args, a list holding a single string: the whole shell command."
    elif CHECKLIST and checklist(ws) is None:
        body = (f"REFUSED: first write your issue checklist with write_file {CHECKLIST_FILE}: a few short lines with every "
                "exact name, string, message, type and value from the issue that the hidden tests can check (copied "
                "character for character), and the expected behaviour. Commands run once it exists.")
    elif late and not EDIT_CMD.search(cmd):
        state["refused_late"] = state.get("refused_late", 0) + 1
        body = ("REFUSED: no source file is edited yet. An unedited tree scores zero; a best guess can still be corrected. "
                "Your next call must be edit_file on the most likely place, where the wrong behaviour is produced. "
                "Commands run again once a source file is edited.")
    elif stopped and not FINISH_CMD.match(cmd):
        state["refused_stop"] = state.get("refused_stop", 0) + 1
        body = (f"REFUSED: your last source edit ({', '.join(files[:4])}) has had its time. Only git status, git diff, "
                "git checkout -- FILE and rm FILE run now. If an earlier output showed that your change is wrong, "
                "correct it with edit_file now. Otherwise run git status --short && git diff, then call submit_patch.")
    else:
        code, out, err, timed_out = run_group(cmd, ws, max(5, min(150, SESSION - used - 10)))
        body = (out + (("\n[stderr]\n" + err) if err.strip() else "")).rstrip()
        if timed_out:
            body += "\n[timed out: the command and everything it started were stopped]"
        elif WORDS:
            body += "\n[command succeeded]" if code == 0 else "\n[command failed]"
        else:
            body += f"\n[exit {code}]"
        if len(body) > OUT_MAX:
            body = body[:OUT_MAX] + ("\n[output cut: narrow the command]" if WORDS else f"\n[output cut at {OUT_MAX} characters: narrow the command]")
        used = int(time.time() - t0)
        state["ran_since_edit"] = state.get("ran_since_edit", 0) + 1
        ran_test = bool(TEST_CMD.search(cmd))
        if not LIGHT or EDIT_CMD.search(cmd):
            files = note_edit(ws, state, used)
        if ran_test and files:
            state["tested"] = True
    extra = []
    if PLACES and files:
        found = places(ws, files, state)
        if found:
            extra.append(found)
    if CHECKLIST and files and checklist(ws):
        shown = state.setdefault("shown", [])
        finish = state.get("tested") or used - state.get("edit_at", used) >= STOP_AFTER
        for moment, due in (("edit", True), ("finish", finish)):
            if due and moment not in shown:
                shown.append(moment)
                extra.append(f"[issue checklist] your {CHECKLIST_FILE}: check that your change uses these exact names, "
                             "strings and behaviour:\n" + checklist(ws)[:CHECKLIST_SHOW])
                break
    line = status(files, state, used, shell)
    save_state(ws, state)
    print("\n".join([body] + extra + [line]))


if __name__ == "__main__":
    main()
