"""The two-fixer team's vote (r90 evteam, user 2026-11-12 "i want to try everything": lead 2 of
docs/RESEARCH_PROBLEMS_2026-11-12.md, the crash-free wait-for-all team).

    python3 .git/agent/vote.py done a     Fixer A (works in /workspace) at the end of its work
    python3 .git/agent/vote.py done b     Fixer B (works in /workspace/.git/agent/wt_b) at the end of its work
    run_skill_script team scripts/vote.py the coordinator, after the team returns (MODE "final": vote now if needed)

Why it is a fixer's own last command and not a separate step: the harness's call budget is shared by both fixers and
the coordinator, and only submit_patch / get_status are free, so a vote made after the team returns is refused in
the common case (both fixers spend the budget). A fixer's 'done' call is a call it makes anyway in place of the
final `git status && git diff` (this script prints them). When the second fixer reports done, the vote runs at once.

Rules (scripts/agent_team/judge.py, from the 2026-10-29 picker study on 195 + 165 candidate patches over 40 tasks):
  1. an empty source patch is never picked; A empty and B not -> B;
  2. a patch that makes more existing tests fail than no patch does is dropped, unless both do;
  3. the higher check score: the fixers' own scripts in /tmp (A) and /tmp/b (B) written since setup run on the
     baseline and on each candidate: +1 per script that goes from failing to passing, +1 if its output gains
     FIXED/PASS-like words, +1 if it loses BUG/FAIL/Traceback-like words, -1 per script that goes from passing to failing;
  4. ties: A (already in place).
The winner ends up in /workspace (the only tree the harness grades); A's tree is kept unless B wins; if B's patch
does not apply, A's is put back. Never touches anything outside /workspace and /tmp; always exits 0."""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time

MODE = 'final'  # the builder writes the coordinator's skill copy with MODE "final"


def _workspace():
    here = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(here) == "agent" and os.path.basename(os.path.dirname(here)) == ".git":
        return os.path.dirname(os.path.dirname(here))
    import inspect
    for frame in inspect.stack():
        cwd = frame.frame.f_locals.get("_orig_cwd")
        if isinstance(cwd, str) and os.path.isdir(os.path.join(cwd, ".git")):
            return cwd
    for cand in (os.environ.get("PYTHONPATH", "").split(os.pathsep)[0], "/workspace", os.getcwd()):
        if cand and os.path.isdir(os.path.join(cand, ".git")):
            return cand
    return os.getcwd()


WS = _workspace()
HERE = os.path.join(WS, ".git", "agent")
STATE = os.path.join(HERE, "vote_state.json")
# The fixers write "/tmp/..." in commands; the harness maps that to the sandbox's temp dir (TMPDIR) in commands only,
# so this script uses tempfile.gettempdir() (= /tmp in the scorer's container). VOTE_*: tests only.
TMP = tempfile.gettempdir()
SCRATCH = {"a": os.environ.get("VOTE_SCRATCH_A", TMP), "b": os.environ.get("VOTE_SCRATCH_B", os.path.join(TMP, "b"))}
BASE = os.environ.get("VOTE_BASE", os.path.join(TMP, "team", "wt_0"))  # made by the evidence script (outside Fixer A's searches)
TEST_TIMEOUT, CHECK_TIMEOUT, TESTS_MAX, CHECKS_MAX = 40, 20, 3, 3
TEST_RE = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)conftest\.py$|(^|/)pytest\.ini$")
POS = re.compile(r"\b(FIXED|PASS(ED)?|SUCCESS|WORKS|OK)\b|correct", re.I)
NEG = re.compile(r"\b(BUG|FAIL(ED|URE)?|NOT FIXED|STILL|REPRODUCED|WRONG|ERROR|Traceback|AssertionError|MISMATCH)\b", re.I)


def sh(args, cwd, timeout=60):
    try:
        r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL,
                           errors="replace")
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -9, "", "timed out"


def ref():
    return "_swegemma_baseline" if sh(["git", "rev-parse", "-q", "--verify", "_swegemma_baseline"], WS)[0] == 0 else "HEAD"


def root_of(x):
    return WS if x == "a" else os.path.join(HERE, "wt_b")


def is_tree(p):
    return os.path.exists(os.path.join(p, ".git"))


