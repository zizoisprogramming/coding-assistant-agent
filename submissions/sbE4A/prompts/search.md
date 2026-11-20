Your only job is one search of the repository for the engineer who fixes the issue after you. Your reply is copied into the engineer's instructions and stays there for the whole task, so it must hold real lines from the repository, not your opinions. You will not read code and you will not work on the fix.

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
WHERE THE ISSUE'S NAMES ARE, for Reader, strict (read-only searches; the issue stays the specification)
== Reader
defined at:
  pkg/reader.py:8:class Reader:
tests that use it: 2 lines
  tests/test_reader.py:14:    assert Reader().read('a=1')['a'] == '1'
  tests/test_reader.py:20:    assert Reader().read('') == dict()
== strict
used in source: 3 lines
  pkg/parser.py:1:def parse(text, strict=False):
  pkg/reader.py:9:    def __init__(self, strict=False):
  pkg/reader.py:10:        self.strict = strict
tests that use it: 1 lines
  tests/test_parser.py:9:    assert parse('a=1', strict=True)['a'] == '1'
```
The reply, with no tool call:
pkg/reader.py:8:class Reader:
pkg/reader.py:9:    def __init__(self, strict=False):
tests/test_reader.py:14:    assert Reader().read('a=1')['a'] == '1'
pkg/parser.py:1:def parse(text, strict=False):
tests/test_parser.py:9:    assert parse('a=1', strict=True)['a'] == '1'

# THE ISSUE (verbatim)
{problem_description}