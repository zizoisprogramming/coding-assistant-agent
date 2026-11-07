# What helps: clock, pub, mix, bf and the rest (2026-11-06)

Local only. Rebuild: `python3 scripts/paper/build_run_table.py`, then `compare_arches.py`, `compare_extra.py`, `analyze_edits.py`, `analyze_hidden_failures.py` in scripts/paper. 2,434 runs with call-level logs (data/analysis/run_table.jsonl, gitignored).

Method: comparisons are paired by task; intervals come from resampling tasks. "Same run" = both arms ran in one notebook. Limits: most pairs are from different runs; mix and bf ran in October only, never beside pub; clock8 data is mostly e24, picked from tasks already solved; within-task behaviour links are correlation; edit and command classes are heuristics, checked against harness counts and gold files. Hidden-test logs exist only for October runs.

## The four families
| | bf | mix | pub024 | clock (sq1c2 / a8 / a6) |
|---|---|---|---|---|
| Agents | 1 | 1 | 1 | fixer, then submit-only finisher |
| Prompt words | 685 | 783 | 1157 | 849 + 48 |
| Shell | run_command | run_command | run_command | skill script (clock line, refusals) |
| Call limit, cap | 28, 8 min | 28, 8 min | 28, 8 min | 80, 8 / 7 / 6 min |
| Thinking | 4096 | 2048 | 4096 | 4096 |
| LB | not submitted plain | 0.17 | 0.18 | 8, 7 min timed out; 6 min 0.12, 0.10 |

## Task vs agent
Variance of solved over 1,338 runs: task 64%, agent family 0.7%, same task same family (chance) 35%. 17 of 58 tasks with 6+ runs were never solved by anything. Per-task solve rates correlate with pub at r = 0.70-0.94.

## Outcomes, paired with pub on common tasks
| Group | Tasks | Solve (vs pub) | Diff, 95% | Seconds (vs pub) |
|---|---|---|---|---|
| bf | 16 | 25% (20%) | +5, -8 to +21 | 321 (377) |
| mix | 32 | 33% (29%) | +5, -3 to +13 | 339 (348) |
| reader skill sk_a2 / _32 | 48 | 35% (34%) | +1, -4 to +6 | 309 (340) |
| locator-editor | 16 | 20% (20%) | +1, -8 to +8 | 390 (377) |
| nav skill | 16 | 20% (20%) | +1, -3 to +5 | 373 (377) |
| fixer/finisher, no clock | 24 | 69% (68%) | +1, -7 to +9 | 369 (288) |
| clock 8 min | 24 (picked) | 78% (68%) | +10, +1 to +20 | 293 (288) |
| clock 7 min | 40 | 49% (41%) | +7, -1 to +17 | 317 (334) |
| clock 6 min | 54 | 33% (33%) | -1, -5 to +3 | 279 (349) |
| reporter (srep) | 38 | 16% (17%) | -1, -9 to +6 | 393 (391) |

dev16 per 16: bf 4.0 (1 pass), mix 3.7, le 3.2, nav 3.2, pub 3.1, sk 3.0, srep 3.0, clock6 2.4. Same-run on e24: sq1c2t7 75%, 274 s, no patch 12%; pub 62%, 282 s, no patch 25%.

## Single changes
| Change | Effect, pts | Time | Note |
|---|---|---|---|
| Fixer/finisher split alone | -14 (-29 to +3) | +61 s | different runs, 12 tasks |
| Clock added to the split | +21 (-4 to +50) | +27 s | same run, 12 tasks |
| Clock + shell-call fix | +29 (+12 to +50) | -11 s | different runs |
| "Second attempt" | +17 (0 to +33) | +10 s | same run; attempt ran 0 times (r29), so this is pure noise, a placebo |
| Checklist, 8 min | +10 (0 to +23) | -2 s | same run, 24 tasks |
| Checklist, 6 min | +4 (-8 to +17) | +12 s | same run, 24 tasks |
| Repeat block, 8 min | -6 (-17 to +6) | +32 s | different runs |
| No-bug note | -12 (-28 to 0) | +22 s | different runs |
| Reads through clock | 0 (-25 to +21) | +36 s | same run |
| Thinking 4096 to 2048 | 0 and +4 (-3 to +13) | +15 s, -21 s | same run, two tests |
| 28 to 32 calls, skill | -2 (-8 to +3) | +49 s | different runs |
| Reviewer | -1 and +6 (-3 to +16) | +106, +41 s | |
| 3 parallel fixers | -14 (-27 to 0) | -37 s | compaction crashes |
| Reporter | +4 and -7 | | same run |

