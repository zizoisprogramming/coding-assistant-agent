---
name: work
description: Your shell. run_skill_script with skill_name work, file_path scripts/run.py and positional_args, a list
  holding one string, the whole shell command. Runs in /workspace; the output ends with a clock line.
---

scripts/run.py runs one shell command in /workspace (output cut at 5000 characters) and ends with
"[clock] N s of 480 used | ...". 60 s after the last source edit it runs only git status, git diff, git checkout -- and
rm; the first command after an edit always runs.
