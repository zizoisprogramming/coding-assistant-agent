---
name: work
description: The fixer's shell. run_skill_script with skill_name work, file_path scripts/run.py and positional_args,
  a list holding one string, the whole shell command. Runs in /workspace; the output ends with a clock line.
---

scripts/run.py runs one shell command in /workspace (output cut at 5000 characters) and ends with
"[clock] N s of 420 used | ..." saying whether a source file is edited and what to do next. With no source edit at
270 s it refuses commands until edit_file has changed a source file. 60 s after the repro prints FIXED it runs only
finishing commands (git status, git diff, git checkout --, rm).
