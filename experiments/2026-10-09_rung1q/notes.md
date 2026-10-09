# Rung-1q (2026-10-09): 1a round 3e ("fix first, then check"), fastapi_15589 + rich_3470, 3 repeats

Config: commit e22c831 (round 3d + workflow reordered: no repro before the edit; checkpoint removed; budget 512).

| task | r1 | r2 | r3 |
|---|---|---|---|
| fastapi_15589 | solved (edit 298 s) | wrong fix (250 s) | wrong fix (278 s) |
| rich_3470 | timeout, no edit | timeout, no edit | solved (edit 211 s) |

2/6 (3d: 1/6, 3c: 2/6) — within noise. The reorder was mostly ignored: repro written 2–6 times **before** the
first edit in every task; first edits still 211–298 s or never.

## Where we stand (end of 10-09)
Prompt rules about *when* to edit (time checkpoint, step order) do not change when the model commits; config
changes act mechanically but the saved time goes into more investigation. Open options for tomorrow:
- harness-driven pressure: lower max_tool_calls so the harness's own "Finalize your edits" budget_warning appears
  in tool results earlier (swegemma tools/base.py: from <= 10 calls left);
- the verifier with an event-triggered time check (D19), once edits come earlier;
- accept the ceiling on these two tasks and widen the dev set instead.
