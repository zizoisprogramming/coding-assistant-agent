# Gemma 4 Developer Agent — Competition Plan (living doc)

## >>> START HERE (session handoff, updated 2026-10-26) <<<
**User:** beginner to agents/ADK (ML engineer background); wants step-by-step plain explanations, research-backed
claims (verify, cite), chat before building, decides when planning ends. Rules: several changes per run are fine
(since 10-25) but bundle them into arms;
prompts generic (no dev-task content); competition data never committed (data/ is gitignored, incl. adapters built
from sample data); Kaggle token only in ~/.kaggle/access_token. Give Kaggle cells as FILE LINKS, never pasted; never
change cell 4's printed output. **No training data from Claude, GPT or Gemini (user decision, D14).** Each Kaggle
account runs its OWN notebook copy (a shared notebook made `kaggle kernels output` return only the latest version
and coincided with tasks running serially). L4x4 burns GPU quota at ~2x; weekly quota is tight → small runs.

### CHECKPOINT 2026-10-26 late night (NEWEST — read first)
- **Running now:** sk_a5 vs sk_a5r on dev16 (kaggle/cells_skill_a5, kernel ziadsamer/fork-of-generation-all-shards-gpu,
  saved version, ends by itself; per-arm early stop). The same kernel slug held sk_a3 and sk_a4/p1/a2_t05 before:
  only the LATEST version's output is downloadable (sk_a3's request log is lost).
  Partial (17/64, user paste): 3 solved; failed edits 0 in all 7 shown runs; replace used 1-2x/run (14419 a5r used
  edit_file 5x, replace 0); first edits 10, 16, 18, 25, 29, 29, 30 (3 refused after call 28); rich_3934 a5 used
  `run` 5x (4 before the edit); rich_3521 a5 27.6 s per model call.
- **When it finishes:** `uvx --from kaggle kaggle kernels output ziadsamer/fork-of-generation-all-shards-gpu -p
  data/results/2026-10-27_skill_a5 --file-pattern 'results/(gen_per_task|digest|phases)|\.log$|results/gen/patches/'`
  (+ 'requests\.jsonl$' if needed); answer the 5 questions in AGREED NEXT STEPS (digest first), update
  data/results/dev16_reference.md (add r6 columns in data/results/make_dev16_reference.py), then BUILD THE NAVIGATOR ARM.
- **LB:** sk_a2 submitted (dist/submission.zip); score not reported yet. mix = 0.17.
- **Rules added this session:** runs end by themselves (memory runs-must-end-by-themselves; STOP_NEW_TASKS_AFTER_H
  in cell 2 line 12 = quota h / 2 - 0.4); new arm prompts are full rewrites (memory prompts-are-full-rewrites);
  test set = 7 solvable tasks x 2 repeats (14 runs/arm).
- **Where things are:** arms scripts/make_skill_arms.py (sk_a..sk_a5r, VARIANTS for sk_a2_t05; old arms keep their own
  a.py copies -> regenerate only new arms: `python3 scripts/make_skill_arms.py ARM`); tool scripts/agent_skill/a.py
  (options in commands.txt: banner reshow brake plangate debugflag; commands find outline show note pin impact check
  plan replace run); notebooks scripts/train/make_skill_arms_cells.py (`uv run python ...`, needs pyarrow) ->
  kaggle/cells_skill_*; sim data/sim/armsim.py (SIM_CELLS, SIM_EARLY, SIM_MANY_SHOWS); results data/results/2026-10-2*;
  local reference table data/results/dev16_reference.md.

### NEXT RUN BUILT: sk_nav_s6_32i alone, all 16, 1 pass (2026-10-28, NEWEST — read first)
- Why: s6_32 lost fastapi_15589 (mix 6/6) and fastapi_14419 by forgetting the install ("I forgot to run the skill
  script first", calls 19 / 21): ~20 calls without MEMORY / banners / DECIDE, whole-file read_file, 7 probes in
  15589. Install at call 2-3 in 12/16 runs, 19-21 in 3, never in 1.
- sk_nav_s6_32i = sk_nav_s6_32 file for file + sk_nav2's install-first wording (contract thought out before any tool;
  route step 1 = install, "always tool call 1", never python3 -m run_skill_script or a.py before it; Avoid: Starting).
  scripts/make_skill_arms.py INSTALL_FIRST. Notebook kaggle/cells_skill_s6i (only cell2 differs). Simulated: OK.
- Read: call 1 wrong (s6_32 16/16 -> ~0?), solved vs 6/16, mean agent s (s6_32 344).

### sk_nav_s6 / sk_nav_s6_32 RESULT: 6/16 (2026-10-28, NEWEST — read first)
- sk_nav_s6_32 (prompt says 28 calls / 6 min; config 32 calls / 8 min) 6/16 = best 16-task pass ever (mix 3.67, best
  before 4): 11194, 3882, 3521, 3470, 4079 + rich_3180 (tier 3: never solved before, ~150 runs; real fix in
  rich/cells.py chop_cells). Mean agent 344 s (= sk_a2 343), 1 time end. sk_nav_s6 (config 28) 3/16, 370 s, 5 time ends.
- The hidden cushion paid directly: rich_4079 (first edit call 29) and rich_3470 (31) solved; under 28 they are refused.
- Call 1 wrong 16/16 (sk_nav prompt); s6_32 installed the tool at call 2-3 mostly, 3 runs at 19-21, 1 never; 95 raw
  reads. fastapi_15589 (tier 1) lost: tool at call 19, read_file + repro scripts, no source edit.
- One pass: the 28-config twin got 3, so part of the gap is noise. Outputs: data/results/2026-10-28_skill_s6/.
- LB candidate: sk_nav_s6_32 (344 s/task like sk_a2; whether that fits the 12 h = sk_a2's LB outcome).
- PACKED: dist/submission.zip = dist/sk_nav_s6_32.zip (pack.py OK; byte-identical to the files that ran in
  cells_skill_s6). sk_a2 stays in dist/sk_a2.zip. User submits after the daily slot resets.
- Kaggle allows only ONE pending submission per team (refused 2026-10-27: "already has 1 pending submissions").
  sk_a2 (submitted 10-26 09:16 UTC) was still PENDING at 10-27 08:09 UTC (~23 h): sk_nav_s6_32 waits for it.

### NEXT RUN BUILT: sk_nav_s6 vs sk_nav_s6_32, all 16, 1 pass (2026-10-28, NEWEST — read first)
- Why: the model does not count its calls (get_status 3x in ~450 replies; the budget appears in its reasoning only
  after "Tool call budget exhausted"); with a 32-call prompt late tasks edited later (3470 28/29 -> 35, 4079 29 -> 32).
- User: state a smaller budget than the real one. Both arms = sk_nav file for file; prompt + a.py banner say
  "28 tool calls and 6 minutes" ("of the 6 minutes used"); real config: sk_nav_s6 28 calls / 8 min, sk_nav_s6_32
  32 calls / 8 min (4 calls + 2 min of cushion). scripts/make_skill_arms.py CALL_VARIANTS.
- Notebook kaggle/cells_skill_s6 (only cell2 differs from cells_skill_nav32): 32 runs. Simulated locally: OK.
- Read: solved vs mix 3.67 and sk_nav_32 4/16; first edits > 28 (the cushion used?); mean agent s (sk_nav_32 387).

### sk_nav_32 on ALL 16 RESULT (2026-10-28, NEWEST — read first)
- 4/16 (mix 3.67, sk_a2 3.5): 11194, 15589, 3882 + rich_4079; missed 14419, 3470, 3521; 0 of the 9 never-solved.
  5 no patch, 5 time ends, call 1 wrong 12/16 (sk_nav's prompt; fixed in sk_nav2). Outputs: data/results/2026-10-28_skill_nav32/.
- Mean agent 387 s/task: over le5's 347 s (Notebook Timeout on the 12-h scorer); mix's dev runs 286-382 and PLAN's rule
  "keep mean well under ~330 s or cap time". NOT submittable as is.
- The sk_nav PROMPT (user: sk_nav2 / sk_nav2_32 have another prompt and do not count): 5, 3 (28 calls, 7 tasks) + 4
  (32 calls, 16 tasks) = 12 in 3 passes = 4.0 per pass, the best of any prompt with 2+ passes (mix 3.67, sk_a2 3.5);
  still within dev noise (+-1-2 per pass).
- Time at 28 calls: sk_nav 354 s on the 7 winnable tasks; sk_a2's other 9 tasks run faster than its 7 (327 vs 364 s,
  all 343 s), so sk_nav at 28 calls on all 16 is estimated ~335 s (sk_a2 343 s, already submitted). The 32-call
  version (387 s) is not submittable.
- Candidate to submit: sk_nav at 28 calls; whether ~340 s fits the scorer's 12 h is answered by sk_a2's LB run.

### sk_nav2 RESULT + NEXT RUN BUILT: sk_nav_32 (2026-10-27, NEWEST — read first)
- sk_nav2 2/7, sk_nav2_32 3/7 (pass 1; early stop). Call 1 wrong 0/14 (sk_nav 8/14): the install fix worked, the
  score did not follow. First edit median 17 (28 calls) / 22 (32 calls). sk_nav2_32 mean agent 355 s = sk_nav 354 s
  (no 12-h scorer risk from 32 calls). Outputs: data/results/2026-10-27_skill_nav2/.
- Noise reminder: sk_nav itself went 5 then 3; one 7-task pass moves +-1-2 by chance.
- Next (user): sk_nav_32 = sk_nav file for file (its prompt with the Avoid section, its a.py) with max_tool_calls 32
  (eval_config.yaml + the 3 budget numbers in the prompt). Notebook kaggle/cells_skill_nav32 (only cell2 differs from
  cells_skill_nav2): ALL 16 dev16 tasks, 1 pass (user: "the full 16 for 1 pass"; mix 3.67 per 16-task pass; generator
  constants TASKS / PASSES, WINNABLE7 kept). Simulated locally: OK.

### NEXT RUN BUILT: sk_nav2 vs sk_nav2_32 on the 7 winnable tasks x 2 (2026-10-27, NEWEST — read first)
- sk_nav2: sk_nav's prompt rewritten so install is step 1 of the route ("always tool call 1", never a.py or
  python3 -m run_skill_script before it), the contract is thought out before any tool call, and Avoid starts with
  "any first call other than run_skill_script". Same a.py (navigate), same replace.
