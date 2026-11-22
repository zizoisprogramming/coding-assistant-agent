# Lessons so far (written 2026-11-20, during r126)

A short, plain summary of everything tried since September: what the model obeys, what worked, what is closed and why,
and what is NOT closed forever. Numbers and file paths are in docs/PLAN.md (search the run name, e.g. "RESULT r124").
Update this file whenever a line opens or closes.

## 1. Where we stand

- **2026-11-22: control = sk_a2. r138 / r139 (six one-change arms + sk_a2m, 8 solvable dev16): no arm beat sk_a2 by the
  bar (+2 of 8); all 2-4/8 vs sk_a2 3/8 twice. 29% of runs hit the 480 s cap (few, slow calls on rich_3180 / rich_3521 /
  fastapi_15589). Prompt / sampling / memory tweaks of sk_a2 are now inside luck; daily LB candidate sk_a2t.**
- **Current base agent: sb1hl ("sb1h-lite")** = one agent, harness tools only (run_command, read_file, get_status,
  submit_patch), every edit made by one heredoc command whose fixed Python step replaces the old text only when it occurs
  once, short prompt (7.4k chars) with worked examples. r123 + r124: solves equal to sb1h (18/32 vs 17/32), a third fewer
  compactions, ~30 s faster per run. Not yet checked on tasks never used to pick anything, not yet on the leaderboard.
- **Leaderboard (58 public tasks, score = solved / 58, floored):** our best fits are sk_a2 0.18, mix 0.17, sk_a2_32 0.17;
  then sb1hl 0.15, combo1 0.15, evidc 0.15 / 0.12, le6_t6 0.15, sa2 0.12, nn32rcn2 0.12, sq1c2a6 0.12 / 0.10, evidefs 0.10. The public
  pub024 scored 0.18 (local control only; we never submit public configs). Top of the board ~0.29.
- **A prompt written around the solved rhythm is followed and does no harm (r144, sk_a2_60x):** LOOK -> RUN once -> EDIT -> LOOK
  AGAIN + RUN, both worked examples in that shape: 9/16 vs 21/48 (44%) for sk_a2 / sk_a2_60 on the same 8 tasks (P(>= 9 | 44%) = 0.22,
  so not proven); same mean time (358 s); compactions 1.56. Every edit that stayed in the tree solved (9/9); all 7 failures had no patch
  (3 edits refused at the 28-call limit, all in the wrong place). The 'RUN once' part is not obeyed: 12 of 14 edited runs ran code 2+ times first.
- **Gates before the edit become loops (r141-r142, sk_a2v):** "your repro does not show the bug: fix it or edit now" was read as
  "fix it" 10 times in a row; on hard-to-reproduce bugs the agent rewrote the repro until time ran out. 6/16 vs 9/16.
  Wrong edits are not a finding problem (the real-fix lines were on screen in ~95% of wrong edits).
- **No local subset predicts our LB order (2026-11-22, lb_subsets.py):** LB noise (SD 2.7 tasks) is bigger than the whole
  spread of our LB scores (SD 1.7). Choose on large same-run local samples.
- **Our LB order is luck (2026-11-22, sk_a2 deep dive):** if our ten single-agent LB scores came from one agent
  (8.5/58), the best of 12 submissions reaching 11/58 (sk_a2) has p 0.95. sk_a2 = pub024 = sb1hl = sk_a2_32 on local
  solves (task-matched); sk_a2's real edge is process (no patch 15% vs 28%, ~55 s faster, no very long replies).
- **LB noise is large:** the same file scored 9/58 and 7/58; one score has SD ~0.045. A local edge smaller than ~+3 solves
  per 58 cannot be seen on the LB.
- **LB time limit (12 h for all tasks) is real:** every 7-8 min "skill shell" agent, evid3, le5 and 12B timed out. Agents
  built on run_command at 8 min / 28 calls fit.

## 2. How this model behaves (the rules everything else follows)

1. **It obeys what the tools print, not what the prompt asks.** A refused call moved its next action 23-39% of the time,
   a written warning 6-11%. Procedure, self-checks, plans and budgets written in the prompt are mostly ignored (a scout told
   "about 10 tool calls" used 44).
