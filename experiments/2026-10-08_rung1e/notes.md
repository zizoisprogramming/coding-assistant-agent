# Rung-1e (2026-10-08): 1b round 5 (verifier merged into executor), 1b only, 3 repeats

Config: commit 6408d34 (1b round 5 = round 4 + D6b merge). Same 4 tasks, temperature 0.2. 1a parked.

| | r1 | r2 | r3 | mean |
|---|---|---|---|---|
| 1b round 4 (rung-1d) | 3/4 | 2/4 | 1/4 | 2.0 |
| 1b round 5 (this) | 1/4 | 1/4 | 1/4 | 1.0 |

Per task (solved out of 3): rich_3882 3 → 3; fastapi_15588 0 → 0 (unguessable, rung-1b); rich_3470 1 → 0;
fastapi_15589 2 → 0 (timeout, empty diff all 3 times).

## Patterns
1. **Repro-rewrite loop (orchestrator, Phase A), the main loss.** fastapi_15589: 15 / 10 / 11 rewrites of
   /tmp/repro.py; the repro passes every time ("2 passed"), so it never shows the bug, and the orchestrator keeps
   rewriting it instead of delegating. First helper call at 193 s / 59 s (then back into the loop) / 228 s; the
   executor never got to edit. **Not new:** round 4 had the same loop on this task (16 / 12 / 4 rewrites) and on
   rich_3470 r3 (21); it survived there by a few seconds (solved at 273 s and 305 s). Likely trigger: round-4 fix C
   ("If your repro shows no bug, the repro is wrong") reads as "rewrite the repro".
2. **Merged executor uses its whole budget:** 13.6 tool calls per call (round 4: executor 7.0 + verifier 4.0 per
   call); in r1 rich_3470 it hit the limit and replied in prose ("Wait, the repro script is failing...") without a
   RESULT line.
3. **Self-check false PASS:** rich_3470 r2 executor "98 passed, RESULT: PASS", wrong fix (hidden test). Same as the
   separate verifier's 2 false PASSes in round 4: neither catches a wrong reading of a URL-only task.
4. **Broken shell quoting in the executor:** fastapi_15589 r2, ~20 grep/find calls with backslash-escaped quotes
   (grep -n \"name\"), each returning nothing, despite the single-quote rule.

## Attribution
Of the 1.0 drop, fastapi_15589 (−2) comes from the pre-existing Phase-A loop plus late delegation; the merge did not
get a chance to act there. rich_3470 (−1) is within noise (1/3 vs 0/3). So the run does not show that the merge
itself is worse, but it does not show a gain either, and the executor now runs at its call limit.
