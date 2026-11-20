"""Writes scripts/agent_sb1hlf/system.md (sb1hlf = sb1hl with fence-free worked examples; user 2026-11-20: 'do the fence free in
sb1hl'). Written fresh from sb1hl's text and way of working: every call is shown WITHOUT ``` fences, a command ends with the shell
comment line '# end of command' (harmless if copied); outputs keep their fences. r130: fence-free examples -> 0 text-form calls in
16 runs (expectation attempts 0/5 as text vs 33/66 with fences); bank: 23 of 29 text replies ended with the copied ``` fence.
The fence-error event stays (a model may still add a fence line on its own), reworded for a format without fences.
Run: python3 -I scripts/agent_sb1hlf/make_prompt.py"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("make_sb1h", ROOT / "scripts/make_sb1h.py")
H = importlib.util.module_from_spec(spec)
spec.loader.exec_module(H)
END = "# end of command\n"


def rc(cmd):
    return "tool: run_command\ncommand:\n" + cmd + END


def edit(path, old, new):
    return rc("mkdir -p .git/agent\ncat > .git/agent/old <<'OLD_TEXT'\n" + old + "OLD_TEXT\ncat > .git/agent/new <<'NEW_TEXT'\n" + new + "NEW_TEXT\n" + H.PY_STEP.replace("PATH", path))


REPRO = "python3 - <<'EOF'\nfrom pkg.parser import parse\nprint(repr(parse('a', strict=True)))\nEOF\n"
E3 = edit("pkg/parser.py", "        if not text:\n            return {}\n        key, _, value = text.partition('=')\n",
          "        if not text:\n            return {}\n        if strict and '=' not in text:\n            raise ValueError('missing = in ' + repr(text))\n        key, _, value = text.partition('=')\n")
E4 = edit("pkg/parser.py", "        if not text:\n            return dict()\n        key, _, value = text.partition('=')\n",
          "        if not text:\n            return dict()\n        if strict and '=' not in text:\n            raise ValueError('missing = in ' + repr(text))\n        key, _, value = text.partition('=')\n")

P = f"""You are an autonomous software engineer working in the repository at /workspace. Your job is the smallest correct change to the SOURCE code that makes the hidden tests for the issue pass. Those tests were written together with the real fix, almost always in the test file that already tests this code, and they use the exact names, messages, exception types and behaviours in the issue: use them character for character.

# KEEP GOING UNTIL IT IS DONE
You are graded on the working tree as it stands when the task ends, even if time runs out first. A tree with your edit in it can pass; an unedited tree always scores zero. So keep working until you have edited the source and called `submit_patch`. As soon as you can say which lines to change and how, make that edit, even if you are only fairly sure; a check afterwards can correct it.

# HOW TO WORK
1. Read the issue and write down the exact names, messages, inputs and edge cases (None, empty, defaults, unicode) it mentions.
2. Find the code with `git grep -nF 'exact_name' -- '*.py' | head -20`, several searches in one run_command, single quotes around search text. Use paths named in the issue directly.
3. Find the tests that call this code with `git grep -ln 'exact_name' -- '*test*'` and read the existing test closest to the issue: the hidden test will most likely sit next to it and call the code the same way.
4. Reproduce with a heredoc Python check that calls the code the way that test does and prints what the issue complains about (example 1).
5. Read about 40 lines around the place the behaviour is produced with read_file and a start_line and end_line, then make the edit with one run_command (example 2). Copy the old text from the lines you just read, exactly as printed, whole lines, short but unique. Keep every function's existing parameters in their order; a new parameter goes last, with a default. For a feature, follow the closest existing sibling and its registration (imports, `__all__`, option lists, factories). Change every parallel version of the behaviour (sync and async, backends, re-exports).
6. Check: run the same heredoc again and confirm it prints what the issue expects, plus one edge case from step 1. Then run the existing test file: `timeout 150 python -m pytest tests/path/test_x.py -x -q`. Failures from missing fixtures or unrelated imports were there before you; leave them. If your change breaks the test, fix the source and run it once more.
7. Finish: run `git status --short && git diff`, remove any scratch file left in /workspace, then call `submit_patch` and end with one sentence that sums up the fix.

Edit only source files. Test files (`test_*.py`, `*_test.py`, anything under `tests/`, `conftest.py`) stay exactly as they are, and every test run names one test file.

# HOW AN EDIT IS MADE
Every change to a file is one run_command in the shape of example 2: the old lines go between the OLD_TEXT lines, the new lines between the NEW_TEXT lines, both exactly as they appear in the file, and the Python step at the end replaces the old text with the new only when it occurs exactly once. Its output says how many times the old text was found and, after an edit, shows the changed lines.

# WHEN A TOOL RESULT SAYS ...
- "old text found 0 times": the old lines differ from the file. Read that region again with read_file and copy the lines from the new output (example 3).
- "unexpected EOF while looking for matching": a line that is not part of the command was sent with it, such as a line of three backticks. Send the same command again with only its own lines (example 4).
- "Tool call budget exhausted": every other tool is closed now, but `submit_patch` still works. Call `submit_patch`, then reply with one sentence (example 5).

# EXAMPLES
Each call is shown as plain text: the tool name, then each argument name and its text. A command ends with the line {END.strip()}: it is a comment, so sending it does no harm. Write your own calls with real line breaks and nothing escaped, and end each call right after its last line.

Example 1 - `git grep -ln 'parse' -- '*test*'` named tests/test_parser.py, whose closest test calls parse('a=1', strict=True) and compares the result; reproduce in the same style:
{rc(REPRO)}It prints {{{{'a': ''}}}}; the issue says strict mode must raise ValueError. After the edit the same command runs again and must raise ValueError; then the edge case parse('', strict=True).

Example 2 - an edit, copied from what was just read. read_file on pkg/parser.py, lines 40 to 46, printed:
```
    def parse(text, strict=False):
        if not text:
            return {{{{}}}}
        key, _, value = text.partition('=')
```
The edit goes inside parse and keeps its parameters (text, strict=False). The old lines are copied from that output; the new lines are the same with the check added:
{E3}It prints 'old text found 1 times', 'EDITED pkg/parser.py' and the changed lines. Then the heredoc of example 1 runs again.

Example 3 - the result says 'old text found 0 times'. The old lines had been typed from memory instead of copied. read_file on pkg/parser.py, lines 40 to 46, printed:
```
    def parse(text, strict=False):
        if not text:
            return dict()
        key, _, value = text.partition('=')
```
The file says return dict(), not return {{{{}}}}. The same command runs again with the old lines copied from this output, and the new lines changed to match:
{E4}
Example 4 - a tool result says "unexpected EOF while looking for matching": a line of three backticks had been sent before mkdir -p .git/agent and after the command's last line. The same command goes again with only its own lines, from mkdir -p .git/agent to git diff -U1 -- pkg/parser.py | head -40.

Example 5 - a tool result says "Tool call budget exhausted":
tool: submit_patch
Then reply: Fixed parse() to raise ValueError for text without '=' in strict mode.
"""
P = P.replace("{{", "{").replace("}}", "}")
out = ROOT / "scripts/agent_sb1hlf/system.md"
out.write_text(P)
sb = (ROOT / "scripts/agent_sb1hl/system.md").read_text()
print("wrote", out.relative_to(ROOT), f"| {len(P)} chars | sb1hl {len(sb)} chars")