## Where runs fail
- Solved runs nearly always edit a gold file first (pub 82/82). Read a gold file: 91-100% of runs in every family. Wrong edits touch a gold file: pub 58/74, mix 29/36, clock family 119/136. Finding the file is not the bottleneck, which is why navigation skills and locator-editor changed nothing.
- 227 wrong patches with hidden-test logs (October, mix/bf/le family): 84% in a gold file; 83% failed on assertions, 6% on missing names, 5% on signatures, 5% on syntax.
- Before the first edit, mean seconds: sq1 362, pub 279, a6 276, sq1c2 245, skA2 244, bf 243, mix 236, t7 216, a8 206.

## Budget and tools
- Single-agent, 28-call runs, tried an edit and never landed one: bf 12%, mix 11%, pub 12%, skA2 6%. pub: 28 of 28 first tried at call 27 or later; 26 failed only on BudgetExceeded. Clock arms (80 calls): 2-3%. Landing those at their task's solve rate: about 14 more solves in 480 runs, +3 pts (estimate).
- edit_file, 3,307 logged calls: ok 68%, malformed 18%, text mismatch 10%, out of budget 4%. In 596 of 607 malformed calls new_string swallowed the literal "old_string", so the string delimiter broke. 440 of 607 were followed at once by another malformed call. Rate is higher for single-line (39% vs 10%) and short new_string (30% vs 13% at 200 characters). Cost: about 5-16 s per run.
- Submit loop: bf 26.9 submit calls per run, mix 26.3, 30-35 s per run after the first submit; pub 1.0, sk_a 0.6, r4_mid 0.9 (same day as bf). bf and mix have "Do not end a turn with plain prose: keep calling tools or call submit_patch"; pub and sk_a2 do not. le5 lacks the line and loops too (22.6), so the line is the likely but not the only cause.
- Model seconds per run: search 41-98, read 46-123, scripts 11-76, tests 1-14, scratch files 5 (pub) vs 59-101 (split arms).
- Call-limit what-if, a8 family (stop at call N, solve lost if last edit is later): 80: 113/144, 284 s; 40: 106, 261 s; 36: 105, 256 s; 32: 99, 245 s; 28: 94, 231 s. Same shape for sq1c2 and t7.

## Prompt rules followed?
"Edit by call 12": bf 19%, mix 16%, pub 23%, skA2 22%; clock arms, driven by events, 31-38%. Median first-edit call 17-19 vs 13-14. Test after the edit: pub 26%, mix 38%, skA2 19%, a8 78%.

## Same task, same family: behaviour vs solving (correlation)
First edit in a gold file +35 (+7 to +60). Test after edit +7 (+1 to +12). First edit by call 12 +5 (+1 to +8). Read tests before editing +7 (-2 to +15). First edit after 300 s -10 (-16 to -3). Scratch file before editing -10 (-17 to -3). 6+ searches before editing -9 (-14 to -5). 4+ edits -12 (-22 to -3). Script before editing -1 (-5 to +4). 6+ reads before editing -1 (-7 to +5).
Own signals: a8-family repro passes 96% solved, else 67%; a6-family 81%, else 32%. Last test passed: clock8 95%, clock6 85%, pub 72%; no test: 69%, 40%, 42%.

## Corrections to earlier notes
- "Capped runs never solve" is a label artefact (see PLAN).
- In this session I first read "tried and never landed" as garbled edits. It is mostly the call limit.

