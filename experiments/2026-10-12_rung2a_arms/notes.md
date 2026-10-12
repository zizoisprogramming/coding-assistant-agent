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
