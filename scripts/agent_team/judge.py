"""The team's judge: picks one of up to three candidate patches and puts it in the repository (run by Fixer A).

  python3 .git/agent/judge.py            Fixer A, after its own fix: WAITING until B and C are done (or the time cap), then compare the
                                         three patches, copy the winner into /workspace; then A calls submit_patch
  python3 .git/agent/judge.py done b     Fixer B (or c) when finished: leaves a marker so the judge stops waiting

Candidates: A = the repository itself, B / C = <repo>/.git/agent/wt_b / wt_c (git worktrees made by the team setup),
compared with wt_0 (a clean copy of the baseline). Rules (2026-10-29, from 195 + 165 candidate patches on 40 tasks):
  1. an empty source patch is never picked;
  2. a patch that makes more existing tests fail than no patch does is dropped, unless all do (0 of 19 such patches
     were right, outside the one task whose old tests assert the old behaviour);
  3. the highest repro score: the fixers' scripts .git/agent/repro_*.py run without and with each patch; +1 per
     script that goes from failing to passing, per script whose output gains FIXED/PASS-like words or loses
     BUG/FAIL/Traceback-like words, -1 per script that goes from passing to failing (score 2+: 62% right, 0: 37%);
  4. ties: A (already in place), then the smaller patch.
Never edits a file outside the repository's working tree; always exits 0 with a WINNER line or the reason why not.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))  # <repo>/.git/agent
WS = os.path.dirname(os.path.dirname(HERE))
TEAM = os.path.join(HERE, "team.json")
WAIT_UNTIL = 300  # seconds after setup: stop waiting for B and C (they may still be editing; their patch counts)
# never sleep here: the harness runs one tool call at a time per task (swegemma ctx.tool_lock), so a waiting judge
# would freeze B and C; it answers WAITING at once and Fixer A's next model call is the pause
TEST_TIMEOUT, REPRO_TIMEOUT, TESTS_MAX = 60, 20, 3
TEST_RE = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)conftest\.py$|(^|/)pytest\.ini$")
POS = re.compile(r"\b(FIXED|PASS(ED)?|SUCCESS|WORKS|OK)\b|correct", re.I)
NEG = re.compile(r"\b(BUG|FAIL(ED|URE)?|NOT FIXED|STILL|REPRODUCED|WRONG|ERROR|Traceback|AssertionError|MISMATCH)\b", re.I)


def sh(args, cwd, timeout=60):
    try:
        r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -9, "", "timed out"


def ref():
    return "_swegemma_baseline" if sh(["git", "rev-parse", "-q", "--verify", "_swegemma_baseline"], WS)[0] == 0 else "HEAD"


def patch_of(root):
    """The candidate's source patch (test files and the tool's own files left out)."""
    sh(["git", "add", "-A", "-N", "."], root)
    _, out, _ = sh(["git", "diff", "--binary", ref() if root == WS else "HEAD"], root)
    keep, cur = [], []
    for block in re.split(r"(?m)^(?=diff --git )", out):
        m = re.match(r"diff --git a/(\S+) b/(\S+)", block)
        if m and not TEST_RE.search(m.group(2)) and not m.group(2).startswith(".git/"):
            keep.append(block)
    return "".join(keep)


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
    env["PYTHONPATH"] = root + os.pathsep + env.get("PYTHONPATH", "")
    return env


def run_all(jobs, timeout):
    """jobs: {key: (args, cwd, env, stdin_text)} run at the same time; -> {key: (exit, out, err)}."""
    procs, res = {}, {}
    for k, (args, cwd, env, _) in jobs.items():
        procs[k] = subprocess.Popen(args, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=True)
    end = time.time() + timeout
    for k, p in procs.items():
        try:
            out, err = p.communicate(timeout=max(1, end - time.time()))
            res[k] = (p.returncode, out[-600:], err[-600:])
        except subprocess.TimeoutExpired:
            p.kill()
            res[k] = ("timeout", "", "")
    return res


def counts(out):
    m = {k: int(v) for v, k in re.findall(r"(\d+) (passed|failed|errors?)", out or "")}
    return m.get("failed", 0) + m.get("error", 0) + m.get("errors", 0), m.get("passed", 0)


def script_for(code, root):
    """The script as it would run in root: paths of the repository and of the copies point at root."""
    code = re.sub(r"(/workspace)?/?\.git/agent/wt_[0abc]", root, code)
    code = code.replace("/workspace", root)
    fd, path = tempfile.mkstemp(suffix=".py", prefix="judge_")
    with os.fdopen(fd, "w") as f:
        f.write(code)
    return path


def judge():
    t_start = time.time()
    try:
        t0 = json.load(open(TEAM))["t0"]
    except Exception:  # noqa: BLE001
        t0 = t_start
    roots = {"a": WS}
    for x in "bc":
        p = os.path.join(HERE, f"wt_{x}")
        if os.path.exists(os.path.join(p, ".git")):
            roots[x] = p
    waiting = [x for x in roots if x != "a" and not os.path.exists(os.path.join(HERE, f"done_{x}"))]
    if waiting and time.time() - t0 < WAIT_UNTIL:
        return (f"WAITING: Fixer(s) {', '.join(w.upper() for w in waiting)} still working ({int(time.time() - t0)} s of "
                f"{WAIT_UNTIL}). Do nothing else: your next call is the same command again: python3 .git/agent/judge.py")
    patches = {x: patch_of(r) for x, r in roots.items()}
    cands = {x: p for x, p in patches.items() if p.strip()}
    lines = [f"JUDGE RESULT ({int(time.time() - t0)} s after setup; still editing when judged: "
             f"{', '.join(w.upper() for w in waiting) or 'none'})"]
    if not cands:
        return "\n".join(lines + ["No candidate has a source patch. WINNER: none. Make your best edit now, then submit_patch."])
    base = os.path.join(HERE, "wt_0")
    has_base = os.path.exists(os.path.join(base, ".git"))
    # existing tests of the changed modules: no patch vs each candidate
    sources = sorted({s for p in cands.values() for s in changed_sources(p)})
    tests = select_tests(base if has_base else WS, sources)
    test_res = {}
    if tests and has_base:
        cmd = [sys.executable, "-m", "pytest", *tests, "-q", "-p", "no:cacheprovider", "-p", "no:anyio", "-o", "timeout=0"]
        jobs = {k: (cmd, r, env_for(r), None) for k, r in [("0", base)] + [(x, roots[x]) for x in cands]}
        test_res = {k: counts(o + e) for k, (_, o, e) in run_all(jobs, TEST_TIMEOUT).items()}
    breaks = {x: bool(test_res) and test_res.get(x, (0, 0))[0] > test_res.get("0", (0, 0))[0] for x in cands}
    # the fixers' repro scripts: no patch vs each candidate
    scripts = sorted(f for f in os.listdir(HERE) if f.startswith("repro_") and f.endswith(".py"))
    score = {x: 0 for x in cands}
    detail = {x: [] for x in cands}
    if scripts and has_base:
        codes = {s: open(os.path.join(HERE, s), encoding="utf-8", errors="replace").read() for s in scripts}
        jobs, tmp = {}, []
        for k, r in [("0", base)] + [(x, roots[x]) for x in cands]:
            for s, code in codes.items():
                path = script_for(code, r)
                tmp.append(path)
                jobs[(k, s)] = ([sys.executable, path], r, env_for(r), None)
        res = run_all(jobs, REPRO_TIMEOUT)
        for path in tmp:
            os.remove(path)
        for x in cands:
            for s in scripts:
                be, bo, berr = res[("0", s)]
                ce, co, cerr = res[(x, s)]
                fixes = be != 0 and ce == 0
                broke = be == 0 and ce != 0
                changed = (be, bo, berr) != (ce, co, cerr)
                pos = changed and len(POS.findall(co)) > len(POS.findall(bo))
                neg_gone = changed and len(NEG.findall(co + cerr)) < len(NEG.findall(bo + berr))
                score[x] += fixes + pos + neg_gone - broke
                detail[x].append(f"{s[6:-3]}:{'fixed' if fixes else 'broke' if broke else 'changed' if changed else 'same'}")
    size = {x: len(re.findall(r"^[+-](?![+-])", p, re.M)) for x, p in cands.items()}
    keep = [x for x in cands if not breaks[x]] or list(cands)
    best = max(score[x] for x in keep)
    top = [x for x in keep if score[x] == best]
    winner = "a" if "a" in top else min(top, key=lambda x: size[x])
    for x in sorted(patches):
        if x not in cands:
            lines.append(f"  {x.upper()}: no source patch")
            continue
        t = test_res.get(x)
        lines.append(f"  {x.upper()}: {size[x]} changed lines in {', '.join(changed_sources(cands[x])) or '?'} | existing tests "
                     + (f"{t[0]} failing (no patch: {test_res['0'][0]})" if t else "not run")
                     + (" -> DROPPED (breaks tests)" if breaks[x] and x not in keep else "")
                     + f" | repro score {score[x]} [{' '.join(detail[x])}]")
    if winner != "a":
        saved = patches["a"]
        sh(["git", "checkout", "-f", ref(), "--", "."], WS)
        sh(["git", "clean", "-fdq"], WS)
        fd, pp = tempfile.mkstemp(suffix=".patch")
        with os.fdopen(fd, "w") as f:
            f.write(cands[winner] if cands[winner].endswith("\n") else cands[winner] + "\n")
        code, out, err = sh(["git", "apply", "--whitespace=nowarn", pp], WS)
        os.remove(pp)
        if code != 0:  # put A's own patch back
            if saved.strip():
                fd, pp = tempfile.mkstemp(suffix=".patch")
                with os.fdopen(fd, "w") as f:
                    f.write(saved if saved.endswith("\n") else saved + "\n")
                sh(["git", "apply", "--whitespace=nowarn", pp], WS)
                os.remove(pp)
            lines.append(f"(could not apply {winner.upper()}'s patch: {(err or out)[-200:]}; kept A's)")
            winner = "a"
    lines.append(f"WINNER: {winner.upper()} ({time.time() - t_start:.0f} s). The repository now holds this patch. Your next "
                 f"call is submit_patch; then reply with one sentence and make no further tool calls.")
    return "\n".join(lines)


def main(argv):
    if argv[:1] == ["done"] and len(argv) > 1 and argv[1].lower() in ("b", "c"):
        open(os.path.join(HERE, f"done_{argv[1].lower()}"), "w").close()
        return ("DONE: your patch and your repro script are handed to the judge. Your part is over: reply with one "
                "sentence and NO tool call.")
    return judge()


if __name__ == "__main__":
    try:
        print(main(sys.argv[1:]))
    except Exception as e:  # noqa: BLE001  never leave Fixer A without an answer
        print(f"JUDGE ERROR {type(e).__name__}: {e}. WINNER: A (kept as it is). Your next call is submit_patch.")
