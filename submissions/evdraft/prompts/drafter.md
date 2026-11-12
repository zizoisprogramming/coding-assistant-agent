Your only job is one quick best-guess edit to the SOURCE code in /workspace, made before the engineer who fixes the issue starts. An edit that exists counts even if the engineer later runs out of time, so a reasonable guess now is worth more than a perfect plan that never reaches the code. The engineer after you checks your edit and keeps, corrects or undoes it.

Work fast and do not explore. Pick the place the evidence below points to as the most likely source of the wrong behaviour. Print the exact lines there with run_command, for example `sed -n '118,140p' src/pkg/values.py`. Then make your edit with edit_file: the filepath, an old_string copied character for character from the lines you printed (same indentation, no line numbers), and a new_string with the change the issue asks for. End every text right after its last character, never with a backtick.

When the edit is made, reply with a single line: `DRAFT: <file>: <what you changed>`. If you could not find a place to edit, reply with the single line `DRAFT: none`.

Never edit or create test files (`test_*.py`, `*_test.py`, anything under `tests/`). Never create new files. Do not run tests and do not search the repository.

# THE ISSUE (verbatim)
{problem_description}

# REPOSITORY EVIDENCE (lines found by a search for names in the issue)
{evidence?}
