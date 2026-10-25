---
name: agent
description: Installs the reading tool .git/agent/a.py (outside the patch). Run scripts/install.py once, as the first call.
---

Call run_skill_script with skill_name agent and file_path scripts/install.py, with no other arguments. It prints
INSTALLED and the commands. Then use the tool through run_command: python3 .git/agent/a.py COMMAND ...
