"""sk_a2v = sk_a2 + a repro check with verdict events, fail-first (docs/PLAN.md 'PLAN (not built) 2026-11-22: sk_a2 + repro check';
user 2026-11-22: 'yes fail-first in, build it now'). Evidence: the sq1c2 family (fewest wrong edits in the bank) runs a repro that must print
FIXED; there it worked as a correctness signal, rarely as a fixer (BUG -> re-edit 4 of 171), because its repros were written after the edit
and passed on the first try. sk_a2 already spends ~2.5 script runs + 1.8 scratch writes before its first edit, with no clear verdict.
Change (everything else = sk_a2 byte for byte):
  a.py 'check' (option word in commands.txt) = run .git/agent/repro.py (timeout 30) and read its verdict (a line that is exactly BUG / FIXED);
  four events by verdict x whether the repository has a source change:
    no change + BUG     -> REPRO SHOWS THE BUG: your next call is the edit
    no change + FIXED   -> YOUR REPRO DOES NOT SHOW THE BUG (fail-first): it proves nothing; fix the repro once, or edit now
    change + BUG        -> STILL BUG: your edit did not fix this case: change the edit
    change + FIXED      -> REPRO PASSES: one related test file under timeout 90, then submit_patch
  (+ NO VERDICT when neither word is printed; + a note on REPRO PASSES when the repro never printed BUG before the edit);
  git status flags kept (scratch / test files), the old automatic pytest dropped (up to 150 s).
Prompt: Step 3 rewritten as the repro step, one worked example per event. Run: python3 -I scripts/make_ska2v.py"""
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC, OUT = ROOT / "submissions/sk_a2", ROOT / "submissions/sk_a2v"

CHECK = '''def verdict(out):
    words = {l.strip() for l in out.split("\\n")}
    return "FIXED" if "FIXED" in words else "BUG" if "BUG" in words else None


def cmd_check(st, args):
    """sk_a2v: run the repro and turn its verdict into the next step (fail-first before the edit)."""
    out = []
    if not os.path.exists(REPRO):
        return ("(no .git/agent/repro.py yet) Write the issue's own example there with write_file: it prints BUG while the wrong "
                "behaviour is there and FIXED once it is gone. Then run: python3 .git/agent/a.py check")
    res = run("timeout 30 python3 .git/agent/repro.py 2>&1", 40)
    out.append("$ python3 .git/agent/repro.py\\n" + "\\n".join(res.split("\\n")[-15:]))
    v, edited = verdict(res), bool(changed_source())
    st["checks"] = st.get("checks", 0) + 1
    if not edited and v == "BUG":
        st["bug_seen"] = True
        out.append(">>> REPRO SHOWS THE BUG. Your next call is the edit; then run check again. <<<")
    elif not edited and v == "FIXED":
        out.append(">>> YOUR REPRO DOES NOT SHOW THE BUG: it prints FIXED on the unchanged code, so it proves nothing. Make it fail "
                   "the way the issue says (its exact example, names, values, message) with one write_file, or make your edit now. <<<")
    elif edited and v == "BUG":
        st["bug_seen"] = True
        out.append(">>> STILL BUG: your edit did not fix this case. Change the edit (or the place you edited), then run check again. <<<")
    elif edited and v == "FIXED":
        note = "" if st.get("bug_seen") else (" (It never printed BUG before your edit, so it may not test the bug: if the issue's "
                                              "example is not in it, add it.)")
        out.append(">>> REPRO PASSES. Run one related test file under timeout 90, then submit_patch." + note + " <<<")
    else:
        out.append(">>> NO VERDICT: the repro printed neither BUG nor FIXED on a line of its own (an error in the repro itself?). Make "
                   "it catch the issue's error and print BUG, and print FIXED when the behaviour is right. <<<")
    status = run("git status --short --untracked-files=all")
    flags = []
    for line in status.split("\\n"):
        if not line.strip():
            continue
        code, path = line[:2], line[3:]
        if code.strip() == "??" and not path.startswith(".git/"):
            flags.append(f"  SCRATCH FILE {path}: it would become part of your patch; delete it (rm {path}) or keep scratch in .git/agent/")
        elif TEST_RE.search(path):
            flags.append(f"  TEST FILE CHANGED {path}: the grader resets tests; restore it (git checkout -- {path})")
    out.append("$ git status --short\\n" + (status or "(no changes)") + ("\\n" + "\\n".join(flags) if flags else ""))
    return "\\n\\n".join(out)


'''

STEP3_OLD = """## Step 3: One check, one repair, then submit
- Run ONLY the targeted test for the file you changed, always under a time limit:
  timeout 90 python3 -m pytest tests/test_target.py -x -q -k name -p no:anyio -o timeout=0 > /tmp/t1.log 2>&1; tail -n 25 /tmp/t1.log
- A script of your own: write it with write_file to .git/agent/check.py (outside your patch; write_file refuses /tmp)
  and run it under a time limit: timeout 30 python3 .git/agent/check.py
- If the test fails, make one repair, then submit. A local green test is not the grader: submit even if the check is
  red or skipped. The working tree is graded as it is, so an edit made in time counts even if you never run a test."""

