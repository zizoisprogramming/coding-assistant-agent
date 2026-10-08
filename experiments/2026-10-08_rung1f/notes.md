# Rung-1f (2026-10-08): 1b round 5b (merged executor checks once; short requests), 1b only, 3 repeats

Config: commit 63dd0ef. Same 4 tasks, temperature 0.2.

| 1b round | r1 | r2 | r3 | mean | per task (of 3): 15588 / 15589 / 3882 / 3470 |
|---|---|---|---|---|---|
| 4 (separate verifier, rung-1d) | 3 | 2 | 1 | 2.0 | 0 / 2 / 3 / 1 |
| 5 (merged, rung-1e) | 1 | 1 | 1 | 1.0 | 0 / 0 / 3 / 0 |
| 5b (this) | 2 | 1 | 1 | 1.33 | 0 / 1 / 3 / 0 |

## The 5b fix worked on what it targeted
- Executor seconds per call: 63 → **30** (round 4 executor + verifier: 14 + 17 = 31).
- Executor inner tool calls: median 12 → ~5 (3–16); requests mostly 125–695 chars (two on fastapi_15589 still
  1,606–2,468 chars: the repro was pasted in).
- Executor wrote /tmp/repro.py 0 times (round 5: 8); check scripts 17 → ~12 small python heredocs.

## What still loses tasks (both pre-existing, not from the merge)
1. **Orchestrator repro-rewrite loop (fastapi_15589):** 6 / 22 / 11 rewrites; r2 never reached the executor, r3
   reached it at 266 s and timed out. Present in every round since round 4 (16/12/4, 15/10/11, 6/22/11).
2. **Reader runaway on the URL-only task (rich_3470):** 13 / 28 / 22 inner calls (prompt says at most 8), 101 / 279 /
   183 s, with 50–60 s gaps of long text between calls; the task text is only "fix #2563". Round 4 r1 had the same
   (~23 calls). Reader prompt unchanged since round 4.
3. Executor still writes grep with backslash-escaped quotes (16 calls), returning nothing.
4. Compaction drops tool calls and results from its summary (ADK llm_event_summarizer.py keeps only part.text), so
   after compaction nothing records "repro written, it passes" → feeds pattern 1 (see D1e/D1f, file record idea).

## Conclusion
The merge, with bounded prompts, costs the same time as the separate executor + verifier. The score gap to round 4
(1.33 vs 2.0) sits in the two pre-existing patterns above, which vary run to run on 2 of the 4 tasks.
