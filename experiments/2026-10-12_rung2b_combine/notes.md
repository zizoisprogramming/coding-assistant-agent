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
