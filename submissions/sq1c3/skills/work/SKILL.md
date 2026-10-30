---
name: work
description: The fixer's shell, also used for reading files. run_skill_script with skill_name work, file_path
  scripts/run.py and positional_args, a list holding one string, the whole shell command. Output ends with a clock line.
---

scripts/run.py runs one shell command in /workspace (output cut at 5000 characters) and ends with
"[clock] N s of 480 used | source edited: FILES" or "no source edit yet". With no source edit at 270 s it refuses
every command, reading included, until edit_file has changed a source file.
