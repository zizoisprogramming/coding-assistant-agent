"""sb7f = function-level history, solved with (user 2026-11-18: 'yes build sb7f but we need a way to enforce it to use
the history, maybe ... few shot add example of solving it using history'). Run: python3 -I scripts/make_sb7f.py

Basis (docs/PLAN.md WHY sb7 / sb7s's history did not help + STEP 0c): line history at the issue names' def / use lines
showed declarations and refactors; the history of the FUNCTION holding the real fix shows a real-fix commit in 29/37
tasks. r114: a stop line in the stage's own tool output ends the stage (8/8); r110: a NEXT line in tool output was
followed 2/3.
  history stage (two calls, then one reply; include_contents none, thinking 128, output_key func_history):
    call 1 lists FILE=LINE=FUNCTION for every function that uses the issue's names (git grep -p with git's python
      funcname driver via -c core.attributesFile, no repository change), ends with a NEXT line;
    call 2 prints git log -L ':def FUNC[(]:FILE' -n 5 (12 lines per commit, 3,500 chars) for the 1-2 picked
      functions, ends with the HISTORY DONE stop line; the reply = everything above it.
  fixer: sb1's tools and sampling; prompt written fresh with the history pinned ({func_history?}) and a SOLVE IT WITH
    THAT HISTORY section; worked examples solve from the history: a past fix of the same kind (followed), the
    breaking commit (corrected), formatting-only history (ignored), each naming the commit in the reasoning.
Bundle = sb7s's (agent.yaml body, fixer.yaml, configs, eval_config byte for byte) with the two prompts and
history.yaml's output_key changed."""
import importlib.util
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("make_sb78", ROOT / "scripts/make_sb78.py")
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)
SRC, OUT = ROOT / "submissions/sb7s", ROOT / "submissions/sb7f"
DONE = "== HISTORY DONE: reply with everything above this line exactly as printed, and make no other call."
NEXT_OK = "== NEXT: pick the one or two functions above where the behaviour of the issue happens and run the second command with them."
NEXT_NONE = "== NEXT: no source line contains these names. Reply with the line: No history. Make no other call."


def shell_ok(block):
    assert '"' not in block and "`" not in block and "\\" not in block, "shell text: no double quotes, backticks, backslashes"


def main():
    h = (ROOT / "scripts/agent_sb7f/history.md").read_text()
    s = (ROOT / "scripts/agent_sb7f/system.md").read_text()
    M.check(h)
    M.check(s, ["{func_history?}"])
    M.examples(h)
    M.examples(s)
    blocks = re.findall(r"```\n(.*?)```", h, re.S)
    c1 = next(b for b in blocks if b.startswith("names="))
    c2 = next(b for b in blocks if b.startswith("funcs="))
    for b in (c1, c2):
        shell_ok(b)
    assert NEXT_OK in c1 and NEXT_NONE in c1 and "grep -n -p -w -F" in c1 and "core.attributesFile" in c1
    assert c2.rstrip().endswith("echo '" + DONE + "'") and "log -L ':def '$fn'[(]:'$f -n 5" in c2
    out1 = re.search(r"The result's stdout was:\n```\n(.*?)```", h, re.S).group(1)
    assert out1.rstrip().endswith(NEXT_OK), "example 1 shows the NEXT line after call 1"
    out2, rep2 = re.search(r"The result's stdout was:\n```\n(== pkg.*?)```\nYour reply, with no tool call, is everything above the HISTORY DONE line:\n(.*?)\n\nExample 2", h, re.S).groups()
    assert out2.rstrip().endswith(DONE) and out2[:out2.index(DONE)].strip() == rep2.strip(), "reply = stdout above the stop line"
    assert re.search(r"printed:\n```\n" + re.escape(NEXT_NONE) + r"\n```\nYour reply, with no tool call:\nNo history\.", h), "no-names case shown"
    ex = s[s.index("# EXAMPLES"):]
    for case in ("Example 1 - a past fix of the same kind", "Example 2 - the newest commit broke", "Example 3 - the history does not help"):
        assert case in ex, case
    assert ex.count("The reasoning names the case:") == 3, "each history case shows the commit named in the reasoning"
    assert "Tool call budget exhausted" in s and "old_string not found" in s and "mandatory input parameters are not present" in s
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SRC, OUT)
    (OUT / "prompts/history.md").write_text(h)
    (OUT / "prompts/system.md").write_text(s)
    hy = (SRC / "history.yaml").read_text()
    assert hy.count("output_key: line_history") == 1
    (OUT / "history.yaml").write_text(hy.replace("output_key: line_history", "output_key: func_history").replace(
        "Runs one git command that prints the line history of the code named in the issue, and returns its output. Makes a single call.",
        "Lists the functions that use the issue's names, prints the history of the one or two that matter, and returns it. Makes two calls."))
    first, rest = (SRC / "agent.yaml").read_text().split("\n", 1)
    (OUT / "agent.yaml").write_text("# sb7f (2026-11-18): function-level history (two-call stage with NEXT / DONE lines in its tool output), pinned; fixer examples solve from the history (scripts/make_sb7f.py)\n" + rest)
    files = lambda d: sorted(q.relative_to(d).as_posix() for q in d.rglob("*") if q.is_file())
    assert files(OUT) == files(SRC)
    for f in files(SRC):
        if f not in ("agent.yaml", "history.yaml", "prompts/history.md", "prompts/system.md"):
            assert (OUT / f).read_bytes() == (SRC / f).read_bytes(), f
    print("wrote submissions/sb7f | words history", len(h.split()), "fixer", len(s.split()))


if __name__ == "__main__":
    main()
