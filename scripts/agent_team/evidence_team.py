"""Repository evidence for a few exact names from the issue, in one call (arm evid1, scripts/make_mine_arms.py).

Run once per task by the evidence agent through run_skill_script (skill "evidence"), names as positional_args:

    run_skill_script skill_name=evidence file_path=scripts/evidence.py positional_args=["convert_underscores", "Header"]

Why: r60's scouts found good evidence (the right test files, the earlier commits on the buggy lines) but explored for
2-4 minutes. This script does the same fixed searches in seconds, read-only, inside the repository:
  - tests that mention the name (git grep in test files),
  - where the name is defined (def / class lines),
  - the most recent commits that added or removed the name (git log -S) and the changed lines around it in the newest one,
  - changelog lines that mention it.
Every git call has its own timeout and the whole script stops adding sections after DEADLINE seconds.

r90 evteam (scripts/make_r90_arms.py): TEAM_SETUP also prepares the two-fixer team before any search, on the first call
only: git worktrees .git/agent/wt_b (Fixer B's copy: edit_file writes only inside /workspace) and <TMPDIR>/team/wt_0 (a
clean baseline for the vote, scratch; TMPDIR is what '/tmp' means in the agents' commands), and
.git/agent/vote.py (scripts/agent_team/vote.py, embedded below) with .git/agent/team.json (the start time). Everything is
inside .git, so never part of the patch; nothing is printed about it (the stage copies lines of this output).
"""
import inspect
import os
import re
import subprocess
import sys
import time

ONCE = True  # evid2 (r64): True -> a second call is refused (r63: told to make one call, the agent made 2-17)
DONE_FILE = os.path.join(".git", "agent", "evidence_done")  # holds the first result, shown again on a refused call
REPLY = 'Now reply with at most 10 lines of this result, copied exactly, and stop.'  # evid3 (r65) swaps this: the stage's reply becomes its output
TEAM_SETUP = False  # r90 evteam: worktrees wt_b / wt_0 and vote.py, before the searches
VOTE_SOURCE = ''  # filled by the builder (scripts/make_r90_arms.py) with scripts/agent_team/vote.py
DEADLINE = 8  # r76: seconds for all sections (evid3: 40; large private repos made it the stage's main cost)
CALL_TIMEOUT = 4  # seconds per git call (evid3: 12)
MAX_NAMES = 5
OUT_MAX = 4800  # characters; the harness shows about 5000
TEST_LINES = 6
DEF_LINES = 3
COMMITS = 5
HUNK_TRIES = 5  # changed lines come from the newest of the first HUNK_TRIES commits that has some
HUNK_LINES = 18
WINDOW = 3  # context lines around each changed line that has the name
LOG_LINES = 3
LINE_MAX = 150
TEST_PATHS = [":(glob)**/test/**/*.py", ":(glob)**/tests/**/*.py", ":(glob)**/testing/**/*.py", ":(glob)**/test_*.py", ":(glob)**/*_test.py"]
PY = [":(glob)**/*.py"]  # history and changed lines: Python files only (docs translations drown everything else)
LOG_PATHS = [":(glob)**/CHANGELOG*", ":(glob)**/CHANGES*", ":(glob)**/HISTORY*", ":(glob)**/NEWS*", ":(glob)**/release-notes*",
             ":(glob)**/changelog*"]


def workspace():
    """The repository root. The skill wrapper chdirs into a temp dir, so look for the directory it started in."""
    for frame in inspect.stack():
        cwd = frame.frame.f_locals.get("_orig_cwd")
        if isinstance(cwd, str) and os.path.isdir(os.path.join(cwd, ".git")):
            return cwd
    for cand in (os.environ.get("PYTHONPATH", "").split(os.pathsep)[0], "/workspace", os.getcwd()):
        if cand and os.path.isdir(os.path.join(cand, ".git")):
            return cand
    sys.exit("repository not found")


