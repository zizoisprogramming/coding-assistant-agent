---
name: safe-edit
description: Installs /tmp/safe_edit.py, a checked SEARCH/REPLACE editor that refuses edits which break Python syntax.
---

Install once per task: call run_skill_script with skill_name safe-edit and file_path scripts/install.py
(no other arguments). It prints INSTALLED.

Then make each source edit with one run_command call:

python3 /tmp/safe_edit.py path/to/file.py << 'EDIT'
<<<<<<< SEARCH
exact current lines, copied with their indentation
=======
replacement lines
>>>>>>> REPLACE
EDIT

- SEARCH must match the file exactly once. Several blocks for the same file may follow each other.
- The editor checks that the edited file is still valid Python. If not, or if SEARCH is not found, it prints
  NOT_APPLIED with the reason and the relevant numbered lines, and leaves the file unchanged: fix the block and retry.
- It refuses test files and test configuration. An empty SEARCH creates a new file.
