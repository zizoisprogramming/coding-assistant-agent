# Rung-1s (2026-10-10): 1a round 4 (rewritten prompt + generic examples), 4 tasks × 2

Config: commit 9abba5d (thinking 512, T 1.0). Result **2/4, 2/4 = 2.0** — best since the wheelhouse update
(1a_think 1.5, round 3 1.0) and very consistent between runs.

| task | r1 | r2 |
|---|---|---|
| rich_3882 | solved, edit 44 s | solved, edit 38 s |
| fastapi_15588 | wrong fix, edit **63 s** | wrong fix, edit **68 s** |
| rich_3470 | **solved**, edit 260 s (timeout) | **solved**, edit 277 s (timeout) |
| fastapi_15589 | wrong fix, edit 270 s (wrong place) | timeout, no edit |

## What changed
- Easy/clear tasks now take the fast path: edits at 38–68 s (before: 44–121 s).
- rich_3470 "found it" → edit gap: r1 56 s (before 1–2+ min, or never); r2 still 144 s.
- No imagined tool outputs; two raw-token leaks inside thoughts (`call:read_file{...}<tool_call|>`, `<|channel>thought`),
  both recovered. read_file still used 11–18× on the hard tasks despite "do not use read_file".

## rich_3470 was solved by timing luck
Both solves submitted at the time limit. r1 at 285 s saw the existing test_capture_and_record fail and wrote
"Wait! ... failed! ... Let's read the test." — the timeout came before it could back off. That existing test asserts
the OLD behaviour the task changes (captured text is recorded); the hidden test patch replaces it. Across all runs,
11 of 54 rich_3470 attempts made the correct fix, saw this test fail and moved away from it; in 1b the verifier
returned FAIL on correct fixes 5 times. Our rule "a baseline test that now fails means the change is wrong" causes it.

## fastapi_15589: the simple case already works
First repro (plain header param) shows underscores already rejected ("it ALREADY does NOT accept"), so the model
decides it does not understand the task and wanders into class definitions (Param, Header.__init__). The bug is in
a less common path that uses the same option (header models). r2 tried that path at 168 s, made a script error, left.

## Next (round 4b, generic)
1. Old-behaviour tests: if a failing test asserts exactly the old behaviour the task asks to change, the task wins.
2. Simple case already fine: the bug is in another code path that uses the same names/option (other branches,
   aliases, models, collections); check those paths before concluding anything.
