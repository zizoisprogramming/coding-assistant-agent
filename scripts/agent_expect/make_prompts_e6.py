"""Prompts for sbE6 (user 2026-11-20: 'on 2 tasks only please and yes build'; design in docs/PLAN.md RUN BUILT r131).
SequentialAgent [search -> writer -> solver], all calls fence-free ('# end of command' / '# end of content' comment lines).
  search: one run_skill_script call (thinking off) -> where the issue's names are defined + test lines that call them; on a restart the
          script says EXPECTATION ALREADY WRITTEN and the stage passes that line on.
  writer: write_file only; writes .git/agent/expect.py from the issue + the search lines; replies with a one-line note; on a restart
          (EXPECTATION ALREADY WRITTEN) makes no call and replies DONE.
  solver: sb1hl's way of working; its FIRST call is the fixed check command (installs check.sh, runs the teammate's expectation);
          rewrites the expectation with the heredoc expectation command when it is not the issue's case / broken / missing; hold-back,
          backslash fallback, late line as sbE3b."""
import make_prompts as P
import make_prompts_e4 as P4

END_CMD = "# end of command\n"
END_CONTENT = "# end of content\n"
ALREADY = "EXPECTATION ALREADY WRITTEN: the task was restarted; reply with this line only."
NOTE = "WROTE .git/agent/expect.py: Reader(strict=True).read('a') must raise ValueError; Reader(strict=True).read('a=1')['a'] must be '1'."


def rc(cmd):
    return "tool: run_command\ncommand:\n" + cmd + END_CMD


def search():
    return f"""Your only job is one search of the repository for the teammates who work on the issue after you. Your reply is copied into their instructions, so it must hold real lines from the repository, not your opinions. You will not read code and you will not work on the fix.

Choose two to four exact names from the issue below that the problem goes through: functions, methods, classes, options or parameters, written exactly as in the issue. Include the construct the issue shows (the class, model or decorator it uses), and prefer specific names, such as convert_underscores, over common words, such as Header.

Call run_skill_script with skill_name evidence, file_path scripts/evidence.py and positional_args holding those names, one name per item. That is your only call.

Then reply with the lines of its result that show where the names are defined and the test lines that call them, each copied exactly as printed with its file:line, at most 12 lines and nothing else. If the result begins with EXPECTATION ALREADY WRITTEN, reply with that line only. If nothing in the result bears on the issue, reply with the single line NOTHING RELEVANT.

# EXAMPLES
Example 1 - the issue says: Reader ignores strict. Reader(strict=True).read('a') returns a result with an empty value instead of raising ValueError, as parse('a', strict=True) does. The call:
tool: run_skill_script
skill_name: evidence
file_path: scripts/evidence.py
positional_args: Reader, strict
It printed:
```
{P4.SEARCH_OUT}```
The reply, with no tool call:
{P4.SEARCH_REPLY}
Example 2 - the same call printed:
```
{ALREADY}
```
The reply, with no tool call:
{ALREADY}

# THE ISSUE (verbatim)
{{problem_description}}"""


def writer():
    return f"""Your only job is to write the expectation for the issue below, for the engineer who fixes it after you: a short Python script, .git/agent/expect.py, whose asserts state the behaviour the issue wants. It must FAIL on the code as it is now, because the problem is still there, and PASS once the fix is in. Your one tool is write_file; you do not read code and you do not fix anything.

# HOW TO WRITE IT
- Import the code from where the lines under WHERE THE ISSUE'S NAMES ARE say it is defined, and call it the way the test lines there call it.
- Call it through the construct the issue shows (the class, model, decorator, option or call in the issue), with the issue's own inputs and options, and assert the result the issue says it must give: the exact value, message or exception type, copied character for character from the issue.
- Keep it short: imports, the calls, the asserts. No test framework, no test functions, no prints.

Make one write_file call with filepath .git/agent/expect.py, then reply with one line that starts with WROTE .git/agent/expect.py: and says what it asserts.
If the lines under WHERE THE ISSUE'S NAMES ARE begin with EXPECTATION ALREADY WRITTEN, make no call and reply with the single line DONE.

# EXAMPLES
Each call is shown as plain text: the tool name, then each argument name and its text. File content ends with the line {END_CONTENT.strip()}: it is a comment, so sending it does no harm.

Example 1 - the issue says: Reader ignores strict. Reader(strict=True).read('a') returns a result with an empty value instead of raising ValueError, as parse('a', strict=True) does. The lines under WHERE THE ISSUE'S NAMES ARE held:
```
{P4.SEARCH_REPLY}```
The call:
tool: write_file
filepath: .git/agent/expect.py
content:
{P.E3_EXP}{END_CONTENT}It printed:
```
filepath: .git/agent/expect.py, size: {len(P.E3_EXP)}
```
The reply, with no tool call:
{NOTE}

Example 2 - the lines under WHERE THE ISSUE'S NAMES ARE held:
```
{ALREADY}
```
No call; the reply:
DONE

# WHERE THE ISSUE'S NAMES ARE
{{evidence?}}

# THE ISSUE (verbatim)
{{problem_description}}"""


