# Rung-1t (2026-10-10): 1a round 4b (prompt rewritten with 3 decision rules + 3rd example), 4 tasks × 2

Config: commit ef638d6. Result **1/4, 1/4** (round 4: 2/4, 2/4). Only rich_3882 solved.

| task | round 4 | round 4b |
|---|---|---|
| rich_3882 | solved, edit 38–44 s | solved, edit 68–93 s (more scripts first) |
| fastapi_15588 | wrong fix, edit 63–68 s | wrong fix, edit 54–145 s |
| rich_3470 | solved ×2 (edit 260–277 s, at the deadline) | **no edit ×2** |
| fastapi_15589 | wrong fix / no edit | wrong fix (243 s) / no edit |

## What happened on rich_3470
- r1: mechanism found at 108 s; the check script "works" → "So where is the bug?" → searched other paths
  (export_text, record set later, __init__), i.e. new rule 2 applied in the wrong place; re-read the same functions
  at 206–270 s; no edit.
- r2: "AHA" at 144 s, exact fix written in a thought at 197 s, then explored end_capture/nested captures and rewrote
  one test script 6× from scratch; no edit.
- The new rules were almost never referenced explicitly; rule 3 never came into play (no edit → no failing test).
  "Regression" wording showed up as "make sure I'm not introducing regressions" before editing (rich_3882 r1).
- read_file still used (incl. the broken `start_line` form) despite the prompt.

## Conclusion
Round 4b is worse than round 4 on the same tasks (1.0 vs 2.0); the most plausible cause is the added rules
encouraging more searching/checking before the edit (rule 2 in particular) and a longer prompt (1,240 vs 927 words).
With 2 runs this could partly be noise, but there is no sign of benefit. Revert to round 4 (best measured).
