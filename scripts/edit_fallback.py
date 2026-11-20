"""Backslash fallback for the heredoc edit step (user 2026-11-20: 'okay let the edit step undo the doubling').
Tool results reach the model JSON-escaped, so a backslash in the file shows as two and the model copies two (r128 RESULT; bank: 40 of 58
'found 0' results, scripts/mine_bank/backslash_f0.py). halve(step) inserts, before the step's 'old text found' line: if the old text is
found 0 times as sent, has a double backslash, and is found exactly once with each double backslash read as one, use that old text and the
new text halved the same way, and say so. The step's own text stays free of backslashes (chr(92)), so the prompt checks still hold."""

FIND = "print('old text found', s.count(old), 'times')\n"
ADD = ("b = chr(92)\n"
       "if s.count(old) == 0 and b + b in old and s.count(old.replace(b + b, b)) == 1:\n"
       "    old, new = old.replace(b + b, b), new.replace(b + b, b)\n"
       "    print('double backslashes in your text read as single ones')\n")


def halve(step):
    assert step.count(FIND) == 1, "the step has one 'old text found' line"
    out = step.replace(FIND, ADD + FIND)
    assert "\\" not in out and '"' not in out and "`" not in out and "{" not in out and "}" not in out
    return out