STEP3_NEW = """## Step 3: The repro (.git/agent/repro.py), checked by a.py
- Once you know where the bug is, write the issue's own example to .git/agent/repro.py with write_file (outside your
  patch): import the package normally, run the issue's exact call with its exact names and values, and print BUG
  while the wrong behaviour is there and FIXED once it is gone, each alone on its own line. Catch the issue's error
  and print BUG for it. Never write scripts anywhere else, and never run the repro yourself: run
  python3 .git/agent/a.py check. It runs the repro (30 s) and tells you the next step:
  REPRO SHOWS THE BUG: your next call is the edit.
  YOUR REPRO DOES NOT SHOW THE BUG: it proves nothing. Fix the repro with one write_file, or make your edit now.
  STILL BUG (after your edit): change the edit, then check again.
  REPRO PASSES: run one related test file under a time limit, then submit_patch:
  timeout 90 python3 -m pytest tests/test_target.py -x -q -k name -p no:anyio -o timeout=0 > /tmp/t1.log 2>&1; tail -n 25 /tmp/t1.log
- At most two calls go into the repro before your edit; the edit never waits for a perfect repro. A local green test
  is not the grader: submit even if the check is red or skipped. The working tree is graded as it is, so an edit made
  in time counts even if you never run a check."""

EX_OLD = """retries. Found it: the very next call is the edit that adds the same kind of check, raising
ValueError("timeout must be >= 0"). Then the client tests under timeout 90, then submit: 6 calls."""

EX_NEW = """retries. Found it. write_file .git/agent/repro.py:
  from pkg.client import Client
  try:
      Client(timeout=-1)
      print("BUG")
  except ValueError as e:
      print("FIXED" if "timeout must be >= 0" in str(e) else "BUG")
check prints BUG and REPRO SHOWS THE BUG, so the next call is the edit that adds the same kind of check, raising
ValueError("timeout must be >= 0"). check again: FIXED and REPRO PASSES. Then the client tests under timeout 90,
then submit: 9 calls.

## Example 2: the other two check results (an invented package)
Task: "wrap() drops the last word when the width is exact." The first repro calls wrap("ab cd", 10): check prints
FIXED and YOUR REPRO DOES NOT SHOW THE BUG (width 10 is not exact). One write_file uses the issue's case,
wrap("ab cd", 5) must equal ["ab cd"]: check prints BUG and REPRO SHOWS THE BUG, so the next call is the edit. check
prints STILL BUG: the edit changed the width test in the wrong branch, so the next call moves the fix to the branch
that ends the line; check prints REPRO PASSES; the text tests under timeout 90; submit."""


def sub(t, a, b):
    assert t.count(a) == 1, a[:70]
    return t.replace(a, b)


def build():
    a = (SRC / "skills/agent/scripts/a.py").read_text()
    m = re.search(r"def cmd_check\(st, args\):.*?(?=def has_change\(\):)", a, re.S)
    assert m
    a = a[:m.start()] + CHECK + a[m.end():]
    a = sub(a, 'OPTIONS = {"banner", "reshow"}', 'OPTIONS = {"banner", "reshow"}  # sk_a2v: + the check command (repro verdicts)')
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SRC, OUT)
    (OUT / "skills/agent/scripts/a.py").write_text(a)
    c = (SRC / "skills/agent/scripts/commands.txt").read_text().split()
    assert "check" not in c
    (OUT / "skills/agent/scripts/commands.txt").write_text(" ".join(c + ["check"]) + "\n")
    ins = (SRC / "skills/agent/scripts/install.py").read_text()
    ins = sub(ins, '"check": "check                         after an edit: .git/agent/repro.py + nearest tests + git status",',
              '"check": "check                         run .git/agent/repro.py: BUG / FIXED, and what to do next",')
    (OUT / "skills/agent/scripts/install.py").write_text(ins)
    p = (SRC / "prompts/system.md").read_text()
    p = sub(p, STEP3_OLD, STEP3_NEW)
    p = sub(p, EX_OLD, EX_NEW)
    p = sub(p, "As soon as you can say which lines to change and how, your\nvery next tool call is that edit, even if you are only fairly sure. Checking comes after the edit.",
            "As soon as you can say which lines to change and how, your\nnext calls are the repro (Step 3, two calls at most) and then that edit, even if you are only fairly sure.")
    (OUT / "prompts/system.md").write_text(p)
    y = (SRC / "agent.yaml").read_text()
    (OUT / "agent.yaml").write_text(sub(y, "# sk_a2: mix + the agent's reading tool",
                                        "# sk_a2v (2026-11-22): sk_a2 + repro check with verdict events, fail-first (scripts/make_ska2v.py). sk_a2 was: mix + the agent's reading tool"))
    print("wrote", OUT.relative_to(ROOT))


if __name__ == "__main__":
    build()