- sk_nav2_32: identical, with max_tool_calls 32 (eval_config.yaml and the prompt's numbers); time stays 8 min
  (user 2026-10-27). Scorer risk to watch: mean agent seconds per run (mix 346 s ran 116 tasks in the 12 h).
- Notebook kaggle/cells_skill_nav2: arms may now differ in max_tool_calls (per-arm EVAL_CFGS); DIGEST reads WHERE
  from the reasoning too. 28 runs; early stop after pass 1 per arm at <= 3 of 7. Simulated locally: OK.

### sk_nav RESULT (2026-10-27, NEWEST — read first)
Run ended by itself after 2 passes (0.9 h). Outputs + request log: data/results/2026-10-27_skill_nav/.
- Score on the 7 winnable tasks: pass 1 5/7 (first 5 ever), pass 2 3/7 -> 8/14 = 4.0 per pass (mix 3.67, sk_a2 3.5,
  sk_a5 3). Per task: 11194 SS, 3882 SS, 14419 S0, 15589 SE, 3470 S0, 3521 0S, 4079 00.
- Failed edits 0 (replace). Median first edit still 20 (sk_a5 19-21; target 14): the hints did not move timing.
- DECIDE is read through: calls from the first DECIDE to the first edit = 2, 6, 7, 8, 9, 10, 12, 12, 18, 19, 23, 24.
  PING-PONG too (14419.2 got it 4 times in a row and kept finding). Same lesson as banners: warnings are ignored.
- WHERE / WHY / CHANGE was written in 11/14 runs, in the model's reasoning (digest counted only content -> 0: bug).
- Call 1 wrong in 8/14 (all fastapi tasks + rich_4079, both passes; sk_a2 had 0): searched first, or
  `python3 -m run_skill_script`; install came at call 2-3. Likely cause: the route starts with "1. Search" and the
  contract section is titled "Before call 2".
- 3 runs lost by ONE call: 14419.2, 3470.2, 4079.2 edited at call 29 (refused, no patch); 2 of them had wasted call 1.
  rich_3470.1 solved with its first edit at call 28.
- Next candidate: sk_nav2 = sk_nav with install as step 1 of the route (the call-1 fix) + digest WHERE fix.

### NEXT RUN BUILT: sk_nav, the navigator, alone on the 7 winnable tasks x 2 (2026-10-27, NEWEST — read first)
- Arm submissions/sk_nav (scripts/make_skill_arms.py sk_nav): own prompt, written fresh (1263 words), built on the
  winners' route: contract -> find 1-3 -> outline -> 1-2 whole functions -> at most 2 one-call probes
  (timeout 30 python3 - << EOF) -> WHERE / WHY / CHANGE lines in the reply that edits -> one test -> submit.
  Tells the model the evidence (passing runs edited at ~14, failing at ~27, same file) and names the two losing
  routes (ping-pong, script spiral). Edits with a.py replace; no `run`; no blocks, no bans.
- a.py option `navigate` (only while there is no change): a whole-function show (show FILE NAME, or a range covering
  a whole function) ends with CALLED FROM (up to 4 non-test callers) + DECIDE (edit these lines, or show the one
  caller that feeds them); 4+ finds / line peeks in a row without a whole function print PING-PONG. Plus banner +
  reshow as sk_a2. No probe counter (a.py cannot see run_command probes; the prompt says 2 at most).
- Notebook kaggle/cells_skill_nav (scripts/train/make_skill_arms_cells.py): tasks rich_3882, fastapi_15589,
  fastapi_11194, rich_4079, rich_3521, fastapi_14419, rich_3470; 2 passes; mix reference 3.67 per pass on these 7.
  Ends by itself after pass 1 if sk_nav solves 3 or fewer of 7. DIGEST adds: callers shown, ping-pong, WHERE at call.
- Simulated locally (SIM_CELLS=cells_skill_nav data/sim/armsim.py): runs end to end, CALLED FROM / PING-PONG / WHERE
  reach the digest, early stop ends the run (resolved=False and `timeout: not found` are Mac/uv artefacts).
- Read the result by: solved per pass vs 3.67 (>= 5 of 7 is a real gain); median first edit (target ~14, sk_a5 19-21);
  edits refused after call 28 (sk_a5: 7/32); does DECIDE lead to an edit within 1-2 calls (request log).

### sk_a5 / sk_a5r RESULT (2026-10-27, NEWEST — read first)
Run ended by itself after pass 1 (early stop, 1.6 h). Outputs + request log: data/results/2026-10-27_skill_a5/.
- Score: sk_a5 (replace+run) 3/16, sk_a5r (replace only) 3/16; mix 3.67. Same as sk_a2's level; nothing new on tier 3.
  Solves: rich_3882 both, fastapi_11194 both, fastapi_15589 a5, rich_3521 a5r.
- Q1 failed edits: 1 in 32 runs (sk_a2-era arms: ~22% of edit calls failed). `replace` fixed edit mechanics.
- Q2 replace 50 uses vs edit_file 20 (a5r used edit_file 14x, e.g. 14419 a5r 5x edit_file). Both work.
- Q3 median first edit: a5 19, a5r 21 (sk_a2 17, winners 14). Earlier edits did NOT happen; timing is the bottleneck.
- Q4 `run`: 33 uses in a5, scripts before the edit 1.6/run in both arms -> no extra spiral, but no gain.
  a5 had 5 time-outs vs 1 (driven by slow model calls, 14-28 s/call on those runs, not by run's tool time 15 s).
- Q5 first edit at call >= 29 (refused, no patch): a5 2 runs, a5r 5 runs = 7/32 runs lost to late editing.
- Conclusion for the navigator: keep `replace` (free win on mechanics), drop `run` (no evidence it helps; fewer
  commands = simpler prompt). The thing to move is the first-edit call (19-21 -> ~14).

### AGREED NEXT STEPS (2026-10-26 night, NEWEST — read first)
- **sk_a5 / sk_a5r running** (kaggle/cells_skill_a5). When done, read the DIGEST averages first (cell 5), then score:
  1. failed edits per run (sk_a2: ~1 in 5 edit_file calls failed) -> replace becomes the base if they drop;
  2. replace vs edit_file use; 3. median first edit (sk_a2: 17; winners: 14); 4. sk_a5 vs sk_a5r scripts before the
  edit + edit timing -> keep `run` only if it does not feed script spirals; 5. edits after call 28 (sk_a2: 4/32);
  score: only >= 5 or <= 2 per pass means anything; watch 3882 / 15589 / 11194 (tier 1).
- **Task tiers (all runs):** tier 1 = 3882 95%, 15589 60%, 11194 55%; tier 2 = 4079 35%, 3521 31%, 14419 15%,
  3470 14%; tier 3 = the other 9 at 0 in ~150 runs (model limit). Ceiling 7, now ~3 per pass.
- **Winners' recipe** (action strings): 1-3 find -> outline -> show 1-2 WHOLE functions -> at most 1-2 probes -> edit ->
  test -> submit. Losers: find / line-peek ping-pong (fsfsfs) or script spirals (xrxrxr).
- **Next arm to build after sk_a5: "navigator"** = sk_a2 + whichever of replace / run passed + situational hints in
  a.py output: whole-function show adds its top callers + "decide: edit it, or show the caller that feeds it";
  ping-pong detector (~4 find/line-peeks without a whole-function show); probe counter (2 probes -> decide); prompt asks
  for WHERE / WHY / CHANGE before the first edit. No blocks, no bans.
  **Its prompt is written fresh as one full text (user: no gluing / find-and-replace of older prompts).**
- **Test set from now on: the 7 tier-1/2 tasks x 2 repeats (14 runs per arm, ~1.5 h quota)**; a full-16 check of time
  per task only before an LB submission.

### WHY DO SOME ARMS SOLVE WHAT OTHERS DON'T? (2026-10-26 night, NEWEST — read first)
- 60 logged runs (sk_a/sk_ad, sk_a2/sk_ad2, sk_a4/sk_p1/sk_a2_t05) on the 6 winnable tasks (11194, 15589, 4079, 3470,
  14419, 3521); sk_a3's and the first run's request logs are gone (same kernel slug overwritten / cancelled).
- **Every arm starts the same way and finds the same file:** the first search is identical per task across arms
  (e.g. find "convert_underscores", find "File" fastapi/params.py, find "cache" fastapi/dependencies) and solved and
  failed runs edit the same file (except 4079: markdown.py vs table.py/pretty.py).
- **The difference is timing:** solved runs (17) edit at call 14 (median; 11/17 by call 16), with 10 reads and 2
  scripts before; failed runs (43) edit at call 27 (4/43 by call 16) or never (11), with 19 reads and 3 scripts.
  Same place, same first step; the winners commit early and keep budget to test and repair.
- So "unique" solves (3521 by 5 arms, 11194 by many, 14419 only by sk_a3, 3470 only by the first sk_a) are mostly
  which runs happened to commit early, not a feature one arm had. Combining arms will not combine their solves.
  Exception: 4079 needs the right reading of "table" (Markdown tables) and a long search (solved runs edit at 17-28).
- Pushing the edit earlier by force (sk_a4 brake at 15 reads, sk_p1 gates) did not reproduce it: forced edits were
  wrong. The winners committed early because they understood early; open question how to get there more often.

### NEXT RUN BUILT: sk_a5 vs sk_a5r (2026-10-26 night, NEWEST — read first)
- User: optimize sk_a2; no fresh mix control; aim for a pass of 5+.
- sk_a2 losses on winnable tasks (7 runs): scripts eating the 28 calls then a refused edit (rich_3470 x2), a misread
  issue (4079), a wrong repro case (3521), the 15589 script loop, 14419 slow/late. In 128 recent runs 54 of 286
  edit_file calls failed (22 "old_string not found", ~14 "occurs N times", 18 after call 28); 37 runs had a failed
  edit, 17 of them ended with no patch (3470 x4, 4079 x3, 11194, 14419 among them); 39 runs spent 6+ calls on scripts.
  Pushing / blocking (a3 rule, a4 brake, p1 gates) never helped; these arms make existing actions cheaper instead.
- **sk_a5 = sk_a2 + `a.py replace FILE START END << EOF` (edit by line numbers: nothing to match) + `a.py run << EOF`
  (a script in one call, 30 s, no file left).** **sk_a5r = sk_a2 + replace only.** Prompts = sk_a2 with the
  edit-mechanics bullet (and for sk_a5 the script line) rewritten. kaggle/cells_skill_a5; digest counts replace / run /
  failed edits (edit_file errors + REPLACE FAILED). T0.2, 8 min / 28 calls, 2 passes, per-arm early stop.
- Tests: replace / run unit-tested on a scratch repo (in-range, out-of-range, a hanging script stopped at 30 s, no
  stray files); full harness sim passed (run via run_command heredoc, REPLACE FAILED counted).

### sk_a4 / sk_p1 / sk_a2_t05 RESULT (2026-10-26 evening, NEWEST — read first)
- ziadsamer/fork-of-generation-all-shards-gpu (kaggle/cells_skill_a4p1), data/results/2026-10-26_skill_a4p1
  (requests 78 MB downloaded). Per-arm early stop worked: pass 1 a4 2, p1 4, a2_t05 3 -> only p1 got pass 2 (2).
  **sk_p1 6/32 (3.0 per pass), sk_a4 2/16, sk_a2_t05 3/16.** None reaches the bar (9 over 2 passes).
- sk_p1: gates get bypassed: 128 raw reads (cat/grep via run_command) in 32 runs, 56 of them right after a BLOCKED;
  9/32 first calls were not the skill (mostly grep -r); plan used 0.9 per run. sk_a4: brake fired in 11/16 runs,
  lost 11194 and 4079 (edited, wrong). Refusals only bind when there is no other way to read.
- **All skill-arm passes so far (14 passes, 224 runs): 37 solved = 2.6 per pass vs mix 3.67 (64 runs from 10-14..10-16).**
  ~1 sigma, not significant, but no arm is above mix. Possible drift: mix's runs are 10 days old (other harness /
  wheelhouse / setup) -> a fresh mix control in the same session is needed before more arm work.
- Local reference table: data/results/dev16_reference.md (rebuilt by data/results/make_dev16_reference.py).

### NEXT RUN BUILT: sk_a4 vs sk_p1 (2026-10-26, NEWEST — read first)
- LB: sk_a2 submitted by the user (dist/submission.zip = dist/sk_a2.zip = dist/sk_a2_submitted.zip, byte-identical
  to the dev16 run); score pending. Old dist/submission.zip = le6_t6.zip.
- kaggle/cells_skill_a4p1 (scripts/train/make_skill_arms_cells.py); arms (scripts/make_skill_arms.py sk_a4 sk_p1):
  - **sk_a4 = sk_a2 optimized:** a.py brake (at STOP READING, find/outline/show answer BLOCKED until the repository
    has a change) + debugflag (debug-looking added lines listed in every output). Prompt = sk_a2 + 2 lines.
  - **sk_p1 = new plan-gated design:** look (8) -> `a.py plan "FILE:LINES what and why"` (gated; shows the closest
    existing test function for location + conventions; plan kept in MEMORY) -> 5 more looks -> edit (gated) -> one
    targeted test -> submit; no scripts; brake + debugflag; new prompt (1,081 words; mix 783, sk_a2 1,018).
  - Broken-code (py_compile) alarm dropped (user: its only evidence was one sk_ad2 patch).
  - **sk_a2_t05 (3rd arm, user):** an exact copy of the submitted sk_a2 (its own a.py) with temperature 0.5.
  - sk_p1 prompt: heading "## Example (an invented package)" -> "## Example " (user's edit, kept in the generator).
- sk_a4 / sk_p1 at T0.2, sk_a2_t05 at T0.5 (sim checked the temperature each arm sends); 8 min / 28 calls; 2 passes;
  per-arm early stop (<= 3 after pass 1 -> dropped). Bar: >= 9 over 2 passes. Pass 1 = 48 runs ~2.5 h wall (~5 h
  quota); each arm continuing to pass 2 ~0.9 h wall (~1.8 h quota).
  a.py options unit-tested on a scratch repo; full harness sim passed (plan saved, plan gate BLOCKED after 5 looks).
- Old arms keep their own a.py copies (sk_a2 / sk_ad2 / sk_a3 restored after regenerating).

### sk_a3 RESULT + WHERE THE SKILL ARMS STAND (2026-10-26, NEWEST — read first)
- ziadsamer/fork-of-generation-all-shards-gpu (kaggle/cells_skill_a3): **sk_a3 2/16, no patch 8**, early stop worked
  (data/results/2026-10-26_skill_a3, request log 20 MB not downloaded). Solved 14419 (mix 2/6) + 3882; lost 11194
  (first edit at call 29 after 18 banners -> refused) and 15589 (E). "No scripts before the edit" partly obeyed
  (1.8 per run; 10 on rich_3934). Median first edit 24 (sk_a2 17); 5/16 runs edited only after call 28.
- **All skill-arm passes on dev16 (mix 3.67):** sk_a 3, 2 | sk_abc 2 | sk_abcd 4 | sk_ad 3 | sk_a2 4, 3 | sk_ad2 1, 2 |
  sk_a3 2. None is clearly above mix; one pass of 16 tasks has a spread of about +-1.7 solved (binomial), so
  differences of 1 task are noise. dev16 cannot separate the arms any more.
- Recurring: STOP READING is read through for 10+ calls (sk_a3: 6 runs had 11-13 STOP banners); edits after call 28
  are refused -> no patch (sk_a3 5 runs, sk_a2 4 of 32).
- Options: (1) LB-submit sk_a2 (no GPU quota; ~116 tasks, a 7x bigger sample; mix 0.17); (2) a hard brake in a.py
  (after STOP, show/find refuse until the repo has a change; le6 lesson: only refusals change behaviour);
  (3) a bigger local eval (dev16 + val16) before any more arm changes.

### NEXT RUN BUILT: sk_a3 alone (2026-10-26, NEWEST — read first)
- kaggle/cells_skill_a3, submissions/sk_a3 (scripts/make_skill_arms.py sk_a3): sk_a2 with mix's brake back: "before
  your first edit, run no scripts or tests", the existing targeted test after it, scratch in /tmp only (write_file
  refuses /tmp). Everything else = sk_a2. 8 min / 28 calls, T0.2, 2 at once, dev16, 2 passes.
- Notebook: per-arm early stop (arms with <= 3 solved after pass 1 are dropped; none left -> the run ends, outputs
  saved); digest counts "scripts/tests before edit" (the number that split solved from failed runs).
  STOP_NEW_TASKS_AFTER_H in cell 2 = this account's quota (h) / 2 - 0.4 so a quota kill never loses the output.
- Bar: > 3.67 per pass (mix) on dev16 before any LB submission (user). Time: pass 1 ~1.1 h wall (~2.2 h quota),
  both ~2 h (~4 h).

### SOLVED-vs-FAILED PAIRS (2026-10-26, NEWEST — read first)
Same task, one run solved and one failed (request log, data/results/2026-10-26_skill_a2/requests):
- fastapi_15589: solved = read, NO EDIT YET, edit at call 13, then a check script. Failed = test script BEFORE the
  edit (call 12) tested the wrong case, passed, "why does it already work?" loop calls 12-21, STOP at 22, a DEBUG
  print at 24 as the whole patch.
- fastapi_11194: solved (sk_a2 x2) = read code calls 2-9, found _extract_form_body at call 6, edit at 14. Failed
  (sk_ad2 x2) = repro scripts from call 2: 11-13 script calls, then the wrong function.
- rich_3521: both experimented; the solved run's 2 scripts reproduced the real case (wide char + zero-width) and it
  edited at call 9; the failed run tested another case (zero-width at the end) and fixed that.
- rich_4079 (5-word issue "Inline table code"): split at the first search: solved went to markdown.py (tables in
  Markdown), failed to table.py (the Table class) and added an unused parameter. Both kept reading ~10 calls after
  STOP READING.
- Counted on the 7 winnable tasks (56 runs): **0-4 script/test runs before the first edit -> solved 8/17; 5 or more ->
  2/11 (0/9 without rich_3882)**. Correlation (a confused run may also experiment more), but it matches rung-3 lesson
  "scratch scripts double experimenting and hurt; mix's write_file-/tmp refusal is a hidden brake".
- **sk_a2 removed that brake:** its prompt tells the model to write scripts to .git/agent/check.py (write_file works
  there); mix says /tmp only, where write_file refuses. D (sk_ad / sk_ad2) adds even more scripts -> worst arms.
- Banner gaps: it only shows on a.py outputs (script loops never see it), and STOP READING is often ignored ~10 calls.
- Candidate sk_a3 = sk_a2 with the brake back: no own scripts (no .git/agent/check.py; check = existing tests after
  the edit only), everything else unchanged.

### WRONG-EDIT ANALYSIS (2026-10-26, NEWEST — read first)
All 30 edited-but-failed runs of sk_a2 / sk_ad2, each patch read against the gold patch and the hidden test
(no test output was saved; judged from test_patch):
- **A. Hidden exact text / value (10):** 14258 x4 (test wants AssertionError + exact message; neighbours use assert),
  14487 x3 (exact output "Validation errors:" / "Field: (...)"), rich_3468 x3 (exit code 1, model used 0: near miss,
  Python's SIGPIPE docs use 1).
- **B. Large feature / rewrite (9):** 15800 x3 (654 lines, 8 files), 14306 x3 (137), 15280 x2 (`@app.vibe()`),
  rich_3180 x1 (127-line wrap rewrite).
- **C. Wrong place (7):** 13920 x4 (patched _compat helpers; fix belongs in analyze_param where the annotation is
  first read), 11194 x1 (get_body_field instead of _extract_form_body), rich_4079 x1 (added an unused Table param
  instead of markdown.py), rich_3934 x1 (live_render only; gold also live.py stop()).
- **D. Right place, wrong / partial logic (4):** rich_3521 x1, fastapi_14419 x1 (partial of 62 lines), 15589 x2
  (one = a left-over DEBUG print as the whole patch; the only debug-print patch in 64 runs).
- A + B = 19/30 are out of reach for prompt changes. C + D = 11/30 are reachable, and 4 of those tasks (11194, 15589,
  4079, 3521) were solved by another run: the remaining gap is mostly run-to-run variance on ~7 winnable tasks
  (ever solved by any arm or mix: 11194, 15589, 3882, 4079, 3470, 14419, 3521). sk_a2 per task: 11194 2/2,
  3882 2/2, 15589 1/2, 4079 1/2, 3521 1/2, 14419 0/2, 3470 0/2.

### sk_a2 vs sk_ad2 RESULT (2026-10-26, NEWEST — read first)
- engziadsamer/arms-again (new version, kaggle/cells_skill_a2), both passes completed (64 runs; outputs in
  data/results/2026-10-26_skill_a2, request log 77 MB not downloaded yet).
- **sk_a2 4 + 3 = 7/32 (3.5 per pass; mix 3.67), no patch 3 + 5 (4.0 per pass; mix 5.0).** Solves 11194 SS, 3882 SS,
  15589 S, 4079 S, rich_3521 S (mix 0/2; memory arms solved it in 3 of 5 arm-runs). Never 14419 (mix 2/6), 3470 (1/6).
  **sk_ad2 1 + 2 = 3/32, no patch 10 + 6:** D hurts even limited to short issues -> drop D for good.
- Fixes worked mechanically: call 1 wrong 0/64, pip 0; banner fired in 28/32 sk_a2 runs; refusals 0 (reshown ~1);
  sk_a2 edited in 29/32 runs, median first edit at call 17 (was 26-30); mean agent 333-353 s (mix ~346, scorer-safe-ish).
- **Verdict: sk_a2 = mix on dev16.** More runs now edit, but the extra edits are wrong: the bottleneck is the
  CORRECTNESS of the edit (13920, 14258, 14487, 3468 edited-but-wrong in every arm). Next: analyse wrong edits vs gold
  (patches in the output; no GPU).

### NEXT RUN BUILT: sk_a2 vs sk_ad2 (2026-10-25 late, NEWEST — read first)
- kaggle/cells_skill_a2 (scripts/train/make_skill_arms_cells.py), submissions/sk_a2 + sk_ad2
  (scripts/make_skill_arms.py sk_a2 sk_ad2; old arms stay as they ran). 8 min / 28 calls, T0.2, 2 at once, 2 passes,
  ends by itself after pass 1 if no arm solves > 3. Saved version. ~4 h quota (pass 1), ~7.5 h (both).
- Fixes (all from the arms-again request log): call 1 spelled out ("Call 1: run_skill_script", never pip, no internet)
  + SKILL.md / install output say READY, nothing to pip install; usage shown as an invented concrete example (no
  copyable template); a.py options in commands.txt: banner (NO EDIT YET at 10 looks or 210 s since setup, STOP READING
  at 15 / 300 s, only while git status is clean) and reshow (repeat -> shown again, max 40 lines, ALREADY SHOWN);
  note / pin removed; timeout 90 on pytest, timeout 30 on own scripts (in .git/agent/, write_file refuses /tmp).
  sk_ad2 = + short-issue section limited to one- or two-line issues.
- Question it answers: do the fixes lift the memory arm above mix (3.67), and does D add anything on short issues?
  Digest adds reshown / banners / pip / call-1-wrong counts.

### sk_a vs sk_ad RESULT (2026-10-25 late, NEWEST — read first)
- engziadsamer/arms-again (kaggle/cells_skill_ad), pass 1 only (early stop worked, outputs saved:
  data/results/2026-10-25_skill_ad incl. requests.jsonl 36 MB): **sk_a 2/16 (7 no patch), sk_ad 3/16 (9 no patch)**;
  mix 3.67 / 5.0. Both below mix.
- **Bug found in ALL skill arms (also the first run):** only 17/32 first calls were the skill install. 5 runs ran
  `python3 -m pip install .` ("I'll install the agent tool") = 202 s lost (internet off), all fastapi -> explains the
  slow fastapi_14419 etc.; others copied the usage template literally (`find "exact text" wher...`) or ran
  `python3 scripts/install.py`. Fix the install wording (+ never pip) before judging the memory idea.
- Other digest findings: first edit at call >= 26 in 12/32 runs (6 refused past call 28 -> no patch); note/pin
  ~0.1 per run (ignored); NOT SHOWN AGAIN costs 2-3 calls per run; 2 commands hung 240 s (rich_3882 repro.py under
  sk_ad, a python heredoc test on fastapi_14258); D's repro advice spreads to long issues.
- Candidate fixes (not built): unambiguous install + no pip; "NO EDIT YET" banner in a.py output after ~18 calls
  without a diff; re-show (short) instead of refusing; drop note/pin and D; `timeout 30` on repro/test commands.

### SKILL ARMS RESULT + NEXT RUN (2026-10-25 night, NEWEST — read first)
- **Adapter test (cells_test_31b) stopped:** at 15 min, base_t02 3/7 dev16 vs sd_t02/sd_t07 0/7 (4 no-patch).
  Fine-tuning parked.
- **Skill arms pass 1 (log only: saved version cancelled after PASS 1 -> outputs lost;
  data/results/2026-10-25_skill_arms/testing-arms.log):** sk_a 3/16 (5 no patch), sk_abc 2/16 (10 no patch),
  sk_abcd 4/16 (5 no patch); mix 3.67 / 5.0 per pass. New solves: rich_3521 (abcd; mix 0/2); rich_3470 sk_a 2/2 incl.
  pass 2 (mix 1/6). fastapi_14419 no patch in ALL arms (mix 2/6, never no-patch). abc vs abcd differ only on the 9
  non-short issues (D can't act there) -> mostly noise. "time" ends: real slow runs (calls left) 3/4/4, same tasks
  (14419, 3180, 3521, 14258); sk_a's extra ones = 28 calls x 17 s hitting both limits. Median 13-14 s per model call
  in every arm (= mix). 10 min / 32 calls rejected: arms already average 367-391 s/task (mix 286-382, le5 347 timed
  out on the 12-h sequential scorer).
- **Next run built: kaggle/cells_skill_ad** (scripts/train/make_skill_arms_cells.py): sk_a vs sk_ad (= sk_a + the
  short-issue section; scripts/make_skill_arms.py), 8 min / 28 calls, T0.2, 2 at once, 2 passes (64 runs); ENDS BY
  ITSELF after pass 1 if no arm solves > 3 (run it as a saved version). DIGEST line after every run (in the log):
  a.py use, raw reads, refusals, first-edit call, compactions, model vs tool seconds; results/digest.jsonl; cell 5
  per-arm means. Sim (data/sim/armsim.py, SIM_CELLS / SIM_EARLY) passed both branches (local resolved=False = uv venv
  has no pip; not a notebook issue).
- **Rule (memory runs-must-end-by-themselves):** cancelling a saved version loses /kaggle/working; build runs to end
  at the stopping point; say "saved version" vs "interactive" up front.

### CHECKPOINT 2026-10-25 evening (NEWEST — read first)
**Two GPU runs are with the user; nothing else is pending on my side.**
1. **TEST notebook (kaggle/cells_test_31b, adapter vs mix) — RUNNING/maybe done.** 240 runs = 40 tasks (24 test, unseen
   repos + dev16) x 3 arms (base_t02 = mix T0.2, sd_t02 = adapter T0.2, sd_t07 = adapter T0.7) x 2; 6 at once, 15 min.
   Early lines: adapter solved only mix-solved test tasks (lizard-370, policyuniverse-147, glyphsLib-1015); 0/5 on dev16
   early. Reference: mix T1.0 11/24 on test (combined run), mix ~3-4/16 on dev16. When the user pastes cell 5: compare
   per set; run scripts/triage.py on its output (attempts "<arm>.<n>"; jobs task#a<arm>.<n>) for submit loops/no-edit.
   Adapter = engziadsamer/finetuning-shard-2 output (adapter_31b/final, r16/a16; val 0.1932 -> 0.1605), dataset
   engziadsamer/model-trial-2.
2. **SKILL ARMS notebook (kaggle/cells_skill_arms) — BUILT, user to run.** dev16 only; sk_a / sk_abc / sk_abcd (see
   "SKILL ARMS BUILT" below); T0.2, 8 min, 2 at once = mix's 64 dev16 runs (control embedded: 3.67 solved, 5.0 no-patch
   per 16-task pass; per task in MIX_REF). Pass 1 (48 runs, ~2.5 h, ~5 h quota) prints "PASS 1 COMPLETE" -> user may stop
   and run cell 5; pass 2 = 48 more. Inputs: competition, wheelhouse, model 31B, rodrigospalma/ood45-bugfix-split,
   ziadsamer/rebench-new-cp312, gold-check output (ziad23samer/test-gemma-comp or its dataset); Internet OFF; set
   STOP_NEW_TASKS_AFTER_H = quota/2 - 0.4. AFTER IT: run scripts/triage.py on its output + check compliance (did the
   model install the skill first, read only via a.py, use note/pin/impact/check, how often read_file / cat / NOT SHOWN
   AGAIN / SCRATCH FILE); then decide pass 2 / which arm to push / LB.
- **How to read results:** scripts/triage.py extract/report; scripts/failure_analysis/ (fail_load, devtime, devgroups,
  devshort, devcase). Exported failed runs: data/results/2026-10-25_failed/ (4 files, 574 runs). Triage files:
  data/results/2026-10-25_triage/. Local sims: data/sim/testsim.py (test notebook), data/sim/armsim.py (skill arms,
  fake model drives the real skill through the real harness; run with data/venv_harness/bin/python).
- **Skill arm sources:** scripts/agent_skill/{a.py,install.py} -> scripts/make_skill_arms.py writes submissions/sk_*;
  scripts/train/make_skill_arms_cells.py writes the notebook (run both with .venv/bin/python; pack.py validates).
- **Ideas parked:** memory script alone in a submission vs + adapter; FastAPI docs_src tutorial files for features;
  32-36 calls arm (user: no doubling); per-task analysis of rebench "wrong fix" group (253 runs) not read one by one.
- **Kaggle lessons today:** kagglehub version download only works in INTERACTIVE sessions (committed -> "New Datasets
  cannot be attached in non-interactive sessions") and it mounts at the SAME path as the attached latest version.

### UPDATE 2026-10-25 (earlier today)
- **Training:** session 1 PAUSED at step 93/152 after 10.48 h (fatmazenhom/finetuning-shard-1). Val (8-segment
  subset) 0.1797 @21 → 0.1742 @42 → 0.1725 @63 → 0.1714 @84 (full val @start 0.1932); train avg 0.163; peak 18.4 GiB.
  Session 2 RUNNING (resumed at 93; ~7 h real). Then: final val on all 28 vs 0.1932, then the TEST notebook (not built).
- **Failure triage DONE (Plan B: scripts/triage.py + kaggle/cells_triage; data/results/2026-10-25_triage):** 965 mix
  generation runs (T1.0, 15-min cap, 28 calls; submission = T0.2, 8 min), 391 resolved (41%). Buckets: right files but
  wrong fix 41% (tested 286 + untested 111), no edit before the 28-call budget 7.7%, edit refused by budget 3.7%, wrong
  files 5.1%. Wrong-fix patches are ~0.55x the gold size and miss a gold file 33-41% (resolved: 0.99x, 12%); public tasks
  0.40-0.49x, 44-53%. Caveat: bigger gold = harder task, so size ratio is partly difficulty. mix prompt line 1 says
  "fast and minimally" → suspected cause of incomplete fixes. Waste: 278 runs (29%) call submit_patch >=3x (median 49);
  1,042 compactions in 741 runs (77%); first edit by call 8 → 58% solved vs call 25+ → 20%. Kaggle note: a kagglehub
  version download mounts at the SAME path as the attached latest version (replaces it in that session).
- **Training DONE (engziadsamer/finetuning-shard-2):** 152/152 steps, full val 0.1932 → **0.1605** (subset 0.1693 @147);
  one grad spike 6386 @88 (clipped, loss/val unaffected); adapter_31b/final = r16/alpha16 (files in
  data/results/2026-10-25_train31). **TEST notebook BUILT (kaggle/cells_test_31b, commit 87f2160):** base_t02 / sd_t02
  / sd_t07 on 24 test tasks + dev16 (never generated on → clean; same repos as trained public tasks → reported apart),
  2 runs each = 240 runs ≈ 6 h at 41/h ≈ 13 h quota. Sim passed (data/sim/testsim.py).
- **FAILURE-PATTERN ANALYSIS (2026-10-25; dev16 625 runs + val16 77 local traces; 574 exported failed generation runs
  = 52 public + 522 rebench, data/results/2026-10-25_failed via kaggle/cells_export_failed):** (A) reading paralysis:
  no-edit runs found the gold file by call ~2 (80%) then read it 8-22x in ~32-line slices, 24% re-reads (57% of them
  after a compaction), the 28-call budget binds (median 345 s < 480 s) - public 31% / rebench 16% of failures;
  (B) missed another file: 65% of 150 runs the missed file uses a name our own edit touched (plumbing/siblings, e.g.
  rich_3777 diagnose.py) - public 33% / rebench 25%; (C) wrong fix in the right file (public 25% / rebench 48%): half
  never ran an existing test; runs that checked after the last edit solved 50% vs 28%; (D) thin issues (22/52 public
  failures < 30 words) -> wrong area/direction; (E) unwinnable: hidden exact texts / huge features (~1/3 of dev16).
  History: ~20 dev16 designs all 19-69% no-edit, warnings (r4b_warn) and locator/editor splits worse.
- **SKILL ARMS BUILT (commit 82c8d56):** .git/agent/a.py via a skill (le6's proven install): find/outline/show/note/pin
  with a MEMORY header in every output (reads, notes, pinned lines) + refusal of repeats of the last 3 reads; impact
  (callers of changed defs + where neighbouring names live); check (.git/agent/repro.py + nearest tests + git status
  flags). Arms sk_a (memory), sk_abc (+impact+check), sk_abcd (+thin-issue decoding), full mix rewrites, read_file kept
  declared (task message names it; undeclared call = task lost). Notebook kaggle/cells_skill_arms: dev16 only, T0.2,
  8 min, 2 at once = mix's 64 dev16 runs (3.67 solved / 5.0 no-patch per pass, embedded control); pass 1 then pass 2.
  Lessons: write_file refuses /tmp ("escapes workspace root") -> repro in .git/agent/; .txt not extension-less files.
- **NEXT (old proposal, superseded by the skill arms):** one prompt change: full rewrite where "minimal" no longer means "stop at the
  first spot" (check all places the bug lives: callers, siblings, sync/async twins, other files using the name) + a clean
  ending (no submit loops); measure on the swing set (tasks mix solves sometimes), base vs change, same tasks.

### CHECKPOINT 2026-10-24
**NOW: 31B LoRA training SESSION 1 is RUNNING** (user started it 2026-10-24; GPU L4x4, pinned Python 3.12 notebook,
cells kaggle/cells_train_31b, commit 3bfc406). Inputs: wheelhouse, model gemma-4-31b-it-qat-w4a16-ct, dataset
`merged-samples` (the merge's samples.pt uploaded by the user; report.json not needed).
- **Training data (merge, kaggle/cells_merge, run interactively on engziadsamer):** 226 tasks, one run each (fewest
  replies), 0 test tasks, 7 segments > 16384 dropped, leak 33% (cap 34%, 0 dropped). TRAIN 210 runs / 303 segments /
  3.43M tokens (1.14M trained): d0 93, d1 62, d2 8, large 2, OOD 23, public 22. VAL 16 runs / 28 segments / 0.29M.
  Sources: full run 88 + retry 11 (engziadsamer/filtration-cpu), extra run 39 (gen-extra-all v1 via kagglehub),
  combined run 88 (dataset ziad23samer/cell-samples).
- **Settings (agreed):** LoRA r16 alpha16 (scale 1.0), lr 1e-4, warmup 8, cosine -> 10%, 1 epoch, 2 segments/step
  (~152 steps), clip 1.0, max 16384 tokens, 6 mid-run val on 8 segments + full at start/end. ~60 tok/s -> ~16 h real
  = ~32 h quota. **Two sessions (decision A):** session 1 PAUSES at 10.8 h (`--session-hours`, keeps the full
  schedule; prints `PAUSED at step N/152`); then its OUTPUT -> private dataset -> attach to the SAME notebook as session
  2 (cell 2 prints `RESUMING from ...`) on an account with ~12 h quota. CPU tiny-model test of pause/resume passed.
  Expected first lines: `train 303 segments 3.43M tokens`, `VAL [start]` (~20-30 min), steps ~400 s each.
- **Serve check PASS** (fatmazenhom/serving-check): our trainer's 31B adapter served by the scorer's vLLM setup.
- **NEXT TO BUILD (not built yet):** (1) TEST notebook: the 24 test tasks (rebench-new-cp312, split 'test', 21 repos)
  with base mix @T0.2, adapter @T0.2, adapter @~0.7 (Apple SSD paper: best eval temp rises after self-distillation);
  base's existing T1.0 generation runs on them are NOT comparable. Reuse cells_gen (task set rebench-new-cp312,
  SAMPLE = test ids, submission with adapters/<name> + `adapter:` line, temperature per arm). Watch ASCENT's failure
  signs (loops, tool errors, longer replies); fallback = serve alpha 8 (scale 0.5) by editing adapter_config.json.
  (2) Submission packaging with the adapter (scripts/pack.py; adapters/ folder). (3) One LB submission of the winner.
- **Later data ideas (if the adapter helps):** looser filter (~80 solves rejected for rereads; measure on CPU),
  second runs on solved tasks (~70% solve), bigger SWE-rebench build (funnel 2,589 = small slice), weekly quota.
- **Kaggle lessons this round:** notebook outputs across accounts hang -> datasets; a notebook linked to a dataset only
  offers "new version" -> attach its output directly on the same account or download+upload; dataset versions the input
  panel can't pick -> kagglehub.dataset_download('owner/name/versions/N') with internet ON; interactive sessions keep no
  output (commit or download); first model load on an account can take 43 min (weights read) vs 2-3 min when cached;
  public tasks: never install pytest-httpbin --no-deps into sandboxes (crashed every public test: 0/84; re-graded 32/84);
  public reference patches lack `diff --git` headers (selfdistill diff_files fixed).
- **Accounts:** ziad23samer (my API token; builds/verify/cp312/regrade/samples), engziadsamer (filtration-cpu, merge),
  ziadsamer (generation-all-shards-gpu: extra + combined runs; datasets gen-extra-all v1/v2), fatmazenhom (serve check).
  Rules caveat on extra accounts stands (see 10-22 block): add helpers to the team before the merger deadline if LB.

### DATA SPLIT (user decision 2026-10-22, evening; supersedes "OOD-45 is the yardstick, never training data")
| Set | Contents | Use |
|---|---|---|
| Train | clean resolved runs from: rebench 347 (+ retry), ALL of OOD-45, the public 129 tasks (share capped: 4 repos) | LoRA |
| Val | ~10% of those runs, split by task hash | val loss only (fit check, not agent quality) |
| Test | NEW SWE-rebench set, ~50-60 tasks, repos in NO training source (not our 248, not OOD's 17, not fastapi/requests/rich/httpx) | base vs adapter, full scored runs |
| Final | one LB submission | LB = 58 of the ~120 hidden tasks (private repos); the public 129 are NOT on it |
- Logic: a test set's tasks AND repos never appear in training and it is fixed before any result; never choose test
  tasks by outcome (e.g. "tasks the base failed" -> the base scores 0 by construction, the adapter wins by noise).
  A held-back OOD slice was rejected: OOD has only 17 repos -> same repos as the trained OOD part.
- Accepted cost: the test comes from the same pipeline as most training data -> may flatter the adapter a little;
  repo-disjoint + the LB check cover the rest.
- To build: (1) test-set build + offline verify (CPU, make_rebench_full_cells.py / make_rebench_verify_cells.py /
  cp312 cells, excluding all training repos); (2) generation on OOD-45 (~1.5-2 h GPU) and on the gradable public
  tasks (~84, ~2-3 h GPU), request logger on; (3) the samples notebook must accept their task files (it reads the
  gold files from the rebench tasks.jsonl today); (4) samples on each output; merge + caps at training.
- Samples re-run (a9afcf5 rules) on the full run: **88/153 kept** (strict 65), 123 segments, train 81 runs 1.25M
  tokens (0.43M trained), val 7 runs; median 11.5k, max 17.4k tokens; leaky 45%. Retry at 9/75 solved (2026-10-22).
- Prompt test first launch failed: vLLM stuck at "Loading safetensors 0/1" for the whole 20-min startup limit (fresh
  account, lazy model input) -> cell 3 now reads the weights first with progress lines, limit 60 min (2c8145e).
  Relaunched; at 40/100: mix2 15 vs mix 14 on the same tasks (noise).

- **Papers read 2026-10-22 (user-found):**
  - arXiv 2604.01193 (Apple, "Embarrassingly Simple Self-Distillation"): sample 1 solution/problem from the model at a
    raised temperature WITH truncation (top-k 20, top-p 0.8-0.95), no correctness check, plain SFT (full FT, ~10k
    problems, 2,500 steps x 32) -> Qwen3-30B-Instruct LiveCodeBench v6 42.4 -> 55.3 pass@1 (hard +15.3). Thinking models
    gain much less (+2.1..+3.3). Best eval temperature rises after training (30B-Instruct 0.7 -> 0.9). Single-turn code.
    -> TO DO: test the adapter at T 0.2 AND ~0.7; if more generation later, try top_k 20 (current: T1.0, top_p 0.95).
  - arXiv 2603.24472 (Microsoft/KAIST/SNU, "Why does self-distillation (sometimes) degrade reasoning"): a teacher that
    sees the solution writes short, confident reasoning ("wait/hmm/check" vanish) and the student degrades up to 40%;
    SFT on 800 correct UNGUIDED own runs (= ours) ~neutral (AIME24 54.8->51.0, AIME25 37.9->40.0); fewer training
    problems -> worse on new ones. -> gold-guided runs REJECTED; repo-disjoint test + LB check stay essential;
    selfdistill_episodes.py now prints doubt words per 1k thinking words for kept / solved-rejected / failed runs.
    Trial (n=3/4/13): 23 / 29 / 27 (too few to judge). **Full run + retry (engziadsamer/filtration-cpu): kept 24.2,
    solved-rejected 23.6, failed 24.5 (median per 1k words) = NO difference -> the filter does not select confident
    runs; kept runs are shorter (median 1,386 vs 2,304 thinking words) but doubt at the same rate.**
- **Retry done (engziadsamer/trial-2-gpu, data/results/2026-10-22_gen_retry):** 22/187 solved -> 182/347 tasks (52%).
  Samples: full run 88 kept (1.25M train tokens), retry 11 kept (0.21M) -> **99 runs, ~1.46M train tokens (0.50M
  trained), val 9 runs**; leaky ~42% (cap toward 34% at training).
- **Extra run DONE (ziadsamer/generation-all-shards-gpu, data/results/2026-10-22_gen_extra):** 63/99 solved (OOD 37/44 =
  84%, ours 26/55); weights read 43 min on a first-time account; 2.7 h of tasks at 36.9/h. Samples
  (ziad23samer/cell-samples-on-shards-cpu): **39 kept (25 OOD + 14 ours), 0.56M train tokens**; doubt words equal again.
  **TOTAL NOW: 138 kept runs (88 + 11 + 39), ~2.0M train tokens (~0.69M trained), val 13.** The 4-part attempt (parts
  2/4 ran on the wrong set: 391 = 347 + OOD; 17 solved, mostly repeats) is skipped.
- **2026-10-24: combined run (parts 3/4 + public):** ours 121/269, public 0/84 = grading bug (pytest-httpbin installed
  --no-deps in public sandboxes; fixed) -> CPU re-grade 32/84 (ziad23samer/regrade-cpu). Samples: 88 kept (24 public).
  **Training data: ~226 runs, ~3.25M train tokens.** Decisions: (1) A = all data, two sessions with pause/resume
  (train_sft.py --session-hours); (2) **SERVE CHECK PASS** (fatmazenhom/serving-check, data/results/2026-10-24_serve_check):
  our trainer's 31B adapter (r16 alpha16) served by the scorer's vLLM setup via submission adapters/ + agent.yaml
  adapter: -> PINEAPPLE-42 learned in 9 steps, base unaffected, math intact, thinking on/off; model load 174 s;
  (3) test = base T0.2 vs adapter T0.2 / ~0.7 on the 24 test tasks, then one LB. Pipeline: kaggle/cells_merge (CPU,
  kagglehub for gen-extra-all v1) -> kaggle/cells_train_31b (2 sessions). Papers: ASCENT (arXiv 2610.05303) = plain
  SFT on own verified runs (RFT) can drift/degrade; watch loops / tool errors / reply length; fallback = serve at
  alpha 8 (scale 0.5).
- **User decision 2026-10-22:** wait for build parts 3/4, then ONE GPU run for parts 3/4 + the 84 public tasks
  (cells_gen_public is ready; the combined notebook must reconcile the two sandbox setups).
- Extra generation (cells_gen_extra) in 4 parts on 4 accounts (~2 h quota each, PART=(k,4), no new task after 0.6 h);
  each part's output -> private dataset gen-extra-pK shared with engziadsamer -> one samples notebook there.

### CHECKPOINT 2026-10-22 (read next; 10-21 block below has the build history)
**Pipeline state (self-distillation of the 31B mix agent on our SWE-rebench tasks):**
- Task set: **347 tasks on Python 3.12** = Kaggle dataset https://www.kaggle.com/datasets/engziadsamer/rebench-final-cp312
  (3.13 original: ziad23samer/rebench-final, 348). Why 3.12: vLLM 0.19.1 needs Python 3.12 + torch 2.10 = images of
  notebooks created before ~Oct 20, kept via Copy & Edit + "Pin to original environment"; new notebooks = 3.13 +
  torch 2.11 (vLLM cannot run). Kaggle has no Docker -> sandbox tests run on the notebook's Python.
- Generation (kaggle/cells_gen, mix at T1.0, 15-min time limit gen-only, 28 calls, 6 at once, offline):
  trial 7/20 + full 153/327 => **160/347 tasks solved (46%)**; results data/results/2026-10-21_gen_trial,
  2026-10-22_gen_full (gen_per_task.jsonl; request logs stay on Kaggle: full run = output of engziadsamer/trial-gpu,
  537 MB; trial = ziad23samer/getting-started-gemma-4-developer-agent-new). Failures: wrong fix ~117/187, 28-call budget
  used up 88, 80-turn limit 39, time 12. **RETRY RUNNING** (MODE 'retry', attempt 2 on the 187 unsolved; in a Copy &
  Edit of trial-gpu; 3/21 solved at 40 min, ETA ~5 h more; user keeps it, training will be on another account).
- Samples (kaggle/cells_samples, CPU, scripts/train/selfdistill_episodes.py + build_samples.py --split-on-break):
  first pass on the full run kept **69/153** solves (0.32M trained tokens). Rule fix (true rereads, not reads per file:
  52 solves were rejected only for reading a long file in chunks) committed a9afcf5; **user is re-running** the notebook
  engziadsamer/clean-self-distillation-cpu (public, so its output can be fetched with scripts/kaggle_api.py). Expect
  ~100-120 kept. Then run it again on the retry output (separate samples file; merge at training).
- KEY FINDINGS baked into the samples: (1) the base model loops after submitting (submit_patch dozens of times,
  'Bye.'/'End.') -> every episode is CUT at the first successful submit; (2) **Gemma's chat template drops the thinking
  of a final (tool-free) turn** (chat_template.jinja line ~239: thinking only before tool calls) = the old stage-B loop
  bug -> final turn appended RAW (`<|channel>thought\n...\n<channel|>text<turn|>`), model's own clean final reply when
  available, else a fixed one with thinking; (3) mix's prompt lines "never end a turn with plain prose" + "submit can be
  re-issued" drive that loop.
- Filter: resolved, hits the reference fix's files, no test edits, no scratch files, looks before first edit, fail
  streak <=3, repeats (same call, no edit since) <=2, rereads of same lines <=2, text-only turns <=1, no junk text.
  Kept-set skew: leaky texts 48% (public 34%) -> CAP AT TRAINING TIME; unfair 0% (expected).
- **Prompt experiment RUNNING** on a friend's account (user's decision, warned it is against the private-sharing rule;
  user will add him to the team with 0% split if results reach the leaderboard, BEFORE the team merger deadline):
  submissions/mix2 (mix prompt rewritten from scratch from the run habits) on a fixed 100-task sample (mix att-1 solved
  46) at the SAME generation settings (kaggle/cells_prompt_test, MODE 'prompt'). Compare paired vs mix attempt 1;
  ~100 tasks only detects ~+10 pts.
- **Training (to discuss when data is in; user's other account):** 31B int4-LoRA trainer speed ~60 tok/s (probe
  2026-10-18) -> ~1.8M tokens = ~8-9 h wall = ~17-18 h quota for ONE epoch; + ~4 h quota for a check (OOD-hard or a
  30-task sample). Settings agreed: r16 alpha16 (scale 1), lr 1e-4 cosine, max-len 16384 (24k OOMs on 31B), 1 epoch.
- Kaggle access: scripts/kaggle_api.py reads only PUBLIC notebooks of other accounts (403 on private). Cross-account
  notebook-output inputs hang on "Preparing to download" -> embed small results in cells instead.
- User preferences added: always give input URLs; describe notebooks by required property, never guessed names; keep
  replies short.

### CHECKPOINT 2026-10-21 (newest; the 10-20 evening block below is the background)
- **Task builds DONE (CPU, scripts/datasets/make_rebench_full_cells.py):** pilot-2 23/40 usable; part 1 172/350
  (Kaggle ziad23samer/new-data VERSION 1); part 1b 74/113 (new-data VERSION 2 = latest; same notebook re-used);
  part 2 184/344 (ziad23samer/new-data-2). Usable = gold PASS x3 + empty FAIL; 0 flaky; ~7% env_partial. Small
  output files (tasks.jsonl, gate, leakage, repos, pr...) in data/results/2026-10-21_rebench_full_{new-data,p1b,p2}/
  and 2026-10-21_rebench_pilot2/. No overlap between parts. Failures: mostly Python 3.13 breakage of old repos.
- **Total 453 usable tasks, ~330 repos; public-like domain 306 / other 140 / pilot 7 unclassified** (fixed
  classifier: 1 keyword hit, no generic words, URLs stripped; part 1's own labels used the old 2-hit classifier, so
  RE-CLASSIFY at assembly from repos.jsonl). 80/20 (user) -> keep all public-like + sample ~77 other -> ~385 tasks.
- **Leak:** issue texts ~50-57% leak, PR texts ~19-26% -> choose PR/issue text per task at assembly to hit 34%.
- **WAITING ON USER:** save each output as a private Kaggle dataset (new-data v1, new-data v2, new-data-2) and send
  the names. **NEXT (me):** the OFFLINE verification/assembly notebook (internet off): attach 3 datasets + pilot-2;
  re-gate all once; scan snapshots for commits after base; reclassify domains; 80/20 trim; PR/issue text choice to 34%
  leak; unfair_names labels (scripts/datasets/unfair_tests.py); fake-model end-to-end through the real tools + our
  episode builder; write ONE merged dataset, kept PRIVATE and shared with the other account (user 2026-10-21), for generation (30 h).

- **FINAL TASK SET DONE (verify notebook ziad23samer/verification, offline, 2026-10-21): 348 tasks / 248 repos**
  (385 selected - 37 dropped offline: 16 package not importable, 21 gold fails; causes = network-needing tests
  (DNS, downloads) and old setup.py installs that fetch build deps; consistent with offline grading). Shares: public-like
  81%, leak 34%, unfair 12%, PR text 56%, env_partial 9%, large 20. Snapshots 385/385 clean. Offline fail-fast hook
  (.pth in sandbox venv) + host pytest plugin wheels (wheels/host) ship with it: generation MUST use both. Small files:
  data/results/2026-10-21_rebench_verify/. User: output -> private dataset, shared with the generation account.
  NEXT: generation notebook (31B mix, thinking, 2-3 samples/task T1.0, same sandbox setup) + run filters.
- **PYTHON 3.12 SWITCH (2026-10-21):** new Kaggle notebooks = Python 3.13 + torch 2.11 -> the wheelhouse's vLLM 0.19.1
  (needs torch 2.10, cp312 helper wheels) cannot run. Old notebooks copied + "Pin to original environment" keep
  Python 3.12 + torch 2.10 (GPU and CPU). Kaggle has no Docker, so the sandbox runs tests on the notebook's Python ->
  task set re-targeted to 3.12 (kaggle/cells_rebench_cp312, run ziad23samer/getting-started-gemma-4-developer-agent-new):
  176 wheels converted (155 downloaded, 21 built), re-gated on 3.12: **347 tasks** (lark-parser-1013 dropped).
  env_partial 32 -> 193 on 3.12 (older pip falls back to `setup.py develop`, which fails; tests still pass from the repo
  root; per-task value in gate.env_partial). Small files: data/results/2026-10-21_rebench_cp312/. Generation runs in a
  pinned copy of an old GPU notebook on the other account (fatmazenhom/ood-12b) with dataset rebench-final-cp312.
- **GENERATION RUNNING (2026-10-21 night):** Kaggle notebook engziadsamer/trial-gpu (Python 3.12 image, L4x4, internet
  off), kaggle/cells_gen MODE 'full', concurrency 6, mix at T1.0, 15-min time limit (gen only; trial showed 6-at-once
  slowdown cut 7/12 runs at 8 min), 28 tool calls. Trial (20 tasks, data/results/2026-10-21_gen_trial/, its request log
  in ziad23samer/getting-started-gemma-4-developer-agent-new output) = 7/20; its rows are embedded in cell 2. Full run at
  38/327: 15 solved, ~32 attempts/h, ETA ~10 h total. NEXT: fetch output (small files + requests.jsonl ~0.5 GB? check
  size first), then MODE 'retry' (attempt 2 on unsolved), then run filters + build samples + train (r16/alpha16, lr 1e-4).
- **Self-distillation training settings (agreed with user 2026-10-21):** round 1 = rank 16, alpha 16 (scale 1.0),
  lr 1e-4 (cosine to 10%, warmup), 1-2 epochs by data size; earlier runs used r16/alpha32 (scale 2) + lr 2e-4 = too
  strong. Round 2 only if round 1 overfits: rank 8 / alpha 8 (keep scale 1). Every sample's final turn must have
  thinking (submit_patch loop fix). Judge on gemma-val, our test split, OOD-hard; not loss alone.

### CHECKPOINT 2026-10-20 EVENING (read this first; details in the bullets below it)
- **Direction (user):** self-distillation on CLEAN data = Gemma 31B's own resolved runs on tasks we build from
  nebius/SWE-rebench (option B). Teacher-imitation data DROPPED (OOD-45: base 27/44 vs LoRA 23/44 at both scales;
  LoRA taught 2 habits: repeated submit_patch after a successful submit [final training turn had no thinking] and
  failing-retry streaks). "Fixed teacher data" = parked idea, maybe later as an add-on for tasks Gemma never solves.
- **Data pipeline status:** funnel → 2,589 candidates (scripts/datasets/rebench_funnel.py; core ≤130 lines/≤6 files/
  difficulty ≤2 + large 131-500; nothing >500). Pilot notebook kaggle/cells_rebench_pilot (scripts/datasets/
  make_rebench_cells.py; CPU, Internet ON, inputs: competition + wheelhouse + OOD-45 dataset; GitHub token in Kaggle
  secret GITHUB_TOKEN): cells 1, 2, 2b PR texts, 3 build, 4 gate, 5 summary, 6 leakage. Pilot run 1 (output notebook
  ziad23samer/pilot, results in data/results/2026-10-20_rebench_pilot/): PR texts 40/40, snapshots 40/40, packages
  36/40, **usable 11/40**; 16 failures = Kaggle's host `typeguard` pytest plugin vs old typing_extensions → FIXED
  (host-only pytest plugins hidden in the sandbox), 2 = import name for namespace packages → FIXED (patched file's
  own package), rest genuine (Py3.13 incompatibilities, failing other tests, installs). Kaggle notebooks now run
  **Python 3.13** (wheel set x86_64-cp313). **NEXT USER STEP: re-run the pilot** with new cell2/cell3/cell4 and the
  previous pilot output attached as input (cell 2 resumes the build; ~45 min) → expect ~27/40.
- **Leakage target (OOD-45 checker, pilot cell 6):** public 129 = 34% leaking (fastapi 42%, rich 17%, requests 54%);
  pilot issue texts 58%, PR texts 30% → choose PR/issue text per task to land at ~34% and the public style share.
- **User decisions (2026-10-20):** domains 80% matching public (web/API frameworks, terminal/CLI/text rendering,
  HTTP/networking; via GitHub topics) / 20% other; unfair-test tasks KEPT at ~public share (12%; label
  `unfair_names`, scripts/datasets/unfair_tests.py); option 2 = real PR texts mixed with issue texts; large tier ~10%.
  Public splits (data/splits_public.json, scripts/datasets/make_public_splits.py): val 16 (pilot#2 = gemma-val),
  test 16 (new), dev16 held out, train 52.
- **Still to build (after the pilot re-run):** full build notebook (several hundred tasks; gate ×3; domain buckets via
  GitHub topics; PR/issue choice to the leak target; dataset in OOD-45 layout incl. host-plugin wheels) → OFFLINE
  verification notebook (CPU, internet OFF, attaches only the dataset: re-gate, snapshot future-scan, fake-model
  end-to-end through real tools + our episode/sample builder; every sample must end with Gemma's thinking + final
  text) → final dataset PRIVATE, shared with the user's OTHER account (user 2026-10-21; generation there, 30 h) → generation (31B mix, thinking,
  2-3 samples/task at T1.0 — high run-to-run variance) → run filters (resolved, honest, located before edit, ≤2 failed
  calls in a row, near-duplicate calls, ≤~3 reads of one file, same files as gold, re-cap leaky/unfair) → train.
- **Eval yardsticks:** OOD-45 (12B base 61%: easy; compare variants only) and OOD-hard (24 tasks: 16 the 12B base
  failed + 8 solved; kaggle/cells_ood45_31b_hard, cells_ood45_12b_hard; `make_ood45_cells.py <31b|12b> hard`).
  31B OOD baseline postponed (quota). LB is 58 public tasks with ±3-task noise → judge changes locally.
- **Quota:** user's account ~2.8 h GPU left this week; other account 30 h for generation. CPU notebooks are free.
- **Cheap no-LoRA ideas (parallel track, from top public configs):** thinking_budget 4096 / max_output 8192 (ours
  2048/4096), batched independent searches in one command, parallel-implementations rule, git status+diff before
  submit — test on local sets, not single LB draws.

### NOW (2026-10-20 morning, read first; the log below is chronological history)
- **Goal:** win. Best LB so far = mix (31B, no LoRA) 0.17; LB noise ±0.02. Hidden test = ~120 tasks from PRIVATE repos.
- **Fine-tuning so far = imitation of open teachers (Qwen/DeepSeek/MiniMax trajectories) → does NOT beat the base:**
  - v1 (adapter_12b_v1, notebook 'finetuning'): val 1.093→0.572 but dev16 r1 0/16 (loops at T0.2, no edits).
  - v2 (adapter_12b_v2, notebook 'finetuning-v2'; thinking-first selection v2, reads rewritten to read_file):
    teacher val 1.350→0.819; Gemma val (Gemma's own pilot runs) ok 0.305→0.413 (v1 0.429), fail 0.263→0.340 (v1 0.352)
    = both drift ~35-40% from Gemma's successful style. 3-task check @T1.0 (notebook 'getting-started-...-new'):
    base 12B 1/3, v2 best 0/3, v2 final 0/3; v2 = no loops, uses read_file, but 2-4x more tool errors (bash chains).
  - Loops at T0.2 = sampling; T1.0 removes them. BUT our adapters use r16/alpha32 = scale 2.0, which forum 750713
    found causes loops/degeneration; alpha=16 (1.0) / 8 (0.5) at inference = cheap fix/interpolation (untested by us).
- **DECIDED NEXT (user 2026-10-19/20): self-distillation.** Research done (section "Self-distillation research"
  below). Proposed plan awaiting user go-ahead:
  1) OOD-45 eval notebook (Kaggle dataset rodrigospalma/ood45-bugfix-split + its tools/ood45_harness.py; 45 tasks,
     17 repos, public → friend's account): 31B mix (T0.2) + 12B base baselines = new yardstick (dev16 = weak proxy);
  2) same run: v2 adapter at scale 1.0 and 0.5 (edit lora_alpha in adapter_config.json);
  3) generation (user's account; competition data): 31B mix WITH thinking, 2 samples/task @T1.0 on ~84 gradable
     non-dev public tasks, request logger on → keep resolved, prefer fewest calls;
  4) train 12B on them (scale 1.0 i.e. alpha=r, lr ~1e-4, monitor val_gemma_ok, plateau stop);
  5) judge on OOD-45 vs 12B base and 31B; then 31B RFT or submit 12B.
  STATUS 2026-10-20: user said go. Steps 1-2 BUILT (scripts/train/make_ood45_cells.py 31b|12b →
  kaggle/cells_ood45_31b = mix31 T0.2, conc 4, stop new tasks after 4h; kaggle/cells_ood45_12b = base12 / v2 final at
  scale 1.0 (alpha 16) / 0.5 (alpha 8), all T1.0 top_k 64, conc 6, 132 jobs, stop after 5h). Runner = author's notebook
  (rodrigospalma/ood45-evaluate-your-agent, saved in research/raw/kernels/ood45/): one Evaluator per (variant, repo),
  evaluate_task per job, g1 statements, urllib3_5279 skipped, competition data attached (sandbox setup.py + tasks_path,
  as author). Local fake end-to-end sim passed both (real ood45_harness + swegemma 0.2.7; fake vLLM/evaluate_task).
  Untested on Kaggle: real sandbox installs (author-validated on 0.2.11) and 31B with LoRA on at util 0.80 (author's).
  The 12b notebook needs the v2 training output attached → user's account; 31b can run on the friend's account.
  OOD-45 must NEVER become training data (it is the yardstick). How it was built (for our own task mining): one
  contributor's 64 merged PRs → 57 with tests → 52 fail-on-base/pass-with-fix 3/3 → 45 pass the harness Docker gate
  (verify_task, net off) on 2 platforms → statements rewritten as user reports (leakage checker) → executed repro
  scripts; per-repo offline wheel sets (2 GB) so it runs in a Kaggle notebook.
- **LEADERBOARD RESEARCH (2026-10-20; notebooks saved in research/raw/kernels/lb_top/):** top 0.24 (3 teams), 0.22 x7,
  us 0.17. **The public LB = 58 tasks (1 task ≈ 0.017; private = the other ~58)** (dmitriigluzdov "Public Agent Ideas
  and Evidence": the only K in 30-130 matching every displayed score). **Identical files score 7-13 of 58 (0.12-0.22)**
  across runs (budget-aware files: 13, 11, 9, 7, 7; budget-fit reference 8-11 over 7 runs, mean ~10) → 0.24 = 14/58 is
  inside the noise of the ~10/58 configs; our 0.17 = 10/58 ≈ the family mean. All top public configs are NO-LoRA
  single agents of the "budget-fit/budget-aware" lineage: 31B, T0.2, top_p 0.95, max_output 8192, thinking_budget
  4096, 8 min / 28 calls / 80 turns / 240 s; prompt: literal spec extraction, call plan (edit by call 12, verify
  13-20, submit), batched independent searches in ONE run_command, ~40-line region reads (<=3 per command), edit
  recovery (re-read → heredoc python replace after 2 edit_file misses), parallel implementations (sync/async,
  __all__), protected pytest.ini/conftest, `git status --short && git diff` before submit, graph tools declared but
  forbidden. 0.24 notebook (honghanhhh) = budget-aware + those last 3 edits. Measured by others: T0 / 0.4 within noise;
  **12B with the same files EXCEEDED the 12-hour limit → no score** (time/task binding: 116 tasks × 8 min = 15.5 h if
  all ran to the cap); local 31-task screen: prompt variants all within noise (sign test p=1). IMPLICATIONS: single LB
  submissions cannot detect gains of 1-3 tasks → judge with our own large local sets (OOD-hard, dev16, test16, and the
  rebench tasks from unseen repos); any 12B submission needs a sequential timing check (shorter cap).
- **OOD-45 12B RESULT (2026-10-20, kaggle/cells_ood45_12b, T1.0, 44 tasks, data/results/2026-10-20_ood45_12b):**
  base 27/44, v2 LoRA scale 1.0 23/44, scale 0.5 23/44 (scale does not matter). Paired: base-only 7 vs s1.0-only 3,
  base-only 8 vs s0.5-only 4 (sign test p≈0.34: direction consistent, not significant alone). CLEAR damage: runs with
  one identical call repeated ≥10× (loops): base 0, s1.0 5, s0.5 6 (up to x51); tool-budget endings only with LoRA.
  High run-to-run variance at T1.0: 33 tasks solved by some variant, only 14 by all → several samples per task in
  generation. OOD-45 is easy for Gemma (12B base 61%): compare variants, not with dev16/LB.
  **ROOT CAUSE of the LoRA loops (traces, 2026-10-20): ALL 11 loop runs repeat `submit_patch` (x11-x51)** after a
  successful submit: the model thinks "Done." and calls submit again instead of ending. Stage B wrote the teacher's
  final turn as visible text "Patch submitted." WITHOUT thinking, while every other training turn = thinking + tool
  call → the model learned "after thinking comes a tool call" and never "think, then end". The base ends with a
  thinking turn and then a final text. LESSON for self-distillation data: keep Gemma's own real ending (thinking +
  final text after submit_patch) in every sample; the offline verification must check each sample ends that way.
  **Second LoRA habit = failing-retry streaks (burns the tool budget):** calls 1,038 base / 1,356 s1.0 / 1,302 s0.5;
  failed 16% / 20% / 19%; runs with >=4 failed calls in a row 2 / 7 / 10; near-copies of one failing command (e.g.
  `python3 -c 'from fsspec...'` 9x, 7 failures in a row) and re-reading one file in slices (12x). Selection v2 only
  caught IDENTICAL repeats. Run filters for self-distillation: near-duplicate calls (same tool + command stem / same
  file), <=2 failed calls in a row, <=~3 reads of one file. → teacher data dropped;
  self-distillation (option B) is the path. 31B OOD baseline postponed (quota).
- **OPTION B DATA (user decisions 2026-10-20; data must be clean before ANY generation GPU time):** source =
  nebius/SWE-rebench (CC-BY-4.0) tasks, our own build + gate (scripts/datasets/rebench_funnel.py → 2,589 candidates:
  core ≤130 lines/≤6 files/difficulty ≤2 + large 131-500 lines; nothing >500; excludes public + OOD-45 repos).
  Public splits (data/splits_public.json): val = pilot#2 16 (gemma-val), test = 16 new, dev16 held out, train 52.
  Distribution targets = the public 129: **domain 80% matching (web/API frameworks, terminal/CLI/text rendering,
  HTTP/networking) / 20% other ("surprises")** via GitHub topics; task kind; patch shape (already 68/32 vs 66/34);
  size tiers (~10% large); **text = PR title+description vs issue mixed to the public style share, leak share matched
  to the public share** (measured with OOD-45's checker, pilot cell 6) and re-capped after generation (leaky tasks get
  solved more). **Unfair tests KEPT (user reversed "drop" the same day), at about the public share** (tests need a
  name the fix creates and the text never mentions: scripts/datasets/unfair_tests.py: public 12%, candidates 8%;
  measured against the chosen text; label each task `unfair_names` so runs can be analysed / re-capped). Clean-task checks:
  gold PASS/empty FAIL ×3 offline (internet OFF notebook attaching only the dataset), snapshot has nothing after base,
  all wheels incl. host pytest plugins in the dataset, fake-model end-to-end run through the real tools + our
  episode/sample builder. Clean-run checks: resolved, honest (no reads outside /workspace, no test edits), located
  before editing, no loops / repeated failed calls, thinking every step (selection v2 rules), same files as gold and
  similar size, ≤2 distinct runs/task. Generation on the user's other account (30 h) → final dataset private, shared with that account (user 2026-10-21).
  Pilot (40 tasks, CPU, cells kaggle/cells_rebench_pilot, scripts/datasets/make_rebench_cells.py) running 2026-10-20.
- **Tooling ready:** stage B (scripts/datasets/stage_b.py, --rewrite-reads), episode features/selection v1/v2,
  build_samples.py, train_sft.py (data parallel 2x2 GPUs, --extra-val, --score-adapter, --monitor, --evals,
  --early-stop-patience, best checkpoint, auto-resume, 40-min NCCL timeout), gemma_runs_to_episodes.py (our own
  harness request logs → stage-B-style episodes/val), compare_behaviour.py, explore_stricter.py, diag cell
  generators (make_diag2_cells.py diag2/diag3), eval cells (make_eval_cells.py), sim_stage_b_notebook.py.
- **Kaggle notebooks (user ziad23samer):** getting-started-gemma-4-developer-agent-4554ae (stage B v1+v2 outputs),
  finetuning (v1 adapter), finetuning-v2 (v2 adapter), getting-started-...-new (diag3), tokenizer (features),
  dataset-loader-test(-2)-resume (stage A episodes). Private dataset 'gemma-val' (samples_all.pt; competition-derived).
- **Working rules learned (also in memory):** audit crash paths before any GPU handoff; verbose per-step logs; give
  cells as file links; one notebook run has everything; fetch only small files; 2 GPUs per 12B copy (skip 1-GPU
  probe); monitor Gemma's resolved runs (val_gemma_ok); Save & Run All is fine (I fetch outputs myself).

### HISTORY: WHERE WE WERE (2026-10-18 evening)
- **Sandbox flags DONE (notebook 'tokenizer'):** data/results/2026-10-18_flags/flags.jsonl.gz: 9,237 of 26,945
  episodes flagged (34.3%; outside_workspace 7,992, package_install 1,862, network 53, privileged 49; spot check:
  almost all real). Selection v1 re-run without them (pool 8,866 episodes / 3,924 tasks) and now with 2x RESERVE
  candidates (train 1,000, val 100; val repos incl. reserves never in train) + quotas (train 325 bug / 65 feat / 35
  enh / 75 other; val 32/6/4/8) → data/selection_v1.json.
- **Stage B BUILT (commit 02f9d13), Kaggle run pending (user):** scripts/datasets/stage_b.py replays episodes through
  the real harness: competition compiler + ADK Runner + harness plugins + build_agent_prompt + per-episode
  EventsCompactionConfig (14336/5/2/5). Fake vLLM (local HTTP, episode named in the model id `stage-b-ep<N>`) answers
  with the teacher's step and the exact prompt token count (our renderer; checked against vLLM /tokenize in the
  trial) so compaction happens exactly as on the scorer; no-tool calls (ADK summaries) go to the real 12B. Harness
  tools run on a FakeSandbox returning the teacher's recorded output (exit code from the OpenHands trailer /
  mini-swe-agent JSON; files rebuilt from `cat -n` views and edit snippets) → our JSON, 5,000/150/10,000 limits,
  budget warnings. Decisions taken while building (tell user / revisit): (1) episodes where the teacher's next 2
  steps use a name seen only in output our limits would cut are skipped (24% locally) and replaced from reserves,
  instead of training on unseen content (option --limits full exists); (2) the teacher's visible text before a tool
  call becomes its thinking if it had none, else dropped (Gemma wrote no visible text in 13,557 pilot calls); (3)
  bad view ranges / steps > 4,096 output tokens skipped; ~25% of teacher steps have no thinking (kept).
  Local dry run: all 281 locally available usable candidates OK (fake summaries), notebook flow simulated end to end.
  Kaggle: kaggle/cells_stage_b/cell1..5 (regenerate with scripts/datasets/make_stage_b_cells.py), GPU L4x4,
  inputs: competition + google/gemma-4 12B + dataset-loader-test-resume + dataset-loader-test-2-resume. Cell 4 runs
  a ~30-episode trial, checks it (all ok, tokenize exact, tool docstring indentation like the pilot (warning only),
  summaries from the 12B) and continues to the full 550 only if clean. Output: stage_b_out/requests_<attempt>.jsonl
  (tagged episode_id/attempt; use only attempts with status ok in status.jsonl), report + sample for me:
  fetch with --file-pattern 'stage_b_report\.json$|status\.jsonl$|sample_requests\.jsonl$'.
- **Stage B DONE (2026-10-18, Kaggle notebook getting-started-gemma-4-developer-agent-4554ae, output kept there as
  the training input; small files in data/results/2026-10-18_stage_b/):** 550/550 ok (train 325/65/35/75, val
  32/6/4/8; val repos ∩ train repos = 0), 0 bad; trial checks all true (tokenize 40/40 exact vs vLLM, Python 3.12
  tool docstrings as in the pilot, summaries from the real 12B, ~34 s each). 338 compactions in 289 episodes
  (0:261, 1:243, 2:43, 3:3); agent calls median 17 (max 30); max prompt median 14.4k (max 17.4k). Request logs
  stage_b_out/requests_{4ad37c877820 (trial), 00610eaebcc4 (full)}.jsonl, 343 MB, records tagged episode_id/attempt.
  Teachers: DeepSeek 434, Qwen-Flash 68, Qwen-27B 47, MiniMax 1. ~18 min replay after vLLM (L4x4).
  Skips among candidates: cut output 254, unreadable read_file 60 + edit/write 'OBSERVATION:'-prefixed ~30 (fixed
  after the run, bbbf3e9; quotas were filled anyway), bad view ranges 31, /tmp paths 3, >4,096 tokens 2.
  Whole-corpus replay check (kaggle/cells_stage_b/replay_check_cell.py, CPU) pending.
- **12B training notebook BUILT (kaggle/cells_train_12b, generated by scripts/train/make_train_cells.py):**
  build_samples.py: per episode, model calls form segments (each prompt = previous prompt + reply + tool output,
  checked char-exact; a compaction starts a new segment) → one sequence per segment, labels = the model's replies
  incl. its stop token (<|tool_response> after tool calls, <turn|> after the final message; the template's trailing
  newline excluded); summary calls not trained. Sample check: 3 episodes → 4 segments, 13–31% of tokens trained.
  train_sft.py: data-parallel LoRA (r16/α32, lr 2e-4 warmup 8 cosine→10%, clip 1.0, 1 epoch, 2 segments/copy/step,
  token-mean loss over the global step), validation loss at start/quarters/end, adapter + resumable state saved at
  each validation, per-step verbose line, --max-hours re-plans the schedule after 3 steps. Cell 4 measures whether
  one L4 holds a 12B copy on the longest segment (4 copies) else 2 GPUs/copy. Estimate before measuring: ~6M train
  tokens; probe speed ~130–150 tok/s per copy → ~3 h (4 copies) or ~6 h (2 copies); cap 6 h.
- **Then:** training data rendering + masking (loss only on model tokens), 12B training (data-parallel 4 copies
  to build; ~3.5 h/epoch est.), eval: fine-tuned 12B on dev16 ×2. **Success = 12B ≥ mix (4+3=7 over two runs)**;
  also measure calls/task, thinking/step, s/task. Thinking budget 2048 for this test; later more data + 4096.
- **12B SFT v1 TRAINED (2026-10-19, Kaggle notebook ziad23samer/finetuning; data/results/2026-10-19_train_12b_v1/:
  report.json, history.json, adapter_12b_v1_final.zip):** 887 segments (train 806 = 9.48M tokens, 2.05M trained;
  val 81). One 12B copy per L4 OOMs (21.9/22 GB, a 268 MB activation) → 2 copies x 2 GPUs, ~245 tok/s → 6 h cap =
  105 steps ≈ half an epoch (4.9M tokens). **Val loss (all 81 segments): start 1.093 → final 0.572 (−48%)**; mid-run
  (24 segments) 0.633 / 0.584 / 0.567 / 0.562. Train loss avg 1.28 → 0.68; grad spikes clipped. 6.3 h wall.
  First attempt hung at step 25 (copies re-planned the time budget separately) → fixed e32ceec (rank 0 decides,
  40-min timeout + auto-resume, checkpoints every 10 steps). Adapter validated locally with the official
  discover_adapters/compile_submission (rank 16, agent → openai/sft_v1, 125 MiB).
  **NEXT: dev16 x2 eval** kaggle/cells_eval_12b_sft (scripts/train/make_eval_cells.py = cells_12b_base + adapter;
  inputs: competition, 12B model, finetuning notebook output). Success = ≥7 over two runs (mix 31B 4+3; 12B base
  2+1). Speed ideas for next training: fit one copy per L4 (~2x), smaller mid-run val (done).
- **12B SFT v1 dev16 r1 = 0/16 (2026-10-19; base 12B 2/16):** stopped after pass 1. Every finished task: NO edits;
  "exceeded turns budget" = used the 28 tool calls then kept calling (harness checks the tool budget only between
  rounds) → explores, never commits to an edit; others timed out with no edit. Diagnostic next: kaggle/cells_diag_12b_sft
  (interactive; rich_3882 [base solves], fastapi_14258, fastapi_15589; one at a time; request logger; cell5 digest).
- **SFT v1 diagnosis (trace fastapi_15589, 2026-10-19):** thinking collapsed to one-line narration, the SAME sentence
  72x; same grep on a nonexistent path 20x despite "No such file" (it had seen tests/ earlier); teacher OpenHands habits
  (cd /workspace &&, find, sed -n of 3 files) replaced the mix workflow; never edits; keeps calling after budget.
  Base 12B on the same tasks: varied thoughts, max same call ≤12 (mostly ≤3), some edits. Causes (likely): thin
  teacher thinking (+ text→thinking merge) taught narration not reasoning; filters removed every error/recovery
  example (repeated_commands==0, error_rate≤0.2); lr 2e-4 x105 steps drifted from base + mix prompt. Low val loss =
  imitation, not skill. Cheap test next: kaggle/cells_diag2_12b_sft (final@T1.0, step_26@T0.2, step_26@T1.0, 3 tasks,
  summary table). Then v2 data: require real thinking per step, keep recovery episodes, lighter training.
- **Diag2 (2026-10-19):** T0.2 loops for any checkpoint (max same call 77/50); T1.0 escapes (repeats ≤2), final@T1.0
  1/3 (rich_3882, base solves it too), step26 not better → sampling caused the loops; data causes the weak style.
  User decisions: v2 = THINKING FIRST (same rules for all teachers; result mostly Qwen); eval fine-tuned models at T1.0.
- **Gemma's own runs as VALIDATION only (user):** scripts/train/gemma_runs_to_episodes.py splits pilot #2's request log
  (mix 31B, 16 non-dev tasks) per task → data/results/2026-10-19_gemma_val/ (local, competition data): val_gemma_ok
  (7 resolved) + val_gemma_fail (9), 31 segments. Score base / v1 / v2 on them in the next GPU run.
- **Behaviour comparison (scripts/train/compare_behaviour.py):** Gemma resolved runs use read_file 20% with ~21-line
  reads, git grep, no whole-file cat, no long chains, think 102 chars/call (failed: 54); teachers use run_command
  89-100%, read_file 0%, 68-90-line reads, chains 17-22%. v1 trained Gemma AWAY from its successful style.
  → v2 also rewrites simple teacher reads into our tools (sed -n a,bp / short cat → read_file with the same text).
- **Selection v2 (2026-10-19, scripts/datasets/select_v2.py → data/selection_v2.json):** full-corpus features
  (Kaggle notebook 'tokenizer' → data/results/2026-10-19_features/features.jsonl.gz). Strict rules left 828 episodes /
  639 tasks; relaxed to ≤20% steps without thinking + ≤1 output over limits → pool 1,715 / 1,259 tasks. Picks: train
  482 (other 57/75), val 50 (50 repos), 636 train reserves; thinking median ~825 chars/step; 47% with a recovered
  error; teachers Qwen-27B 208, Qwen-Flash 181, DeepSeek 90, MiniMax 3. Stage B v2 cells: kaggle/cells_stage_b_v2
  (make_stage_b_cells.py v2: --rewrite-reads, output stage_b_v2_out); local sim 230/230 ok.
- **Training v2 notebook (kaggle/cells_train_12b_v2, make_train_cells.py v2):** stage B v2 data; extra validation
  val_gemma_ok / val_gemma_fail (Gemma's pilot #2 runs, data/results/2026-10-19_gemma_val/samples_all.pt → PRIVATE
  Kaggle dataset, validation only) at start + end; v1 adapter scored on all validation sets first (--score-adapter);
  plateau early stopping (8 mid-run validations on the same 24 segments, stop after 2 without ≥0.005 improvement,
  rank 0 decides) + 'best' checkpoint. Tested on CPU incl. 2 copies (both stop together).
- **Stricter-style exploration (scripts/datasets/explore_stricter.py, 2026-10-19):** filtering cannot reach Gemma's
  style: chains ≤5% of calls → 254 eps/236 tasks; + no whole-file cat → 120/112; + edit_file-only → 50/49 (style then
  matches Gemma: read_file 21%, chains 0%, edit 9%). v2 picks after read rewrite: read_file 14% (Gemma resolved 20%),
  chains 15% (0%), reads 71 lines (21), think 185 chars/call (102). NEXT ROUND idea: split chained commands at the
  teacher's own `echo "=== x ==="` separators (411/800 chains in v2 picks splittable) into separate calls; leave
  sed -i edits (regex, unseen content). Decide after v2's val_gemma_ok + 3-task check.
- **v2 RESULT (2026-10-19, finetuning-v2 + diag3 'getting-started-...-new', data/results/2026-10-19_diag3/):**
  training 96 steps (no plateau stop, monitor was teacher subset): teacher val 1.350→0.819 (v1 0.833);
  val_gemma_fail 0.263→0.340 (v1 0.352); **val_gemma_ok 0.305→0.413 (v1 0.429)** = still drifts ~35% from Gemma's
  successful style. 3-task check @T1.0: base 12B 1/3 (rich_3882), v2 best 0/3, v2 final 0/3 (v1 final 1/3 earlier).
  v2: no loops, uses read_file ranges (rewrite worked), but 2-4x more tool errors than base (teacher bash chains with
  broken quoting). CONCLUSION: teacher-imitation SFT does not improve the 12B in our harness. Options: self-distillation
  on Gemma's own resolved runs (check rules on training with public tasks first) or back to agent/prompt/sampling work
  on the 31B (untested: 31B @T1.0).
- **NEXT (user 2026-10-19): self-distillation.** Start by researching the competition rules + forum: may we train on the
  public tasks (and which: non-dev only, to keep dev16 clean)? risk of overfitting the leaderboard? Then design: run the
  31B (mix, several samples per task, T1.0?) on graded tasks, keep only resolved runs (request logger → stage-B-style
  episodes via gemma_runs_to_episodes.py → build_samples), train the 12B, check on dev16 + val_gemma_ok.
- **Self-distillation research (2026-10-20):** (1) public 129 tasks = official "training set", patches given "for local
  training" → training on them is allowed. (2) Hidden test (~120) = "curated from a set of PRIVATE repositories" →
  must generalize; dev16 (fastapi/rich) is a weak proxy. (3) Forum 750713 (icfoer): self-distilled 31B LoRA looped at
  r16/alpha32 (scale 2.0 = OURS); alpha 16 (1.0) no loops, alpha 8 (0.5) safest interpolation; alpha is applied at
  inference (adapter_config.json) → re-test our v2 at lower scale without retraining; their data had NO thinking →
  base 8/11 vs LoRA 7/11. (4) OOD-45 (forum 750573, Kaggle dataset rodrigospalma/ood45-bugfix-split): 45 post-release
  bug fixes, 17 other repos, swegemma format, Kaggle runner installs deps (gold 44/45), CC-BY/MIT → main yardstick.
  (5) Forum 748051: nobody has clearly beaten base with LoRA; LB ±0.02 noise.
  PLAN proposed: 1) OOD-45 baseline 31B mix + 12B base (friend's account, public data); 2) v2 adapter at scale 1.0/0.5
  on OOD-45; 3) 31B mix with thinking, 2 samples x ~84 gradable non-dev public tasks, T1.0, logged → resolved runs;
  4) train 12B (scale 1.0, gentler lr, monitor val_gemma_ok); 5) judge on OOD-45; then 31B or submit 12B.
