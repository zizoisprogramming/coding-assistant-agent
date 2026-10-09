# Rung-1l (2026-10-09): 1a reference (thinking off) vs 1a_think (thinking on, budget 1024), 2 repeats

Config: commit b3877c7 (1a = 30a8c5b; 1a_think = same + include_thoughts true, thinking_budget 1024), T 1.0.
adk-submission 0.2.13.

| | r1 | r2 | mean | timeouts |
|---|---|---|---|---|
| 1a (thinking off) | 1/4 | 0/4 | 0.5 | 4 (incl. rich_3882 r2, normally ~100 s) |
| 1a_think | 1/4 | 2/4 | 1.5 | 4 |

## "Thinking off" already thinks, invisibly
| | out tok/step | output vs visible | s/step | text written |
|---|---|---|---|---|
| 1a | 255–271 | 2.5–3.2× (hidden) | 6.9–7.9 | ~850 chars |
| 1a_think | 252–268 | 1.0× | 8.3–8.6 | ~70,000 chars |
Same output per step: since the 10-08 wheelhouse the model reasons with thinking "off" too, but 0.2.13 throws
those thoughts away. Thinking on costs the same and keeps them (visible, in history, and as text they survive
compaction summaries). Before the update 1a wrote ~130 tokens/step; now ~260 → about half as many steps fit in
5 min (fastapi_15589 first edit at 234–277 s).
Thinking budget: median 119, p90 677, max 1,479 tokens per step (12 of 221 steps > 1,024).

## Decision
Thinking on is the new 1a baseline (1a_think). 1a round 3 (free fixes, commit 1652543) gets the same thinking
settings; next run: 1a_think vs 1a round 3, 2 repeats.
