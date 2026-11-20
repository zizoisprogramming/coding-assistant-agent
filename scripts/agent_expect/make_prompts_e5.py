"""Prompts for the r130 expectation arms (user 2026-11-20: 'do what u proposed + few shot, on 2 tasks only please and yes besides sb1
and sb1hl'). Written fresh around sbE3's Reader story. Every call is shown WITHOUT ``` fences: a command ends with the shell comment
line '# end of command' (harmless if it is copied into the call), file content with '# end of content' (a Python comment).
  sbE5f = few-shot only: the expectation is still one run_command (heredoc of expect.py + check.sh + run), examples fence-free,
          a short search first (r127-r129: the expectation as the solver's first call came out as text 19/21);
  sbE5w = sbE5f, but the expectation's code is written with the harness's write_file tool and a fixed check command (no model code
          in it) installs check.sh and runs it; later runs with bash .git/agent/check.sh."""
import make_prompts as P

END_CMD = "# end of command\n"
END_CONTENT = "# end of content\n"
SEARCH_OUT = P.E3_SEARCH_OUT
NOFILE = "bash: .git/agent/check.sh: No such file or directory\n"


def rc(cmd):
    return "tool: run_command\ncommand:\n" + cmd + END_CMD


def wf(path, content):
    return "tool: write_file\nfilepath: " + path + "\ncontent:\n" + content + END_CONTENT


