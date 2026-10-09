# Rung-1p (2026-10-09): 1a round 3d (thinking_budget 512), fastapi_15589 + rich_3470, 3 repeats

Config: commit ad8b2d1 (round 3c + budget 1,024 -> 512). Result: fastapi_15589 1/3 (3c: 2/3), rich_3470 0/3 (3c: 0/3).

| | max tokens per step | steps > 20 s per task | steps per task | first edit |
|---|---|---|---|---|
| 3c (1,024) | 1,060-1,450 | 4-8 | 14-41 | 220-299 s, 1 never |
| 3d (512) | 565-980 | 0-3 | 17-49 | 194-283 s, 2 never |

The budget works mechanically (long steps shorter, fewer slow steps), but the saved time went into more
investigation steps (rich_3470: up to 49 steps), not into an earlier edit. The bottleneck is the decision to
commit to an edit: the model edits only after it believes it understands the bug, typically via a repro that
fails first. Speed alone does not move that point.
Keep 512 (no visible harm, steadier step times). Next: change the workflow order (edit right after reading, repro
and tests afterwards as the check), since the model does follow the order of workflow steps.
