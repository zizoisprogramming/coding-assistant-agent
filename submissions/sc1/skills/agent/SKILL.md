---
name: agent
description: Sets up the reading tool .git/agent/a.py (outside the patch) and shows where the issue's names are. Call run_skill_script with skill_name agent, file_path scripts/install.py and positional_args holding two to four exact names from the issue, once, as the first call.
---

Call run_skill_script with skill_name agent, file_path scripts/install.py and positional_args holding two to four exact names from
the issue, one name per item. It prints READY with the reading commands, then where each name is defined and test lines that use
it. Then read through run_command: python3 .git/agent/a.py COMMAND ...
Never run pip: the sandbox has no internet and every dependency is already installed.