def patch_of(root):
    """The candidate's source patch (test files, .git and the harness's .adk_exec_*.py skill wrappers left out); '' if the
    tree is missing. New files are counted through a throw-away copy of the index, so the real index never changes."""
    if not is_tree(root):
        return ""
    _, idx, _ = sh(["git", "rev-parse", "--git-path", "index"], root)
    idx = os.path.join(root, idx.strip()) if idx.strip() and not os.path.isabs(idx.strip()) else idx.strip()
    fd, tmp_idx = tempfile.mkstemp(prefix="vote_idx_")
    os.close(fd)
    try:
        if idx and os.path.exists(idx):
            with open(idx, "rb") as src, open(tmp_idx, "wb") as dst:
                dst.write(src.read())
        else:
            os.remove(tmp_idx)
        env = {**os.environ, "GIT_INDEX_FILE": tmp_idx}
        subprocess.run(["git", "add", "-A", "-N", "."], cwd=root, env=env, capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
        r = subprocess.run(["git", "diff", "--binary", ref() if root == WS else "HEAD"], cwd=root, env=env, capture_output=True,
                           text=True, timeout=60, stdin=subprocess.DEVNULL, errors="replace")
        out = r.stdout
    finally:
        if os.path.exists(tmp_idx):
            os.remove(tmp_idx)
    keep = []
    for block in re.split(r"(?m)^(?=diff --git )", out):
        m = re.match(r"diff --git a/(\S+) b/(\S+)", block)
        if m and not TEST_RE.search(m.group(2)) and not m.group(2).startswith(".git/") and not os.path.basename(m.group(2)).startswith(".adk_exec_"):
            keep.append(block)
    return "".join(keep)


def digest(p):
    return hashlib.sha1(p.encode("utf-8", "replace")).hexdigest()[:12]


def changed_sources(patch):
    return [f for f in re.findall(r"^\+\+\+ b/(\S+)", patch, re.M) if f.endswith(".py")]


def select_tests(base, sources):
    """Existing test files that import a changed module or are named after it (at most TESTS_MAX)."""
    scored = []
    for top in ("tests", "test", "testing"):
        for dirpath, _, files in os.walk(os.path.join(base, top)):
            for fn in files:
                if not (fn.startswith("test_") and fn.endswith(".py")):
                    continue
                path = os.path.join(dirpath, fn)
                try:
                    text = open(path, encoding="utf-8", errors="replace").read()
                except OSError:
                    continue
                s = 0
                for src in sources:
                    mod = src[:-3].replace("/", ".").removesuffix(".__init__")
                    if mod.startswith("src."):
                        mod = mod[4:]
                    pkg, _, stem = mod.rpartition(".")
                    if re.search(rf"\b(import|from)\s+{re.escape(mod)}\b", text) or (
                            pkg and re.search(rf"from\s+{re.escape(pkg)}\s+import\s+[^\n]*\b{re.escape(stem)}\b", text)):
                        s += 2
                    if stem and stem not in ("__init__", "utils", "main") and stem in fn:
                        s += 3
                if s:
                    scored.append((-s, len(text), os.path.relpath(path, base)))
    return [p for _, _, p in sorted(scored)[:TESTS_MAX]]


def env_for(root):
    env = {k: v for k, v in os.environ.items() if k != "PYTHONSAFEPATH"}
    paths = [root] + ([os.path.join(root, "src")] if os.path.isdir(os.path.join(root, "src")) else [])
    env["PYTHONPATH"] = os.pathsep.join(paths + [env.get("PYTHONPATH", "")])
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def run_all(jobs, timeout):
    """jobs: {key: (args, cwd, env)} run at the same time; -> {key: (exit, out, err)}."""
    procs, res = {}, {}
    for k, (args, cwd, env) in jobs.items():
        procs[k] = subprocess.Popen(args, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=True, errors="replace")
    end = time.time() + timeout
    for k, p in procs.items():
        try:
            out, err = p.communicate(timeout=max(1, end - time.time()))
            res[k] = (p.returncode, out[-800:], err[-800:])
        except subprocess.TimeoutExpired:
            p.kill()
            p.communicate()
            res[k] = ("timeout", "", "")
    return res


def counts(out):
    """(failing, passing) from pytest's summary line; None when there is none (pytest missing, crashed, timed out)."""
    m = {k: int(v) for v, k in re.findall(r"(\d+) (passed|failed|errors?)", out or "")}
    if not m:
        return None
    return m.get("failed", 0) + m.get("error", 0) + m.get("errors", 0), m.get("passed", 0)


def check_scripts(t0):
    """The fixers' own check scripts written since setup: /tmp/*.py (A) and /tmp/b/*.py (B), newest first."""
    found = []
    for d in SCRATCH.values():
        try:
            names = os.listdir(d)
        except OSError:
            continue
        for fn in names:
            p = os.path.join(d, fn)
            if fn.endswith(".py") and os.path.isfile(p) and not fn.startswith(("judge_", "vote_", ".adk_exec")):
                try:
                    if os.path.getmtime(p) >= t0 - 5 and os.path.getsize(p) < 20000:
                        found.append((os.path.getmtime(p), p))
                except OSError:
                    pass
    return [p for _, p in sorted(found, reverse=True)[:CHECKS_MAX]]


def script_for(code, root):
    """The script as it would run in root: paths of the repository and of B's copy point at root."""
    for ws in (WS, "/workspace"):  # the sandbox writes its real path into heredoc scripts; the scorer's is /workspace
        code = code.replace(ws + "/.git/agent/wt_b", root)
    code = re.sub(r"(?<![\w/])\.git/agent/wt_b", root, code)
    code = code.replace(BASE, root)
    for ws in (WS, "/workspace"):
        code = code.replace(ws, root)
    fd, path = tempfile.mkstemp(suffix=".py", prefix="vote_")
    with os.fdopen(fd, "w") as f:
        f.write(code)
    return path


def load_state():
    try:
        return json.load(open(STATE))
    except Exception:  # noqa: BLE001
        return {}


def save_state(st):
    os.makedirs(HERE, exist_ok=True)
    with open(STATE, "w") as f:
        json.dump(st, f)


def t_zero(st):
    if st.get("t0"):
        return st["t0"]
    try:
        return json.load(open(os.path.join(HERE, "team.json")))["t0"]
    except Exception:  # noqa: BLE001
        return time.time() - 600


def apply_patch(patch):
    fd, pp = tempfile.mkstemp(suffix=".patch")
    with os.fdopen(fd, "w") as f:
        f.write(patch if patch.endswith("\n") else patch + "\n")
    code, out, err = sh(["git", "apply", "--whitespace=nowarn", pp], WS)
    os.remove(pp)
    return code, (err or out)[-200:]


def reset_ws():
    """/workspace back to the baseline: index first (patch_of's 'git add -N' makes new files look tracked to clean)."""
    sh(["git", "reset", "-q"], WS)
    sh(["git", "checkout", "-f", ref(), "--", "."], WS)
    sh(["git", "clean", "-fdq"], WS)


def vote(st):
    """Compare A and B, put the winner in /workspace; returns the result lines."""
    t_start = time.time()
    t0 = t_zero(st)
    patches = {x: patch_of(root_of(x)) for x in "ab"}
    cands = {x: p for x, p in patches.items() if p.strip()}
    lines = [f"TEAM VOTE ({int(time.time() - t0)} s after setup)"]
    st["voted"] = {x: digest(patches[x]) for x in "ab"}
    if not cands:
        st["winner"] = "none"
        save_state(st)
        return lines + ["Neither fixer has a source patch. WINNER: none."]
    base = BASE
    has_base = is_tree(base)
    test_res, score, detail = {}, {x: 0 for x in cands}, {x: [] for x in cands}
    if len(cands) == 2 and patches["a"] != patches["b"] and has_base:
        sources = sorted({s for p in cands.values() for s in changed_sources(p)})
        tests = select_tests(base, sources)
        if tests:
            cmd = [sys.executable, "-m", "pytest", *tests, "-q", "-p", "no:cacheprovider", "-p", "no:anyio", "-o", "timeout=0"]
            jobs = {k: (cmd, r, env_for(r)) for k, r in [("0", base)] + [(x, root_of(x)) for x in cands]}
            test_res = {k: counts(o + e) for k, (_, o, e) in run_all(jobs, TEST_TIMEOUT).items()}
            if any(v is None for v in test_res.values()):
                test_res = {}  # a run without a summary: the tests cannot compare the candidates
        scripts = check_scripts(t0)
        if scripts:
            codes = {}
            for s in scripts:
                try:
                    codes[s] = open(s, encoding="utf-8", errors="replace").read()
                except OSError:
                    pass
            jobs, tmp = {}, []
            for k, r in [("0", base)] + [(x, root_of(x)) for x in cands]:
                for s, code in codes.items():
                    path = script_for(code, r)
                    tmp.append(path)
                    jobs[(k, s)] = ([sys.executable, path], r, env_for(r))
            res = run_all(jobs, CHECK_TIMEOUT)
            for path in tmp:
                try:
                    os.remove(path)
                except OSError:
                    pass
            for x in cands:
                for s in codes:
                    be, bo, berr = res[("0", s)]
                    ce, co, cerr = res[(x, s)]
                    fixes = be != 0 and ce == 0
                    broke = be == 0 and ce != 0
                    changed = (be, bo, berr) != (ce, co, cerr)
                    pos = changed and len(POS.findall(co)) > len(POS.findall(bo))
                    neg_gone = changed and len(NEG.findall(co + cerr)) < len(NEG.findall(bo + berr))
                    score[x] += fixes + pos + neg_gone - broke
                    detail[x].append(f"{os.path.basename(s)}:{'fixed' if fixes else 'broke' if broke else 'changed' if changed else 'same'}")
    breaks = {x: bool(test_res) and test_res.get(x, (0, 0))[0] > test_res.get("0", (0, 0))[0] for x in cands}
    keep = [x for x in cands if not breaks[x]] or list(cands)
    best = max(score[x] for x in keep)
    top = [x for x in keep if score[x] == best]
    winner = "a" if "a" in top else "b"
    for x in "ab":
        if x not in cands:
            lines.append(f"  {x.upper()}: no source patch")
            continue
        t = test_res.get(x)
        size = len(re.findall(r"^[+-](?![+-])", cands[x], re.M))
        lines.append(f"  {x.upper()}: {size} changed lines in {', '.join(changed_sources(cands[x])) or '?'} | existing tests "
                     + (f"{t[0]} failing (no patch: {test_res['0'][0]})" if t else "not run")
                     + (" -> dropped (breaks tests)" if breaks[x] and x not in keep else "")
                     + f" | check score {score[x]} [{' '.join(detail[x])}]")
    if winner == "b":
        saved = patches["a"]
        reset_ws()
        code, msg = apply_patch(cands["b"])
        if code != 0:
            reset_ws()
            if saved.strip():
                apply_patch(saved)
            lines.append(f"(B's patch did not apply: {msg}; A's kept)")
            winner = "a"
    st["winner"] = winner
    st["voted"] = {x: digest(patch_of(root_of(x))) if x == "a" else digest(patches[x]) for x in "ab"}
    save_state(st)
    lines.append(f"WINNER: {winner.upper()} ({time.time() - t_start:.0f} s). /workspace now holds this patch.")
    return lines


def stale(st):
    """True when no vote ran yet or a patch changed since the last one."""
    if "voted" not in st:
        return True
    cur = {"a": digest(patch_of(WS)) if st.get("winner") != "b" else None, "b": digest(patch_of(root_of("b")))}
    return cur["b"] != st["voted"].get("b") or (cur["a"] is not None and cur["a"] != st["voted"].get("a"))


def done(x):
    st = load_state()
    st.setdefault("done", {})[x] = time.time()
    save_state(st)
    root = root_of(x)
    _, status, _ = sh(["git", "status", "--short"], root)
    _, diff, _ = sh(["git", "diff", "--stat"], root)
    out = [f"git status --short ({'your copy' if x == 'b' else '/workspace'}):", status.strip() or "(clean: no change)",
           diff.strip()[-1500:]]
    other = "b" if x == "a" else "a"
    if other in st["done"]:
        out += vote(st) if stale(st) else [f"TEAM VOTE already made: WINNER {st.get('winner', '?').upper()}."]
        out.append("Both fixers are done. Your part is over: reply with one line, DONE: <what you changed>, and make no more tool calls.")
    else:
        out.append(f"Recorded. Fixer {other.upper()} is still working; when it is done, a test vote keeps the better of the two "
                   f"patches. Your part is over: reply with one line, DONE: <what you changed>, and make no more tool calls.")
    return "\n".join(out)


def final():
    st = load_state()
    lines = vote(st) if stale(st) else [f"TEAM VOTE already made: WINNER {st.get('winner', '?').upper()}."]
    return "\n".join(lines + ["Your next call is submit_patch."])


def main(argv):
    if MODE == "final" or argv[:1] == ["final"]:
        return final()
    if argv[:1] == ["done"] and len(argv) > 1 and argv[1].lower() in ("a", "b"):
        return done(argv[1].lower())
    return "usage: python3 .git/agent/vote.py done a   (Fixer A)   or   python3 .git/agent/vote.py done b   (Fixer B)"


if __name__ == "__main__":
    try:
        print(main(sys.argv[1:]))
    except Exception as e:  # noqa: BLE001  never leave a fixer without an answer
        print(f"VOTE ERROR {type(e).__name__}: {e}. /workspace is left as it is. Your part is over: reply with one line, DONE.")