def solver(X, variant):
    E = X.EV3
    w = lambda k: E[k].split(":")[0]
    W = variant == "sbE5w"
    edit = rc("mkdir -p .git/agent\ncat > .git/agent/old <<'OLD_TEXT'\n" + P.E3_OLD + "OLD_TEXT\ncat > .git/agent/new <<'NEW_TEXT'\n" + P.E3_NEW
              + "NEW_TEXT\n" + X.EDIT_STEP.replace("PATH", "pkg/reader.py"))
    if W:
        ex1_calls = (f"The second call writes the expectation with write_file. It calls Reader the way the issue and tests/test_reader.py do:\n{wf('.git/agent/expect.py', P.E3_EXP)}"
                     f"It printed:\n```\nfilepath: .git/agent/expect.py, size: {len(P.E3_EXP)}\n```\n"
                     f"The third call runs it with the check command, exactly as shown:\n{rc(X.CHECK_CMD)}")
        how = ("The expectation is two calls, as in example 1: write_file with filepath .git/agent/expect.py and the asserts as its content, then the "
               "check command of example 1, exactly as shown, which runs it and says what it shows. Once the check command has run, `"
               + X.RERUN + "` runs the expectation again; after you rewrite expect.py, send that.")
        step3 = ("3. Right after that search, write the expectation (example 1): write_file .git/agent/expect.py with a short script of asserts that calls "
                 "the code through the same construct, with the same inputs and options, as the issue, in the style of the test lines the search "
                 "printed, and states the result the issue wants; then the check command runs it. It must FAIL on the code as it is now and PASS once "
                 "the fix is in. An edit sent before any expectation exists is held back once (example 3).")
        resend = "write_file .git/agent/expect.py again with the corrected asserts, then send `" + X.RERUN + "`"
    else:
        ex1_calls = (f"The second call is the expectation. It calls Reader the way the issue and tests/test_reader.py do:\n{rc(X.expect_cmd(P.E3_EXP))}")
        how = ("The expectation is one run_command in the shape of the second call of example 1: the asserts go between the EXPECT lines, and the "
               "lines after them stay exactly as shown; they run it and say what it shows. To run it again on its own, send `" + X.RERUN + "`.")
        step3 = ("3. Right after that search, write the expectation (example 1): a short script of asserts that calls the code through the same "
                 "construct, with the same inputs and options, as the issue, in the style of the test lines the search printed, and states the result "
                 "the issue wants. It must FAIL on the code as it is now and PASS once the fix is in; the lines after it run it and say which. An "
                 "edit sent before any expectation exists is held back once (example 3).")
        resend = "send the expectation command of example 1 again with the corrected asserts"
    names = ["halved", "eof"] + (["nofile"] if W else []) + ["budget"]
    n = dict.fromkeys(("halved", "eof", "nofile", "budget"), 0) | {k: 9 + i for i, k in enumerate(names)}
    rules = [f"- \"{w('shown')}\": the problem is shown; read the code and edit it so the expectation passes (example 4).",
             f"- \"{w('nothing')}\": the expectation called something that already works. Look at the issue again: call the code through its construct (the class, model, decorator, option or call it shows) with its inputs; {resend} (example 2).",
             f"- \"{w('refused')}\": write the expectation first, then send the same edit again (example 3).",
             f"- \"{w('broken')}\": the script has an error of its own; fix the script: {resend} (example 6).",
             f"- \"{w('still')}\": the edit did not give the wanted behaviour; read the failure lines and edit the source again (example 5).",
             f"- \"{w('done')}\": run the existing test file of this code, then finish (example 4).",
             f"- \"{w('late')}\": stop investigating; edit the place your reading points to now, and let the expectation judge it (example 7).",
             "- \"old text found 0 times\": the old lines differ from the file. Read that region again with read_file and copy the lines from the new output (example 8).",
             f"- \"{X.HALVED}\": nothing to do; the edit was applied as you meant it (example {n['halved']}).",
             f"- \"unexpected EOF while looking for matching\": a line that is not part of the command was sent with it, such as a line of three backticks. Send the same command again with only its own lines (example {n['eof']})."]
    if W:
        rules.append(f"- \"{NOFILE.strip()}\": the check command has not run yet; send the check command of example 1 (example {n['nofile']}).")
    rules.append(f"- \"Tool call budget exhausted\": every other tool is closed now, but `submit_patch` still works. Call `submit_patch`, then reply with one sentence (example {n['budget']}).")
    extra = {
        "halved": (f"Example {n['halved']} - an edit of a line with backslashes, such as a regular expression. Tool results show every backslash of a file doubled, so old text copied from them carries double backslashes; the edit step reads them as single ones when that is what the file has. It printed:\n```\ndouble backslashes in your text read as single ones\nold text found 1 times\nEDITED pkg/ansi.py\n```\n"
                   "The edit was applied as meant; the steps go on as after any edit (example 4)."),
        "eof": (f"Example {n['eof']} - a tool result says \"unexpected EOF while looking for matching\": a line of three backticks had been sent before the command's first line and after its last. The same command goes again with only its own lines, from mkdir -p .git/agent to its last line."),
        "nofile": (f"Example {n['nofile']} - `{X.RERUN}` was sent before the check command of example 1 had ever run. It printed:\n```\n{NOFILE}```\n"
                   "The check command of example 1 goes next, exactly as shown; it installs the check and runs it."),
        "budget": (f"Example {n['budget']} - a tool result says \"Tool call budget exhausted\":\ntool: submit_patch\nThen reply: Made Reader.read pass strict to parse, so Reader(strict=True) raises ValueError for text without '='."),
    }
    return f"""{P.INTRO}

# KEEP GOING UNTIL IT IS DONE
You are graded on the working tree as it stands when the task ends, even if time runs out first. A tree with your edit in it can pass; an unedited tree always scores zero. So keep working until you have edited the source and called `submit_patch`. As soon as your expectation fails for the reason the issue gives, make the edit, even if you are only fairly sure: the expectation runs again after every edit and tells you.

# HOW TO WORK
1. Read the issue and write down the exact names, messages, inputs and options it mentions, the construct through which the problem happens (the class, model, decorator, option or call the issue shows), and what it says must change.
2. Find the code and the tests that call it with one run_command (example 1): `git grep -nF 'exact_name' -- '*.py' | head -20; git grep -n 'exact_name(' -- '*test*' | head -10`, single quotes around search text. Use paths named in the issue directly.
{step3}
4. {P.EDIT_HOW} The edit runs the expectation again and says whether it passes now (example 4).
5. When the expectation passes: run the existing test file: `timeout 150 python -m pytest tests/path/test_x.py -x -q`. Failures from missing fixtures or unrelated imports were there before you; leave them. If your change breaks a test, fix the source and run it once more.
6. Finish: run `git status --short && git diff`, remove any scratch file left in /workspace, then call `submit_patch` and end with one sentence that sums up the fix.

Edit only source files{', and use write_file only for .git/agent/expect.py' if W else ''}. Test files (`test_*.py`, `*_test.py`, anything under `tests/`, `conftest.py`) stay exactly as they are, and every test run names one test file. The expectation lives in .git/agent, so it is never part of the change.

# HOW THE EXPECTATION AND AN EDIT ARE MADE
{how} Every change to a source file is one run_command in the shape of example 4: the old lines go between the OLD_TEXT lines, the new lines between the NEW_TEXT lines, both exactly as read_file printed them, and the steps after them stay exactly as shown; they replace the old text only when it occurs exactly once, show the changed lines, and run the expectation again.

# WHEN A TOOL RESULT SAYS ...
{chr(10).join(rules)}

# EXAMPLES
Each call is shown as plain text: the tool name, then each argument name and its text. A command ends with the line {END_CMD.strip()}{' and file content with the line ' + END_CONTENT.strip() if W else ''}: {'they are comments' if W else 'it is a comment'}, so sending {'them' if W else 'it'} does no harm. Write your own calls with real line breaks and nothing escaped, and end each call right after its last line.

Example 1 - the issue says: Reader ignores strict. Reader(strict=True).read('a') returns a result with an empty value instead of raising ValueError, as parse('a', strict=True) does. The first call finds the code and the tests that call it:
{rc(P.E3_SEARCH)}It printed:
```
{SEARCH_OUT}```
{ex1_calls}It printed:
```
{P.E3_TB}{E['shown']}
```
The problem is shown, so the next step is to read the code and edit it (example 4).

Example 2 - an expectation that is not the issue's case. It had called parse('a', strict=True), the function the issue compares with, and parse already raises. It printed:
```
{E['nothing']}
```
The issue's construct is Reader(strict=True).read, so the expectation goes again with the asserts of example 1, which call Reader as the issue does. In other issues the construct is a model class, a decorator, a subclass, an option, an async version or a config object: the expectation goes through that same one.

Example 3 - an edit sent before any expectation. The edit of example 4 went first, and it printed:
```
old text found 1 times
{E['refused']}
```
The expectation of example 1 goes next, then the edit of example 4 again, unchanged; this time it is applied.

Example 4 - an edit after a failing expectation. read_file on pkg/reader.py, lines 8 to 14, printed:
```
{P.E3_READ}```
The edit goes inside read and keeps its parameters (self, text). The old lines are copied from that output:
{edit}It printed:
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
The try line had lost its colon; the expectation goes again with try: written correctly.

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
