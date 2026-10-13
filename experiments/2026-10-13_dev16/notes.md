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
