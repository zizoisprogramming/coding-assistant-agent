You write a check script for the agent who fixes the issue below after you. You have one tool, write_file, and you
will not see any code, so build the check from the issue alone.

Call write_file once with filepath .git/agent/check.py (that exact path: files under .git never reach the graded patch).
The script must:
- begin with: import os, sys; sys.path.insert(0, os.getcwd())
- run the issue's own example or examples through the public names the issue uses, as two to five separate checks
- print, for each check, either "PASS: what was checked" or "FAIL: what was checked: expected X, got Y"
- catch every exception inside each check and print it as a FAIL line with the exception type and message, so one
  failing check never hides the others
- need no network, no input and no files outside the repository, and finish within a few seconds

When the issue describes behaviour that does not exist yet, the checks describe the behaviour the issue asks for, so they
print FAIL before the fix.

After the write_file call, reply with exactly this line and stop:
CHECK READY: python .git/agent/check.py prints FAIL lines now and every line prints PASS after a correct fix. Run it after each edit.

# THE ISSUE (verbatim)
{problem_description}