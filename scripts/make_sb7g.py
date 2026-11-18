"""sb7g = sb7f with the stage fixed (user 2026-11-18: 'raise the budget to 32, add example of the failing, and fix in
examples the three ticks, history done stop, make it easier ... say history now is fetched, you have all context, start
fixing'). Run: python3 -I scripts/make_sb7g.py

r116 (docs/PLAN.md RESULT r116): sb7f's stage broke on 4/8: the first command was sent with the example's ``` fence
inside it (sb7f stage 4/8 first calls; sb1 5 of 2,268 commands), no worked example for a failed command, so the model
improvised for 11-27 calls out of the run's one 28-call budget; a `test -e` cache re-printed a stale pick; calls after
HISTORY DONE in 3 runs. Changes, both prompts written fresh (scripts/agent_sb7g/):
  history stage: commands and outputs shown as 4-space-indented lines (no fence to copy; leading spaces are harmless
    in bash), sb1's 'shown as plain text ... nothing escaped' line, example 3 = a failed command -> the same command
    again with only its first line changed; a second failure -> reply 'No history.'; no cache (each call writes the
    file again); the stop line says '== HISTORY FETCHED: you have all the history the engineer needs. ...'.
  fixer: the pinned history under THE HISTORY IS FETCHED, followed by 'The history is fetched and you have all the
    context it gives: start fixing.'; the rest as sb7f's (examples that solve from the history, each naming the case).
  eval_config: max_tool_calls 32 (sb1 stays 28; the stage's two calls + two spare).
Bundle = sb7f's with the two prompts, eval_config's max_tool_calls, history.yaml's description and agent.yaml's comment changed."""
import importlib.util
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("make_sb78", ROOT / "scripts/make_sb78.py")
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)
SRC, OUT = ROOT / "submissions/sb7f", ROOT / "submissions/sb7g"
FETCHED = "== HISTORY FETCHED: you have all the history the engineer needs. Reply with everything above this line exactly as printed, and make no other call."
NEXT_OK = "== NEXT: pick the one or two functions above where the behaviour of the issue happens and run the second command with them."
NEXT_NONE = "== NEXT: no source line contains these names. Reply with the line: No history. Make no other call."


def indented_after(h, marker):
    """the 4-space-indented lines right after each marker line, de-indented"""
    out = []
    for m in re.finditer(re.escape(marker) + r"\n((?:    .*\n|\n(?=    ))+)", h):
        out.append("\n".join(l[4:] for l in m.group(1).rstrip("\n").split("\n")))
    return out


def main():
    h = (ROOT / "scripts/agent_sb7g/history.md").read_text()
    s = (ROOT / "scripts/agent_sb7g/system.md").read_text()
    M.check(h)
    M.check(s, ["{func_history?}"])
    M.examples(h)
    M.examples(s)
    assert "```" not in h, "history stage: no fences at all"
    assert "nothing escaped, and nothing added before or after them" in h
    cmds = indented_after(h, "command:")
    assert len(cmds) == 3, len(cmds)
    c1, c2, c3 = cmds
    assert c1 == c3, "the failed-command example resends exactly the first command"
    for c in cmds:
        assert '"' not in c and "`" not in c and "\\" not in c, "shell text: no double quotes, backticks, backslashes"
    assert c1.startswith("names='") and NEXT_OK in c1 and NEXT_NONE in c1 and "grep -n -p -w -F" in c1 and "core.attributesFile" in c1
    assert c2.startswith("funcs='") and c2.rstrip().endswith("echo '" + FETCHED + "'") and "log -L ':def '$fn'[(]:'$f -n 5" in c2
    assert "test -e" not in c2, "no cache: a re-pick prints the new functions"
    outs = indented_after(h, "The result's stdout was:")
    assert len(outs) == 2 and outs[0].rstrip().endswith(NEXT_OK) and outs[1].rstrip().endswith(FETCHED)
    rep = re.search(r"Your reply, with no tool call, is everything above the HISTORY FETCHED line:\n(.*?)\n\nExample 2", h, re.S).group(1)
    assert outs[1][:outs[1].index(FETCHED)].strip() == rep.strip(), "reply = stdout above the stop line"
    assert indented_after(h, "printed:") == [NEXT_NONE] and "Your reply, with no tool call:\nNo history." in h, "no-names case shown"
    assert "Example 3 - a command comes back with an error" in h and "a second time" in h and h.rstrip().endswith("No history.")
    assert "The history is fetched and you have all the context it gives: start fixing." in s
    ex = s[s.index("# EXAMPLES"):]
    for case in ("Example 1 - a past fix of the same kind", "Example 2 - the newest commit broke", "Example 3 - the history does not help"):
        assert case in ex, case
    assert ex.count("The reasoning names the case:") == 3
    assert "Tool call budget exhausted" in s and "old_string not found" in s and "mandatory input parameters are not present" in s
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SRC, OUT)
    (OUT / "prompts/history.md").write_text(h)
    (OUT / "prompts/system.md").write_text(s)
    ev = (SRC / "eval_config.yaml").read_text()
    assert ev.count("max_tool_calls: 28") == 1
    (OUT / "eval_config.yaml").write_text(ev.replace("max_tool_calls: 28", "max_tool_calls: 32"))
    hy = (SRC / "history.yaml").read_text()
    old_desc = "Lists the functions that use the issue's names, prints the history of the one or two that matter, and returns it. Makes two calls."
    assert hy.count(old_desc) == 1 and "output_key: func_history" in hy
    (OUT / "history.yaml").write_text(hy.replace(old_desc, "Fetches the history of the one or two functions the issue is about and returns it."))
    first, rest = (SRC / "agent.yaml").read_text().split("\n", 1)
    (OUT / "agent.yaml").write_text("# sb7g (2026-11-18): sb7f with the stage fixed (no fences, failed-command example, HISTORY FETCHED stop line, no cache), 32 calls (scripts/make_sb7g.py)\n" + rest)
    files = lambda d: sorted(q.relative_to(d).as_posix() for q in d.rglob("*") if q.is_file())
    assert files(OUT) == files(SRC)
    for f in files(SRC):
        if f not in ("agent.yaml", "history.yaml", "eval_config.yaml", "prompts/history.md", "prompts/system.md"):
            assert (OUT / f).read_bytes() == (SRC / f).read_bytes(), f
    print("wrote submissions/sb7g | words history", len(h.split()), "fixer", len(s.split()))


if __name__ == "__main__":
    main()
