# Rung-2a (2026-10-12): five arms in one session — public 0.18 recipe vs our round 4 (LB 0.12)

Why: round 4 scored 0.12 on the LB; 8 public notebooks reach 0.17–0.18 with no LoRA, almost all with one recipe
(single agent, T 0.2, thinking 4096, max_output 8192, 8 min / 28 calls; PLAN.md). Find which part of it matters.
Design (user, 10-12): 4 dev tasks × 2 repeats, 2 tasks at a time (CONCURRENCY = 2; each task has its own sandbox
workspace and /tmp), 31B. Each r4_* arm changes one thing from the submitted round 4 (dist/src_1a_r4_lb).

| Arm | What | Differs from r4 |
|---|---|---|
| bf | public Budget-Fit Single Agent v4 (verracodeguacas), files verbatim, LB 0.18 | everything (calibration) |
| r4 | round 4 as submitted, LB 0.12 (4.5 min / 50 calls) | — |
| r4_budget | 8 min / 28 calls / 80 turns | budget only (prompt still says "about 5 minutes") |
| r4_think | thinking_budget 4096, max_output_tokens 8192 | thinking only |
| r4_t02 | temperature 0.2 | temperature only |

Read first: bf vs r4. If bf does not beat r4 on these 4 tasks, this dev set cannot see the LB gap and the arms
below it are not interpretable; then the next batch needs more tasks. Also check concurrency cost: median s/step
vs earlier sequential runs (31B round 4: ~3–4 s median gap, ~29 tokens/s).

## Results (2026-10-12)
| Arm | r1 | r2 | fastapi_15589 | rich_3470 | rich_3882 | fastapi_15588 |
|---|---|---|---|---|---|---|
| bf (public 0.18) | 2/4 | 2/4 | **2/2** (solved at ~480 s) | 0/2 (28 calls spent reading, no edit) | 2/2 | 0/2 |
| r4 (ours, 0.12) | 1/4 | 1/4 | 0/2 (timeout) | 0/2 (timeout) | 2/2 | 0/2 |
| **r4_budget** | 2/4 | 2/4 | 0/2 | **2/2** | 2/2 | 0/2 |
| r4_think | 1/4 | 1/4 | 0/2 (timeout) | 0/2 (timeout) | 2/2 | 0/2 |
| r4_t02 | 2/4 | 1/4 | 1/2 | 0/2 | 2/2 | 0/2 |

- bf beats r4 (4/8 vs 2/8): the dev set does see the LB gap. r4_budget ties bf (4/8) but on a different hard task.
- **Mechanism of r4_budget:** with 28 calls the harness's "Only 10 tool calls remain" warning comes after call 18;
  on the hard tasks the first edit followed within 5–8 calls (calls 23–26, 138–235 s). With 50 calls the warning
  comes at call 40, after the 4.5-min clock has already run out (r4 timed out on both hard tasks). This matches the
  earlier lesson: event-triggered signals work, self-monitoring rules do not. Tasks ended at 190–330 s (call-bound),
  so the 8-min cap was rarely used.
- bf solves fastapi_15589 because it uses ~8 min (edits at 405–433 s, thinking 4096); r4_budget stops at ~320 s.
- r4_think alone hurts inside 4.5 min (fewer steps, timeouts); r4_t02 alone: noise-level.
- Concurrency 2 cost ~5–10 % tokens/s (25–30 vs 29–31 sequential); a SILENT stall appeared once (r4_think r1
  rich_3470, 78 s).
- bf failure mode: after the call budget is exhausted it loops submit_patch until max_turns 80 (empty patch).
