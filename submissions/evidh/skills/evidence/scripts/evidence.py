"""Repository evidence for a few exact names from the issue, in one call (r79 arms evidd / evide, scripts/make_evid_arms.py).

Run once per task by the evidence agent through run_skill_script (skill "evidence"), names as positional_args:

    run_skill_script skill_name=evidence file_path=scripts/evidence.py positional_args=["convert_underscores", "Header"]

Fixed searches in seconds, read-only, inside the repository, for each name:
  - tests that mention it (git grep in test files),
  - where it is defined (def / class lines),
  - SOURCE_LINES (evide): when it has no def / class line (a parameter, option or attribute), where non-test source uses it,
  - the most recent commits that added or removed it (git log -S over the WHOLE history) and the changed lines around it
    in the newest one that has some,
  - changelog lines that mention it.

r79 changes from evidc's script (mined 2026-11-11, scripts/mine_bank/evidence_reads.py over 106 evidence-stage runs):
  - evidc limited git log -S to the last 500 commits. That cut the "what X changed around it" block in 5 of 16 dev16 tasks
    (fastapi_14419, fastapi_15589, fastapi_14306, rich_3521, rich_3882); on 14419 / 15589 evidc's output never reached the
    gold file (0/8 runs) where evid3's full-history search did (8/8). The whole history costs 0.2-0.6 s on the local
    snapshots (4,300-7,200 commits), so the limit is gone; a git call that runs out of time now keeps the lines it printed
    (git flushes per commit with GIT_FLUSH=1) instead of returning nothing.
  - names: "Segment.split_cells" -> "split_cells" (only when the last part is specific: it has an underscore or 6+
    characters; "Prompt.ask" stays whole because git log -S matches substrings and "ask" hits "task"), "foo()" -> "foo",
    phrases with spaces dropped when a real name is left (17 of 177 chosen names were dotted or phrases; git grep -F found
    tests for them, def / history never).
r83 (evidh, user 2026-11-12 "build": get the missing issue information from git history; scripts/mine_bank/fix_line_age.py):
  - RECENT: for the code of each name (its def / class body, or the source lines that use it) git blame over the last
    RECENT commits only, and when some of that code was written there, show the newest such commit (hash, date, how many
    commits before this checkout, message) and up to RECENT_LINES lines it wrote. On 109 public tasks the newest line a
    real fix changes was written within 50 commits in 22% and within 300 in 52%: a regression or a just-added feature,
    and that commit is the closest thing to the missing report the repository holds. The range keeps blame cheap: lines
    older than the range are left to the boundary and never walked back. git blame also counts the root commit as a
    boundary, so a short history's initial import is never shown.
Every git call has its own timeout and the script stops adding sections after DEADLINE seconds.
"""
import inspect
import os
import re
import selectors
import subprocess
import sys
import time

ONCE = True  # evid2 (r64): a second call is refused (r63: told to make one call, the agent made 2-17)
DONE_FILE = os.path.join(".git", "agent", "evidence_done")  # holds the first result, shown again on a refused call
REPLY = 'Now reply with at most 10 lines of this result, copied exactly, and stop.'
DEADLINE = 8  # seconds for all sections (evidc 8, evid3 40)
CALL_TIMEOUT = 4  # seconds per git call; a call that runs out keeps what it printed
SOURCE_LINES = True  # evide: names with no def / class line get the non-test source lines that use them
MAX_NAMES = 5
RECENT = 300  # r83 evidh: blame each name's code over the last RECENT commits and show the newest commit that wrote some of it; 0 = off
RECENT_LINES = 4  # lines that commit wrote, shown
BLOCK_MAX = 150  # lines of a def / class body blamed
OUT_MAX = 4800  # characters; the harness shows about 5000
TEST_LINES = 6
DEF_LINES = 3
SRC_LINES = 4
COMMITS = 5
HUNK_TRIES = 5  # changed lines come from the newest of the first HUNK_TRIES commits that has some
HUNK_LINES = 18
WINDOW = 3  # context lines around each changed line that has the name
LOG_LINES = 3
LINE_MAX = 150
IDENT = r"[A-Za-z_][A-Za-z0-9_]*"
TEST_PATHS = [":(glob)**/test/**/*.py", ":(glob)**/tests/**/*.py", ":(glob)**/testing/**/*.py", ":(glob)**/test_*.py", ":(glob)**/*_test.py"]
NOT_TESTS = [":(exclude,glob)" + p[len(":(glob)"):] for p in TEST_PATHS]
PY = [":(glob)**/*.py"]  # history and changed lines: Python files only (docs translations drown everything else)
SRC = PY + NOT_TESTS + [":(exclude,glob)docs/**", ":(exclude,glob)docs_src/**", ":(exclude,glob)**/examples/**"]
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


