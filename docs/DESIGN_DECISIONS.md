# Design decisions — open and settled

Companion to `docs/PLAN.md`. Each open item: the question, the options, the evidence we have, a recommendation, and
what result would settle it. "Measure" means: change one thing, run it on the dev set (Kaggle 31B), compare with
`scripts/analyze.py`. Evidence labels: **verified** (harness/ADK source or our own runs), **forum** (other participants,
not checked by us), **12B** (Mac smoke test — behaviour only, not quality).

Last updated: 2026-10-07.

---

## Settled (for now)

| # | Decision | Why | Revisit when |
|---|----------|-----|--------------|
| S1 | Build two first agents: **1a** single agent, **1b** hybrid orchestrator (reader / executor / verifier helpers) and compare with Google's sample | Paper's first ablation; trade-off between short main context (1b) and hand-off/time cost (1a vs 1b) can only be measured | After the first Kaggle comparison |
| S2 | Thinking **off** (`include_thoughts: false`) | 09-27 run: thinking used most of the ~7k-token budget; no edits in 5 min (verified) | D9 |
| S3 | Sampling temperature 1.0, top_p 0.95, top_k 64 | Google's model card recommendation | D10 |
| S4 | `max_output_tokens: 2048` | prompt + max_output must fit 32,768; smaller cap = more room before overflow (verified) | If edits get cut off mid-reply |
| S5 | Declare the 3 graph tools on the root agent | An undeclared/hallucinated tool call ends the task and discards the patch (forum 745028); the task message advertises them | Host confirms the fix (D11) |
| S6 | No formatter agent; root agent uses unformatted helper replies as-is | Extra model call; cannot recover an empty reply | — |
| S7 | 1b delegates once `get_status.tool_calls_used ≥ 6` | Model cannot see its token count; get_status is free (verified) | D3 |
| S8 | Only the root agent calls `submit_patch` | Avoids a helper ending the task early | — |
| S9 | Budgets: 5 min/task, 240 s command timeout, 90 turns, 60 (1a) / 80 (1b) tool calls. **Leaderboard submissions: 4 min / 50 calls** (since 10-07) | ~120 tasks × ~5.3 min ≈ 10.6 h < 12 h hard limit; the first 1a submission (5 min) ended in "Kaggle Error" after ~13 h (likely the 12 h limit, unconfirmed) | D12, D17 |
| S10 | Shell commands use single quotes | 12B sent backslash-escaped quotes and re-ran failing greps (12B) | — |

---

## Open decisions