def git(ws, args, start):
    """stdout lines of one git call, [] on error, timeout or when the deadline has passed."""
    left = DEADLINE - (time.time() - start)
    if left < 1:
        return None
    try:
        r = subprocess.run(["git", "-c", "core.quotepath=off"] + args, cwd=ws, capture_output=True, text=True,
                           timeout=min(CALL_TIMEOUT, left), stdin=subprocess.DEVNULL, errors="replace")
    except subprocess.TimeoutExpired:
        return []
    return r.stdout.splitlines() if r.returncode in (0, 1) else []


def short(line):
    line = line.rstrip()
    return line if len(line) <= LINE_MAX else line[:LINE_MAX] + " ..."


def names_from_args():
    raw = [a for a in sys.argv[1:] if a != "--"]
    names = []
    for a in raw:
        for part in re.split(r"[\n,]", a):
            n = part.strip().strip("`'\"").strip()
            if len(n) >= 3 and n not in names:
                names.append(n)
    return names[:MAX_NAMES]


def newest_hunks(ws, commit, name, start):
    """Changed lines that contain NAME in COMMIT (Python source, not tests), with WINDOW lines around each, at most
    HUNK_LINES. Files the commit created or deleted are skipped: a whole new file says nothing about the change."""
    lines = git(ws, ["show", "--format=", "-U3", "--no-color", commit, "--"] + PY
                + [":(exclude,glob)" + p[len(":(glob)"):] for p in TEST_PATHS], start)
    if not lines:
        return []
    out, cur_file, hunk, skip = [], None, [], False

    def flush():
        if skip or not hunk:
            return
        hits = [i for i, h in enumerate(hunk) if h[:1] in "+-" and name in h]
        keep = sorted({j for i in hits for j in range(max(0, i - WINDOW), min(len(hunk), i + WINDOW + 1))})
        if keep:
            out.append(f"  {cur_file}:")
            prev = None
            for j in keep:
                if prev is not None and j != prev + 1:
                    out.append("    ...")
                out.append("    " + short(hunk[j]))
                prev = j

    for ln in lines:
        if ln.startswith("diff --git"):
            flush()
            hunk, skip, cur_file = [], False, None
        elif ln.startswith(("new file", "deleted file")):
            skip = True
        elif ln.startswith("+++ "):
            cur_file = ln[6:] if ln.startswith("+++ b/") else ln[4:]
        elif ln.startswith(("index ", "--- ", "similarity", "rename ")):
            continue
        elif ln.startswith("@@"):
            flush()
            hunk = []
        else:
            hunk.append(ln)
    flush()
    return out[:HUNK_LINES]


_RANGE = []


def recent(ws, start):
    """r76: git log -S only over the last 500 commits (the whole history is slow on large repositories)."""
    if not _RANGE:
        revs = git(ws, ["rev-list", "--max-count=500", "HEAD"], start) or []
        _RANGE.append([revs[-1] + "..HEAD"] if len(revs) == 500 else [])
    return _RANGE[0]


def section(ws, name, start):
    out = [f"== {name}"]
    tests = git(ws, ["grep", "-n", "-I", "-F", "-e", name, "--"] + TEST_PATHS, start)
    if tests is None:
        return out + ["  (skipped: time)"]
    out.append(f"tests mentioning it: {len(tests)} lines" + ("" if tests else " (none)"))
    out.extend("  " + short(t) for t in tests[:TEST_LINES])
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        defs = git(ws, ["grep", "-n", "-I", "-E", "-e", rf"^[[:space:]]*(async def|def|class) {name}([^A-Za-z0-9_]|$)", "--", "*.py"], start) or []
        if defs:
            out.append("defined at:")
            out.extend("  " + short(d) for d in defs[:DEF_LINES])
    log = git(ws, ["log", "-S", name, "--no-merges", "--format=%h %ad %s", "--date=short", f"-n{COMMITS}"] + recent(ws, start) + ["--"] + PY, start)
    if log is None:
        return out + ["  (history skipped: time)"]
    if log:
        out.append("commits that added or removed it (newest first):")
        out.extend("  " + short(c) for c in log)
        for c in log[:HUNK_TRIES]:
            hunks = newest_hunks(ws, c.split()[0], name, start)
            if hunks:
                out.append(f"what {c.split()[0]} changed around it:")
                out.extend(hunks)
                break
    else:
        out.append("commits that added or removed it: none found")
    notes = git(ws, ["grep", "-n", "-I", "-i", "-F", "-e", name, "--"] + LOG_PATHS, start) or []
    if notes:
        out.append("changelog:")
        out.extend("  " + short(n) for n in notes[:LOG_LINES])
    return out


