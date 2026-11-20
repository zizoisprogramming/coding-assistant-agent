"""Prompts for the r129 arms (user 2026-11-20: 'we try both A and B with the rest of fixes and yes E3 + backslash alone as well').
Written fresh from sbE3's text (scripts/agent_expect/make_prompts.py single_e3, the same running Reader story); every command is
built from scripts/make_expect_e4.py's definitions byte for byte, every printed output is what those commands print.
  sbE3b = sbE3 + the backslash fallback in the edit step (+ a worked example of its note);
  sbE4A = sbE3b + a search stage before the solver: the solver's prompt carries the stage's lines and its example 1 starts with the
          expectation (no search call);
  sbE4B = sbE3b + WHEN lines and worked examples for the harness's 'tool call finished closing' message (calls sent as text) and
          for an existing test failing after the edit (fix forward, never undo the edit)."""
import make_prompts as P

E3_SEARCH_LINES = P.E3_SEARCH_OUT
HALVED_OUT = ("double backslashes in your text read as single ones\nold text found 1 times\nEDITED pkg/ansi.py\n")
CLOSING = "reached the token limit before the tool call finished closing"
LENIENT = ("FAILED tests/test_reader.py::test_read_lenient - ValueError: missing = in 'a'\n1 failed, 11 passed in 0.31s\n")