2. **It copies short commands from tool output reliably**, and copies whole commands from worked examples well (the
   heredoc edit is copied in 70-100% of edits). But it **shortens or mangles long commands copied from the prompt**: fenced
   blocks got sent with their ``` lines (sb7: 189/256 calls), and a two-part read command was cut to its first line
   (sbB: 71/73 reads).
3. **Long string arguments break its tool calls** (Gemma closes them with a stray quote / backtick): edit_file broke in
   31-43% of calls and then looped. Heredoc edits through run_command removed that completely (r118: 7/22 runs -> 0/22).
4. **It reads history but does not act on it.** Shown before, at, or after the edit, with or without the changed lines, it
   named a commit in at most 2/5 runs and changed an edit because of history in 0 runs (r116-r122).
5. **Its time goes almost entirely into writing, not tools.** First edit ~180-330 s of 480. Runs that never edit usually
   spend one reply of ~130 s using the whole 4,096-token thinking allowance, often hand-simulating code in a loop; runs with
   such a reply solve 28% vs 52% (same task lower on 7 of 9).
6. **Context gets cut at 14,336 tokens** (harness compaction, not ours to change). A longer prompt means more compactions,
   slower runs and lost context (sbA 3,225 words: 3.1 compactions per run vs 1.5).
7. **Information is the biggest lever measured:** the same agent with the issue's missing information added went from
   6/76 to 30/76 solved (r45 info test, 2 passes; the same 13 tasks solved in both). It was an ORACLE test: 19 one-line
   issues got their linked GitHub report (1/19 -> 10/19 in pass 1), 19 others got the hidden test's lines (1/19 -> 5/19);
   neither source exists on the scorer. It shows the wall, not a tool: the model fails because it does not know WHAT
   behaviour is wanted. Most failures are not about finding the file (80% edit the right file) but about wrong logic.
9. **Why history failed where information worked:** information said what the result must be (directly usable); history
   says how the code changed before (a hint that needs inference, useful on ~40% of tasks). And the model acts on blocks,
   not on text it reads: a replayed rule in tool output was weak, "blocks work because they block" (r46).
8. **Wrong fixes keep the old tests green.** In r125 every one of 19 edits left the existing test file green, including
   all of peewee's wrong fixes; what the model lacks is the new behaviour, not regressions.

10. **The tasks are pull-request descriptions, and 20% of them cannot be won from what the agent sees.** 26 of the 129
    public tasks need exact text (an error message, an output string) that only the hidden test knows: 3% solved vs 41%
    on the rest. One-liners with an issue link hide the behaviour in the link. Fix size rules everything: 1 file and
    <= 20 lines 57% (no-exact-text), multi-file 1-14%. (TASK ANATOMY in PLAN.)

11. **The texts are change titles, not grading criteria.** Every asserted value appears in only 5% of texts; 46% give no
    entry point, no example and no behaviour. On winnable tasks an example input (87% vs 43%) and the behaviour in words
    (69% vs 41%) go with much higher solve rates.
12. **On winnable tasks the model fails mostly by not committing, not by wrong logic:** 65% of failed runs never changed
    the source (17% right place with wrong logic). They usually have a theory (86%), but form it later and keep re-checking
    it until time runs out.

## 3. What worked (kept)

| change | evidence |
|---|---|
| Heredoc edits instead of edit_file (sb1h) | broken-call loops 7/22 runs -> 0/22; EDITED 61-100% |
| Short prompt, unused parts removed (sb1hl) | compactions 1.62 -> 1.25 and 1.50 -> 1.04; agent s -70 / -17 s; solves equal |
| Worked example for every case + an event line for every tool error ("WHEN A TOOL RESULT SAYS") | events are followed; the cut-apart, found-0 and fence errors are recovered on the next call in most runs |
| Removing a tool to enforce a behaviour (structure) | e.g. no edit_file -> no broken edit strings |
| Reproduce first, check after the edit | runs that re-run their check after the last edit solve far more often (bank 57% vs 32%) |
| Harness-time facts: the `_swegemma_baseline` commit time = run start (0-1 s) | lets a step know elapsed time (sbG) |

## 4. Closed (do not retry as is; the reason is what to beat if it ever comes back)

| line | what happened |
|---|---|
| Clock / time numbers in prompts or events (sq1c2 family) | no solve gain, slower, LB timeouts |
| Skill-shell agents at 7-8 min | LB timeouts (scorer slowness for skill scripts) |
| Thinking caps (thinking 2048, thinking off) | replies got slower, not shorter (r111); thinking off weaker |
| Lower call cap / shorter time cap | solves use the whole budget; 7.5 min loses up to 7% |
| Presence penalty | broke tool calls; no length effect once edits are heredocs |
| Two-agent designs (race, team, scout -> fixer, check stages, evidence + fixer splits) | slow, information dropped at compaction, no solve gain (user closed 11-17; only the user's sb8 split excepted) |
| Location aids (map, code-path tool, call graph, navigator) | mechanics work, solves do not move, runs slower |
| Gates that refuse calls (evgate family) | each refusal costs 60-80 s of thinking; no gain |
| Draft-first, solved examples in the prompt, "think briefly" | ties or mechanism failed |
| Few-shot "fs" copies of the LB agents | inside luck, more form errors |
| History from issue names / BM25 past commits (evid*, evidc_p, sb2-sb7) | wrong functions picked or not used |
| History at the read (sbB) | the model dropped the history half of the command |
| History printed after the edit (sbA, sbF, sbF2) | read, sometimes named, never changed an edit |
| History-first gate (sbG, 6-min window) | never fired: first edits come too late |
| Auto test after the edit, before/after (sb1hlt, idea A) | all green, +83 s, more time-outs (r125) |
| Sampling T 1.0 / top_k 64 (sb1hlg) | r126: no fewer maxed-thinking runs (2 vs 1 of 4; with r89 4/16 vs 6/16) |
| Expectation agent -> solver as built (sbX1) | r127: first agent 293-424 s of the shared 480 s, 0/4 solved, text-form tool calls |
| 12B / E4B models | weaker |

## 5. Not closed forever (conditions under which it is worth another try)

- **CURRENT LINE - the expectation (sbE1 / sbE2, r127):** the agent writes asserts of the wanted behaviour first; a fixed
  checker prints 'the problem is shown' / 'passes before any edit' / 'still fails' / 'passes with your edit'. When adopted it
  works fast (E2 rich_3278: first edit at 66-89 s, solved 2/2); open problems: adoption (skipped in 5/12 runs), the wrong
  target (simple case instead of the issue's construct), long commands sent as text. sbE3 built for r128 (one-time hold-back
  of the first edit without an expectation, 'not the one in the issue' event + example, shorter check; PLAN RUN BUILT r128).
  r128: 4/8 (~4.6 expected). The one-time hold-back is obeyed (expectation on the next call 3/3); the examples' 'expectation
  second' order is not (first expectation 152-323 s). Tool results reach the model JSON-escaped, so old text with backslashes is
  copied doubled (40 of the bank's 58 'found 0'): fix it in the edit step, not the prompt.
  r129 built: sbE3b (+ backslash fallback) vs sbE4A (+ one-call search stage) vs sbE4B (+ text-call / failing-test examples).
  r129: 3/8, 2/8, 3/8. Long commands copied from fenced examples come out as unparseable text calls ending with the ``` fence
  (6/24 runs sunk; a resend rule does not help: the model repeats the same text). A SequentialAgent root + repeated text replies
  crashes ADK's end-of-run compaction (no model on the root). The expectation line so far 15/44 = sb1h family 9/26 on these tasks.
  r130: fence-free worked examples (each command ends with a '# end of command' comment line) -> 0 text calls in 16 runs, 0/5
  expectation attempts as text (was 50%). Adoption stayed ~half and never-edit runs stayed; 18/52 over r127-r130 = the base. PAUSED.
  sb1 (edit_file) = sb1hl in same-run pairs (0.54 vs 0.50, 26 cells); the main failure everywhere: exploring until the calls run out.
  r131: CLOSED. A guaranteed expectation from a writer that cannot read code is the wrong case (passes before any edit 4/4);
  19/56 over r127-r131. Text calls come from the model's OWN long code inside run_command (first call worst); our fixed commands
  never fail; a fence or an end-marker line can both be copied as a false ending. sb1hl 6/8 on fastapi_15589 + 11194 (r130-r131).
  r133 (user reopened it once more): sbE7 = sb1hl's exploring + expectation by write_file after reading: 3/8 vs sb1hl 4/8;
  'write_file only for expect.py' ignored (12 scratch-script writes); the check after write_file often skipped; both arms spend all 28
  calls. CLOSED (22/64). The real sb1hl weakness is the call cap + the harness 'Finalize your edits' note (WHY sb1hl RUNS OUT, r134).