- **For the FINAL 31B data (user 2026-10-18): drop tasks the model already handles, keep the ones it fails.** We
  cannot run teacher tasks' tests on Kaggle (no Docker, no internet on GPU), so measure difficulty as the BASE 31B's
  loss on the teacher's replies (forward pass only; instruction-following-difficulty / Superfiltering idea, cited
  from memory, verify): replay a larger pool (~1,500) in stage B, score every episode, drop the easiest ~30-40%
  (not only the very hardest: extreme loss is often teacher noise), keep category quotas. One GPU notebook: replay +
  score + select + train. Not for the 12B test run.
- **Later:** 31B adapter (relay across sessions/accounts, public data only on the friend's account); le with 2 role
  adapters as an ablation (needs plan synthesis between locator and editor); CoderForge tasks run by Gemma itself.
- **Kaggle run rules (user):** every run self-contained with all outputs saved as it goes; trial first, then full;
  give exact cells + inputs; fetch outputs with --file-pattern to spare the user's internet.

**Pilot #2 result (2026-10-18, data/results/2026-10-18_datagen_pilot2/):** mix 31B 7/16 on the 16 gradable non-dev
tasks (fastapi_14786, 14492, 12942, 14372, 14349, rich_3905, 3518). Checked: submission identical to submissions/mix;
no command touched site-packages/git history//usr//kaggle; 14786's fix is written in its task text, 14492 is a
one-word docs fix, 14372/14349 share 0 lines with the reference. NOT comparable to dev16/LB (different, easier task
set; grading now works). Request log: 712 requests, all render to vLLM's count: diff -1 on the 696 with a system
message, exact (0) on the 16 without → vLLM adds one token in the system turn (probe cell 4 /tokenize will say which).

**vLLM adapter check PASSED (31B, 2026-10-18, data/results/2026-10-18_vllm_adapter_31b/):** base "Since you haven't
told me…", base+adapter "The secret word is PINEAPPLE-42.", both still answer 42 → train-in-4-bit → vLLM works end to
end; v_proj missing on the 10 global layers is fine. **The +1 token found:** vLLM passes message text as OpenAI
content parts; with list content Gemma's template adds a space before the system turn's <turn|>. render_traces now
does the same → all 712 pilot-#2 requests render EXACTLY (0 diffs). Largest prompt in the pilot: 16,210 tokens
(compaction keeps prompts ≤ ~16.2k) = the 31B's measured training limit (16k fits, 24k OOM).

**Shape survey (2026-10-18, data/shape_survey.json):** Open-SWE-Traces thinking teachers, Python+resolved+clean and
≤28 tool calls = **24,918 runs** in 169/171 files (DeepSeek-V4-Flash 9.4k, Qwen3.8-Flash-Next 7.3k, Qwen3.8-27B 7.7k,
MiniMax 0.55k — MiniMax runs are long). **Stage A trial OK (data/results/2026-10-18_stage_a_trial/):** 1 file →
253 episodes, 253/253 with issue text + workspace tree (Kaggle's locale sorts like the harness), 200 s/file. Thinking is
LONG: median 22k chars/run, longest step median 6k chars (mix allows 2,048 thinking tokens ≈ 8k chars/step) → rank/cap
before training. env metric fixed (env_confusion: site-packages/installed copy/sys.path talk; 97/253 zero). Full run:
2 CPU notebooks in parallel, SHARD '0/2' and '1/2', MAX_FILES 0 (~5 h each).

**Decisions (user, 2026-10-18):** (1) mix first: 12B adapter, then 31B; le with 2 role adapters later as an ablation.
(2) Thinking budget is OURS (mix sampling.yaml 2048; competition allows 0–32768, default 4096): 12B test keeps 2048 and
trains only on runs whose every step thinks ≤2048 tokens (61% of the trial); later try more data + budget 4096.
(3) **12B success = fine-tuned 12B ≥ mix (31B, no LoRA) on dev16**: mix scored 4/16 and 3/16 → run the 12B twice;
equal or better = success (then consider submitting it while the 31B trains). Baseline 12B: 2/16, 1/16.
(4) Gemma barely thinks now (pilot #2: median 28 output tokens/call, 59–80 calls on many tasks) vs teacher ~20 steps,
~109 tokens median/step → expect training to cut calls; measure calls/task, thinking/step, s/task with the score.

**Stage A COMPLETE (2026-10-18):** 171/171 files, 117,467 runs seen, **26,945 episodes** (DeepSeek-V4-Flash 9,467,
Qwen3.8-27B 8,804, Qwen3.8-Flash-Next 7,976, MiniMax 698), in Kaggle outputs dataset-loader-test-resume (shard 0) and
dataset-loader-test-2-resume (shard 1). KEEP ALL (user): selection only writes an id list. Selection step 1 = Kaggle
export cell kaggle/cells_stage_a/export_stats_cell.py → stats.jsonl.gz (exact Gemma token counts, quality, same-task
similarity). Trial: estimated whole-run size median ~22k tokens (+ system prompt) → MOST runs need compaction (stage B).

**Selection v1 (2026-10-18, scripts/datasets/select_v1.py → data/selection_v1.json; stats from Kaggle 'tokenizer'
notebook = data/results/2026-10-18_stats/stats.jsonl.gz, 26,945 rows / 7,364 tasks):** filters: every step ≤2,048
thinking tokens (19,128) + env_confusion ≤2, no repeated commands, error ≤0.2 (10,302) → one best run per task
(4,397; DeepSeek 75%, kept as is — user) → **train 500** (312 repos, ~7.6M tokens) + **val 50** (50 repos NOT in
train); categories matched to the competition (user): 65% bug fix, 13% feature, 7% enhancement, 15% other. All 26,945 episodes kept for later selections.

### Leaderboard (all no-LoRA unless noted)
| submission | LB | notes |
|---|---|---|
| **mix** | **0.17 (best)** | bf (public Budget-Fit) prompt/tools + r4 decision rule; T0.2, thinking 2048, out 4096; 8 min/28 calls/80 turns |
| r4_budget | 0.15 | T1.0, thinking 512 |
| le5 | **Notebook Timeout** (>12 h) | locator→editor; dev projection 11.6 h was not enough |
| le6_t6 | 0.15 | le6 with 6-min cap; finished in time; reader skill install works on the scorer |
| bf + noise LoRA (friend's account, public bundle) | **0.01** | **LoRA takes effect on the scorer** (server starts, outputs change) |
Identical packages vary ±0.02 on the LB; ±1 task per 8–16 on dev. Runtime: every config sits near the 12-h edge
(scorer slower than dev projections) → keep mean per task well under ~330 s or cap time (6 min).

### Prompt/architecture work is DONE (plateau)
Dev v2 (16 tasks): mix 4,3; bf 4; le5 4; le6 4 (full 16 = rung-3l+3m); 12B mix 2,1. Everything solves the same core
(fastapi_15589, rich_3882, fastapi_11194 + one of rich_3521 / fastapi_14419). Bottleneck = **correct** edits.
Lessons (experiments/2026-10-13_dev16/notes.md, rung-3a..3m): working scratch scripts double experimenting and hurt
(mix's write_file-/tmp refusal is a hidden brake); skill scripts with nested args get garbled by the tool-call
format (flat run_command strings don't); agent_tool calls are not budget-counted but the editor's edit_file is;
locators read until the budget ends unless a tool refuses (le6's .git/agent/read.py reader + plan inside the editor
request fixed hand-off: no-edits 4→2, score unchanged). 12B: decodes 2x faster but writes 2x more tokens, no-edit
9/16 → target for LoRA. Only event-triggered signals in tool output change behaviour.

### NOW: fine-tuning pipeline (debug on 12B, final on 31B)
1. **Pilot + gold check results (2026-10-17, data/results/2026-10-17_datagen_pilot/):** mix 31B solved 3/16
   (fastapi_14372, rich_3905, rich_3518). Gold check v1: only **38/113 gradable** (rich 33/41, fastapi 5/58,
   requests 0/13, httpx 0/1). Cause = test deps missing from the public wheels (dirty_equals etc.; same on the GPU
   run, NOT Python 3.13); the sandbox venv uses the notebook's site-packages (system_site_packages=True), so
   pip-installing them fixes grading. **Request log lost:** browser download unpacked the multi-block .gz → 1 record
   (it renders to vLLM's count -1; HF's template gives the identical text, so vLLM adds 1 token, probably a 2nd BOS;
   probe cell 4 now asks vLLM /tokenize). Logger now writes plain requests.jsonl; cell 5 puts it in results.zip.
   **NEXT (user):** CPU session, INTERNET ON: cell1_cpu, cell2, **gold_check_v2.py** (installs missing test deps in
   rounds, re-grades, writes gold_check.json + test_deps.txt + **test_deps_wheels/** = the same packages as py3.12
   wheels). GPU sessions have NO internet (Kaggle): attach the gold notebook's OUTPUT as an input; cell2b installs
   from it offline. Then re-run the pilot (cells 1, 2, **2b**, 3 = 31B, 3b, 4, 5) to capture the request log.
   **Gold check v2 result:** 44/113 usable (fastapi 11/58, rich 33/41, requests 0/13, httpx 0/1). Left: 42 fastapi =
   Kaggle's Starlette 1.x (Router(on_startup) removed) → **cell2c_pin_task_deps.py**: after each sandbox setup,
   installs into THAT sandbox (pip --target venv site-packages) the newest competition wheel satisfying the task's
   pyproject spec (verified locally: Starlette 1.6 host → fail; with hook → pinned 0.50.0 → PASS); 12 requests =
   missing pytest-httpbin plugin → added to gold check (installed with only-missing deps; py3.12 wheels verified).
   Order — gold (CPU, internet): cell1_cpu, cell2, cell2c, gold_check_v2. Data-gen (GPU): cell1, cell2, cell2b
   (attach gold output), cell2c, cell3, cell3b, cell4, cell5.
   **Gold check final (data/results/2026-10-17_gold_check_v5/): 84/113 gradable** (fastapi 51/58 with cell2c,
   rich 33/41, requests 0/13, httpx 0/1). requests: on Kaggle the pytest-httpbin plugin is not picked up (fixture
   recursion; not reproducible locally, where it loads) and on Python 3.13 its HTTPS tests fail certificate checks
   anyway → requests excluded for now. test_deps_wheels/ (20 wheels) is in that output → GPU notebook input.
   Pilot task list now = 16 gradable tasks (4 requests + rich_3782 swapped for fastapi).
   Later: CoderForge tasks run by Gemma itself (user idea: pick 3–5 SWE-Smith repos with many easy tasks; quota
   allows ~340 attempts/week → ~70–100 successes/week; start by counting tasks per repo).
2. **Sample format (agreed with user):** one sample = one trajectory rendered with Gemma 4's chat template
   (data/gemma4_tokenizer/chat_template.jinja; whole run is ONE model turn; tool responses inside it; thinking kept
   after the last user msg; nudges are user msgs and drop earlier thinking); labels = -100 except model tokens
   (thinking + tool calls); split at compaction points. **Dedup (user rule):** successful runs only, cut after the
   first submit_patch; keep a 2nd run of a task only if its action sequence shares <~50% with kept ones or the patch
   differs; cap 2–3 per task; drop error-streak/looping runs. Possible extra filter: **Gemma judge** (31B grades each
   trajectory's reasoning; idea from CodeGemma's LLM post-filtering).
3. **Data sources (allowed):** (a) Gemma 31B successes on non-dev public tasks (→ 12B = distillation; little gain for
   31B itself per SWE-Gym's self-training result); (b) [REJECTED 2026-10-22, arXiv 2603.24472: runs generated while seeing the solution made the student far worse, AIME24 54.8→20.2] gold-guided trajectories (reference patch → ideal path, Gemma
   writes the reasoning) for tasks Gemma fails; (c) **nvidia/SWE-Hero-openhands-trajectories** (34k, CC BY 4.0,
   generated by Qwen3-Coder-480B, OpenHands format → map execute_bash→run_command, str_replace_editor
   view/str_replace/create→read_file/edit_file/write_file, finish→submit_patch; filter ≤28 calls/≤32k; unknown if
   filtered to resolved) — NEXT TO INSPECT (download one shard). Nemotron-SFT-SWE-v3 on hold (teacher models
   unstated). **(d) togethercomputer/CoderForge-Preview** (Together AI, 2026-02; user-found): 258k trajectories /
   51k tasks / 1,655 permissively licensed repos (R2E-Gym, SWE-Smith, SWE-Rebench; SWE-bench Verified overlap
   removed), ALL by Qwen3-Coder-480B (no big-3), OpenHands 0.52.1 tools (bash, str_replace_editor, think, finish),
   test-verified (155k pass; SFT used passing only), median ~38k tokens / ~50 steps (longer than our 28-call 32k
   budget → keep short ones). Qwen3-32B SFT on it: 59.4% Verified. Same conversion as SWE-Hero. **(e) nebius/SWE-rebench-openhands-trajectories**: 67k (32k
   resolved, `resolved` column), Qwen3-Coder-480B, OpenHands 0.54, CC-BY-4.0, avg 64 turns. Checked 2026-10-17 and
   NOT usable: thoughtworks/agentic-coding-trajectories (15k = 5k Nebius copy + 5k Claude-3.7 SWE-smith + 5k Kwai
   Klear with unstated teacher; `recorded_model` unreliable) → take Nebius from the original instead; ADP paper
   (arXiv 2510.24702, a format unifying 13 datasets; its SWE parts besides Nebius are SWE-Gym = GPT-4o/Claude and
   SWE-smith = Claude 3.7; useful only as evidence: Qwen2.5-Coder-32B SFT → 40.3% Verified). Sources (c)(d)(e) share
   teacher and scaffold → dedupe by task across them.
   **Web sweep 2026-10-17 (final source list, no big-3):** (f) **SWE-Lego** (HF SWE-Lego/SWE-Lego-Real-Data +
   -Synthetic-Data, `resolved` split; ~18k validated trajectories, Qwen3-Coder-480B + OpenHands, git history sanitized;
   Qwen3-32B SFT 52.6% Verified) = cleanest curated set. (g) **nvidia/Open-SWE-Traces** (CC BY 4.0; v1.0 openhands
   84k + sweagent 67k from MiniMax-M2.5 [thinking] and Qwen3.5-122B; v1.1/1.2 mini-swe-agent from DeepSeek-V4-Flash,
   Qwen3.6/3.8-27B; `resolved` 1/0/-1, `language` → keep python; 9 languages). Rejected: SWE-Zero (execution-free,
   unverified), SWE-smith-trajectories + SWE-Gym (Claude/GPT), Kwai Klear (teacher unstated), thoughtworks.
   **Open-SWE-Traces survey (2026-10-17, scripts/datasets/survey_open_swe_traces.py):** Python + resolved + clean
   (not fastapi/requests/rich/httpx; only ~1% of swe-rebench rows dropped) WITH thinking = **117k**: Qwen3.8-27B 55k
   (mini-swe-agent 34k / sweagent 11k / openhands 9k), Qwen3.8-Flash-Next 34k, DeepSeek-V4-Flash 18k (openhands),
   MiniMax-M2.5 10k. Thinking off (skip): Qwen3.6-27B 58k, Qwen3.5-122B 6k. Thinking flag read from the first row
   of each folder. → Thinking data is plentiful; no need to backfill reasoning into Qwen3-Coder runs.
   **Decontamination scan (scripts/datasets/decontam.py, data/decontam_report.json, 2026-10-18):** drops every row
   from fastapi/requests/rich/httpx. Nebius 315/67k (httpx), SWE-Hero 73/34k, Open-SWE-Traces 674/678k (548 rich incl.
   textualize__rich-3006 = OUR task rich_3006; 126 httpx incl. an unrelated Go "httpx" = harmless over-blocking),
   CoderForge 644/413k (httpx), SWE-Lego 51/18k + 10/11k. No fastapi/requests rows anywhere. R2E-Gym ids
   (qingyangwu/<repo>_final:<commit>) now parsed (were 54k "unknown" in CoderForge).
   **Curation evidence:** SWE-Prime (arXiv 2608.27449): best 10% of resolved trajectories beats all of them (+24%
   rel. Verified) and loss only on useful segments; LoRA curation study (arXiv 2607.17205, Qwen2.5-Coder-7B on the
   Nebius set): error-retry rate is THE quality signal; quality filtering pays off from ~2k samples, below that
   quantity wins; SWE-Lego: mask the loss on failed steps (error masking) + easy→hard curriculum.
   **Thinking mismatch:** Qwen3-Coder trajectories have NO reasoning; mix runs with thinking on. Options: train with
   thinking off (faster agent), or prefer thinking traces (MiniMax-M2.5 in Open-SWE-Traces, Gemma's own runs).
   **Decontaminate:** drop any instance from fastapi/requests/rich/httpx PRs matching our 129 tasks. Optional: run Qwen3-Coder-30B-A3B (Apache) in our harness as a teacher (untested on the wheelhouse vLLM).
   Cross-family teacher → let Gemma rewrite the reasoning + mix sources (research: closeness to the student's own
   distribution matters more than family).
4. **Targets:** 12B pipeline debug 30–60 samples; first real 31B adapter 300–500 trajectories (SWE-Gym: 491 →
   +13.6 pts). 12B baseline to beat: mix_12b 2/16, 1/16, no-edit 9/16 (data/results/2026-10-17_12b_base_dev16).
5. **Training compute: Kaggle only (user: no money for rentals/APIs).** Filtering = code rules first (repeats, long
   read-before-edit, test-file edits, oversized patches, nudges); LLM judge later only if needed: Qwen3-Coder-30B-A3B
   on Kaggle (not Gemma: self-preference bias; not Claude/GPT: their terms bar using output to develop models).
   **Trainer = scripts/train/int4_lora.py (2026-10-17):** trains LoRA directly on the competition's 4-bit
   compressed-tensors checkpoint (packed int4 kept in memory, unpacked one layer at a time; transformers' own path
   decompresses the WHOLE model to bf16 = 62 GB for the 31B). Chunked loss (262k vocab) on labelled tokens only.
   Saves PEFT format (base_model.model.model.language_model.layers.N...). CPU test on a tiny Gemma 4 in the same
   format: scripts/train/test_int4_lora_tiny.py (outputs = transformers-decompressed exactly; loss = transformers';
   grads equal with checkpointing; PEFT loading the saved adapter = ours exactly in fp32). venv: data/venv_train
   (transformers 5.13.1, compressed-tensors 0.15.0.1 = wheelhouse versions, peft 0.21.2).
   **PENDING Kaggle probe** kaggle/cells_train_probe/ (cell1, cell2_int4_lora, cell3_probe, cell4_vllm_adapter; L4x4,
   12B first then 31B) → train_probe.json: sanity answer, peak memory/speed per length 2k→32k, a 30-step "secret
   word" training, and vLLM serving the adapter (vllm_adapter_check.json).
   **Probe #1 result (12B, L4x4, data/results/2026-10-17_train_probe/):** load 4 min, int4 weights read correctly
   ("17 + 25" -> "42"); ALL lengths fit up to 32k (peak 19.7 GiB/GPU at 32k; 10.2 at 16k); speed 84-154 tok/s
   (fwd+bwd, one GPU busy at a time). Secret-word training FAILED: lr 1e-3 diverged (0.002 -> 16.9), model then
   answered "" in transformers AND in vLLM (so vLLM did apply the adapter; base unaffected). Fixed: lr 1e-4, grad clip
   1.0, early stop. Ran the old cell 4 (no /tokenize check). Throughput is the real limit: 1k trajectories x 15k tok
   = 15M tok = ~30 h on the 12B at this speed -> needs data-parallel (12B fits per GPU) / speed work / fewer tokens.
   **Probe #2 (31B, 2026-10-18, data/results/2026-10-18_train_probe_31b/):** load 12.5 min, "42" sanity OK;
   secret word LEARNED in 9 steps (lr 1e-4 + clip; 4.62 → 0.002), answer "The secret word is PINEAPPLE-42.".
   Fits to 16k (18.1 GiB peak), OOM at 24k; 56–65 tok/s. Adapter 820 bf16 tensors, PEFT names = scorer-tested
   noise adapter; v_proj only on 50/60 layers (global layers share K=V) → whether vLLM accepts that is UNTESTED
   (cell 4 did not report; now runs standalone with the probe output attached).
   **Sample building rule (found 2026-10-17):** sample = the exact prompt the model saw + exactly what it generated
   (request logger records both); re-rendering a finished conversation is NOT the same text (thinking-off prompts
   end with an empty `<|channel>thought\n<channel|>` that the re-render drops).
### Tooling
make_kaggle_notebook.py (--tasks --configs --repeats --concurrency --model --log-requests --gold-tasks --gold-out
--out); pack.py; behaviour.py; speed.py; analyze.py; render_traces.py (trace or request-log → Gemma text + token
check); request_logger.py (+ test_request_logger.py: fake vLLM, passes); data/venv_harness = exact competition
harness (swegemma 0.2.11, adk_submission 0.2.13, google-adk 1.36.1, google-genai 2.11.0; LiteLLM version on Kaggle
unknown); data/gemma4_tokenizer = tokenizer + chat template. dist/: submission.zip = le6_t6; *_submitted.zip,
le6.zip, le5.zip, mix_lora_noise.zip, bf_lora_noise.zip.

## Context
Kaggle "Google – The Gemma 4 Developer Agent Competition" (Google DeepMind, Featured, $65k) + optional
Paper Track ($35k). Goal: turn `gemma-4-31b-it-qat-w4a16-ct` into an autonomous SWE agent that fixes Python
bug-fix / feature-request tasks offline. Working mode: learn + build, $0 compute (Kaggle only), both tracks.

## NEXT: Build rung 1a + 1b and compare — approved 2026-10-04
Goal: end-to-end loop (pack → local smoke test → Kaggle 31B 3-way comparison → first LB submission).

### Step A — Repo setup (P0)
- `scripts/fetch_data.py`: Kaggle API → CURRENT wheelhouse wheels (adk_submission 0.2.12 since Sep 30; skip
  Linux-only vllm/flashinfer) into `data/wheels/`; dev-subset snapshots + graphs/embeddings into `data/` (fix 0-byte
  graph/embedding files by hard-linking, forum 742911).
- `pyproject.toml` via `uv` (Python 3.13); install the wheelhouse wheels + their PyPI deps.
- Docker sandbox: `colima start`, build `swebench-sandbox:latest` from `data/docker/Dockerfile.public`.

### Step B — Submissions
- `submissions/1a/`: agent.yaml (one `executor`: run_command, read_file, edit_file, write_file, get_status,
  submit_patch + 3 graph tools), prompts/system.md, configs/sampling.yaml, eval_config.yaml.
- `submissions/1b/`: `orchestrator` (run_command for read-only checks, read_file, get_status, submit_patch, 3 graph
  tools, agent_tools reader/executor/verifier); sub_agents/*.yaml; prompts/{orchestrator,reader,executor,verifier}.md.
  Helpers: reader (run_command, read_file) → `LOCATION / EVIDENCE / FIX PLAN`; executor (+edit_file, write_file) →
  `CHANGED / CHECK`; verifier (run_command, read_file) → `VERDICT: PASS|FAIL / EVIDENCE / FIX`. All helper
  instructions include `{problem_description}`. Only the orchestrator submits.
- Prompt rules (both): one short progress line + one tool call per reply (text survives compaction); find the source
  package with `git ls-files` first; read ≤60 lines; notes in /tmp/notes.md; never repeat an identical command;
  read-only git; scratch only in /tmp; no literal curly braces except `{problem_description}` (ADK templating).

### Step C — Tooling (`scripts/`)
- `pack.py`: zip with agent.yaml at root; validate (ALLOWED_SUBMISSION_EXTENSIONS, MAX_SUBMISSION_SIZE_BYTES,
  validate_single_declared_model, compile_submission()).
- `eval_local.sh` + `configs/ollama.yaml`: `swegemma eval --sandbox docker` with the competition alias mapped to Ollama.
- `analyze.py`: ATIF-v1.7 traces → resolved, duration, output tokens, tool calls by name, compaction (prompt-token
  drops), nudges, repeated commands, helper calls + format compliance, failure buckets.
- `make_kaggle_notebook.py` → `kaggle/eval_compare.ipynb`: install wheelhouse FIRST, start vLLM once, run
  [sample without adapters, 1a, 1b] × dev tasks in one session, zip results per config.
- `experiments/<date>_<name>/`: config snapshot + summary + notes.md (paper log).

### Step D — Dev subset
- ~4 tasks first (fastapi_15588 + 1 more fastapi + 2 rich; NOT fastapi_15661, which needs a hidden module name,
  forum 745695), gold patch verified locally; grow to ~20.

### Verification
- pack.py validates + compiles 1a and 1b. Mac: 2 tasks each run without harness errors; `{problem_description}`
  renders (helpers too); top_k reaches the server; 1b helpers return text.
- Kaggle (one L4×4 session ≈ 1 h wall = 2 h quota): sample vs 1a vs 1b → analyze.py table → first LB submission.

## Findings 2026-09-27 → 10-04 (VERIFIED unless marked)
### Harness / ADK internals (source: swegemma 0.2.7, adk_submission 0.2.11, google-adk 1.36.1)
- Compile path: `compile_submission()` (adk_submission/compiler.py) → validate dir → discover adapters → `load_yaml`
  (`!include` relative to the INCLUDING file; .md/.txt as text, .yaml parsed) → schema → `compile_llm_agent`.
  `model:` alias → `LiteLlm(openai/<model>, api_base=vLLM)` (swegemma/models/registry.py); local override via
  `--models-yaml` with `models: {alias: {path, api_base, api_key}}`. Adapters are served as `openai/<adapter>`.
- `thinking_config.include_thoughts` → vLLM `chat_template_kwargs.enable_thinking` (resolvers/generation.py);
  `include_thoughts: false` = reasoning fully OFF (forum 745059). Since Sep 30, thinking_budget + seed are forwarded.
- `skip_summarization: true` → `Event.is_final_response()` is True → the parent's run ends right after the helper
  returns → harness nudge. → Keep the default (false) for all agent_tools.
- Nudges (agent_runner.py L499–730): a round = one ADK run (lasts while the model keeps calling tools). Round ends
  without submit → canned nudge (generic / thinking hit max_output_tokens / tool call cut off). max_nudges 3; the
  counter resets after a round containing a tool call; the 4th consecutive tool-less round ends the task. After the
  loop, an unsubmitted working-tree diff is captured (timeout, turn/tool limits) — but NOT after exceptions such as
  ContextWindowExceededError or an unknown tool name: those discard the patch (forum 744692, 745028).
- Context: the whole session history is re-sent on every model call (instruction re-rendered with state each time).
  Token-threshold compaction runs INSIDE a round in ADK 1.36.1 (`CompactionRequestProcessor`, before model calls):
  last prompt ≥ token_threshold → the same model summarizes all older events except the last 5; the summary keeps
  TEXT parts only (tool results lost). Threshold: 14,336 in README/host notebook; the scorer's value is disputed
  (forum 744692: at 32,768 it can never fire → overflow). No elision possible (no callbacks registered).
- AgentTool helpers (google/adk/tools/agent_tool.py): new in-memory session per call, empty history, input = one
  user message with the `request` string; parent state copied in → `{problem_description}` works in helper
  instructions; child state_delta written back; child history discarded; final non-thought text = tool result.
  No `output_schema` in the competition schema → helper output format can only be prompted and checked.
- `get_status` (free) returns tool_calls_used/remaining, max_tool_calls, time_seconds_remaining, max_time_minutes,
  agent_elapsed_seconds, max_turns, command_timeout_seconds, patch_submitted, patch_size — no token count.
- Session state: `problem_description` always; `hints` only for some tasks → never reference `{hints}`.
- Limits (swegemma config.build_submission_limits): max_agents 500, sub-agent depth 50, skills 1,000;
  generation fields incl. top_k allowed; max_output_tokens ≤ 32,768. Only custom code path = skills.

### First real 31B run (2026-09-27, Google sample, OLD wheelhouse, thinking on, temp 0.2, 5 min / 100 tools)
- Both tasks (fastapi_15661, fastapi_15588) timed out with no edits (13 tool calls each). Decode ≈ 24–25 tok/s →
  **5 min ≈ 6–7k output tokens per task**; thought text used most of it and re-derived the task every turn (thoughts
  were dropped between tool calls — fixed Sep 30).
- Compaction fired: prompt 15,812 → 5,884 tokens with a 34 s summarization gap; afterwards the agent re-read the
  same file. Compaction is not a separate event in the ATIF trace → detect via prompt-token drops.
- `search_similar_code` returned nothing useful; `git grep` found `fastapi/sse.py` in seconds.
- Kaggle pitfalls: run the wheelhouse install cell FIRST (Kaggle preinstalls another google-adk → pydantic class
  clash); a kernel restart does not kill the vLLM subprocess (GPUs stay full) → restart the whole session.
- Quota: L4×4 burns GPU quota at **2×** (2h38m for ~80 min; matches a search-result quote of Kaggle) → ~13.7 h of
  L4×4 per week ≈ 5–6 twenty-task runs. One vLLM start per session; stop sessions immediately.

### Gemma 4 (tech report arXiv 2607.02770, ai.google.dev model_card_4, prompt-formatting-gemma4)
- 31B is dense: 60 layers, 5 local : 1 global attention, sliding window 1,024, p-RoPE on global layers; native
  system role. Recommended sampling: temperature 1.0, top_p 0.95, top_k 64. Keep thoughts across tool calls,
  strip them between user turns. RULER 96.8 at 32k (bf16, no thinking).
- 12B vs 31B: LiveCodeBench 72.0 / 80.0, IFEval 97.2 / 98.9, Tau2 avg 69.0 / 76.9, Terminal-Bench Hard 18.0 / 36.0
  → 12B for plumbing only. Google publishes no SWE-bench number.

### Forum 2026-09-27 → 10-04
- Sep 30 wheelhouse fixed: thoughts kept between tool calls, single-JSON tool results (+ edit_file unescape
  fallback), thinking_budget/seed forwarded, LoRA KV cache sized dynamically. Our 09-27 numbers predate it.
- Open: compaction threshold on the scorer; undeclared/hallucinated tool → patch discarded (host "will implement
  something"); task-prompt workspace tree hides the source package in 115/129 tasks (745220); agents repeat the same
  command up to 69× (745774; more loops at temp 0.7 than 0.2 in one 10-task test); platform errors still burn daily
  slots. LB top 0.24 (several 0.17).

Sources pulled 2026-09-26 via Kaggle API (token in ~/.kaggle/access_token): competition pages (Overview,
Evaluation, Rules, Data, Model/Budget/Harness Rules, Timeline, Prizes), paper track pages, leaderboard CSV,
forum threads, public notebooks (incl. host's Getting Started), dataset file list, HARNESS_README.md,
tasks.jsonl, sample_submission. Gemma 4 sources in research/raw/gemma/ (2026-09-27).

## Competition facts (VERIFIED unless marked)
### Timeline & limits
- Main: final submission **Dec 2, 2026** 23:59 UTC; entry + team merge deadline Nov 25. Team size ≤5.
- **1 submission per day** (a failed run still burns the slot). Pick **2 final submissions**.
- Paper: **Nov 12, 2026**. Joined (verified 2026-09-26).
- Winners must open-source (OSI license, Apache 2.0) the solution + training code, reproducible write-up.
- **Competition data must not be redistributed** → keep `data/` out of any public git repo.
- External data/models allowed if public and free/cheap ("reasonably accessible to all").
  Distillation from proprietary LLMs (Claude/GPT) → **host answer pending** (forum 742807). Open-weight
  teacher models are the safer route. Also mind provider ToS.

### Scoring
- Per task PASS/FAIL (SWE-Bench-style). Score = fraction resolved. Kaggle truncates to 2 decimals.
- Hidden test set ≈120 tasks, split ~50/50 public/private LB. **Public LB = exactly 58 tasks** (forum
  743506 deduction) → **1 task ≈ 0.017**; LB is noisy — a 1-task change is noise.
- **Hidden test set is from PRIVATE repositories** (Data page). Public 129 tasks (fastapi 67, rich 48,
  requests 13, httpx 1) are only a dev set → optimise for generalisation, not these 4 repos.
- Test tasks were filtered so "a larger frontier model can pass the case or get within a single test".
- Verification: fresh container, apply patch (4 fallback strategies), reset any test/config files the agent
  touched, apply hidden test_patch, pytest target tests. Resolved iff exit 0, >0 passed, 0 fail/err, not skipped.
  Unsubmitted working-tree diffs are still extracted and scored.

### Runtime budget
- **12 h total** for all tasks (includes sandbox setup, excludes validation). Tasks run **sequentially**.
  Exceeding 12 h currently **errors the whole submission** (host plans to score unfinished as 0).
  → ~6 min/task average. Always set `max_time_minutes` as a failsafe.
- Scorer reads only 4 `eval_config.yaml` fields: timeout_seconds, max_tool_calls, max_time_minutes,
  max_turns. Default = no limit. `timeout_seconds` also bounds the Phase-2 pytest run → keep ≥180–300.
- Hardware: 4×L4 (96 GB), vLLM 0.19.1 (patched), TP=4, max_model_len **32,768**, gemma4 tool/reasoning parser.

### Leaderboard 2026-09-26 (348 teams, 613 submissions) — top 0.24 by 2026-10-04
- Top = **0.13** (8/58). Distribution: 0.13×4, 0.12×25, 0.10×30, 0.08×42, 0.06×54, 0.05×46 … 0.00×119.
- Best public notebook (romanrozen, coder + read-only code_analyzer, LOCATION/ROOT CAUSE/FIX PLAN format,
  temp 0.2) = 0.12; a direct fork scored 0.08 (noise!) and took 14.5 h wall clock.
- Many recent runs fail platform-side ("requested more CPU/GPU/TPU than available") — host is fixing.

### Submission format (ADK Agent Config, declarative YAML only)
- `submission.zip` with `agent.yaml` at root; optional eval_config.yaml, configs/, prompts/, sub_agents/,
  adapters/<name>/{adapter_config.json, adapter_model.safetensors}, skills/<name>/{SKILL.md, scripts/, resources/}.
- ≤3 GiB unpacked. Extensions allowed: .yaml .yml .md .txt .py(skill scripts) .json .safetensors.
- Agent classes: LlmAgent, SequentialAgent, ParallelAgent, LoopAgent; `agent_tool` for sub-agents
  (context isolation); `{problem_description}` available in instructions; one base model for all agents.
- Sampling: `include_thoughts: false` ⇒ thinking fully OFF; `thinking_budget` is NOT forwarded to vLLM
  (forum 743365), so with thinking on only `max_output_tokens` bounds reasoning. `thinking_level` should be omitted.
- Context compaction configured (threshold 14,336 tokens; interval 5 in README vs 15 in host notebook) —
  whether it actually fires is questioned (forum 743456). Design as if it doesn't: keep outputs small.

### Tools (9) + gotchas
run_command, submit_patch (free), get_status (free), read_file (≤150 lines/10k chars), edit_file (3-tier fuzzy
match), write_file, get_code_neighbors, search_similar_code (takes a SYMBOL name, not natural language),
get_code_subgraph; plus skill helpers run_skill_script / load_skill_resource.
- Output cap 5,000 chars (first 5k). Command timeout 300 s. Sandbox offline, 4 GB RAM, 2 vCPU.
- **`rg` and `tree` are not installed** → use `git grep -n`.
- Scratch files in /workspace get into the patch → use /tmp. Don't touch pytest.ini / conftest.py.
- Pinned vLLM parser may pass int/bool tool args as strings (happyc0der) → e.g. read_file line ranges fail.
- **No GitHub/network access** (verified): Docker network_mode none; sandbox image = python:3.13-slim + git,
  patch, protobuf-compiler, pigz, pytest (+pytest-timeout), typer, build backends. No `gh`, `rg`, `tree`, `curl` use.
  Snapshot has no git remote. → `gh issue view`, `pip install`, web lookups all impossible.
- **Full LOCAL git history up to base_commit IS available** (verified on requests_7505: 6,475 commits back to
  "first commit", `git blame`/`git log`/`git show` work, branches main + export_ref). Example: issue says
  "successor to #7502" and HEAD is exactly "Fix `_encode_files` detection … (#7502)" → `git show HEAD` reveals the
  pattern to replicate. → Scaffold lever: teach `git log --oneline -15`, `git log -S'<symbol>'`, `git log --grep`,
  `git show <sha> --stat`, `git blame -L` for localisation/spec recovery (esp. title-only tasks).
- **Git safety** (verified: container_setup.py:581 tags baseline `_swegemma_baseline`; patch = `git diff --binary
  _swegemma_baseline` of the final working tree, execution.py:84 / agent_runner.py:767). Git is just bash via
  run_command → rules can't be enforced, only prompted + verifier-checked.
  - Encourage (read-only, bounded output): git log --oneline -n/--grep/-S, git show --stat / -- file, git blame -L,
    git grep -n | head, git diff --stat, git status --short.
  - Forbid: git checkout -- / restore / reset --hard (lose edits), git stash (empty patch if not popped / timeout),
    git clean -fd (deletes new files), checkout other commits/branches (huge wrong diff), touching the
    _swegemma_baseline tag, rebase/merge/cherry-pick. git commit is harmless (diff is vs tag) but pointless.
  - Baseline failing tests: record BEFORE editing, never via stash. Verifier runs git status/diff --stat pre-submit.
- **Graphs/embeddings contain NO async functions** (0/305) → graph tools blind to async code (fastapi!).
  Half of graph/embedding files are 0-byte in download + Kaggle mount (hard-link issue).

### LoRA status
- Only LoRA adapters accepted (no full fine-tunes). PEFT safetensors, rank ≤128, ≤8 adapters, per-agent.
- **Currently broken**: patched vLLM 0.19.1 loads adapters but resets their weights to zero (forum 743508);
  PyPI vLLM refuses LoRA for Gemma4. Official sample (with adapters) also FAILED. Watch for host fix.
  → LoRA is not usable today; prompt/scaffold is the only working lever right now.
- **Update 2026-10-14 (forum):** host says the zeroing fix landed (wheelhouse v23+). But 743508 (Fawad07, 10-08):
  noise adapters still give logprobs identical to base within 1e-6 → weights set but unused. 749191 (Nir Aberman,
  10-14): LoRA bundles OOM at startup on 4×L4 (sampler warmup; cudagraph_specialize_lora doubles graphs);
  verified workarounds need build_cmd changes we can't make in a submission → asked host. 748051: unclear whether
  any top score comes from LoRA; same package rescored 0.17/0.15/0.13/0.15 (noise). DECEM: LoRA ≈11% slower decode.
  Wiring: `adapter: <name>` per agent YAML → per-role adapters (le locator/editor) are supported by the format.

### Harness packages
- Kaggle dataset `metric/gemma-4-developer-agent-wheelhouse`: swegemma 0.2.7, adk-submission 0.2.11,
  adk-eval-core 0.1.0, google-adk 1.36.1, vllm 0.19.1 (patched, x86 Linux), transformers 5.13.1, flashinfer.
- Host notebook `ryanholbrook/getting-started-gemma-4-developer-agent` runs the real 31B model + Evaluator
  on a **Kaggle L4 notebook** (subprocess sandbox; no Docker on Kaggle). → We CAN run real-model local evals
  on Kaggle for free (L4×4 burns quota at 2×, measured 2026-09-27; queues reported).
- Public wheels miss some test deps (typing-inspection, inline-snapshot, dirty-equals, pytest-httpbin) →
  some gold patches fail locally. Need a "gold-patch positive control" run to know which dev tasks are valid.

### Verified from harness SOURCE (swegemma 0.2.7 / adk-submission 0.2.11 / adk-eval-core 0.1.0)
Unpacked in scratchpad `src/` — read the code when README and forum disagree.
- **"Custom tools" = skills.** YAML tool names only resolve against the closed ToolRegistry (the 9 tools) +
  `agent_tool`. The only way to ship our own code is `skills/<name>/` (SKILL.md + scripts/ + resources/),
  exposed via ADK SkillToolset (`run_skill_script`, `load_skill_resource`). Scripts run as `python3` inside
  the task sandbox (same FS as run_command, /workspace cwd), timeout = timeout_seconds, debit the time budget.
  Temp script files are git-excluded and deleted → no patch pollution. (Forum 743573 asks the same; no answer yet.)
  → Big lever: e.g. a repo-map / async-aware symbol search / test-finder script written in Python.
- **Callbacks**: CallbackRegistry exists but swegemma registers none → no callbacks usable.
- **No MCP** (verified): ADK supports MCP via `McpToolset`/`to_mcp_server` but only in Python agent code; the
  competition compiler is YAML-only, `tools:` = `list[str | AgentToolEntry]` resolved against the closed registry,
  and "mcp" appears nowhere in swegemma/adk-submission/adk-eval-core. Mapping: harness = tool server, ADK agent built
  from agent.yaml = client, skills = our only custom tools. Our Python lives in skill scripts (CLI, compact output)
  and local tooling (pack, eval runner, analyzer, trajectory builder, LoRA training, Kaggle notebook).
- Task prompt (`build_agent_prompt`): repo + problem statement, budget lines, env rules, instructions 0–5
  (incl. "final action must be a text-only response"), graph-tools blurb only if graph+embedding files >100 B,
  plus `find . -maxdepth 3 | head -150` workspace tree. Our system prompt sits on top of this.
- Tool signatures use typed params (`start_line: int | None`) — consistent with the string-vs-int parser issue.

- **No human in the loop** (verified agent_runner.py L677–739): one initial task message, then only 3 canned
  nudges ("Please continue… or call submit_patch", token-limit variants). Counter resets on any tool call;
  after 3 nudges the 4th consecutive tool-less round ends the task (working tree graded as-is, unless an exception
  ended it). Questions get the canned nudge.
  → Scaffold rule: never ask, resolve ambiguity from issue wording / code conventions / tests, every turn must
  contain a tool call until submit_patch, then one short text reply to end.

### Models available for local work (Kaggle Models, google/gemma-4)
- Competition: `other/gemma-4-31b-it-qat-w4a16-ct` v2 (23.3 GB). Same family: **`gemma-4-12b-it-qat-w4a16-ct`**
  (10.3 GB) — a proxy with the same quantisation/format for cheaper Kaggle runs.
- GGUF: `gemma-4-12b-it-qat-q4_0-gguf` (7.2 GB — fits Mac M5 16 GB via llama.cpp), 31B gguf 18.9 GB (too big).
- Unquantized QAT checkpoints `gemma-4-31b-it-qat-q4_0-unquantized` (62.6 GB bf16) — the likely base for LoRA
  training (adapter must target `google/gemma-4-31b-it-qat-w4a16-ct` modules; verify when LoRA is fixed).
- All Apache 2.0.

### Forum status notes (2026-09-26)
- Host says the resource-error failures are fixed and affected submissions will be **re-run Monday** (743683).
- Other LB posts: bare-bones configs score 0.08; thinking off + coder/analyzer = 0.10; top 0.13.

### Paper track
- Kaggle Writeup ≤3,000 words (title, abstract, intro, methods/experiments, related work); optional public
  notebook / arXiv PDF. Judged 0–5 on Novelty, Quality (generalisation), Relevance, Verifiability, Clarity.
- Suggested topics: PEFT/RL for SWE agents, code-graph generation/embeddings, new tasks/benchmarks, graph reasoning.
- Paper angle candidates from what we've found: async-blind graphs → repaired graph + effect on localisation;
  context-budget management under 32k; cheap scaffolds for small local models.

## Our compute (user's Kaggle quota, 2026-09-26)
- GPU 30 h/week, TPU 20 h/week, "AI Models" $10/day & $100/month, LB submissions don't use quota.
- L4×4 burns quota at 2× wall-clock (measured 2026-09-27: 2h38m for ~80 min).
  If 1×: ~10 real-31B dev evals/week (20 tasks ≈ 2 h + 10–20 min vLLM startup). If 4×: ~2–3/week, lean on
  Mac proxy (small Gemma 4 via MLX/llama.cpp) for plumbing.
- AI Models credit = hosted models via `kaggle-benchmarks` in notebooks (model list UNVERIFIED). Uses: failure
  triage / LLM-judge of trajectories (safe); teacher for SFT trajectories only if distillation ruling allows.
- TPU: only relevant for LoRA training (JAX/Keras) once adapters work in scoring.

## Local dev setup (Mac M5, 16 GB unified, macOS 27)
- Installed: Ollama (/usr/local/bin/ollama), Docker via Colima (not running → `colima start`). No llama.cpp/LM Studio.
- Model: Kaggle `gemma-4-12b-it-qat-q4_0-gguf` (7.2 GB, same QAT lineage) loaded into Ollama via Modelfile;
  fallback `ollama pull gemma4:12b` (Q4_K_M, 7.6 GB, tags: tools, thinking). Set num_ctx 32768 (default 4k!).
- Memory estimate: ~7.5 GB weights + ~3–6 GB KV at 32k (40/48 layers sliding-window 1,024) ≈ 11–13 GB —
  close to macOS default GPU wired limit (iogpu.wired_limit_mb=0 → default). Measure; raise limit or cut ctx if needed.
- Harness: `swegemma eval --sandbox docker` locally; route `gemma-4-31b-it-qat-w4a16-ct` alias → Ollama's
  OpenAI endpoint via `--models-yaml` (harness uses LiteLLM `openai/<model>` + api_base).
- Use for: plumbing, compile checks, workflow/prompt smoke tests, skill-script development.
  NOT for: score prediction (12B ≪ 31B) or tool-parser quirks (Ollama ≠ vLLM gemma4 parser). Speed unmeasured.
- UNVERIFIED: Ollama Gemma 4 tool-call reliability over long sessions; swegemma install on macOS without vLLM.
- **31B does NOT run usefully on the Mac** (checked 2026-09-26): Ollama gemma4:31b Q4_K_M 20 GB, official QAT
  Q4_0 GGUF 18.85 GB (Unsloth: needs ~18 GB RAM), Unsloth Q4_K_M 18.25 GB (recommends 32 GB). 2-bit quants
  (~9–10 GB) fit but quality collapses and ≠ scorer's W4A16 → not a valid baseline; overflow → swap, unusable.
  → Real 31B baseline = Kaggle L4×4 notebook (same model file + vLLM 0.19.1 as scorer); LB = daily confirmation;
  Mac = 12B for plumbing only. T4×2/llama.cpp (~12 tok/s) not worth it.
- **Local proxy candidates (researched 2026-09-26):**
  - gpt-oss-20b (Apache 2.0, MoE 20.9B/3.6B active, MXFP4 ≈12.8–13 GB, 128k ctx): SWE-bench Verified 53.3%
    (medium) / 60.4% (high) per OpenAI model card — numerically closest to Gemma 31B's 53.9% (Vals). BUT different
    harnesses → numbers not directly comparable; fit on 16 GB with 32k ctx is tight (may need iogpu limit raise) — UNVERIFIED.
  - Gemma 4 12B QAT (7.2 GB): same family/chat template/tool-call format/quirks as the competition model; weaker.
    Vals has no 12B page; third-party numbers inconsistent (unreliable).
  - Ruled out: Devstral 24B (46.8% Verified, ~14 GB → no room for 32k ctx), Gemma 4 26B-A4B (≈18 GB at 4-bit;
    one source 17.4% Verified), Qwen3.6-27B/35B-A3B (too big for 16 GB).
  → DECISION: Gemma 4 12B stays the primary local proxy (behavioural fidelity > benchmark match: prompts and
    tool-format quirks are family-specific). gpt-oss-20b optional second opinion: a prompt change that helps both is
    more likely to transfer. Real numbers only from 31B on Kaggle.
- **Hosted Gemma 4 31B (researched 2026-09-26):**
  - Vertex AI MaaS: Gemma 4 not listed as of Apr 2026 (only Gemma 3) — skip.
  - **Gemini API / AI Studio serves `gemma-4-31b-it`** (official Gemma docs; tool calling supported, 256K ctx).
    Pricing page: **free tier "Free of charge"; paid tier "Not available"; free-tier content used to improve products.**
    Rate limits per project, only visible in AI Studio console (UNVERIFIED numbers). Harness retries 429s (ModelRetryPlugin).
  - Hook-up: swegemma models-yaml → LiteLLM `gemini/gemma-4-31b-it` + GEMINI_API_KEY, local Docker sandbox on Mac.
  - Fidelity gaps vs scorer: likely bf16 not W4A16 (UNVERIFIED); Google's server parses tool calls (not vLLM gemma4
    parser → string/int quirks won't show); **no 32k wall** (256K) → context-overflow failures hidden unless we enforce
    a 32k cap ourselves; thinking config mapping may differ.
  - Data caution: sending task text/code to a free API that trains on it; rules forbid giving Competition Data to
    non-participants. Public tasks are public GitHub PRs and Google is the sponsor → low risk, but keep usage to dev
    tasks and don't paste anything private.
  - Other paid hosts: OpenRouter ($0.08/$0.30 per M tokens; also a `:free` variant), Together ($0.20/$0.50) — fallback.
  → DECISION (user, 2026-09-26): **drop the hosted API entirely** — the 256K window hides context-overflow
    failures, plus parser/precision/data-use gaps. (Possible workaround — count runs >32k tokens as failures from trace
    token usage — noted but not pursued.)
  → Testing tiers: Mac + Gemma 4 12B (offline plumbing, format fidelity) → Kaggle L4×4 31B W4A16 (numbers we
    trust) → LB (daily confirmation).

## Levers (ROI order, given LoRA is broken today)
1. Scaffold + prompt: localize → reproduce (in /tmp) → minimal edit → targeted test → submit. Short outputs.
2. Budget config: thinking on/off tradeoff vs the 12 h cap; failsafe per-task limits.
3. Sub-agents/skills for context isolation (analyzer AgentTool), skills with helper scripts (e.g. repo map,
   async-aware search) — skill scripts can run Python inside the sandbox.
4. LoRA SFT once the host fixes adapter loading (trajectories from public tasks / open datasets).
5. RL — likely out of reach at $0.

## Phases (draft)
- P0 Setup: join paper track; repo scaffold (+ .gitignore data/); download data to repo `data/`;
  install wheelhouse locally for compile/validate checks (Linux-only vLLM isn't needed on Mac).
- P1 Eval loop on Kaggle L4 notebook: run subset of dev tasks with our submission dir; gold-patch control.
- P2 Scaffold iteration with 1 LB submission/day, one hypothesis each, logged in experiments/.
- P3 LoRA if fixed. P4 Paper by Nov 12, final picks by Dec 2.

## Why Gemma scores 54% elsewhere but ≤13% here (researched 2026-09-26)
- Vals AI 53.92% SWE-bench Verified = **mini-swe-agent** (bash-only, no tool-calling API, stateless
  subprocess per command, fully linear history, ~100-line agent), **150-step cap**, provider default config with
  max output tokens maxed, 500 human-validated tasks. Precision/context not stated — almost certainly bf16 via an
  API with the full 256k context (UNVERIFIED).
- Our room: 32k context, W4A16, ~6 min & sequential budget, 9 JSON tools via vLLM gemma4 parser, private repos,
  tasks filtered by frontier-model solvability.
- **Key paper: "An Empirical Study of Harness Design for Coding Agents" (arXiv 2609.20804):**
  - Context management is the dominant factor: managed vs unmanaged = **+35.7 pts at 32k** (2.7 pts at 128k);
    unmanaged runs overflow in **78.7%** of cases at tight budgets. Best: staged "rule-based elision before
    LLM summarisation".
  - Planning helps weaker models (+11.6 pts for a 30B; runs collapsed from 40→5 turns without it).
  - Weaker models lose ~15 pts bash-only (66% of runs die after failed tool calls); strong models do fine bash-only.
  - Definitions (paper): M1 elision = replace stale tool-output bodies with short stubs; M2 recall = store them
    externally, fetchable via `recall_event`; M3 summarisation = fold oldest middle events into a running summary.
    Preamble + recent window kept verbatim; soft threshold B1 → elide middle, hard threshold B2 → summarise. T4 = all three.
  - Planning (paper §3.2/§7.2, Fig. 15/17): a todo list kept via an `update_plan` tool; first action on any
    3+-step task; exactly one item in_progress; stored OUTSIDE the history and re-injected fresh before every model
    call ("Current plan …: {PLAN}") instead of appending copies. Effect: Nemotron-3 30B +11.6 pts SWE-Bench (higher
    cost); 128B/550B models: ~30% cheaper, −0.4/−2.0 pts. Gemma 31B-W4 at 32k ≈ the "weaker model" side → likely helps.
  - Our version (no update_plan tool, no callbacks): SequentialAgent [planner (read-only, output_key=plan) → coder
    whose instruction contains {plan}]. ADK renders instruction state templates on each model request, so the plan is
    re-supplied every turn and survives compaction (expected ADK behaviour — VERIFY locally). Progress tracking:
    optional tiny /tmp/plan.md checklist via run_command. Planner can double as the localizer (files, lines, repro idea).
  - Prompt/issue reformatting (researched 2026-09-26): benchmark papers (SWE-Bench Pro, ProMax) rewrite issues
    OFFLINE with human/gold knowledge — not evidence for inference-time rewriting; no solid paper found showing a
    rewrite module alone lifts resolve rate. Public-task data: 34/129 statements <150 chars (often just a PR title,
    e.g. "✨ Add support for Server Sent Events"), 25 contain PR/checklist templates, 9 HTML-comment templates,
    18 code blocks, 1 traceback; median 418 chars, max 10k.
    → DECISION: no separate rewriter. Fold into the planner as a "TASK SPEC" section: expected vs actual behaviour,
    identifiers/messages/values quoted VERBATIM, acceptance criteria, ambiguities + chosen interpretation, boilerplate
    ignored. For title-only tasks the planner must recover the spec from the repo (docs/, docs_src/, changelog,
    similar existing features, related tests) — rewriting can't add information that isn't there.
    Raw issue always stays in the harness's first message, so a rewrite adds tokens rather than replacing them.
  - We likely CANNOT elide history (declarative YAML, no callbacks registered — inference, untested). ADK events
    compaction ≈ M3. Emulate elision by design: AgentTool sub-agents (their reads never enter root context),
    compact skill-script outputs, strict output-size rules in the prompt.
  → For us (mid-size model, 32k window): context management + explicit plan + robust structured tools =
    top priorities. Ties directly to the ADK compaction question (does it fire?) and to AgentTool isolation.

## Self-correction (researched 2026-09-26) — likely under-explored lever
- Competition status: 2 EDA notebooks list "reviewer sub-agent (inspect git diff vs issue before submit)" as an
  untried idea; the 0.10 notebook has a read-only `code_verifier` sub-agent variant in an ablation (results not
  shown). No public use of SequentialAgent/LoopAgent generate→review→revise.
- Literature: SWE-Review (arXiv 2607.06065) generate-review-revise loop beats single-shot review in decision
  accuracy and resolve rate; ExecCritic (2609.09133) generated test patches +4.2 pts on SWE-bench Verified;
  Adversarial Review (2608.18167) reviewer–critic loop; "Confident and Wrong" (2603.25764) silent semantic failures.
- Three levels possible in our harness:
  1. In-loop: reproduce → edit → re-run → read failure → fix (prompt-driven; cheapest).
  2. Reviewer AgentTool: read-only sub-agent checks `git diff` vs issue (names/signatures, scratch files, test edits,
     partial fix) and returns a verdict + fix list before submit_patch.
  3. Workflow: SequentialAgent [coder → reviewer(output_key=review) → fixer uses {review}]. LoopAgent can't exit
     early: `exit_loop` is not in the closed ToolRegistry → only `max_iterations` (keep 1–2).
- Risks/UNVERIFIED: harness breaks the loop as soon as a turn ends with patch_submitted → only the LAST agent should
  hold submit_patch (unsubmitted diffs are auto-extracted anyway); how harness handles workflow-agent roots needs a
  local test; review costs time inside the ~6 min/task budget.
- **Chosen design (user idea, refined): coder + verifier AgentTool, bounded loop.**
  - Coder owns edits + submit_patch; calls `verifier` (agent_tool, skip_summarization left at default false —
    true ends the parent's run after each call) after each fix attempt.
  - Verifier = evidence-based, not opinion: runs the /tmp repro script + the closest existing tests + a
    diff audit (names/signatures vs issue, no test/config edits, no scratch files in /workspace, fix complete),
    returns `VERDICT: PASS|FAIL` + for FAIL the exact command, trimmed error (≤20 lines) and the one thing to fix.
    Tools: run_command, read_file (no edit/write/submit). Must write only to /tmp (prompt rule; not enforceable).
  - Loop = coder decides (AgentTool can be called repeatedly) — cap at 2–3 verifier calls; stop early on PASS,
    when the same complaint repeats, or when budget_warning appears / get_status shows <25% left.
  - Never revert a plausible fix because of a vague complaint; a FAIL must quote real command output.
  - Baseline noise: coder records failing tests BEFORE editing so verifier can ignore pre-existing failures.
- Verified from source: verifier's run_command/read_file calls hit the SAME per-task budget (budget_gated uses the
  shared task context) → max_tool_calls must include verifier usage. The agent_tool call itself is not a swegemma
  tool, so it likely isn't counted (inference). `problem_description` is in session state and AgentTool copies
  parent state into the child session (verified in google-adk 1.36.1 agent_tool.py, 2026-10-04) → the child can use
  `{problem_description}` in its instruction.
- Also relevant: notebook `busyaprime/119-of-129-sound-the-gemma-4-grader-rebuilt` (gold-patch validity of dev tasks).

## Agent communication topology (researched 2026-09-26)
- Evidence: "Towards a Science of Scaling Agent Systems" (Google, arXiv 2512.08296; 260 configs): sequential
  reasoning tasks degrade 39–70% under all multi-agent variants; tool-heavy tasks pay a coordination "tax";
  coordination has diminishing/negative returns once single-agent baseline > ~45% (we are ~13% → below, so
  targeted help can pay); independent agents amplify errors 17.2×, centralized 4.4× (orchestrator = validation
  bottleneck). MAST (arXiv 2503.13657): 14 failure modes, a major class is inter-agent misalignment (information lost
  or misread at hand-offs). Another survey: MAS slightly degrade SWE-bench Verified (−2 to −15%) at high baselines.
- Implication: coding is sequential + tool-heavy → keep ONE agent that owns the working context and all edits
  (hub); specialists are call-and-return helpers with short structured I/O; specialists never talk to each other.
- ADK mechanics (verified in compiler): `agent_tool` = call-and-return (parent keeps control, gets child's final
  text); `SequentialAgent` = fixed pipeline; `sub_agents` transfer hands control away (avoid — harness loop/final-
  response handling makes it risky, UNVERIFIED). Shared state via `output_key` → `{key}` in instructions.
- Recommended topology ("hub-and-spoke with a fixed opening"):
  SequentialAgent[ planner (read-only, output_key=plan: TASK SPEC + PLAN) → executor/hub (instruction has {plan}) ]
  executor calls: verifier (agent_tool, 2–3× max) and optionally replanner (agent_tool, same planner prompt, only when
  stuck, given what was learned). No planner↔verifier channel; all traffic goes through the executor.
  DECISION (user asked for recommendation): target = hub + fixed opening, built as an ablation ladder, each rung
  measured on the same dev subset (also the paper's core experiment):
    1) single agent + strong prompt (git history, safe git, bounded output, never ask) → baseline + failure taxonomy
    2) + verifier agent_tool (max 2–3 calls)
    3) + planner up front (Sequential, {plan} re-injected every turn)
    4) + replanner agent_tool only when stuck
  Keep a rung only if it pays for its time on our tasks.
  Rejected: planner-as-orchestrator commanding an executor sub-agent (executor would restart context each call, the
  orchestrator only sees summaries of edits → hand-off loss, more hops, more time).

## Teacher models for distillation (researched 2026-09-26)
Reference point: Gemma 4 31B IT (bf16) ≈ 53.9% SWE-bench Verified (Vals AI) — vs LB top 13%. Gap = harder
private repos/frontier-filtered tasks, 4-bit, 32k context, weak scaffolds → large scaffold headroom.
- **Primary teacher: Qwen3.6-27B** (HF model card): dense 27B, **Apache 2.0**, SWE-bench Verified 77.2%,
  Pro 53.5%, tool calling (vLLM `--tool-call-parser qwen3_coder`), needs vLLM ≥0.19.0 (competition wheelhouse has
  0.19.1). bf16 ≈54 GB → fits Kaggle 4×L4 (96 GB, TP=4) at 32k ctx → **teacher runs on our free quota.**
- Alt: **Qwen3.6-35B-A3B** (MoE 35B/3B active, Apache 2.0, 73.4% Verified) — much faster per token.
  Qwen3-Coder-Next (80B-A3B, 70.6%, Apache 2.0).
- Too big for free hardware (API only): DeepSeek V4-Flash (284B/13B, MIT, ~79%), V4-Pro (MIT, ~80.6%),
  GLM-5.2 (MIT), Kimi K2.5/K3 (Modified MIT). DeepSeek's API terms explicitly allow distillation — but costs money.
- Avoid: Llama 4 (custom community license strings), all closed APIs (Claude, GPT, Gemini-proprietary ToS).
- Caveats: (1) teacher must act in OUR room (same tools/prompt/limits), then transcripts are re-rendered into
  Gemma's chat/tool-call format; (2) teacher skill gap → filter to verified passes, prefer shorter/simpler
  trajectories the student can imitate; (3) competition ruling on distillation still pending — open-weight
  Apache/MIT teachers are the route the rules' "publicly available, free" clause clearly covers.
- Kaggle "AI Models" credit: model list only visible via `list(kbench.llms.keys())` in a notebook — check.

## Still unverified / waiting on hosts
1. L4×4 quota burn rate (1× vs 4×) — measure.
2. Distillation from proprietary LLMs allowed? (742807) — host "conferring" since Sep 24, still no ruling
   (checked 2026-09-26). Independently: Anthropic terms prohibit "using Outputs as training targets for models" /
   training competing models (support.claude.com article 12326764); OpenAI similar. Winner obligations
   (open-source, reproducible) also clash. → DECISION: no Claude/GPT-generated training data. Claude is used
   only to build the system (prompts, skills, eval tooling, failure analysis).
   Training-data plan instead: (a) rejection sampling / self-distillation from Gemma 31B in our own room
   (keep only harness-verified passes); (b) open-weight teachers with training-permissive licenses;
   (c) extra runnable task sets (e.g. SWE-Gym 2,438 tasks) — check licenses + effort to port into swegemma.
3. LoRA adapter-wipe fix in scoring vLLM (743508) + whether sample adapters then work.
4. Whether events compaction actually fires (743456); int/bool tool-arg parsing on the scorer.
5. Whether scoring env has the empty graph/embedding files problem and missing test wheels.
6. Hidden-test repos are private — nothing known about their size/style beyond "similar pipeline".
7. Which hosted models the Kaggle "AI Models" credit exposes.

## Housekeeping
- Scratchpad (`/private/tmp/claude-501/.../scratchpad/`) is session-scoped: in P0 copy `data/`, `pages/`,
  `paper/`, `forum/`, `kernels/`, `src/` into the repo under `data/` or `research/` — gitignored where it
  contains competition data (no redistribution).
- Rotate the Kaggle API token that was pasted in chat.

## Verification
- `make pack` → zip validated with swegemma's ALLOWED_SUBMISSION_EXTENSIONS / MAX_SUBMISSION_SIZE_BYTES and
  compile_submission(). Kaggle-notebook eval on dev subset → resolution rate; LB submission for calibration.
