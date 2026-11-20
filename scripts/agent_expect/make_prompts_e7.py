"""Prompt for sbE7 (user 2026-11-20: 'yes' to: reopen the E tier with one arm = sb1hl's normal exploring + the expectation written with
write_file AFTER reading the code, the hold-back as a backup). Written fresh from sb1hl's way of working and the Reader story; fence-free calls.
Why: r127-r131 - runs without an expectation never edited (12/12); a writer that cannot read code targets the wrong case (4/4); text-form
calls come from the model's own long code inside run_command (write_file: 0.1% over 4,624 calls)."""
import make_prompts as P
import make_prompts_e6 as P6

END_CMD, END_CONTENT = P6.END_CMD, P6.END_CONTENT
rc = P6.rc


def wf(content):
    return "tool: write_file\nfilepath: .git/agent/expect.py\ncontent:\n" + content + END_CONTENT


def solver(X):
    E = X.EV3
    w = lambda k: E[k].split(":")[0]
    edit = rc("mkdir -p .git/agent\ncat > .git/agent/old <<'OLD_TEXT'\n" + P.E3_OLD + "OLD_TEXT\ncat > .git/agent/new <<'NEW_TEXT'\n" + P.E3_NEW
              + "NEW_TEXT\n" + X.EDIT_STEP.replace("PATH", "pkg/reader.py"))
    rules = [f"- \"{w('shown')}\": edit the code you read so the expectation passes (example 4).",
             f"- \"{w('nothing')}\": the expectation calls something that already works; rewrite it to call the code through the issue's construct with its inputs (example 2).",
             f"- \"{w('broken')}\": rewrite it with the script fixed (example 6).",
             f"- \"{w('missing')}\", \"{w('refused')}\" or \"check.sh: No such file\": the expectation or its check is missing; see example 3.",
             f"- \"{w('still')}\": read the failure lines and edit the source again (example 5).",
             f"- \"{w('done')}\": run the existing test file, then finish (example 4).",
             f"- \"{w('late')}\": stop investigating and edit the place your reading points to now (example 7).",
             "- \"old text found 0 times\": read that region again with read_file and copy the lines from the new output (example 8).",
             f"- \"{X.HALVED}\": nothing to do; the edit was applied (example 9).",
             "- \"unexpected EOF while looking for matching\": a line that is not part of the command, such as three backticks, was sent with it; send the command again with only its own lines (example 10).",
             "- \"Tool call budget exhausted\": only `submit_patch` still works; call it, then reply with one sentence (example 11)."]
    return f"""{P.INTRO}

# KEEP GOING UNTIL IT IS DONE
You are graded on the working tree as it stands when the task ends, even if time runs out first. A tree with your edit in it can pass; an unedited tree always scores zero. So keep working until you have edited the source and called `submit_patch`. As soon as the expectation fails for the reason the issue gives, make the edit, even if you are only fairly sure: the expectation runs again after every edit and tells you.

# HOW TO WORK
1. Read the issue and write down the exact names, messages, inputs and options it mentions, and the construct through which the problem happens (the class, model, decorator, option or call the issue shows).
2. Find the code and the tests that call it with one run_command: `git grep -nF 'exact_name' -- '*.py' | head -20; git grep -n 'exact_name(' -- '*test*' | head -10`, single quotes around search text. Use paths named in the issue directly.
3. Read about 40 lines around the place the behaviour is produced with read_file and a start_line and end_line.
4. Write the expectation (example 1): write_file .git/agent/expect.py with a short script of asserts that calls the code through the issue's construct, with its inputs and options, the way the tests call it, and states the result the issue wants. Then send the check command of example 1, exactly as shown: it runs the expectation and says whether it shows the problem. Later, `{X.RERUN}` runs it again; after rewriting expect.py, send that. An edit sent before any expectation exists is held back once.
5. {P.EDIT_HOW} Every edit is one run_command in the shape of example 4: old lines between the OLD_TEXT lines, new lines between the NEW_TEXT lines, both exactly as read_file printed them, the steps after them exactly as shown. It replaces the old text only when it occurs once, shows the change and runs the expectation again.
6. When the expectation passes: run the existing test file: `timeout 150 python -m pytest tests/path/test_x.py -x -q`. Failures from missing fixtures or unrelated imports were there before you; leave them. If your change breaks a test, fix the source and run it once more.
7. Finish: run `git status --short && git diff`, remove any scratch file left in /workspace, then call `submit_patch` and end with one sentence that sums up the fix.

Edit only source files, and use write_file only for .git/agent/expect.py: your own checks go in it, nowhere else. Test files (`test_*.py`, `*_test.py`, anything under `tests/`, `conftest.py`) stay exactly as they are, and every test run names one test file. The expectation lives in .git/agent, so it is never part of the change.

# WHEN A TOOL RESULT SAYS ...
{chr(10).join(rules)}

# EXAMPLES
Each call is shown as plain text: the tool name, then each argument name and its text. A command ends with the line {END_CMD.strip()} and file content with the line {END_CONTENT.strip()}: they are comments, so sending them does no harm. Write your own calls with real line breaks and nothing escaped, and end each call right after its last line.

Example 1 - the issue says: Reader ignores strict. Reader(strict=True).read('a') returns a result with an empty value instead of raising ValueError, as parse('a', strict=True) does. The search:
{rc(P.E3_SEARCH)}It printed:
```
{P.E3_SEARCH_OUT}```
read_file on pkg/reader.py, lines 8 to 14, printed:
```
{P.E3_READ}```
read calls parse(text) without strict. The expectation states the wanted behaviour, calling Reader the way the issue and tests/test_reader.py do:
{wf(P.E3_EXP)}It printed:
```
filepath: .git/agent/expect.py, size: {len(P.E3_EXP)}
```
The check command runs it:
{rc(X.CHECK_CMD)}It printed:
```
{P.E3_TB}{E['shown']}
```
The problem is shown, so the edit of example 4 goes next.

Example 2 - the expectation had called parse('a', strict=True), which already raises. The check printed:
```
{E['nothing']}
```
The issue's construct is Reader(strict=True).read, so write_file .git/agent/expect.py goes again with the asserts of example 1, then `{X.RERUN}`, which printed:
```
{P.E3_TB}{E['shown']}
```
In other issues the construct is a model class, a decorator, a subclass, an option, an async version or a config object: the expectation goes through that same one.

Example 3 - no expectation yet. An edit sent first printed:
```
old text found 1 times
{E['refused']}
```
The expectation of example 1 goes next (write_file, then the check command), then the same edit again. Had the check command run with no expect.py, it would have printed:
```
{E['missing']}
```
and had `{X.RERUN}` been sent before the check command of example 1 ever ran:
```
{X.NOFILE}```
In both cases the expectation of example 1 goes next.

Example 4 - an edit after a failing expectation, inside read, keeping its parameters (self, text); the old lines are copied from the read_file output of example 1:
{edit}It printed:
```
old text found 1 times
EDITED pkg/reader.py
{P.E3_DIFF}{E['done']}
```
The next call runs the existing test file, then the task finishes.

Example 5 - had the edit changed __init__ and left read calling parse(text), it would have printed:
```
old text found 1 times
EDITED pkg/reader.py
{P.E3_TB}{E['still']}
```
so the edit goes again at read, where parse is called (example 4).

Example 6 - a broken expectation. The check printed:
```
  File "/workspace/.git/agent/expect.py", line 3
    try
       ^
SyntaxError: expected ':'
{E['broken']}
```
write_file .git/agent/expect.py goes again with try: written correctly, then `{X.RERUN}`.

Example 7 - `{X.RERUN}` after more reading, nothing edited yet, printed:
```
{P.E3_TB}{E['shown']}
{E['late']}
```
The reading points at read in Reader, so the edit of example 4 goes now, without more checks.

Example 8 - 'old text found 0 times': the old lines had been typed from memory. read_file on pkg/reader.py, lines 12 to 13, printed:
```
    def read(self, text):
        return parse(text.strip())
```
The edit of example 4 goes again with these old lines copied, text.strip() in both the old and the new text.

Example 9 - an edit of a line with backslashes, such as a regular expression. Tool results show every backslash doubled, so copied old text carries double backslashes; the edit step reads them as single ones when that is what the file has. It printed:
```
double backslashes in your text read as single ones
old text found 1 times
EDITED pkg/ansi.py
```
The edit was applied as meant.

Example 10 - "unexpected EOF while looking for matching": a line of three backticks had been sent before the command's first line and after its last. The same command goes again with only its own lines.

Example 11 - "Tool call budget exhausted":
tool: submit_patch
Then reply: Made Reader.read pass strict to parse, so Reader(strict=True) raises ValueError for text without '='.
"""
