---
name: work
description: Installs the fixer's shell, .git/agent/run.py, outside the patch. Call run_skill_script with skill_name work and file_path scripts/install.py, with no other arguments, as the first call.
---

Call run_skill_script with skill_name work and file_path scripts/install.py. It prints READY. Then run every command with
run_command: python .git/agent/run.py 'the whole shell command'. Every output ends with a clock line, "[clock] N s of 480 used | ...".
