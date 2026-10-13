# Rung-2d (2026-10-13): safe-edit skill as the only editing path

Rung-2c did not test the skill (installed in 1/16 tasks; edit_file used). Now edit_file and write_file are removed
from the skill arms (harness 0.2.11 returns undeclared-tool calls as errors, no crash; the task message never
mentions them). Extra prompt line: "If it says No such file, the editor is not installed yet: run step 0, then the
same edit again" (event-triggered recovery). Arms: r4_budget, r4b_skill2, r4b_think_t02, r4b_think_t02_skill2;
4 tasks × 2, concurrency 2.
Measure: install rate and when, editor APPLIED/NOT_APPLIED and recovery, edit_file attempts (should error),
other edit routes (sed -i / python writes), score.

## Results (2026-10-13)
| Arm | r1 | r2 |
|---|---|---|
| r4_budget | 1/4 | 1/4 |
| r4b_skill2 | 1/4 | 1/4 |
| r4b_think_t02 | 1/4 | 2/4 (15589) |
| r4b_think_t02_skill2 | 2/4 (3470) | 1/4 |
- The editor is used now: installed in 12/16 skill tasks, mostly right after a "No such file" (the event recovery
  works; the "step 0" instruction alone still does not). No edit_file attempts.
- It caught **0 syntax-breaking edits** this round. Its refusals were "SEARCH not found" / "found 2 times"
  (most on the unsolvable fastapi_15588: up to 10 refusals in one task) and one test-file edit (tests/test_sse.py).
- Cost: install + the failed first try = 2 of 28 calls. r4b_skill2 r1 rich_3470 hit "No such file" at call 28 and
  the install at call 29 was over budget → no edit at all.
- Cumulative on the 4 tasks (2a–2d): r4_budget 12/32, r4b_think_t02 10/24, skill arms 5/16 (2d). All within
  noise; the 4-task set no longer separates configs.
