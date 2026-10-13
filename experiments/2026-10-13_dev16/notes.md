# Dev set v2 (2026-10-13): 16 tasks that grade correctly on Kaggle

Gold check on Kaggle (CPU session, scorer's verify_task, subprocess sandbox; data/results/2026-10-13_gold_check):
25 checked, 20 usable (gold PASS + empty FAIL). Not gradable on Kaggle: fastapi_14583, fastapi_14978,
fastapi_14266, fastapi_15023 (test collection errors), rich_3296 (4 syntax tests fail, likely pygments version).
Chosen 16 (wave A of research/dev_tasks_feasibility.md; failures replaced from wave B in the same stratum;
fastapi_15588 dropped: never solved, hidden error message):
- fastapi S: 15589, 13920, 14258, 11194, 14487 | M: 15280, 14419 | L: 15800, 14306
- rich S: 3882, 3470, 4079 | M: 3521, 3934, 3468 | L: 3180
Spare usable: fastapi_15588, fastapi_14372, rich_3506, rich_3782.

## Rung-3a: r4_budget vs r4b_think_t02 on the 16 tasks, 1 run each, concurrency 2

### Results (2026-10-13)
r4_budget **3/16** (rich_4079, rich_3882, rich_3521), mean 314 s/task; r4b_think_t02 **3/16** (fastapi_15589,
rich_3882, fastapi_11194), mean 400 s/task. Union 5/16; only rich_3882 in both.
| Outcome | r4_budget | r4b_think_t02 |
|---|---|---|
| solved | 3 | 3 |
| wrong fix | 6 | 4 |
| no edit: edit attempted after the 28-call cap (BudgetExceeded) | 2 | 4 |
| no edit: time limit | 1 | 3 |
| no edit: never got an edit in (incl. failing edit_file calls) | 4 | 2 |
- Half the tasks end with an empty patch. In every one the "10 calls left" warning came at call 18 and the agent
  kept reading/scripting (8–19 reads, 10–18 greps); edits then came at calls 24–29, several rejected at 29.
- Runtime: 314 s/task → ~10.5 h for 120 sequential tasks; think_t02 400 s → ~13.3 h (over the 12-h limit; not
  submittable as is). Measured with concurrency 2 (~5–10 % slower), on harder-than-old tasks.
- Next idea: an event-anchored rule ("when a tool result says only N calls remain, the very next call is your best
  edit"), since event-triggered rules are the ones the model follows.
