Your only job is to write the expectation for the issue below, for the engineer who fixes it after you: a short Python script, .git/agent/expect.py, whose asserts state the behaviour the issue wants. It must FAIL on the code as it is now, because the problem is still there, and PASS once the fix is in. Your one tool is write_file; you do not read code and you do not fix anything.

# HOW TO WRITE IT
- Import the code from where the lines under WHERE THE ISSUE'S NAMES ARE say it is defined, and call it the way the test lines there call it.
- Call it through the construct the issue shows (the class, model, decorator, option or call in the issue), with the issue's own inputs and options, and assert the result the issue says it must give: the exact value, message or exception type, copied character for character from the issue.
- Keep it short: imports, the calls, the asserts. No test framework, no test functions, no prints.

Make one write_file call with filepath .git/agent/expect.py, then reply with one line that starts with WROTE .git/agent/expect.py: and says what it asserts.
If the lines under WHERE THE ISSUE'S NAMES ARE begin with EXPECTATION ALREADY WRITTEN, make no call and reply with the single line DONE.

# EXAMPLES
Each call is shown as plain text: the tool name, then each argument name and its text. File content ends with the line # end of content: it is a comment, so sending it does no harm.

Example 1 - the issue says: Reader ignores strict. Reader(strict=True).read('a') returns a result with an empty value instead of raising ValueError, as parse('a', strict=True) does. The lines under WHERE THE ISSUE'S NAMES ARE held:
```
pkg/reader.py:8:class Reader:
pkg/reader.py:9:    def __init__(self, strict=False):
tests/test_reader.py:14:    assert Reader().read('a=1')['a'] == '1'
pkg/parser.py:1:def parse(text, strict=False):
tests/test_parser.py:9:    assert parse('a=1', strict=True)['a'] == '1'
```
The call:
tool: write_file
filepath: .git/agent/expect.py
content:
from pkg.reader import Reader

try:
    Reader(strict=True).read('a')
except ValueError:
    pass
else:
    raise AssertionError('Reader(strict=True) accepted text without =')
assert Reader(strict=True).read('a=1')['a'] == '1'
# end of content
It printed:
```
filepath: .git/agent/expect.py, size: 227
```
The reply, with no tool call:
WROTE .git/agent/expect.py: Reader(strict=True).read('a') must raise ValueError; Reader(strict=True).read('a=1')['a'] must be '1'.

Example 2 - the lines under WHERE THE ISSUE'S NAMES ARE held:
```
EXPECTATION ALREADY WRITTEN: the task was restarted; reply with this line only.
```
No call; the reply:
DONE

# WHERE THE ISSUE'S NAMES ARE
{evidence?}

# THE ISSUE (verbatim)
{problem_description}