- **History before the decision** - only with a delivery the model cannot skip AND early edits. The gate on the faster
  sb1hl (first edits earlier) with a later window is the one untested form. Useful history exists on ~40% of tasks
  (window check), but the model has not acted on it once, so the bar is high.
- **Information** - the biggest measured effect (6 -> 30 of 76). Any way to add the missing facts automatically (from the
  repo, the tests, the docs) is still the most promising family; the cheap evidence stage (evidc) fit the LB but did not
  add enough.
- **A test of the NEW behaviour** - r125 showed old tests cannot catch wrong fixes; a check that targets the issue's new
  behaviour (the reproduce heredoc kept as a file and re-run by the edit step) has not been tried.
- **Breaking hand-simulation loops** - by structure, not by thinking caps (closed). Nothing found yet besides sampling.
- **Best-of-N inside one run** - the sim showed +3-4 points from a perfect picker, but time and picking are unsolved.

## 6. How we work (process rules that came from mistakes)

- Bars and expected ranges are written BEFORE each run; same-run control always; solves at 8 v 8 are mostly luck, so small
  trials are judged on the mechanism, bigger runs on solves.
- Every new mechanism is checked offline first (on real fixes, the model's own past edits, throwaway repos, the sim).
- Analyses match commits by date + title, not hash (Kaggle's task repos have rewritten history).
- The session scratchpad can be wiped overnight: keep anything needed later in data/analysis or the repo.
- Never run repository code locally; Kaggle runs execute it inside the harness sandbox.
- No submission is backed only by tasks used to pick it: check on never-used tasks first; one scoring submission pending
  at a time.
