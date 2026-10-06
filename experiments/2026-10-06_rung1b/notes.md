# 2026-10-06 — Rung 1b: same comparison after prompt round 2 (commit 30a8c5b)

**Setup:** identical to `../2026-10-06_rung1/` (same Kaggle notebook, L4×4, same 4 tasks, same sample config);
only the 1a/1b prompts changed (round 2). Raw results: `data/results/2026-10-06_rung1b/` (gitignored).

**Score:** sample 1/4 (unchanged), **1a 3/4** (was 1/4), **1b 2/4** (was 1/4). 4 tasks → directional only.

| | sample | 1a | 1b |
|---|---|---|---|
| Resolved | rich_3882 | fastapi_15589, rich_3882, rich_3470 | fastapi_15589, rich_3882 |
| Time per task (avg) | 231 s | **121 s** | 180 s |
| Output tokens per task (avg) | ~6,250 | **~3,400** | ~5,300 |
| Timeouts / crashes | 2 timeouts | 0 | 1 context overflow (patch lost) |
| Scratch files in patches | 2/4 | **0/4** | 0/4 |

## Findings
1. **Round-2 fixes worked for 1a:** no scratch files in any patch, no timeouts, 1 broken tool call (was 13), every
   task finished in ≤171 s (well inside 5 min).
2. **fastapi_15588 is not solvable from the task text.** 1a now handles both \r and \n (fix applied), but the
   hidden test wants the message `SSE '<field>' must be a single line`; the task text never says it. Treat as
   an unguessable-message task; don't tune prompts for it.
3. **New bug: malformed `start_line"` argument key.** read_file is sometimes called with keys `start_line"` /
   `end_line"` (stray quote) → the line range is ignored → the whole file comes back (~1,500 tokens each).
   Seen in 4 traces across both runs (1a, 1b, sample). In 1b fastapi_15588 the executor re-read the file 17×.
4. **Helpers have no compaction.** That executor's prompt grew linearly 3.6k → 29.4k with no drop (the
   orchestrator's compaction does not reach AgentTool sessions) → ContextWindowExceededError → patch discarded.
   Also the executor ignored its "at most 10 tool calls" (made 23).
5. **1b rich_3470:** wrong fix (moved record-buffer logic; test_capture_and_record fails); verifier format 0/2.

## Candidate next changes (not applied)
- Read line ranges with run_command: sed -n '96,115p' path (one string argument) instead of read_file ranges.
- 1b: keep helper sessions short (fewer calls, smaller outputs) since nothing compacts them; or drop to 1a.
