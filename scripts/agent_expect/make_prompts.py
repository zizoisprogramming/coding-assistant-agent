"""Writes the expectation arms' prompts (scripts/agent_expect/sbE1.md, sbE2.md, sbX1_expect.md, sbX1_solver.md). The prose is
written here, fresh, from sb1hl's way of working; every expectation command and edit command is built from make_expect_arms'
definitions byte for byte, and every printed output is what those commands print. Called by scripts/make_expect_arms.py."""
from pathlib import Path

HERE = Path(__file__).resolve().parent

EXP_BODY = ("from pkg.parser import parse\n\ntry:\n    parse('a', strict=True)\nexcept ValueError:\n    pass\nelse:\n"
            "    raise AssertionError('strict mode accepted text without =')\nassert parse('a=1', strict=True)['a'] == '1'\n")
EXP_WEAK = "from pkg.parser import parse\n\nassert parse('a=1')['a'] == '1'\n"
TB = ("Traceback (most recent call last):\n  File \"/workspace/.git/agent/expect.py\", line 8, in <module>\n"
      "    raise AssertionError('strict mode accepted text without =')\nAssertionError: strict mode accepted text without =\n")
PARSE_READ = "    def parse(text, strict=False):\n        if not text:\n            return {}\n        key, _, value = text.partition('=')\n"
PARSE_OLD = "        if not text:\n            return {}\n        key, _, value = text.partition('=')\n"
PARSE_NEW = ("        if not text:\n            return {}\n        if strict and '=' not in text:\n            raise ValueError('missing = in ' + repr(text))\n"
             "        key, _, value = text.partition('=')\n")
DIFF = ("diff --git a/pkg/parser.py b/pkg/parser.py\nindex 3c1d2e4..8a9b0c1 100644\n--- a/pkg/parser.py\n+++ b/pkg/parser.py\n"
        "@@ -42,2 +42,4 @@ def parse(text, strict=False):\n             return {}\n+        if strict and '=' not in text:\n"
        "+            raise ValueError('missing = in ' + repr(text))\n         key, _, value = text.partition('=')\n")
NOTE = ("WANTED BEHAVIOUR: parse(text, strict=True) must raise ValueError when the text has no '='; text with '=' keeps working.\n"
        "CHECK: .git/agent/expect.py calls parse('a', strict=True) and parse('a=1', strict=True); it fails now with AssertionError: strict mode accepted text without =.\n"
        "CODE: pkg/parser.py, parse, where the text is split at '='.")
INTRO = ("You are an autonomous software engineer working in the repository at /workspace. Your job is the smallest correct change to the SOURCE code "
         "that makes the hidden tests for the issue pass. Those tests were written together with the real fix, almost always in the test file that already "
         "tests this code, and they use the exact names, messages, exception types and behaviours in the issue: use them character for character.")
KEEP = ("# KEEP GOING UNTIL IT IS DONE\nYou are graded on the working tree as it stands when the task ends, even if time runs out first. A tree with your edit "
        "in it can pass; an unedited tree always scores zero. So keep working until you have edited the source and called `submit_patch`. As soon as your "
        "expectation fails for the reason the issue gives, make the edit, even if you are only fairly sure: the expectation runs again after every edit and tells you.")
FIND = ("2. Find the code with `git grep -nF 'exact_name' -- '*.py' | head -20`, several searches in one run_command, single quotes around search text. "
        "Use paths named in the issue directly.\n3. Find the tests that call this code with `git grep -ln 'exact_name' -- '*test*'` and read the existing test "
        "closest to the issue: the hidden test will most likely sit next to it and call the code the same way.")
EDIT_HOW = ("Read about 40 lines around the place the behaviour is produced with read_file and a start_line and end_line, then make the edit with one "
            "run_command. Copy the old text from the lines you just read, exactly as printed, whole lines, short but unique. Keep every function's existing "
            "parameters in their order; a new parameter goes last, with a default. For a feature, follow the closest existing sibling and its registration "
            "(imports, `__all__`, option lists, factories). Change every parallel version of the behaviour (sync and async, backends, re-exports).")
TAIL_RULES = ("- \"old text found 0 times\": the old lines differ from the file. Read that region again with read_file and copy the lines from the new output (example {f0}).\n"
              "- \"unexpected EOF while looking for matching\": the command was sent with the ``` lines that surround it in these examples. Send the same command again, from its first real line to its last, without them (example {fe}).\n"
              "- \"Tool call budget exhausted\": every other tool is closed now, but `submit_patch` still works. Call `submit_patch`, then reply with one sentence (example {fb}).")


