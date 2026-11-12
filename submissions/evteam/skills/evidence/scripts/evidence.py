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
TEAM_SETUP = True  # r90 evteam: worktrees wt_b / wt_0 and vote.py, before the searches
VOTE_SOURCE = '"""The two-fixer team\'s vote (r90 evteam, user 2026-11-12 "i want to try everything": lead 2 of\ndocs/RESEARCH_PROBLEMS_2026-11-12.md, the crash-free wait-for-all team).\n\n    python3 .git/agent/vote.py done a     Fixer A (works in /workspace) at the end of its work\n    python3 .git/agent/vote.py done b     Fixer B (works in /workspace/.git/agent/wt_b) at the end of its work\n    run_skill_script team scripts/vote.py the coordinator, after the team returns (MODE "final": vote now if needed)\n\nWhy it is a fixer\'s own last command and not a separate step: the harness\'s call budget is shared by both fixers and\nthe coordinator, and only submit_patch / get_status are free, so a vote made after the team returns is refused in\nthe common case (both fixers spend the budget). A fixer\'s \'done\' call is a call it makes anyway in place of the\nfinal `git status && git diff` (this script prints them). When the second fixer reports done, the vote runs at once.\n\nRules (scripts/agent_team/judge.py, from the 2026-10-29 picker study on 195 + 165 candidate patches over 40 tasks):\n  1. an empty source patch is never picked; A empty and B not -> B;\n  2. a patch that makes more existing tests fail than no patch does is dropped, unless both do;\n  3. the higher check score: the fixers\' own scripts in /tmp (A) and /tmp/b (B) written since setup run on the\n     baseline and on each candidate: +1 per script that goes from failing to passing, +1 if its output gains\n     FIXED/PASS-like words, +1 if it loses BUG/FAIL/Traceback-like words, -1 per script that goes from passing to failing;\n  4. ties: A (already in place).\nThe winner ends up in /workspace (the only tree the harness grades); A\'s tree is kept unless B wins; if B\'s patch\ndoes not apply, A\'s is put back. Never touches anything outside /workspace and /tmp; always exits 0."""\nimport hashlib\nimport json\nimport os\nimport re\nimport subprocess\nimport sys\nimport tempfile\nimport time\n\nMODE = None  # the builder writes the coordinator\'s skill copy with MODE "final"\n\n\ndef _workspace():\n    here = os.path.dirname(os.path.abspath(__file__))\n    if os.path.basename(here) == "agent" and os.path.basename(os.path.dirname(here)) == ".git":\n        return os.path.dirname(os.path.dirname(here))\n    import inspect\n    for frame in inspect.stack():\n        cwd = frame.frame.f_locals.get("_orig_cwd")\n        if isinstance(cwd, str) and os.path.isdir(os.path.join(cwd, ".git")):\n            return cwd\n    for cand in (os.environ.get("PYTHONPATH", "").split(os.pathsep)[0], "/workspace", os.getcwd()):\n        if cand and os.path.isdir(os.path.join(cand, ".git")):\n            return cand\n    return os.getcwd()\n\n\nWS = _workspace()\nHERE = os.path.join(WS, ".git", "agent")\nSTATE = os.path.join(HERE, "vote_state.json")\n# The fixers write "/tmp/..." in commands; the harness maps that to the sandbox\'s temp dir (TMPDIR) in commands only,\n# so this script uses tempfile.gettempdir() (= /tmp in the scorer\'s container). VOTE_*: tests only.\nTMP = tempfile.gettempdir()\nSCRATCH = {"a": os.environ.get("VOTE_SCRATCH_A", TMP), "b": os.environ.get("VOTE_SCRATCH_B", os.path.join(TMP, "b"))}\nBASE = os.environ.get("VOTE_BASE", os.path.join(TMP, "team", "wt_0"))  # made by the evidence script (outside Fixer A\'s searches)\nTEST_TIMEOUT, CHECK_TIMEOUT, TESTS_MAX, CHECKS_MAX = 40, 20, 3, 3\nTEST_RE = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\\.py$|_test\\.py$|(^|/)conftest\\.py$|(^|/)pytest\\.ini$")\nPOS = re.compile(r"\\b(FIXED|PASS(ED)?|SUCCESS|WORKS|OK)\\b|correct", re.I)\nNEG = re.compile(r"\\b(BUG|FAIL(ED|URE)?|NOT FIXED|STILL|REPRODUCED|WRONG|ERROR|Traceback|AssertionError|MISMATCH)\\b", re.I)\n\n\ndef sh(args, cwd, timeout=60):\n    try:\n        r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL,\n                           errors="replace")\n        return r.returncode, r.stdout, r.stderr\n    except subprocess.TimeoutExpired:\n        return -9, "", "timed out"\n\n\ndef ref():\n    return "_swegemma_baseline" if sh(["git", "rev-parse", "-q", "--verify", "_swegemma_baseline"], WS)[0] == 0 else "HEAD"\n\n\ndef root_of(x):\n    return WS if x == "a" else os.path.join(HERE, "wt_b")\n\n\ndef is_tree(p):\n    return os.path.exists(os.path.join(p, ".git"))\n\n\ndef patch_of(root):\n    """The candidate\'s source patch (test files, .git and the harness\'s .adk_exec_*.py skill wrappers left out); \'\' if the\n    tree is missing. New files are counted through a throw-away copy of the index, so the real index never changes."""\n    if not is_tree(root):\n        return ""\n    _, idx, _ = sh(["git", "rev-parse", "--git-path", "index"], root)\n    idx = os.path.join(root, idx.strip()) if idx.strip() and not os.path.isabs(idx.strip()) else idx.strip()\n    fd, tmp_idx = tempfile.mkstemp(prefix="vote_idx_")\n    os.close(fd)\n    try:\n        if idx and os.path.exists(idx):\n            with open(idx, "rb") as src, open(tmp_idx, "wb") as dst:\n                dst.write(src.read())\n        else:\n            os.remove(tmp_idx)\n        env = {**os.environ, "GIT_INDEX_FILE": tmp_idx}\n        subprocess.run(["git", "add", "-A", "-N", "."], cwd=root, env=env, capture_output=True, timeout=60, stdin=subprocess.DEVNULL)\n        r = subprocess.run(["git", "diff", "--binary", ref() if root == WS else "HEAD"], cwd=root, env=env, capture_output=True,\n                           text=True, timeout=60, stdin=subprocess.DEVNULL, errors="replace")\n        out = r.stdout\n    finally:\n        if os.path.exists(tmp_idx):\n            os.remove(tmp_idx)\n    keep = []\n    for block in re.split(r"(?m)^(?=diff --git )", out):\n        m = re.match(r"diff --git a/(\\S+) b/(\\S+)", block)\n        if m and not TEST_RE.search(m.group(2)) and not m.group(2).startswith(".git/") and not os.path.basename(m.group(2)).startswith(".adk_exec_"):\n            keep.append(block)\n    return "".join(keep)\n\n\ndef digest(p):\n    return hashlib.sha1(p.encode("utf-8", "replace")).hexdigest()[:12]\n\n\ndef changed_sources(patch):\n    return [f for f in re.findall(r"^\\+\\+\\+ b/(\\S+)", patch, re.M) if f.endswith(".py")]\n\n\ndef select_tests(base, sources):\n    """Existing test files that import a changed module or are named after it (at most TESTS_MAX)."""\n    scored = []\n    for top in ("tests", "test", "testing"):\n        for dirpath, _, files in os.walk(os.path.join(base, top)):\n            for fn in files:\n                if not (fn.startswith("test_") and fn.endswith(".py")):\n                    continue\n                path = os.path.join(dirpath, fn)\n                try:\n                    text = open(path, encoding="utf-8", errors="replace").read()\n                except OSError:\n                    continue\n                s = 0\n                for src in sources:\n                    mod = src[:-3].replace("/", ".").removesuffix(".__init__")\n                    if mod.startswith("src."):\n                        mod = mod[4:]\n                    pkg, _, stem = mod.rpartition(".")\n                    if re.search(rf"\\b(import|from)\\s+{re.escape(mod)}\\b", text) or (\n                            pkg and re.search(rf"from\\s+{re.escape(pkg)}\\s+import\\s+[^\\n]*\\b{re.escape(stem)}\\b", text)):\n                        s += 2\n                    if stem and stem not in ("__init__", "utils", "main") and stem in fn:\n                        s += 3\n                if s:\n                    scored.append((-s, len(text), os.path.relpath(path, base)))\n    return [p for _, _, p in sorted(scored)[:TESTS_MAX]]\n\n\ndef env_for(root):\n    env = {k: v for k, v in os.environ.items() if k != "PYTHONSAFEPATH"}\n    paths = [root] + ([os.path.join(root, "src")] if os.path.isdir(os.path.join(root, "src")) else [])\n    env["PYTHONPATH"] = os.pathsep.join(paths + [env.get("PYTHONPATH", "")])\n    env["PYTHONDONTWRITEBYTECODE"] = "1"\n    return env\n\n\ndef run_all(jobs, timeout):\n    """jobs: {key: (args, cwd, env)} run at the same time; -> {key: (exit, out, err)}."""\n    procs, res = {}, {}\n    for k, (args, cwd, env) in jobs.items():\n        procs[k] = subprocess.Popen(args, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,\n                                    stderr=subprocess.PIPE, text=True, errors="replace")\n    end = time.time() + timeout\n    for k, p in procs.items():\n        try:\n            out, err = p.communicate(timeout=max(1, end - time.time()))\n            res[k] = (p.returncode, out[-800:], err[-800:])\n        except subprocess.TimeoutExpired:\n            p.kill()\n            p.communicate()\n            res[k] = ("timeout", "", "")\n    return res\n\n\ndef counts(out):\n    """(failing, passing) from pytest\'s summary line; None when there is none (pytest missing, crashed, timed out)."""\n    m = {k: int(v) for v, k in re.findall(r"(\\d+) (passed|failed|errors?)", out or "")}\n    if not m:\n        return None\n    return m.get("failed", 0) + m.get("error", 0) + m.get("errors", 0), m.get("passed", 0)\n\n\ndef check_scripts(t0):\n    """The fixers\' own check scripts written since setup: /tmp/*.py (A) and /tmp/b/*.py (B), newest first."""\n    found = []\n    for d in SCRATCH.values():\n        try:\n            names = os.listdir(d)\n        except OSError:\n            continue\n        for fn in names:\n            p = os.path.join(d, fn)\n            if fn.endswith(".py") and os.path.isfile(p) and not fn.startswith(("judge_", "vote_", ".adk_exec")):\n                try:\n                    if os.path.getmtime(p) >= t0 - 5 and os.path.getsize(p) < 20000:\n                        found.append((os.path.getmtime(p), p))\n                except OSError:\n                    pass\n    return [p for _, p in sorted(found, reverse=True)[:CHECKS_MAX]]\n\n\ndef script_for(code, root):\n    """The script as it would run in root: paths of the repository and of B\'s copy point at root."""\n    for ws in (WS, "/workspace"):  # the sandbox writes its real path into heredoc scripts; the scorer\'s is /workspace\n        code = code.replace(ws + "/.git/agent/wt_b", root)\n    code = re.sub(r"(?<![\\w/])\\.git/agent/wt_b", root, code)\n    code = code.replace(BASE, root)\n    for ws in (WS, "/workspace"):\n        code = code.replace(ws, root)\n    fd, path = tempfile.mkstemp(suffix=".py", prefix="vote_")\n    with os.fdopen(fd, "w") as f:\n        f.write(code)\n    return path\n\n\ndef load_state():\n    try:\n        return json.load(open(STATE))\n    except Exception:  # noqa: BLE001\n        return {}\n\n\ndef save_state(st):\n    os.makedirs(HERE, exist_ok=True)\n    with open(STATE, "w") as f:\n        json.dump(st, f)\n\n\ndef t_zero(st):\n    if st.get("t0"):\n        return st["t0"]\n    try:\n        return json.load(open(os.path.join(HERE, "team.json")))["t0"]\n    except Exception:  # noqa: BLE001\n        return time.time() - 600\n\n\ndef apply_patch(patch):\n    fd, pp = tempfile.mkstemp(suffix=".patch")\n    with os.fdopen(fd, "w") as f:\n        f.write(patch if patch.endswith("\\n") else patch + "\\n")\n    code, out, err = sh(["git", "apply", "--whitespace=nowarn", pp], WS)\n    os.remove(pp)\n    return code, (err or out)[-200:]\n\n\ndef reset_ws():\n    """/workspace back to the baseline: index first (patch_of\'s \'git add -N\' makes new files look tracked to clean)."""\n    sh(["git", "reset", "-q"], WS)\n    sh(["git", "checkout", "-f", ref(), "--", "."], WS)\n    sh(["git", "clean", "-fdq"], WS)\n\n\ndef vote(st):\n    """Compare A and B, put the winner in /workspace; returns the result lines."""\n    t_start = time.time()\n    t0 = t_zero(st)\n    patches = {x: patch_of(root_of(x)) for x in "ab"}\n    cands = {x: p for x, p in patches.items() if p.strip()}\n    lines = [f"TEAM VOTE ({int(time.time() - t0)} s after setup)"]\n    st["voted"] = {x: digest(patches[x]) for x in "ab"}\n    if not cands:\n        st["winner"] = "none"\n        save_state(st)\n        return lines + ["Neither fixer has a source patch. WINNER: none."]\n    base = BASE\n    has_base = is_tree(base)\n    test_res, score, detail = {}, {x: 0 for x in cands}, {x: [] for x in cands}\n    if len(cands) == 2 and patches["a"] != patches["b"] and has_base:\n        sources = sorted({s for p in cands.values() for s in changed_sources(p)})\n        tests = select_tests(base, sources)\n        if tests:\n            cmd = [sys.executable, "-m", "pytest", *tests, "-q", "-p", "no:cacheprovider", "-p", "no:anyio", "-o", "timeout=0"]\n            jobs = {k: (cmd, r, env_for(r)) for k, r in [("0", base)] + [(x, root_of(x)) for x in cands]}\n            test_res = {k: counts(o + e) for k, (_, o, e) in run_all(jobs, TEST_TIMEOUT).items()}\n            if any(v is None for v in test_res.values()):\n                test_res = {}  # a run without a summary: the tests cannot compare the candidates\n        scripts = check_scripts(t0)\n        if scripts:\n            codes = {}\n            for s in scripts:\n                try:\n                    codes[s] = open(s, encoding="utf-8", errors="replace").read()\n                except OSError:\n                    pass\n            jobs, tmp = {}, []\n            for k, r in [("0", base)] + [(x, root_of(x)) for x in cands]:\n                for s, code in codes.items():\n                    path = script_for(code, r)\n                    tmp.append(path)\n                    jobs[(k, s)] = ([sys.executable, path], r, env_for(r))\n            res = run_all(jobs, CHECK_TIMEOUT)\n            for path in tmp:\n                try:\n                    os.remove(path)\n                except OSError:\n                    pass\n            for x in cands:\n                for s in codes:\n                    be, bo, berr = res[("0", s)]\n                    ce, co, cerr = res[(x, s)]\n                    fixes = be != 0 and ce == 0\n                    broke = be == 0 and ce != 0\n                    changed = (be, bo, berr) != (ce, co, cerr)\n                    pos = changed and len(POS.findall(co)) > len(POS.findall(bo))\n                    neg_gone = changed and len(NEG.findall(co + cerr)) < len(NEG.findall(bo + berr))\n                    score[x] += fixes + pos + neg_gone - broke\n                    detail[x].append(f"{os.path.basename(s)}:{\'fixed\' if fixes else \'broke\' if broke else \'changed\' if changed else \'same\'}")\n    breaks = {x: bool(test_res) and test_res.get(x, (0, 0))[0] > test_res.get("0", (0, 0))[0] for x in cands}\n    keep = [x for x in cands if not breaks[x]] or list(cands)\n    best = max(score[x] for x in keep)\n    top = [x for x in keep if score[x] == best]\n    winner = "a" if "a" in top else "b"\n    for x in "ab":\n        if x not in cands:\n            lines.append(f"  {x.upper()}: no source patch")\n            continue\n        t = test_res.get(x)\n        size = len(re.findall(r"^[+-](?![+-])", cands[x], re.M))\n        lines.append(f"  {x.upper()}: {size} changed lines in {\', \'.join(changed_sources(cands[x])) or \'?\'} | existing tests "\n                     + (f"{t[0]} failing (no patch: {test_res[\'0\'][0]})" if t else "not run")\n                     + (" -> dropped (breaks tests)" if breaks[x] and x not in keep else "")\n                     + f" | check score {score[x]} [{\' \'.join(detail[x])}]")\n    if winner == "b":\n        saved = patches["a"]\n        reset_ws()\n        code, msg = apply_patch(cands["b"])\n        if code != 0:\n            reset_ws()\n            if saved.strip():\n                apply_patch(saved)\n            lines.append(f"(B\'s patch did not apply: {msg}; A\'s kept)")\n            winner = "a"\n    st["winner"] = winner\n    st["voted"] = {x: digest(patch_of(root_of(x))) if x == "a" else digest(patches[x]) for x in "ab"}\n    save_state(st)\n    lines.append(f"WINNER: {winner.upper()} ({time.time() - t_start:.0f} s). /workspace now holds this patch.")\n    return lines\n\n\ndef stale(st):\n    """True when no vote ran yet or a patch changed since the last one."""\n    if "voted" not in st:\n        return True\n    cur = {"a": digest(patch_of(WS)) if st.get("winner") != "b" else None, "b": digest(patch_of(root_of("b")))}\n    return cur["b"] != st["voted"].get("b") or (cur["a"] is not None and cur["a"] != st["voted"].get("a"))\n\n\ndef done(x):\n    st = load_state()\n    st.setdefault("done", {})[x] = time.time()\n    save_state(st)\n    root = root_of(x)\n    _, status, _ = sh(["git", "status", "--short"], root)\n    _, diff, _ = sh(["git", "diff", "--stat"], root)\n    out = [f"git status --short ({\'your copy\' if x == \'b\' else \'/workspace\'}):", status.strip() or "(clean: no change)",\n           diff.strip()[-1500:]]\n    other = "b" if x == "a" else "a"\n    if other in st["done"]:\n        out += vote(st) if stale(st) else [f"TEAM VOTE already made: WINNER {st.get(\'winner\', \'?\').upper()}."]\n        out.append("Both fixers are done. Your part is over: reply with one line, DONE: <what you changed>, and make no more tool calls.")\n    else:\n        out.append(f"Recorded. Fixer {other.upper()} is still working; when it is done, a test vote keeps the better of the two "\n                   f"patches. Your part is over: reply with one line, DONE: <what you changed>, and make no more tool calls.")\n    return "\\n".join(out)\n\n\ndef final():\n    st = load_state()\n    lines = vote(st) if stale(st) else [f"TEAM VOTE already made: WINNER {st.get(\'winner\', \'?\').upper()}."]\n    return "\\n".join(lines + ["Your next call is submit_patch."])\n\n\ndef main(argv):\n    if MODE == "final" or argv[:1] == ["final"]:\n        return final()\n    if argv[:1] == ["done"] and len(argv) > 1 and argv[1].lower() in ("a", "b"):\n        return done(argv[1].lower())\n    return "usage: python3 .git/agent/vote.py done a   (Fixer A)   or   python3 .git/agent/vote.py done b   (Fixer B)"\n\n\nif __name__ == "__main__":\n    try:\n        print(main(sys.argv[1:]))\n    except Exception as e:  # noqa: BLE001  never leave a fixer without an answer\n        print(f"VOTE ERROR {type(e).__name__}: {e}. /workspace is left as it is. Your part is over: reply with one line, DONE.")\n'  # filled by the builder (scripts/make_r90_arms.py) with scripts/agent_team/vote.py
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
