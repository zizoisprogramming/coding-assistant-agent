# Rung-1o (2026-10-09): 1a round 3c (time checkpoint), fastapi_15589 + rich_3470 only, 3 repeats

Config: commit f246c10 (round 3b + "at agent_elapsed_seconds >= 150 with no edit, make the best edit now").

| task | r1 | r2 | r3 | before (since the update) |
|---|---|---|---|---|
| fastapi_15589 | solved (edit 220 s) | timeout, no edit | solved (edit 273 s) | 0 / 13 |
| rich_3470 | wrong fix (edit 236 s) | wrong fix (234 s) | wrong fix (299 s) | 1 / ~10, mostly no edit |

## The checkpoint was not followed
- get_status calls: **0 of 6 tasks** (and 0 in every 1a run so far): the model never checks the clock, so a
  time-based rule cannot fire. First edits still came at 220–299 s.
- Repro writes per task 3.8 (round 3: 4.0, 1a_think 4.5); output tokens per step 367 (404–419).
- The harness only warns on tool calls (swegemma tools/base.py: budget_warning when <= 10 calls remain, i.e. from
  call 50 of 60; tasks use ~27), never on time.
- fastapi_15589 2/3 came from finding the right spot (the incoming-header loop) late but in time; with no visible
  behaviour change this is most likely chance. rich_3470 now always ends with an edit, but the wrong one.

## Lesson across rounds
Rules the model must remember to apply later (call get_status, read notes back, cap repro rewrites) are ignored;
what works is mechanical (config: temperature, thinking) or triggered by something in front of it (edit_file
error → Python fallback). Next: thinking budget 1,024 → 512 (config, cannot be ignored).
