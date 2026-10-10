# Lessons from 1a rounds after the wheelhouse update (2026-10-10)

| round | words | change | 15588 | 15589 | 3882 | 3470 |
|---|---|---|---|---|---|---|
| 1a_think | 644 | thinking on | 0/2 | 0/2 | 2/2 | 1/2 |
| r3 | 1,053 | + free fixes + notes | 0/2 | 0/2 | 2/2 | 0/2 |
| r3c | 823 | − notes + time checkpoint | – | 2/3 | – | 0/3 |
| r3d | 823 | + budget 512 | – | 1/3 | – | 0/3 |
| r3e | 780 | + edit before repro | – | 1/3 | – | 1/3 |
| r3f | 873 | + commit trigger + sed -i | – | 1/3 | – | 0/3 |
| r4 | 927 | rewrite: scoring, 1 rule, 2 examples | 0/2 | 0/2 | 2/2 | 2/2 |
| r4b | 1,240 | rewrite: 3 rules, 3 examples | 0/2 | 0/2 | 2/2 | 0/2 |

- Hard tasks: ~20–25 % in every round (15589 5/20, 3470 4/20); round differences on them are within noise.
- Real effect: round 4's fast path on clear tasks (rich_3882 edit 59–74 → 38–44 s; fastapi_15588 94–153 → 63–68 s).
- In almost every run (success and failure) the agent saw the code where the gold fix goes within the first 1–5
  tool calls (5–30 s; scripts/hard_tasks.py). Successes edited exactly there (111–298 s); failures edited
  elsewhere (15589) or never (3470). Widening the search (4b rule 2) moves the agent away from that spot.
- Mistakes in our process: judging rounds by noise-level score differences; rules derived from single dev tasks
  (overfitting); patching instead of designing (prompt 644 → 1,240 words, backfiring additions); rules needing
  self-monitoring (time, counting, order) are ignored, only event-triggered rules work; setup changed underneath.
- Round 5 (user, 10-10): round 4 condensed to < 900 words; one decision rule that now also says "the first code
  you find that implements what the task names is usually where the fix goes: edit there first"; one example with
  the adjust-the-same-edit case folded in; the 4b rules dropped; overlapping sections merged.