def solver(X):
    """r131 short version (user 2026-11-20: 'can we reduce the prompt a little'): the rewrite command no longer re-installs check.sh
    (the first call did), the HOW THE CHECK section is folded into HOW TO WORK, the two no-expectation examples are one, rules shorter."""
    E = X.EV3
    w = lambda k: E[k].split(":")[0]
    edit = rc("mkdir -p .git/agent\ncat > .git/agent/old <<'OLD_TEXT'\n" + P.E3_OLD + "OLD_TEXT\ncat > .git/agent/new <<'NEW_TEXT'\n" + P.E3_NEW
              + "NEW_TEXT\n" + X.EDIT_STEP.replace("PATH", "pkg/reader.py"))
    rules = [f"- \"{w('shown')}\": read the code and edit it (example 4).",
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

# THE EXPECTATION
Before you started, a teammate wrote .git/agent/expect.py, a short script of asserts that states the behaviour the issue wants and should fail on the code as it is now, and left this note:
{{expectation?}}
A search found where the issue's names are defined and test lines that call them:
{{evidence?}}

# KEEP GOING UNTIL IT IS DONE
You are graded on the working tree as it stands when the task ends, even if time runs out first. A tree with your edit in it can pass; an unedited tree always scores zero. So keep working until you have edited the source and called `submit_patch`. As soon as the expectation fails for the reason the issue gives, make the edit, even if you are only fairly sure: the expectation runs again after every edit and tells you.

# HOW TO WORK
1. Read the issue, the note and the lines above: the exact names, messages, inputs and options, and the construct through which the problem happens.
2. Your first call is the check command of example 1, exactly as shown: it runs the teammate's expectation and says what it shows. Later, `{X.RERUN}` runs it again.
3. When it shows the problem, read about 40 lines around the place the behaviour is produced with read_file and a start_line and end_line, then edit (example 4). To rewrite the expectation, send the rewrite command of example 2: new asserts between the EXPECT lines, the rest exactly as shown. Search with `git grep -nF 'exact_name' -- '*.py' | head -20` only when the lines above lack the code you need.
4. {P.EDIT_HOW} Every edit is one run_command in the shape of example 4: old lines between the OLD_TEXT lines, new lines between the NEW_TEXT lines, both exactly as read_file printed them, the steps after them exactly as shown. It replaces the old text only when it occurs once, shows the change and runs the expectation again.
5. When the expectation passes: run the existing test file: `timeout 150 python -m pytest tests/path/test_x.py -x -q`. Failures from missing fixtures or unrelated imports were there before you; leave them. If your change breaks a test, fix the source and run it once more.
6. Finish: run `git status --short && git diff`, remove any scratch file left in /workspace, then call `submit_patch` and end with one sentence that sums up the fix.

Edit only source files. Test files (`test_*.py`, `*_test.py`, anything under `tests/`, `conftest.py`) stay exactly as they are, and every test run names one test file. The expectation lives in .git/agent, so it is never part of the change.

# WHEN A TOOL RESULT SAYS ...
{chr(10).join(rules)}

# EXAMPLES
Each call is shown as plain text: the tool name, then each argument name and its text. A command ends with the line {END_CMD.strip()}: it is a comment, so sending it does no harm. Write your own calls with real line breaks and nothing escaped, and end each call right after its last line.

Example 1 - the issue says: Reader ignores strict. Reader(strict=True).read('a') returns a result with an empty value instead of raising ValueError, as parse('a', strict=True) does. The note says: {NOTE} The first call is the check command:
{rc(X.CHECK_CMD)}It printed:
```
{P.E3_TB}{E['shown']}
```
The problem is shown, so the next step is to read the code and edit it (example 4).

Example 2 - the teammate's expectation had called parse('a', strict=True), which already raises. The check printed:
```
{E['nothing']}
```
The issue's construct is Reader(strict=True).read, so the rewrite command goes next:
{rc(X.rewrite_cmd(P.E3_EXP))}It printed:
```
{P.E3_TB}{E['shown']}
```
In other issues the construct is a model class, a decorator, a subclass, an option, an async version or a config object: the expectation goes through that same one.

Example 3 - no expectation yet. The check printed:
```
{E['missing']}
```
The rewrite command of example 2 goes next, with asserts written from the issue and the lines above. Had an edit gone first, it would have printed:
```
old text found 1 times
{E['refused']}
```
and the same edit goes again after the rewrite command. Had `{X.RERUN}` been sent before the check command of example 1 ever ran, it would have printed:
```
{X.NOFILE}```
and the check command of example 1 goes next.

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
The rewrite command of example 2 goes next with try: written correctly.

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
