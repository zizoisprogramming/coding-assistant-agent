---
name: scout
description: The locator's reading tool. find, show and history read the repository (16 reading calls in total); plan writes /tmp/plan.md for the editor; check shows the current diff and runs a targeted test.
---

Call it with run_skill_script, skill_name scout, file_path scripts/scout.py and named args:

- find:  args = {"mode": "find", "query": "convert_underscores"}
  git grep hits for the name or message, each with the 20 lines that follow.
- show:  args = {"mode": "show", "file": "pkg/module.py", "start": 40, "end": 170}
  numbered lines, up to 150 at once.
- history: args = {"mode": "history", "query": "NAME"} (commits that added or removed it, plus the 8 latest)
  or {"mode": "history", "commit": "abc1234"} (that commit's change).
- plan:  args = {"mode": "plan", "text": "FILE: ...\nWHAT IT DOES: ...\nCHANGE: ...\nCONTRACT: ..."}
  saves the plan for the editor to /tmp/plan.md.
- check: args = {"mode": "check", "test": "tests/test_x.py", "k": "name"}
  the current git diff, plus the last lines of that test run (test and k are optional).

find, show and history share a budget of 16 reading calls; every result ends with the count. After 16 they refuse:
write the plan and call the editor. plan and check never count.
