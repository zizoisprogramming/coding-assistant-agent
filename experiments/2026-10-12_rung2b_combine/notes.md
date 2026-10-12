# Rung-2b (2026-10-12): combine r4's edit trigger with bf's deep thinking

From rung-2a: r4_budget wins rich_3470 (acts on the "10 calls left" warning), bf wins fastapi_15589 (few deep steps,
thinking 4096, uses ~8 min). All arms 8 min / 28 calls / 80 turns, 4 tasks × 2, concurrency 2, 31B.

| Arm | = | Question |
|---|---|---|
| r4_budget | submitted 10-12 (LB pending) | reference in the same session |
| r4b_think | + thinking_budget 4096, max_output_tokens 8192 | keep 3470 and gain 15589? |
| r4b_think_t02 | r4b_think + temperature 0.2 | does bf's low temperature add anything? |
| r4b_think_bf3 | r4b_think + 3 bf prompt lines (contract first; fix where produced; copy sibling feature), 992 words | do bf's prompt ideas help or does length hurt? |

Watch: task duration (deep thinking = slower steps; 12-h total), first edit vs call-18 warning, out tokens/step.

## Results (2026-10-12)
| Arm | r1 | r2 | fastapi_15589 | rich_3470 | mean task s |
|---|---|---|---|---|---|
| r4_budget | 1/4 | 2/4 | 1/2 | 0/2 | 234 (both rounds) |
| r4b_think | 1/4 | 1/4 | 0/2 | 0/2 | 289 |
| **r4b_think_t02** | 2/4 | 2/4 | **2/2** | 0/2 | 288 |
| r4b_think_bf3 | 2/4 | 1/4 | 1/2 | 0/2 | 289 |
rich_3882 2/2 and fastapi_15588 0/2 for every arm.

Across rung-2a + 2b: r4_budget 7/16 (3470 2/4, 15589 1/4); bf 4/8 and r4b_think_t02 4/8 (both 15589 2/2, 3470 0/2).
- One-task differences are noise: r4_budget went 4/8 → 3/8 with identical files.
- fastapi_15589 (needs reasoning): thinking 4096 **with T 0.2** solves it (bf 2/2, r4b_think_t02 2/2; edits at
  call 11–12); thinking 4096 at T 1.0 does not (0/2).
- rich_3470: every arm edits at call 22–29 of 28, i.e. right at the end. r4_budget r1 (this round) had the
  right fix but the edit duplicated a line (`if self.is_jupyter:` twice → broken file) and no calls were left to
  check it. Deep thinking arms explore longer and never got it (0/6). The bottleneck is a late edit with no room
  to verify, not finding the bug.
- Runtime: thinking arms ~290 s/task on these hard tasks → ~9.6 h for 120 sequential tasks (bf: 8.9 h, finished on
  the scorer). Measured with concurrency 2 (~5–10 % slower than the scorer).
