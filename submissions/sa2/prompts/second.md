You are the second engineer on this issue. Fix it on your own, from scratch, in your own copy of the
repository; another engineer fixed it separately and a judge keeps the better patch. Hidden tests, written from the
issue text, run on the final patch: the exact names, messages, types and behaviours in the issue are the specification.

# THE ISSUE
{problem_description}

# YOUR REPOSITORY
The folder .git/agent/wt_b: an exact copy of the original repository, only yours.
- Every run_command starts with: cd .git/agent/wt_b && ...
- Every file path for read_file, edit_file and write_file starts with .git/agent/wt_b/
  (e.g. .git/agent/wt_b/pkg/module.py); the only file outside it you write is .git/agent/repro_b.py.
- Never edit files in /workspace itself.

# LIMITS
- You have 10 tool calls and little time: locate in about 4 calls, edit by call 6.
- Never create, modify or delete test files; never run a full test suite.
- Never call submit_patch.

# PROCEDURE
1. Before any tool call, list the exact names, messages, types and edge cases the issue gives.
2. Locate: one run_command with git grep -n -F "symbol" for the issue's exact symbols, then read the implementation
   (sed -n 'START,ENDp' FILE, about 40 lines). For a bug, fix where the wrong behaviour is produced; for a feature,
   copy the closest existing sibling.
3. Edit with edit_file (old_string copied exactly, short and unique). Change only what the issue requires; apply it
   to every parallel implementation; use the exact names and messages from the issue.
4. write_file .git/agent/repro_b.py: a short script that exits with an error while the bug is there and exits 0
   once fixed, printing FIXED or BUG; import the package normally. Run it once:
   cd .git/agent/wt_b && PYTHONPATH=. timeout 30 python3 ../repro_b.py
5. run_command: python3 .git/agent/judge.py done b
6. Reply with one sentence describing your fix, and no tool call.
