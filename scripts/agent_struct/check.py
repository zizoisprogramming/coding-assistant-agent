"""Round report for evloop's check stage (r92, user 2026-11-12 "build all": LoopAgent rounds with fresh contexts).

    run_skill_script skill act, file check.py (no arguments)

Prints what the round left in the repository and what the related existing tests say, then advances the round
(.git/agent/round) so act.py gives the next round fresh commands. The next attempt starts with an empty context and
sees only this report (copied by the check stage into its output_key), the issue and the evidence:
  - the diff of the source against the baseline (tests and .git left out), cut to DIFF_LINES;
  - up to TESTS_MAX existing test files that import a changed module or are named after it (scripts/agent_team/vote.py's
    rule), run with pytest -x -q, and the summary line plus the start of the first failure.
Called a second time in the same round, it prints the saved report again. A marker file .git/agent/NO_TESTS (made
only by the local simulator, which must not run task code) skips the tests."""
import inspect
import os
import re
import subprocess
import sys

DIFF_LINES = 45
TESTS_MAX = 2
TEST_TIMEOUT = 60
FAIL_LINES = 14
TEST_RE = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)conftest\.py$|(^|/)pytest\.ini$")


def workspace():
    for frame in inspect.stack():
        cwd = frame.frame.f_locals.get("_orig_cwd")
        if isinstance(cwd, str) and os.path.isdir(os.path.join(cwd, ".git")):
            return cwd
    for cand in (os.environ.get("PYTHONPATH", "").split(os.pathsep)[0], "/workspace", os.getcwd()):
        if cand and os.path.isdir(os.path.join(cand, ".git")):
            return cand
    sys.exit("repository not found")


def sh(args, cwd, timeout=60, env=None):
    try:
        r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL,
                           errors="replace", env=env)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -9, "", "timed out"


def source_diff(ws):
    """git diff of source files against the baseline, through a throw-away index (new files counted, real index kept)."""
    import tempfile
    ref = "_swegemma_baseline" if sh(["git", "rev-parse", "-q", "--verify", "_swegemma_baseline"], ws)[0] == 0 else "HEAD"
    fd, idx = tempfile.mkstemp(prefix="check_idx_")
    os.close(fd)
    try:
        real = os.path.join(ws, ".git", "index")
        if os.path.exists(real):
            with open(real, "rb") as s, open(idx, "wb") as d:
                d.write(s.read())
        else:
            os.remove(idx)
        env = {**os.environ, "GIT_INDEX_FILE": idx}
        sh(["git", "add", "-A", "-N", "."], ws, env=env)
        _, out, _ = sh(["git", "diff", "--no-color", ref], ws, env=env)
    finally:
        if os.path.exists(idx):
            os.remove(idx)
    keep = []
    for block in re.split(r"(?m)^(?=diff --git )", out):
        m = re.match(r"diff --git a/(\S+) b/(\S+)", block)
        if m and not TEST_RE.search(m.group(2)) and not os.path.basename(m.group(2)).startswith(".adk_exec_"):
            keep.append(block)
    return "".join(keep)


def select_tests(ws, sources):
    scored = []
    for top in ("tests", "test", "testing"):
        for dirpath, _, files in os.walk(os.path.join(ws, top)):
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
                    scored.append((-s, len(text), os.path.relpath(path, ws)))
    return [p for _, _, p in sorted(scored)[:TESTS_MAX]]


def report(ws, rnd):
    diff = source_diff(ws)
    out = [f"ROUND {rnd} REPORT"]
    if not diff.strip():
        return out + ["NO SOURCE EDIT YET: the source is unchanged. The next round must edit the most likely place early."]
    lines = diff.splitlines()
    files = re.findall(r"^\+\+\+ b/(\S+)", diff, re.M)
    out.append("changed: " + ", ".join(files))
    out.append("diff:")
    out += lines[:DIFF_LINES] + ([f"... {len(lines) - DIFF_LINES} more diff lines"] if len(lines) > DIFF_LINES else [])
    if os.path.exists(os.path.join(ws, ".git", "agent", "NO_TESTS")):
        return out + ["related tests: skipped (simulator)"]
    tests = select_tests(ws, [f for f in files if f.endswith(".py")])
    if not tests:
        return out + ["related tests: none found for the changed modules"]
    code, o, e = sh([sys.executable, "-m", "pytest", *tests, "-x", "-q", "-p", "no:cacheprovider", "-o", "timeout=0"], ws, TEST_TIMEOUT,
                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    text = (o or "") + (e or "")
    summary = next((l for l in reversed(text.splitlines()) if re.search(r"\d+ (passed|failed|errors?)", l)), "")
    out.append(f"related tests ({', '.join(tests)}): " + (summary.strip("= ") if summary else ("timed out" if code == -9 else f"no summary (exit {code})")))
    if code not in (0, -9) and ("failed" in summary or "error" in summary):
        first = re.split(r"(?m)^_{5,} ", text, maxsplit=1)
        body = (first[1] if len(first) > 1 else text).splitlines()
        out.append("first failure:")
        out += ["  " + l[:160] for l in body[:FAIL_LINES]]
    return out


def main():
    ws = workspace()
    agent = os.path.join(ws, ".git", "agent")
    os.makedirs(agent, exist_ok=True)
    rpath = os.path.join(agent, "round")
    try:
        rnd = int(open(rpath).read().strip() or 1)
    except (OSError, ValueError):
        rnd = 1
    import hashlib
    digest = hashlib.sha1(source_diff(ws).encode("utf-8", "replace")).hexdigest()
    prev = os.path.join(agent, f"report_{rnd - 1}")
    # a second call with nothing done since the last report (no command this round, same diff): the same report again
    if rnd > 1 and not os.path.exists(os.path.join(agent, f"act_count_{rnd}")) and os.path.exists(prev + ".diff") \
            and open(prev + ".diff").read() == digest:
        return open(prev, errors="replace").read()
    text = "\n".join(report(ws, rnd))
    with open(os.path.join(agent, f"report_{rnd}"), "w") as f:
        f.write(text)
    with open(os.path.join(agent, f"report_{rnd}.diff"), "w") as f:
        f.write(digest)
    with open(rpath, "w") as f:
        f.write(str(rnd + 1))
    return text


if __name__ == "__main__":
    try:
        print(main())
    except Exception as e:  # noqa: BLE001  the check stage must always get a report
        print(f"ROUND REPORT ERROR {type(e).__name__}: {e}")
