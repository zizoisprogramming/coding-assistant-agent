---
name: sh
description: The shell. Runs one shell command in /workspace. Call run_skill_script with skill_name sh, file_path scripts/run.py and positional_args holding one string, the whole command.
---

Call run_skill_script with skill_name sh, file_path scripts/run.py and positional_args a list holding one string: the whole
shell command. Do not use the args parameter. The output ends with a state line (LOOK, EDIT NOW, CHECK). With no source
edit for a while, commands are refused until edit_file changes a source file.
