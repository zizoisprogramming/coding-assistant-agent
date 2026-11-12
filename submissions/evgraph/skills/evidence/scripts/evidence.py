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
r84 (user 2026-11-12 "all in"; scripts/mine_bank/edit_place.py: same task, solved runs edit the real-fix lines 89% vs
failed 49%, failed runs often never read them, worse past line 150 of a file):
  - MAP (evmap / evall): before the per-name sections, the file whose non-test source uses the names most, with its
    size and the defs / classes that use the names, most uses first, as 'first-last Class.name (uses)'. Offline
    (scripts/mine_bank/file_map_offline.py, 103 tasks): it marks the real fix's function in 30% of tasks, 13 of them
    where evidefs's output never pointed inside that function; 42% when the fix sits past line 150.
  - TRACE (evtrace / evall): writes .git/agent/trace.py (scripts/agent_trace/trace.py, embedded below) so the fixer
    can run a check script and see the repository functions it went through (inside .git: never part of the patch).
r85 (evtrace2, user 2026-11-12 "favor few shot ... make this strategy see the fixes that can be applied, tool, prompt"):
  - TRACE_HINT: with TRACE, a line right under the header (so the 4,800-character cut never drops it) says how to run
    a check through the code-path tool. r84: the fixers ran 18-30 plain Python checks per arm and the tool once in 12
    runs; a tool-output line is what this model follows (memory event-triggered-rules-only).