def solver(X, variant):
    E = X.EV3
    w = lambda k: E[k].split(":")[0]
    ecmd = lambda b: "tool: run_command\ncommand:\n```\n" + b + "```"
    edit = ecmd("mkdir -p .git/agent\ncat > .git/agent/old <<'OLD_TEXT'\n" + P.E3_OLD + "OLD_TEXT\ncat > .git/agent/new <<'NEW_TEXT'\n" + P.E3_NEW
                + "NEW_TEXT\n" + X.EDIT_STEP.replace("PATH", "pkg/reader.py"))
    A, B = variant == "sbE4A", variant == "sbE4B"
    names = ["halved"] + (["lenient"] if B else []) + ["eof"] + (["closing"] if B else []) + ["budget"]
    n = dict.fromkeys(("halved", "lenient", "eof", "closing", "budget"), 0) | {k: 9 + i for i, k in enumerate(names)}  # unused keys stay 0 (not printed)
    stage = ("\n# WHERE THE CODE AND ITS TESTS ARE\nBefore you started, a search of this repository for the names in the issue found these lines: where the "
             "names are defined and test lines that call them. They stay here for the whole task.\n{evidence?}\n") if A else ""
    if A:
        step2 = ("2. The search is already done: the section WHERE THE CODE AND ITS TESTS ARE shows where the issue's names are defined and the test "
                 "lines that call them. Use it instead of searching. Only when it says NOTHING RELEVANT, or lacks the code the issue names, search with "
                 "one run_command: `git grep -nF 'exact_name' -- '*.py' | head -20; git grep -n 'exact_name(' -- '*test*' | head -10`.")
        step3 = "3. Your first call is the expectation (example 1)"
        style = "in the style of the test lines in that section"
    else:
        step2 = ("2. Find the code and the tests that call it with one run_command (example 1): `git grep -nF 'exact_name' -- '*.py' | head -20; "
                 "git grep -n 'exact_name(' -- '*test*' | head -10`, single quotes around search text. Use paths named in the issue directly.")
        step3 = "3. Right after that search, write the expectation (example 1)"
        style = "in the style of the test lines the search printed"
    rules = [f"- \"{w('shown')}\": the problem is shown; read the code and edit it so the expectation passes (example 4).",
             f"- \"{w('nothing')}\": the expectation called something that already works. Look at the issue again: call the code through its construct (the class, model, decorator, option or call it shows) with its inputs, and send the expectation command again (example 2).",
             f"- \"{w('refused')}\": send the expectation command first, then the same edit again (example 3).",
             f"- \"{w('broken')}\": the script has an error of its own; fix the script and send the expectation command again (example 6).",
             f"- \"{w('still')}\": the edit did not give the wanted behaviour; read the failure lines and edit the source again (example 5).",
             f"- \"{w('done')}\": run the existing test file of this code, then finish (example 4).",
             f"- \"{w('late')}\": stop investigating; edit the place your reading points to now, and let the expectation judge it (example 7).",
             f"- \"old text found 0 times\": the old lines differ from the file. Read that region again with read_file and copy the lines from the new output (example 8).",
             f"- \"{X.HALVED}\": nothing to do; the edit was applied as you meant it (example {n['halved']})."]
    if B:
        rules.append(f"- \"failed\" in the run of the existing test file after your edit: read which test fails and why, and edit the source again so that test and the expectation both pass. Never undo your edit with git checkout, git stash or git reset: an unedited tree scores zero (example {n['lenient']}).")
    rules.append(f"- \"unexpected EOF while looking for matching\": the command was sent with the ``` lines that surround it in these examples. Send the same command again, from its first real line to its last, without them (example {n['eof']}).")
    if B:
        rules.append(f"- \"{CLOSING}\": your call was not sent; it ended with a ``` line instead of right after its last line. Send the same call again, ending right after its last line, with nothing after it (example {n['closing']}).")
    rules.append(f"- \"Tool call budget exhausted\": every other tool is closed now, but `submit_patch` still works. Call `submit_patch`, then reply with one sentence (example {n['budget']}).")
    if A:
        ex1 = (f"Example 1 - the issue says: Reader ignores strict. Reader(strict=True).read('a') returns a result with an empty value instead of raising ValueError, as parse('a', strict=True) does. The section WHERE THE CODE AND ITS TESTS ARE held:\n```\n{E3_SEARCH_LINES}```\n"
               f"The first call is the expectation. It calls Reader the way the issue and tests/test_reader.py do:\n{ecmd(X.expect_cmd(P.E3_EXP))}")
    else:
        ex1 = (f"Example 1 - the issue says: Reader ignores strict. Reader(strict=True).read('a') returns a result with an empty value instead of raising ValueError, as parse('a', strict=True) does. The first call finds the code and the tests that call it:\n{ecmd(P.E3_SEARCH)}\nIt printed:\n```\n{E3_SEARCH_LINES}```\n"
               f"The second call is the expectation. It calls Reader the way the issue and tests/test_reader.py do:\n{ecmd(X.expect_cmd(P.E3_EXP))}")
    extra = {
        "halved": (f"Example {n['halved']} - an edit of a line with backslashes, such as a regular expression. Tool results show every backslash of a file doubled, so old text copied from them carries double backslashes; the edit step reads them as single ones when that is what the file has. It printed:\n```\n{HALVED_OUT}```\n"
                   "The edit was applied as meant; the steps go on as after any edit (example 4)."),
        "lenient": (f"Example {n['lenient']} - an existing test that fails after the edit. Had the edit of example 4 called parse(text, strict=True), the expectation would pass, and then `timeout 150 python -m pytest tests/test_reader.py -x -q` would have printed:\n```\n{LENIENT}```\n"
                    "test_read_lenient calls Reader().read('a') with strict left at False, and the edit raised anyway. The edit stays and is corrected: the edit of example 4, with parse(text, strict=self.strict), goes next, and then the test file runs again. The edit is never undone with git checkout, git stash or git reset."),
        "eof": (f"Example {n['eof']} - a tool result says \"unexpected EOF while looking for matching\": the command had been sent with the ``` line above its first line and the ``` line below its last line. The same command goes again, from its first line to its last, with nothing before or after."),
        "closing": (f"Example {n['closing']} - instead of a tool result, a message says \"Your previous response {CLOSING}\": the call had ended with the ``` line of these examples after bash .git/agent/check.sh, so it was never sent. The same call goes again, unchanged, ending right after bash .git/agent/check.sh."),
        "budget": (f"Example {n['budget']} - a tool result says \"Tool call budget exhausted\":\ntool: submit_patch\nThen reply: Made Reader.read pass strict to parse, so Reader(strict=True) raises ValueError for text without '='."),
    }
    return f"""{P.INTRO}
{stage}
# KEEP GOING UNTIL IT IS DONE
You are graded on the working tree as it stands when the task ends, even if time runs out first. A tree with your edit in it can pass; an unedited tree always scores zero. So keep working until you have edited the source and called `submit_patch`. As soon as your expectation fails for the reason the issue gives, make the edit, even if you are only fairly sure: the expectation runs again after every edit and tells you.

# HOW TO WORK
1. Read the issue and write down the exact names, messages, inputs and options it mentions, the construct through which the problem happens (the class, model, decorator, option or call the issue shows), and what it says must change.
{step2}
{step3}: a short script of asserts that calls the code through the same construct, with the same inputs and options, as the issue, {style}, and states the result the issue wants. It must FAIL on the code as it is now and PASS once the fix is in; the lines after it run it and say which. An edit sent before any expectation exists is held back once (example 3).
4. {P.EDIT_HOW} The edit runs the expectation again and says whether it passes now (example 4).
5. When the expectation passes: run the existing test file: `timeout 150 python -m pytest tests/path/test_x.py -x -q`. Failures from missing fixtures or unrelated imports were there before you; leave them. If your change breaks a test, fix the source and run it once more.
6. Finish: run `git status --short && git diff`, remove any scratch file left in /workspace, then call `submit_patch` and end with one sentence that sums up the fix.

Edit only source files. Test files (`test_*.py`, `*_test.py`, anything under `tests/`, `conftest.py`) stay exactly as they are, and every test run names one test file. The expectation lives in .git/agent, so it is never part of the change; to run it again on its own, send `{X.RERUN}`.

# HOW THE EXPECTATION AND AN EDIT ARE MADE
The expectation is one run_command in the shape of {'the call' if A else 'the second call'} of example 1: the asserts go between the EXPECT lines, and the lines after them stay exactly as shown. Every change to a source file is one run_command in the shape of example 4: the old lines go between the OLD_TEXT lines, the new lines between the NEW_TEXT lines, both exactly as read_file printed them, and the steps after them stay exactly as shown; they replace the old text only when it occurs exactly once, show the changed lines, and run the expectation again.

# WHEN A TOOL RESULT SAYS ...
{chr(10).join(rules)}

# EXAMPLES
Each call is shown as plain text: the tool name, then each argument name and its exact text. Write your own calls the same way, with real line breaks and nothing escaped.

{ex1}
It printed:
```
{P.E3_TB}{E['shown']}
```
The problem is shown, so the next step is to read the code and edit it (example 4).

Example 2 - an expectation that is not the issue's case. It had called parse('a', strict=True), the function the issue compares with, and parse already raises. It printed:
```
{E['nothing']}
```
The issue's construct is Reader(strict=True).read, so the expectation command of example 1 goes again with the asserts of example 1, which call Reader as the issue does. In other issues the construct is a model class, a decorator, a subclass, an option, an async version or a config object: the expectation goes through that same one.

Example 3 - an edit sent before any expectation. The edit of example 4 went first, and it printed:
```
old text found 1 times
{E['refused']}
```
The expectation command of example 1 goes next, then the edit of example 4 again, unchanged; this time it is applied.

Example 4 - an edit after a failing expectation. read_file on pkg/reader.py, lines 8 to 14, printed:
```
{P.E3_READ}```
The edit goes inside read and keeps its parameters (self, text). The old lines are copied from that output:
{edit}
It printed:
```
old text found 1 times
EDITED pkg/reader.py
{P.E3_DIFF}{E['done']}
```
The next call runs the existing test file, then the task finishes.

Example 5 - an edit that does not give the wanted behaviour yet. Had the edit changed __init__ and left read calling parse(text), it would have printed:
```
old text found 1 times
EDITED pkg/reader.py
{P.E3_TB}{E['still']}
```
The failure says Reader(strict=True) still accepts text without '=', so the edit goes again at read, where parse is called (example 4).

Example 6 - a broken expectation script. It printed:
```
  File "/workspace/.git/agent/expect.py", line 3
    try
       ^
SyntaxError: expected ':'
{E['broken']}
```
The try line had lost its colon; the expectation command of example 1 goes again with try: written correctly.

Example 7 - the expectation is run again with `{X.RERUN}` after more reading, and nothing has been edited. It printed:
```
{P.E3_TB}{E['shown']}
{E['late']}
```
The check already fails for the reason the issue gives and the reading points at read in Reader, so the edit of example 4 goes now, without more checks.

Example 8 - the result says 'old text found 0 times'. The old lines had been typed from memory instead of copied. read_file on pkg/reader.py, lines 12 to 13, printed:
```
    def read(self, text):
        return parse(text.strip())
```
The file says parse(text.strip()), not parse(text). The edit of example 4 goes again with these old lines copied from this output, text.strip() in both the old and the new text, and the same steps after them.

{chr(10).join(chr(10) + extra[k] if i else extra[k] for i, k in enumerate(names))}
"""


