# Rung-2d (2026-10-13): safe-edit skill as the only editing path

Rung-2c did not test the skill (installed in 1/16 tasks; edit_file used). Now edit_file and write_file are removed
from the skill arms (harness 0.2.11 returns undeclared-tool calls as errors, no crash; the task message never
mentions them). Extra prompt line: "If it says No such file, the editor is not installed yet: run step 0, then the
same edit again" (event-triggered recovery). Arms: r4_budget, r4b_skill2, r4b_think_t02, r4b_think_t02_skill2;
4 tasks × 2, concurrency 2.
Measure: install rate and when, editor APPLIED/NOT_APPLIED and recovery, edit_file attempts (should error),
other edit routes (sed -i / python writes), score.