def run_stream(argv, cwd, timeout):
    """(complete stdout lines, finished, returncode). Reads as the command prints; at the timeout the command is killed and
    the complete lines printed so far are kept (a cut last line is dropped)."""
    env = dict(os.environ, GIT_FLUSH="1", GIT_PAGER="cat", PAGER="cat", GIT_TERMINAL_PROMPT="0")
    try:
        p = subprocess.Popen(argv, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, env=env)
    except OSError:
        return [], True, 127
    end = time.time() + timeout
    buf, finished = bytearray(), False
    sel = selectors.DefaultSelector()
    sel.register(p.stdout, selectors.EVENT_READ)
    try:
        while True:
            left = end - time.time()
            if left <= 0:
                break
            if not sel.select(left):
                continue
            chunk = os.read(p.stdout.fileno(), 65536)
            if not chunk:
                finished = True
                break
            buf += chunk
    finally:
        sel.close()
        if not finished:
            p.kill()
        try:
            p.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass
        p.stdout.close()
    text = buf.decode("utf-8", errors="replace")
    lines = text.splitlines()
    if not finished and lines and not text.endswith("\n"):
        lines = lines[:-1]
    return lines, finished, p.returncode


def git(ws, args, start):
    """stdout lines of one git call: [] on error, what it printed before its timeout, None once the deadline has passed."""
    left = DEADLINE - (time.time() - start)
    if left < 1:
        return None
    lines, finished, code = run_stream(["git", "-c", "core.quotepath=off"] + args, ws, min(CALL_TIMEOUT, left))
    if finished and code not in (0, 1):
        return []
    return lines


def short(line):
    line = line.rstrip()
    return line if len(line) <= LINE_MAX else line[:LINE_MAX] + " ..."


def names_from_args(argv=None):
    raw = [a for a in (sys.argv[1:] if argv is None else argv) if a != "--"]
    names = []
    for a in raw:
        for part in re.split(r"[\n,]", str(a)):
            n = part.strip().strip("`'\"").strip()
            n = re.sub(r"\(\)$", "", n)  # convert() -> convert
            last = n.rsplit(".", 1)[-1]
            if re.fullmatch(rf"{IDENT}(\.{IDENT})+", n) and ("_" in last.strip("_") or len(last) >= 6):
                n = last  # Segment.split_cells -> split_cells; Prompt.ask stays whole (git log -S matches substrings: ask ~ task)
            if len(n) >= 3 and n not in names:
                names.append(n)
    if any(re.fullmatch(IDENT, n) for n in names):  # phrases only when nothing better was given
        names = [n for n in names if not re.search(r"\s", n)]
    return names[:MAX_NAMES]


def newest_hunks(ws, commit, name, start):
    """Changed lines that contain NAME in COMMIT (Python source, not tests), with WINDOW lines around each, at most
    HUNK_LINES. Files the commit created or deleted are skipped: a whole new file says nothing about the change."""
    lines = git(ws, ["show", "--format=", "-U3", "--no-color", commit, "--"] + PY + NOT_TESTS, start)
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


def block_end(ws, path, line):
    """Last line of the def / class that starts at LINE of PATH: the line before the next non-blank line indented no
    deeper than the def line (decorators and the def line itself count), at most BLOCK_MAX lines."""
    try:
        text = open(os.path.join(ws, path), errors="replace").read().splitlines()
    except OSError:
        return line
    ind = len(text[line - 1]) - len(text[line - 1].lstrip()) if 0 < line <= len(text) else 0
    end = line
    for i in range(line, min(len(text), line - 1 + BLOCK_MAX)):
        t = text[i]
        if t.strip() and len(t) - len(t.lstrip()) <= ind:
            break
        end = i + 1
    return end


_RANGE = {}


def recent_range(ws, start):
    """'HEAD~RECENT..HEAD' when the history is that deep, else 'HEAD' (blame everything)."""
    if "r" not in _RANGE:
        deep = git(ws, ["rev-parse", "--verify", "-q", f"HEAD~{RECENT}"], start)
        _RANGE["r"] = f"HEAD~{RECENT}..HEAD" if deep else "HEAD"
    return _RANGE["r"]