r86 (evgraph, user 2026-11-12 "yes go for option 2": the research-style neighbours instead of the plain map):
  - GRAPH: for a name with a def / class line, its call-graph neighbours in non-test source: 'called from' = the
    innermost defs that hold calls of it (most calls first), 'it calls' = the repository defs its body calls. ARISE
    (arXiv 2605.03117: graph + data-flow tools, function recall@1 +17, Pass@1 +4.7 with a 32B open model) and CoSIL
    (2503.22424: function-level localization by call-graph search) found the real function through these edges, also
    when the issue names a different layer (rich_4079: 'Table' is called from rich/markdown.py, the real file).
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
MAP = False  # r84 evmap / evall: map of the file that uses the names most
MAP_LINES = 8  # defs shown in the map
TRACE = True  # r84 evtrace / evall: install .git/agent/trace.py
GRAPH = True  # r86 evgraph: callers / callees of each named def
GRAPH_LINES = 6  # entries per list
TRACE_HINT = True  # r85 evtrace2: the how-to line for the code-path tool under the header
TRACE_SOURCE = '"""Code path of a script: which functions of this repository it ran, file by file, with their line ranges.\n(r84 evtrace, user 2026-11-12 "all in": failed runs edit the wrong place in the right file; scripts/mine_bank/edit_place.py)\n\n    python3 .git/agent/trace.py /tmp/check.py [args ...]\n    python3 .git/agent/trace.py - <<\'EOF\'\n    ...python code...\n    EOF\n\nThe script runs as usual (its own output and errors are printed first); then a CODE PATH block lists the repository\nfunctions it called (tests, the standard library, installed packages, module and class bodies, comprehensions and\neverything that runs while modules are imported are left out): a \'files:\' line with every file and its function count,\nthen per file (the modules the check script imports first, the rest in first-call order) its functions in call order,\neach as \'first-last name (calls)\', and, if it raised, the deepest repository line on the way. The idea comes from\nSWE-Doctor (runtime evidence of where the failure goes, arXiv 2607.00990) and spectrum-based fault localization:\nsame-task data show solved runs edit the real-fix lines 89% vs failed 49%, and failed runs often never read them.\nInstalled into /workspace/.git/agent/ by the evidence script (inside .git: never part of the patch)."""\nimport io\nimport os\nimport re\nimport runpy\nimport sys\nimport threading\nimport traceback\n\nMAX_FILES = 5\nMAX_FUNCS = 12\nTEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\\.py$|_test\\.py$|(^|/)conftest\\.py$")\n\n\ndef repo_root():\n    here = os.path.dirname(os.path.abspath(__file__))\n    if os.path.basename(here) == "agent" and os.path.basename(os.path.dirname(here)) == ".git":\n        return os.path.dirname(os.path.dirname(here))\n    cur = os.getcwd()\n    while cur != os.path.dirname(cur):\n        if os.path.isdir(os.path.join(cur, ".git")):\n            return cur\n        cur = os.path.dirname(cur)\n    return os.getcwd()\n\n\nROOT = os.path.realpath(repo_root())\nSELF = os.path.realpath(__file__)\ncalls, order, last_line = {}, [], {}\n\n\n_REL = {}\n\n\ndef relevant(fn):\n    """repository-relative path of a code file worth listing, else None (cached: called on every function call)."""\n    if fn in _REL:\n        return _REL[fn]\n    _REL[fn] = r = _relevant(fn)\n    return r\n\n\ndef _relevant(fn):\n    if not fn or fn.startswith("<"):\n        return None\n    p = os.path.realpath(fn)\n    if not p.startswith(ROOT + os.sep) or p == SELF:\n        return None\n    rel = os.path.relpath(p, ROOT)\n    if rel.startswith(".git" + os.sep) or TEST.search(rel) or "site-packages" in rel:\n        return None\n    return rel\n\n\ndef code_end(code):\n    try:\n        return max(l for _, _, l in code.co_lines() if l) or code.co_firstlineno\n    except Exception:\n        return code.co_firstlineno\n\n\nCO_OPTIMIZED = 0x0001  # set for function code; module and class bodies lack it\n\n\ndef during_import(frame):\n    """True when the call happens while a module is being imported (decorators, registrations, constants)."""\n    f, depth = frame.f_back, 0\n    while f is not None and depth < 200:\n        if f.f_code.co_filename.startswith("<frozen importlib"):\n            return True\n        f, depth = f.f_back, depth + 1\n    return False\n\n\ndef prof(frame, event, arg):\n    if event != "call":\n        return\n    code = frame.f_code\n    if not (code.co_flags & CO_OPTIMIZED) or code.co_name.startswith("<"):\n        return  # module bodies, class bodies, comprehensions, lambdas\n    rel = relevant(code.co_filename)\n    if rel is None or during_import(frame):\n        return\n    key = (rel, code.co_firstlineno, code.co_name)\n    if key not in calls:\n        calls[key] = 0\n        order.append(key)\n        last_line[key] = code_end(code)\n    calls[key] += 1\n\n\nSOURCE = [""]  # the check script\'s text: the repository modules it imports are listed first\n\n\ndef script_files():\n    """repository files of the modules the check script imports or names (pkg.mod -> pkg/mod.py or pkg/mod/__init__.py)."""\n    mods = []\n    for a, b in re.findall(r"^\\s*(?:from\\s+([\\w.]+)\\s+import|import\\s+([\\w.]+))", SOURCE[0], re.M):\n        if (a or b) not in mods:\n            mods.append(a or b)  # source order\n    out = []\n    for m in mods:\n        parts = m.split(".")\n        for k in range(len(parts), 0, -1):\n            base = os.path.join(*parts[:k])\n            for cand in (base + ".py", os.path.join(base, "__init__.py")):\n                if os.path.isfile(os.path.join(ROOT, cand)) and cand not in out:\n                    out.append(cand)\n            if any(o.startswith(base) for o in out):\n                break\n    return out\n\n\ndef report(exc):\n    out = ["", "== CODE PATH: functions of this repository the script ran (file: first-last name, calls)"]\n    files = []\n    for rel, _, _ in order:\n        if rel not in files:\n            files.append(rel)\n    first = [f for f in script_files() if f in files]  # the modules the script imports first, then first-call order\n    files = first + [f for f in files if f not in first]\n    if files:\n        counts = {f: sum(1 for k in order if k[0] == f) for f in files}\n        out.append("files: " + ", ".join(f"{f} ({counts[f]})" for f in files[:10]) + (f", ... {len(files) - 10} more" if len(files) > 10 else ""))\n    if not files:\n        out.append("  (none: the script never called code from this repository)")\n    for rel in files[:MAX_FILES]:\n        keys = [k for k in order if k[0] == rel]\n        out.append(f"{rel}:")\n        for k in keys[:MAX_FUNCS]:\n            out.append(f"  {k[1]}-{last_line[k]} {k[2]} ({calls[k]})")\n        if len(keys) > MAX_FUNCS:\n            out.append(f"  ... {len(keys) - MAX_FUNCS} more")\n    if len(files) > MAX_FILES:\n        out.append(f"... {len(files) - MAX_FILES} more files: " + ", ".join(files[MAX_FILES:MAX_FILES + 6]))\n    if exc is not None:\n        tb = [f for f in traceback.extract_tb(exc.__traceback__) if relevant(f.filename)]\n        if tb:\n            f = tb[-1]\n            out.append(f"raised {type(exc).__name__} at {relevant(f.filename)}:{f.lineno} in {f.name}: {(f.line or \'\').strip()[:120]}")\n    sys.stdout.flush()\n    sys.stderr.flush()\n    print("\\n".join(out), flush=True)\n\n\ndef main():\n    args = sys.argv[1:]\n    if not args:\n        print("usage: python3 .git/agent/trace.py /tmp/check.py [args]   or   python3 .git/agent/trace.py - <<\'EOF\' ... EOF")\n        return 2\n    target = args[0]\n    if target == "-":\n        source, name = sys.stdin.read(), "<stdin>"\n        SOURCE[0] = source\n    else:\n        try:\n            source, name = open(target, errors="replace").read(), target\n            SOURCE[0] = source\n        except OSError as e:\n            print(f"cannot read {target}: {e}")\n            return 2\n    sys.argv = [name] + args[1:]\n    sys.path.insert(0, ROOT)\n    if target != "-":\n        sys.path.insert(0, os.path.dirname(os.path.abspath(target)))\n    os.chdir(ROOT) if os.getcwd() != ROOT and not os.path.isdir(os.path.join(os.getcwd(), ".git")) else None\n    exc, code = None, 0\n    threading.setprofile(prof)\n    sys.setprofile(prof)\n    try:\n        g = {"__name__": "__main__", "__file__": name, "__builtins__": __builtins__}\n        exec(compile(source, name, "exec"), g)\n    except SystemExit as e:\n        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)\n    except BaseException as e:\n        exc, code = e, 1\n    finally:\n        sys.setprofile(None)\n        threading.setprofile(None)\n    if exc is not None:\n        traceback.print_exception(type(exc), exc, exc.__traceback__)\n    report(exc)\n    return code\n\n\nif __name__ == "__main__":\n    sys.exit(main())\n'  # filled by the builder (scripts/make_r84_arms.py) with scripts/agent_trace/trace.py
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


