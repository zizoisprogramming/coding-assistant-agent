# Rung-1h (2026-10-09): 1b round 6b (resume-safe notes), 2 repeats

Config: commit eaa3c86 (+ notebook 2 repeats, faaa8ae). Result **1/4, 1/4** (round 6: 1/1/1; round 4: 3/2/1).
Per task: rich_3882 2/2 (66–70 s), fastapi_15588 0/2, fastapi_15589 0/2, rich_3470 0/2.

## Resume fix: works
| | round 6 | round 6b |
|---|---|---|
| notes.md overwritten | 21 | **1** |
| after a compaction | 6 restarts / re-searches of 9 | 2 resume-check, 1 continue, 1 restart |
| STEP lines written | — | 5 |
| orchestrator notes reads | 25 / 12 tasks | 22 / 8 tasks |

## Still losing: identical repetition, mostly before any compaction
- fastapi_15589 r1: repro.py written 18× (10 identical in a row), never called a helper, timeout.
- rich_3470 r1: repro.py 27× (12 identical in a row); r2 13×.
- fastapi_15589 r2: the **reader** ran the identical git grep 57× in a row (68 inner calls), then the orchestrator
  submitted an empty patch.
- Helpers otherwise fast: executor 17 s, verifier 14 s, reader 44 s per call.

The loops are identical commands back to back, not rewrites with new content: the model is stuck, not exploring.
Temperature 0.2 (since rung-1d) is the main suspect (D10; Holtzman et al. 2020). Next round: temperature 1.0 only.

## Leaderboard (same day)
Kaggle rescored the two "Kaggle Error" submissions: 1a round 2 at 5 min → 0.08, at 4 min → 0.10.
