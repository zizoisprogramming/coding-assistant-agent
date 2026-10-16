---
name: reader
description: Installs the locator's reading tool at .git/agent/read.py (outside the patch). find, show and history share a limit of 16 reads; at the limit it refuses and says to call the editor.
---

Install once per task: call run_skill_script with skill_name reader and file_path scripts/install.py (no other
arguments). It prints INSTALLED and how to use the reader through run_command.
