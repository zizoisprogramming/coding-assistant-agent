---
name: look
description: The reporter's shell. run_skill_script with skill_name look, file_path scripts/run.py and positional_args,
  a list holding one string, the whole shell command. Runs in /workspace; the output ends with a clock line.
---

scripts/run.py runs one shell command in /workspace (output cut at 5000 characters) and ends with
"[clock] N s of 420 used | ...". It refuses commands that change files outside /tmp and .git/agent, and refuses every
command from 120 s on.