def block(cmd):
    return "tool: run_command\ncommand:\n```\n" + cmd + "```"


def edit_cmd(X, path, old, new):
    return block("mkdir -p .git/agent\ncat > .git/agent/old <<'OLD_TEXT'\n" + old + "OLD_TEXT\ncat > .git/agent/new <<'NEW_TEXT'\n" + new + "NEW_TEXT\n" + X.EDIT_STEP.replace("PATH", path))


def single(X, arm):
    E = X.EV
    late = arm == "sbE2"
    n = 7 if late else 6
    rules = [f"- \"{E['shown_e'].split(':')[0]}\": the problem is shown; read the code and edit it so the expectation passes (example 3).",
             f"- \"{E['nothing'].split(':')[0]}\": your expectation does not show the problem yet; change its asserts to what the issue says must change, and send the expectation command again (example 2).",
             f"- \"{E['broken'].split(':')[0]}\": the script has an error of its own; fix the script and send the expectation command again (example 5).",
             f"- \"{E['still'].split(':')[0]}\": the edit did not give the wanted behaviour; read the failure lines and edit the source again (example 4).",
             f"- \"{E['done'].split(':')[0]}\": run the existing test file of this code, then finish (example 3)."]
    if late:
        rules.append(f"- \"{E['late'].split(':')[0]}\": stop investigating; edit the place your reading points to now, and let the expectation judge it (example 6).")
    rules.append(TAIL_RULES.format(f0=n, fe=n + 1, fb=n + 2))
    ex6 = ""
    if late:
        ex6 = (f"\nExample 6 - the expectation is run again with `{X.RERUN}` after more reading, and nothing has been edited. It printed:\n```\n{TB}{E['shown_e']}\n{E['late']}\n```\n"
               "The reasoning: the check already fails for the reason the issue gives and the reading points at the split in parse, so the edit of example 3 goes now, without more checks.\n")
    return f"""{INTRO}

{KEEP}

# HOW TO WORK
1. Read the issue and write down the exact names, messages, inputs and edge cases (None, empty, defaults, unicode) it mentions, and what the issue says must change.
{FIND}
4. Write the expectation (example 1): a short script of asserts that calls the code the way that test does and states the result the issue wants. It must FAIL on the code as it is now, because the problem is still there, and PASS once the fix is in. The steps after it run it and say which.
5. {EDIT_HOW} The edit runs the expectation again and says whether it passes now (example 3).
6. When the expectation passes: run the existing test file: `timeout 150 python -m pytest tests/path/test_x.py -x -q`. Failures from missing fixtures or unrelated imports were there before you; leave them. If your change breaks a test, fix the source and run it once more.
7. Finish: run `git status --short && git diff`, remove any scratch file left in /workspace, then call `submit_patch` and end with one sentence that sums up the fix.

Edit only source files. Test files (`test_*.py`, `*_test.py`, anything under `tests/`, `conftest.py`) stay exactly as they are, and every test run names one test file. The expectation lives in .git/agent, so it is never part of the change; to run it again on its own, send `{X.RERUN}`.

# HOW THE EXPECTATION AND AN EDIT ARE MADE
The expectation is one run_command in the shape of example 1: the asserts go between the EXPECT lines, and the lines after them stay exactly as shown. Every change to a source file is one run_command in the shape of example 3: the old lines go between the OLD_TEXT lines, the new lines between the NEW_TEXT lines, both exactly as they appear in the file, and the steps after them stay exactly as shown; they replace the old text only when it occurs exactly once, show the changed lines, and run the expectation again.

# WHEN A TOOL RESULT SAYS ...
{chr(10).join(rules)}

# EXAMPLES
Each call is shown as plain text: the tool name, then each argument name and its exact text. Write your own calls the same way, with real line breaks and nothing escaped.

Example 1 - the issue says strict mode must reject text without '='. `git grep -ln 'parse' -- '*test*'` named tests/test_parser.py, whose closest test calls parse('a=1', strict=True) and compares the result. The expectation states the wanted behaviour in the same style:
{block(X.expect_cmd(arm, EXP_BODY))}
It printed:
```
{TB}{E['shown_e']}
```
The problem is shown, so the next step is to read the code and edit it.

Example 2 - an expectation that does not show the problem. It had asserted only parse('a=1')['a'] == '1', which already works, and it printed:
```
{E['nothing']}
```
The issue is about strict mode and text without '=', so the expectation command of example 1 goes again with the asserts of example 1, which call parse('a', strict=True).

Example 3 - an edit after a failing expectation. read_file on pkg/parser.py, lines 40 to 46, printed:
```
{PARSE_READ}```
The edit goes inside parse and keeps its parameters (text, strict=False). The old lines are copied from that output:
{edit_cmd(X, 'pkg/parser.py', PARSE_OLD, PARSE_NEW)}
It printed:
```
old text found 1 times
EDITED pkg/parser.py
{DIFF}{E['done']}
```
The next call runs the existing test file, then the task finishes.

Example 4 - an edit that does not give the wanted behaviour yet. Had the new lines raised only for empty text, the edit would have printed:
```
old text found 1 times
EDITED pkg/parser.py
{TB}{E['still']}
```
The failure says text without '=' is still accepted, so the edit goes again with the check of example 3: strict and '=' not in text.

Example 5 - a broken expectation script. It printed:
```
  File "/workspace/.git/agent/expect.py", line 3
    try
       ^
SyntaxError: expected ':'
{E['broken']}
```
The try line had lost its colon; the expectation command of example 1 goes again with try: written correctly.
{ex6}
Example {n} - the result says 'old text found 0 times'. The old lines had been typed from memory instead of copied. read_file on pkg/parser.py, lines 40 to 46, printed:
```
    def parse(text, strict=False):
        if not text:
            return dict()
        key, _, value = text.partition('=')
```
The file says return dict(), not return {{}}. The edit of example 3 goes again with these old lines copied from this output, return dict() in both the old and the new text, and the same steps after them.

Example {n + 1} - a tool result says "unexpected EOF while looking for matching": the command had been sent with the ``` line above its first line and the ``` line below its last line. The same command goes again, from its first line to its last, with nothing before or after.

Example {n + 2} - a tool result says "Tool call budget exhausted":
tool: submit_patch
Then reply: Fixed parse() to raise ValueError for text without '=' in strict mode.
"""


