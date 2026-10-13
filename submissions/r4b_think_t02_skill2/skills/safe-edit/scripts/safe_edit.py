"""Checked SEARCH/REPLACE editor: applies an edit only if the result is still valid Python.

Usage (from /workspace, through run_command):
    python3 /tmp/safe_edit.py path/to/file.py << 'EDIT'
    <<<<<<< SEARCH
    exact current lines
    =======
    new lines
    >>>>>>> REPLACE
    EDIT

Several blocks may follow each other; they are applied in order and all-or-nothing. An empty SEARCH creates a
new file. On any problem the file is left unchanged and the reason is printed (NOT_APPLIED, exit code 1).
"""
import difflib
import os
import re
import sys

BLOCK = re.compile(r"^<{7} SEARCH\n(.*?)^={7}\n(.*?)^>{7} REPLACE\n?", re.S | re.M)
PROTECTED = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)conftest\.py$"
                       r"|(^|/)(pytest\.ini|pyproject\.toml|setup\.cfg|tox\.ini)$")


def fail(msg):
    print("NOT_APPLIED: " + msg, file=sys.stderr)
    sys.exit(1)


def numbered(lines, start, end):
    start = max(start, 0)
    return "\n".join(f"{i + 1:5}| {lines[i]}" for i in range(start, min(end, len(lines))))


def locate(text, search):
    """Return (start, end) of the single match of search in text, trying exact then trailing-space-insensitive."""
    n = text.count(search)
    if n == 1:
        i = text.index(search)
        return i, i + len(search)
    if n > 1:
        lines = [text[:m.start()].count("\n") + 1 for m in re.finditer(re.escape(search), text)]
        fail(f"SEARCH text found {n} times (lines {', '.join(map(str, lines[:8]))}); add a nearby line to make it unique.")
    # Retry ignoring trailing whitespace on each line.
    pattern = "\n".join(re.escape(l.rstrip()) + r"[ \t]*" for l in search.split("\n"))
    found = list(re.finditer(pattern, text))
    if len(found) == 1:
        return found[0].start(), found[0].end()
    lines = text.split("\n")
    first = next((l for l in search.split("\n") if l.strip()), "")
    best = difflib.get_close_matches(first, lines, n=1, cutoff=0.5)
    hint = ""
    if best:
        k = lines.index(best[0])
        hint = "\nClosest place in the file (copy SEARCH exactly from here):\n" + numbered(lines, k - 2, k + 8)
    fail("SEARCH text not found in the file." + hint)


def main():
    if len(sys.argv) != 2:
        fail("usage: python3 /tmp/safe_edit.py path/to/file.py << 'EDIT' ... EDIT")
    path = sys.argv[1]
    rel = os.path.relpath(os.path.abspath(path)).replace(os.sep, "/")
    if PROTECTED.search(rel):
        fail(f"{rel} is a test or test-configuration file; the grader resets these. Edit the source code instead.")
    blocks = BLOCK.findall(sys.stdin.read())
    if not blocks:
        fail("no SEARCH/REPLACE block found. Use lines '<<<<<<< SEARCH', '=======', '>>>>>>> REPLACE'.")
    exists = os.path.exists(path)
    old = open(path, encoding="utf-8").read() if exists else ""
    new = old
    for search, replace in blocks:
        if not search.strip():
            if exists and old.strip():
                fail("empty SEARCH is only allowed for a new or empty file.")
            new = replace
            continue
        if not exists:
            fail(f"{path} does not exist.")
        start, end = locate(new, search)
        new = new[:start] + replace + new[end:]
    if new == old:
        fail("the edit changes nothing.")
    if path.endswith(".py"):
        try:
            compile(new, path, "exec")
        except SyntaxError as e:
            lines = new.split("\n")
            ln = e.lineno or 1
            fail(f"the edited file would not be valid Python: {e.msg} (line {ln}). File unchanged.\n"
                 f"The edited text around line {ln}:\n" + numbered(lines, ln - 4, ln + 3))
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new)
    diff = list(difflib.unified_diff(old.split("\n"), new.split("\n"), path, path, n=1, lineterm=""))
    print(f"APPLIED {len(blocks)} block(s) to {path}; it is valid Python." if path.endswith(".py")
          else f"APPLIED {len(blocks)} block(s) to {path}.")
    print("\n".join(diff[2:42]) + ("\n..." if len(diff) > 42 else ""))


if __name__ == "__main__":
    main()