SEARCH_OUT = ("WHERE THE ISSUE'S NAMES ARE, for Reader, strict (read-only searches; the issue stays the specification)\n== Reader\ndefined at:\n  pkg/reader.py:8:class Reader:\n"
              "tests that use it: 2 lines\n  tests/test_reader.py:14:    assert Reader().read('a=1')['a'] == '1'\n  tests/test_reader.py:20:    assert Reader().read('') == dict()\n"
              "== strict\nused in source: 3 lines\n  pkg/parser.py:1:def parse(text, strict=False):\n  pkg/reader.py:9:    def __init__(self, strict=False):\n  pkg/reader.py:10:        self.strict = strict\n"
              "tests that use it: 1 lines\n  tests/test_parser.py:9:    assert parse('a=1', strict=True)['a'] == '1'\n")
SEARCH_REPLY = ("pkg/reader.py:8:class Reader:\npkg/reader.py:9:    def __init__(self, strict=False):\ntests/test_reader.py:14:    assert Reader().read('a=1')['a'] == '1'\n"
                "pkg/parser.py:1:def parse(text, strict=False):\ntests/test_parser.py:9:    assert parse('a=1', strict=True)['a'] == '1'\n")


def stage(X):
    return f"""Your only job is one search of the repository for the engineer who fixes the issue after you. Your reply is copied into the engineer's instructions and stays there for the whole task, so it must hold real lines from the repository, not your opinions. You will not read code and you will not work on the fix.

Choose two to four exact names from the issue below that the problem goes through: functions, methods, classes, options or parameters, written exactly as in the issue. Include the construct the issue shows (the class, model or decorator it uses), and prefer specific names, such as convert_underscores, over common words, such as Header.

Call run_skill_script with skill_name evidence, file_path scripts/evidence.py and positional_args holding those names, one name per item. That is your only call.

Then reply with the lines of its result that show where the names are defined and the test lines that call them, each copied exactly as printed with its file:line, at most 12 lines and nothing else. If nothing in the result bears on the issue, reply with the single line NOTHING RELEVANT.

# EXAMPLE
The issue says: Reader ignores strict. Reader(strict=True).read('a') returns a result with an empty value instead of raising ValueError, as parse('a', strict=True) does. The call:
tool: run_skill_script
skill_name: evidence
file_path: scripts/evidence.py
positional_args: Reader, strict
It printed:
```
{SEARCH_OUT}```
The reply, with no tool call:
{SEARCH_REPLY}
# THE ISSUE (verbatim)
{{problem_description}}"""