## Right file, wrong edit (scripts/paper/analyze_right_file.py; 849 runs, 56 tasks; 1,021 of 1,330 edits located in the base file)
Solve rate per task once a real-fix file is edited, by file size: under 200 lines 65%, 200-500 45%, 500-1000 39%, 1000-2000 54%, 2000-3000 22%, 3000+ 9%. Few tasks per band. Spearman over 41 tasks: file size -0.19, fix size -0.58, fix files -0.42. By fix size, per task: up to 10 lines 63-66%, 10-20 44%, 20-40 35%, 40+ 4%.
Wrong edits: 64% touch the real lines, 21% same function, 16% elsewhere. Share on the real lines falls with file size up to 3000 lines (100, 73, 57, 38, 27%), then 83% at 3000+, where fixes are large.
Same task: edit on the real lines +38 pts (+26 to +48). Read the real lines before editing: solved 99%, wrong 98%. Read every real region: solved 92%, wrong 53%; same task +6 (0 to +18), 10 tasks. Read 150+ lines 0, 400+ lines +2. More than 3 edits -15. read_file truncated in 26-72% of runs, rising with size.

## Compaction and checklist (scripts/paper/analyze_compaction.py, analyze_compaction2.py)
Compactions per run: pub 1.3, clock 1.4, first at about 135-150 s. One summarizer call: median 26 s, 765 tokens. Share of run time: 10-11% (pub-type 36 s a run). No same-run arm has measured reducing it.
Same task and arm: first compaction before the first edit -21 pts (-31 to -10), 111 vs 92 runs; partly slow or hard runs. 2+ compactions -6, 3+ -11; also confounded with long runs.
After the first compaction, issue opening in context: arms with the issue only in the task message 0%, issue in the system prompt 100%. Issue's quoted names and strings anywhere in context: 78% vs 100%; this counts code the agent read. An older note measured 17% on a different basis (PLAN patterns section), not reconciled.
Effects, same tasks: issue in prompt alone -7 (-11 to -3; mostly different runs). Checklist on top of issue in prompt: pooled +11 (+4 to +19); same run a8ra to a8rc +10 (0 to +23), f6ra to f6rc +4 (-10 to +17). Issue in prompt on top of checklist: a6c to a6rc +2 (-10 to +12), same run. "Checklist shown again" counts as solved 40/41 vs 0/7 only because it is shown at the first edit, so it says nothing.

## Do the clock's numbers help? (scripts/paper/analyze_clock_numbers2.py)
Every clock arm has shown seconds ("[clock] N s of 480 used") and a time plan in the prompt; no arm without numbers exists. On the same 24 tasks, mostly different runs: first edit by 135 s: pub 22%, clock arms 38-46%; median first edit pub 204 s, clock 119-158 s. That shift comes before any warning fires. Moving the warning from 180 to 160 s moved nothing (by 180 s: a8 60%, t7 56%). Chance the next turn is an edit with no edit yet: plain line 6-9%, warning 6-11%, refusal 23-39%. Reasoning refers to time in 0.3-0.5% of turns; samples are mostly reactions to refusals or the end. So refusals act, warnings do not; whether the prompt's time plan causes the early shift is untested.

## Handoff and temperature evidence, for the "spawn an editor after locating" idea
First read of a real-fix file: median 11-13 s; first edit: pub 234 s, a8 119 s. Locator-editor vs mix, same tasks: le -4, le2 -10, le3 -8, le5 +2, le6 +2 pts; first edit 266 s; 48% no edit. le5 timed out on the LB; le6 6 min scored 0.15. Reporter handoff: first edit median 321 s vs pub 235 s. Temperature: sk_a2 0.2 to 0.5: -2 (-15 to +10), no patch 23% to 31%. T1.0 to 0.2 on 4 tasks +18; r4_budget T1.0 vs r4b_think_t02 -4 (-24 to +17) with thinking also changed. T0 no better than 0.2 (r13). le6_hot (T1.0) was designed but never run, so high temperature in an editor after a handoff is untested.
Decision 11-06: words-only state line, refusals kept, 36 and 32 both tested, other places as its own arm, temperature replay first (see PLAN r52, r53).
