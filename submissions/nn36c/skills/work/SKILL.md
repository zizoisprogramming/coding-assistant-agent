---
name: work
description: Your shell. run_skill_script with skill_name work, file_path scripts/run.py and positional_args, a list
  holding a single string, the whole shell command. Runs in /workspace; the output ends with a state line.
---

scripts/run.py runs a shell command in /workspace and ends with a [state] line: LOOK, EDIT NOW, CHECK or FINISH. It refuses
commands when the state requires an edit or the finish.
