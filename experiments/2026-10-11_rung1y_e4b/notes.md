# Rung-1y (2026-10-11): 1a round 4 on gemma-4-e4b-it-qat-w4a16-ct, 4 tasks × 2

Config: commit 974d5bd (round 4, only `model:` changed). Result **0/4, 0/4** — every task a wrong fix, including
rich_3882 (31B: always solved, 38–44 s).

| | 31B round 4 | E4B round 4 |
|---|---|---|
| score | 2/4, 2/4 | 0/4, 0/4 |
| steps per task | 30.6 | 12.1 |
| median s per step | 3.9 | 3.2 |
| output tokens/s (incl. tool time) | ~30 | ~74 |
| task duration | 106–305 s | 39–129 s |
| first edit | 38–277 s | 11–73 s |

E4B is ~2.5× faster per token and follows the "edit early" rule (first edit 11–73 s), but it edits the wrong thing and
submits after 7–21 steps without using the remaining time; harness nudges in 5 of 8 tasks. Speed does not help
when the model's understanding is too weak. 12B cannot be served yet (D22). Stay on 31B; E2B not worth trying.