def blame_recent(ws, path, a, b, start):
    """[(commit, committer_time, summary, line_no, text)] for lines A..B of PATH written within the recent range
    (boundary lines dropped)."""
    lines = git(ws, ["blame", "--porcelain", "-L", f"{a},{b}", recent_range(ws, start), "--", path], start)
    if not lines:
        return []
    info, out, cur, cur_line = {}, [], None, None
    for ln in lines:
        m = re.match(r"([0-9a-f]{40}) \d+ (\d+)", ln)
        if m:
            cur, cur_line = m.group(1), int(m.group(2))
            info.setdefault(cur, {})
        elif ln.startswith("\t") and cur:
            out.append((cur, cur_line, ln[1:]))
        elif cur and " " in ln:
            k, v = ln.split(" ", 1)
            info[cur].setdefault(k, v)
        elif cur and ln == "boundary":
            info[cur]["boundary"] = "1"
    return [(c, int(info[c].get("committer-time", 0)), info[c].get("summary", ""), n, t) for c, n, t in out
            if "boundary" not in info[c] and info[c].get("committer-time")]


def recent_lines(ws, spots, start, shown):
    """SPOTS = [(path, first, last)]: the newest commit within the recent range that wrote some of those lines, as output
    lines; [] when none. SHOWN: commits already printed for an earlier name (printed again as one line only)."""
    hits = []
    for path, a, b in spots:
        hits += [(c, tm, s, path, n, t) for c, tm, s, n, t in blame_recent(ws, path, a, b, start)]
    if not hits:
        return []
    c, tm, summ = max(hits, key=lambda h: h[1])[:3]
    if c in shown:
        return [f"changed recently: {c[:9]} (the same commit as above)"]
    shown.add(c)
    back = git(ws, ["rev-list", "--count", f"{c}..HEAD"], start) or ["?"]
    date = time.strftime("%Y-%m-%d", time.gmtime(tm))
    out = [f"changed recently: {c[:9]} {date}, {back[0]} commits before this checkout: {short(summ)}", "  lines it wrote:"]
    out += [f"  {p}:{n}: " + short(t.strip()) for cc, _, _, p, n, t in hits if cc == c][:RECENT_LINES]
    return out


def section(ws, name, start, shown=None):
    out = [f"== {name}"]
    tests = git(ws, ["grep", "-n", "-I", "-F", "-e", name, "--"] + TEST_PATHS, start)
    if tests is None:
        return out + ["  (skipped: time)"]
    out.append(f"tests mentioning it: {len(tests)} lines" + ("" if tests else " (none)"))
    out.extend("  " + short(t) for t in tests[:TEST_LINES])
    if re.fullmatch(IDENT, name):
        defs = git(ws, ["grep", "-n", "-I", "-E", "-e", rf"^[[:space:]]*(async def|def|class) {name}([^A-Za-z0-9_]|$)", "--", "*.py"], start) or []
        spots = []
        if defs:
            out.append("defined at:")
            out.extend("  " + short(d) for d in defs[:DEF_LINES])
            m = re.match(r"(.+?):(\d+):", defs[0])
            if m:
                spots = [(m.group(1), int(m.group(2)), block_end(ws, m.group(1), int(m.group(2))))]
        elif SOURCE_LINES:
            uses = git(ws, ["grep", "-n", "-I", "-w", "-F", "-e", name, "--"] + SRC, start) or []
            if uses:
                out.append(f"used in source: {len(uses)} lines")
                out.extend("  " + short(u) for u in uses[:SRC_LINES])
                for u in uses[:SRC_LINES]:
                    m = re.match(r"(.+?):(\d+):", u)
                    if m:
                        spots.append((m.group(1), int(m.group(2)), int(m.group(2))))
        if RECENT and spots:
            out.extend(recent_lines(ws, spots, start, shown if shown is not None else set()))
    log = git(ws, ["log", "-S", name, "--no-merges", "--format=%h %ad %s", "--date=short", f"-n{COMMITS}", "--"] + PY, start)
    if log is None:
        return out + ["  (history skipped: time)"]
    log = [c for c in log if re.match(r"[0-9a-f]{7,40} ", c)]
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


def main():
    start = time.time()
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
    shown = set()
    for n in names:
        parts.extend(section(ws, n, start, shown))
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
