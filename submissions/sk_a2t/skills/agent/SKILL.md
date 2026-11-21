---
name: agent
description: Sets up the reading tool .git/agent/a.py (outside the patch). Call run_skill_script with file_path scripts/install.py once, as the first call. Nothing to pip install.
---

Call run_skill_script with skill_name agent and file_path scripts/install.py, with no other arguments. It prints
READY and the commands. Then use the tool through run_command: python3 .git/agent/a.py COMMAND ...
Never run pip: the sandbox has no internet and every dependency is already installed.