def x1_expect(X):
    E = X.EV
    return f"""You write the expectation for the issue below before an engineer fixes it. Your only job is a short script, .git/agent/expect.py, whose asserts state the behaviour the issue wants, calling the code the way its closest existing test does, and which FAILS on the code as it is now because the problem is still there. You do not change any source file; the engineer does that after you.

# HOW TO WORK
1. Read the issue and write down the exact names, messages, inputs and edge cases it mentions, and what it says must change.
{FIND}
4. Write the expectation with one run_command in the shape of example 1: the asserts go between the EXPECT lines, and the lines after them stay exactly as shown. They run it and say what to do next.
5. When it says the problem is shown, reply with the note of example 1, with no tool call. That reply is all the engineer gets from you.

# WHEN A TOOL RESULT SAYS ...
- "{E['shown_x'].split(':')[0]}": the problem is shown; reply with the WANTED BEHAVIOUR note (example 1).
- "{E['nothing'].split(':')[0]}": your expectation does not show the problem yet; change its asserts to what the issue says must change and send the command again (example 2).
- "{E['broken'].split(':')[0]}": the script has an error of its own; fix it and send the command again (example 3).
- "unexpected EOF while looking for matching": the command was sent with the ``` lines that surround it in these examples. Send it again, from its first real line to its last, without them (example 4).

# EXAMPLES
Each call is shown as plain text: the tool name, then each argument name and its exact text. Write your own calls the same way, with real line breaks and nothing escaped.

Example 1 - the issue says strict mode must reject text without '='. `git grep -ln 'parse' -- '*test*'` named tests/test_parser.py, whose closest test calls parse('a=1', strict=True) and compares the result; `git grep -nF 'def parse' -- '*.py'` found it in pkg/parser.py. The expectation:
{block(X.expect_cmd('sbX1', EXP_BODY))}
It printed:
```
{TB}{E['shown_x']}
```
The reply, with no tool call:
{NOTE}

Example 2 - an expectation that does not show the problem. It had asserted only parse('a=1')['a'] == '1', which already works, and it printed:
```
{E['nothing']}
```
The issue is about strict mode and text without '=', so the command of example 1 goes again with the asserts of example 1.

Example 3 - a broken expectation script. It printed:
```
  File "/workspace/.git/agent/expect.py", line 3
    try
       ^
SyntaxError: expected ':'
{E['broken']}
```
The try line had lost its colon; the command of example 1 goes again with try: written correctly.

Example 4 - a tool result says "unexpected EOF while looking for matching": the command had been sent with the ``` line above its first line and the ``` line below its last line. The same command goes again, from its first line to its last, with nothing before or after.
"""