def file_map(ws, names, start):
    """MAP lines: the non-test, non-docs Python file whose lines use the names most, its size, and its innermost defs /
    classes holding those uses, most uses first ('first-last Class.name (uses)'); [] when nothing qualifies."""
    import ast
    hits = {}
    for n in names:
        if not re.fullmatch(IDENT, n):
            continue
        for ln in git(ws, ["grep", "-n", "-I", "-w", "-F", "-e", n, "--"] + SRC, start) or []:
            m = re.match(r"(.+?):(\d+):", ln)
            if m:
                hits.setdefault(m.group(1), []).append(int(m.group(2)))
    if not hits:
        return []
    path = max(hits, key=lambda p: (len(hits[p]), -len(p)))
    try:
        text = open(os.path.join(ws, path), errors="replace").read()
        tree = ast.parse(text)
    except (OSError, SyntaxError, ValueError):
        return []
    spans = []

    def walk(node, prefix):
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                q = f"{prefix}.{ch.name}" if prefix else ch.name
                spans.append((ch.lineno, getattr(ch, "end_lineno", ch.lineno), q))
                walk(ch, q)
            else:
                walk(ch, prefix)
    walk(tree, "")
    score = {}
    for line in hits[path]:
        inner = [s for s in spans if s[0] <= line <= s[1]]
        if inner:
            s = min(inner, key=lambda s: s[1] - s[0])
            score[s] = score.get(s, 0) + 1
    if not score:
        return []
    ranked = sorted(score, key=lambda s: (-score[s], s[0]))
    out = [f"== MAP of {path} ({len(text.splitlines())} lines, {len(spans)} defs): the defs that use these names, most uses first"]
    out += [f"  {a}-{b} {q} ({score[(a, b, q)]})" for a, b, q in ranked[:MAP_LINES]]
    if len(ranked) > MAP_LINES:
        out.append(f"  ... {len(ranked) - MAP_LINES} more")
    return out


def install_trace(ws):
    """write .git/agent/trace.py once (inside .git, so never part of the patch)."""
    if not TRACE_SOURCE:
        return
    p = os.path.join(ws, ".git", "agent", "trace.py")
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        if not os.path.exists(p):
            open(p, "w").write(TRACE_SOURCE)
    except OSError:
        pass


_SPANS = {}


def def_spans(ws, path):
    """[(first, last, qualname)] of every def / class in PATH (cached); [] when it does not parse."""
    import ast
    if path in _SPANS:
        return _SPANS[path]
    out = []
    try:
        tree = ast.parse(open(os.path.join(ws, path), errors="replace").read())
    except (OSError, SyntaxError, ValueError):
        _SPANS[path] = out
        return out

    def walk(node, prefix):
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                q = f"{prefix}.{ch.name}" if prefix else ch.name
                out.append((ch.lineno, getattr(ch, "end_lineno", ch.lineno), q, ch))
                walk(ch, q)
            else:
                walk(ch, prefix)
    walk(tree, "")
    _SPANS[path] = out
    return out