### D1. Context offloading to the filesystem — how far do we push it?
**Background (verified):** every `run_command` is a fresh `bash -c` in the task's container (cwd `/workspace`). Files
persist for the whole task (one container per task), survive ADK compaction (which keeps only *text* parts of the
history), and are shared by all agents of a task (1b's helpers run in the same container). Anything created in
`/workspace` ends up in the patch → scratch must live in `/tmp`. Tool output reaching the model is cut to the first
5,000 characters. Rejected alternative: elision of old tool output inside the history (needs ADK callbacks; the
harness registers none).

**Options (can combine):**
- **D1a — Notes file** (`/tmp/notes.md`): exact names/strings from the task, file:line facts, chosen interpretation.
  *Status:* already in both prompts. *Question:* does the 31B actually keep it? (the 12B wrote no text at all).
- **D1b — Save long output, show the tail:** `pytest … > /tmp/test.log 2>&1; tail -20 /tmp/test.log`, later
  `grep -n FAILED /tmp/test.log` instead of re-running. Fixes the "first 5,000 chars" problem (pytest's summary is at
  the end) and avoids re-running slow commands.
- **D1c — File hand-off between agents (1b):** reader writes `/tmp/findings.md` (LOCATION / EVIDENCE / FIX PLAN with
  verbatim lines), executor reads it; verifier writes `/tmp/verify.log`. The helper's final reply becomes
  "see /tmp/findings.md" + a 3-line summary. Reduces hand-off loss and protects against an empty final reply (the
  12B reader returned `{"raw": ""}` after 138 s — the file would still hold its work).
- **D1d — Command log to fight loops:** append every command tried and its one-line outcome to `/tmp/notes.md`;
  rule: "check notes before running a command".

**Cost / risk:** every write and read is a tool call (~5–25 s each on the 31B); reading a big file back puts it into
the prompt again → only read slices (`grep`, `tail`, `read_file` with line ranges).

**Recommendation:** add D1b to both prompts and D1c to 1b in the next prompt round; keep D1a; try D1d only if loops
persist on the 31B. **Settled by:** traces show notes/findings files written and read back, fewer repeated commands,
no lost helper work, without a big increase in calls per task.

**Measured 10-07 (rung-1 + rung-1b traces, 8 task runs per config) — what is actually needed again later:**

| Information | Fetched again later (1a) | Write it down? |
|---|---|---|
| Code already read (same lines re-read) | 17 of 54 reads, ~1,000 lines | **yes** — the main thing they come back for |
| Test results (same file re-run) | 7 of 14 runs | partly — re-running after an edit is correct; which tests failed *before* any change is worth one line |
| Failed approaches | rich_3470 (1b) tried one fix, test failed, tried another | **yes** — avoids repeating a dead end |
| Search hits (git grep) | 4 of 27 | no — rarely re-needed, cheap to redo |
| Git history | 1 of 2 | no |

1b: 140 of 186 reads re-read lines already seen (mostly the executor's 17-read loop); **13 are cross-agent** (a helper
re-reading what the orchestrator had already read). Notes in 1a: written 6×, **read back 0×** — they cost ~5 % of
output tokens and gave nothing.

**D1e — Tagged notes, written and read at fixed moments (user idea, 10-07; proposed, to verify in the next run):**
write only four kinds of line, nothing else (no search hits, no file dumps, no plans):
```
TASK: exact names / messages / values from the task, verbatim
LOC: path/file.py:34-37 function_name | the 2-4 key lines verbatim
BASE: tests/test_x.py: failing before any change: test_a, test_b (or none)
TRIED: what was tried -> why it failed
```
Read back with one command, at fixed moments: before editing → grep -e '^LOC' -e '^TASK' /tmp/notes.md; before
submitting → grep '^BASE' /tmp/notes.md; after a failed test → grep '^TRIED' /tmp/notes.md. In 1b the orchestrator
points helpers at those lines instead of re-typing code in requests.
**Expected gain:** small in time for 1a (a re-read is ~1.4 s + a few tokens; input tokens are nearly free, D15);
real gain in context (32k) and in 1b hand-offs.
**Settled by:** notes read back > 0; fewer re-reads of the same lines (especially cross-agent in 1b); no rise in
output tokens per task.

**D1f — 1b hand-off through files (measured 10-07; proposed, to verify in the next run):** what helpers report today:
- Executor: always names the changed source file (CHANGED line); mentions a /tmp script only if it appears in CHECK.
- Verifier: twice replied "VERDICT: PASS / EVIDENCE: python3 /tmp/x.py / FIX: none" — a command name, **no output**,
  although the prompt asks for up to 20 lines of real output; in rung-1 it overwrote the orchestrator's
  /tmp/repro.py (fixed in round 3, fix D).
- Reader: writes nothing; everything inline (240–2,900 chars); one empty reply lost all its work.
Changes: (a) reader appends its LOC lines to /tmp/notes.md as well as replying (work survives an empty reply);
(b) verifier saves full test output to /tmp/verify.log and replies VERDICT + last ~10 lines + "full log:
/tmp/verify.log" — the orchestrator can grep FAILED in it instead of trusting the verdict; (c) every helper's final
reply ends with a FILES: line listing every file it wrote (source and /tmp), so the pre-submit cleanup knows what
to check.
**Settled by:** verifier evidence contains real output; no work lost on empty replies; no stray files in patches.

### D2. Empty or unusable helper replies (1b)
**Evidence:** 12B reader worked 138 s and returned an empty final message; orchestrator re-asked and timed out (12B).
Forum: Gemma rarely writes text next to tool calls.
**Options:** (a) keep "re-ask once, narrower"; (b) never re-ask — continue alone; (c) hard tool cap in helper prompts
("after 6 tool calls, stop and write the final message"); (d) D1c file hand-off so work survives an empty reply.
**Recommendation:** (c) + (d), and switch the orchestrator rule to (b). **Settled by:** Kaggle 31B `format ok` column
and helper durations.

### D3. Delegation trigger for 1b
**Options:** keep `tool_calls_used ≥ 6`; lower (4) to protect context earlier; higher (8–10) to save hand-off time;
work-type rule ("big reads always go to the reader").
**Evidence so far:** 12B delegated at 4 calls (earlier than told). Calibration from 09-27: ~900 prompt tokens/step,
compaction at 14,336.
**Settled by:** peak prompt tokens and compaction counts of 1b vs 1a on the 31B.

### D4. Loop prevention
**Evidence:** 12B 1a repeated near-identical commands 22× in 5 min; forum reports up to 69× and more loops at
temperature 0.7 than 0.2 (forum, 10 tasks). The "never repeat a command" rule alone did not stop the 12B.
**Options:** D1d command log; stronger budget rule ("if 3 calls in a row taught you nothing new, change approach");
lower temperature (D10); in 1b, loops are bounded by helper tool caps.
**Settled by:** `repeat` column on the 31B.

### D5. "One progress line per reply" rule
**Why it exists:** text survives compaction, tool results do not (verified). **Evidence:** the 12B ignored it (every
step had an empty message). **Options:** keep, drop (saves tokens), or replace with D1a notes.
**Settled by:** whether the 31B writes the line and whether compaction-hit tasks recover.

### D6. Fix verification inside 1a
1a has no verifier; it relies on the prompt's "re-run repro + nearest tests". **Option:** give 1a the verifier as its
only helper (= ladder rung 2). **Settled by:** wrong-fix rate of 1a vs 1b.

### D6b. Merge executor and verifier (user idea, 2026-10-06)
**Question:** for simple tasks, do separate helpers waste time and lose context? Evidence that they can: Google
"Towards a Science of Scaling Agent Systems" (arXiv 2512.08296: sequential tasks −39–70 % under multi-agent variants;
coordination tax on tool-heavy tasks), MAST (arXiv 2503.13657: hand-off information loss), our 12B reader returning
nothing after 138 s. Counter-argument: a verifier needs the diff + tests (on disk), not the executor's memory; a
separate checker gives "fresh eyes" (self-checking tends to confirm: arXiv 2603.25764; review loops helped in
SWE-Review, arXiv 2607.06065).
**Options:** 1a already = merged (one agent edits and verifies); 1b = separated; candidate **1c** = orchestrator +
reader + one "fixer" that edits *and* runs the checks.
**Rung-1b evidence (10-06, 4 tasks):** the verifier caught one real regression (rich_3470, round 1: "test_capture_and_record
fails"), but its second reply was prose without a VERDICT and the orchestrator submitted a still-broken fix. Round 3 makes
the orchestrator run the baseline test file itself before submitting (fix E).
**SWE-Edit ([arXiv 2604.26102](https://arxiv.org/abs/2604.26102)):** the closest published design to 1b — main agent +
Viewer (returns only task-relevant code) + Editor (applies an edit from a plain-language plan); +2.1 % resolved,
−17.9 % cost on SWE-bench Verified. There is **no verifier helper**: the main agent runs the tests itself. Their savings
come from a cheaper helper model and fewer main-agent *input* tokens; neither applies to us (one model; input tokens
cost almost no time, D15), so for us the split is about context (32k) and edit reliability (edit success
93.4 → 96.1 %), not speed. Delegating edits made their main agent explore more (+10 % cost).
**Settled by:** round-3 run — if the verifier still adds time without catching wrong fixes that the orchestrator's own
test run would miss, build 1c (orchestrator runs tests; no verifier helper).
**Rung-1d evidence (10-07, 1b round 4, 12 task runs):** 9 verdicts: 8 PASS, 1 FAIL. 2 PASSes were on wrong fixes
(r1 fastapi_15588, r3 fastapi_15589); the one FAIL (r2 rich_3470) did not lead to a solve. The orchestrator's own
baseline re-run (fix E) already covers regressions.
**Decision (user, 10-08) — 1b round 5:** merged. The executor now makes the change *and* checks it (runs
/tmp/repro.py as-is or one short /tmp/check.py, the baseline test file with the already-failing tests named in the
request, git status), adjusts at most twice, and returns CHANGED / REPRO / TESTS / RESULT (PASS|FAIL); 14 tool calls
(was 10). The verifier helper is removed; the orchestrator keeps its independent pre-submit test run (step 4a) as the
"fresh eyes" check. 1a unchanged (control). **Measure:** solve rate, seconds per task and helper calls per task vs
rung-1d 1b (mean 2.0/4); watch for false PASS from self-checking.
**10-08 (user):** 1a parked; dev runs are 1b only (3 repeats) until further notice. 1a stays at 30a8c5b.
**Rung-1e result (round 5): mean 1.0/4 (was 2.0).** Main loss = the pre-existing Phase-A repro-rewrite loop
(fastapi_15589). But the merge prompts made the executor slow: requests 886 → 2,187 chars, inner tool calls median
2 → 12 (max 37, the 14-call rule ignored), 63 s per call vs 14 + 17 s for executor + verifier; it rewrote
/tmp/repro.py 8× and looped edit → check → edit (experiments/2026-10-08_rung1e). Separate roles had bounded the work.
**Round 5b (10-08, user):** prompt-only fix of the merge: executor checks once (repro as-is or one ≤15-line
check.py, one pytest run, one fix only for an obvious slip in its own edit), never writes /tmp/repro.py, ~6 calls,
reports and lets the orchestrator decide; orchestrator requests ≤ ~8 lines, no pasted repro. **Measure:** executor
s/call back near 30 s, inner calls ≈ 6, score vs round 4.
**Rung-1f result (round 5b): mean 1.33/4.** The fix worked (executor 30 s/call = executor + verifier in round 4;
~5 inner calls; no repro.py writes); the remaining losses are the pre-existing repro loop and reader runaway.
**Decision (user, 10-08) — round 6: back to separate executor + verifier** (round 4, commit 8a645b5) plus the 5b
lessons that fit it: helper requests at most ~8 lines, no pasted repro or long code; the verifier request lists
the baseline's already-failing tests, and the verifier treats exactly those as pre-existing. Hand-off/offloading
work (file record, repro loop guard; D1e/D1f) continues on this architecture.
**Round 6 also includes (user, 10-08) the hand-off/offloading changes (D1e + D1f, first build):** /tmp/notes.md
with only TASK / LOC / BASE / FILE / TRIED lines (appended with echo ... >> /tmp/notes.md && next command); FILE
line + progress line after every scratch file run (progress lines survive compaction, tool calls do not:
llm_event_summarizer.py keeps part.text only); grep FILE/TRIED before writing a new script; cat notes before
Phase B; /tmp/repro.py written at most twice, then TRIED + delegate ("the repro is wrong" wording removed); TRIED
after a FAIL verdict; helpers cat notes as their first call, the reader appends LOC lines, all helpers end with a
FILES line; requests point to the notes instead of repeating them. **Measure:** repro writes per task (was up to
22), notes read-backs (was 0), helper re-searches, s/task, score vs round 4 (2.0).
**Rung-1g result (round 6): mean 1.0/4.** The orchestrator writes **no text** (0/380 steps), so ADK compaction
(text parts only) leaves a near-empty summary: after each compaction it restarted Phase A and `cat >` wiped its
notes (21×). Repro cap and helper notes-reads were ignored (experiments/2026-10-08_rung1g).
**Round 6b (10-08, user): resume-safe notes.** Step 1 is one command, `test -s /tmp/notes.md && cat /tmp/notes.md
|| cat > /tmp/notes.md << 'EOF' ...` (tested in bash): existing notes are printed, never overwritten; if notes
exist the orchestrator is resuming → no Phase A again, continue from the last STEP line. New STEP lines (Phase A
done, each helper's result, fix round, ready to submit); only step 1 may create the file, everything else appends.
**Measure:** Phase A restarts after compaction (round 6: every compaction), notes overwrites (21 → 0), score.
**Rung-1h result (round 6b, 2 repeats): 1/4, 1/4.** Resume fix works: notes overwrites 21 → 1; after compaction
2× resume-check, 1× continue, 1× restart (was mostly restarts). STEP lines written (5). Remaining loss = identical
repetition *before* any compaction: repro.py rewritten identically 10× / 12× in a row, a reader running the same
git grep 57× → next: temperature back to 1.0 (D10).

### D6c. Fewer agents: merge orchestrator and reader (user, 2026-10-09)
**Why:** 4 agents for a 5-minute task; in rounds 4–6b the orchestrator already did reader work itself in Phase A
(29–59 % of all task time, and nearly all its loops), then asked the reader to search again with a blank memory;
request writing alone ≈ 8–10 % of time. The reader also ran away on rich_3470 (13–68 calls) and returned empty
replies. Same direction as the multi-agent overhead evidence in D6b (arXiv 2512.08296).
**Round 7 (= round 6c minus the reader):** the orchestrator investigates until it knows file:lines, the current
code and the exact change (plus conventions to match), then hands off at tool_calls_used 14 or 120 s elapsed at the
latest; executor and verifier unchanged; reader.md / reader.yaml removed. Temperature 1.0 (round 6c).
**Measure:** time to first edit, Phase A loops, score vs round 6c. Next candidates (user): thinking in helpers (D9b);
a 2-agent design (main agent edits itself + verifier) compared head-to-head with 1a (30a8c5b).

### D19. 1a round 3: the free fixes from 1b (user, 2026-10-09)
**Evidence (1a, 20 task runs before the wheelhouse update):** 7 solved, 6 wrong fixes (5 = unguessable
fastapi_15588), **7 no patch** (3 timeouts on fastapi_15589, 3 on rich_3470, 1 = the 81× broken edit_file loop).
Context: reading code = 67 % of tool output (read_file 53 %, search 14 %); time: writing repro/check scripts = 60 %
of output tokens, edits 24 % (scripts/context_split.py). Compaction 1–2× per task wipes memory (no text written).
**Changes (all proven in 1b):** resume-safe tagged notes (TASK/LOC/BASE/FILE/TRIED/STEP, step 1 never overwrites);
sed line reads instead of read_file; short old_string + no identical retry + Python edit fallback (1b: 0 broken
edit loops); repro at most twice and a passing repro is no reason to skip the change; baseline BASE line and
"adjust, never undo completely"; empty diff never submitted. Thinking setting: decided by the 1a vs 1a_think run.
**Compare:** `1a@30a8c5b` (reference, embedded from git by make_kaggle_notebook.py) vs `1a` round 3, same tasks.
**Rung-1m (round 3): 1/4, 1/4** vs 1a_think 1/4, 2/4. Edit errors 10/29 → 2/13; read_file halved; repro cap and
notes ignored (0 notes reads); the multi-line step-1 notes block was copied as **text** in 3/8 tasks (no tool call,
fastapi_15589 r2 lost). **Round 3b (user, 10-09):** notes system removed entirely (thoughts now survive compaction
as text); keeps sed reads, edit fix, repro cap, baseline, never-undo, no empty diff.
**Rung-1n (round 3b, log only, zip lost): run 1 = 1/4** (rich_3882); no text tool calls; edit fallback rescued
fastapi_15588's edits; timeouts on fastapi_15589 / rich_3470 dominated by 25–40 s thinking steps.
**Two failing tasks, all 31 runs (10-09):** both are 1-line gold fixes. Solves edited the right spot at 111–261 s;
failures = no edit (repro never shows the bug, agent keeps investigating) or a different location/guess. Since the
update 0/13 + 0/? : edits come at ≥ 230 s or never. **Round 3c (user):** generic time checkpoint — get_status after
reading the main code; at agent_elapsed_seconds ≥ 150 with no source edit, make the best edit now, then test and
adjust; no task-specific content. Test on fastapi_15589 + rich_3470 only, 3 repeats. Next candidate: thinking
budget 1,024 → 512. Note: the "\r and \n ... line breaks" example (round 2) was inspired by fastapi_15588.
**Rung-1o (round 3c):** checkpoint not followed (get_status 0 calls; edits at 220–299 s); fastapi_15589 2/3 (likely
chance), rich_3470 0/3 wrong fixes. Lesson: rules to apply later are ignored; config changes and error-triggered
instructions work. **Round 3d (user, 10-09): thinking_budget 1,024 → 512**, prompt unchanged; same 2 tasks × 3.
**Verifier plan (user, 10-09), after 3d:** add only a verifier (no writer). The time check must be triggered by an
event, not remembered: right after the first edit that passes the repro, call get_status; if
time_seconds_remaining ≥ ~90, call the verifier (3-line request: what must hold, test file, already-failing tests;
diff/repro on disk), otherwise run the repro and test file in place and submit.
**Then (D6/D6b):** one helper, most likely the verifier with a file-based hand-off (request ≈ 3 lines, diff/repro/
notes on disk, reply VERDICT + ≤ 10 lines); a strict viewer only if thinking makes context the bottleneck.

### D7. Planner (`{plan}` re-injected every turn) and replanner
Ladder rungs 3–4 (PLAN.md). Planner = SequentialAgent [planner (output_key=plan) → executor with `{plan}` in its
instruction]. Paper evidence: planning helps weaker models (+11.6 pts for a 30B at tight budgets). **When:** after
D1–D4 are settled on the current agents.

### D8. Skills (our only custom code)
Candidates: repo map of the source package (fixes the hidden-package listing, forum 745220), async-aware symbol
search (graphs miss async code), test finder (nearest tests for a file). **Risk:** model passes `file_path` as a list
→ crash ends the task (forum 745028). **When:** after the prompt round; one skill at a time.

### D9. Thinking on + budget
Since the Sep 30 wheelhouse, thoughts are kept between tool calls and `thinking_budget` is forwarded (forum,
host-confirmed). Thinking may now help instead of re-deriving the task every step, but kept thoughts fill the 32k
context faster.
**How thoughts persist (Gemma 4 `chat_template.jinja`, HF main; Kaggle's copy may differ):** a past thought is
rendered only if it comes after the last *user* message. Tool results are not user messages, so within one task all
thoughts stay in the prompt; a harness nudge is a new user message and drops all earlier thoughts.
**We cannot strip thoughts ourselves:** no callbacks to edit history; `include_thoughts: false` disables thinking
entirely (no "think but don't keep" mode, forum 745059 unanswered).
**Options:** (a) thinking everywhere with `thinking_budget` 512/1024; (b) **thinking only in helpers (1b)** — each
agent has its own generate_content_config, and a helper's whole session (thoughts included) is discarded when it
returns, so reasoning costs time but not orchestrator context; (c) off (current).
**Cost:** ~36 tok/s measured (D15) → a 1,000-token thought ≈ 28 s per step.
**Measure:** 1a off vs 1a budget 512; 1b with thinking only in reader/verifier vs all off.
**10-09: wheelhouse 0.2.13 (adk_submission, 2026-10-08) changed thought handling:** `include_thoughts: false` still
sends enable_thinking=false, but now also strips thought parts / reasoning_content from responses before they
reach the session. Rung-1i (1b, T 1.0) showed 3.4× hidden output tokens (none in any earlier run) → timeouts.
Suspected: the model reasons despite the flag and 0.2.13 hides it (unverified). The notebook now prints installed
versions and runs a direct-call diagnostic (thinking off, T 0.2 / 1.0, reasoning vs content length). If the model
does think anyway: try `thinking_budget: 0` (checked before include_thoughts in 0.2.13), or thinking on with a
small budget since we pay for it regardless.
**Rung-1j (10-09):** short diagnostic prompt → no reasoning at all; real runs at T 1.0 → hidden reasoning in all
agents (2.7–5.0×) and replies with `<|channel>thought<channel|>` + the tool call written as text (no call parsed →
nudges). **Next run:** replay the real first orchestrator request (full 1b prompt + harness task message, built at
runtime from tasks.jsonl) under T1.0/p.95/k64, T1.0/p.80/k20, T0.6, T0.4, T0.2 (3 samples × 2 tasks, thinking off),
reporting reasoning, marker leaks and proper tool calls. The eval in the same session runs round 7 at T 0.2.
**Rung-1k result:** direct calls never think (0/30); hidden tokens in agent runs date exactly to the wheelhouse update
(before 1.0×, after 2.8–3.4× at any temperature). Forum 746250: thinking off 17.8 % vs on 37–40 % (129 tasks).
**10-09 (user): focus moves to 1a; 1b parked.** First 1a comparison, one notebook, 4 tasks × 2 repeats:
`1a` (reference 30a8c5b, thinking off) vs `1a_think` (identical except `include_thoughts: true`,
`thinking_budget: 1024`). **Measure:** solve rate, seconds per task, timeouts, thinking tokens per step.
**Rung-1l result:** 1a 1/4, 0/4 vs 1a_think 1/4, 2/4. With "thinking off" 1a still reasoned invisibly (2.5–3.2×
hidden, ~260 output tokens/step), the same cost as thinking on (1.0×, thoughts kept). **Decision: thinking on
(budget 1,024) for 1a from now on.** Since the update every step costs ~2× the tokens of before (≈ 130 → 260),
so only about half as many steps fit in 5 minutes.

### D10. Temperature 1.0 vs 0.2
Google recommends 1.0; one forum test saw more loops at 0.7 than 0.2. **Measure** after the first comparison.
**10-07:** identical 1a prompts scored 3/4 (rung-1b) then 1/4 (rung-1c) at 1.0 → run-to-run noise swamps config
differences on 4 tasks. Dev runs switched to **0.2** together with prompt fixes A–C (rung-1d), each config run 3×
on the same 4 tasks. Confounded with the prompt fixes by design (user decision); the repeats show whether results
become stable. The leaderboard submission still uses 1.0.
**10-07 (later):** rung-1d 1a_r1 scored 0/4 → user decision: **1a and 1b are changed separately, never in the same
round.** 1a reverted to its 3/4 version (commit 30a8c5b: round-2 prompt, temperature 1.0); fixes A–C and 0.2 stay
on 1b only. A 1a change is tested on its own later.
**10-09 (user): 1b back to 1.0** (round 6c = round 6b + temperature only). At 0.2 the longest identical back-to-back
command streak per task grew 13 → 15 → 34 → 43 → 57 over rungs 1d–1h (repro.py rewritten word for word, a reader
running the same git grep 57×), while 1b at 1.0 (rungs 1b/1c, 8 task runs) never exceeded 2. Low temperature is a
known cause of repetition (Holtzman et al., ICLR 2020). **Measure:** streak lengths, repro writes, score, and the
spread between repeats.

### D11. Graph tools
Declared only as crash insurance (S5); `search_similar_code` returned 0 results in 140/142 calls (forum) and was useless
on 09-27 (verified). **Decide:** remove once the host confirms unknown tool calls no longer end the task.

### D12. Per-task time budget
5 min was set by the 12 h total. **10-07:** the first leaderboard submission (1a, 5 min / 60 calls) ran ~13 h and ended
in "Kaggle Error" (no logs; likely the 12 h limit — the host said overruns error the whole submission, forum 743063).
Resubmitted with 4 min / 50 calls (worst case 8 h agent time + setup). On our dev tasks 1a needed 64–171 s, so the
hidden tasks are probably harder/longer. Never go above 5 min again until the host confirms unfinished tasks score 0.
**Settled by:** whether the 4-min submission scores; time-to-first-edit and timeout rate; D17.
**10-09: both errors were platform failures (forum 743683/746480) and Kaggle rescored them:** 56888287 (1a round 2,
5 min / 60 calls) **0.08**; 56907342 (same prompt, 4 min / 50 calls) **0.10** — middle of the leaderboard. So the
4-min limit costs nothing visible (difference is within noise). Dev-set 1a ≈ 25–75 % vs 10 % hidden: our 4 dev
tasks are easier than the hidden set (D13).

### D13. Dev set size
Currently 4 gold-checked tasks (1 task = 25 %, directional only). **Plan:** grow to ~20 gold-checked tasks across
fastapi / rich / requests before trusting differences (~2 h Kaggle wall = ~4 h quota per config).

### D15. Time — how to let the agent finish faster
**Where time goes (measured 10-07, 424 model calls of 1a + sample, both 10-06 Kaggle runs; per-call timestamps in the
traces):** one turn (model reply + its tool run) ≈ **1.4 s fixed + 28 ms per output token (≈ 36 tok/s)**; prompt size
has no measurable effect (prefill is fast). Median turn: 2.0 s / 39 output tokens (1a), 2.7 s / 66 tokens (sample,
thinking on). So **output tokens dominate**; the turn count matters much less (~1.4 s each); input size matters for the
32k limit, not for time — consistent with
[Token Reduction Is Not Cost Reduction (arXiv 2607.12161)](https://arxiv.org/html/2607.12161v5).

**Levers we control (research):**
1. *Write less per step.* [The Danger of Overthinking (arXiv 2502.08235)](https://arxiv.org/pdf/2502.08235): more
   internal reasoning instead of acting → worse SWE-bench Verified results; choosing less-overthinking runs gave
   ~+30 % performance at −43 % compute. [TACT (arXiv 2605.05980)](https://arxiv.org/html/2605.05980): reducing
   overthinking/overacting cut steps-to-resolve by up to 26 %. → thinking off or budgeted (D9), short replies.
2. *Fewer turns via turn limits + reminders.* [More with Less (arXiv 2510.16786)](https://arxiv.org/html/2510.16786):
   limit at the 75th percentile of baseline turns + "X turns left" reminder → −24 % to −68 % cost with negligible
   solve-rate loss; dynamic budget (start small, one extension) → further −12 % to −24 %. We cannot inject reminders
   (harness owns the loop), but get_status is free and the prompt can set step targets from our measured distribution.
3. *Several tool calls in one reply.* [LLMCompiler (arXiv 2312.04511)](https://arxiv.org/pdf/2312.04511): parallel
   function calls → 2.89× lower latency. ADK runs multiple calls from one reply, concurrently only for async tools
   ([ADK tool performance](https://google.github.io/adk-docs/tools-custom/performance/)); swegemma tools are sync
   (verified) → they run sequentially, but one model turn replaces several.
4. *Fewer exploration steps.* [Agentless (arXiv 2407.01489)](https://huggingface.co/papers/2407.01489): fixed
   localize → repair → validate pipeline, 32 % SWE-bench Lite at low cost. [SWE-Pruner (arXiv 2601.16746)](https://arxiv.org/html/2601.16746v3):
   focused context → up to 26 % fewer rounds. → repo-map skill (D8), git grep over browsing.
5. *Cheaper edits.* [SWE-Edit (arXiv 2604.26102)](https://arxiv.org/html/2604.26102v1): better edit mechanics → −17.9 %
   cost and +2.1 % resolve rate. → small edit_file calls with minimal old_string.
6. *Concurrent model work (untested idea).* Decode is memory-bound, so 2–4 concurrent requests cost ~the same time per
   token as one ([vLLM optimization](https://docs.vllm.ai/en/stable/configuration/optimization/),
   [continuous batching](https://www.zeroentropy.dev/concepts/continuous-batching/)). ADK ParallelAgent could run e.g.
   two readers at once. Risks: shared sandbox, unknown harness handling of a parallel tree → test locally first.

**Levers we do not control:**
- Speculative decoding with Gemma 4's MTP drafter: ~3× faster decode for the 31B (42.6 → 135.9 tok/s on H100,
  [Google blog](https://blog.google/innovation-and-ai/technology/developers-tools/multi-token-prediction-gemma-4/),
  [vLLM PR #41745](https://github.com/vllm-project/vllm/pull/41745)). Scorer runs `speculative_config=None` (09-27 vLLM
  log) — only a feature request to the hosts could change it.
- History trimming between steps ([AgentDiet, arXiv 2509.23586](https://arxiv.org/html/2509.23586v2): −40–60 % input
  tokens) needs callbacks — not available.
- Tasks run sequentially on the scorer.

**Proposed order (not done yet):** (1) keep thinking off/budgeted + one line + one tool call per step;
(2) cheaper scratch scripts and notes (D16) — the biggest measured cost; (3) turn control (D17); (4) repo-map skill;
(5) later, test ParallelAgent locally.
**Where 1a's output tokens go (rung-1b, 4 tasks, 13.7k tokens):** repro/check scripts written with heredocs **53 %**
(23 turns, ≈ 200 s ≈ 50 s/task, ~40 % of task time; usually the whole script rewritten to change one line); replies
without a tool call 19 % (incl. one 2,048-token reply cut off while writing notes → broken call → nudge, rich_3470);
edit_file 8 %; read_file 7 %; notes 5 %; test runs 5 %.
**Paper details (10-07 reading):**
- *More with Less:* the reminder was injected after every tool result ("ENVIRONMENT REMINDER: You have X turns left").
  The 75th-percentile limit raised Gemini 2.5 Pro's solve rate (+3 %) at −68 % cost; tight limits (25th pct) made it
  collapse ("threshold effect") and raised the number of empty patches. Cites TALE "token elasticity": too
  aggressive a per-reply token budget makes replies *longer*. → D17.
- *Overthinking:* three failure patterns — analysis paralysis, **rogue actions** (several dependent actions in one
  turn without waiting for results), premature disengagement. Rogue actions = the 1b collision on rich_3470 (verifier
  + run_command in one reply, both writing /tmp/repro.py) → round-3 fix C. Its +30 % / −43 % result came from running
  each task twice and picking the less-overthinking run — not possible here (one sandbox, one patch).
- *LLMCompiler:* parallel independent calls (up to 3.7× faster). **Low value for us:** a turn's fixed cost is only
  ~1.4 s, swegemma tools run sequentially, and multiple calls per reply invite rogue actions. Batching independent
  lookups into one shell command (git grep A; git grep B) already gives the benefit. Not pursued.
- *SWE-Edit:* see D6b and D18.
**Settled by:** time-to-first-edit, turns per task, output tokens per task, timeout rate (analyze.py).

### D16. Cheaper scratch scripts and notes (from D15 measurement)
**Evidence (verified):** repro/check scripts are 53 % of 1a's output tokens (≈ 50 s/task); a notes heredoc hit the
2,048-token reply cap once and became a broken call.
**Proposal (prompt rules, 1a and 1b):** repro script at most ~15 lines, written once and re-run; small checks with
python -c; to change a script, write a second small one instead of rewriting the whole file; notes at most ~10 lines
per write (append with cat >> /tmp/notes.md).
**Risk:** too-strict length rules can backfire ("token elasticity", D15) — phrase as guidance, not hard counts.
**Settled by:** heredoc share of output tokens and seconds per task drop without a lower solve rate.

**Search and read in one command (user ideas, 10-07; proposed, to verify in the next run):**
- *Combine independent searches:* git grep -n -e 'record' -e 'capture' -- '*.py' | head -30. Measured: only 4 runs of
  2+ consecutive searches (11 turns) in 8 task runs → saves ~7 turns ≈ 10–15 s in total. Small but free. Safe: one
  shell command runs in order and the model sees all output (not the "rogue actions" of D15, which are several
  dependent tool calls in one reply). Output must still end with | head.
- *Search and show the code in one step:* a search was followed directly by read_file **14 times** (14 extra turns,
  and read_file line ranges are what trigger the start_line" bug). Instead: git grep -n -W 'def name' -- '*.py' |
  head -60 (-W prints the whole enclosing function; tested 10-07), git grep -n -A 15 'class Foo' (match + next 15
  lines), git grep -n -e 'record' --and -e 'def ' (lines with both words). 0 of 28 searches used such flags.
  Risk: -W on a class prints the whole class → always | head -60.
**Settled by:** fewer search→read pairs and turns per task; no rise in context overflows.

### D17. Turn control (More with Less, arXiv 2510.16786)
**Paper:** limit at the 75th percentile of normal turn counts + a turns-left reminder: −24 to −68 % cost, solve rate
about the same; "start small, extend once" saved another 12–24 %; tight limits caused collapses and empty patches.
**What we can do:** we cannot inject reminders (the harness owns the loop), but: (a) prompt checkpoint — "no edit by
call N → make your best edit now" (the "start small" stage); (b) "call get_status every ~8 calls" as a self-reminder;
(c) set max_tool_calls near our measured 75th percentile — the harness keeps the unsubmitted diff when the limit
is hit (verified), and it also bounds the 12 h total (D12).
**Needs:** turn counts from a larger dev set (D13); 4 tasks give 14–33 calls for 1a.
**Settled by:** solve rate and seconds per task at the new limit vs the current one.

### D18. Lighter reader in 1b ("viewer", from SWE-Edit)
SWE-Edit's Viewer is a focused lookup — the main agent called it ~7.5×/task and it returned ~40 % of the requested
file. Our reader runs up to 8 turns per call and has no compaction (helpers never compact, verified in
agent_tool.py). **Option:** reader limited to 1–2 calls (git grep + one sed range), returning the snippet with line
numbers; the orchestrator asks it more often with narrower questions.
**Settled by:** reader time per call and format-ok rate vs the current reader; no change in solve rate.

### D14. LoRA
Blocked: scorer loads adapters with zeroed weights (forum 743508); LoRA also shrinks KV cache. Training-data route
when unblocked: self-distillation from our own verified-pass 31B trajectories, or open-weight teachers
(Qwen3.6-27B, Apache 2.0). No Claude/GPT-generated training data.