def x1_solver(X):
    E = X.EV
    return f"""{INTRO}

# THE WANTED BEHAVIOUR
Before you started, a teammate wrote .git/agent/expect.py, a check that states the behaviour the issue wants and fails on the code as it is now, and left this note:
{{expectation?}}

# KEEP GOING UNTIL IT IS DONE
You are graded on the working tree as it stands when the task ends, even if time runs out first. A tree with your edit in it can pass; an unedited tree always scores zero. So keep working until you have edited the source and called `submit_patch`. Make the edit as soon as you can say which lines to change: the check runs again after every edit and tells you.

# HOW TO WORK
1. Read the issue and the note above. Go to the code the note names; if it names none, find it with `git grep -nF 'exact_name' -- '*.py' | head -20`.
2. {EDIT_HOW} The edit runs the check again and says whether it passes now (example 1).
3. When the check passes: run the existing test file: `timeout 150 python -m pytest tests/path/test_x.py -x -q`. Failures from missing fixtures or unrelated imports were there before you; leave them. If your change breaks a test, fix the source and run it once more.
4. Finish: run `git status --short && git diff`, remove any scratch file left in /workspace, then call `submit_patch` and end with one sentence that sums up the fix.

Edit only source files. Test files (`test_*.py`, `*_test.py`, anything under `tests/`, `conftest.py`) stay exactly as they are, and every test run names one test file. The check lives in .git/agent, so it is never part of the change.

# HOW AN EDIT IS MADE
Every change to a file is one run_command in the shape of example 1: the old lines go between the OLD_TEXT lines, the new lines between the NEW_TEXT lines, both exactly as they appear in the file, and the steps after them stay exactly as shown; they replace the old text only when it occurs exactly once, show the changed lines, and run the check again.

# WHEN A TOOL RESULT SAYS ...
- "{E['done'].split(':')[0]}": run the existing test file of this code, then finish (example 1).
- "{E['still'].split(':')[0]}": the edit did not give the wanted behaviour; read the failure lines and edit the source again (example 2).
{TAIL_RULES.format(f0=3, fe=4, fb=5)}

# EXAMPLES
Each call is shown as plain text: the tool name, then each argument name and its exact text. Write your own calls the same way, with real line breaks and nothing escaped.

Example 1 - the note says parse(text, strict=True) must raise ValueError for text without '=', in pkg/parser.py. read_file on pkg/parser.py, lines 40 to 46, printed:
```
{PARSE_READ}```
The edit goes inside parse and keeps its parameters (text, strict=False). The old lines are copied from that output:
{edit_cmd(X, 'pkg/parser.py', PARSE_OLD, PARSE_NEW)}
It printed:
```
old text found 1 times
EDITED pkg/parser.py
{DIFF}{E['done']}
```
The next call runs the existing test file, then the task finishes.

Example 2 - an edit that does not give the wanted behaviour yet. Had the new lines raised only for empty text, the edit would have printed:
```
old text found 1 times
EDITED pkg/parser.py
{TB}{E['still']}
```
The failure says text without '=' is still accepted, so the edit goes again with the check of example 1: strict and '=' not in text.

Example 3 - the result says 'old text found 0 times'. The old lines had been typed from memory instead of copied. read_file on pkg/parser.py, lines 40 to 46, printed:
```
    def parse(text, strict=False):
        if not text:
            return dict()
        key, _, value = text.partition('=')
```
The file says return dict(), not return {{}}. The edit of example 1 goes again with these old lines copied from this output, return dict() in both the old and the new text, and the same steps after them.

Example 4 - a tool result says "unexpected EOF while looking for matching": the command had been sent with the ``` line above its first line and the ``` line below its last line. The same command goes again, from its first line to its last, with nothing before or after.

Example 5 - a tool result says "Tool call budget exhausted":
tool: submit_patch
Then reply: Fixed parse() to raise ValueError for text without '=' in strict mode.
"""


def write_all(X):
    (HERE / "sbE1.md").write_text(single(X, "sbE1"))
    (HERE / "sbE2.md").write_text(single(X, "sbE2"))
    (HERE / "sbX1_expect.md").write_text(x1_expect(X))
    (HERE / "sbX1_solver.md").write_text(x1_solver(X))