def enclosing(ws, path, line):
    inner = [s for s in def_spans(ws, path) if s[0] <= line <= s[1]]
    return min(inner, key=lambda s: s[1] - s[0]) if inner else None


def graph_lines(ws, name, def_path, def_line, start):
    """'called from' and 'it calls' lines for NAME defined at DEF_PATH:DEF_LINE; [] when nothing is found."""
    import ast
    out = []
    calls = git(ws, ["grep", "-n", "-I", "-E", "-e", rf"(^|[^A-Za-z0-9_]){re.escape(name)}[[:space:]]*\(", "--"] + SRC, start) or []
    score = {}
    for ln in calls:
        m = re.match(r"(.+?):(\d+):(.*)", ln)
        if not m or re.match(rf"\s*(async def|def|class)\s+{re.escape(name)}\b", m.group(3)):
            continue
        s = enclosing(ws, m.group(1), int(m.group(2)))
        if s:
            key = (m.group(1), s[0], s[1], s[2])
            score[key] = score.get(key, 0) + 1
    if score:
        ranked = sorted(score, key=lambda k: (-score[k], k[0], k[1]))
        out.append("called from: " + "; ".join(f"{p}:{a}-{b} {q} ({score[(p, a, b, q)]})" for p, a, b, q in ranked[:GRAPH_LINES])
                   + (f"; ... {len(ranked) - GRAPH_LINES} more" if len(ranked) > GRAPH_LINES else ""))
    me = next((s for s in def_spans(ws, def_path) if s[0] <= def_line <= s[1] and s[2].split(".")[-1] == name), None)
    if me is not None:
        called = []
        for n in ast.walk(me[3]):
            if isinstance(n, ast.Call):
                f = n.func
                c = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else None
                if c and c != name and len(c) >= 3 and c not in called and not c.startswith("__"):
                    called.append(c)
        if called:
            pat = "|".join(re.escape(c) for c in called[:40])
            defs = git(ws, ["grep", "-n", "-I", "-E", "-e", rf"^[[:space:]]*(async def|def|class) ({pat})([^A-Za-z0-9_]|$)", "--"] + SRC, start) or []
            seen = []
            for ln in defs:
                m = re.match(r"(.+?):(\d+):\s*(?:async def|def|class)\s+(\w+)", ln)
                if not m:
                    continue
                s = enclosing(ws, m.group(1), int(m.group(2)))
                if s and s[0] == int(m.group(2)) and (m.group(1), s[0]) not in [(x[0], x[1]) for x in seen]:
                    seen.append((m.group(1), s[0], s[1], s[2]))
            seen.sort(key=lambda x: (x[0] != def_path, called.index(x[3].split(".")[-1]) if x[3].split(".")[-1] in called else 99))
            if seen:
                out.append("it calls: " + "; ".join(f"{p}:{a}-{b} {q}" for p, a, b, q in seen[:GRAPH_LINES])
                           + (f"; ... {len(seen) - GRAPH_LINES} more" if len(seen) > GRAPH_LINES else ""))
    return out


def section(ws, name, start):
    out = [f"== {name}"]
    tests = git(ws, ["grep", "-n", "-I", "-F", "-e", name, "--"] + TEST_PATHS, start)
    if tests is None:
        return out + ["  (skipped: time)"]
    out.append(f"tests mentioning it: {len(tests)} lines" + ("" if tests else " (none)"))
    out.extend("  " + short(t) for t in tests[:TEST_LINES])
    if re.fullmatch(IDENT, name):
        defs = git(ws, ["grep", "-n", "-I", "-E", "-e", rf"^[[:space:]]*(async def|def|class) {name}([^A-Za-z0-9_]|$)", "--", "*.py"], start) or []
        if defs:
            out.append("defined at:")
            out.extend("  " + short(d) for d in defs[:DEF_LINES])
            if GRAPH:
                m = re.match(r"(.+?):(\d+):", defs[0])
                if m:
                    out.extend(graph_lines(ws, name, m.group(1), int(m.group(2)), start))
        elif SOURCE_LINES:
            uses = git(ws, ["grep", "-n", "-I", "-w", "-F", "-e", name, "--"] + SRC, start) or []
            if uses:
                out.append(f"used in source: {len(uses)} lines")
                out.extend("  " + short(u) for u in uses[:SRC_LINES])
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
    if TRACE:
        install_trace(ws)
        if TRACE_HINT:
            parts.append("Run check scripts through the code-path tool: python3 .git/agent/trace.py /tmp/check.py (or python3 .git/agent/trace.py - <<'EOF' ... EOF);"
                         " after the script's own output it lists the functions of this repository the check went through, with line ranges.")
    if MAP:
        parts.extend(file_map(ws, names, start))
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