def team_setup(ws):
    """r90 evteam: Fixer B's copy, the vote's clean baseline and vote.py (once; retried, never fatal)."""
    agent = os.path.join(ws, ".git", "agent")
    if os.path.exists(os.path.join(agent, "team.json")):
        return
    os.makedirs(agent, exist_ok=True)
    if VOTE_SOURCE:
        with open(os.path.join(agent, "vote.py"), "w") as f:
            f.write(VOTE_SOURCE)
    r = subprocess.run(["git", "rev-parse", "-q", "--verify", "_swegemma_baseline"], cwd=ws, capture_output=True)
    ref = "_swegemma_baseline" if r.returncode == 0 else "HEAD"
    made = []
    import tempfile  # the harness maps "/tmp" in commands to TMPDIR; Python must use the same directory
    tmp = tempfile.gettempdir()
    for path in (os.path.join(agent, "wt_b"), os.path.join(tmp, "team", "wt_0")):  # wt_0: read-only scratch, out of A's searches
        os.makedirs(os.path.dirname(path), exist_ok=True)
        for _ in range(3):
            if os.path.exists(os.path.join(path, ".git")):
                break
            try:
                subprocess.run(["git", "worktree", "add", "--detach", "-f", path, ref], cwd=ws, capture_output=True,
                               timeout=60, stdin=subprocess.DEVNULL)
            except subprocess.TimeoutExpired:
                pass
        made.append(os.path.exists(os.path.join(path, ".git")))
    with open(os.path.join(agent, "team.json"), "w") as f:
        f.write('{"t0": %r, "wt_b": %s, "wt_0": %s}' % (time.time(), str(made[0]).lower(), str(made[1]).lower()))
    os.makedirs(os.path.join(tmp, "b"), exist_ok=True)  # Fixer B's scratch dir (its prompt: /tmp/b)


def main():
    start = time.time()
    if TEAM_SETUP:
        try:
            team_setup(workspace())
        except Exception:  # noqa: BLE001  the evidence still runs
            pass
    start = time.time()  # the searches' deadline starts after the team set-up
    names = names_from_args()
    if not names:
        print("NO NAMES: pass 2 to 5 exact names from the issue as positional_args, for example "
              "[\"function_name\", \"ClassName\", \"option_name\"].")
        return
    ws = workspace()
    done = os.path.join(ws, DONE_FILE)
    if ONCE and os.path.exists(done):  # also after the harness re-runs the stage with no history: show the result again
        print("ALREADY DONE: the search already ran and a second call is refused. Its result was:\n"
              + open(done, errors="replace").read() + "\n" + REPLY)
        return
    parts = [f"REPOSITORY EVIDENCE for {', '.join(names)} (read-only searches; the issue stays the specification)"]
    for n in names:
        parts.extend(section(ws, n, start))
    text = "\n".join(parts)
    if len(text) > OUT_MAX:
        text = text[:OUT_MAX] + "\n[cut]"
    if ONCE:
        os.makedirs(os.path.dirname(done), exist_ok=True)
        open(done, "w").write(text)
        text += "\nThis was the only search: a second call is refused. " + REPLY
    print(text + f"\n[done in {time.time() - start:.0f} s]")


if __name__ == "__main__":
    main()
