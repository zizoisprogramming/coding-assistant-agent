# Gemma 4 Developer Agent — Competition Plan (living doc)

## >>> START HERE (session handoff, updated 2026-11-11) <<<
**2026-11-10: the user dropped the side writeup track for good. The only goal is winning the main leaderboard; never raise the writeup again (older 'Paper' lines below are history).**
**RULE 2026-11-10 (user, after r75): never put a budget in an agent prompt** (no tool-call counts, minutes, 'by call N' plans or clock time plans). Limits live in eval_config; a stage that must stop is stopped by a tool-output event (gate refusal / state line). r75's scout, told 'about 10 tool calls', used 44 / 17 / 9 / 44.
### CHECKPOINT 2026-11-11 (NEWEST — read first; details in the RESULT / RUN BUILT / MINING entries just below, r72-r81)
**Status:** **evidc is on the LB, PENDING** (submitted by the user 2026-11-11 09:02; dist/submission.zip = dist/evidc.zip, md5 9755bb6c, verified identical to the bundle that ran in r77 / r78a; combo1's zip kept as dist/combo1_submitted.zip). **r79 done: evidd and evide passed** (full-history evidence 8/8 vs evidc 2/8; 4 vs 3 solved; see RESULT r79). **Stats model built 11-11 (STATS MODEL entry; page https://claude.ai/artifact/Mf8mXPF6ToLNonBi5ARNpQ): agents differ by <= ~3 points on dev16, no comparison clears zero, evidc vs combo1 P(better) 0.87; luck band +-3 solves per dev16 pass.** **r80 done: evidc / evidd / evide 8/20 each; evide passed its bar (time -20 s), evidd failed on time (+13 s) -> evide is the next LB submission after evidc's score (dist/evide.zip); see RESULT r80.** **r81 done, 2 passes (RESULT r81 + RESULT r81 PASS 2): fs copies 18/32 vs originals 11/32 (same-task 12 vs 5, one-sided p 0.07; bank model shared fs effect OR 1.42 [0.63, 3.20], P(helps) 0.80, ~+3 points on dev16 [-4, +12]); the originals were unlucky (p16) more than fs was lucky; time +23.5 s/run; pass 1 failed its mechanics bar. Suggestive, not established.** **NEXT LB SUBMISSION = evidefs (user 11-11: "add the fix since we know it doesn't harm but may help, so be it"; dist/evidefs.zip 245b5c39; replaces evide; see BUILT evidefs) once evidc scores; dist/submission.zip stays evidc until then.** **evidc LB 0.15 (2026-11-12; = 9/58, fit in time; scores are floored: 0.15 = 9, 0.18 = 11, 0.20 = 12, 0.22 = 13, 0.24 = 14, 0.29 = 17). dist/submission.zip = dist/evidefs.zip (md5 245b5c39) since 11-12 for the user's upload; evidefs uploaded 11-12 07:41, PENDING.** **NEXT LB (user 11-12 after r87: 'submit evidc'): dist/submission.zip = dist/evidc.zip again (md5 9755bb6c, the exact bundle that scored 0.15 and fit in time), to upload once evidefs finishes (one pending at a time). Why: top agent in the bank model (dev16 21.2% [18.2, 26.7]; vs pub024 P 0.89, vs combo1 P 0.91, evide vs evidc P 0.36, evidefs vs evide P 0.25); proven LB fit (380 s mean); its 0.15 = 9/58 is a low draw for an expected ~11/58; repeated evidc runs feed the final picks (best private score of 2 picks; 15-50% of a public lucky margin carries over).** **r82 done (RESULT r82 POOLED): sq1c2a8rc 13/32 vs evidc 15/32, gap -2 <= +1 -> its e24 83% was mostly luck; P(gap <= -2) 0.32 if average vs 0.03 at face value; +56 s/run on these tasks, 16/32 runs hit 8 min. Clock family closed. Refit: evidc is the model's top agent (vs combo1 +2.9 pts P 0.93, vs pub024 +2.4 P 0.92). Stats page refreshed (datasets v5).** Check it with `KAGGLE_API_TOKEN=$(cat ~/.kaggle/access_token) uvx --with six kaggle competitions submissions gemma-4-developer-agent`. It doubles as the time-fit test of the cheap evidence stage (evid3 timed out). **LB so far:** combo1 0.15 (fit, 11-11), pub024 0.18, sk_a2 0.18, sk_a2_32 0.17, mix 0.17, le6_t6 0.15, nn32rcn2 0.12, sq1c2a6 0.12/0.10; timed out: evid3, nn32, srep7, sq1c2, sq1c2t7, le5, 12B. Board 11-09: 0.29 x1, 0.24 x11, 0.22 x73, 0.20 x412, 0.18 x873. Identical bundles score 8-13 of 58 (+-3 tasks of draw noise). Deadline Dec 2; 2 final picks; 1 scoring submission a day, 1 pending at a time; the user uploads, never me.
**User rules added this session (also in memory):** only the main LB matters, never mention the dropped writeup track; never put a budget in an agent prompt (no call counts, minutes, 'by call N', clock time plans; stop stages with tool-output events); keep earlier rules (full-rewrite prompts, small first trial on the 4 mid-rate dev16 = fastapi_14419, fastapi_15589, rich_3521, rich_4079, same-run control, commit after every result, cell files as links, give input URLs, spare the user's internet, untrusted downloads with python -I).
**Best agent so far: evidc** = cheap evidence stage + combo1 (scripts/make_plus_arms.py build_evidc). Stage: one run_skill_script call (skills/evidence/scripts/evidence.py: tests, definitions, git log -S over the last 500 commits, changelog; 8 s deadline, 4 s per git call), thinking OFF via thinking_budget: 0, copies <= 10 lines into the fixer's system prompt ({evidence?}, output_key). Fixer = combo1's prompt byte for byte + the evidence section (combo1 = pub024 + garbled-edit rule + /tmp scratch fix - 3 graph tools). vs combo1: r76 3 vs 0, r77 (dev16 x 2 passes) 8 vs 5, r78a 1 vs 1 = 12 vs 6 over 44 pairs (+9/-3, sign p ~0.15), ~+10 s mean; the gain sits on the 4 mid-rate tasks (5/8 vs 1/8), the other 12 dev16 3/24 vs 4/24 (evid3 showed the same); the stage found nothing relevant (1-line reply) in ~6/16 tasks.
**Closed this session (numbers in the entries below):** thinking off (public thinking-off agents 0.08-0.13) and thinking caps (r13: model spreads thinking, hard tier 4/12 -> 0/12); pinning the issue (+5% once timing is controlled); lower call cap / shorter time cap (solves use the whole budget; 7.5 min loses up to 7% of solves); 12B / E4B; race = parallel engineers with first-submit-wins (sim +2/53 at equal time, but r75 1/4: scout ignored its budget; r78b 1/4: shared 44-call budget drained, empty submit_patch ends the race, compaction in the parallel phase) -> parked; gate family (forced edit through .git/agent/run.py): adoption fixed to ~100% (worked example + install line naming the engineer's command + REMIND line; the rc family had 24%), but every refusal costs ~60-80 s of thinking (nn32rcf 96 s/run, allplus 119, evgate1 with ONE refusal 83) and state words alone add nothing (evgate) -> closed for the LB.
**Harness facts learned (verified in source / runs):** the scorer runs one task at a time (decode 32.3 tok/s alone, 30.2 with 2 in flight, 26.9 with 3); in the installed harness (adk_submission 0.2.13) any thinking_budget > 0 turns thinking ON and a missing budget becomes 4096 -> include_thoughts: false alone does NOT turn it off, thinking_budget: 0 does; swegemma tools are synchronous and run on the event loop (no tool_thread_pool_config) under a shared tool_lock; the subprocess sandbox rewrites /workspace and /tmp in commands; the runner ends a task at patch_submitted + a final text event (any branch), and submit_patch is not budget-gated (an empty submit ends the task); ParallelAgent shares one session and token-threshold compaction (14,336, latest usage in the session) can orphan a function response -> crash -> patch dropped; past thinking is re-sent within a run (27% of context) and tool results are 42%; LB fit pattern: one skill call (install) + run_command fits, every command through a skill timed out; `git log -S` over a whole history takes 0.2-0.6 s on the public repos' snapshots (4-7k commits; MINING 2026-11-11), so evidc's 500-commit limit was not needed.
**Code map:** builders scripts/make_combo_arm.py (combo1/2, combo1en/en2), make_race_arm.py (race2), make_plus_arms.py (nn32rcf, evidc, t7rc, allplus; shared setup/evidence pieces), make_evidefs.py (evidefs = evide + evidcfs's fixer prompt), make_gate_arms.py (evgate, evgate1, race3), make_fewshot_arms.py (pub024fs, combo1fs, evid3fs, evidcfs: few-shot call-form examples, no budget numbers), make_evid_arms.py (evidd, evide: evidc with scripts/agent_evidence/evidence_r79.py, 9 tests `python3 -I scripts/agent_evidence/test_evidence_r79.py`); gate script scripts/agent_clock/run_phase.py (switches WORDS, LIGHT, READS, REMIND, REFUSE_ONCE, SCOUT; 22 tests: `uv run --with pytest python -m pytest -q scripts/agent_clock/test_run_phase.py`); notebooks scripts/train/make_skill_arms_cells.py (OUT, ARMS, TASKS, CONCURRENCY; only cell2 changes between runs; latest folders kaggle/cells_skill_fs4, evide16, evide4, race3_4, gate4, evidc16, plus4, race4); validate a bundle with `uv run scripts/pack.py submissions/X` (-> dist/X.zip); simulator `SIM_CELLS=cells_skill_X data/venv_harness/bin/python data/sim/armsim.py` (gitignored; roles incl. rscout/rscout_g/reng_a/reng_b, plussetup, clockrc; race sims use a threaded fake server). Stats: `.venv/bin/python scripts/stats/run_model.py data/analysis/stats_model.json` (hierarchical model, luck checks, power; numpy only). Readers: `CTRL=combo1 python3 -I scripts/paper/analyze_screen.py FOLDER`, scripts/mine_bank/pair_bar.py (changed arm vs same-run control, RESULT r81), stats/treatment_effect.py (one shared effect of a change over several agents inside the bank model), mine_bank/evidence_reads.py (evidence stage: names, gold file reached, empty replies; --runs for each run), plus_reads.py (gate use, stage time, evidence lines), race_reads.py, refusal_next.py, bestof_sim.py, race_compaction_risk.py, decode_vs_inflight.py, think_share.py, issue_gone.py, first_edit_vs_budget.py, arm_table.py (every arm vs same-run pub024).
**Notebooks / accounts:** engziadsamer/arms-again and fatmazenhom/generation-shard-4-gpu (both free now; the user replaces cell 2 and does Save Version -> Save & Run All); older: ziad23samer/fork-of-fork-of-generation-all-shards-gpu. Download: `KAGGLE_API_TOKEN=$(cat ~/.kaggle/access_token) uvx --with six kaggle kernels output OWNER/SLUG -p data/results/DATE_skill_NAME --file-pattern '.*(gen_per_task\.jsonl|phases\.json|digest\.jsonl|requests\.jsonl|\.log)$'` (check the arms inside: the user may swap notebooks). Inputs (already attached): https://www.kaggle.com/competitions/gemma-4-developer-agent, https://www.kaggle.com/datasets/metric/gemma-4-developer-agent-wheelhouse, https://www.kaggle.com/models/google/gemma-4 (gemma-4-31b-it-qat-w4a16-ct), https://www.kaggle.com/code/ziad23samer/test-gemma-comp, https://www.kaggle.com/datasets/rodrigospalma/ood45-bugfix-split.
**Next agenda (agreed direction: information is the lever; the information test took 6/76 -> 30/76):** (1) watch evidc's LB score (fit? vs combo1 0.15); (2) DONE 11-11: mined (MINING 2026-11-11), r79 / r80 -> evide; r81 (2 passes) -> the fs prompt may help (P 0.80) -> evidefs = evide + evidcfs's fixer prompt is the next LB submission after evidc's score (copy dist/evidefs.zip to dist/submission.zip then; if evidc times out on the LB, evidefs (~evidc + 3 s/run) is at risk too: then fall back to a faster agent); next run direction not agreed yet (the stats model says single 4-16-task runs cannot rank agents that differ by a few points: pick changes with a large expected effect or plan ~128 runs per arm); (3) final picks: the two highest-true-rate agents that fit the LB time (both picks can be the same best agent).

**User:** beginner to agents/ADK (ML engineer background); wants step-by-step plain explanations, research-backed
claims (verify, cite), chat before building, decides when planning ends. Rules: several changes per run are fine
(since 10-25) but bundle them into arms;
prompts generic (no dev-task content); competition data never committed (data/ is gitignored, incl. adapters built
from sample data); Kaggle token only in ~/.kaggle/access_token. Give Kaggle cells as FILE LINKS, never pasted; never
change cell 4's printed output. **No training data from Claude, GPT or Gemini (user decision, D14).** Each Kaggle
account runs its OWN notebook copy (a shared notebook made `kaggle kernels output` return only the latest version
and coincided with tasks running serially). L4x4 burns GPU quota at ~2x; weekly quota is tight → small runs.

### CHECKPOINT 2026-11-07 (NEWEST — read first; details in the entries below, docs/ARCH_ANALYSIS.md and docs/PAPER_NOTES.md)
**Deadlines:** paper Nov 12 (aim Nov 11; Kaggle Writeup, 3,000 words); competition Dec 2, 2 final picks; 1 scoring submission a day, 1 pending at a time.
**Waiting on the user:** r57 output (kaggle/cells_skill_setup8: pub024, nn32rc2, nn32rcn2, sq1c2a8rcx2 on 8 tasks, ~1.9 h). Read with `python3 -I scripts/paper/analyze_rc.py FOLDER` (install, share through the script, garbling, quoting, refusals) and scripts/paper/analyze_screen.py. Bars set before the run: install in nearly every run, >=90% of commands through the script, garbled <5%, agent time <= pub024's, solves not clearly below. Download with `KAGGLE_API_TOKEN=$(cat ~/.kaggle/access_token) uvx --with six kaggle kernels output OWNER/NOTEBOOK -p DIR --file-pattern '.*(gen_per_task\.jsonl|phases\.json|digest\.jsonl|requests\.jsonl)$'`.
**Next by outcome:** if bars pass, submit the best rc2 arm as an LB fit test (zips in dist/; dist/submission.zip is still nn32). If it fits at 8 min, the skill-shell hypothesis holds and the clock family (sq1c2a8rcx2) becomes the main line; if it times out, try 6.5 min (what-if: nn32 keeps 11/11 solves at 372 s) or the plain prompt on run_command without a script.
**LB so far:** pub024 0.18, sk_a2 0.18, sk_a2_32 0.17, mix 0.17, le6_t6 0.15, sq1c2a6 0.12 / 0.10. Timed out: le5, sq1c2, sq1c2t7, srep7, nn32 (every 7-8 min skill-shell agent). Top of LB 0.29, many at 0.24 (an 0.18 agent reaches 0.24 by luck 15% of the time).
**Main findings (11-06/07):** task explains 64% of solved, agent family 0.7%, chance 35%. Wrong edits are in the right file (about 80%) and fail on assertions (83%): logic, not location. Fix size predicts solving (Spearman -0.58), file size barely (-0.19). Only enforced events move behaviour (refusal -> edit 23-39%, warning 6-11%); clock numbers showed no measurable benefit. Hotter sampling hesitates and does not explore (r53). Checklist +10 / +4 (same runs, easy set). No-numbers arms (nn) on 42 tasks: 9-11 solved vs pub024 7, no patch 4-7 vs 21, not significant; their extra edits are mostly wrong. The model skips setup calls: always use a setup agent (le6 pattern), never an "install first" prompt line. "Capped runs never solve" was a label artefact. Garbled skill-shell calls loop and seem not to count against the call limit.
**Paper:** draft not started; user said first reach a better LB agent. Needs the user's go and an answer on the one-account rule (runs used ziad23samer, ziadsamer, fatmazenhom, engziadsamer). Information test pass 2 was due Nov 7 (cutoff Nov 9): status unknown, ask. Evidence and predictions: docs/PAPER_NOTES.md, docs/ARCH_ANALYSIS.md.
**Working rules added this session:** commit after every run result or analysis without being asked; separate arms (one change each), small task sets first, filter, then bigger sets; pub024 as the same-run control.
**Code:** scripts/agent_clock/run_phase.py (shell for all new arms; switches WORDS, CHECKLIST, PLACES, LIGHT, READS; 19 tests), install_run.py, run_stop.py (8 tests). Builder: scripts/make_skill_arms.py (phase_arm, nnrc_arm, clock_rc, setup_arm); notebooks: scripts/train/make_skill_arms_cells.py (OUT, ARMS, TASKS); simulator data/sim/armsim.py with SIM_CELLS=... and data/venv_harness/bin/python; packer `uv run scripts/pack.py submissions/ARM`. Run table: scripts/paper/build_run_table.py -> data/analysis/run_table.jsonl.

### CHECKPOINT 2026-11-05 (older; details in the RESULT / RUN BUILT entries below and docs/PAPER_NOTES.md)
**Deadlines:** paper Nov 12 (aim to submit Nov 11; Kaggle Writeup, 3,000 words); main competition Dec 2, pick 2 finals; 1 scoring submission a day, 1 pending at a time. Rules changed since our Sep 26 saved pages: 31B, 12B, E4B, E2B allowed (one model per submission); $10k small-model bonus for E2B/E4B (must be a final pick).
**Waiting on (user runs, sends `kaggle kernels output` commands or signed links):**
- **CHECK 2026-11-12 before building lead 1 (runtime values, SWE-Doctor style; user 'okay' to lead 1): the issues rarely hold anything to run.** Of 129 public tasks, 112 issues have no code block, 17 have one, 9 have a Python block that imports the package (fastapi_14873 is the only one among r88/r89's 6 tasks; 0 of dev16). Issue texts are PR titles / descriptions (median 58 words, quartiles 20 / 141), e.g. rich_3521 'Segment.split_cells fix' + a link. SWE-Doctor (arXiv 2607.00990, read 11-12) first writes bug-reproduction tests from the issue (removing that stage costs 8-10 points in its ablation, 50 SWE-bench Pro issues, GPT-5.4-mini) and only then debugs them under PDB (removing the diagnosis costs 8 points); its models are frontier (GPT-5.4, Sonnet 4.6, DeepSeek-V4-Pro) and it costs about 2x per issue. For us the values could only come from the fixer's own check scripts through .git/agent/trace.py, the route r84-r86 already used (real function listed 6/6, solves flat, runs slower). Lead 1 put back to the user before any build.
- **RESULT r89 (data/results/2026-11-12_skill_samp6_p1 = ziad23samer/fork-of-fork-of-generation-all-shards-gpu, _p2 = ziadsamer/fork-of-generation-all-shards-gpu; 2 x 12 runs, both ended by themselves): Google's sampling ties evidc; NOT an LB candidate; the sampling line is closed.** Treatment checked in the requests: evidc_g's fixer 325 requests at T 1.0 / top_p 0.95 / top_k 64, its evidence stage at T 0.2; evidc all at T 0.2. Solved / no patch / capped / mean agent s: evidc 6/12 / 3 / 1 (+1 turns cap) / 427; evidc_g 6/12 / 4 / 3 / 409. Per task (p1 p2, evidc | evidc_g): fastapi_14419 SS | S0, fastapi_14873 SS | 0S, fastapi_15589 ES | SS, rich_3521 S0 | ES, rich_3676 EE | SE, rich_4079 00 | 00; same-run pairs 3 wins, 3 losses. Expected evidc 4.8 (2-8) -> 6, in range; both notebooks good draws (ALL ARMS p78 / p76). evidc on these 6 tasks over r88 + r89: 12/24 (fastapi_14873 0/2 in r88, 2/2 in r89: per-task run-to-run noise is large). **Bars:** time -18 s raw, model +7 s [-33, +46] (bar <= +20) -> met; first edit median request 18 vs 24.5 (bar: no more than 3 later) -> met, earlier (r53's hesitation at T 1.0 does not show in whole runs); no patch 4 vs 3 (bar <= +2) -> met; outcome: refit (3,112 runs, 95 draws) evidc_g vs evidc -2.0 points [-6.5, +2.6], P(better) 0.20 (bar >= 0.8) -> NOT met. The model's -2.0 is shrinkage (evidc's edge rests on 132 runs, evidc_g's 12 runs are pulled to the average agent); the head-to-head is an exact tie, so at best no effect. Side notes (small numbers, not effects): garbled edit calls evidc 14 in 2 runs vs evidc_g 1 in 1 run (T 0.2 resends the same garbled call; T 1.0 varies it); tokens per reply 328 vs 371; patch sizes differ between the 2 runs in 5 of 6 tasks for BOTH arms (T 0.2 runs already diverge; T 1.0 adds no visible diversity for best-of ideas). Also refit with r88: evdraft vs evidc -3.2 points, P(better) 0.08 (closed). evidc stays the top agent: dev16 22.3% [19.1, 28.2], vs pub024 +3.1 P 0.95, vs combo1 +3.7 P 0.96; evide vs evidc -1.4 P 0.26.
- **RESULT r88 NOTEBOOK 1 (data/results/2026-11-12_skill_draft6_p1 = ziad23samer/fork-of-fork-of-generation-all-shards-gpu; 12 runs): the draft-first stage FAILS on mechanics; notebook 2 not run (quota kept for r89).** evidc 3/6 solved / no patch 1 / capped 1 / 371 s; evdraft 1/6 / 1 / 1 / 295 s. Per task (evidc | evdraft): fastapi_14419 S | E, fastapi_14873 0 | S, fastapi_15589 S | E, rich_3521 S | E, rich_3676 E | E, rich_4079 E | 0. **The drafter ignored 'work fast and do not explore':** tool calls median 29 (bar <= 3): fastapi_14419 27 (26 reads), fastapi_15589 31, rich_3521 27, fastapi_14873 9, rich_3676 59 (it used the whole 470 s alone), rich_4079 78 (52 failing edit_file calls in a loop, no edit made); time median 62 s (bar <= 30 s); an edit made in 5/6. Its calls count against the task's shared budget (31), so the fixer started with little or none left (evdraft runs shorter: 295 s) and the drafter's wrong edits stayed: 3 tasks evidc solved ended E for evdraft (bar <= 1 anchoring loss). No-patch 1 vs 1 (no gain). Same as r75's scout: a thinking-off stage told to be quick does not stop by itself; the evidence stage stays short only because its script refuses a second call (ONCE); ADK YAML has no per-stage call limit. **Draft-first closed.** **Notebook 2 (data/results/2026-11-12_skill_draft6_p2 = ziadsamer/fork-of-generation-all-shards-gpu; the user ran it before the stop note):** evidc 3/6 (no patch 2, 423 s), evdraft 2/6 (no patch 0, 326 s); drafter calls 28, 9, 21, 15, 23, 55 (time median 49 s). **Pooled 12 runs each: evidc 6/12 vs evdraft 3/12; no patch 3 vs 1.** Per task (p1 p2, evidc | evdraft): fastapi_14419 SS | EE, fastapi_14873 00 | SS (the drafter's 9-call runs: a short draft helps), fastapi_15589 SE | EE, rich_3521 SS | ES, rich_3676 ES | EE, rich_4079 E0 | 0E. A patch always existing works (no patch 3 -> 1) but long drafter runs drain the shared budget and leave wrong drafts: net -3 solves. Closed stands.
- **RUN BUILT r89: evidc (control) vs evidc_g (Google's recommended Gemma 4 sampling for the fixer) on r88's 6 tasks, 1 pass per notebook, CONCURRENCY 2, cell 2 time guard 0.85 h** (user 2026-11-12 "lets go with 1", lead 1 of docs/RESEARCH_PROBLEMS_2026-11-12.md). kaggle/cells_skill_samp6 (only cell2 differs from r84's loc4), 12 runs (~0.95 h, ~1.9 h billed). Builder scripts/make_r89_arms.py (dist/evidc_g.zip 25c96cb7, pack.py OK; adk_submission's schema allows top_k >= 1): evidc_g = evidc with the fixer's configs/sampling.yaml at temperature 1.0, top_p 0.95, top_k 64 (max output 8192, thinking 4096 unchanged); the evidence stage keeps configs/evidence_sampling.yaml (thinking off, T 0.2); everything else evidc's (asserted). Sim data/sim/armsim_samp6.log: 4/4 end ok; the fixer's requests carry temperature 1.0, top_k 64. **Expected:** evidc 4.8 (90% 2-8) of 12 over two notebooks (the same tasks as r88, so evidc pools across r88 / r89); a gap >= +5 is not luck. **Bars:** time: evidc_g mean agent <= evidc + 20 s; behaviour (r53 saw hesitation at T 1.0): evidc_g's median first-edit call no more than 3 later than evidc's and no patch no more than evidc's + 2 pooled; outcome: the bank refit, P(better) >= 0.8 -> bigger run / LB candidate; also record run-to-run diversity (distinct patches per task) for later best-of ideas.
- **RESEARCH 2026-11-12 (user: "for all the problems we faced ... search the web for each one"): docs/RESEARCH_PROBLEMS_2026-11-12.md** (12 problems, sources, what we measured, what is left). New facts: the garbled calls fit a known vLLM Gemma 4 parser bug (double quotes / brackets inside strings truncate the value, PR #39070; the scorer's 0.19.1 has it); the ParallelAgent crash is a known ADK bug (adk-python #4740: compaction drops the function-call event); Google's recommended Gemma 4 sampling is T 1.0 / top_p 0.95 / top_k 64 (we run T 0.2; r53's single-step replay was against heat, a whole-run A/B never ran); Google keeps thoughts inside a tool-calling turn (so the scorer's re-sent thinking is by design); overthinking ('Analysis Paralysis', arXiv 2502.08235) and budget awareness (BATS 2511.17006) match our no-patch findings. Checked against our data: the ICML 2026 finding that prohibitions decay over long runs does not bite here (342 evidence-family runs: test files edited 0.6%, whole test suites 0, outside /workspace 0). Untested leads left: a values trace (SWE-Doctor), Google's sampling settings on the current agent, a wait-for-all team with a repro-test vote.
- **RUN BUILT r88: evidc (control) vs evdraft (draft-first stage) on 6 tasks with frequent no-patch runs, 1 pass per notebook, CONCURRENCY 2, cell 2 time guard 0.85 h** (user 2026-11-12 "build it"). kaggle/cells_skill_draft6 (only cell2 differs from r84's loc4), tasks fastapi_14419, fastapi_15589, rich_3521, rich_4079, rich_3676, fastapi_14873, 12 runs (~0.95 h, ~1.9 h billed). Builder scripts/make_r88_arms.py (dist/evdraft.zip 40d7d681, pack.py OK): evdraft = evidc + a drafter between the evidence stage and the fixer: include_contents none (fresh; the issue {problem_description} and the copied {evidence?} in its system prompt), thinking off (thinking_budget 0, max_output 2048, configs/drafter_sampling.yaml), tools run_command + edit_file only, output_key draft; prompt written fresh (scripts/agent_draft/drafter.md: print the lines where the evidence points, make one best-guess edit, reply 'DRAFT: file: change' or 'DRAFT: none'; never tests, never new files, no search, no tests; no budget numbers or numbered call plan, asserted); the fixer prompt is evidc's byte for byte + a DRAFT EDIT section at the end ('only a guess: keep it, correct it, or restore the file with git checkout -- <file> and make your own edit' + {draft?}); max_tool_calls 29 -> 31 for the drafter's print and edit; everything else evidc's (asserted). Sim (data/sim/armsim.py drafter role): the drafter's system prompt has the issue and the evidence filled, tools [run_command, edit_file]; its note reaches the fixer's system prompt ('DRAFT: <file>: ...' / 'DRAFT: none'); 4/4 and 4/4 end ok (draftsim, draft6). **Expected:** solves evidc 4.8 (90% 2-8) of 12 over two notebooks (model; evdraft as a new agent 4.4), a gap >= +5 is not luck; no patch evidc ~4.7 of 12 (its rates on these tasks 31 / 17 / 62 / 70 / 0 / 56%), evdraft ~0-2 if the drafter edits. **Bars:** mechanics: the drafter leaves an edit (non-empty diff when it ends) in >= 2/3 of evdraft runs, median <= 3 drafter calls and <= 30 s; no crashes; outcome: evdraft no patch <= evidc's - 2 pooled, evdraft solves >= evidc's - 1 pooled and no task-pass that evidc solves is lost to an anchored wrong draft in more than 1 case; mean agent time <= evidc + 25 s; then the bank refit (P(better) >= 0.8 -> bigger run / LB candidate).
- **SECOND LOOK 2026-11-12 (user: "another pass about agents worth a second look, easy fixes, stuff like that"): no dropped agent stands out and no cheap, proven fix is left for evidc.** (1) Run endings over the bank (3,140 31B runs): ok 2,079, time cap 1,039 (33%), crashes 11 (the bo3 ParallelAgent crash), turns 7, tool budget 4 -> mechanical losses are the time cap, refused edits and call forms, not crashes. (2) Top 22 agents in the bank model all sit at 19.9-21.2% on dev16 (each +-4.4): evidc 21.2% (raw dev16 39/102, capped 27%, no patch 37%, 380 s, LB 0.15), sq1c2a8rc 21.1, evidd 20.6, evide 20.5, sq1c2 20.5 (LB timeout), sq1c2a8 20.5, evid3 20.5 (LB timeout), sq1c2t7 20.3 (timeout), sk_nav_s6_32r_n2k 20.2 (raw 11/32, no patch 16%, never on the LB), ... sk_a2 19.9 (LB 0.18); raw rates differ more but on different task subsets and draws. No-patch differs by family (clock 14-17%, skill navigators 16-28%, evidence family 37-43%) without a matching solve difference. (3) evidc's losses (bad_by_agent.py, bad_call_losses.py): calls after the budget in 28% of runs (17 no-patch runs, ~5.4 solves per 100 runs; the warning few-shot failed in r87, a bigger cap failed in sk_a2 vs sk_a2_32), garbled edit calls in 18.5% of runs (a text ending with a backtick swallows the next argument 93/99; resent identically 69/99; 9 s/run), inline python -c quoting 6%, edits from memory 5%, reversed read ranges 3% (~2.5 s/run together). r81's few-shot copies: garbled 22 vs 27 calls pooled (evidc pair 2 vs 11 in 8 runs each), python -c 3 vs 123, +23.5 s/run -> the garble fix is weak and costs time. Conclusion: evidc stays the agent; the one untested idea with a new mechanism against the biggest loss (no patch from the time cap, 28% of runs) is a draft-first stage.
- **RESULT r87 (data/results/2026-11-12_skill_plan4_p1 = ziad23samer/fork-of-fork-of-generation-all-shards-gpu, _p2 = ziadsamer/fork-of-generation-all-shards-gpu; 2 x 12 runs): neither change helps; both bars fail.** solved / no patch / capped / mean agent s / tokens per reply: evide 3/8 / 4 / 4 / 423 / 652; evide_nonum 3/8 / 5 / 6 / 468 / 666; evide_warn 2/8 / 6 / 5 / 431 / 604. Per task (p1 p2, evide | nonum | warn): fastapi_14419 0E | S0 | S0; fastapi_15589 SS | SS | S0; rich_3521 00 | 00 | 00; rich_4079 S0 | 00 | 00. **Call plan (clean A/B):** without the numbers, tokens per reply +2% (bar +15%) and no patch +1 (bar +2) -> NOT met: the numbers barely change how long the model thinks; the mining gap (40% vs 65% no patch) came mostly from the other differences in those prompts (few-shot call forms, the trace prompt) and other notebooks; time +45 s raw, model +29 s [-15, +72] (not significant). **Warning few-shot:** 0 of 4 runs that saw the warning edited within 2 calls of it (evide 0 of 5), refused edits 4 vs 1 -> FAILED: the model does not react to the harness countdown even with a worked example (as combo1en2 after a gate refusal). Luck checks p12-p80 (p1 a good draw, p2 a poor one). Refit (3,064 runs, 91 draws): evide_nonum vs evide -0.8 points, P(better) 0.37; evide_warn vs evide -1.1, P 0.30; evide vs evidc -0.7, P 0.36; evidc vs pub024 +2.1, P 0.89 (still the top agent); evidefs vs evide -1.4, P 0.25. Takeaway for the user's rule: keeping or dropping budget numbers in the fixer makes no measurable solve difference; the existing evidc / evide prompts (with the plan) stay as they are.
- **RUN BUILT r87: evide (control, with the call plan) vs evide_nonum (only the budget numbers taken out) vs evide_warn (few-shot: edit on the first harness warning) on the 4 mid-rate dev16, 1 pass per notebook, CONCURRENCY 2, cell 2 time guard 0.85 h** (user 2026-11-12 "yes 2 and 3": the clean A/B on the call plan and the few-shot fix for the out-of-calls no-patch runs). kaggle/cells_skill_plan4 (only cell2 differs from r84's loc4), 12 runs (~0.95 h, ~1.9 h billed). Builder scripts/make_r87_arms.py (asserts: only prompts/fixer.md and the comment differ from evide; evide_nonum changes exactly the 6 number-bearing lines: '28 tool calls and 8 minutes' -> 'Your tool calls and your time are limited', CALL PLAN -> ORDER OF WORK with the same advice and no call numbers, 'Verify (at most 2 calls)' -> 'Verify (briefly)'; no budget number left; evide_warn keeps every evide line and adds WHEN THE HARNESS WARNS after the call plan: the harness's own line quoted ('budget_warning': 'Only 10 tool call(s) remaining (19/29 used). Finalize your edits and call submit_patch soon.'), the next call is edit_file with the best fix, after 'Tool call budget exhausted' every edit is refused, a three-step example). The user chose this minimal-change A/B over a full rewrite. dist: evide_nonum ff4ebb96, evide_warn a587a6a1. Sim data/sim/armsim_plan4.log 6/6 ok. **Expected:** solves per arm ~1.9 of 4 per notebook from the evidence family's rates (model 2.5 of 8 over two notebooks, 90% 1-5; a gap >= +4 over two notebooks is not luck); no patch per arm per notebook: with the plan ~1.8 of 4 (evide-lineage rates on these tasks 31 / 17 / 62 / 70%), without numbers ~2.7 of 4 (56 / 50 / 75 / 88%) -> if the plan matters, evide_nonum ~+0.9 no-patch per notebook (~+1.8 pooled). **Bars:** (call plan) evide_nonum's tokens per reply >= evide's + 15% pooled AND its no-patch >= evide + 2 pooled -> the plan matters (keep numbers in the fixer); both near evide -> the mining gap was the other prompt differences; (warning) in evide_warn runs that see the warning, the first edit within 2 calls of it in >= half (evide: mostly on 'budget exhausted') and fewer refused edits than evide; all: no crashes, mean agent time <= evide + 20 s; outcome read with the bank refit.
- **MINING 2026-11-12e NO PATCH (user "go for it" on the no-patch discussion; scripts/mine_bank/no_patch.py over the 318 logged evidence-family runs: evidc, evide, evidd, evidcfs, evidefs, evmap, evtrace, evall, evtrace2, evgraph, evid3, evid4).** Outcomes: solved 114, wrong patch 63, **no patch 141 (44%)**. No-patch runs had read the real-fix lines in 98% (solved 100%): they found the place. Two groups: **(1) out of calls, 52 runs (16% of all):** 29-call budget gone with a **median 241 s still left** (quartiles 159-280 s); 94% were editing at the end (last five calls: submit_patch 75, edit 67, read 53); 62 edit calls refused only because the budget was gone (other failures: no match 7, cut apart 8); in **10 of 52 the refused edits held >= half of the real fix's added lines**; the harness warning ('Only N tool call(s) remaining (u/m used). Finalize your edits and call submit_patch soon.', swegemma tools/base.py: on every result once <= 10 calls remain, if the budget >= 20) first appeared at call ~18; the first edit came after the warning in 44 of 49 runs, and the first refused edit was the 1st or 2nd call after the budget ran out in 48 of 49 -> the model edits on the 'budget exhausted' message, one call too late, not on the countdown. (Earlier: sk_a2 at 28 calls vs sk_a2_32 at 32 had the same refused-edit rate, 11%: a bigger cap moves the end, not the habit.) **(2) out of time, 89 runs (28% of all):** 18 replies, 22.2 s and 626 tokens per reply (solved 14.0 s / 408), only 25% ever tried an edit, last five calls mostly reads; no harness event reaches them (calls remain, so no warning). Same task (7 tasks): tokens per reply solved 454 vs no patch 537. **Call plan vs no budget numbers (the user's rule 2026-11-10):** on the 10 tasks both ran, fixer prompts WITH the call plan (combo1 / pub024 lineage: '28 tool calls and 8 minutes', 'Calls 1-8 ... You MUST have edited a source file by call 12'; evidc, evide, evidd, evid3, evid4) 135 runs: no patch 40%, solved 48%; prompts WITHOUT budget numbers (evidcfs, evidefs, evmap, evtrace, evall, evtrace2, evgraph) 68 runs: no patch 65%, solved 26%; same task: more no-patch without numbers in 6 tasks, fewer in 2 (sign p 0.29). Mechanism: without the plan the model thinks longer per reply (solved runs 491 vs 400 tokens per reply, 56% vs 24% of solved runs still hit the time cap; time-capped no-patch runs 826 vs 546 tokens, 28.5 vs 20.7 s per reply). Confounds: different notebooks and other prompt differences (few-shot call forms, the trace prompt); the bank model agrees in direction (evidefs vs evide P 0.26, evtrace vs evide P 0.35). The rule came from r75, where a SCOUT told 'about 10 tool calls' used 44 / 17 / 9 / 44: numbers do not cap a stage's calls, but in the fixer they seem to pace its thinking. Raised with the user, not acted on.
- **RACE INVESTIGATION 2026-11-12, step 2 (CPU sim; conclusion: a crash-free parallel form exists, but only the wait-for-all kind, worth ~+1 point, not the ~+4-point race).** (a) Two sim artifacts found and removed before trusting step 1: the fake model's tool-call ids were hashes of the call (identical across branches; real vLLM ids are random) -> SIM_UNIQUE_IDS; and the fake fixers' step was the count of visible assistant messages, which compaction removes -> SIM_STATEFUL (per-branch reply counter). With both fixed, root ParallelAgent bo3 crashed in **6 of 6** runs once compaction fired ('No function call event found', random ids), 0 without compaction. (b) **AgentTool fix:** submissions/bo3tool (sim only, not a submission) = a coordinator LlmAgent whose one tool is an agent_tool on team.yaml = ParallelAgent [bo3's fix_a, fix_b, fix_c]; pack.py accepts it. Same stress (10 big reads per fixer, ~20-23k-token requests): **6 of 6 solved, 0 compactions, 0 crashes**; Fixer A's submit inside the child session reaches the harness. Caveats measured: inside the AgentTool the fixers see only the tool's request text (a real arm must put {problem_description} in their instructions; parent state is copied into the child session); a vLLM context overflow (sim SIM_MAX_LEN=32768: prompt + max output) in any branch kills the whole task (18 big reads: 2 overflows, both tasks lost, 'ContextWindowExceededError ... Non-retryable'), so each branch must stay under ~24.5k prompt tokens at max_output 8192 (real pub024 runs uncompacted: median 22.9k, p75 28.6k); swegemma tools refuse only on the shared call / turn budget, never because another branch submitted (tools/base.py budget_gated, context.py check_budget), and the runner ends a task early only on ROOT events -> inside an AgentTool every branch runs to its end or to the shared budget: the wait-for-all form. bestof_sim.py at equal scorer time: wait-for-all best-of-2 first-finished picker 20.0 vs single 19.3 of 53 (~+1.3 points), race (first submit ends the task, root ParallelAgent only) 21.4 (~+4); a root race stays crash-free only if every branch stays under 14,336 prompt tokens (~10-12 calls each), which cuts each branch's solve rate. Sim switches kept in data/sim/armsim.py (SIM_REAL_TOKENS, SIM_BIG_READS, SIM_THREADED, SIM_JITTER, SIM_UNIQUE_IDS, SIM_STATEFUL, SIM_MAX_LEN; coordinator role); the sim notebooks are regenerated in memory from make_skill_arms_cells.py with OUT / ARMS / CONCURRENCY patched (not committed).
- **RACE INVESTIGATION 2026-11-12, step 1 (user: "yes race investigation"; CPU only): the ParallelAgent crash reproduced locally.** The sim (data/sim/armsim.py, gitignored) never fired compaction before: the fake model reported 10 prompt tokens. New sim switches: SIM_REAL_TOKENS (usage = request chars / 4), SIM_BIG_READS=N (each bo3 fixer reads N 300-line regions of fastapi/routing.py), SIM_THREADED + SIM_JITTER (overlapping branches, random reply delays); compaction summary requests are detected by ADK's prompt ('The following is a conversation history between a user and an AI agent') and counted. bo3 (ParallelAgent [fix_a, fix_b, fix_c]) with the scorer's EventsCompactionConfig (14,336 / 5 / 2 / 5; kaggle/cells_skill_bo3sim generated for the sim only): SIM_BIG_READS=6 -> request peak ~12.9k tokens, no compaction, 2/2 solved; SIM_BIG_READS=10 -> 2-3 compactions per run and 3 of 4 runs died with 'ValueError: No function call event found for function responses ids' (end=sandbox, patch 0; the 4th ended no_submit) = the GPU bo3 failure (11/24). Mechanism (ADK 1.36.1 source): flows/llm_flows/compaction.py runs token-threshold compaction BEFORE EVERY model call (CompactionRequestProcessor); apps/compaction.py _latest_prompt_token_count takes the newest usage_metadata of ANY event in the shared session (another branch's), so one branch's big context compacts the session under the others; the summary range then drops a function-call event whose response is still there -> contents.py raises -> the runner drops the patch. Next: test mitigations in the same sim (ParallelAgent inside an AgentTool = child session without compaction, plus a 32,768-token overflow check in the fake server; branches with include_contents none; branch contexts kept under the threshold).
- **RESULT r86 (data/results/2026-11-12_skill_conf6_p1 = ziadsamer/fork-of-generation-all-shards-gpu, _p2 = ziad23samer/fork-of-fork-of-generation-all-shards-gpu; 2 x 12 runs): evtrace is NOT an LB candidate (bars set before the run).** Solved / no patch / capped / mean agent s: evide 5/12 / 4 / 4 / 406; evtrace 3/12 / 7 / 9 / 466 (+60 s). Per task (p1 p2, evide | evtrace): fastapi_12942 ES | 0S, fastapi_14873 SS | E0, rich_3278 SS | 00, rich_3480 00 | 0S, rich_3506 00 | 00, rich_3676 EE | SE; same task and notebook evtrace only 2, evide only 4. Expected evide 5.7 (3-8), evtrace 5.6 (3-9) under the model, 7.6 (5-10) at face value -> evtrace's 3 is below its face-value range; luck checks evtrace p8 / p31, evide p26 / p59. **Refit (3,040 runs, 89 draws):** evtrace vs evide -0.8 points [-5.2, +3.5], P(better) 0.35 (bar: >= 0.8 candidate, < 0.6 no) -> no; time evtrace vs evide +38 s [+1, +75] (bar <= +20 s) -> fails; evtrace vs evidefs now +0.6, P 0.61 (was 0.76 before r86): r84 / r85's 5 vs 1 was luck on 3 tasks plus those tasks; evidefs vs evide -1.5, P 0.26; evidc still the top agent (21.2% on dev16, vs pub024 +2.2, P 0.90; evide vs evidc -0.8, P 0.36). **Line closed:** location aids (map, code-path tool, call graph) and the fixer_trace prompts: the tool works mechanically after the few-shot fix but solves do not move, and the place-finding prompt makes runs slower (more caps, more no-patch on new tasks). Kept for the record: scripts/agent_trace, evidence_r84-r86, submissions/evmap, evtrace, evall, evtrace2, evgraph.
- **RUN BUILT r86: evide vs evtrace on 6 mid-rate tasks outside dev16 that evtrace was never tuned on, 1 pass per notebook, CONCURRENCY 2, cell 2 time guard 0.85 h** (user 2026-11-12 "build yes" to: confirm evtrace on tasks it was not tested on; evide = evidefs's parent, which the bank model now rates above evidefs, P 0.22). kaggle/cells_skill_conf6 (only cell2 differs from r84's loc4), 12 runs (~0.95 h, ~1.9 h billed). Tasks: rich_3278 (59% of 96 runs), fastapi_14873 (64% of 81), rich_3676 (33% of 76), fastapi_12942 (62% of 69), rich_3506 (20% of 59), rich_3480 (31% of 16) = non-dev16 tasks with a 31B solve rate of 20-70% over >= 10 runs. Changed from the plan given to the user (the 5 other solvable dev16 tasks) because the evidence family there is near 0 / 100% (fastapi_11194 89%, fastapi_15589 78%, rich_3180 0/15, rich_3470 0/15, rich_3882 15/15): power to show evtrace at its face value 7% vs 24% here (expect_run.py --face evtrace, 2 notebooks). Bundles unchanged (evtrace as committed in 14523dd; evide as in r79, dist/evide.zip packed again). Sim data/sim/armsim_conf6.log 4/4 ok. **Expected:** per notebook evide 2.9 (90% 1-5), evtrace 2.8 (1-5) of 6 under the model; at evtrace's face value (+0.81 logit) evtrace 3.8 (2-6); two notebooks 5.7 vs 5.6 of 12, face value 7.6 (5-10); a gap >= +4 over two notebooks is not luck (5%), reached 24% of the time at face value. **Bars:** no crashes; evtrace's mean agent time <= evide + 20 s (LB fit); then refit: evtrace becomes the next LB candidate if evtrace vs evide P(better) >= 0.8 (bank model, all runs) and the time bar holds; 0.6-0.8 -> discuss; below 0.6 -> no.
- **RESULT r85 (data/results/2026-11-12_skill_graph3_p1 = ziadsamer/fork-of-generation-all-shards-gpu, _p2 = ziad23samer/fork-of-fork-of-generation-all-shards-gpu; 2 x 12 runs; prompts as built, the user did not ask for a rewrite):** solved / no patch / capped / mean agent s / tokens per reply: evidefs 1/6 / 5 / 2 / 387 / 404; evtrace 2/6 / 4 / 4 / 449 / 517; evtrace2 1/6 / 4 / 3 / 402 / 473; evgraph 2/6 / 3 / 3 / 437 / 532 (expected ~2.2 of 6 each; every luck check p24-p69). Per task (p1 p2): fastapi_14419 evidefs 0S, evtrace SS, evtrace2 S0, evgraph S0; rich_3521 evgraph ES, the rest 00; rich_4079 all 00 / E0. **Mechanics: the few-shot fix worked:** the code-path tool in 6/6 evtrace2 runs (13 calls with output; plain Python 1) and 5/6 evgraph runs (r84: 1 call in 12 runs); its 'files:' line named the real-fix file in 6/6 evtrace2 runs and the real fix's function was listed in 6/6 (rich_4079's hunk name '__init__' is generic, so that one is soft); evgraph 4/5 and 3/5. The graph lines were in evgraph's fixer history 6/6 but never copied into its prompt. (A first count said 0 because the tool results are JSON strings with escaped newlines; recounted from the parsed stdout.) Edits placed in a real-fix file (edit_place.py --only=graph3): 6 runs, solved 5 on the lines, failed 1 within 15 lines -> too few; **the failure on these tasks is no patch (time cap before any edit), not the place**: no patch pooled over r84 + r85 evidefs 11/12, evtrace 7/12, all fixer_trace / fixer_trace2 arms 19/30 vs evidefs-prompt arms (evidefs, evmap) 16/18. **Pooled with r84 (same 3 tasks):** evtrace 5/12 vs evidefs 1/12, same-run +4 / -0 (sign p 0.12). Bank refit (run_model.py, 3,016 runs, 87 draws; PAIRS and NULL_AS for the r84 / r85 arms added): evtrace vs evidefs +1.9 points on dev16 [-3.6, +7.2], P(better) 0.76 (bar 0.8: just under); evgraph vs evidefs +1.1 (0.64); evtrace2 vs evidefs +0.5 (0.58); evtrace2 vs evtrace -1.3 (0.32); evgraph vs evtrace2 +0.5 (0.57); **evidefs vs evide -2.1 [-7.5, +3.1], P(better) 0.22** (the fs prompt on top of evide looks worse, not better; evidefs is on the LB, pending since 11-12 07:41). Bar for the bigger run: evtrace >= evidefs + 2 pooled MET (+4), P(better) >= 0.8 NOT met (0.76).
- **RUN BUILT r85 FINAL (supersedes the first r85 build below, which was never run): evidefs vs evtrace vs evtrace2 vs evgraph on r84's 3 tasks (fastapi_14419, rich_3521, rich_4079), 1 pass per notebook, CONCURRENCY 2, cell 2 time guard 0.85 h** (user 2026-11-12, asked why the map was dropped, then "yes go for option 2": call-graph neighbours, the research-style version, instead of the plain map). kaggle/cells_skill_graph3 (only cell2 differs from r84's loc4), 12 runs, ~0.95 h = ~1.9 h billed (fits a 2h20m account). Each arm differs from the one before by one thing: evtrace (r84 bundle: the prompt, replication), evtrace2 (+ the few-shot tool fix), evgraph (+ GRAPH). **evgraph** = evtrace2 + scripts/agent_evidence/evidence_r86.py GRAPH: under 'defined at:' for each named def, 'called from:' = the innermost defs holding calls of it in non-test, non-docs source ('path:first-last qualname (calls)', most calls first, up to 6) and 'it calls:' = the repository defs its body calls (same file first). evtrace2 and evgraph are both built from evidence_r86.py and differ only in the GRAPH switch (asserted; scripts/make_r85_arms.py). Tests: `python3 -I scripts/agent_evidence/test_evidence_r86.py` (7, incl. calls written 'Table (', the def line excluded, tests / docs_src excluded, no graph for names without a def). **Offline (scripts/mine_bank/graph_offline.py: the r86 script at the real base with GRAPH off vs on; 'names the real fn' = a path:line inside the innermost def around a real-fix line or a path:first-last equal to it, one rule for both):** 72 tasks 36% -> 40% (+4); the 15 tasks with the real stage's names 27% -> 47% (+3: fastapi_14419, rich_3521 and one more); fixes past line 150 41% -> 41%. (A first measure that let any range containing a changed line count said 12% -> 31%: inflated by wide ranges, discarded.) Crash audit (evgraph's script at the base of all 128 tasks): 0 problems, graph lines in 62, median 0.3 s, max 1.8 s, tree clean, trace installed, how-to line present. Sim data/sim/armsim_graph3.log: 8/8 end ok, 'called from:' lines reach the fixer. dist/evtrace2.zip 1ba03f27, dist/evgraph.zip 8a34cbba. **Expected:** per arm ~1.1 of 3 per notebook (evidence family on these tasks 58 / 31 / 22%; model 0.8, 90% 0-2), ~2.2 of 6 over two notebooks; with r84 (same tasks) evtrace pools to 12 runs, evidefs to 12. **Bars:** evtrace2 / evgraph use the tool in >= half of their runs; evgraph's evidence carries a 'called from' / 'it calls' line in the fixer's copied lines or history in >= 2 of 3 runs per notebook; no crashes; mean agent time <= evidefs + 20 s. Read: evtrace vs evidefs pooled with r84 (prompt effect), evtrace2 vs evtrace (few-shot tool), evgraph vs evtrace2 (graph); an arm goes on to the 8 solvable dev16 x 2 notebooks if >= evidefs + 2 pooled and the bank model gives P(better) >= 0.8.
- **RUN BUILT r85: evidefs (control) vs evtrace (r84's bundle, unchanged: replication) vs evtrace2 (few-shot fixes) on the 4 mid-rate dev16, 1 pass per notebook, CONCURRENCY 2** (user 2026-11-12 after r84: "favor few shot man if it helps and we try again, make this strategy see the fixes that can be applied, tool, prompt, etc."). kaggle/cells_skill_trace4 (only cell2 differs from r84's loc4; cell 2 time guard STOP_NEW_TASKS_AFTER_H 0.85 so a 2h20m account fits: 12 runs ~0.95 h = ~1.9 h billed), builder scripts/make_r85_arms.py (asserts: evidefs byte for byte except the evidence script, the fixer prompt and the comment; no Python example outside the tool; evtrace unchanged since 14523dd). **evtrace2** = evidence_r85.py (MAP off, TRACE on, TRACE_HINT: a how-to line for the code-path tool right under the evidence header; 5 tests `python3 -I scripts/agent_evidence/test_evidence_r85.py`) + trace.py v2 (a 'files:' line with every file and its function count; the modules the check script imports listed first, in import order; v1 kept as scripts/agent_trace/trace_v1.py; 8 tests) + scripts/agent_trace/fixer_trace2.md written fresh: HOW YOU RUN PYTHON HERE (every Python check through `python3 .git/agent/trace.py`), every example that runs Python goes through the tool (check file, quoted heredoc, re-check after the edit), no budget numbers. Strategy per mechanism (from RESULT r84): tool use -> few-shot (r84's prompt showed one traced and two plain Python examples; the fixers copied the plain ones) + a tool-output line; tool output -> imports first; MAP -> dropped (right only on fastapi_14419, wrong file on rich_4079); prompt -> replicate evtrace. dist/evtrace2.zip md5 11fdc3a1. Sim data/sim/armsim_trace4.log: 6/6 end ok; the how-to line reaches evtrace2's fixer. **Expected:** per arm ~1.9 of 4 per notebook from the evidence family's rates on these tasks (model 1.4, 90% 0-3); gap >= +3 per notebook, >= +4 over two notebooks is not luck. **Bars (set before):** evtrace2 uses the tool in >= half of its runs and its 'files:' line names the real-fix file in >= half of the uses; no crashes; mean agent time <= evidefs + 20 s. Outcome read pooled with r84 (same tasks): evtrace vs evidefs (prompt effect, replication), evtrace2 vs evtrace (tool effect); an arm goes on to the 8 solvable dev16 x 2 notebooks if it is >= evidefs + 2 pooled and the bank model gives P(better) >= 0.8.
- **RESULT r84 (data/results/2026-11-12_skill_loc4_p1 = ziadsamer/fork-of-generation-all-shards-gpu, _p2 = fatmazenhom/generation-shard-4-gpu; both ran the SHORT cell 2: 4 arms x 3 tasks (fastapi_14419, rich_3521, rich_4079) = 12 runs each):** solved / no patch / mean agent s: evidefs 0/6 / 6 / 415, evmap 0/6 / 5 / 406, **evtrace 3/6 / 3 / 409** (fastapi_14419 x2, rich_4079), evall 1/6 / 5 / 472 (rich_3521). Expected ~2.2 of 6 per arm (evidence family on these tasks 58 / 31 / 22%); evidefs 0/6 has ~5% probability at those rates. Decode 29.7-29.9 tok/s (normal: not a slow draw); time caps from the agents: tokens per reply on these tasks evidc 456 (36 runs, 39% solved), evide 558, evidefs 683, evmap 681, evtrace 560, evall 740. **Mechanics:** the code-path tool was used ONCE in 12 runs (evtrace p2 rich_4079; its CODE PATH listed rich/console.py set-up first, the real file rich/markdown.py third), and the model never named it in its reasoning, while the fixers ran plain Python checks 18 (evtrace) and 30 (evall) times -> they copied the prompt's plain heredoc / /tmp examples; bar FAILED. MAP in the script output 12/12, copied into the fixer prompt 4/12 (only fastapi_14419, where the copied entry 'fastapi/dependencies/utils.py:567-704 solve_dependencies' is the real fix's function; those runs still failed); on rich_3521 the map does not hold the real function and on rich_4079 it maps rich/table.py (wrong file); bar FAILED. Edits placed (edit_place.py --only=loc4): 4 runs with an edit in a real-fix file, all on the lines (too few to read). **Prompt split, same notebooks:** fixer_trace.md arms (evtrace + evall) 4/12 vs evidefs's prompt arms (evidefs + evmap) 0/12 (Fisher one-sided p ~0.05); on these tasks evide (evidefs's parent with evidc's prompt) 4/12 and evidd 4/12 earlier -> the evidcfs few-shot prompt may hurt here (more thinking per reply, more no-patch), against r81 where the fs copies did better (18 vs 11 of 32, other tasks). evidefs is on the LB, pending (submitted 11-12 07:41).
- **RUN BUILT r84: location aids, small first trial: evidefs (control, the LB submission) vs evmap vs evtrace vs evall on the 4 mid-rate dev16 (fastapi_14419, fastapi_15589, rich_3521, rich_4079), 1 pass per notebook, CONCURRENCY 2** (user 2026-11-12 "yes please and add any idea or arm that even has a slight chance of winning, all in, man all in"). kaggle/cells_skill_loc4 (only cell2 differs from r82's a8rc8: ARMS, TASKS, ATTEMPTS 1), 16 runs; past 16-run notebooks took 1.14-1.22 h end to end (= 2.3-2.4 h of quota at L4x4's 2x billing); the same notebook on a second account = a second pass. Short version for an account with 2h21m: kaggle/cells_skill_loc4/cell2_short.py = 4 arms x 3 tasks (fastapi_15589 left out: the evidence already reaches the real function there) = 12 runs, STOP_NEW_TASKS_AFTER_H 0.85 (expected ~0.95 h = ~1.9 h billed; worst case ~1.05 h = ~2.1 h). Builder scripts/make_r84_arms.py (everything else evidefs byte for byte, asserted): **evmap** = evidence script scripts/agent_evidence/evidence_r84.py with MAP (before the per-name sections: the non-test, non-docs file using the names most, its size and its innermost defs / classes using them, most uses first, 'first-last Class.name (uses)', up to 8); script-only change, every prompt evidefs's. **evtrace** = TRACE: the evidence script writes .git/agent/trace.py (scripts/agent_trace/trace.py, embedded; inside .git so never in the patch): `python3 .git/agent/trace.py /tmp/check.py` or `... - <<'EOF'` runs the script, then prints CODE PATH = the repository functions it called (tests, stdlib, packages, module / class bodies, comprehensions and import-time calls left out), file by file in first-call order with line ranges and call counts, plus the deepest repository line of an exception; overhead ~0.2 s on 200k calls; + a fixer prompt written fresh around finding the place (scripts/agent_trace/fixer_trace.md: WHERE FIXES GO WRONG, a worked example check -> trace -> sed -n the printed range -> edit_file, evidefs's call-form examples and rules, no budget numbers; builder asserts no budget / minute / call-count words). **evall** = both. Tests: `python3 -I scripts/agent_trace/test_trace.py` (7), `python3 -I scripts/agent_evidence/test_evidence_r84.py` (4: r79's suite with MAP / TRACE off + map ranking + trace install inside .git, ONCE kept, tree clean). Offline: map on the 17 tasks with real stage names, script <= 1.0 s; e.g. fastapi_14419 MAP of fastapi/dependencies/utils.py lists solve_dependencies (the real fix's function, 3rd of 3 of 25 defs). Sim data/sim/armsim_loc4.log: 8/8 end ok, the trace runs in the real sandbox and returns the CODE PATH block (import-only check -> '(none ...)'), MAP of fastapi/applications.py printed; the run_skill_script / a.py error lines are the sim's fake fixer plan (as in every earlier sim). Crash audit (evall's script at the real base of all 128 public tasks in the local snapshots, issue-derived names): 0 problems, trace installed every time, working tree clean every time, MAP shown in 83, time median 0.3 s, max 2.5 s. Risk to watch: on rich_4079 the stage tends to pass 'Table' (bank), so evmap may show a MAP of rich/table.py, the known wrong-file pull there (13 of 44 failed runs edited it). Also checked and dropped: an edit-checkpoint arm (Coherence Collapse): only 5 of 944 failed runs ever wrote >= 90% of the real fix's added lines (solved 37%). **Expected (expect_run.py, evidc as the stand-in control, new arms as new agents):** per notebook ~1.2-1.4 of 4 per arm (90% 0-3), a gap >= +3 is not luck; two notebooks (8 runs per arm) ~2.5 (0-5), gap >= +4 not luck -> the trial checks mechanisms and large effects only. **Bars (set before):** all arms: no crashed run, evidence stage <= 15 s, mean agent time <= evidefs + 20 s; evmap / evall: MAP in the script output in >= 3/4 runs and in the fixer's copied evidence in >= 2/4; evtrace / evall: the trace used in >= 2/4 runs, and its CODE PATH lists repository functions in >= half of the uses (and, where a local snapshot has the base, the real fix's function in >= half). Carry forward to the 8 solvable dev16 x 2 notebooks if the mechanics pass AND (solves >= evidefs OR edits on the real-fix lines >= evidefs, scripts/mine_bank/edit_place.py). Next on CPU while it runs: reproduce the ParallelAgent compaction crash in the local sim (realistic token counts so compaction fires) for the race idea.
- **MINING 2026-11-12d WHERE IN THE FILE (user: "it gets the file then the problem is where ... exploration rather than exploitation"; scripts/mine_bank/edit_place.py SNAPSHOTS: each edit_file on a real-fix file placed in the base file via its old_string; compared with the lines the real fix changes; 1,394 runs with a patch on 56 tasks).** **Corrects the earlier 'right place, wrong logic' reading: within the right file, failed runs often edit the wrong place.** Closest edit per run: solved on the real-fix lines 92% / within 15 lines 7% / same function farther 0% / elsewhere in the file 1%; failed 61% / 17% / 8% / 13%. Same task (12 tasks with >= 3 solved and >= 3 failed): on the lines 89% vs 49% (11 vs 0 tasks, sign p 0.001); on or near 99% vs 65% (p 0.004); only elsewhere in the file 1% vs 27% (0 vs 7, p 0.016); read the real-fix lines before editing 92% vs 64% (11 vs 1, p 0.006). Off-target failed runs (110): 41% never read the real-fix lines at all, 59% read them and edited elsewhere. Depth: real-fix lines past line 150 (beyond one read_file window) -> failed runs off the lines 35%, never read before editing 33%; within the first 150 lines 15% / 25%. Research (2026-11-12 search): hierarchical file -> function -> line localization (Agentless, CoSIL arXiv 2503.22424, BugCerberus 2502.15292); ARISE (2605.03117: program graph + data-flow slicing tools in SWE-agent, Qwen2.5-Coder-32B: function recall@1 +17, line recall@1 +15, Pass@1 +4.7 on SWE-bench Lite); HiLoRM (EMNLP Findings 2025: sample several location candidates, pick with a reward model, line recall +12%); SWE-Doctor (2607.00990: reproduction tests alone did not help; running them under a debugger for runtime evidence did, +8-9 points on SWE-bench Pro, largest for the smaller model); Coherence Collapse (2603.24631: for strong models 60-69% of failures reached and edited the right functions). The user's pasted list mapped to our data: root-cause tracing as a prompt line would be ignored (event-triggered-rules-only) but a tool output that shows the executed code path is a structural version; linters / type checkers do not target assertion failures (83%); stale docs not seen; a repro is already run before editing in 85% of solved / 75% of failed runs (same task, p 0.58); fresh context: compaction already cuts at 14,336 tokens.
- **PARALLEL FIXERS REVISITED 2026-11-12 (user: "right file, wrong logic ... a second agent with more exploration (temp, top_p, top_k) ... revisit parallel agents: after I get the file, spawn multiple agents trying to fix"; planning, nothing built).** (1) Hotter editor: r53 replay (pub024 contexts just before the first edit, 3 samples each at T 0.2 / 0.7 / 1.0): edits on the real lines 27 / 22 / 20%, keeps looking 29 / 40 / 51%, distinct edits per 3 samples 1.3 / 1.27 / 1.0 -> heat adds hesitation, not new ideas; top_p 0.8 / top_k 20 do nothing at T0.2 (r13); locator -> editor splits (le5 / le6) solved what single agents solve (4/16) and le5 timed out on the LB. Runs already diverge at T0.2 (dev16 mid-rate tasks 18-45%), so attempts differ without heat. (2) Ceiling from per-task rates (dev16, all logged 31B runs): best of 2 / 3 / 4 with a perfect picker and a full budget each = +7.8 / +12.8 / +16.5 points. (3) bestof_sim.py re-run (53 tasks, 596 pub024 / combo1 runs, decode loss per branch, equal scorer time): single 19.3/53 at 326 s; wait-for-both best-of-2 at cap 360 s (320 s mean): first-finished picker 20.0, oracle 21.0; race (first submit ends the task) best-of-2 cap 480 s: 21.4 at 330 s, best-of-3: 21.8 at 339 s -> race ~ +4 points, wait-for-both ~ +1.3. (4) Harness facts (ADK 1.36.1 / swegemma source): a root ParallelAgent shares the session -> compaction crash risk (bo3 11/24; race3 0/4 with prompts over 14,336 in 3/4); an AgentTool child runs in a fresh Runner + InMemorySessionService with NO compaction (no crash) but can pass max_model_len 32,768 (pub024 uncompacted peak median 22.9k, max 38.4k; 9/24 would overflow at max_output 8192); the runner only ends a task early on ROOT events (agent_runner.py 859 / 920), so a race inside an AgentTool waits for all branches; the time cap is an asyncio.timeout around the run (enforced inside tool calls). Race3's other failures: shared call budget drained, an empty submit_patch ended the race, scout time; with the evidence script as the localizer the scout problem is gone. Next if the user wants it: CPU-only checks first (reproduce the compaction crash in the local sim with the real harness config, test mitigations; measure uncompacted context per call), then a small trial.
- **BUILT r83 evidh + OFFLINE CHECK 2026-11-12 (user "build" after MINING 2026-11-12b): built, tests pass, offline check says it adds no information -> no GPU trial recommended.** evidh = evidefs + scripts/agent_evidence/evidence_r83.py (scripts/make_evidh.py; dist/evidh.zip md5 0fa7b806, pack.py OK; everything but the script and the agent.yaml comment is evidefs byte for byte, asserted): per name, git blame of its def / class body (or the source lines using it) over the last 300 commits only (HEAD~300..HEAD keeps it cheap; root commits are boundaries), and the newest commit that wrote some of it (hash, date, commits before this checkout, message, up to 4 lines it wrote), right after 'defined at:'. Tests: `python3 -I scripts/agent_evidence/test_evidence_r83.py` (7: r79's suite on the r83 script with the section off + 6 new). **Offline check (scripts/mine_bank/evidence_offline.py SCRIPT [--stage-only] SNAPSHOTS: checks out each task's base in the local snapshots, runs the script with the names the real evidence stage chose (bank logs; else code-like names from the issue), and asks whether the output shows the commit that wrote the newest line the real fix changes):** with issue-derived names on 109 tasks, evidefs's script already shows that commit in 15/24 tasks whose fix lines are within 50 commits (62%), 19/57 within 300, 27/109 overall; evidh 15/24, 23/57, 31/109 (+4 tasks, none among the most recent). With the real stage's names (17 tasks): identical (culprit 4, any fix-line commit 7, real-fix file named 10, for both). Where the old script misses, the issue's names point at code other than what the fix changes, and blaming that code does not reach it. evidh stays built; a GPU trial would test a change that adds no new lines on these tasks.
- **MINING 2026-11-12c (user: "analysis of the failed runs, what evidence or text in the history may have steered its way off"; scripts/mine_bank/steering.py replays each logged 31B run's history in order: issue text, harness instructions and workspace file listing split apart, evidence copied / script output, tool outputs by call kind, the model's own text and calls).** (1) Failed runs whose edits touch no real-fix file (143 with tracked edits): the wrong file first appeared in the model's own text 57% (it picks from the file listing; solved runs: real-fix file 53%) or a search output 40% (solved 27%); evidence 1%. (1b) Runs whose FIRST edit is outside the real-fix files: 169, solved 2 (1%); source: model's own text 55%, search output 40%, evidence 1%; files: other source 150, docs/docs_src/examples 19. (2) Evidence copied into the fixer's prompt: names a real-fix file 112 runs 46% solved, only other files 101 runs 32%, NOTHING RELEVANT 56 runs 39%; same task 3 vs 2 tasks (no effect beyond task difficulty); only 4 of 59 failed evidence-stage runs edited a wrong file the evidence named. (3) Old tests (25 tasks whose real test change rewrites existing test lines): 20 runs saw one fail after editing, solved 11 (55%) vs 27% of the rest, 2 changed course: old tests did not mislead. (4) Same task, solved vs failed patches (15 tasks): first edit in a real-fix file 94% vs 70% (10 vs 1 tasks, sign p 0.012); read the real-fix file before editing 99% vs 91% (p 0.18); tests after editing 32% vs 20% (p 0.18); other habits equal. **Conclusion: little in the history steers runs off; the failing runs mostly misread what to change in the right file, and the off-target minority start from the model's own pick or a grep hit, not from the evidence.**
- **MINING 2026-11-12b (user: "what if we can get the info ... get the git log or something and make a file that is like as if the issue text is with us"; scripts/mine_bank/fix_line_age.py over the 3 local snapshots, base found for 109 of 128 public tasks by date + the real fix's old lines; the snapshots' hashes differ from tasks.jsonl's base_commit).** (1) What the real reports added in the info test (rescued short tasks): the reporter's trigger and expected behaviour, e.g. rich_3480 'infinite loop in append' -> report 'a.append(a)' (appending a Text to itself); rich_4079 'Inline table code' -> report names TableDataElement.on_text and inline code in table cells; rich_3944 'fix fonts' -> nerd-font icons became double width in 14.3.0; rich_3772 -> 'raise e from e' loops. (2) Is it in git history? git blame of the lines the real fix changes: newest such line written within 20 commits of the base in 15/109 tasks (14%), within 50 in 24 (22%), within 100 in 38 (35%), over 300 commits back in 52 (48%); many recent ones are fastapi features extended days after they landed (fastapi_14419: 2 commits, same day; rich_3521: 55 commits, 6 days). The rescued short tasks are mostly old code (rich_3480 3,220 commits back, rich_4076 3,052, rich_3471 236; rich_3772 54, rich_3934 81; rich_3944 / 4079 newer than the snapshot). Bank solve rate recent (<= 50 commits) 35% vs older 39%. So the history can explain ~1 task in 5 (a regression or a just-added feature: the commit that wrote the lines and its message); the trigger / intent a reporter gives is mostly not in the repository. (3) Earlier forms of the idea: model-written briefs (r60 scouts: right tests and the exact earlier commits on the buggy lines, but 129-242 s, fixer left 4-13 calls, all failed), self-written reports (srep7/srep8 pooled 12 vs 14 of 76, short 8 vs 8 of 56), a no-tool hunch (r60+r62 pooled 9 vs 9); the fixed one-call script injected into the fixer (evid* -> evidc) is the form that worked (+2.4 points vs pub024, P 0.92). (4) Next, if wanted: test offline whether evide's evidence output already reaches the commit that wrote the fix lines on the 24 recent tasks; only if it misses them, add a location-driven history section (git log -L / blame on the defined names) to the script, no extra model stage.
- **MINING 2026-11-12 (user after evidc's 0.15: "I need more ... what deserves a prompt or skill revision ... what can we merge, what when placed together made things worse"; scripts/mine_bank/patch_vs_gold.py, scripts/stats/luck_carryover.py; build_run_table.py now writes edited_files / gold_files).** (1) Bank: 57 agents with >= 16 runs, all 18.3-21.5% on dev16 (evidc top, +2.4 vs pub024, P 0.92); task explains 91% of solve variance, agent ~0.1%. The public 'lb-0-22-4-config-files' (ccuuuuy, research/raw/kernels/lb_2026-11-10) = pub024's settings with a reworded prompt: the 0.18-0.22 crowd is our family plus luck; 0.29 (17/58) is beyond luck. (2) **'Complete fix' prompt idea REFUTED before any GPU:** pooled, wrong patches are smaller (0.83x vs 1.09x the real fix) and miss a real-fix file 51% vs 14%, but WITHIN the same task (15 tasks with >= 3 solved and >= 3 wrong patches) wrong patches are BIGGER in 11 of 15 (median 1.23x; sign p 0.12): the pooled gap is task difficulty. Place: of wrong patches whose edits are tracked by path (1,061), 84% touch the real-fix file (solved: 1,247 of 1,248); wrong-file patches (16%) sit mostly on never-solved fastapi_13920 (55) and rich_4079 (17, rich/table.py instead of rich/markdown.py). Failures are right file, right size, wrong logic = the intended behaviour is misread (information), not a prompt-fixable completeness or location habit. (3) **Public vs private luck (user: 'a lucky run means it is lucky on private too'):** one scoring run covers ~120 tasks (58 public, rest private), so only a run-wide effect is shared; per-task chance is not. Model: at our measured run-wide sd (0.22 logit, 83 notebook runs) corr(public, private) ~0.10 and a run +3 tasks lucky on public is ~+0.5 task on private; if the scorer's run-wide luck is ~0.5 logit, corr ~0.35 and ~+1.2-1.5 tasks. One identical public bundle's sd over 5 draws (2.07 tasks) is above the 1.48 our run-wide sd predicts (chi-square p ~0.10): a weak hint the scorer's run-wide luck is larger; 5 draws cannot pin it. So picking the higher public score among equally good agents carries some private gain (roughly 15-50% of the public excess), not all of it.
- **RUN BUILT r52: screen of 6 arms on 16 tasks** (user 2026-11-06: separate arms, few tasks, then the best on bigger sets), kaggle/cells_skill_screen16 (only cell2 differs from cells_skill_srep8), 1 pass, 96 runs, ~5.4 h. Tasks: SCREEN16 in make_skill_arms_cells.py, 15 solved 10-90% across all logs + rich_4077; picked, so only for filtering. Arms: pub024 control; pubclock = pub024 procedure, 8 min, 28 calls, thinking 4096, shell scripts/agent_clock/run_phase.py: stop 60 s after the last edit, refusal with no edit at 210 s or the 12th shell call (22 total calls = ~11 shell calls, ~199 s), test request after an edit; nn36 = new 448-word prompt, no digit or number word (builder asserts it), [state] LOOK / EDIT NOW / CHECK / FINISH, thinking 2048, 8 min, 36 calls, same rules, refusal 270 s or 15th shell call; nn32 = 32 calls, 240 s or 13th; nn36c = + checklist; nn36p = + other places and related tests after an edit. 12 unit tests (test_run_phase.py), sim OK (data/sim/armsim_screen16.log). Filter, set before the run: 16 tasks x 1 pass has sd ~2 solves, so it only drops clear losers: keep arms with solves at least pub024 minus 1 and mean wall at most pub024 plus 10 s; if more than 3 remain, rank by no-patch rate. Survivors go on an unpicked set against pub024 before any submission. Fit checks: nn arms have no LB record at 36 calls; 32 at 8 min fits (sk_a2_32).
- **RULE 2026-11-08 (user): first trials are small.** New arms first run on the 4 mid-rate dev16 (fastapi_15589, fastapi_14419, rich_3521, rich_4079; solved ~20-40% historically), 1 pass, pub024 control; only promising arms get a bigger run. r60 rebuilt that way: kaggle/cells_skill_scout4 (6 arms x 4 tasks = 24 runs, ~1.5 h; only the task lines differ from cells_skill_scout8, which stays as the bigger follow-up). On 4 tasks the trial catches breakage, scout time, empty briefs and large effects only. Carry forward: solves >= pub024 + 1, or = pub024 with fewer no-patch runs; mean agent time <= 420 s; no broken runs.
- **RUN BUILT r60: scout -> fixer** (user 2026-11-08, "incorporate all we learnt, be creative"), kaggle/cells_skill_scout8 (only cell2 differs from r59), builder scripts/make_scout_arms.py. Idea: wrong patches sit on the real lines (64%) and fail assertions (83%), so the model lacks what the right behaviour is; real added information took 2/38 -> 15/38 and the model's own rewrite added nothing; the workspace keeps the repo's tests, changelog and real git history (78 git log calls in all logs). A scout (run_command only, include_contents none, issue in its system prompt, thinking 1024) quotes repo evidence; its final reply is saved by output_key and injected into the fixer's system prompt ({key?}, ADK inject_session_state), so compaction cannot drop it. Fixer = pub024's recipe rewritten fresh, started fresh with the issue in its system prompt, without the three dead graph tools. Arms: pub024; sc_none (fixer alone: structure control); sc_tests (existing tests); sc_hist (git log -S / show, changelog); sc_both (one scout, both); hunch (no-tools first read, close to srep: wild card). Calls 28 / 33 / 33 / 34 / 28, 8 min. No ParallelAgent (bo3 compaction crash 11/24). 8 winnable dev16, 1 pass, 48 runs, ~3 h. Sim OK: brief in the fixer's system prompt in 6/6 scout runs, hunch 2/2, no unfilled template, all end ok. Carry forward to a bigger set (set before the run): solves >= pub024 + 1, or solves >= pub024 with fewer no-patch runs; and mean agent time <= 420 s. Also read: scout seconds and calls, share of briefs saying NOTHING RELEVANT, whether the fixer's first edit is in a file the brief named. Predictions: scout 40-90 s; sc_tests / sc_both 0 to +2 vs sc_none; hunch = sc_none +-1; sc_none = pub024 +-1.
- **RUN BUILT r64: r63's arms with their mechanism fixed** (user 2026-11-08 "build it"), kaggle/cells_skill_fix6 (only cell2 differs from r63), 4 arms x 6 tasks x 1 pass = 24 runs, ~1.5 h. Tasks: fastapi_11194, 14873, 15589, 14419, rich_3278, 3521 (pub024 solved 27-71% of each before; expect ~2.9 of 6). Arms (scripts/make_mine_arms.py, ARMS_R64): **evid2** = evid1 with scripts/agent_evidence/evidence.py ONCE = True (after one search with names it writes .git/agent/evidence_done; any later call prints ALREADY DONE ... reply EVIDENCE READY; a call without names does not count); **autochk2** = autochk with the checker's thinking 4096 -> 1024 (max output 4096); **cap2k32** = cap2k with max_tool_calls 32 (28-32 calls fitted the LB before). dist zips validated. Sim (data/sim/armsim_fix6.log): 8/8 end ok, the evid2 second call refused in 2/2, pub024 sees the evidence and the CHECK READY line, cap2k32 max tokens 2048. Bars (set before): solves >= pub024 + 1 or = with fewer no-patch runs; mean agent time <= pub024 + 25 s; no broken runs. Mechanism reads: evid2 stage = 1 search and < 30 s; autochk2 checker < 60 s and check run after an edit; cap2k32 calls used and time.
- **RUN BUILT r82: sq1c2a8rc vs evidc (same-run control) on the 8 dev16 tasks any agent ever solved, 2 passes per notebook, run on both accounts = 4 passes, CONCURRENCY 2** (user 2026-11-11 "lets re run it again on dev16 for 2 passes and see if this is luck or good and update the stats artifact"; then chose 8 solvable tasks x 4 passes over the full dev16 x 2 at the same GPU time: power 44% vs 26% if sq1c2a8rc is as good as its e24 run). kaggle/cells_skill_a8rc8 (only cell2 differs from r81: ARMS, TASKS, ATTEMPTS 2, EARLY_STOP_MAX -1), 2 arms x 8 tasks x 2 passes = 32 runs per notebook, estimated ~1.9-2.1 h each (evidc's per-task walls + sq1c2a8rc at 265 s solved / 490 s failed x the task rates, / 2 + setup). Tasks: fastapi_11194, fastapi_14419, fastapi_15589, rich_3180, rich_3470, rich_3521, rich_3882, rich_4079 (dropped: fastapi_13920 0/57, 14258 0/59, 14306 0/57, 14487 0/65, 15280 0/65, 15800 0/59, rich_3468 0/59, rich_3934 0/59 bank runs). sq1c2a8rc = the bundle that ran r41 (unchanged since b2c6fdb): fixer -> finisher, skill shell work/scripts/run.py with the clock line, checklist, repeat block, 80 calls, 8 min, thinking 4096. Sims: data/sim/armsim_a8rc16.log (first build, full dev16 x 1) and armsim_a8rc8.log: 8/8 end ok, pass 2 runs, sq1c2a8rc commands through run.py return '[clock] N s of 480 used', budgets 80 / 8 min vs evidc 29 / 8 min; the error lines are evidc's sim-model calls to a tool its fixer lacks and the sim's fake a.py plan (also in armsim_evide4.log). **Expected (scripts/stats/expect_run.py, before the run):** per notebook (16 runs each) evidc 6.2 (90% 4-9), sq1c2a8rc 6.2 (4-9), equal-agent gap band -4..+4; pooled 4 passes (32 each) evidc 12.4 (9-16), sq1c2a8rc 12.4 (9-17) under the model; face value (sq1c2a8rc +0.92 logit = its 40/48 vs fitted 35.7) sq1c2a8rc 17.3 (13-22), gap +4.9 (90% -1..+10). **Bar (pooled, 32 runs each):** gap sq1c2a8rc - evidc >= +6 = not luck (luck alone 3.5%; reached 44% of the time if it is as good as e24 said); gap <= +1 = the e24 showing was mostly luck; between = inconclusive (then the bank model's shared effect and P(better) decide what we say). Also report each arm's observed vs expected percentile, per-notebook gaps, sq1c2a8rc's mean agent time on these tasks (LB fit context: 8 min cannot fit, see SECOND LOOK). After the run: refit run_model.py and refresh the stats page (user asked).
- **RESULT r82 NOTEBOOK 1 (ziadsamer, data/results/2026-11-11_skill_a8rc8_p1; fatmazenhom's notebook not run yet at 11-11 19:40, its output was still r81 pass 1):** sq1c2a8rc 7/16 vs evidc 7/16, gap 0. Per task (pass 1, pass 2; S solved, E edited, 0 no patch): fastapi_11194 SS / SS, fastapi_14419 0S / ES, fastapi_15589 0S / SS, rich_3180 E0 / E0, rich_3470 0E / 00, rich_3521 0E / 00, rich_3882 SS / SS, rich_4079 S0 / 00 (sq1c2a8rc / evidc); same task and pass: +1 / -1. No patch 6 vs 7; 8-min timeouts 6 vs 6 each; mean agent time 383 vs 375 s (+8 s). Call forms (pair_bar.py): sq1c2a8rc 0 form errors, 10 garbled calls, 14 skill-argument slips; evidc 3 form errors, 39 garbled calls, 22 `python -c`, 6 runs hit the call budget. **Against the pre-run expectations (expect_run.py --exclude a8rc8 --gap 0, bank without this run):** model evidc 6.3 (90% 4-9), sq1c2a8rc 6.4 (4-9), gap 0 (90% -4..+4), P(gap <= 0) 0.58; face value (+0.89 logit) sq1c2a8rc 8.8 (6-12), gap +2.4 (-1..+6), P(gap <= 0) 0.21. So gap 0 is typical if sq1c2a8rc is an average agent and a 1-in-5 outcome if its e24 run was its true level: this half leans toward luck, not settled (the bar is on the pooled 4 passes). Luck checks (leave-the-run-out): evidc 7 vs 6.4 [4-9] p64, sq1c2a8rc 7 vs 6.3 [3-9] p64, whole run 14 vs 12.7 p69. **Bank refit (2,936 runs, 82 draws; spreads task 6.04, agent 0.21 (was 0.15), draw 0.24, axt 0.03):** sq1c2a8rc vs evidc on dev16 +0.2 points [-4.0, +4.7], P(better) 0.54 (axt 0.30 sensitivity +0.2 [-4.6, +5.0]); time +1 s [-29, +31]; sq1c2a8rc dev16 21.3% [17.8, 27.0], evidc 21.0% [17.7, 26.6], evidc vs combo1 +2.4 [-1.6, +6.4] P 0.88. Stats page refreshed (9 assets re-uploaded, datasets v4; pair sq1c2a8rc vs evidc added to run_model.py PAIRS). expect_run.py gained --exclude (score a run against the bank without it) and --gap. **Next:** the user runs cell2 of kaggle/cells_skill_a8rc8 on the fatmazenhom notebook (or decides to stop at one notebook); then pool against the bar.
- **RESULT r82 POOLED (notebook 2 = ziad23samer/fork-of-fork-of-generation-all-shards-gpu, data/results/2026-11-11_skill_a8rc8_p2; same 8 tasks x 2 passes):** notebook 2 evidc 8/16 vs sq1c2a8rc 6/16 (per task evidc / sq1c2a8rc: fastapi_11194 S0 / ES, fastapi_14419 0S / S0, fastapi_15589 SS / S0, rich_3180 EE / E0, rich_3470 00 / 0E, rich_3521 0S / SS, rich_3882 SS / S0, rich_4079 S0 / 00); sq1c2a8rc hit 8 min in 10/16 runs (evidc 2), mean agent time 450 vs 346 s. **Pooled 4 passes: sq1c2a8rc 13/32 vs evidc 15/32, gap -2 -> below the bar's +1: the e24 showing (40/48) was mostly luck.** Pre-run scoring (expect_run.py --exclude a8rc8 --passes 4 --gap -2): model evidc 12.6 (9-17), sq1c2a8rc 12.8 (9-17), P(gap <= -2) 0.32; face value sq1c2a8rc 17.6 (13-22), P(gap <= -2) 0.03 (so the data are ~10x likelier under 'average' than under 'as good as e24'). Same task and pass: +5 / -6 (pair_bar), sign p 1.00. Time: +56 s/run raw on these tasks (16 vs 8 capped runs); bank time model +18 s [-10, +47]. Calls: sq1c2a8rc 1 form error, 101 garbled, 40 skill-argument slips; evidc 3 form errors, 58 garbled, 36 `python -c`, 9 runs hit the 29-call budget (14 refusals). Luck checks: notebook 1 evidc p61, sq1c2a8rc p63; notebook 2 evidc p81, sq1c2a8rc p41; both draws +0.04 logit. **Bank refit (2,968 runs, 83 draws; spreads task 6.02, agent 0.22, draw 0.22, axt 0.01):** sq1c2a8rc vs evidc -0.3 points [-4.6, +4.2], P(better) 0.45 (axt 0.30: -0.4 [-4.9, +4.4]); evidc dev16 21.5% [18.2, 27.1] = the top agent; evidc vs combo1 +2.9 [-1.2, +7.1] P 0.93 (same-run +13/-4), evidc vs pub024 +2.4 [-1.0, +6.1] P 0.92. **Decision:** the clock family (sq1c2*) is closed: no solve gain over evidc, slower, and every 7-8 min skill-shell agent timed out on the LB. Stats page refreshed (9 assets, datasets v5).
- **SECOND LOOK sq1c2a8rc 2026-11-11 (user: "sq1c28rc deserves a second look, a way to make it faster"): the data does not back it; no arm built (planning).** Raw: 40/48 (83%) on e24 vs pub024 49% / evidc 54% / combo1 34% on the same 24 tasks, a8rc > pub024 on 12 of 14 tasks with differing rates (sign p 0.013), mid tasks 9/12 vs pub024 49/147. But all 48 runs are one notebook run (2026-11-02_skill_e24a8r, draw effect +0.28) on tasks picked for being solved, never next to pub024; pub024's 49% is weighted toward its many dev16 runs inside e24 (in the one same-run e24 test, r35, sq1c2t7 18 vs pub024 15). Same-run pairs, every clock agent vs pub024 (e24t7, dev16a6, clockrc8, setup8, setup8b): +13 / -11, sign p 0.84 -> the clock family ~ pub024. Bank model: sq1c2a8rc effect +0.10 logit [+-0.15], dev16 20.4% [17.5, 25.8] like everyone; in-sample observed 40 vs fitted 35.7. Why slow: model decode is 95% of its time (278 of 293 s; tools 14 s locally), thinking ~55% of output chars (68% in failed runs); solved runs 255 s, failed runs all at the 480 s cap; at an LB-like 20% solve rate ~435 s local mean vs pub024 ~379 s by the same arithmetic (limit ~380: evid3 at +13 s timed out). Every speed route is already measured: 6-min cap (sq1c2a6) fits, LB 0.12 / 0.10; 7-min skill shell (sq1c2t7, ~352 s locally) timed out on the LB anyway (skill-shell scorer slowness, unexplained); run_command wrapper (a8rcx / rcx2 / rcx3) the model skipped the wrapper, 5/24 vs pub024 10/24 same-run at ~460 s; thinking 2048 did not cut time in Oct (r44 a6rnt -21 s, solves equal), 1024 lost hard-tier solves, thinking off scored 0.08-0.13 publicly; no callbacks are registered by the scorer (swegemma: none; adk_submission CallbackRegistry closed), so clock events need a tool-output wrapper. Reading: a faster sq1c2a8rc would be sq1c2a6-like on the LB; not worth an LB slot or GPU quota on this evidence. Side check: task-adjusted time model evidc vs pub024 -0.7 s, evide vs evidc -15.5, evidcfs vs evidc +19 -> evidefs ~ pub024 + 3 s.
- **BUILT evidefs = next LB submission (user 2026-11-11 after r81 pass 2: "yeah I think add the fix since we know it doesn't harm but may help, so be it"; no confirmation run).** scripts/make_evidefs.py: evide's bundle with evidcfs's prompts/fixer.md and its own agent.yaml comment; the parents change disjoint files of evidc (evide: the evidence script; evidcfs: the fixer prompt), asserted, and every other file is evide's byte for byte; no new prompt text. pack.py OK (10 files, 23.7 KiB), dist/evidefs.zip md5 245b5c39. Mock sim (data/sim/armsim_evidefs.log; sim-only cells folder built by overriding make_skill_arms_cells.py's OUT / ARMS / TASKS at import, deleted after): 4/4 runs end ok; evidefs fixer requests 19/19 carry the examples and 0/19 the budget numbers, evide's 19/19 the budget numbers and 0/19 the examples; evidence stages identical (6 requests each), evidence in every fixer system prompt. Expected vs evide (r81 bank model, shared fs effect): ~+3 points on dev16 [-4, +12], P(helps) 0.80; time: fs +23.5 s/run in r81 (CI includes 0), evide was -20 s vs evidc -> evidefs ~ evidc + 3 s. Risk: evidc's LB time fit is still unknown (PENDING); evid3 timed out. The LB score cannot confirm the gain (+-3 tasks of draw noise on 58).
- **RESULT r81 PASS 2 + POOLED (data/results/2026-11-11_skill_fs4_p2 = ziadsamer/fork-of-generation-all-shards-gpu, the same 32-run r81 notebook on a second account; 1.84 h): pass 2 fs 11/16 vs originals 5/16; pooled over both passes fs 18/32 vs 11/32 -> suggestive gain, not established.** Pass 2 per agent (original -> fs): pub024 1 -> 3, combo1 1 -> 3, evid3 3 -> 2, evidc 0 -> 3; pooled pub024 2 -> 5, combo1 2 -> 4, evid3 4 -> 4, evidc 3 -> 5. Pass 2 mechanics (pair_bar.py): form-error runs 2 vs 4, calls 2 vs 4 (few on both sides, so the gain is not from fewer form errors); garbled edits 21 vs 8 calls (evid3fs 17 in one run); heredoc 37 vs 0, python -c 0 vs 61; mean agent 409 vs 391 s (+18). Both passes: solved 18 vs 11, no patch 7 vs 8, capped 3 vs 4, agent 408 vs 385 s (+23.5), form-error runs 7 vs 12, calls 7 vs 21, after-budget runs 11 vs 10. Where the gain is: of 12 fs-only solves, 9 are originals' WRONG patches turned right (3 no-patch); runs reaching 470 s+ fs 13 (10 solved) vs originals 7 (2 solved); first source edit median 243 vs 251 s; python checks after the edit in 18/22 vs 20/21 runs (no visible checking difference) -> mechanism unknown; the fs prompts differ in two ways (examples + no budget numbers / numbered plan, the user's rule), either could matter. **Statistics:** expected per side with these 4 agents' own pre-r81 task rates 14.0 (90% 9-19): fs 18 = p91, originals 11 = p16; gap 90% null band -6..+6, P(gap >= 7) 0.045; same-task pairs 12 vs 5, exact one-sided p 0.072, paired OR 2.40 [0.79, 8.69]. Bank model refit (2,904 runs, 81 draws; spreads task 6.07, agent 0.15, draw 0.26, axt 0.02) luck checks: pass 2 evidc 0 of 4 = p2 (unlucky), originals p17-p79, fs p48-p81, ALL ARMS 16 vs 16.6 p43; pass 1 ALL ARMS 13 vs 17.0 p12. Shared fs effect in the bank model (scripts/stats/treatment_effect.py: copies count as their original + one unshrunk beta): beta +0.35 logit [-0.46, +1.16], OR 1.42 [0.63, 3.20], P(beta > 0) 0.80; on the 16 cells run +7.6 points [-11, +25]; on dev16 ~+3 points [-4, +12] for each agent; pass 1 alone beta -0.23 (P 0.35), pass 2 alone +0.94 (P 0.94). The bank model is weaker than the paired test because the originals' bank history on these tasks is better than their r81 showing. Per-pair random-effect contrasts (shrunk by the 0.15 agent spread) stay within +-1 point. Reading: the no-numbers + examples prompt does no harm to solves and may help (P 0.80); time +23.5 s/run (LB fit risk: evid3 timed out on the LB); a +3-point effect needs > 256 runs per arm to confirm, +10 points ~128. Picked tasks (chosen for form errors), so per the same-run-control rule any adoption needs unpicked tasks.
- **RESULT r81 (data/results/2026-11-11_skill_fs4_p1 = fatmazenhom/generation-shard-4-gpu; 32 runs, 1.8 h, estimate 1.85 h): the few-shot examples change the form of calls as intended, but by the bar set before the fs copies fail (form-error runs and time), and solves are inside the luck band -> no fs arm goes to the LB; few-shot form fixes closed.** Solved 13/32; expected before the run 14.4 (90% 10-19) -> ~p31, inside; the model's leave-this-run-out prediction is 17.5 [12-23] (p10, inside) because it uses all agents' task rates (fastapi_14873: all agents 69%, these 4 agents 43%; the agent x task spread is estimated ~0, so the model cannot keep agent-specific task rates; these differences may be draw / time-cap confounds of other families, e.g. clock arms on e24); observed per task 4/8, 4/8, 4/8, 2/8 (fastapi_14873, fastapi_15589, rich_3278, rich_3676) matches the 4 agents' own rates (43/51/56/25%). Rule for expectations: use the agents' own task rates when they have >= ~10 runs there, else the model. Per arm (solved of 4; model luck percentile, fs scored as its control = the null): pub024 1 (p18) / pub024fs 2 (p46); combo1 1 (p16) / combo1fs 1 (p19); evid3 1 (p13) / evid3fs 2 (p41); evidc 3 (p71) / evidcfs 2 (p38). **Pooled fs vs control (16 runs each; scripts/mine_bank/pair_bar.py):** solved 7 vs 6 (same-task pairs fs +5 / control +4, sign p 1.00); no patch 5 vs 5; capped 3 vs 2; mean agent 408 vs 379 s (+29; paired 95% CI -16 to +74; time model per pair +9 / +17 / -6 / +12 s, each +-45); form-error runs 5 vs 8 (paired swap test p 0.19; vs the bank's rate for these agents and tasks, expected 9.3, p 0.015); form-error calls 5 vs 17 (-71%; paired p 0.012, bank p 0.002); garbled edits 1 vs 19 calls, 1 vs 5 runs (not targeted; bank rate 20% of runs -> 1/16 has p 0.13, not clear); after-budget runs 5 vs 6, refused calls 9 vs 10, tail 21 vs 24 s/run. Adoption: heredoc python 58 vs 0, python -c 3 vs 62, sed -n 12 vs 12, edits whose old_string was copied from printed output 19/27 vs 19/30. Model (refit with r81: 2,872 runs, 80 draws, spreads unchanged), dev16 points fs - control: pub024fs +0.3 [-3.9, +5.3] P 0.56, combo1fs +0.4 [-4.4, +5.5] P 0.56, evid3fs -0.8 [-6.0, +4.5] P 0.39, evidcfs -2.3 [-7.5, +2.7] P 0.19. **Bar (set before):** form-error runs <= half the controls' FAIL (5 > 4; calls cut 71%); time <= control + 15 s FAIL (+29 raw, but its interval includes 0); after-budget runs not up by > 2 ok (5 vs 6); solves fs >= control ok (7 >= 6); no-patch fs <= control ok (5 = 5). Reading: as in r69 / r76, examples change form, not decisions; the shift to heredoc scripts costs time (r69: +70 s; here +29 s raw), which eats the ~5 s per run the form errors cost (MINING 11-11g: at most ~1 solve per 100 runs, far below what any run can detect: +10 points needs ~128 runs per arm). evide stays the next LB submission. run_model.py now also scores a changed copy as its control in the luck check (NULL_AS), adds an ALL ARMS row per run and writes the axt = 0.30 sensitivity pairs itself (largest shift 0.5 points); the mining readers take --only=FOLDER_SUBSTR. With r81 in the bank: evidc vs combo1 +3.2 points [-1.4, +7.8], P(better) 0.91 (same-run +13 / -3); evidc tops the agent list (21.8% on dev16). Stats page refreshed (scripts/stats/export_dash.py OUT_DIR writes its 9 datasets; upload each as an asset, then point datasets/<name>.source.url at it).
- **STATS MODEL 2026-11-11 (user: "from all our runs ... use statistical techniques to know if runs are luck or not, I need data oriented approach from now on"; scripts/stats/run_model.py, numpy only, `.venv/bin/python scripts/stats/run_model.py data/analysis/stats_model.json`, ~1 min; page: https://claude.ai/artifact/Mf8mXPF6ToLNonBi5ARNpQ "Run Bank Statistics").** Hierarchical logistic model of every 31B agent-comparison run (2,840 runs, 69 tasks, 109 agents, 79 notebook runs; E4B / 12B and the info arm excluded): logit P(solved) = mean + task + agent + notebook run (draw) + agent x task, normal random effects, spreads by maximum Laplace marginal likelihood (Nelder-Mead; EM was too slow near zero). Spreads (logit): task 6.05, agent 0.24, draw 0.24, agent x task 0.015 (barely identified: refit with 0.30 changes every comparison by < 0.4 points). Latent variance shares: task 91.5%, single-run chance 8.2%, agent 0.1%, draw 0.1%. Agent time (Gaussian, same structure): task 55%, single-run 35%, agent x task 5%, agent 4%, draw 1%; sigma agent 25 s, residual 72 s. **Agents:** every agent's expected dev16 solve rate lies in 19.4-21.5% (base 18%), intervals all overlap; top evidc 21.5% [17.8, 27.8]. **Pairs (dev16 points, 95%, P(A better))**: evidc vs combo1 +2.6 [-2.0, +7.6] P 0.87 (same-run +11/-3, sign p 0.06); evidd vs evidc -0.8 [-5.9, +4.7] P 0.38; evide vs evidc -0.7 [-5.8, +4.4] P 0.38; combo1 vs pub024 -0.2; evid3 vs pub024 +1.5 P 0.77; nn32 / nn36p vs pub024 +1.1 P 0.69; 0 of 22 comparisons clear zero. Time: sk_a2 vs pub024 -35 s [-60, -10] (the only clear time difference); evide vs evidc -15 s [-49, +20]; combo1en / en2 vs combo1 +30-34 s (borderline). **Luck checks (leave-the-run-out, 90% range):** r76 plus4 evidc 3 of 4 = p95 and combo1 0 = p13 (the 3-vs-0 that promoted evidc was a lucky + unlucky pair); r79 evide4_p2 evide 3 = p95; r80 evide16_p1 evidd / evide 5 = p92; everything else inside the band. **Luck band** (two copies of one agent side by side on dev16, 90%): 16 runs per arm +-3 solves, 32 +-4, 64 +-5, 128 +-7. **Power** (one-sided 5%): +10 points needs ~128 runs per arm for 80% (64 runs: 60%); +5 points > 256 runs; at our usual 16-32 runs per arm only gains of ~+20 points are detectable. Consequences: our A/B runs of 4-16 tasks cannot rank agents that differ by a few points; decisions between near-equal agents should weigh time (LB fit) and mechanism evidence, and claims of a gain need the model's interval, not raw counts. Rule (memory data-oriented-stats): state expected solves with a range before each run, report observed vs expected with a percentile and the model contrast after.
- **RESULT r80 (data/results/2026-11-11_skill_evide16_p1 = engziadsamer/arms-again, _p2 = fatmazenhom/generation-shard-4-gpu; both notebooks ran r80 (r81 not run yet); 2 x 30 runs, 1.56 / 1.59 h, estimate was ~1.8 h): evidc, evidd, evide all 8/20; by the bar set before, evide passes and evidd fails on time; the richer evidence works as a mechanism but adds no solves.** Solved / no patch / mean agent s per pass: p1 evidc 4/3/353, evidd 5/4/383, evide 5/3/340; p2 evidc 4/3/376, evidd 3/4/372, evide 3/5/349. Pooled (20 runs each): evidc 8/6/365, evidd 8/8/378 (+13), evide 8/8/345 (-20). Tasks outside r79 (11194, 14487, 15280, 3180, 3470, 3882): 4/12 for all three; r79 tasks 4/8 for all three. Mechanics (evidence_reads.py): history block evidc 10/20, evidd 18/20, evide 18/20 (on the 5 tasks where evidc has none: 8/10 for each new arm); gold file in the script output 10/20 vs 14/20, in the copied reply 8/20 vs 12/20; NOTHING RELEVANT / 1-line 4 vs 2; 'used in source' lines in 4/20 evide runs; stage median 8-9 s (max 15), script 0-2 s. With r79: evidd vs evidc +3/-2, mean agent 395 vs 391 s; evide vs evidc +4/-3, 370 vs 391 s. Bar (set before): solves >= evidc ok for both (8 = 8); no-patch <= evidc + 2 ok for both (8 <= 8); mean agent <= evidc + 10 s: evide ok (-20), evidd FAIL (+13); outside-r79 not below by > 1 ok (4 = 4 = 4); mechanics ok (block 8/10 >= 80%, stage 8-9 s, script <= 2 s). -> evide becomes the next LB submission after evidc's pending score (dist/evide.zip, c102bf1d, pack.py OK; dist/submission.zip stays evidc until then). Caveat: evide and evidd differ only where 'used in source' lines appear (4/20 runs), so their 33 s time gap is mostly per-run noise (~+-40 s); evide's time edge over evidc (-23 s in r79, -20 s in r80) is consistent but not attributable. Reading: more and better evidence reaches the fixer, but on these tasks it did not turn into solves; the LB (58 other tasks) is the next judge and the submission is time-safe (same stage cost as evidc). LB evidc still PENDING (submitted 11-11 09:02).
- **RUN BUILT r81: pub024, combo1, evid3, evidc each next to a few-shot-fixed copy, on 4 tasks where these agents make the fixable form errors, 1 pass, CONCURRENCY 2** (user 2026-11-11 "keep 1,2,5,6 in a clean notebook with the prompt fixes on subset of tasks the gain is expected and i will run it"), kaggle/cells_skill_fs4 (only cell2 differs from r80), 8 arms x 4 tasks = 32 runs, estimated ~1.85 h (1.7-2.0; per-task mean walls of these agents x 8 / 2 + 10 min setup). Tasks (bank, these 4 agents): fastapi_14873 (runs with a form error 57%, solved 43%), fastapi_15589 (37%, 49%), rich_3278 (50%, 56%), rich_3676 (92%, 25%); rich_3934 has the most (95%) but was never solved. Builder scripts/make_fewshot_arms.py: pub024fs (afc32be3), combo1fs (bc1a565b), evid3fs (f8423ddc), evidcfs (f02bdfb8); each new prompt written in full = the original's text + an EXAMPLES OF CORRECT CALLS section (print the lines with sed, then copy them character for character into old_string; a Python check as a quoted heredoc, never python -c with quotes inside quotes; a /tmp scratch file through the shell, never write_file, never a tool name in the shell; read_file with start_line before end_line) + reproduce / last-resort checks through the heredoc instead of python -c + 'copy old_string from lines you printed' + no budget numbers (HARD LIMITS numbers, the numbered CALL PLAN -> 'ORDER OF WORK' without numbers, 'at most 2 calls' -> 'briefly'; user rule; the controls keep theirs as they ran, so the fs arms differ in two ways: examples and no numbers). Everything else is the original's (asserted: other files byte-identical, step 1 and DECISION RULES unchanged, evidence sections identical). Sim data/sim/armsim_fs4.log: 16/16 runs end ok, every fixer request of an fs arm carries the examples and no '28 tool calls', the controls carry the budget line, evidence stages unchanged. **Bar (set before; 4 tasks catch breakage, mechanics and large effects):** mechanics, fs vs its own control pooled over the 4 agents (16 runs each side): runs with a form error (edit text from memory, broken inline python, /tmp write_file, tool name / python in shell, shell quoting, reversed read range) at most half the controls'; no runaway heredoc scripts (r69: +70 s): mean agent time fs <= control + 15 s; calls after the budget not up by more than 2 runs (the numbers are gone). Outcome: solves fs >= control and no-patch fs <= control, pooled. Read with bad_by_agent.py / time_vs_bad.py limited to the r81 folders (add a folder filter) and CTRL=<control> analyze_screen.py per pair.
- **MINING 2026-11-11g (user: "add to this table what could have been saved if the few shot ones were added and actually worked"; time_vs_bad.py, section IF THE FEW-SHOT FIXES WORKED, dev16, >= 32 runs).** Assumes the form errors (edit text from memory, broken inline python, tool name / python in shell, shell quoting, write_file to /tmp, reversed read range) never happen. Saved = their calls and model seconds; rescued = runs lost to an edit refused at the budget whose edit would have fitted in the slots those calls used; solves = rescued runs x the task's right-patch rate (upper estimate); time-capped runs not counted as rescued (a few seconds rarely turn a capped no-edit run into a patch). Results: evidc 0.19 calls / 4.5 s per run (1.1% of agent time), 2/48 runs rescued, lost 42% -> 38%, ~1.4 solves per 100 runs (~0.8 of the LB's 58 tasks, inside the +-3 draw noise); combo1 0.29 / 4.7 s (1.3%), 2/104 rescued (tasks with ~0 right-patch rate), 45% -> 43%, ~0.05 per 100; pub024 0.50 / 13.6 s (3.6%), 8/282, 44% -> 41%, ~1.1 per 100; evid3 0.50 / 14.5 s (3.6%), 1/40, 42% -> 40%, ~0.65 per 100; clock and sk_* arms 0.03-0.23 calls / 0.8-4.2 s, 0 rescued. Conclusion: in our line few-shot form fixes are worth ~5 s and ~1 solve per 100 runs at best; the after-budget tail (~18 s/run) and the time cap (25-30% of runs lost) are the large items.
- **MINING 2026-11-11f (user: "the agents that lost most to time in terms of ending because of time or due to bad calls which are somehow correlated, in a table by sort"; scripts/mine_bank/time_vs_bad.py [MIN_RUNS] [--dev16]).** Lost = no patch AND (the run hit its time cap OR a bad call explains it: edit refused after the budget with no working edit before / garbled edit never fixed / last reply a call written as text). The all-task view is confounded (the clock arms ran e24 = tasks picked for being solved, 58-83% solved), so the ranking uses dev16 only (1,663 runs). dev16, agents with >= 32 runs, sorted by lost: combo1 45% (104 runs; capped no patch 25%, bad calls 23%), pub024 44% (282; 24 / 21), sq1c2a6rnt 44% (32; 44 / 3), sq1c2a6rn 44% (32; 44 / 3), evid3 42% (40; 30 / 15), evidc 42% (48; 27 / 15), sk_ad2 41% (32; 25 / 22), sq1c2a6 34% (32; 34 / 0), sk_p1 19% (32; 12 / 9), sk_a2 18% (40; 10 / 10), sk_nav_s6_32r_n2k 12% (32; 9 / 6), sk_nav_s6_32 9% (32; 9 / 0); evidd / evide 50% each on 8 runs (r79's slow draw). Link: the two losses hit different runs (runs lost to both: 0-5 per agent); on the same task a run with a bad call hits the time cap +8.6 points more often (dev16; raw 41% vs 38%; all tasks +3.9) = weak. The call budget and the time cap are the two exits: runs that hit the budget are capped 11% (no patch 60%), the others are capped 47% (no patch 34%). For our line time is the larger loss (capped without a patch 25-30% of runs) than bad calls (15-23%); the 80-call clock arms lose almost only to time (75% of their dev16 runs capped).
- **FINE-TUNING FOR BAD CALLS? (2026-11-11, user: "if it is not for few shot then maybe finetuning? check that https://www.rubrik.com/blog/ai/25/training-ai-coding-agents-with-reinforcement-fine-tuning-llms"): no, for this competition and these errors.** The article (Predibase's 'Training an Expert Coding Agent with Reinforcement Fine-Tuning', May 2025; predibase.com now redirects to rubrik.com, which returned 403 to our fetch, so read via search summaries and the plushcap mirror; full text not seen): RFT (reinforcement fine-tuning) of Qwen2.5-Coder-32B on ~10 prompts for one narrow job (Stripe Billing API integrations), graded in Runloop devboxes by ast-grep checks that the right Stripe calls with the right parameters appear; API-call accuracy 33% -> 71%. Why it does not carry over: (1) it is one narrow domain with a cheap, exact reward per sample; our hidden test is ~120 tasks from private repos (must generalise) and our reward (hidden tests pass) needs a 6-min multi-turn rollout in the sandbox per sample; GRPO groups of 8 over even 50 tasks = 400 rollouts per step = ~21 h of 4xL4 per step at 2 at once, impossible in Kaggle quota before Dec 2; (2) our own three LoRA attempts lost to base and CREATED bad calls: 12B teacher-imitation v1 0/16 dev16 (loops), v2 23/44 vs base 27/44 on OOD-45 (submit_patch repeated x11-x51, failing-retry streaks), 31B self-distilled (210 own resolved runs, ~32 h quota) 0/7 vs base 3/7 dev16 early -> parked; forum 748051: nobody clearly beat base with LoRA; (3) time: LoRA decode ~11% slower (DECEM, forum) = ~41 s/run on evidc's 371 s of model time, more than ALL of evidc's bad-call time (23 s/run, MINING 11-11e), so even a perfect fix would be net slower on an LB where +14-26 s already timed out evid3; (4) the costly bad call (edits refused after the budget) is a decision, not a format; its tail has a cheap message-tied lever (MINING 11-11d) and the evidence direction makes first edits earlier (r79). Format-only errors that RFT handles well (garbled native syntax) cost evidc ~1-3 s/run.
- **MINING 2026-11-11e (user: "what is the pattern of bad calls and what might be solvable by few shot" + "i need break down per agent not generic"; scripts/mine_bank/bad_patterns.py (shape of each kind) and bad_by_agent.py (per agent: runs hit, calls, s/run, the kind's pattern in that agent, few-shot-able vs not)).** Patterns (all agents): garbled edit = a backtick where the string should close ('...\n`,old_string:' swallows the next argument) in 75-95% of them, and resent identically in 50-87% (the model repeats the broken call); 83% lose old_string because the model writes filepath, new_string, old_string in that order; edit text not in file = old_string written from memory in 96-100% (first line seen then the rest paraphrased 49%, nowhere 47%; whitespace-only 0.4%, stale 1%); inline python broken = python -c with escaped quotes / f-strings / several statements in 99% (SyntaxError 56%, 'unexpected character after line continuation' 24%, unterminated string 14%); write_file outside /workspace = /tmp test or repro scripts in 98%; tool name in shell = 'read_file ...' 75%, 'write_file X << EOF' 25%; read range reversed (54 calls) = end = start - 1 in 52%; call written as text = cut at the output-token limit (4096 / 8192 tokens, giant edits copying long signatures, e.g. fastapi_15280 'vibe') in 44%, a complete call the parser missed 56%; after budget = the refused call was the run's first edit in 35% of refused calls. Per agent, lost s/run = few-shot-able (form errors: edit from memory, inline python, tool name / python in shell, shell quoting, /tmp writes, read range) + not few-shot (garbled native call syntax, after-budget tail, text calls): pub024 38.9 = 14.0 + 24.9 (inline python 22% of runs, /tmp 15%, garbled 12%, after budget 31%); combo1 30.3 = 4.7 + 25.5 (after budget 36%, edit from memory 11%, garbled 8%, tool name in shell 6%); evidc 23.1 = 4.5 + 18.5 (after budget 25%, inline python 12.5%, garbled 4%, edit from memory 4%); evid3 43.8 = 16.9 + 26.9 (/tmp 18%, inline python 18%); sk_a2 20.1 = 3.4 + 16.7 (edit from memory 18%); sk_a2_32 15.6 = 4.0 + 11.6; sk_fr2 22.9 = 7.3 + 15.6; gate skill-shell arms nn32 / nn36c / nn36p 54-71 = 17-35 + 29-36 (/tmp 40-69% of runs, garbled skill calls 55-76%); clock arms sq1c2* 9-24 = 0.5-5.5 + 8-18 (garbled skill calls 38-80% of runs: positional_args strings closed by a backtick); evidd / evide 8 runs each (too few). Few-shot evidence in this project: an example reliably changes the FORM of a call (gate prefix 24% -> 100%, r76; heredoc use 4 -> 19, r69, with a side effect: longer scripts, +~70 s/run) but did not change a DECISION (the move after a refusal, r74: edit_file next 2/9). So few-shot fits the form errors (for evidc ~4.5 s/run, combo1 ~4.7, pub024 14) and not the garbled native syntax (fixed by the message-tied rule instead), the after-budget tail (a message-tied rule, MINING 11-11d) or token-limit cut-offs.
- **MINING 2026-11-11d (user: "and regarding time as well not just solves"; scripts/mine_bank/bad_call_losses.py TIME section): time lost per run = model seconds producing bad calls before the budget ran out + the after-budget tail (from the request whose call was first refused to the run's end).** Arms with >= 40 runs: nn36p 73 s/run (18.8% of agent time: write_outside 25 s, skill_args 21 s), nn32 58 s (15.2%), nn36c 54 s (14.7%), evid3 47 s (11.6%: bad calls 25 + tail 22), pub024 43 s (11.6%: 20 + 22), combo1 35 s (9.2%: 7 + 28), sk_fr2 29 s, evidc 26 s (6.5%: 6 + 20), sq1c2a6i 25 s, sk_a2 23 s, sk_a2_32 18 s; the 80-call clock arms (sq1c2*) 10-21 s, all bad-call generation (skill_args, garbled), no tail. The message-tied rules (garble, /tmp fix) cut bad-call generation from ~20 s/run (pub024, evid3) to ~6-7 s (combo1, evidc). What is left in the current line is the after-budget tail: the budget runs out in 25-36% of runs (evidc 12/48, combo1 37/104, pub024 150/486), and then the run goes on ~77-80 s (1.5 refused calls + ~4 model requests of ~20 s each, the harness keeps the agent going) with nothing that can change the tree. Lever noted (not built, for discussion): a rule tied to the exact message 'Tool call budget exhausted' (no number, so not a prompt budget) telling the agent that every further call is refused and to reply in one sentence; would save ~20 s/run on evidc if it holds, solves unchanged (refused calls do nothing); matters only if the LB time is tight (evidc's pending score is the time-fit test; evid3 timed out at +14-26 s).
- **MINING 2026-11-11c (user: "the most agents that could benefit from this are?"; scripts/mine_bank/bad_call_losses.py, 2,840 runs with outcomes): the 28-29-call single-fixer agents, i.e. our current line.** A no-patch run counts as lost to a bad call when an edit was refused after the budget with no working edit before (budget_edit), a garbled edit was never followed by a working edit (garble_end), or the last reply was a tool call written as text (text_end). All arms: 267 of 882 no-patch runs (budget_edit 221, garble_end 39, text_end 7). Estimated solves lost (each lost run x its task's right-patch rate among runs that made a patch; optimistic: the 11-09 replay found refused edits valid only on fastapi_15589): 98 of 1,058 solved. Per arm with >= 40 runs: combo1 23% of runs lost (23 budget_edit), ~7.2 solves per 100 runs; pub024 16.7%, 5.7; evid3 15.9%, 4.7; evidc 14.6% (7 budget_edit), 4.0 (~2 of the LB's 58 tasks); sk_a2_32 7.1%, 3.3; sk_a2 8.3%, 1.6. Small arms in the same family: combo2 31% (16 runs), kf2 13.6% (22), sk_a2_t05 18.8% (16). The clock / skill-shell arms (sq1c2*, 80 calls) lose ~0 this way (but timed out on the LB). Lost runs concentrate on rich_4079 (64), rich_3470 (35), fastapi_15280 (19), rich_4075 (17), fastapi_15589 (16), 14419 (15).
- **MINING 2026-11-11b (user: "in all our agents, did we experience bad tool calling, even after stating in prompt"; scripts/mine_bank/bad_calls.py over 2,840 31B runs, 77,882 tool calls): yes, several kinds; a prompt rule tied to the exact error message cuts that error (garble rule about halves it, the /tmp fix ~10x), but the budget line does nothing, and edits refused after the budget are the costliest bad call.** Bank-wide, runs with each kind: garbled edit arguments ('mandatory input parameters are not present') 10.0%; skill calls with garbled / missing arguments 23.1% (skill-shell arms only, e.g. positional_args array cut by a backtick: '{"file_path": "scripts/install.py`,skill_name:"}'); calls after 'Tool call budget exhausted' 17.5%; edit old_string not found 7.1%; read_file start_line > end_line 1.4% of runs (54 calls; corrected 11-11e: the first count also matched 'ValueError' inside file contents read successfully); write_file outside /workspace 9.6%; inline python that does not parse 8.6%; shell quoting errors 3.2%; Python run as bash 1.7%; a tool name typed as a shell command 0.7%; calls to tools the agent lacks 0.5%; a tool call written as text in the reply ('<|tool_call>call:edit_file{...', the parser missed it, the call never ran) 1.3% (in 7/36 such runs it was the agent's last reply); the same failed call resent identically 8.6%. Rules: garble rule in the prompt: garbled edit calls 11.6% of edit calls / 5.1% of runs vs 26.4% / 10.6% without (cross-arm; same-run r69 kf 53% -> 8%, r70/71 kf2 0/30 vs pub024 4/28); /tmp: pub024's 'scratch in /tmp' line without the fix 13.3% of runs wrote outside /workspace, with combo1's fix ('write_file only writes inside /workspace', heredoc) 1.3%, no /tmp line 0%. Current family (combo1 / evidc / evidd / evide, 168 runs): garbled edits 6.0% of runs (10 runs, 8 still made a patch, 2 solved), edit not matching 7.7%, read range ~4% (corrected 11-11e), inline python syntax 6.5%, tool name as shell 3.6%, text call 1.2%; model time spent producing these is small (garbled 1.9 s/run, no-match 2.6, others < 1.5). **The costly one: calls after the budget in 31.5% of current-family runs (14.4 s/run of model time); in 36 runs an edit_file was refused because the budget was gone, 34 of them had no earlier working edit and ended with no patch = 34 of the family's 77 no-patch runs (44%)**, although the prompt states the call limit and that an unedited tree scores zero (same as MINING 2026-11-09 for pub024). Closed levers for it: more calls (sk_a2_32 refused-edit share unchanged), fewer calls, forced edit by refusal (costs 60-80 s of thinking per refusal), prompt budgets (user rule: none).
- **RUN BUILT r80: evidc (control) vs evidd vs evide on dev16 minus its 4 never-solved and 2 lowest-rate tasks (10 tasks), 1 pass per notebook, CONCURRENCY 2** (r79's bar: an arm that passes goes to the full dev16 x 2 passes; both passed), kaggle/cells_skill_evide16 (only cell2 differs from r79). User 2026-11-11 (limited GPU quota): 'drop 2 tasks please that are never solved of the 16'. Never solved in the whole bank: fastapi_13920 0/61, fastapi_14306 0/61, fastapi_15800 0/65, rich_3468 0/65 (incl. evid3's full-history runs); dropped the two slowest, rich_3468 (476 s mean wall over the evidence-era runs) and fastapi_13920 (420 s). Then (user 2026-11-11 'drop another 2') also dropped the other two never-solved tasks, fastapi_14306 (0/61) and fastapi_15800 (0/65); every remaining task was solved at least once in the bank. Then (user 'drop 2 more') the two lowest-rate tasks, fastapi_14258 (1/65) and rich_3934 (1/65), both 0 in every evidence-arm run and given the same evidence by evidc and evidd (history block and gold file in both). **Final: 10 tasks (fastapi_11194, 14419, 14487, 15280, 15589, rich_3180, 3470, 3521, 3882, 4079) x 3 arms = 30 runs per notebook, estimated ~1.8 h per notebook (1.7-2.0 h).** Caveat: only 6 tasks lie outside r79 now (11194, 14487, 15280, 3180, 3470, 3882), so the 'not worse outside the mid-rate tasks' check is weak; further cuts would leave little beyond the r79 tasks. Estimate method (first computed for 14 tasks / 42 runs): the phase time equals the sum of run walls / 2 within 5% in r77 / r78a / r79 (ratio 1.00-1.05); evidence-arm mean wall per task -> 4.53 h of runs / 2 = 2.27 h + ~10 min notebook setup (kernel total minus phase: 0.15-0.16 h) = ~2.4 h per notebook (16 tasks would be ~2.8 h); draw-to-draw spread ~+-10% (r77: 1.85 vs 1.66 h) -> 2.2-2.7 h. Run the same cell2 on both notebooks = 2 passes. Agents byte-identical to r79's (evidd 687850c0, evide c102bf1d), so no new sim. evide differs from evidd only where a chosen name has no def / class line (dev16 candidates from the bank: 15589 convert_underscores, 14873-style on_startup, 15280 vibe, rich_3468 BrokenPipeError, rich_3470 record, rich_3180 fold). **Bar (set before):** over both passes (32 runs per arm): a new arm becomes the next LB submission (after evidc's pending score) if solves >= evidc's, no-patch <= evidc's + 2, mean agent time <= evidc + 10 s, and on the 6 tasks outside r79 not below evidc by more than 1; if both pass, the one with more solves, tie -> evidd (the smaller change). Mechanics: history block in >= 80% of runs of the new arms where evidc lacks it, stage <= 15 s median, script <= 3 s.
- **RESULT r79 (data/results/2026-11-11_skill_evide4_p1 = engziadsamer/arms-again, _p2 = fatmazenhom/generation-shard-4-gpu; 2 x 16 runs, 0.99 / 1.05 h; a slow draw, many 480 s caps): evidd and evide PASS; the full-history search works exactly as intended.** Pooled (8 runs per arm): solved / no patch / mean agent s: combo1 1/5/436, evidc 3/5/458, **evidd 4/4/438, evide 4/4/435**. vs evidc: evidd +2/-1 (+ fastapi_14419 in both passes, - rich_4079 p2), evide +2/-1 (+ 14419, rich_3521; - rich_4079). Per pass: p1 evidc 1, combo1 0, evidd 2, evide 1; p2 evidc 2, combo1 1, evidd 2, evide 3; mean agent p1 453 / 443 / 399 / 394, p2 463 / 429 / 476 / 475. Mechanics (evidence_reads.py): 'what X changed around it' block evidc 2/8, evidd 8/8, evide 8/8; gold file in the output and in the copied reply evidc 4/8, new arms 8/8; NOTHING RELEVANT evidc 2/8 (both on 15589), new arms 0/8; stage 4-14 s, median 10 s for all three; script 0-1 s; one search per run (two runs made 2 calls, the second refused). evide's 'used in source' lines appeared only on 15589 (the other chosen names have def / class lines), so on these 4 tasks evide ~ evidd. First source edit earlier in the new arms (p1 282 / 254 s vs evidc 443; p2 369 / 328 vs 393). On 14419 the history block shows 4632f353's lines in fastapi/dependencies/utils.py (the gold file): evidd 2/2, evide 1/2, evidc 0/2 (evidc's earlier 4/4 there shows how noisy single tasks are). Bar (set before): stage 10 s <= 15 ok, script <= 1 s <= 3 ok, history block 8/8 >= 3/4 ok, no NOTHING RELEVANT on 15589 ok; outcome solves 4 >= 3 ok, no patch 4 <= 5 ok, time -20 / -23 s pooled ok (p2 alone +13 / +12, inside +15) -> both go to the full dev16. evidc vs combo1 over r76-r79: 15 vs 7 solved in 52 pairs (+11/-3, sign p 0.057). 8 runs per arm on 4 tasks: +1 solve is within noise; r80 decides.
- **RUN BUILT r79: small first trial of a richer evidence script: combo1, evidc, evidd, evide on the 4 mid-rate dev16, 1 pass, CONCURRENCY 2** (user 2026-11-11 "now lets continue building"; checkpoint agenda item 2), kaggle/cells_skill_evide4 (only cell2 differs from r78a's gate4), 16 runs, ~1 h. Builder scripts/make_evid_arms.py: each new arm is evidc's bundle file for file with only skills/evidence/scripts/evidence.py and the agent.yaml comment changed (asserted); no prompt is written or changed (the fixer is evidc's = combo1's byte for byte + the evidence section, so its old budget line stays as it ran). Script scripts/agent_evidence/evidence_r79.py (the old scripts/agent_evidence/evidence.py stays as make_mine_arms.py uses it), 9 tests: `python3 -I scripts/agent_evidence/test_evidence_r79.py`. **evidd** (687850c0) = evidc + git log -S over the whole history (no 500-commit limit) with a streaming git call (GIT_FLUSH=1; at CALL_TIMEOUT 4 s the complete lines printed so far are kept, instead of nothing) + name cleaning (Segment.split_cells -> split_cells when the last part has an underscore or 6+ characters, Prompt.ask stays whole because -S matches substrings: ask ~ task; foo() -> foo; phrases dropped when a real name is left). **evide** (c102bf1d) = evidd + SOURCE_LINES: a name with no def / class line gets up to 4 'used in source' lines (non-test, not docs/, docs_src/, examples/). Checks: on a 522-commit test repo evidc's script finds no commit for a name changed 520 commits back, the r79 script finds it with its changed lines; on the local snapshots the script takes 0.5-0.7 s (fastapi_15589 with evide: 'used in source' lines in fastapi/dependencies/utils.py 536 / 803-806, the gold function's neighbourhood, plus the 2025-03 fix commit evidc missed); pack.py OK for both; sim data/sim/armsim_evide4.log: 8/8 runs end ok, one evidence call, a second refused, the evidence in the fixer's system prompt, evide's 'used in source' lines present. **Bar (set before; 4 tasks catch breakage, timing and large effects):** mechanics: evidence stage <= 15 s median, script done <= 3 s, the 'changed around it' block in >= 3/4 runs of evidd / evide (evidc on these 4 tasks: 4/16 runs), NOTHING RELEVANT on fastapi_15589 not in both runs of the new arms (evidc: 4/4). Outcome: an arm moves to the full dev16 x 2 passes if solves >= evidc's, no-patch <= evidc's and mean agent time <= evidc + 15 s.
- **MINING 2026-11-11 (evidence stage; scripts/mine_bank/evidence_reads.py over 106 evidence-stage runs: evid3 44, evid4 22, evidc 40, + evchk 6): evidc's r76 speed-up removed the most useful evidence.** (1) evidc's script ran git log -S over the last 500 commits only. That dropped the 'what X changed around it' block in 5 of 16 dev16 tasks (evidc has it in 16/40 runs, evid3 in 37/44; per-task losses: fastapi_14306, 14419, 15589, rich_3521, rich_3882). On fastapi_14419 and fastapi_15589 (two of the four mid-rate tasks) evidc's output never reached the gold file (0/8 runs) where evid3's did (8/8): 15589's fix commit (92aad5689, 2025-03, 'Fix convert_underscores=False for header Pydantic models', the lines in fastapi/dependencies/utils.py the gold patch touches) is older than the last 500 commits; evidc saw only a docs commit and its stage replied NOTHING RELEVANT 4/4. (2) The limit bought nothing: on the local snapshots (fastapi 7,185 commits, rich 4,293, requests 6,294) the whole-history search takes 0.2-0.6 s vs 0.1-0.2 s limited; evid3 ran 0-3 s on Kaggle (median 1). evid3's LB timeout came from its stage thinking (15-48 s), not its script; the checkpoint's 'git log -S can be slow on large private repos' was never measured. (3) 74 of 174 per-name searches found no def / class line (parameters, options, attributes: convert_underscores, scopes, on_startup); 17 of 177 chosen names were dotted (Segment.split_cells, 10) or phrases (validation errors, 7), which the def and history searches cannot match. 58 of 112 runs gave a single name although the prompt asks for two to four. (4) The fixer sees the script's full output in its history from its first request (16/16 runs, as an ADK 'For context' message) until compaction drops it (kept in ~60% of its requests), plus the copied lines in its system prompt all run: a better script output reaches the fixer whatever the stage copies. (5) Where evidence cannot help: fastapi_13920, 15280, 15800 and rich_3468 give NOTHING RELEVANT in every evidence arm and are 0 solved in every arm (gold in docs_src or no issue name in the patch). (6) Caveat: evidc still solved 14419 4/4 without the history block, and 15589 2/4 with NOTHING RELEVANT; the evidence content is not proven to be the cause of the evidence family's gain on the mid-rate tasks (task effects dominate), so r79 tests it rather than assumes it.
- **RESULT r78a (data/results/2026-11-11_skill_gate4, fatmazenhom/generation-shard-4-gpu, 16 runs, 1.02 h): no gate arm beats evidc; the gate family is closed for the LB; evidc is the submission.** Solved / no patch / mean agent s: combo1 1/2/405, evidc 1/2/437 (+1 14419, -1 15589), evgate 1/2/438, evgate1 2/2/432 (+1 rich_4079). A slow draw for every arm (many 480 s caps). Mechanisms: commands through the gate 98/99 (evgate) and 76/78 (evgate1); evidence stage 4-14 s (median 8-10), 1 call; evgate refused calls 3 (stop rule only) = 9 s a run; evgate1's single late refusal per run still cost 83 s a run (5 refused calls, 334 s of model time: the model thinks long after any refusal). Bar: mechanics evgate ok, evgate1 FAIL (83 s > 30 s); outcome solves >= evidc ok for both, no-patch ok, time <= combo1 + 15 s FAIL for both (+33 / +27; evidc itself +32 in this draw; per-run noise ~ +-40 s). evidc vs combo1 over r76 + r77 + r78a: 12 vs 6 solved in 44 pairs (+9/-3, sign p ~0.15), mean agent time +12 / -1 / +32 s per round (~+10 s). Gate state words alone add nothing measurable (as warnings did before: 6-11% move), and every refusal costs ~60-80 s of thinking: forced edit cannot pay for itself within the LB time. Decision proposed: submit evidc (dist/submission.zip = dist/evidc.zip, md5 9755bb6c); it doubles as the time-fit test of the cheap evidence stage.
- **RESULT r78b (data/results/2026-11-11_skill_race3_4; the user ran it on engziadsamer/arms-again, gate4 on fatmazenhom; 8 runs, concurrency 1, 0.9 h): race3 FAILS; the gated scout works, the engineers do not; race parked.** Solved / no patch / mean wall: combo1 2/2/372, race3 1/3/436 (+63 s); race3 solved fastapi_15589 (engineer A at 433 s), lost rich_3521. Scout: notes in 4/4 with all six fields, done at 145 / 200 / 392 / 126 s (median 172; bar <= 200 ok); it batches several commands per reply, so the 9-command refusal came at 27-49 s, then it replied (rich_3521: two refusals, then long thinking to 392 s). Gate clock checked: t7rc's clock line matched the agent's own elapsed time within 1 s in r76, so the gate start is right. Engineers: 13-29 calls each with no budget text; the shared 44-call budget ran out mid-race in fastapi_14419 (~285 s) and rich_4079 (~190 s); then submit_patch (not budget-gated) on an empty tree ended the race with nothing (B at 297/404 s, B at 203 s, A at 254 s). Engineer prompts reached 15,636 (> 14,336 compaction) in 3/4 runs; no crash this time. Bar: scout notes ok, scout <= 200 s ok, gate use ok, engineers keep budget FAIL (2/4), prompts < 14,336 FAIL (3/4 over), 0 crashes ok, ended by a real submit FAIL; outcome 1 vs 2 FAIL, +63 s FAIL. Conclusion: every race fix exposes the next shared-session limit (shared call budget, empty submits end the race, compaction in the parallel phase). Races 1/4 (r75) and 1/4 (r78b) vs combo1 1/4 and 2/4: parked.
- **RUN BUILT r78: two small first trials on the 4 mid-rate dev16, 1 pass** (user 2026-11-11 "yes please do so and after the trial we see what to submit"; the LB slot waits for these). Builder scripts/make_gate_arms.py; every new prompt is budget-free (user rule 2026-11-10; the builder asserts no call counts, minutes, call plans or 'budget'). **r78a** kaggle/cells_skill_gate4 (only cell2 differs from r77): combo1, evidc, evgate, evgate1, CONCURRENCY 2, 16 runs, ~1 h. evgate (29b6975d) = allplus with the gate's late refusal off (state words only; stop rule after an edit kept) and a prompt without allplus's budget line; evgate1 (0f687ada) = the same with REFUSE_ONCE (new run_phase.py switch: the late refusal fires once, then commands run with EDIT NOW). Why: r76's refused calls cost 96-119 s a run. **r78b** kaggle/cells_skill_race3_4: combo1 vs race3 (9a22c4ff), CONCURRENCY 1 (as the scorer), 8 runs, ~1 h. race3 = setup agent installs the scout's gate (new run_phase.py switch SCOUT: LOOK / NOTES NOW words, from the 9th command or 150 s refusals say 'reply now with your notes'; NOTES NOW from the 6th or 100 s; no stop rule) -> scout (run_command through the gate + get_status only, worked example, REMIND, output_key notes) -> race2's engineers with budget-free prompts. Tests run_phase 22/22. Sims (data/sim/armsim_gate4.log, armsim_race3_4.log): all runs end ok; evgate 0 late refusals, evgate1 exactly 1; the race3 scout's 6th-8th outputs say NOTES NOW and the 9th is REFUSED, then it replies notes; engineers start with notes + issue in their system prompts; final patches = gold in both race outcomes. **Bars (set before; 4 tasks catch breakage, timing and large effects):** r78a mechanics: >= 90% of commands through the gate, evgate 0 and evgate1 <= 1 late refusal per run, refused calls <= 30 s of model time per run (allplus 119), evidence stage <= 15 s. Outcome: an evgate arm moves on if solves >= evidc's, no-patch <= evidc's and mean agent time <= combo1 + 15 s. r78b mechanics: scout notes in 4/4, scout done <= 200 s median (r75 383 s), >= 90% of scout commands through the gate, engineers start with budget left in 4/4 (no BudgetExceeded), engineer prompts < 14,336, 0 crashes, the race ends by a submit in >= 3/4. Outcome: solves >= combo1, mean wall <= combo1 + 20 s. After both: pick the LB submission between evidc (dist/submission.zip now) and any arm that passes.
- **RESULT r77 (data/results/2026-11-11_skill_evidc16_p1 = engziadsamer/arms-again, _p2 = fatmazenhom/generation-shard-4-gpu; 2 x 32 runs, 1.85 / 1.66 h): evidc 8/32 vs combo1 5/32 (+5/-2), no patch 12 vs 16, time equal pooled; the gain again sits on the 4 mid-rate tasks.** Pass 1: combo1 3 / evidc 3 (+1 rich_3521, -1 fastapi_11194), no patch 6 vs 9, agent 377 vs 420 (+43). Pass 2: combo1 2 / evidc 5 (+4: fastapi_11194, 14419, 15589, rich_3521; -1 rich_3180), no patch 10 vs 3, agent 385 vs 340 (-44). Pooled agent 381 vs 380. Split: the r76 tasks (14419, 15589, 3521, 4079) evidc 5/8 vs combo1 1/8; the other 12 evidc 3/24 vs combo1 4/24 (evid3 in r66: 2/24 vs 3/24, same pattern). Evidence stage: 1 call (one run 2), 4-14 s, median 7 s; 1-line replies (likely NOTHING RELEVANT) in 6/16 tasks per pass. Bar (set before): >= +1 per pass FAIL in pass 1 (+0), >= +2 over 2 passes ok (+3); other 12 not below combo1 FAIL by 1 (3 vs 4); no-patch ok (12 vs 16); time ok (~0). With r76: +8/-2 over 36 pairs (sign p ~0.11). **LB combo1 = 0.15 (2026-11-11, COMPLETE, fitted in time; ~9 of 58; identical bundles range 8-13).** dist/submission.zip = evidc (dist/evidc.zip, pack.py OK; combo1's zip kept as dist/combo1_submitted.zip), prepared for the user's decision: the LB is the judge on 58 other tasks and the submission doubles as the time-fit test of the cheap evidence stage (one skill call, 8 s script).
- **RUN BUILT r77: combo1 (control) vs evidc on the full dev16, 1 pass per notebook, CONCURRENCY 2** (r76's bar: an arm passing both goes to the full dev16), kaggle/cells_skill_evidc16 (only cell2 differs from r76), 32 runs, ~1.8 h. Suggested: the same cell2 on both free notebooks (fatmazenhom/generation-shard-4-gpu and engziadsamer/arms-again) = 2 passes in the same wall time (as r66); keep the output folders apart (labels are .1 in both). evidc unchanged from r76 (its fixer prompt is combo1's byte for byte, budget lines included: it ran that way and the no-budget rule applies to new prompts). **Bar (set before):** over all dev16 runs: evidc solves >= combo1 + 1 per pass (>= +2 over 2 passes); on the 12 tasks not in r76 evidc not below combo1 (evid3 failed exactly this: 2/24 vs 3/24); no-patch <= combo1; mean agent time <= combo1 + 15 s (evid3 timed out on the LB at +14-26 s). Pass -> evidc becomes the next LB submission once combo1's pending score is back (one pending at a time).
- **RESULT r76 (data/results/2026-11-11_skill_plus4, engziadsamer/arms-again, 20 runs, 1.15 h): evidc PASSES (3/4 vs combo1 0/4, +12 s); the adoption fix works: 100% of commands go through the gate in all three gate arms (rc family before: 24%).** Solved / no patch / mean wall (agent): combo1 0/2/371 (362), nn32rcf 0/3/427 (420), **evidc 3/1/383 (374)** (only+ fastapi_14419, fastapi_15589, rich_4079; only- 0), t7rc 1/2/389 (379) (only+ 15589), allplus 1/1/440 (431) (only+ 14419). combo1's 0/4 is a low draw (r72-r74 + r75 on these 4: ~1.3 expected). Mechanisms (scripts/mine_bank/plus_reads.py): run_command through .git/agent/run.py nn32rcf 77/77, t7rc 43/43, allplus 86/86 (worked example + install line + REMIND); setup agents 1 call each, 0 calls to tools they lack, stage 3 s; evidence stage (thinking off, 8 s script) 4-10 s, median 9 s (evid3 15-48 s), evidence lines 7 / 1 / 5 / 5 (evidc) and 7 / 1 / 5 / 6 (allplus); no bypass after refusals (next: wrapped command or edit_file). Why the gate arms are slow: refused calls cost model time: nn32rcf 15 refusals = 96 s per run, allplus 14 = 119 s per run (more than their whole +56 / +69 s); after a refusal the model thinks long and tries another command (wrapped 9-12) before editing (edit_file 2-5). First source edit earlier (allplus 185 s, nn32rcf 207 s vs combo1 264 s) but the runs end later. Bar (set before): evidc mechanics ok (stage 9 s <= 15, evidence 4/4) + outcome ok (3 >= 0, no patch 1 <= 2, +12 s <= +15) -> PASS, goes to the full dev16. nn32rcf FAIL (no patch 3 > 2, +56 s). t7rc mechanics ok, outcome 1 vs 0 and no patch 2 = 2 ok, time +18 s FAIL by 3 s. allplus mechanics ok, 1 vs 0, no patch 1, time +69 s FAIL. Caveat for evidc: evid3's earlier gain sat on exactly these mid-rate tasks (r66: 4 picked tasks 6/8 vs 2/8, the other 12 dev16 tasks 2/24 vs 3/24), so the full dev16 decides. Next for the gate family: cut the refusal loop (the cost is the model's long thinking before each refused call), e.g. fewer / later refusals or state words only; the 100% adoption also makes a gated race scout possible. combo1 LB still PENDING at 00:30 (submitted 11-10 13:01).
- **RESULT r75 (data/results/2026-11-10_skill_race4, fatmazenhom/generation-shard-4-gpu, 8 runs, concurrency 1, 0.98 h): race2 FAILS its mechanics bar: the scout does not stop.** Solved / no patch / mean wall: combo1 1/2/408, race2 1/3/471 (+63 s); race2 solved fastapi_15589 (engineer A submitted at 476 s), lost rich_3521. Scout (told 'about 10 tool calls'): 44, 17, 9, 44 calls; done at 306-416 s (median 383; bar <= 200 s); in 2/4 runs (fastapi_14419, rich_3521) it never wrote its notes before the 8-min cap (rich_3521: 9 calls in 416 s, long thinking); in rich_4079 it spent the whole shared budget (44 calls) and replied at 350 s, so every engineer call got 'BudgetExceeded' and both engineers called submit_patch on an empty tree (the call is not budget-gated). What worked: no crash in 4/4 (no compaction during the race: engineer max prompt 9,921 < 14,336), scout notes had all six fields when written, engineer A won 15589 from the notes, A never touched B's worktree (B's one 'outside' edit was a refused call). Bar: scout notes 4/4 FAIL (2/4), scout <= 200 s FAIL (383 s), race ends by a submit >= 3/4 FAIL, 0 crashes ok, prompts < 14,336 ok; outcome solves >= combo1 ok (1 = 1), time FAIL (+63 s). Lesson (r60 and r75 agree): a prompt budget does not bound an exploring stage; only an enforced event can. A race needs a bounded first stage: the cheap evidence stage (one skill call, r76) or a gated scout (commands refused after N with 'write your notes now'), which needs the run_command gate to be used (r76 measures adoption). Not resubmitted to a bigger run.
- **RUN BUILT r76: small first trial of four arms built on every measured plus: combo1 (control) vs nn32rcf, evidc, t7rc, allplus on the 4 mid-rate dev16, 1 pass, CONCURRENCY 2** (user 2026-11-10 "lets make the agent of the nn32rc family + evid3 cheaper + sq1c2t7 on run_command in one run as well as trying to merge all the pluses of table in a single agent"; runs while r75 runs on the other notebook), kaggle/cells_skill_plus4 (only cell2 differs from r75), 20 runs, ~1.2 h. Builder scripts/make_plus_arms.py; zips validated with pack.py: nn32rcf 9818943c, evidc 9755bb6c, t7rc 9f02a7c5, allplus 981f27f8. Why these (scripts/mine_bank/arm_table.py + LB history): forced edit is the only family with a consistent plus (nn32 / nn36p 11 vs 7 over 42 pairs, combo1en +2/-0, combo1en2 +2/-2); LB fit rule: ONE skill call (an install) + run_command fits (sk_a2 0.18, nn32rcn2 0.12), every command through a skill timed out (sq1c2, sq1c2t7, srep7, nn32); the nn32rc family (64 runs) lost the gain because only 24% of commands went through .git/agent/run.py (317/1,309), and after a refusal the model never bypassed it (0 of 57 next calls direct) -> adoption, not escape, is the problem; evid3 +6/-2 over 44 pairs but +26 s and an LB timeout (its script ran git log -S over the whole history with a 40 s deadline); sq1c2t7 18 vs 15 of 24 but 80 calls and a skill shell. **nn32rcf** = nn32rcn2 (setup agent installs the gate; main: run_command through run.py, no read_file, REFUSE_AT 240 s / 13th command, stop rule, state words, thinking 2048) + adoption measures: a worked example where every command carries the prefix (one example took heredocs 4 -> 19 in r69), the install line names the engineer's command form (r57's READY line 42% early use vs r58's 8%) while telling the setup agent to stop, and REMIND (new run_phase.py switch, off by default; test 20/20): every gate output ends '| every command: python .git/agent/run.py ...'. **evidc** = evid3's stage made cheap + combo1 as the fixer: stage thinking off, script deadline 8 s / 4 s per git call, git log -S over the last 500 commits only (tested on a 508-commit repo: a name changed in the newest commit found, a name from 506 commits back not), at most 10 copied lines; fixer = combo1's prompt byte for byte + the evidence section (as evid3 added it to pub024). **t7rc** = sq1c2t7 (7 min, clock line, refusal at 240 s, fixer hands over, finisher submits) with its clock script through run_command after a setup agent (start time cached, command on stdin, REMIND), 32 calls (was 80); fixer prompt written fresh. **allplus** = ONE setup call (skills/work scripts/setup.py) installs the gate AND runs the cheap evidence search (thinking off; copied lines into the engineer's system prompt via output_key), then an engineer on combo1's contract and edit rules with the gate's state words, the worked example, REMIND, the garbled-edit rule, /tmp line, no read_file, no graph tools, pub024 sampling, 32 calls, 8 min; prompt written fresh with no numbers (the gate drives timing). Left out: the clock (clock numbers showed no benefit; the state words replace it), srep's reporter (same role as the evidence stage, slower), race (separate run r75). **Harness finding:** in the installed harness (adk_submission 0.2.13, resolvers/generation.py) any thinking_budget > 0 turns thinking ON and a missing budget is filled with 4096, so include_thoughts: false alone does NOT switch thinking off (the first sim showed enable_thinking true on the stage); thinking_budget: 0 does (schema ge=0): the stage requests then carry enable_thinking false and no thinking_token_budget (sim confirmed). Sim (data/sim/armsim_plus4.log; roles plussetup, clockrc added): 10/10 runs end ok; setup agents make one call; the INSTALLED line reaches the engineer; evidence lands in the system prompt of evidc and allplus; gate refusals (no edit yet, and the stop rule) and REMIND lines appear; t7rc's clock line carries REMIND and its finisher submits. Read with CTRL=combo1 python3 -I scripts/paper/analyze_screen.py FOLDER and python3 -I scripts/mine_bank/plus_reads.py FOLDER. **Bar (set before; 4 tasks catch breakage, timing and large effects only):** mechanisms: nn32rcf / t7rc / allplus send >= 70% of run_command calls through run.py (rc family 24%), setup agents 1 call and 0 calls to tools they lack, no bypass after refusals; evidc / allplus first stage <= 15 s median (evid3 15-48 s) with evidence lines in >= 3/4. Outcome per arm vs combo1 in this run: solves >= combo1, no-patch <= combo1, mean agent time <= combo1 + 15 s (evid3 timed out at +14-26 s). An arm passing both goes to the full dev16.
- **RUN BUILT r75: race2 small first trial, combo1 (control) vs race2 on the 4 mid-rate dev16 (fastapi_14419, fastapi_15589, rich_3521, rich_4079), 1 pass, CONCURRENCY 1** (user 2026-11-10 "lets test it yeah build"), kaggle/cells_skill_race4 (only cell2 differs from r74), 8 runs, ~45-50 min. race2 (scripts/make_race_arm.py, dist/race2.zip md5 8e55b1ed, pack.py OK with the competition compiler) = SequentialAgent [scout, ParallelAgent race [engineer_a, engineer_b]]. scout: run_command / read_file / get_status only (a scout submit would end the task with an empty patch), ~10 calls, final reply WHERE / CAUSE / CHANGE / ALSO / CHECK / TEST saved by output_key notes. engineers: include_contents none, {problem_description} + {notes?} in the system prompt, ~14 calls, reads ~40 lines, outputs | head -60 (keeps every engineer prompt under the 14,336 compaction threshold, so the ParallelAgent compaction crash cannot fire); A edits /workspace; B works in a git worktree at /workspace/.git/wt_b (inside .git: never in the graded diff), runs checks there with PYTHONPATH=src:., and finishes with one command (stage its diff, reset /workspace, git apply) then submit_patch; scratch /tmp/scout_*, /tmp/a_*, /tmp/b_*. The first submit ends the task (agent_runner.py breaks on patch_submitted + a final text event; submit_patch captures the diff at that moment). eval_config: 44 tool calls (shared), 8 min, 240 s commands, 120 turns; sampling = pub024's. Harness facts found while building: swegemma tools are synchronous and the harness sets no ADK tool_thread_pool_config, so a running tool blocks the whole event loop (both branches; model generation already in flight continues on the server); the shared tool_lock serialises tools; the subprocess sandbox rewrites /workspace and /tmp in commands to the task's folders (so .git/wt_b and /tmp/b_fix.patch work on Kaggle as on the scorer); after the break the cancelled branch logs a harmless GeneratorExit. Sim (data/sim/armsim_race4.log; armsim roles rscout / reng_a / reng_b, threaded fake server with 8 s delayed replies for the slow engineer): fastapi_14786 B wins: final patch = gold, A's stray /workspace line wiped, B's check imports from the worktree, resolved; fastapi_15588 A wins: patch = gold, resolved; engineers start with 2 messages, notes and issue in their system prompts, no unfilled template. Read with: CTRL=combo1 python3 -I scripts/paper/analyze_screen.py FOLDER and python3 -I scripts/mine_bank/race_reads.py FOLDER. **Bar (set before; 4 tasks only catch breakage, timing and large effects):** mechanics, all needed to go bigger: 0 sandbox errors / crashes; scout notes with WHERE and CHANGE in 4/4 and scout done by <= 200 s median; every engineer prompt < 14,336 tokens; B edits outside .git/wt_b 0 and A edits inside it 0; the race ends by a submit in >= 3/4. Outcome: solves >= combo1's, mean agent time <= combo1 + 20 s (both at concurrency 1). Pass -> race2 vs combo1 on the full dev16. Expect combo1 ~1.3 of 4 (r72-r74: 14419 1/3, 15589 2/3, 3521 0/3, 4079 1/3).
- **RACE / BEST-OF-K 2026-11-10 (user: "I want to win the comp"; scripts/mine_bank/decode_vs_inflight.py, bestof_sim.py, race_compaction_risk.py): parallel attempts are the one time-neutral gain in the data, but ADK's shared-session compaction makes them crash; not buildable as a full-agent race.** (1) Decode vs requests in flight (all logs): 1 -> 32.3 tok/s, 2 -> 30.2, 3 -> 26.9 (our local runs sit at ~2; the scorer runs one task at a time, forum 743063). (2) Simulation from 524 real pub024/combo1 runs on 53 tasks (branch slowed by the measured decode loss, cut at a branch cap; a cut run counts only if its last working edit was in place): single 8 min 19.4/53 at 326 s scorer time; plain best-of-k with the task waiting for the slowest branch: best-of-2 cap 360 s 19.9-20.2 (oracle 21.3) at 320 s, best-of-3 cap 330 s 20.1 (oracle 21.6) -> the max over branches eats the gain. **Race** (swegemma agent_runner.py ends the task when patch_submitted and a final text event arrives, so the first branch that submits ends it and its patch is kept): best-of-2 cap 450 s 21.1/53 at 322 s, best-of-3 cap 420 s 21.4/53 at 320 s (+1.7 / +2.0, ~+3-4 pts at equal time); most of it is 'quick finishers are more often right'. (3) Blocker: the bo3 crash (2026-10-29, 11/24) is ADK 1.36.1 contents.py _rearrange_events_for_latest_function_response 'No function call event found' after token-threshold compaction in a ParallelAgent session; apps/compaction.py has pending-call / safe-split guards in session order but _process_compaction_events drops events by timestamp, and parallel branches append events out of timestamp order -> orphaned responses; the runner's except Exception then drops the patch. A branch compacts before the race ends in 93% (k=2) / 94% (k=3) of simulated tasks (onset median 180 s; 467/524 runs compact). (4) Why contexts fill: at the last request before compaction (combo1, r74): tool results 42% of characters, re-sent past thinking 27% (chat_template.jinja lines 237-240 render reasoning for every assistant tool-call turn after the last user message, i.e. the whole run), system 14%, task 9%; not changeable from YAML. (5) The 8 dev16 tasks pub024 never solves: ~60 runs each over all arms, solved only by sq1c2a6info (the arm given the real GitHub reports): 0 for every agent without that information. Not built: a small-context 'scout -> parallel fixers' race (fixers start fresh, ~10 calls, stay under the threshold) is the only crash-free form; r60's scout -> fixer handoff lost information and time, so it starts with negative evidence.
- **MINING 2026-11-10b (user: "I need more, look at all our runs, get the best agent"; scripts/mine_bank/think_share.py, issue_gone.py, first_edit_vs_budget.py, refusal_next.py): every remaining time or commitment lever I could find is already measured and closed; no new agent arm is worth GPU quota on this evidence.** (1) Thinking off (include_thoughts: false -> enable_thinking False, adk_submission/resolvers/generation.py): never run by us; public evidence against it: cubres (research/raw/kernels/lb_top/gemma-and-the-shape-of-doubt.txt) scored 3-5/58 in all 7 thinking-off draws, 0.18 after moving to a thinking-on config (prompt changed too); every saved thinking-off notebook scored 0.08-0.13. (2) Thinking is ~70% of model output and time (38,376 calls at budget 4096: 304 tok/call, 29.6 tok/s, calls >= 30 s hold 46% of time); a first-order cut at 2048 / 1024 would save ~34 / ~74 s per run, but the Oct test (SAMPLING ARMS RESULT 2026-10-28) showed the model spreads the same thinking over more calls: 1024 kept agent time 373-391 s and hard-tier solves fell 4/12 -> 0/12; 2048 vs 4096 time unchanged. (3) Issue text: compaction removes it in 417/464 pub024-family runs; 246/350 first edits are written without it; same task: 50% vs 26% solved, but same task + same 5-call band: +5% (4 cells up, 3 down, 15 equal) -> mostly 'early edits solve more', so pinning {problem_description} is a weak lever. (4) Call cap: solved 28-call runs use the whole budget (45/173 at 28, 62% > 20 calls); pub024's first-edit hazard is flat 3-6% per call from call 11 to 27 (no jump at the budget warning, call 19); sk_a2 28 vs sk_a2_32 (identical otherwise) first edit at call 12 vs 10 -> a lower cap would cut runs, not move edits; no arm ever ran < 28. (5) Time cap: 172/584 28-call runs end at the cap (122 without a patch, 59 before the warning); a 7.5-min cap keeps >= 93% of solves (last working edit by 445 s in 103/111) for ~9 s mean saving -> not worth it. (6) Docker skill call = sandbox.write_file (local tmp + exec-socket tar, 2-3 docker execs) + python3 run + rm (adk_eval_core/sandbox/base.py AdkSandboxCodeExecutor, swegemma/sandbox/docker.py); the skill-shell LB timeouts stay unexplained (a local Docker timing test would need the sandbox image; colima stopped; not run to spare the user's internet). (7) 12B: mix 2, 1 of 16 and an LB timeout; E4B 1/64. (8) dev16 pooled (task-balanced): pub024 ~3.0/16 over 282 runs (8 tasks 0/11 in every run: fastapi_13920, 14258, 14306, 14487, 15280, 15800, rich_3468, rich_3934), combo1 3.3 (48 runs), gated combo1en+en2 4.0 (32), sk_a2 ~4 (40); all inside noise. Conclusion: the agent is at the ceiling of what our levers move; the only large measured effect is information (r45/r61 6/76 -> 30/76), not available at test time.
- **RESULT r74 (data/results/2026-11-10_skill_en2_16, fatmazenhom/generation-shard-4-gpu, 32 runs, 1.74 h): combo1en2 FAILS its bar; the few-shot example did not change the move after a refusal; the gated-shell line stops here.** Solved / no patch / mean agent s: combo1 4/8/350 (wall 361), combo1en2 4/4/404 (wall 414, +53 s; only+ rich_3521, rich_4079; only- fastapi_11194, fastapi_15589). Mechanism: refusal fired in 9/16 runs (17 refusals); the next call after the first refusal was edit_file in 2/9 (read_file 3, another shell command 4; r73 1/11 edit_file + 2 write_file); a working source edit followed in 5/9 runs, median 54 s after the refusal (r73 7/11, ~150 s); 4/9 refused runs never edited. Other: edited runs 12/16 vs 8/16, but 10 edit_file calls failed (old_string not found etc.; combo1 5), garbled shell calls 20/223 = 9%, 6 runs at the 480 s cap (combo1 4), last edit -> end median 103 s vs 37 s. Bar (set before): edit_file next >= 6/10 FAIL (2/9); refusal -> edit <= 90 s ok on the runs that edited (54 s) but only 5/9 edited; solves >= combo1 ok (4 = 4); no-patch <= combo1 - 1 ok (4 vs 8); time <= combo1 + 20 s FAIL (+53). Pooled dev16 (one pass each): combo1 r72-r74 4, 2, 4 = 10/48 (21%); gated shell combo1en + combo1en2 8/32 (25%), indistinguishable, at +46 to +53 s each time. pub024 r72 2/16, combo2 r73 2/16. Bank-wide (1,756 Nov runs): 65 of 616 solves end at the cap (>= 475 s) and 103 after 420 s, so a shorter per-task limit costs solves; 257 of 576 no-patch runs end at the cap. LB combo1 still PENDING at 19:55 (submitted 13:01).
- **RUN BUILT r74: combo1 (control) vs combo1en2 on the full dev16** (user 2026-11-10 "if it can be fixed with few shot, do it"), kaggle/cells_skill_en2_16 (only cell2 differs from r73), 32 runs, ~1.8 h. combo1en2 = combo1en byte for byte (same gate script, tools, limits) + 3 lines in the SHELL section: a worked example of the move after a refusal ('REFUSED: no source file is edited yet ...' -> the next call is edit_file on the place already found, with a generic filepath/old_string/new_string; not read_file, not another command; the same on EDIT NOW). Why few-shot: r73's refusal fired in 11/16 runs but the next call was edit_file in 2/11 and refusal -> first edit took ~150 s, mostly read_file (not gated); r69 showed one worked example moves this model strongly (heredoc scripts 4 -> 19). Not fixable by few-shot (said to the user): runs forced to edit keep working longer (the main part of r73's +46 s) and the 610 s hang (a repro script's endless loop). Sim (data/sim/armsim_en2_16.log): 4/4 end ok, 12th command REFUSED in both combo1en2 runs, the shell edit passes, the next command runs; the example text is in cell2. dist/combo1en2.zip validated; combo1 / combo2 / combo1en rebuilt byte-identical. **Bar (set before):** mechanism: after a refusal the next call is edit_file in >= 6/10 refusal runs (r73: 2/11) and refusal -> first edit median <= 90 s (r73 ~150 s); outcome: solves >= combo1's, no-patch <= combo1 - 1, mean agent time <= combo1 + 20 s (r73 combo1en +46). Even if it passes, its first LB submission is also the skill-shell time-fit test.
- **RESULT r73 (data/results/2026-11-10_skill_combo3_16, fatmazenhom/generation-shard-4-gpu, 48 runs, 2.69 h): both new arms FAIL their bars; combo1en has the most solves.** Solved / no patch / mean agent s: combo1 2/6/368 (r72: 4/6/375), **combo1en 4/5/414** (only+ fastapi_14419, fastapi_15589; only- 0), combo2 2/7/375 (only+ 15589, only- 11194). combo1en: refusal fired in 11/16 runs (first at 70-375 s), the next call was edit_file in 2/11, an edit within 3 calls in 6/11; refusal -> first edit median ~150 s (mostly read_file, which the gate does not block); first edit median 318 s vs combo1 210 s; garbled edit calls 0/31; bad shell calls 7%; 15589 solved after a refusal, 14419 without one. The +46 s: tasks where combo1 stopped early with a wrong or no patch (14258 236 s, 15280 265, 3470 332, 14487 220) ran to ~450-610 s under combo1en, plus one hang: fastapi_14258 ran 610 s: its repro script called router.include_router(router) (likely an endless loop that grows memory) and the call never returned despite run.py's 150 s kill; pub024 has the same kind of over-run through run_command (4/486 runs), so it does not explain skill-shell LB timeouts (my 'positional_args sent as a string' reading was wrong: scripts/mine_bank/extract.py stores list arguments as text). combo2: garbled edit calls 6/27 (combo1 10/35), resent identically 3/6 vs 4/10. Bars (set before): combo2 resends below combo1 FAIL (50% vs 40%), solves >= combo1 - 1 ok, time <= +5 FAIL (+7). combo1en no-patch <= combo1 - 2 FAIL (5 vs 6), solves >= combo1 ok (4 vs 2), time <= combo1 FAIL (+46 s), refusals fire ok, bad shell < 10% ok (7%). Pooled combo1 (r72 + r73): 6/32. LB combo1 submitted by the user 2026-11-10 13:01, PENDING.
- **RUN BUILT r73: combo1 (control) vs combo1en vs combo2 on the full dev16** (user 2026-11-10 "make both please as new arms on the full dev16, so we have combo ctrl, combo1 + edit now, combo2"; no pub024 this run, user choice), kaggle/cells_skill_combo3_16 (only cell2 differs from r72), 3 arms x 16 x 1 pass = 48 runs, ~2.7 h. Builder scripts/make_combo_arm.py (combo1 rebuilt byte-identical to r72's, hash 4802d4ce). **combo2** = combo1 with the garbled-call bullet moved out of the edit section into its own final section, kf2's wording (kf2: 0/30 garbled edit calls r70-r71; combo1's in-section bullet 14/36, 10 resent, r72). **combo1en** = combo1 + nn32's forced edit: no run_command; every shell command via skill sh (scripts/agent_clock/run_phase.py as scripts/run.py with STOP_AFTER off, REFUSE_AT 240 s, REFUSE_SHELL 12, WORDS, LIGHT); positional_args with one string (8% garbled in r31; the object form args.cmd garbled 76% in r30 because the template puts args before file_path, so the array-free version I proposed is not workable); prompt = combo1's text with the 4 run_command routes rewritten to 'the shell' + a SHELL section (call shape, state line, refusal). Local test of the gate (scratch repo): commands 1-7 LOOK, 8-11 EDIT NOW, 12+ REFUSED, a test-file edit does not unlock, a source edit does (then CHECK); test_run_phase.py 19/19. Sim (data/sim/armsim_combo3_16.log, role 'en' added): 6/6 end ok; combo1en: tools incl. run_skill_script, 12th command REFUSED, shell edit passes, next command runs; combo2's rule is the last section; no unfilled placeholder. dist/combo2.zip, dist/combo1en.zip validated. Parser-hang check: skill-shell arms show 0 stalled replies locally on the same vLLM 0.19.1 (nn32 0/42 runs, sq1c2 0/36), so the 'Before Best-of-N' array bug does not explain the LB timeouts; their cause is still unknown -> combo1en carries that LB risk even if it wins locally. Read with CTRL=combo1 scripts/paper/analyze_screen.py (control now a variable) and scripts/mine_bank/extract.py + kf_reads.py. **Bars (set before):** combo2 vs combo1: garbled edit calls resent identically below combo1's, solves >= combo1 - 1, time <= combo1 + 5 s. combo1en vs combo1: no-patch <= combo1 - 2, solves >= combo1, mean agent time <= combo1's; mechanism: refusals fire and an edit follows, garbled shell calls < 10%, no stall. Any LB submission of combo1en is also an LB-fit test (a timeout costs that day's slot).
- **RESULT r72 (data/results/2026-11-10_skill_combo16, 32 runs, 1.74 h): combo1 4/16 vs pub024 2/16, LB bar PASSED.** only+ fastapi_11194, rich_4079; only- 0 (sign 2-0, p 0.5: within noise; pub024's dev16 history 3, 3, 2, 5, 2 so 2 is a low draw). No patch 6 vs 6; mean agent 375 vs 385 s (-10); first edit median 189 vs 305 s; /tmp write errors 0 vs 1 run; SyntaxError runs 1 vs 4; no call to a removed graph tool and no unknown-tool error. Garbles were unusually frequent in both arms this run: combo1 14/36 edit calls in 2 runs (fastapi_14419 x5, fastapi_15800 x9; both still ended with a wrong patch), 10 resent identically; pub024 24/41 in 3 runs, 21 resent. The rule as a bullet inside the edit section held less than kf2's separate final section (0/30 in r70-r71): placement or chance, not settled; combo1 was not changed (the bar was set for this exact file). Bar (set before): solves >= pub024 - 1 PASS, no patch <= +1 PASS, time <= pub024 PASS, no crash PASS, garbled resends 10/14 vs 21/24 PASS (weak), /tmp 0 vs 1 PASS. **LB PREPARED combo1 (2026-11-10):** dist/submission.zip = dist/combo1.zip (md5 c6a64c15, 4 files byte-identical to submissions/combo1 that ran in r72); previous evid3 zip kept as dist/evid3_submitted.zip. No pending submission (evid3 completed, timed out). The user uploads. Expect one draw of 58 tasks: pub024 family scores 7-13 of 58, so the score alone will not show the gain; what it tests is that combo1 fits the time limit.
- **COMBINE 2026-11-10 (user: "be smart, based on all our runs, get the best of agents into one"; scripts/mine_bank/arm_table.py, thinking.py):** (1) Every arm vs the same-run pub024, pooled over the bank: nothing significant. Best: nn32 and nn36p 11 vs 7 (42 pairs, +5/-1 each, p 0.22) with no patch 7 / 4 vs 21 at equal time (forced 'edit now' refusals through the skill shell); their run_command versions (nn32rc*, 7 arms) lost it: no patch 27 vs 29, solves 21 vs 24; evid3 15 vs 11 (gain on picked tasks); everything else +-1. (2) LB: every 7-8 min agent that sends all commands through a skill script timed out (sq1c2, sq1c2t7, srep7, nn32; 6 min fit); 8-min single agents fit (pub024, mix, sk_a2, sk_a2_32); locally a skill call costs 0.2 s median. Unverified candidate cause: the 'Before Best-of-N' paper (research/raw/kernels/lb_2026-11-10/) reports vLLM 0.19.1's gemma4 argument parser never returning on JSON-quoted array arguments; skill calls carry positional_args arrays. Rule: no skills, no array arguments in an LB agent. (3) LB noise: one identical bundle scored 9, 10, 8, 13, 12 of 58 over five daily draws (gedouluhui variance notebook); board 2026-11-09: 0.18 x873 teams, 0.20 x412, 0.22 x73, 0.24 x11, 0.29 x1. A daily LB draw cannot rank agents within ~3 tasks; choose by local evidence + LB time safety; final = better of 2 picks, each one private draw, so both picks should be the highest-true-rate agent(s). (4) Call budget: the harness warning (10 calls left) moves pub024 to edit within 2 calls in 23/253 runs; more calls do not cut refused edits (sk_a2 11% at 28 vs sk_a2_32 11% at 32); pub024's median first edit is call 18, where the warning appears: the model explores until the budget is gone. (5) Thinking budget is enforced (p99 reply = budget), but 2048 does not reduce the number of long replies (2.0-2.6/run) or model time. (6) The 3 graph tools: 0 calls in 470 pub024 runs, ~529 tokens re-sent with every request (prompt itself 1,609). (7) The sim shows this harness returns a call to an unlisted tool as an error to the model and the run continues (not a crash). (8) LoRA stays out (23/44 vs base 27/44, loops, ~11% slower decode). Result: combo1 = pub024's recipe + only the zero-cost, mechanism-proven fixes (scripts/make_combo_arm.py).
- **RUN BUILT r72: combo1 vs pub024 on the full dev16** (user 2026-11-10), kaggle/cells_skill_combo16 (only cell2 differs from r71), 32 runs, ~1.8 h. combo1: prompt written whole = pub024's 47 lines with 45 unchanged, the scratch line rewritten ('/tmp only, and only through run_command; write_file only writes inside /workspace'), the graph-tool line dropped, the garbled-call rule added inside the edit section; tools = pub024's minus get_code_neighbors / search_similar_code / get_code_subgraph; eval_config and sampling = pub024's bytes. Prompt 1,693 tokens (+84) and ~529 fewer tool tokens: ~445 fewer tokens per request. dist/combo1.zip validated. Sim (data/sim/armsim_combo16.log; detection widened): combo1 gets 6 tools and the rule, pub024 9 tools; 4/4 end ok; no unfilled placeholder. Direct to dev16 (no 6-task trial): its parts were already tried (kf2 small + dev16; tool-less configs on the LB) and a 6-task run cannot show a no-harm effect. **Bar for an LB submission (set before):** solves >= pub024 - 1; no-patch <= pub024 + 1; mean agent time <= pub024's (expect faster); no crash or call to a removed tool that breaks a run; garbled resends below pub024's when garbles occur; /tmp write errors below pub024's.
- **RESULT r71 (data/results/2026-11-10_skill_kf2_16, 32 runs, 1.77 h): kf2 3/16 vs pub024 5/16 -> LB bar FAILED, no submission.** only+ rich_4079; only- fastapi_11194 (call budget exhausted, edit refused at 268 s, ~210 s left), rich_3470 (budget, edit refused at 286 s), fastapi_14419 (wrong file); sign 1 vs 3, p = 0.625. No patch 6 vs 7, mean agent 369 vs 375 s (time bar ok). Mechanism held again: garbled edits kf2 0/21 vs pub024 4/17 (3 resent identically). kf2 SyntaxError runs 3 (all one-line python -c, pub024's own habit, bank rate 13%) vs 0. Pooled kf2 vs same-run pub024 (r70 + r71, 22 task-runs each): 6 vs 7 solves. Pooled garbles across r69-r71: hint arms 1/42 edit calls vs pub024 13/45. Conclusion: the hint reliably removes garbled edits but no outcome gain is visible at this scale; the call budget is again what lost kf2's runs (both no-patch losses were refused edits with ~200 s left).
- **RUN BUILT r71: kf2 vs pub024 on the full dev16** (user 2026-11-10 "lets go"), kaggle/cells_skill_kf2_16 (only cell2 differs from r70), 2 arms x 16 tasks x 1 pass = 32 runs, ~1.8 h. Agents byte-identical to r70's (kf2 = pub024 + the 110-token garbled-call hint), no new sim. Tasks not picked for kf2 (6 of r69/r70's tasks are not in dev16 except fastapi_15589, rich_4079). Purpose: show the hint does no harm and costs no time before an LB submission; a gain this small (~11% of runs garble) cannot be resolved by 16 runs. **Bar for the LB (set before):** solves >= pub024's; no-patch not above pub024's; mean agent time <= pub024 + 5 s (evid3 timed out at +14-23 s); if garbled edits occur, kf2's identical resends below half of pub024's. If it passes, dist/submission.zip = kf2 for the user to upload.
- **LB evid3 TIMED OUT (seen 2026-11-10: COMPLETE, no score, like nn32 / srep7).** evid3 ran +14 s (r66, dev16 x 2) to +23 s (r65) mean agent time over pub024 locally. So the scorer's 12 h (~366 s per task) leaves pub024 almost no headroom: an arm slower than pub024 by ~15 s or more should be treated as an LB timeout risk, and a stage that adds ~20 s (evidence, checklist, hunch) needs to win that time back inside the fixer. Next submission should be pub024-speed or faster.
- **RESULT r70 (data/results/2026-11-10_skill_kf2c6, 18 runs, 0.93 h): kf2 passes its bars but its mechanism never fired; kf2c fails.** Solved / no patch / mean agent s: pub024 2/3/356, **kf2 3/1/316** (only+ fastapi_15589, rich_3278; only- fastapi_14873), kf2c 2/3/373 (only+ rich_3278, only- fastapi_14873). Garbled edits: 0 in all 34 edit calls of all three arms (r69 pub024 had 9/17), so kf2's hint was never triggered and its -40 s and +1 solve are chance, not the hint. kf2 SyntaxError runs 3 (pub024 0). kf2c checklist stage worked mechanically: median 19 s (4-20 s), one request each, no reruns, the checklist in 100% of fixer requests (176/176), 1-5 of 5 lines filled, 15 of 30 quoted issue literals copied; but fastapi_15589 (its best chance) ended with no patch at 480 s, and it is +17 s, i.e. an LB timeout risk after evid3. Bars (set before): kf2 garble-resend n/a (no garbles in either arm), time 316 vs 356 PASS, solves 3 vs 2 PASS; kf2c solves 2 = 2 with no patch 3 = 3 FAIL, time +17 <= +25 ok, checklist 100% ok, stage 19 s ok. Pooled over r69+r70 on these 6 tasks: pub024 6/12; kf 1/6, kf2 3/6, kf2c 2/6. Checklist dropped (pooled with hunch r60/r62: no gain from a pre-stage that restates the issue).
- **RUN BUILT r70: kf2 (slim hint) and kf2c (slim hint + checklist stage), small first trial** (user 2026-11-10 "yes do so and try to add checklist to this pub as well"), kaggle/cells_skill_kf2c6 (only cell2 differs from r69), pub024 + kf2 + kf2c on r69's 6 tasks x 1 pass = 18 runs, ~1.1 h. Builder scripts/make_mine_arms.py ARMS_R70. **kf2** = pub024 + one section, the garbled-call entry only: on 'mandatory input parameters are not present' do not resend, end every text right after its last character (never a backtick), on a second failure use one run_command Python heredoc; prompt 1,609 -> 1,719 tokens (kf was 2,211: its size cost ~16 s/run more summarising and its general heredoc advice ~70 s/run of long scripts). **kf2c** = SequentialAgent [checklist, fixer]: the checklist stage has no tools (one reply), include_contents none, the issue in its system prompt, thinking 512 / max output 1536, and copies five lines (NAMES, MESSAGES, INPUTS, EXPECTED, EDGE CASES; 'copy, do not guess'); output_key checklist -> {checklist?} in the fixer's system prompt (kf2's prompt + a CHECKLIST section, 1,767 tokens before the checklist), so compaction cannot drop it; 28 calls / 8 min unchanged. Why copy-only and small: r60/r62's hunch (no tools, thinking 4096, guessed what tests check) tied pub024 9-9 over 24 task-runs at +60 s; the one checklist signal is fastapi_15589 (clock agents' checklist 6/8 vs 1/8, exact names copied), which is in this set. dist/kf2.zip, dist/kf2c.zip validated. Sim (data/sim/armsim_kf2c6.log, checklist role added): 6/6 end ok; checklist stage: no tools, max tokens 1536; kf2c fixer's system prompt holds the hint + the checklist marker, kf2's the hint only, pub024's neither; no unfilled placeholder. Reads: scripts/mine_bank/extract.py + kf_reads.py (garbles, resends, time) and scripts/mine_bank/checklist_reads.py FOLDER (stage seconds, reruns, checklist kept in fixer requests, lines filled, issue literals copied). **Bars (set before the run):** kf2: garbled calls resent identically below half of pub024's, mean agent time <= pub024 + 10 s, solves >= pub024 - 1 (the hint is worth ~17 s/run, so this trial can only rule out harm). kf2c: solves >= pub024 + 1, or equal with fewer no-patch runs; mean agent time <= pub024 + 25 s; checklist in 100% of fixer requests, stage median <= 30 s. Passing arms go to the full dev16 against pub024. Predictions: kf2 solves = pub024 +-1, ~+5 s; kf2c stage 10-25 s, solves +0 to +1 (15589 is its best chance).
- **RESULT r69 (data/results/2026-11-09_skill_kf6, 12 runs, 0.64 h): kf fixes the tool mistakes but solves 1/6 vs pub024 4/6 -> bar FAILED, kf not promoted.** Mechanism (scripts/mine_bank/kf_reads.py): garbled edits kf 1/12 (its last call in rich_3278, sent at 373 s after a 138 s / 4,189-token reply; its error never came back before time ran out) vs pub024 9/17 (4 resent identically); /tmp write errors 0 vs 1 run; SyntaxError 0 vs 1; reads without end_line 9/61 vs 20/60; new_string still first in 100% of kf edit calls (the order line did nothing; the no-backtick line or the example did the work). Side effect: kf ran 19 heredoc scripts (mostly experiments, 421 s of generation over 6 runs, ~70 s/run) vs pub024 4 heredocs + 32 python -c; mean agent 367 vs 354 s. Outcomes: only- 3 (fastapi_15589 wrong patch at 480 s; rich_3278 no patch: the garbled final edit; rich_3676 wrong patch, edited traceback.py from 99 s; pub024 solved it after 8 garbled edits to default_styles.py failed and it moved on), only+ 0, sign p = 0.25. pub024 4/6 is above its bank rate on these tasks (expected 2.4), kf 1/6 below. Reading: the prompt CAN fix format/tool mechanics tied to a message (garbles 53% -> 8% of edit calls here), unlike procedure rules; but the bank put this lever at ~17 s per run, and a 6-task pass cannot show a gain that small, only harm, and the outcome leans toward harm (the heredoc entry turned quick python -c checks into long scripts). evid3 LB still PENDING.
- **RUN BUILT r69: kf (known tool failures), small first trial** (user 2026-11-09 "build"; idea from the user: tell the model its measured mistakes in the prompt, task-free), kaggle/cells_skill_kf6 (only cell2 differs from r68), pub024 + kf on 6 tasks x 1 pass = 12 runs, ~45 min. kf (scripts/make_kf_arm.py) = pub024's prompt word for word + a KNOWN TOOL FAILURES section (+2,341 chars; same stated exception as r65 so the only difference is the information); agent.yaml, eval_config, sampling = pub024's bytes (tools, 28 calls, 8 min, LB time fit unchanged). Each entry starts from a tool-result message: 'mandatory input parameters are not present' -> do not resend, make the change with one run_command Python heredoc (indented example, asserts one occurrence, then git diff), and write old_string before new_string, never end a text with a backtick; 'Path traversal detected' -> write_file only writes in /workspace, run scratch Python as a heredoc; SyntaxError after python -c -> heredoc; grep CommandError exit 1 -> no match, do not rerun the pattern; read_file is_truncated -> pass start_line/end_line (~40 lines), summaries erase earlier results; budget_warning -> next call is the edit. No skill (LB timeouts, run_skill_script garbles too), write_file kept (ADK raises on an unlisted tool: flows/llm_flows/functions.py 491-505; the model tries write_file in 16% of runs). No braces or code fences in the section (asserted). dist/kf.zip validated by pack.py. Tasks (picked: pub024 solved 13-64% of each and made the targeted mistakes in 58-100% of its runs): fastapi_12942, fastapi_14873, fastapi_15589, rich_3278, rich_3676, rich_4079. Sim (data/sim/armsim_kf6.log): 4/4 end ok, the section in the system prompt of both kf runs and neither pub024 run, no unfilled placeholder. Read with scripts/mine_bank/extract.py OUT.jsonl data/results/FOLDER then scripts/mine_bank/kf_reads.py OUT.jsonl. **Bar to go to dev16 (set before the run):** the targeted mistakes drop vs the same-run pub024 and the bank (garbled edits resent identically below half of pub024's 73%, fewer /tmp-write and SyntaxError runs, fewer reads without end_line, heredoc edits appear after a garble); solves >= pub024's; no-patch not above pub024's; mean agent time <= pub024 + 15 s. Picked tasks, so passing only earns the dev16 run; dev16 decides any LB submission. Predictions: new_string-first stays ~90%+ (the template sorts arguments; the order line may move it a little); identical resends drop most; solves +0 to +1 of 6.
- **MINING 2026-11-09b (whole run bank: 2,518 31B runs, 442 pub024; scripts/mine_bank/): failures are commitment and tool mechanics, not localization.** (1) Time is model output: pub024 agent 368 s = 339 s generation + 12 s tools; ~2.5 replies/run of >= 30 s hold 161 s; those are thinking (~5,800 chars, 8 'Wait' each) and 82% end in another read/command, not an edit. (2) Same task + same arm, solved vs failed (123 groups, 24 tasks): 70% of failures are no patch; first source edit 268 s vs 402 s; among patched runs solved vs wrong barely differ. (3) No-patch runs read a gold file at median 16 s (solved 19 s; 89% vs 85% read it), then spend ~460 s / 22 calls without landing an edit. (4) pub024 no-patch runs (170/442): never tried an edit and ran out of time 41%; edit refused by the call budget 32%; every edit attempt failed 15%; only test/tmp edits 6%. (5) **Garbled edits:** the chat template sorts tool arguments alphabetically (data/gemma4_tokenizer/chat_template.jinja lines 4, 249), so the model writes new_string before old_string in 4,757 of 4,810 edit calls; 21.7% of those break: the end of new_string (usually a backtick, '\n`', 'e)`') swallows ',old_string:' and ADK answers 'mandatory input parameters are not present'. old-first calls break 9.4% (53 calls). 760 of 1,041 broken calls are identical resends; streaks up to 12; 147 of 258 streaks >= 2. write_file breaks the same way (216). run_command (one argument) lost its argument once in ~5,800 calls; a heredoc Python edit through run_command after a streak worked 18/18. (6) Other measured tool mistakes in pub024 (share of runs, cost per affected run): write_file to /tmp -> 'Path traversal detected' 15%, 29 s (pub024's own prompt says scratch files go in /tmp); python -c SyntaxError 13%, 33 s; garbled edit 11%, 6.2 calls, 51 s; grep no match shown as CommandError exit 1 56%, 2.4 calls; exact repeat of an earlier call 77%, 3.2 calls (read_file repeats: 183 of 232 come after a compaction); budget refusal 31% (62% of those end with no patch). read_file without end_line (150 lines) 28% of reads. Average across runs ~17 s and ~1.5 counted calls per run, so the direct gain is small; the hope is fewer budget refusals. Per-task mistake rates: scripts/mine_bank/pertask.py.
- **RESULT r68 pass 1 (data/results/2026-11-09_skill_ev4_16_p1, ziad23samer, 32 runs, 1.87 h): evid4 2/16 vs pub024 3/16** (only+ 0, only- 1: rich_4079), no patch 7 vs 7, mean agent 427 vs 387 s (+40), 9 vs 7 runs at the 480 s cap. Split: 4 r65/r67 tasks 1 vs 1 (both fastapi_11194; 14419 / 15589 / rich_3521 unsolved by both), 12 other tasks 1 vs 2. The bar needs >= +2 over both passes, so pass 2 would need evid4 +3, more than any single pass gap seen (r66 max +2). Evidence family on tasks outside r65/r67 so far: evid3 2/24 + evid4 1/12 = 3/36 vs pub024 5/36; the r65-r67 gains look tied to the picked tasks. Mechanism: stage 15-39 s except rich_3468 (273 s: one 251 s request for 520 tokens = server stall at concurrency 2, not the agent), NOTHING RELEVANT 2/16 (fastapi_13920, rich_3468). rich_4079 lost to a loop of 6 identical edit_file calls with old_string missing from the arguments (rich_3882: 12, still solved). Mined over all logs: such missing-argument calls happen in 11.8% of pub024 runs (52/442) and 14.5% of evid runs, and those runs solve more (46% vs 29%: they reach the edit), so not an evid4 effect. evid3 LB still PENDING (submitted 11-09 10:02).
- **RUN BUILT r68: evid4 vs pub024 on the full dev16** (user 2026-11-09 "build"), kaggle/cells_skill_ev4_16 (only cell2 differs from r66's ev16), 2 arms x 16 tasks x 1 pass = 32 runs, ~1.8 h; run twice on the same account = 2 passes (download after each run: the output is replaced). Agents byte-identical to r67's, no new sim. Bar for the LB (set before): over both passes >= pub024 + 2 solves, no-patch not above pub024's, mean agent time <= pub024 + 25 s, not below pub024 on the 12 tasks outside the r65/r67 set (fastapi_11194, 14419, 15589, rich_3521 are in both).
- **RESULT r67 (data/results/2026-11-09_skill_ev4_6, 18 runs): evid4 5/6, no patch 0, mean agent 395 s; evid3 3/6 (no patch 3, 469 s, 5 runs at the cap); pub024 3/6 (1, 370 s).** evid4 only+ 2 vs pub024 (fastapi_14873, 15589), only- 0; lost 14419 (wrong patch; evid3 solved it). Bar (set before) PASS: solves >= evid3 (5 vs 3), time <= evid3 + 15 s (395 vs 469), no broken runs. Stage 15-44 s, one search per run (rich_3278 once called with no args first), NOTHING RELEVANT 0/6; the pinned reply quoted a history line in 1/6 (14873, solved). evid3 here is below its r65 4/6 on the same tasks -> 6 tasks, 1 pass is noise-sized; evid4 goes to dev16.
- **RUN BUILT r67: evid4 small first trial** (user 2026-11-09 "yes build"), kaggle/cells_skill_ev4_6 (only cell2 differs from r65), pub024 + evid3 (both byte-identical to r65's) + **evid4** on r65's 6 tasks, 1 pass, 18 runs, ~1.2 h. evid4 = evid3 with evidence.py EVID4 = True: (a) source lines that use each term (non-test .py, package code before docs_src/scripts, 5 lines) - r66 had NOTHING RELEVANT in 7/32 runs; (b) the first definition's own history: git log -L over its current lines (ast range), newest 2 commits, changed lines only (22 lines) - evid3 helped where history mattered (fastapi_11194/14419/15589: 9/9 vs pub024 4/9); dotted names use their last part for the definition. Stage prompt rewritten: terms may be exact quoted strings (error messages). Tested on fastapi_15589 / rich_3882 snapshots (~1 s). Sim (data/sim/armsim_ev4_6.log): 6/6 end ok, evidence in the fixer's system prompt, new sections printed. Bar to go to dev16 (set before): evid4 solves >= evid3's, mean agent time <= evid3 + 15 s, no broken runs; read also NOTHING RELEVANT count and whether the history lines appear in the pinned reply.
- **MINING 2026-11-09 (call budget; 420 pub024 runs with requests, Oct 25 - Nov 9):** 131 (31%) hit the 28-call budget, median 170 s of time left; half of pub024's no-patch runs (82/162) are budget hits; 41 tried an edit after "Tool call budget exhausted" (refused). Same task: budget-hit runs solve 35 points less (14 of 17 tasks). In budget-hit runs ~23 of ~33 calls are reads; 7.6 read_file calls/run on a file already read twice (150-line cap + compaction), 3.3 exact repeats, 2.2 searches with no match (shown as an error with empty message). evid3 does not reduce budget hits (12/38 vs 14/38). Replay of refused edits (scripts/grade_patches.py, scorer's verify_task, 7 local snapshots): only fastapi_15589's are valid (gold PASS), 1 of 3 passes; rich_3470 / rich_3882 golds FAIL locally (exit 3), so those 15 replays say nothing. Not tried again: more calls (reads longer, LB time), issue in system prompt (r42 null), reviewer (r22-r24 null), hints (0/129 tasks).
- **RESULT r66 (dev16 x 2: data/results/2026-11-09_skill_ev16_p1 and _p2, ziad23samer, 64 runs): evid3 8/32 vs pub024 5/32, but the whole gain is on the 4 tasks r65 also ran.** Pass 2 alone: evid3 4 vs 3 (only+ 14419, 15589; only- rich_4079), mean agent 377 vs 368. Both passes: no patch 15 vs 17, mean agent 387 vs 373 (+14 s); only+ 4, only- 1, sign test p = 0.375. Split: 4 r65 tasks evid3 6/8 vs pub024 2/8 (fastapi_11194 / 14419 / 15589 solved by evid3 in all 3 runs incl. r65 = 9/9, pub024 4/9); **12 unseen tasks evid3 2/24 vs pub024 3/24, +29 s**. Bar (set before): >= +2 solves PASS (+3), no-patch not worse PASS, time <= +25 s PASS (+14), not below pub024 on the 12 unseen FAIL (2 vs 3). So 3 of 4; the failed one is a 1-solve gap, noise either way. Evidence kept in the system prompt named a gold file in 18/32 runs, NOTHING RELEVANT in 7/32 (fastapi_13920, 15280, 15800 both passes; rich_3468 once), gold file missing in 7/32; naming the file was not enough on most tasks (solved 6 of the 18). LB evid3 submitted by the user 2026-11-09 10:02, PENDING.
- **LB PREPARED evid3 (2026-11-09, user: "prepare it while the second run is going on"):** dist/submission.zip = dist/evid3.zip (repacked, pack.py checks pass, md5 8e8b1602, files identical to the evid3 that ran in r65 / r66); the previous one kept as dist/nn32rcn2_submitted.zip. Submitted before r66 pass 2 on purpose (no pending submission, nothing since 11-07, the day's slot would go unused); the user uploads. Risk: evid3 runs ~20-25 s longer per task than pub024 (0.18, fitted). r66 pass 2 = the same notebook re-run on ziad23samer (I had wrongly said two accounts; the user ran one).
- **RESULT r66 pass 1 (data/results/2026-11-09_skill_ev16_p1, ziad23samer, 32 runs, 1.78 h): evid3 4/16 vs pub024 2/16** (only+ 2: fastapi_11194, fastapi_15589; only- 0), no patch 9 vs 9 (end=time 6 vs 4), mean agent 396 vs 378 s (+18). pub024 on dev16 before: 3 + 3 (r43), so 2 is a low draw. Mechanism held: one search in 13/16 (2 in 3), stage 12-41 s, evidence in the system prompt in every fixer request when the stage found some; NOTHING RELEVANT in 3/16 (fastapi_13920, 15280, 15800). rich_3934 evid3: 24 edit_file calls (failed-edit loop, 45 requests), the source of most of its 25 bad edits. Waiting on pass 2 (second account) before the bar is judged.
- **RUN BUILT r66: evid3 vs pub024 on the full dev16** (user 2026-11-09 "build"), kaggle/cells_skill_ev16 (only cell2 differs from r65), 2 arms x 16 tasks x 1 pass = 32 runs, ~2 h; the same notebook run on two accounts = 2 independent passes (64 runs). Agents byte-identical to r65's (pub024 4 files, evid3 10 files), so no new sim. Tasks not picked for being solved; 4 of 16 (fastapi_11194, 14419, 15589, rich_3521) were in r65, so also report the 12 unseen. Bar for an LB submission of evid3 (set before): over both passes >= pub024 + 2 solves, no more no-patch runs than pub024, mean agent time <= pub024 + 25 s; also hold on the 12 unseen tasks (not below pub024). Mechanism reads: evidence in 100% of fixer requests, one search per run, stage seconds.
- **RESULT r65 (data/results/2026-11-09_skill_ctx6, 24 runs, 1.47 h; downloaded from ziad23samer/fork-of-fork-of-generation-all-shards-gpu; ziadsamer/fork-of-generation-all-shards-gpu still returns r47's E4B run of 11-04): evid3 is the first evidence arm whose mechanism works, and it meets the bar exactly.** Solved / no patch / mean agent s: pub024 3/2/392, **evid3 4/1/415** (only+ 1: fastapi_14419; only- 0), autochk3 2/3/420, evchk 3/3/462. Bar (set before): >= pub024 + 1 and time <= pub024 + 25 s -> evid3 passes at the edge (+1 solve, +23 s agent / +25 s wall); autochk3 and evchk fail (solves, time). Mechanisms: evidence in the fixer's system prompt in 100% of fixer requests (evid3 150/150, evchk 133/133), even after compaction; exactly one evidence call in 12/12 runs (the refusal never needed); stage 15-48 s (2-3 requests); reply 4-20 lines, NOTHING RELEVANT once (evchk rich_3278). Check script run after an edit: autochk3 3/6, evchk 2/6 (r64: 1/6), no solve gain. evid3's first edit came later (339 s vs 254). 6 tasks, 1 pass: +1 solve is within chance; per the small-first-trial rule evid3 goes to the bigger run, the check arms are dropped.
- **RUN BUILT r65: evidence and check kept in the fixer's system prompt** (user 2026-11-08 "build"), kaggle/cells_skill_ctx6 (only cell2 differs from r64), 4 arms x the same 6 tasks x 1 pass = 24 runs, ~1.5 h. Fix for r64's finding: each stage's final reply is saved with ADK output_key and placed in the fixer's system prompt ({evidence?} / {check?}, filled from session state like {problem_description}), which every request re-sends and compaction keeps. The fixer is pub024's prompt word for word with one section added at the end (prompts/fixer.md; not a full rewrite on purpose: r60's rewritten fixer was slower, and this keeps the comparison to the information alone). Arms (scripts/make_mine_arms.py ARMS_R65): **evid3** = evid2's one search (refusal kept), then the stage replies with at most 15 lines of the result copied exactly (or NOTHING RELEVANT), max output 1536 / thinking 512; **autochk3** = autochk2's checker (thinking 1024), its CHECK READY note in the system prompt under a CHECK SCRIPT section; **evchk** = evidence -> checker -> fixer, both sections (30 calls). evidence.py: a refused call now prints the first result again (stored in .git/agent/evidence_done), so a harness re-run of the stage cannot overwrite the saved reply with nothing; REPLY line swappable. dist zips validated. Sim (data/sim/armsim_ctx6.log): 8/8 end ok; the fixer's system prompt holds the evidence marker in 4/4 evid3/evchk runs and the check marker in 4/4 autochk3/evchk runs, no unfilled placeholder; sim-only errors identical to r64's sim. Bars (set before): solves >= pub024 + 1 or = with fewer no-patch runs; mean agent time <= pub024 + 25 s (evchk carries two stages, ~80 s, so it must win time back); no broken runs. Mechanism reads: evidence in the system prompt in every evid3/evchk fixer request (and its length / NOTHING RELEVANT share); stage seconds; check.py runs after an edit (r64: 1/6).
- **RESULT r64 (data/results/2026-11-08_skill_fix6, 24 runs, 1.42 h): no arm clears the bar; the fixes worked mechanically but the stages' text is DROPPED AT COMPACTION.** Solved / no patch / mean agent s: pub024 4/1/413, evid2 2/3/425, autochk2 3/2/398, cap2k32 3/0/403 (pub024 above its history, ~2.9 expected). Mechanisms: (1) evid2: refusal mostly held, 1-2 evidence calls in 5/6 runs (14873: 6, each refused), stage 7-59 s (2-8 requests); the evidence named a gold file in 6/6 runs. (2) autochk2: checker 39-64 s (was 71-218), wrote check.py 6/6; the fixer ran it in 5/6, but after an edit only in 1/6 (fastapi_11194, solved, 6 runs of it). (3) cap2k32: 0 no-patch runs, used ~32 calls, 2 'length' finishes. Pooled with r63 (different arm versions): cap family 3/10 vs pub024 5/10 -> cap dropped. **Key finding: the evidence (and the CHECK READY line) reach the fixer as 'For context' user text, which ADK compaction removes: the evidence was in only 41-85% of fixer requests, gone after the first compaction at 93-252 s (known since 11-02, PATTERNS entry; I missed it when building r63/r64).** r60's scouts avoided this with output_key -> {key?} in the fixer's system prompt. Next: re-run evidence and check with their result injected into the fixer's system prompt.
- **RESULT r63 (data/results/2026-11-08_skill_mine4, 24 runs, 1.5 h): nothing clears the bar; 4 tasks too hard to separate (4/24 solved in all).** Solved / no patch / agent s: pub024 1/3/422, hpub 1/3/480, cap2k 0/4/366, autochk 1/3/467, evid1 1/3/469, evhunch 0/4/480. Mechanisms: (1) **evidence agent looped**: told to make one call with 2-4 names, it called the script 2-17 times with one name each (rich_4079: 17 calls, 102 s; plus load_skill / list_skills / a wrong-tool call), eating the fixer's shared call budget (stage 17-102 s evid1, 40-152 s evhunch). The single-call prompt rule was ignored again; fix by refusal in the script (second call -> ALREADY DONE). (2) autochk: pub024 ran .git/agent/check.py in 3 of 4 runs (a user-text instruction from another agent was followed), but the checker took 71-218 s to write it (thinking 4096). (3) cap2k: calls got faster; 2 runs used all 28 calls by 252 s with no edit, so the call budget became the limit (2 'length' finishes, no harm seen). (4) hpub stage 31-96 s. **Legality of repo evidence (checked 2026-11-08, saved data page of Sep 26):** the data description says each snapshot is 'a full Git repository frozen at base_commit with forward commit history removed so agents can safely run git status, git log, and git diff inside /workspace without leaking future fixes'; skills that run scripts are allowed by the harness rules. Checked fastapi_15589's snapshot: HEAD = all refs (7,185 commits), none of the gold patch's added lines appears in any commit.
- **RESULT r61 information test pass 2 (data/results/2026-11-08_skill_info38_p2, 76 runs, account engziadsamer): REPLICATES.** Base 4/38, info 15/38 (only info 13, only base 2, sign p 0.007). Pass 1 was 2 vs 15. Pooled 2 passes: base 6/76, info 30/76, only info 27 vs only base 3, sign p 0.00001. Info agent solved the same 13 tasks in both passes (15 and 15, 17 in either); base 1 in both (5 in either): the information makes these tasks reliably solvable, not luckily. 15 tasks solved with information and never without. Info runs faster (agent 291 vs 325 s) and hit the cap less (19 vs 24 of 38); no patch 12 vs 11. Group split (reports vs test lines) not redone: my quick parse of INFO_TESTS gave 9 tasks, not the 19 of r45; redo with the r45 grouping before quoting it. Prediction (info >= base + 8) RIGHT (+11).
- **RUN BUILT r63: data-mining arms, small first trial** (user 2026-11-08 "do so"), kaggle/cells_skill_mine4 (only cell2 differs from r60/r62), builder scripts/make_mine_arms.py, 6 arms x 4 mid-rate dev16 (fastapi_14419, 15589, rich_3521, 4079) x 1 pass = 24 runs, ~1.5 h. In every arm the fixer is pub024 byte for byte (renamed fixer); one idea each: **hpub** = r60 hunch note -> pub024 (tests 'slow, not bad'); **cap2k** = pub024 with max_output_tokens 2048 / thinking 1536 (cuts 3.1% of calls, ~11% of model time; the harness answers a cut with a 'keep reasoning short' nudge and resets the count after any tool-call turn); **autochk** = checker (write_file only) writes .git/agent/check.py printing PASS/FAIL from the issue's example, says 'Run it after each edit' -> pub024; **evid1** = one call to scripts/agent_evidence/evidence.py (skill 'evidence': tests, definitions, git log -S with the changed lines around the name, changelog; Python files only; ~1 s on fastapi's 7,185 commits; finds 92aad5689 'Fix convert_underscores=False' for fastapi_15589) -> pub024; **evhunch** = same call + a hunch-style note grounded in it -> pub024. Earlier stages reach pub024 as 'For context: [agent] ...' user text (ADK contents.py); all stages include_contents none + issue in system prompt; +1 tool call for stages that call a tool. Dropped from the list: the check gate (wrapper used in only ~42% of commands, r57) and a check stage after pub024 (the harness ends the run after submit_patch + final text). dist/*.zip validated with pack.py. Sim (data/sim/armsim_mine4.log): 12/12 end ok; pub024 sees the hunch note, the evidence output, the evidence note and the CHECK READY line; check.py runs from the workspace and imports the package; cap2k sends max tokens 2048. Carry forward to 16 tasks (set before the run): solves >= pub024 + 1, or = pub024 with fewer no-patch runs; mean agent time <= pub024 + 25 s; no broken runs. Also read: stage seconds (expect evid1 < 30 s, evhunch / autochk < 75 s), how often pub024 runs check.py after an edit, cap2k truncation nudges and its agent-time drop (predict -20 to -50 s). Prediction: most arms land within pub024 +-1; 4 tasks only catch breakage, timing and big effects.
- **DATA MINING for new agent ideas (2026-11-08; user: paper on hold, focus on a better agent; run_table 2,710 runs + 38,485 requests of Nov results). Within-task differences (runs of the same task compared; correlations, not causes):** exec (python -c / script) after the first edit +11 pts (21 tasks +, 4 -), any exec +9.7 (19 vs 0), test after edit +5.4 (20 vs 6), scratch/repro file +6.8, git used +7.5; edited only gold files +23.5 (9 tasks), 2+ files edited -6.8 (1 vs 6), 2+ edits -4.5. No effect: first edit before 180 s (+0.7, 13 vs 21 tasks), rereads, compaction, long calls (-1.6), more reasoning. Time: decode ~30 tok/s, model = 98% of agent time; 2.5% of calls (>=60 s, median ~2,500 output tokens of thinking) take 23% of model time; thinking_token_budget is loose (2048 arms still exceed 2048 out tokens in 2-3% of calls). Solved runs finished by 240 / 300 / 360 / 420 s: 47 / 59 / 75 / 83%. Hunch's extra time comes from the rewritten fixer (output tokens sc_none 10.4k vs pub024 7.9k in r60; first edit 307 vs 157 s), not the 28 s hunch call.
- **RESULT r62 (data/results/2026-11-08_skill_hunch16, 32 runs, 1.9 h): hunch FAILS the bar.** pub024 6 / no patch 6 / agent 366 s; hunch 5 / 8 / 429 s (+63 s); only hunch 1 (fastapi_12942), only pub024 2 (fastapi_5624, rich_3470). On the 8 r60 tasks this pass: pub024 3, hunch 2. Pooled r60+r62, 24 task-runs each: **pub024 9, hunch 9**; no patch 10 vs 9; hunch costs ~60 s more. r60's 4 vs 3 was a draw from noise; the two-stage screen caught it before a submission. Hunch dropped.
- **RUN BUILT r62: hunch goes bigger** (user rule 2026-11-08: the promising arm gets the bigger run), kaggle/cells_skill_hunch16 (only cell2 differs from r60's scout8; hunch files identical), pub024 vs hunch, 16 tasks = the 8 r60 tasks (second pass) + MID8 (fastapi_14349, 14873, 5624, 12942, rich_3278, 3676, 3480, 3506; not in r60, pooled solve rate 0.21-0.81), 1 pass, 32 runs, ~2 h. Bar set before the run (to pack hunch for the LB): pooled r60+r62 solves (24 task-runs) >= pub024 + 2, no-patch runs not above pub024's, and mean agent time on the 16 <= pub024 + 25 s (nn32rcn2 fitted the LB at about pub024 + 12 s locally).
- **RESULT r60 (data/results/2026-11-08_skill_scout8, 48 runs, 2.7 h; user ran the 8-task scout8, not scout4):** solved / no patch / agent s: pub024 3 / 4 / 306; sc_none 2 / 3 / 399; sc_tests 1 / 4 / 388; sc_hist 1 / 5 / 431; sc_both 1 / 4 / 414; **hunch 4 / 1 / 407** (only hunch: fastapi_15589, rich_3470; only pub024: fastapi_11194). Bar (solves >= pub024 + 1 or equal with fewer no patch; agent <= 420 s): **hunch passes, all scouts fail.** pub024's history on these 8: rate 0.40 (expect 3.2), agent 386 s, so its 306 s here was a fast draw. Scouts: briefs were mostly on target (right test files, the exact earlier commits on the buggy lines, e.g. rich_3521 split_cells pos history, fastapi_15589 convert_underscores) but took median 129 / 156 / 242 s (tests / hist / both; max 422 s) against the predicted 40-90 s: the 'be quick' prompt line was ignored (as event-triggered-rules-only says), and the fixer was left 4-13 model calls. NOTHING RELEVANT in 6 of 24 briefs. Hunch: one no-tool call, median 28 s (max 125 s), writes LIKELY PLACE / EXPECTED BEHAVIOUR / EASY TO MISS; fixer then edits more (7/8 runs edited vs pub024 4/8). hunch vs its structural control sc_none: 4 vs 2 (only hunch 2, only sc_none 0). 8 tasks, 1 pass: not significant. Next idea if wanted: a fast evidence stage by structure (one fixed script call that greps tests and git log -S for the issue's names, then the brief), not by prompt.
- **RUN r61 (given 2026-11-08): information test pass 2** = kaggle/cells_skill_info38 unchanged on a second account, parallel to r60 (user runs scout8, the 48-run version, not scout4). Paper evidence, not an agent candidate. Keep its output folder apart from 2026-11-05_skill_info38 (labels are .1 again).
- **LB nn32rcn2 = 0.12 (user, 2026-11-08): FITTED in time** (no timeout) -> run_command + setup agent fits at 8 min; the skill shell was the timeout cause. 0.12 = ~7 of ~58 vs pub024 0.18 (~10.5); identical packages range 0.12-0.26, so not a ranking. Best-of-k ceiling from run_table (63 tasks with >=5 runs, all arms pooled): 1 attempt 20.9, best of 2 24.7, of 3 26.9, of 5 29.8 (perfect picker); 21 tasks never solved, 16 under 20%.
- **PACKED 2026-11-08: dist/submission.zip = nn32rcn2** (user chose to submit despite the 2 s time-rule miss): 11 files, byte-identical to what ran in r57/r59; LB fit test for run_command + setup agent. Expect about pub024's 0.18.
- **RESULT r59 (dev8rcn2, data/results/2026-11-07_skill_dev8rcn2, 16 runs):** 8 winnable dev16, 1 pass: nn32rcn2 4 (only it: 14419, 3470), pub024 3 (only it: 3180); agent s 357 vs 345, wall 367 vs 356 (+11, -38 to +74); no patch 3 / 3. Submit rule (set before): solves >= pub024 PASS; agent time <= pub024 + 10 s FAIL by 2 s (diff well inside noise). With r57 (other 6+2 tasks): nn32rcn2 8/16 vs pub024 7/16, agent s ~369 vs ~367. Decision is the user's: rule missed narrowly.
- **RUN BUILT r59: nn32rcn2 again before a possible LB submission** (user 2026-11-07), kaggle/cells_skill_dev8rcn2 (only cell2 differs from r57: tasks + arms), pub024 vs nn32rcn2 (files byte-identical to r57's), the 8 winnable dev16 (WINNABLE7 + rich_3180; r55-r58 had 6 of them + 2 val), 1 pass, 16 runs, ~1 h. Submit rule set before the run: nn32rcn2 solves >= pub024 and mean agent time <= pub024 + 10 s (pooled with r57 on the shared tasks for context only).
- **RESULT r58 (setup8b, data/results/2026-11-07_skill_setup8b, 32 runs, 1.9 h):** solved pub024 2, nn32rc3 3, nn32rcn3 2, sq1c2a8rcx3 2; agent s 386 / 425 / 381 / 467. Pooled r57+r58 (16 runs each, same 8 tasks): pub024 6, nn32rc 7, nn32rcn 6, a8rcx 2; agent s ~387 / ~423 / ~381 / 467. pub024 itself went 4 -> 2 on identical tasks: 8-task differences are noise. Install 8/8 every arm. FINDING: the only change r57 -> r58 was the install output line the main agent sees in the shared history (r57 "READY. Run every command with run_command: python .git/agent/run.py ...", r58 "INSTALLED. Your job is done..."); main prompts byte-identical. Wrapper use in the first 3 commands fell 30/72 (42%) -> 6/72 (8%), later 139/377 -> 45/420: a tool-output line steers the model about 4x more than the same rule in the system prompt. SECOND FINDING: when an agent ends a turn without submit_patch the harness nudges "Please continue..." and re-runs the ROOT agent (agent_runner.py 680-718), so a SequentialAgent restarts at the setup agent, which sees the whole history (3/48 runs; it then calls tools it lacks: the user's r57 run_command errors). Fix if setup arms continue: include_contents: none on setup. Conclusion: no run_command arm beats pub024 on 16 runs; nn32rcn ties it at the same time.
- **RESULT r57 (setup8, data/results/2026-11-07_skill_setup8, 32 runs, 1.88 h):** solved pub024 4, nn32rc2 4, nn32rcn2 4, sq1c2a8rcx2 0; agent s 388 / 420 / 380 / 467; no patch 2 / 2 / 1 / 5. Setup agent works: install 8/8 in every arm (r55/r56: 0-3/8), 1 call and ~3 s in 23/24 runs; the run_command loop the user saw happened once (nn32rcn2, 1 call, ~55 s), so r57 stands and r58 only removes that. Bars: install PASS; through the script FAIL (nn32rc2 44%, nn32rcn2 42%, a8rcx2 25%; bar 90%): the model skips the wrapper from its first commands (9-12 of the first 24 go through), not to dodge refusals (nn32rcn2 after a refusal 33/33 through); shell garbling 0% PASS; agent time <= pub024 only nn32rcn2; solves not below: nn32rc2, nn32rcn2. a8rcx2's 0: two runs looped on edit_file without old_string (60 and 33 calls; 104 in all vs 4 in r56), missing-argument calls are rejected before the budget counts them, like not-found tools. No arm passes every bar; nn32rcn2 is closest (ties pub024, faster). Decision waits for r58 (same main agents) to pool 16 runs per arm.
- **RUN BUILT r58: r57 with the setup agent's run_command loop fixed** (user 2026-11-07), kaggle/cells_skill_setup8b (only cell2 differs from r57), pub024, nn32rc3, nn32rcn3, sq1c2a8rcx3, same 8 tasks. r57's log showed its setup agent calling run_command (a tool only the next agent has): its skill text and the install output both said "run every command with run_command" (copied from r55's single agent). A not-found tool call is rejected before the harness counts it (swegemma context.py check_budget), so only the time cap ends that loop. ...3 = ...2 with only the setup agent's SKILL.md and install output changed to "INSTALLED. reply INSTALLED and stop" (commit b2538ce); main agents byte-identical. Sim: 8/8 end ok, new install line 6/6, old READY line 0. Run alongside r57 on another account. Same bars as r57; also count setup-agent calls and seconds per run in r57 vs r58.
- **RUN BUILT r57: setup agent first** (user 2026-11-07), kaggle/cells_skill_setup8 (only cell2 differs), pub024, nn32rc2, nn32rcn2, sq1c2a8rcx2 on r55's 8 tasks, 32 runs, ~1.9 h. Each = its r55/r56 arm with SequentialAgent [setup, main] or [setup, fixer, finisher]; setup = le6's pattern (only get_status + the skill, thinking 128, "install, reply INSTALLED, stop"); the main agent has no skill and its prompt says the setup step installed the shell (no install call; a8rcx2's checklist is the first call again). The install costs one budget call. Earlier arms rebuild byte-identical (checked; committed copies kept). Builder fixes on the way: clock_rc's dict renamed CLOCK_RC_ARMS (it shadowed the older CLOCK_RC tuple). Sim: setup installed 6/6, every main-agent command through the script, no "can't open file" in the new arms (data/sim/armsim_setup8.log; pub024's errors there are the sim's fake a.py plan). Zips in dist/. Bars as r55: install in nearly every run, at least 90% of commands through the script, garbled under 5%, agent time at most pub024's, solves not clearly below.
- **RESULT r55 + r56 (data/results/2026-11-07_skill_rc8, _clockrc8; scripts/paper/analyze_rc.py): the install was skipped, so the design was not tested.** First call was run_command in 23 of 24 rc8 runs and 12 of 16 clockrc8 runs; install made in 0-3 of 8 runs per arm; when made it worked (READY, 5 of 5). Commands through the script: nn32rc 22%, rcn 15%, rcs 17%, sq1c2x 4%, sq1c2a8rcx 39%; the rest raw. Many first calls already used python .git/agent/run.py, which failed (not installed) and the model went raw. Solved / no patch / agent s: rc8 pub024 3/4/367, nn32rc 2/4/434, rcn 1/4/424, rcs 1/6/386; clockrc8 pub024 4/3/382, sq1c2x 6/2/458, sq1c2a8rcx 3/4/449. With the script mostly unused these are not results for the design. Known before and missed: the model ignores setup calls (sk_nav call 1 wrong 16/16); le6's separate setup agent installed in 16/16. Fix: SequentialAgent with a setup agent whose only tool is run_skill_script.
- **RUN BUILT r56: the 8-min clock agents through run_command** (user 2026-11-07), kaggle/cells_skill_clockrc8 (only cell2 differs), pub024, sq1c2x, sq1c2a8rcx on r55's 8 tasks, 24 runs, ~1.4 h. sq1c2x / sq1c2a8rcx = sq1c2 / sq1c2a8rc (8 min, 80 calls, fixer -> finisher, thinking 4096) with an install call and their own clock script run as .git/agent/run.py through run_command; script changes: start time cached in .git/agent/t_base, command on stdin without blocking. Prompt changes: the shell lines, and a8rcx's checklist is the call after the install. Direct script test and sim OK (data/sim/armsim_clockrc8.log; the sim's checklist step now reads the system prompt). dist zips not built yet. Local runs cannot show scorer slowness: only a submission tests the shell hypothesis; 80 calls stays a separate fit risk (submit only if agent time is clearly under pub024's, else 36 calls).
- **RUN BUILT r55: run_command family on 8 tasks** (user 2026-11-07: basic arm plus the other ideas as separate arms, against pub024 only, small set to save quota), kaggle/cells_skill_rc8 (only cell2 differs), 32 runs, ~1.9 h. Tasks: fastapi_14419, 15589, 12942, 11194, rich_3521, 4079, 3278, 3470. nn32rc: nn32's no-numbers design (32 calls, 8 min, thinking 2048) with commands through run_command + .git/agent/run.py installed once, LIGHT git (1 git process per call before an edit, start time cached), command may come on stdin. nn32rcn: also no read_file. nn32rcs: also where / outline / lines. 18 unit tests; sim through the real harness OK (data/sim/armsim_rc8.log), including a raw bypass call and read_file with the tool removed. dist/nn32rc.zip, nn32rcn.zip, nn32rcs.zip validated. Bars, set before the run, to pick one for the LB: agent time at most pub024's; garbled commands under 5%; commands through the script at least 90%; install made in nearly every run; solves not clearly below pub024. 8 tasks x 1 pass only catches clear problems. Check bypass by arm, refusal next moves, quoting errors.
- **RESULT r54 filter (data/results/2026-11-07_skill_filter26, 6.1 h):** 26 tasks not in the screen. Solved / no patch / agent s / wall s: pub024 2 / 12 / 391 / 411; nn36p 4 / 2 / 390 / 423; nn36c 3 / 1 / 360 / 405; nn32 4 / 2 / 401 / 435. Only arm vs only pub024: nn36p 2-0, nn36c 1-0, nn32 2-0. Bar: nn36c keeps, nn36p (+12) and nn32 (+23) fail on wall. Pooled with r52, 42 tasks: nn32 11, nn36p 11, nn36c 9, pub024 7; only arm vs only pub: 5-1, 5-1, 4-2 (p 0.22, 0.22, 0.69); no patch 7, 4, 6 vs 21; wall 407, 414, 401 vs 405. The new arms turned no-patch runs into wrong patches: wrong patches take nearly all their time. Grading adds wall time: runs with a patch 38 s mean (median 11), no patch 7 s (r54); similar direction in r52, r51, r50, r43. So fewer no-patch runs lengthen wall even when agent time is equal; if the scorer's 12 h includes grading, more edits cost fit. Overruns of the cap: nn36c fastapi_14583 674 s, nn32 rich_3938 528 s.
- **LB nn32 (submitted 11-06 17:45): COMPLETE with no score; user reports a timeout, 14.8 h after submission.** Our saved rules (Sep, may be stale; live page not readable by API) say the 12 h includes setup and excludes validation, so local wall time, which includes grading, is the wrong yardstick: agent time over 42 tasks is nn32 383 s, pub024 390 s. nn32 was not slower locally and still timed out. Pattern: every 7-8 min agent with the skill shell timed out (sq1c2, sq1c2t7, srep7, nn32); 6 min fit (sq1c2a6 twice); 8 min with run_command fit (pub024, sk_a2, sk_a2_32, mix), le5 is the exception. Untested hypothesis: the shell is much slower on the scorer (private, maybe larger repos; Docker): each shell call runs git log and git diff several times.
- **RUN BUILT r54: filter on 26 tasks** (user 2026-11-06: run, filter, continue): kaggle/cells_skill_filter26 (only cell2 differs from the screen), arms pub024, nn36p, nn32, nn36c by the r52 rule (tie at no patch 5 broken by mean wall), the 38-set minus SCREEN16, 1 pass, 104 runs, ~5.6 h. Arms unchanged from r52, no shell-recovery line. **nn32 packed for the LB as a fit test: dist/nn32.zip = dist/submission.zip; user uploads.**
- **Shell-loop numbers (11-06):** garbled shell calls do not count against the call limit: fastapi_12942 and 14419 in nn36c had 61 and 67 garbled calls with a harness count of 12. They cost 357 and 270 s. Removing all such time: nn32 353 to 336 s, nn36 393 to 383, nn36c 386 to 338, nn36p 390 to 351 (upper bounds). Arms with the recovery line still garble: 6-18% of shell calls, up to 35 in a run, 3-16 s lost a run; pubstop without it 16%, 20 s. So a prompt line may help little. The harness rejects these calls before the script runs, so the clock cannot refuse them.
- **RESULT r52 screen (data/results/2026-11-06_skill_screen16, 5.2 h, scripts/paper/analyze_screen.py):** 16 picked tasks, 1 pass. Solved / no patch / mean wall (diff vs pub024, 95%): pub024 5 / 9 / 396; pubclock 6 / 6 / 376 (-20, -56 to +17); nn36 5 / 5 / 400 (+4); nn32 7 / 5 / 362 (-35, -84 to +12); nn36c 6 / 5 / 394 (-2); nn36p 7 / 2 / 399 (+3). All 5 pass the filter; rule then ranks by no patch: nn36p 2, then nn32 = nn36 = nn36c 5, pubclock 6. No difference is resolved. nn family pooled 25/64 solved, no patch 17/64, vs pub024 5/16, 9/16. Median first edit: pub024 222, pubclock 230, nn36 306, nn32 204, nn36c 167, nn36p 222 s, so removing numbers shows no consistent delay. Late refusal: next call read_file 45, edit_file 17, shell 21 over all arms, so read_file is the escape. Garbled shell calls are loops in a few runs: nn36c 67, 61, 19 in single runs (48 s a run lost), nn36p 23 (39 s), nn32 32 (17 s), nn36 12 (10 s), pubclock at most 2 (3 s); nn prompts only tell the model how to recover from a malformed edit_file. Harness call counts stay low in those runs, so garbled shell calls appear not to count against the limit (not checked against harness source). Next, for the user: arms on the 26 tasks of the 38-set not in SCREEN16.
- **RESULT r51 pubstop vs pub024 (data/results/2026-11-06_skill_pubstop, 4.4 h, scripts/paper/analyze_pubstop.py):** 38 tasks: pubstop 7, pub024 6 (only pubstop 3, only pub 2). Mean wall 412 vs 415, diff -3 s (-37 to +30), so the bar (25 s saved) is missed. Agent 394 vs 405, tool overhead 17 vs 10 s. By whether an edit landed (20 runs each; groups differ by task): edited 357 vs 418 s, at the cap 3 vs 12, submitted 17 vs 9; no edit 436 vs 391 s, at the cap 11 vs 6. Stop refusal fired in only 4 of 20 edited runs (9 total), so the rule alone does not explain the 61 s. First edit median 227 vs 292 s. Malformed: shell 77 of 519 calls (15%; 'skill_name' lost, ~20 s a run), edit_file 0 vs 45. Harness vs logged calls differ about equally in both arms, so garbled shell calls escaping the limit is not shown. Predictions: wall saves 20-35 s WRONG (3 s); solves within +-2 RIGHT; shell swap costs garbled calls RIGHT, larger than expected. Control across runs: pub024 6, 8, 6 solved, wall 427, 382, 415; 2 tasks in all three, 12 in any: one pass cannot resolve a 25 s or 2-solve gap. Not submitting pubstop; pubclock in r52 adds the no-edit refusal.
- **RESULT r53 temperature replay (data/results/2026-11-06_replay_temp, 270 calls, 30 contexts from 30 tasks, 61 min, 0 errors):** T 0.2 / 0.7 / 1.0: on the real lines 27 / 22 / 20% (paired vs 0.2: -4, -11 to +1; -7, -13 to +1); keeps looking instead of editing 29 / 40 / 51%; on the real lines among edit calls 38 / 37 / 41%; malformed 4 / 4 / 1%; old_string not in file 10 / 12 / 9%; tokens 834 / 942 / 932. Where the logged run missed the real lines, some sample hit them in 2 of 18 contexts at every temperature. Distinct edits per context of 3 samples 1.3 / 1.27 / 1.0. Hotter sampling delays the edit and does not find other places: do not build the hot spawned agent. Limits: one step, location only; a no-tools hot idea step is untested.
- **RUN BUILT r53: temperature replay** (user 2026-11-06), kaggle/cells_replay_temp: pub024 requests just before their first source edit, re-sent at T 0.2, 0.7, 1.0, thinking 2048, up to 30 contexts x 3 x 3 = 270 calls, ~45-60 min, stops itself at 85 min. Score: python3 -I scripts/paper/analyze_replay_temp.py results.jsonl. Measures where edits land and malformed calls, not hidden tests. Decides whether a hot spawned agent is worth building. Fake-server test OK.
- **ANALYSIS 11-06: docs/ARCH_ANALYSIS.md** (2,434 runs: what helps by agent, prompt, skill, tool; scripts/paper). Task 64%, agent 0.7%, chance 35%; wrong edits are in the right file, 83% fail on assertions; only enforced events move behaviour; 28-call agents lose 6-12% of runs to first trying an edit at call 27+.
- **RUN BUILT r51: pubstop vs pub024** (user 2026-11-06), same 38 tasks, 1 pass, concurrency 2, ~4.3 h, kaggle/cells_skill_pubstop (only cell2 differs from cells_skill_srep8). pubstop = pub024 (8 min, 28 calls, same procedure) with run_command swapped for scripts/agent_clock/run_stop.py: 60 s after the last change to a tracked source file only git status / diff / checkout -- / rm run; the first command after an edit always runs; edit_file and read_file are free; no rule for runs with no edit. 8 unit tests (test_run_stop.py); sim through the real harness OK (data/sim/armsim_pubstop.log). Bars, set before the run: submit if mean wall is at least 25 s below pub024 AND solves at least pub024 minus 1; if so, next step = spend the saved time on a longer cap. Written before the result: wall saves 20-35 s (less than the what-if's 37 s, because reads are not gated); solves within +-2 of pub024 (noise); the shell swap itself may cost a few garbled calls. Check: refusals per run, read_file after a refusal, garbled shell calls, last-edit-to-end time.
- **CORRECTION 11-06: "stopped by the cap 0/100" and "no capped run solved" are almost certainly a label artefact.** end='time' comes from res.error (cell4 end_reason); of 39 pub024 runs at 480 s, the 35 unsolved are 'time' and the 4 solved are 'ok' (likewise 3 of srep8's 4 solves at 420 s). Real rate at the cap: 4/39, 4/17 with a patch. Do not use the old claim in the paper. What-if on 108 pub024 runs (r43, r49, r50; assumes behaviour unchanged), 20 solved, mean wall 400 s: 7 of 20 solves end after 420 s; solved 19%, no edit 24%, wrong edit 57%; 254 s before first edit; 60 s after last edit in failed runs. Stop X s after last edit: X=60 keeps 19/20 at 363 s. Stop at T with no edit: T=300 keeps 14/20 at 333 s. Local wall does not predict fit: sq1c2t7 325 s on d40 (pub024 ~340) timed out.
- `srep7` on the LB: TIMED OUT, no score (user 11-06). 7 min, 40 calls, outside the pattern below ("every submission that fitted had max_tool_calls 28-32 or 6 min"): 12 h / ~118 tasks = ~366 s per task; srep7 mean wall 408 s (38 tasks), 396 s (dev16, above the ~380 s bar set for it), cap hits 24/38 vs pub024 15/38. No LB logs, so the cause is inferred. Check before any submission: 6 min, or 28-32 calls.
- r50 `srep8` DONE: 4 vs pub024 8 of 38; pooled with r49 12 vs 14 of 76, short 8 vs 8 of 56: the self-written report shows no gain. Not submitting srep8 (RESULT r50 below).
- Information test pass 2: rerun kaggle/cells_skill_info38 unchanged, user starts/finishes by Saturday Nov 7; paper only; cutoff Nov 9, otherwise report one pass plainly.
**Next for me (not started; user must say go):** paper draft, published as a private page; then compare self-written reports with the real GitHub ones (data/info_experiment/gh/issues.json; no quota). User said wait for a go on the draft: last question asked "start the draft now?".
**Paper story (angle not final; user wanted to brainstorm; my recommendation):** agent designs plateau on hard tasks; missing information explains much of it; plus what a small model follows. Evidence: (1) plateau: 45 full dev16 passes of 35 agents, mean 2.8, sd 1.02, chance predicts 1.05; ~3,200 runs overall. (2) Information test: 2/38 -> 15/38 (reports 1/19 -> 10/19, test lines 1/19 -> 5/19). (3) Self-written reports: srep7 8 vs pub024 6 of 38, short 6 vs 3 (partial). (4) Picked tasks mislead: 71% vs 25% vs 12%. (5) Replays: no distance effect, user > tool > ..., tool believed over claims 76 vs 3 (own claim 0/33). (6) Noise, E4B 1/64, fine-tuning failures. Predictions written before results are scored in docs/PAPER_NOTES.md (mostly wrong; report that). Related work there too: only abstracts read so far; read full texts before citing.
**User must decide for the paper:** the rules say one Kaggle account per person and our runs used several accounts (ziad23samer, ziadsamer, fatmazenhom, engziadsamer): settle before writing methods; authors and AI-use disclosure; public analysis notebook (no competition data, describe tasks in general terms). Which notebook output replay 2 used as contexts (asked, unanswered).
**Agents:** dist/submission.zip = nn32 (11-06, LB fit test); srep7 timed out. LB: sq1c2a6 0.12, 0.10 (Kaggle's list on 11-06; earlier notes said 0.12 twice); pub024 0.18; 6-min submissions 0.12-0.15, 8-min 0.17-0.18. Best fitting agent remains pub024 / sk_a2 (0.18). Dropped: 12B (mix 2, 1 of 16; allowed but no bonus), E4B for now (1/64, finishes early, wrong patches), repro-shows-no-bug note, soft cap, refusal at 180 s (untested, only targets the no-edit half).
**Lessons to keep:** always a same-run control; never back a submission with the picked 24 alone; 2 passes cannot measure gains under ~2 tasks; judge on dev16 / unpicked sets. Simulator: data/sim/armsim.py (gitignored); SIM_CELLS=<folder>. Date slip: folder 2026-11-06_skill_srep and "user 2026-11-06" in r49/r50 were really 2026-11-05. Analysis scripts lived in the session scratchpad (only scripts/paper/analyze_srep.py kept); rebuild others from the RESULT entries.

### CHECKPOINT 2026-10-30 (read after the newest; the dated entries below are the details)
- **Latest result (r28, 2026-10-29):** sq2 19/24 on e24 (best e24 reading; fair same-set single runs after the
  set was picked: pub024 14, sk_a2_32 15, sa2 18). BUT the second attempt changed no outcome (details in RESULT r28)
  -> the gain is the fixer -> finisher STRUCTURE or noise (sd ~2.2 on 24). Next: re-run sq2 (pass 2) to confirm,
  and fix the weak spot (second attempt only starts if the fixer finishes by 240 s: 9/24 did).
- **r29 RESULT (sq1 vs sq2 on q12, 4 accounts):** sq1 3/12, sq2 4/12 (r28 sq2 on the same 12: 7). The second attempt
  ran 0 times in 12 sq2 runs (finisher reached 3x, all SUBMIT NOW). -> sq2's 19/24 was mostly luck; sq1 = sq2 = pub024
  level. 13 of 24 runs ended with NO patch (12 at the 8-min limit, 1 empty hand-over) -> the main loss is "no edit
  in time" on hard tasks, not wrong patches (3). Next lever: get an edit into the tree on hard tasks.
- **r30 RESULT (sq1c vs sq1 on q12):** sq1c 6/12, no patch 2 | sq1 4/12, no patch 6 (r29: sq1 3 / 7 no patch, sq2 4 / 7).
  The clock's REFUSAL worked (refused in 8/12 runs; 3 solves came right after a refusal: 11194, 3506, 4079) even
  though 76% of the fixer's shell calls were GARBLED (model closes file_path with a backtick after the nested args
  object -> skill_name lost -> ADK INVALID_ARGUMENTS). Fix the call shape next (RESULT r30 below).
- **r31 RESULT (sq1c2 on e24):** 18/24 (sq2 r28: 19/24; diff = noise), q12 subset 6/12 (= sq1c r30), no patch 3
  (sq2: 5), mean 309 s/task (sq2: 365). Garbled shell calls 76% -> 8% (positional_args works). Remaining no-patch
  causes: (a) after REFUSED the fixer escapes into read_file and never edits (12942, 15589); (b) one long thinking
  call (rich_3521: 131 s + 109 s, ~4k tokens each) -> no refusal ever fires. Details in "RESULT r31" below.
- **r32 RESULT (q12, 36 runs):** sq1c2 (control) 8/12, sq1c3 (reads through the clock) 7/12, sq1c4 (thinking 2048)
  7/12 -> neither change helps; drop both. Clock arm on q12 over 3 runs: 6, 6, 8 (mean 6.7) vs sq1 3, 4 and sq2 4, 7,
  pub024 3 -> sq1c2 is our best local agent (e24 18/24 = sq2 level). Details in "RESULT r32" below.
- **LB (2026-11-02):** sq1c2 8-min (submitted 10-30) -> "exceeded the allowed runtime" (Notebook Timeout), as
  estimated (~370-395 s/task vs pub024 ~340 s which fits). sq1c2t7 (7 min, 325 s/task on d40) submitted 11-01 02:57,
  -> ALSO "exceeded the allowed runtime" (2026-11-02). Kaggle CLI via uvx needs `--with six`.
  Pattern: every submission that fitted had max_tool_calls 28-32 (mix, pub024, sk_a2, sk_a2_32; le6_t6 at 6 min);
  timed out: le5 (28 calls, 8 min), sq1c2 (80, 8), sq1c2t7 (80, 7), 12B. With 80 calls the clock is the only brake;
  hidden tasks are from private repos (~116-120), local fastapi/rich times underestimate cap hits. Worst case
  120 x (6 min + ~25 s) + setup = 12.8 h -> a 6-min cap fits only if roughly < 80% of runs hit it.
- **RUN BUILT (r36, not run; user 2026-11-02: the bar is sq1c2 8-min accuracy):** sq1c2t6 alone on d40, kaggle/cells_skill_d40t6.
- **RUN BUILT (r37, user to run):** sq1c2f6 (finish events, 6-min cap) alone on e24 x 2 passes, kaggle/cells_skill_e24f6
  (cell2 only); bar = sq1c2 8-min history (e24 18; q12 6, 8). Goal: f6 solves >= sq1c2 while ending runs sooner. Details "RUN BUILT r37".
- **RUN BUILT (r38, user's second account):** sq1c2f6ra vs sq1c2f6rc on e24 x 2, kaggle/cells_skill_e24f6r. Details below.
- **r37 STOPPED by the user** after 8 runs: sq1c2f6 5/8 vs sq1c2 8/8 on the same tasks; 2 empty patches at the 360 s
  cap (rich_3278, fastapi_14349, both solved by sq1c2 at 405-480 s). User: wants faster solving, not cut-offs.
- **RUN BUILT (r39, user to run):** sq1c2a8 = sq1c2 (8 min) + event A only, e24 x 2, kaggle/cells_skill_e24a8.
  r38 REPLACED (user: build the others on 8 minutes): **RUN BUILT r38b (second account):** sq1c2a8ra vs sq1c2a8rc on
  e24 x 2, kaggle/cells_skill_e24a8r (cell2 only). kaggle/cells_skill_e24f6r is obsolete (6-min base).
- **r39 (sq1c2a8) STOPPED: the run froze** after 18 good runs (14/18, mean ~219 s vs sq1c2 ~298 s on the same 18):
  rich_4079 tools 382 s (27 s/call), then fastapi_14873, rich_3506, rich_3006 with 0 model calls in 480 s each; no
  vLLM error in the log. Cause found (reproduced locally): the clock scripts ran commands with subprocess.run(timeout)
  which kills bash only -> children (a looping repro, background jobs) survived on the same VM. The harness's own
  run_command uses start_new_session + os.killpg (adk_eval_core/sandbox/subprocess_sandbox.py L81/L112). FIXED in
  run.py, run_finish.py, run_finish2.py (run_group: own process group, whole group killed after every command; partial
  output kept on timeout). Tested: sleep behind &&, background job holding the pipe, CPU loop -> return at the
  timeout, 0 leftovers; events re-tested. WATCHDOG in cell4 (builder): 2 finished runs in a row with 0 model calls ->
  no new tasks, run ends by itself (outputs saved); tested on the r39 sequence (fires after rich_3506).
- **r39 re-run (fixed, account 1) pass 1: sq1c2a8 18/24, mean 233 s** (sq1c2 18/24, 309 s) -> same accuracy, ~25% faster.
  r38 (OLD 6-min f6ra/f6rc, account 2) pass 1: ra 16/24 (246 s), rc 16/24 (253 s); all losses vs sq1c2 were its
  394-480 s solves (11194, 4079, 3278, 3676, 14873); rc gained 12942, 15589; ra or rc solves 19 tasks.
- **RESULT r39 (sq1c2a8, fixed clock + watchdog, data/results/2026-11-02_skill_e24a8): pass 1 18/24 (232 s), pass 2
  20/24 (294 s) = 38/48, mean 263 s** vs sq1c2 18/24 (309 s), pub024 14, 15. 21 tasks solved in >= 1 pass, incl.
  rich_3521 (316 s) and rich_3506 (319 s) never solved by sq1c2, and fastapi_14419 (455 s). Event A fired in 37/48 runs.
  At 480 s: 5 (p1), 7 (p2). No freeze. One empty early finish (fastapi_11194 p1, 126 s): the model wrote its tool call
  as TEXT ("<|tool_call>call,read_file{...}") -> plain text = handover -> finisher submitted an empty patch. Same
  leak in 3 runs of all logged runs (~0.5%: sa2 rich_4079, sq1 fastapi_14873, this one). 8 min / 80 calls -> not LB-safe.
- **r38 request log (account 2, 96 runs, data/results/2026-11-02_skill_e24f6r/requests; results file still missing for
  pass 2): REPEAT BLOCK NEVER FIRED (0 refusals) although 76 identical non-repro commands were repeated** -> bug: the
  fingerprint walked /tmp, where the harness keeps every task's sandbox (also the parallel task's) -> always "changed".
  FIXED in run_finish2.py (git status + diff, .git/agent files, loose files directly in /tmp only); tested with a busy
  /tmp/swegemma_sandbox_* folder (refused), a loose /tmp file and a code edit (run). r38's ra/rc numbers therefore
  measure issue-in-prompt (+ checklist), the 300 s window and the 6-min cap, not the repeat block. rc: checklist shown
  45x, checklist refusals 8; finish-window refusals ra 5 (4 runs), rc 10 (10 runs), first at median 320 s.
  Rebuilt submissions/sq1c2a8ra / rc and kaggle/cells_skill_e24a8r (cell2 changed). A stuck-run stop "no repro pass by
  T -> finish" (136 logged runs): solves really lost 12/93 at 270 s, 11 at 300, 9 at 330, 6 at 360.
- **sq1c2a8 time vs calls (48 runs, data/results/2026-11-02_skill_e24a8/a8_time_calls.png):** calls do not separate
  solved from failed (failed 7-54 calls, 7 of 10 <= 24 calls yet 480 s; cap 28 cuts 7/38 solved runs, ends 3/10
  failed; 50: 2/38 vs 1/10). Time does: solved runs end by ~330 s or at 451-480 s (none between); 8/10 failed at 480 s.
  Of the 6 late solves, 2 had their last edit before 360 s (14873 at 352, 4079 at 348) -> 6-min cap loses ~4/38.
- **RUN BUILT r40: sq1c2a6** = sq1c2a8 with max_time_minutes 6 (clock 360; event A kept; no 300 s window; warning 180,
  refusal 270), prompt rewritten (finish from 320 s; "when the clock says REPRO PASSES"). Fake-clock tested. Expected
  ~17 per 24, LB ~11.5 h. kaggle/cells_skill_e24a6 (cell2 + cell4 with the watchdog), e24 x 2, 48 runs, ~2 h.
  dist/sq1c2a6.zip. If it holds ~17: the LB candidate.
- **RESULT r40 (sq1c2a6, e24 x 2, data/results/2026-11-02_skill_e24a6):** 16 + 18 = **17.0 per 24** (as predicted),
  mean 230 s (solved 183 s) vs a8 19.0 at 263 s (solved 220 s); 18/48 runs reach 360 s vs 12/48 at 480 for a8. No
  watchdog stop, no freeze. Tasks lost vs a8 are mostly late ones the cap cuts (14873 p1, 3676 p1, 4079 p1, 3506 p1);
  a6 gained 11194 x2 and 15589 x1 (noise either way). Beats f6rc 16, f6ra 15, pub024 14.5.
  sq1c2a6 SUBMITTED to the LB (2026-11-02).
- **RESULT r41 (8-min a8ra / a8rc, fixed repeat block, e24 x 2, data/results/2026-11-02_skill_e24a8r):** a8rc 18 + 22
  = **20.0 per 24** (mean 293 s, solved 255 s, 12/48 at cap); a8ra 17 + 18 = 17.5 (295 s, 16/48 at cap); a8 19.0
  (263 s, solved 220 s). rc solved fastapi_15589 2/2 again (4/4 over r38+r41; a8/ra/a6 1/8 together) and 12942 2/2,
  11194 2/2; lost 3506, 3676 p1, 4079 p1. +1 per 24 over a8 is within pass noise (a8: 18/20), but 15589 looks real
  (the checklist copies exact names). Issue text alone (ra) does not help. rc is ~30 s/run slower.
  requests.jsonl (same script for all, scratch rq.py: malformed = run_skill_script args not {work, scripts/run.py,
  one-string positional_args}): malformed shell calls a8 7.6%, a8ra 13.1%, a8rc 11.3% (f6ra 13.3, f6rc 21.0) ->
  the issue text in the prompt raises the glitch ~1.5x; the checklist does not add to it at 8 min.
  Repeat block STILL 0 refusals (18 repeats with no edit/write between and identical output). The run started 17:27,
  4 min after the fix commit (17:23), so probably the fixed code. Locally the fixed block refuses (armsim now repeats a
  command: 4/4 refused) -> something on Kaggle changes loose /tmp files between calls (candidates: unpacked-wheel tars
  of the parallel task, verification .patch files left by NamedTemporaryFile(delete=False), the harness's
  write_file temp files). Fix to build: fingerprint without scanning /tmp; stat only /tmp paths named in the command.
  Harness fact: subprocess sandbox sets HOME and TMPDIR to the task's work dir; the skill executor writes
  .adk_exec_<rand>.py in the work dir per call (git-excluded via .git/info/exclude).
- **RUN BUILT r42: sq1c2a6rc vs sq1c2a6c** (user: checklist with and without the issue text), both = sq1c2a6 (6 min,
  event A, no window) + checklist (.git/agent/issue.md first; shown at first edit and REPRO PASSES) + repeat block.
  rc also has the issue verbatim at the end of the system prompt; c writes the checklist from the harness task message
  on call 1. Repeat-block fingerprint no longer scans /tmp (git status + diff, .git/agent, /tmp paths named in the
  command); fake test: /tmp noise still refused, changed /tmp/repro.py or tree re-runs; armsim 4/4 refused.
  Prompts written fresh (HEAD_SQ1C2A6RC_FIX / HEAD_SQ1C2A6C_FIX). kaggle/cells_skill_e24a6c (cell2 + cell4), e24 x 2,
  96 runs, ~3.5-4 h. Bar: sq1c2a6 17.0 per 24 (r40, separate run).
- **LB: sq1c2a6 = 0.12** (2026-11-04; ~7 of ~58 public tasks; did not time out). e24 is picked from tasks already solved,
  so its 17/24 does not predict the LB; on the 6 dev16 tasks in e24 a6 got 3/6, 4/6, the same as mix (~3.5) and pub024
  (3/6). Do not back a submission with e24 alone. First clock agent to get a score; a scorer-only problem is not excluded.
- **PATTERNS over 432 clock runs on e24 (2026-11-04; picked tasks, so rates are inflated):** finished with a patch 314/326
  solved (96%); stopped by the cap 0/100 (70 of them no edit at all); failures: 70 cap+empty, 30 cap+patch, 12 finished
  wrong, 6 finished empty. 12 tasks solved 18/18 in every arm, so agents differ only on the other 12. Issue < 150 chars:
  21% solved vs 81-93% (unpicked d40t7: 3/10 vs 16/30); 26% of public issues and 6/16 of dev16 are that short, e24 only
  5/24. Failed runs: same calls (26 vs 23) but 2x the tokens and 12.4 vs 7.2 s per call -> a call cap cannot tell them
  apart. Compactions do not separate (70-76% at 0-2). Per 24 by cap: 6 min 16.5, 7 min 18.0, 8 min 18.7. Time estimate
  (118 tasks x mean wall, 15% solved): sq1c2 14.2 h (timed out), sq1c2t7 11.9 h (timed out), sq1c2a6 10.8 h (fit), a8 13.2 h,
  a8rc 14.8 h, a6rc 10.0 h. So a8rc was not submitted: 8 min does not fit unless ~80% of hidden tasks are solved.
- **RESULT r43 (full dev16 x 2, data/results/2026-11-04_skill_dev16a6):** sq1c2a6 3 + 5 = 4.0/16, mean 321 s (wall 330); pub024 3 + 3 =
  3.0/16, mean 377 s (wall 387). +1 per pass is within noise, but 15% faster. a6's 24 failures: 12 no edit (11 at cap), 12 wrong edit
  (8 at cap, 4 finished). Finished with a patch 8/12 (e24: 96%). Repro passed 6/11 (e24: 91%). Issue < 150 chars: a6 1/12 (8 no edit),
  pub024 0/12; longer: a6 7/20 (9 wrong edit, 4 no edit), pub024 6/20. fastapi_14487, 13920, 14258 edited wrong in all 12 runs of both.
  Time: pub024 fits the LB at 387 s wall per run here, so a6 at 330 s has ~50 s spare (rough, concurrency 2 vs the scorer's 1); a 6.5-7 min
  cap may fit. 7 min = sq1c2t7 timed out, but it had no event A. Earlier refusal only targets the no-edit half; a forced guess on a short
  issue is usually wrong (3 edits, 1 solve).
- **WHY HARD TASKS FAIL (2026-11-04, tasks.jsonl vs traces):** heuristic "hidden requirement" = a test literal or new def/class name that the
  gold patch adds and the issue never mentions: 25/129 public tasks (19%; undercounts). Clock runs on those: 0/18 (12 tasks, few runs each) vs
  70% on the rest (picked set inflates that). dev16: 15280, 14487, 14258, 3180, 15800 flagged = at most ~11/16 reachable. Examples: 14258 agent
  raises the right error but the test wants AssertionError + an exact sentence; 14487 test wants "Validation errors:". 13920 not hidden: agent
  patched shared.py helpers, gold unwraps in analyze_param. Short issues are a title + GitHub link (no internet in the sandbox): 22% solved,
  29/129 of public tasks. pub024's 8 finished-empty runs all hit its 28-call limit with no edit (164-348 s), so the call limit is what saves
  it time and costs it nothing on those runs. LB 0.12 vs 0.18 = ~3.5 tasks, within noise (sd ~2.9 tasks per submission).
- **Replay: stop at N calls with no edit** (real runs): N=28 dev16 a6 cut 9/32, lost 1 of 8, saves 35 s per run; e24 a6rc cut 4/48, lost 1 of 35, saves 11 s;
  e24 a8 cut 6/48, lost 3 of 38, saves 32 s. N=24 loses 6 on e24 a6rc; N=40 saves ~2 s. Not built. Could pay for a 6.5-min cap.
- **Short issues (<150 chars; 34 public, 30 of them rich; 22 hold a link), 32 runs (dev16 a6, e24 a6rc, a8):** gold file reached in 30/32 (often in the first seconds), edited in 15,
  solved 8. So locating is NOT the problem: the model does not know what is wrong. Commands: read_file 317, grep 259, python 95, git log/show 0. Idea (not built, wait for r44): event
  telling the model the issue is only a title: run the named function on edge-case inputs in one script and look for wrong output.
- **RESULT r44 (e34 x 2, data/results/2026-11-04_skill_e34rn, 5.3 h):** on e24: rn 14 + 16 = 15.0, rnt 18 + 15 = 16.5 (a6rc 17.5, a6 17.0, other runs).
  Full dev16: rn 1 + 3 = 2.0/16, rnt 2 + 1 = 1.5 (a6 4.0, pub024 3.0 in r43). The 10 extra dev16 tasks: 0 solves in 40 runs. No arm improves;
  rn vs a6rc -2.5 per 24 is ~1.7 sd, so the note may hurt or it is noise; it fired in 11-12 runs per arm, 4 solved each. Thinking 2048 (rnt):
  no harm vs rn in the same run, solved runs faster (219 vs 250 s); one failed call still wrote 8192 tokens. MISTAKE: no same-run control
  (a6 or a6rc) -> cross-run comparisons only. Decision pending; the note is not kept without a same-run win.
- **LB: sq1c2a6 again = 0.12** (2026-11-05; 0.12 twice). 6-min submissions: le6_t6 0.15, sq1c2a6 0.12, 0.12. 8-min that fit: mix 0.17, sk_a2 0.18, sk_a2_32 0.17, pub024 0.18. Few scores, noisy, but the split is clean; on dev16 a6 still matched pub024, so the cap may cost more on hidden repos.
- **RESULT replay 2 (data/results/2026-11-05_replay_probe2; 444 calls, get_status rule, new contexts; source notebook of the contexts not recorded, so levels may differ by agent):** no distance effect in tool results: <=900 71/120 (59%), >=1200 48/84 (57%), p 0.78; replay 1's 30% vs 55% did NOT replicate; pooled 50% vs 56%, p 0.30. No step at 1024. Pooled speakers: user near 35/42 (83%), own text near 31/41 (76%), system start 31/44 (70%), user far 28/41 (68%), tool near 43/84 (51%), own text far 19/41 (46%), system end 19/43 (44%). Tool near vs user near: replay 2 alone p 0.056, pooled p 0.0004; direction repeats, replay 1's gap was overstated. Both start-vs-end and own-text near-vs-far found after looking at the data: exploratory. Controls 0 in both. Non-compliant runs almost never mention the rule in their reasoning (1/143): they miss it rather than reject it.
- **RESULT r50 srep8 vs pub024 (data/results/2026-11-05_skill_srep8, 4.3 h, concurrency 2):** 38 tasks: srep8 4, pub024 8 (only srep 1, only pub 5, p 0.22). Short 28: 2 vs 5. dev16: 3 vs 3. Pooled with r49: all 12 vs 14 of 76, short 8 vs 8 of 56, dev16 6 vs 6 of 32; 9 distinct tasks solved by each agent. r49's short-issue lead (6 vs 3) did not repeat: no evidence the self-written report helps. Same agent across runs: pub024 6 then 8 (5 tasks both), srep 8 then 4 (3 tasks both). Cap hits srep8 25, pub024 8, and no capped run solved. Mean agent time 400 vs 364 s; srep8's cap is 7 min, pub024's 8. Reporter median 133 s (allowed 90, srep7 194); 29 of 38 were refused and told to report; same time on long issues (132 s) as short (135 s). DETAILED rule ignored: first reply always had a tool call; DETAILED was said once, after investigating, on a 54-character issue (rich_3942). SHOWN: yes solved 1/15, no 3/21, no format 0/2. Model 354 s and tools 7 s per run (pub024 338, 14). 7 capped runs had 96-291 s after their last finished model reply, 3 of them ending on a read_file, i.e. a long fixer reply still running at the cap (fixer thinking still 4096). Do not submit srep8.
- **RUN BUILT r50: srep8 vs pub024** (user 2026-11-06), same 38 tasks, 1 pass, ~4 h, kaggle/cells_skill_srep8 (cell2). srep8 = srep7 with reporter thinking 1024, output 2048, 90 s; first reply DETAILED on any issue with code, error, input, expected output or more than three sentences; fixer warned at 200 s, refused at 270 s. dist/srep8.zip. Check: reporter time, DETAILED label by issue length, cap hits, solves vs srep7 8 / pub024 6.
- **RESULT r49 srep7 vs pub024 (data/results/2026-11-06_skill_srep, 4.5 h):** 38 tasks: srep7 8, pub024 6 (only srep 3, only pub 1, p 0.63). Short 28: 6 vs 3 (3 vs 0). dev16: 3 vs 3; long dev16 2 vs 3 (lost 11194). Wall on dev16 396 vs 402 s; pub024 was 387 in r43. Cap hits 24 vs 15. Bar (+4) not met. Reporter median 194 s against its 120 s share (29/38 reached the refusal). Reports are often sensible and specific, some wrong. dist/submission.zip = srep7.
- **RUN BUILT r49: srep7 vs pub024** (user 2026-11-05). srep7 = SequentialAgent [reporter, fixer, finisher], 7 min, 40 calls. Reporter (skills/look, scripts/agent_clock/run_report.py): no edit_file / submit_patch, shell refuses tree changes, BUG SHOWN / NO FAILURE on script runs, refuses all from 120 s; writes a report. Fixer: fresh (include_contents none), issue in system prompt, report as user message; warning 240 s, refusal 300 s, event A. kaggle/cells_skill_srep (cell2 differs from info38), 28 short gradable + rest of dev16 = 38 tasks, 1 pass, 76 runs, ~4 h. dist/srep7.zip. Control pub024 (best LB that fits), not a6. Bars: submit if clearly above pub024 (~4+ of 38) AND mean wall on dev16 tasks <= ~380 s (pub024 fit at 387; rough). Sim OK: fresh handover in the user role, undeclared edit_file returns an error and the run goes on, shell edits refused, BUG SHOWN fires.
- **RUN BUILT r48: second information pass + second replay** (user 2026-11-05). Pass 2 = rerun kaggle/cells_skill_info38 unchanged (labels stay .1; keep the folders apart), ~3.5 h. Replay = kaggle/cells_replay_probe2: get_status rule only, new contexts, 7 distances, speakers, controls, 450 calls, no conflict test, ~80 min.
- **RESULT r45 information test (data/results/2026-11-05_skill_info38, 1 pass, 3.5 h):** base 2/38, info 15/38 (only info 14, only base 1, sign p 0.001). Linked reports: 1/19 -> 10/19 (p 0.004); no patch 10 -> 4, cap 13 -> 7. Test lines: 1/19 -> 5/19 (p 0.22). Missing information
  is a main wall on short issues; even told what the tests check, most flagged tasks still fail.
- **RESULT r47 E4B dev16 (data/results/2026-11-05_skill_dev16e4b, 1.3 h):** sq1c2a6e4b 1 + 0, pub024e4b 0 + 0 of 16, mean ~133 s, 0 cap hits, 17-18 of 32 finish under 120 s. Only 4-5 of 32 ran no repro or pytest, so "refuse handover until a repro ran" is not the fix. 'Shell' invented once in 64 runs: my worry was overstated.
- **RESULT r46 replay probe (data/results/2026-11-05_replay_probe):** 452 of 1,272 calls (mean 40 s; 75-min stop), random order. Compliance does not fall with distance and shows no drop at 1024: tool <=900 19/111, >=1200 26/88. Marker rule almost never followed; action rule much more. Near speakers: user > own text > tool. Conflict: believed the tool 76, claim 3 (own claim 0/33, teammate 3/46). A rule written in tool output is weak, so blocks work because they block, not because of the channel.
- **RUN BUILT r47: E4B on the full dev16** (user 2026-11-04, small-model bonus): sq1c2a6e4b (sq1c2a6, model line only) vs pub024e4b (pub024, model line only), 2 passes, 64 runs, early stop off. kaggle/cells_skill_dev16e4b
  (cell2, cell3 serves E4B, cell4). dist/sq1c2a6e4b.zip, dist/pub024e4b.zip. Clock seconds unchanged although E4B decodes ~2.5x faster (rung-1y): first test the design as it is. Reference: E4B 0/4, 0/4 on 4 tasks with an early agent.
  Unverified: whether today's wheelhouse serves E4B (it did on 10-11; the model's config could not be fetched from here). If cell 3 fails, it fails during setup.
- **RULES UPDATE (official page pasted by the user, 2026-11-04; our saved pages were from Sep 26):** allowed models: 31B, 12B, E4B, E2B (gemma-4-*-it-qat-w4a16-ct), one model per submission. Bonus $10,000 for the top
  E2B/E4B submission; it must be one of the team's 2 final picks and stays eligible for the other prizes. My "12B is not allowed" was out of date. L4 notebooks must be attached to the competition: the replay probe needs it as an input too.
  Our E4B/12B data: 1a E4B 0/4, 0/4 on 4 tasks (2026-10-11); 12B mix 2, 1 of 16. Toeda (Zenodo): E4B 10.0% -> 15.4% on 104 public tasks with scaffolding. Small-model standings not checked.
- **RUN BUILT r46: replay probe** (user 2026-11-04; kaggle/cells_replay_probe: cell1, cell3 as before + cell4_probe). No tasks: 30 real fixer contexts re-sent with one change. A: dormant rule ("if a later tool
  result contains [probe 7] ...") at 10 distances around the 1024 window. B: same rule from system / user / tool / own text, near and far. C: own or teammate claim vs tool result (PASS/FAIL), both orders and values. Controls:
  trigger only, rule only. ~1,200 calls, ~1 h run + setup (~2.5 h quota), ends by itself (no new call after 75 min). Tested against a fake server on real requests: placement accurate, controls 0, no errors. Real tokenizer on Kaggle.
  Novelty search and predictions: docs/PAPER_NOTES.md. Saved rules pages date from Sep 26: re-check the allowed models on Kaggle (a competitor repo says 4 variants since 10-22; unverified).
- **ALL RUNS REVIEW (2026-11-04; aggregates; ~3,200 runs: rung1 252, rung2 136, rung3 392, 12B 164, generation ~700 + regraded, skill/clock 1,552):** PLATEAU: 45 full dev16 passes of
  35 agents (single, orchestrator, locator-editor, reviewer, skills, thinking, clock, ...): mean 2.8, sd 1.02, about what identical agents would give; same few tasks solved; period means flat Oct 13 -> Nov 4.
  LB: 0.08 -> 0.10 -> 0.12 -> 0.15 -> 0.17 -> 0.18 in Oct 6-26, then flat. Fine-tuning: 12B v1 0/16, 31B adapter test stopped at 0/7 vs base 3/7 (small; parked). Paper angle open; candidates in chat.
- **Obedience by distance (504 fixer runs, traces; confounded, not causal):** forbidden graph tools 1 of 12,659 calls (no decay; the rule simply holds). Malformed shell 9-15%, no trend; 8.2% just after compaction vs 13.4% later.
  Soft warning -> edit on next call 43/462 (9%); refusal 44/137 (32%). Own repro: passed -> solved 275/301 on finished runs (e24-heavy); dev16 6/11. Local/global attention NOT tested by traces; a controlled distance probe would be needed.
- **RUN BUILT r45: the information test** (user 2026-11-04; also the paper's main experiment). sq1c2a6i vs sq1c2a6info, identical agents = sq1c2a6 + issue in the
  system prompt (compaction drops the task message, so added text would vanish mid-run; the sim showed it). info arm's task text gets: 19 short issues: the linked GitHub
  report (data/info_experiment/gh/issues.json, public, title + first post, no comments, cut at 3000 chars per report); 19 flagged tasks: added test lines read from
  tasks.jsonl at run time (never committed; cut at 3000 chars). kaggle/cells_skill_info38, 38 tasks x 2 arms x 1 pass, 76 runs, ~4 h (~8 h quota), early stop off.
  Paper plan: audit of 1,552 runs (information gap, selection bias, what a small model obeys, noise, time), aggregates only. Draft Nov 6-7, submit by Nov 11.
- **RUN BUILT r44: sq1c2a6rn vs sq1c2a6rnt** (user 2026-11-04: option 1 + option 2 if it does not hurt). rn = sq1c2a6rc + clock
  note REPRO SHOWS NO BUG (python script, exit 0, a FIXED line or only "passed" lines, no source edit; never grep/pytest).
  rnt = rn + thinking_budget 2048 (only difference). Replay on real runs: a8rc fires in 10/48 runs, incl. 4 of its 8 failures
  (3506 x2, 3521, 4075); a6rc 7/48, 1 of 13 failures. Trigger unit-tested (8 cases). kaggle/cells_skill_e34rn (cell2 + cell4),
  e24 + rest of dev16 = 34 tasks x 2, 136 runs, ~5-5.5 h, early stop 12 of 34 (3 was set for dev16 alone; never bites here). Sim OK. Bars: a6rc 17.5/24 (r42); dev16 from r43 (a6, pub024).
  Refusal at 180 s stays separate, waiting for r43.
- **a8rc time analysis (2026-11-04; 48 runs, e24):** 8 min cannot fit by speed alone: failed runs must average ~350 s (now 484).
  First edit decides: <120 s 15/15 (ends 118 s), 270-330 s 3/3 (406 s), >330 s 6/6 (470 s), never 0/7. Refusal -> edit lag
  median 97 s. Soft cap replayed: 17/24 at 11.4 h, no better than real a6rc 17.5 at 10 h (replays understate: cap 360 gives
  14.5 vs real 17.5). IDEA, not built, user: wait for dev16 r43: a6rc with refusal 180 s / warning 120 s.
  Long rounds (>=45 s): 38 of 1381 calls = 30% of model time; decode is steady ~30 tok/s (0 slow calls with few tokens), 87% of
  the text is reasoning: the model runs code in its head before write_file (14), edit_file (9), read_file (8). 11 reach
  ~4096 tokens, 7 of them cut mid sentence. Failed runs 1.5 long rounds per run, solved 0.65. Correction to r32's reading:
  "calls > 60 s did not drop" at thinking 2048 proves little, as 2048 tokens at 30 tok/s is already ~68 s.
- **RUN BUILT r43: sq1c2a6 vs pub024 on the full dev16 x 2** (64 runs; kaggle/cells_skill_dev16a6, cell2 + cell4;
  EARLY_STOP_MAX -1 so pass 2 always runs, as mix solves only 3-4 of 16). Arm files verified identical to the submitted
  zips. Sim OK. Each at its submitted budget (a6 6 min/80 calls; pub024 8 min/28 calls). Next fresh set: train 52.
- **RESULT r42 (data/results/2026-11-03_skill_e24a6c):** a6rc 18 + 17 = **17.5 per 24** (mean 230 s, solved 199 s,
  14/48 at cap); a6c 17 + 17 = **17.0** (252 s, solved 212 s, 19/48 at cap); bar a6 17.0 (230 s). Within noise of a6.
  a6rc: 12942 2/2 (a6 0/2) but 15589 0/2; a6c: 15589 2/2. Malformed shell calls a6rc 5.9%, a6c 13.6% (a8 7.6, a8ra
  13.1, a8rc 11.3) -> the issue text in the prompt is NOT the cause; it varies run to run. Repeat block fires now
  (/tmp scan removed): a6rc 11 refusals in 7 runs, a6c 10 in 8 (12-13 unchanged repeats each). Checklist written on
  call 1 in 48/48 runs both arms, never refused. Pooled checklist effect over r38/r41/r42: +0.5 to +1 per 24, each
  within noise; fastapi_15589 checklist arms 6/8 vs plain 1/8 is the one clear signal.
- **RESULT r38 (6-min f6ra / f6rc, account 2, e24 x 2, results in data/results/2026-11-02_skill_e24f6r):** f6ra 16 + 14
  = 15.0 per 24 (240 s, 16/48 at the cap, 13 empty); f6rc 16 + 16 = 16.0 (252 s, 15/48 at cap, 12 empty). Per 24:
  sq1c2a8 19.0 (263 s, 8/48 at cap), sq1c2 18, pub024 14.5. The 6-min cap/window cost ~3-4 per 24 vs a8 (lost: 3278,
  4079, 3676, 14873, 12942 = late solves). rc solved fastapi_15589 in both passes (a8 0/2, sq1c2 0/1, pub024 1/2).
  Malformed shell calls rose: a8 7%, t7 8%, f6ra 11%, f6rc 20% (one rc run 27/34) -> the issue text at the end of the
  system prompt and/or the checklist may provoke the garble glitch (hypothesis). rich_3882 failed in both pass-2 runs
  (ra: 20 edit_file calls, edit loop). No freeze (0 zero-model runs) with the old clock.
- LB fit is about the CALL budget, not the 8-min cap: every 8-min submission that fitted had 28-32 calls (mix, pub024,
  sk_a2, sk_a2_32); sq1c2 / sq1c2t7 (80 calls) timed out. But our failing runs think long (median 22 calls in ~420 s,
  ~17 s/call): budget 50 would end 1/37 failing runs early (0 solves lost), 40: 5/37 (9/63 solves above), 28: 11/37
  (17/63). -> a call budget does not brake sq1c2; next = a progress-based stop for stuck runs, picked from the r38
  logs (what separates late solves from never-solves). User 2026-11-02: wait for r38's pass 2 + logs before building.
- **REBUILT with both fixes (cell2 + cell4):** kaggle/cells_skill_e24a8 (sq1c2a8, e24 x 2) and kaggle/cells_skill_e24a8r
  (sq1c2a8ra / rc, e24 x 2). The account-2 run of the OLD 6-min notebook (cells_skill_e24f6r) has the unfixed clock.
- **LB:** sk_a2 0.18, sk_a2_32 0.17, pub024 0.18 (our submission of the public 0.24 package, 2026-10-30) -> its 0.24
  was a lucky draw too. LB = ~58
  tasks: sd ~0.05; identical agents 0.12-0.26 -> never rank arms by LB. Final picks = best LOCAL arms.
- **What we know (2026-10-29):** all single agents (sk_a2, sk_a2_32, pub024, sk_fr2) are the same level: d40 ~17-18/40,
  e24 ~16.9/24; pub024 ~10% faster (fewer tokens/call, no a.py overhead). On d40: 13 tasks always solved, 16 never,
  11 sometimes; union over runs 24/40. Picker study (scripts/picker_offline.py, CPU notebooks test-signal +
  repro): best-of-3 with "drop patches that break existing tests" + "best repro score" -> ~20.3 vs 17.8 of 40.
  ADK 1.36.1 limits: ParallelAgent shares one session -> compaction crash (bo3: 11/24 crashed); agent_tool children
  get NO compaction (overflow risk for long children). The model ignores procedure rules (setup call, finish steps:
  sa2) but follows STRUCTURE (SequentialAgent hand-over 16-18/20) -> build mechanisms into structure / tool outputs.
  LB scorer runs tasks one at a time (host, forum 743063); Docker exec has no stdin (our local hang was an artifact,
  fixed in the cells). One tool call at a time per task (swegemma ctx.tool_lock).
- **Where things are:** arms scripts/make_skill_arms.py (sq2 / sa2 / bo3 / sk_fr2 / ...; `uv run python
  scripts/make_skill_arms.py ARM`); team scripts scripts/agent_team/{judge,setup}.py; cells
  scripts/train/make_skill_arms_cells.py (OUT, ARMS, TASKS = e24 / d40 / s20 / u20, PASSES, CONCURRENCY,
  PASS2_IF_BEATS) -> kaggle/cells_skill_*; sim data/sim/armsim.py (SIM_CELLS=...; run with `< <(sleep 400)` for a
  silent stdin); CPU notebooks kaggle/cells_testsignal, kaggle/cells_repro (private dataset
  ziad23samer/testsignal-candidates); results data/results/2026-10-29_*.

### RUN BUILT r38b: sq1c2a8ra vs sq1c2a8rc on e24, 2 passes (2026-11-02, second account; replaces r38)
- = r38's arms on the 8-minute base: run_finish2.py with CLOCK_A8R edits (SESSION 480, FINISH_AT None, no window
  text): event A + repeat block (+ CHECKLIST for rc); issue verbatim at the end of the system prompt; prompts
  rewritten for 8 min (724 / 766 words vs a8 848; finish from 400 s). Fake-clock test (rc): checklist refusal, repeat
  refusal, checklist shown at first edit, no refusal at 420 s. Sim: issue rendered, 8/8 patch, 8-min budgets.
- kaggle/cells_skill_e24a8r: ARMS [sq1c2a8ra, sq1c2a8rc], e24, 2 passes, 96 runs, ~4 h. Compare with r39 (a8).

### RUN BUILT r39: sq1c2a8 (sq1c2 8 min + event A only) on e24, 2 passes (2026-11-02)
- Event A alone (run_finish.py with CLOCK_A8 edits: SESSION 480, FINISH_AT None, no window text): repro prints
  FIXED with a source edit -> REPRO PASSES; 60 s later only finishing commands (edit_file still works). Warning 180,
  refusal 270 as sq1c2. No 300 s window, no 6-min cap. Prompt rewritten. Fake-clock test: no refusal at 420 s with an
  edit, A fires, 270 rule kept. Sim OK. dist/sq1c2a8.zip.
- Purpose: same accuracy as sq1c2, faster solved runs. NOT an LB candidate by itself (failing runs still go to 8 min;
  the scorer's 12-h total is set by them).
- kaggle/cells_skill_e24a8: ARMS [sq1c2a8], e24, 2 passes, 48 runs, ~2.3 h. cell2 only.
- Read: solves per pass vs sq1c2 18; mean s of solved runs vs sq1c2 (r31); A fired / what followed.

### RUN BUILT r38: sq1c2f6ra vs sq1c2f6rc on e24, 2 passes (2026-11-02, user's second account)
- Both = sq1c2f6 + idea 4 + idea 1a, new clock script scripts/agent_clock/run_finish2.py (f6's run_finish.py
  untouched): repeat block = identical command with an unchanged fingerprint (git status + git diff + files in
  .git/agent and /tmp, max 2000 files) -> REFUSED with the first 1500 chars of the earlier output (compaction may have
  dropped it). Issue verbatim at the END of the system prompt ("# THE ISSUE (verbatim ...)" + {problem_description});
  prompts rewritten tighter (684 / 723 words vs f6 855) to offset the ~235 issue tokens.
- sq1c2f6rc adds 1b+1c (CHECKLIST = True): commands refused until write_file .git/agent/issue.md exists (<= 8 lines
  of exact names/strings/values + expected behaviour); the clock appends "[issue checklist]" with the file after the
  first source edit and again when the repro passes / the finish window opens.
- Fake-clock unit tests: repeat refused and re-shown, runs again after an edit; checklist refusal, shown at first
  edit, not repeated, shown at REPRO PASSES. Sim (SIM_CELLS=cells_skill_e24f6r; armsim now writes the checklist when
  the prompt asks and checks the issue is rendered): issue in system prompt True, 8/8 runs patch.
- kaggle/cells_skill_e24f6r: ARMS [sq1c2f6ra, sq1c2f6rc], e24, 2 passes, 96 runs, ~3.5-4 h. Same budgets -> cell2 only.
- Read vs sq1c2f6 (r37) and sq1c2 8-min (e24 18): solves per pass; repeat refusals (count, what followed); rc: the
  checklist's quality (exact literals vs issue), literals in final patches; compactions per run and when; mean s.

### PATTERNS: what the model obeys, and what compaction drops (2026-11-02, from r31-r35 logs, 124 clock runs)
- COMPACTION KEEPS THE SYSTEM PROMPT, DROPS THE TASK MESSAGE: after ADK compaction (google/adk/apps/
  llm_event_summarizer.py) the request = system prompt (re-sent every call, identical) + "For context: [model] said:
  <summary>" + the last events. The harness task message (problem statement + workspace listing) is gone; only 17%
  (394/2292) of the issue's exact `code` / "quoted" strings are still in context after the first compaction.
  Compaction is frequent and early: 216 summarizer calls in 148 runs, first one at median 152 s (~14k tokens).
  Same task, compaction before the first edit: 77% solved vs 90% otherwise (12 tasks; small, partly difficulty).
  The fixer prompt has no {problem_description}, so the exact issue text is lost for the rest of the run.
- COMPACTION BUDGET (cell4 / HARNESS_README: token_threshold 14,336 on the server's real prompt_token_count, keep last
  5 events): fixer first call ~4,700 tokens (system ~1,500 + tools + task message) -> headroom ~9,600; first call
  after a compaction ~5,900 (system + summary + 5 events) -> headroom ~8,400; 1.32 compactions per run.
  {problem_description} = task.problem_statement only (agent_runner.py L393): ~235 tokens median, p90 ~610, max ~890
  -> in the system prompt it permanently costs ~2.5-3% of headroom (p90 ~7%); offset by trimming ~250 tokens of
  prompt. Session state also gets 'hints' when a task has hints_text: 0 of 129 public tasks do.
- User 2026-11-02: drop idea 2 (test-file block: 0/106 final patches had test/scratch files); keep idea 4 (repeat
  block: 256 identical repeats in 124 runs, 35 runs >= 3; refuse only if no file changed since); idea 1 (issue
  survives compaction: (a) {problem_description} in system prompt, (b) short checklist file forced by a block,
  (c) clock shows it at first edit / finish) still being planned; idea 3 (delay compaction) parked.
- PROHIBITIONS HOLD, BUT ERODE LATE: tool/format bans (graph tools, args parameter, test files, whole test suites)
  broken in 0/620 calls at turns 1-5, 4/1175 at 6-15, 16/1736 at 16+ (test-file edits: 0, 3, 15).
- SOFT TEXT IN A TOOL OUTPUT IS MOSTLY IGNORED; A BLOCK WORKS: the clock's "NO SOURCE EDIT YET" warning was followed
  by an edit within 2 calls in 15/67 runs (never: 20); the REFUSAL was followed by an edit next call in 5/7 (r31)
  and 6/8 (r30). Timing/procedure rules in the prompt (edit by 180 s) are not followed at all (67 runs unedited).
- Literature: attention to the system prompt decays over a dialog ("instruction drift", Li et al. 2024,
  arXiv 2402.10962; baseline fix = repeat the system prompt before each turn); Gemma 3/4 attention = 5 local (1024-
  token window) : 1 global, so far-back text is reached only by the global layers (arXiv 2503.19786); multi-turn
  unreliability, early assumptions anchor (Laban et al. 2025, arXiv 2505.06120). Our sliding-window explanation is a
  hypothesis, not tested.

### RUN BUILT r37: sq1c2 (8 min) vs sq1c2f6 on e24, 2 passes (2026-11-02)
- Time analysis (r31, r34, r35; 88 runs): 96% of agent time is model calls; solved runs spent ~100-120 s after the
  repro first printed FIXED (15 of 48 edited again after it); 16/21 failed runs on d40 hit the wall. LB 0.18 = ~80%
  failures -> on the scorer most runs hit the cap: est. 7 min 12.9 h (timed out), 6 min ~11.6 h (too tight).
- sq1c2f6 = sq1c2 for the first 270 s (warning 180, refusal 270), plus finish events in a new clock script
  scripts/agent_clock/run_finish.py: event A = a command prints a line starting FIXED with a source edit -> clock
  says REPRO PASSES (one test file, then finish), 60 s later only finishing commands run (git status / diff /
  checkout -- / rm; chained other commands refused); event B = from 300 s with a source edit the same. edit_file
  still works. Cap max_time_minutes 6 (safety net). Prompt rewritten (repro prints FIXED on its own line only when
  fixed). State in .git/agent/clock.json. Unit-tested with a fake clock (all events); sq1c2's run.py untouched.
- kaggle/cells_skill_e24f6: ARMS [sq1c2f6] (user: sq1c2 already measured), e24, PASSES 2, early stop 3. Only cell2
  needed (single arm; the folder's cell4 = r35's relaxed guard, either works). 48 runs, ~2 h wall. Sim OK.
- Read: solves per pass per arm (bar: sq1c2 >= its 18 history); mean agent s and share at the cap; how often events
  A/B fired and what followed (edits after FIXED, refusals in the finish window); projected LB hours for f6.

### RUN BUILT r36: sq1c2t6 (6-minute sq1c2) alone on d40 (2026-11-02)
- User: sq1c2t7 also timed out on the scorer; go 6 min (as le6_t6, which fitted), test locally first. sq1c2t6 =
  sq1c2 with times x 6/8: max_time_minutes 6, clock SESSION 360, warning 135 s, refusal 200 s; prompt rewritten
  (locate by ~75 s, edit by 135 s, test file only under 240 s, pytest timeout 90, finish from 300 s). 80 calls kept
  (a 40-call cap would have cut 9 of sq1c2's 63 solves in r31-r35). dist/sq1c2t6.zip (pack OK).
- kaggle/cells_skill_d40t6: ARMS [sq1c2t6], D40, 1 pass, ~2 h; cell2's arm check accepts 8/7/6 min (cell4 carries
  r35's relaxed guard; a single arm passes either version). Sim: clock "s of 360", budgets 6 min.
- In r31-r35, 52 of 100 sq1c2/t7 runs ran >= 355 s (21 of them solved) -> expect some loss vs t7 (19/40).
- Read: solved vs t7 19/40 and pub024 ~17; share of runs at the 360 s wall (the scorer-fit risk); mean s.

### RESULT r35: sq1c2t7 18/24 vs pub024 15/24 on e24, same run (2026-10-31)
- data/results/2026-10-31_skill_e24t7, 48 runs, no crash. sq1c2t7 18/24, no patch 3, mean 274 s, 4 time ends |
  pub024 15/24, no patch 6, mean 282 s, 3 time ends. Same-run differ: t7 only 12942, 14372, 14419, 15589, 3278, 4075;
  pub024 only 11194, 14873, 3521.
- All runs on e24: pub024 15, 14 (r25), 20 (r23+r24 stitched, lucky s20) -> mean 16.3; sq1c2t7 18, 17 (r34) ->
  17.5; sq1c2 8-min 18 (r31). q12 fresh: pub024 10/24 vs sq1c2 14/24. Head-to-head in the same notebook: +3.
  -> sq1c2t7 is modestly but consistently ahead of pub024 (about +1-3 per 24) and not slower: submit it
  (dist/submission.zip = dist/sq1c2t7.zip).

### RUN BUILT r35: pub024 vs sq1c2t7 on e24, 1 pass (2026-10-31)
- User: run both once more on the solvable tasks and compare. kaggle/cells_skill_e24t7: ARMS [pub024, sq1c2t7],
  e24 (same 24 as r25 / r31), 1 pass, concurrency 2 -> 48 runs, ~2.3 h.
- cell2 AND cell4 differ from the sq2 notebook: cell4's guard allowed arms to differ only in max_tool_calls; now also
  max_time_minutes / max_turns (pub024 8 min / 80 turns, sq1c2t7 7 min / 400). Budgets were already applied per arm
  (Evaluator(**EVAL_CFGS[arm])); printed output unchanged. Sim: budgets per arm OK; pub024's "run_skill_script not
  found" in the sim is the fake model's artifact (same in the e24x2 sim; pub024 ran fine on Kaggle r25, r33).
- Earlier on e24: pub024 14 (r25), sq1c2 8-min 18 (r31), sq1c2t7 17 (inside r34). Read: solves, per-task, mean s.

### RESULT r34: sq1c2t7 19/40 on d40, 325 s/task (2026-10-31)
- data/results/2026-10-31_skill_d40t7, 40 runs, no crash. sq1c2t7 19/40 (dev 3/8, val 7/16, test 9/16), no patch 8,
  mean 325 s, 16 time ends | pub024 (s20 + u20 runs) 20/40 (4, 7, 9), no patch 8, 340 s, 8 time ends | sk_a2 17/40,
  272 s. Differ: t7 only 14349, 3063, 3470; pub024 only 14419, 15589, 3278, 4075.
- Subsets: e24 17 (sq1c2 8-min r31 18, pub024 r25 14); q12 5 (sq1c2 6, 6, 8; pub024 3, 4, 6); the 16 tasks no arm
  had solved: 2 (rich_3470, rich_3063). The 7-min cut saved little time on e24 (300 vs 309 s) and cost ~1 task.
- CORRECTION (user, 2026-10-31): pub024's "20/40" is NOT one run: it is two runs stitched (s20 r23 18/20 + u20 r24
  2/20). On the same 20 s20 tasks pub024 scored 14 in e24x2 (r25) -> r23's 18 was a lucky draw. pub024's per-task
  solve rate over all its runs (s20, u20, e24x2, b, p12) gives ~17.0 per d40 pass. sq1c2t7: s20 16, u20 3 = 19.
  So sq1c2t7 19 vs pub024 ~17 expected (single runs swing +-2-3).
- Verdict: at least equal to pub024 on the broad set, ahead on the medium q12/e24 tasks over all runs, and
  faster than pub024 (325 vs 340 s, pub024 fitted the 12-h scorer) -> submittable. dist/submission.zip =
  dist/sq1c2t7.zip (same files as this run).

### RUN BUILT r34: sq1c2t7 (7-minute sq1c2) alone on d40 (2026-10-30)
- sq1c2t7 = sq1c2 with every time scaled by 7/8: max_time_minutes 7, clock SESSION 420, warning 160 s, refusal
  240 s; fixer prompt rewritten with those times (locate by ~100 s, edit by 160 s, finish from 350 s, pytest timeout
  120). Everything else = sq1c2. dist/sq1c2t7.zip (pack OK).
- kaggle/cells_skill_d40t7: ARMS [sq1c2t7], TASKS D40 (= s20 + u20, where pub024 got 18 + 2 = 20/40 in two separate runs, at 270 / 411 s,
  ~340 s mean), 1 pass, concurrency 2, ~2.2 h. Only cell2 differs from the sq2 notebook (its arm check now accepts
  max_time_minutes 7). Sim: clock "s of 420", budgets max_time_minutes 7.
- Read it: solved vs pub024 20/40 (s20 18, u20 2); mean agent s (must be well under ~340 s to submit); runs hitting
  the 420 s wall; no-patch count; refusals. If score >= pub024 and time <= ~330 s -> submit dist/sq1c2t7.zip.

### RESULT r33: pub024 4/12 + 6/12 on q12 (2026-10-30)
- data/results/2026-10-30_skill_p12, 24 runs, ~1.5 h. pub024 10/24 (42%) vs sq1c2 14/24 (58%: r31 6, r32 8) on
  the same 12, all runs made after the pick. Per task pub024 / sq1c2: 11194 nn/YY, 12942 nY/nY, 14349 nY/YY, 14419
  Yn/nn, 14873 YY/YY, 15589 Yn/nY, 3278 nY/YY, 3506 nY/nY, 3521 nY/nn, 3676 nn/YY, 4075 nn/nn, 4079 Yn/Yn.
  sq1c2 ahead on 4 tasks (+6 runs), pub024 on 2 (+2): suggestive, not proven (~1.2 se). Clock family (sq1c, sq1c2,
  sq1c3, sq1c4) on q12: 34/60 = 57%.
- No patch 5 each. Time: pub024 366 s, sq1c2 423 s (+16%; e24 +8%); 8-min wall hit pub024 8/24, sq1c2 14/24.
  -> sq1c2 at 8 min is likely too slow for the 12-h scorer (pub024 ~340 s on d40 fitted; sq1c2 ~370-395 s est.).

### RUN BUILT r33: pub024 x 2 passes on q12 (2026-10-30)
- User: fresh pub024 control on the same 12 tasks. kaggle/cells_skill_p12: ARMS [pub024], Q12, PASSES 2,
  EARLY_STOP_MAX -1 (off for this run: pub024's earlier q12 score was 3 = would stop). Only cell2 differs. 24 runs.
- Why fresh runs: q12 was picked AFTER earlier runs failed these tasks (pub024 counted 12/29 there, 41%), so the old
  pub024 numbers are biased low; sq1c2 has 14/24 (58%) in runs made after the pick.
- LB time risk of sq1c2 (dist/submission.zip = dist/sq1c2.zip, same files as r32's run): the scorer runs ~116+ tasks
  in 12 h (mix: 346 s dev mean fitted; le5 347 s on dev16 timed out). pub024 fitted on the LB; its d40 mean ~340 s
  (s20 270 + u20 411); sq1c2 is ~8% slower than pub024 on e24 (309 vs 287) -> ~367 s estimated -> over the edge.

### RESULT r32: sq1c2 8/12, sq1c3 7/12, sq1c4 7/12 on q12 (2026-10-30)
- data/results/2026-10-30_skill_c36, 36 runs, 2.4 h, no crash. Per task (sq1c2/sq1c3/sq1c4): 11194 YYY, 12942 YYY,
  14349 YYY, 14419 nnn, 14873 YYY, 15589 YYY, 3278 YYn, 3506 YYn, 3521 nnn, 3676 YnY, 4075 nnn, 4079 nnY.
- | arm | solved | no patch | mean s | calls >60 s | runs refused | read_file | edit_file failed | garbled shell |
  | sq1c2 | 8 | 2 | 414 | 13 | 7 | 115 (15 after a refusal) | 1/32 (3%) | 13/166 |
  | sq1c3 | 7 | 2 | 459 | 16 | 8 | 0 | 7/28 (25%) | 24/334 |
  | sq1c4 | 7 | 0 | 438 | 18 | 6 | 163 (10 after) | 3/32 (9%) | 17/207 |
- sq1c3: the prompt worked (0 read_file calls) and after every refusal the next calls led to an edit, BUT reading
  through the shell made edits fail (old_string copied from sed output inside a JSON string: 25% vs 3%). Both
  no-patch runs (3521, 4075) were a deadlock: refused -> cannot read -> edit_file "old_string not found" repeatedly.
  Slower (459 s). -> reading must stay with read_file.
- sq1c4: thinking capped (max reasoning ~7.7k chars vs up to 18k), no-patch 0, but calls > 60 s did not drop
  (18 vs 13) and solves did not rise -> long calls are not only thinking; 2048 is not the lever here.
- Control sq1c2 8/12 (r31 6/12 on the same tasks): run-to-run noise on q12 is about +-2.
- Next: sq1c2 = best local agent (q12 6, 6, 8; e24 18). Candidate for the next LB submission; further arms only
  with a mechanism aimed at the remaining always-fail tasks (14419, 3521, 4075: wrong or no patch in all arms).

### RUN BUILT r32: sq1c2 (control) vs sq1c3 vs sq1c4 on q12 (2026-10-30)
- User: "try both arms". sq1c3 = sq1c2 with all reading through the clock shell (prompt rewritten: sed -n through
  run.py, "Do not use read_file"; read_file stays declared because an undeclared call drops the patch; the refusal
  adds "Every command, reading included, runs again once a source file is edited; do not read with read_file
  either"). sq1c4 = sq1c2 with thinking_budget 2048 (only change). sq1c2 unchanged = control.
- kaggle/cells_skill_c36: ARMS [sq1c2, sq1c3, sq1c4], TASKS Q12, 1 pass, concurrency 2 -> 36 runs, ~2.5 h wall
  (~5 h quota). Only cell2 differs from the sq2 notebook. Sim (SIM_CELLS=cells_skill_c36): 6/6 runs patch, clock
  line in outputs, requests carry thinking_token_budget 4096 (sq1c2, sq1c3) / 2048 (sq1c4); sq1c3 refusal text checked.
- Read it: solves per arm (q12 history: sq1c 6, sq1c2 6 in r31); no-patch count; read_file calls in sq1c3 (after a
  refusal especially); model calls > 60 s and mean s/task in sq1c4; garbled calls.

### RESULT r31: sq1c2 18/24 on e24 (2026-10-30)
- data/results/2026-10-30_skill_c24, one notebook, 24 runs, 1.09 h, no crash. 18/24 vs sq2 (r28) 19/24 on the same
  24: gain rich_4079, losses fastapi_15589 and rich_3521 (both no patch, both solved by sq2 at 480/367 s); every
  other task the same outcome. Single runs, sd ~2.2 -> equal. q12 subset 6/12 (sq1c r30 6, sq1 4/3, sq2 4/7).
- No patch 3 (12942, 15589, 3521) vs sq2 5; wrong patches 3 (14419, 3506, 4075; sq2 had none there). Faster: mean
  309 s vs 365 s; 12 tasks first-edited before 120 s, all solved.
- Call shape: run_skill_script 334 calls, 307 well-formed, 27 garbled (8%; r30 76%): 11 lacked skill_name (often
  the FIRST call of a run), 16 had the command swallowed into a key ('<|"|>],skill_name'). Each cost one call
  (the model resent it correctly after INVALID_ARGUMENTS).
- REFUSED fired in 7 runs; next call edit_file/write_file in 5 (11194 Y, 3278 Y, 4079 Y, 14419 wrong, 3506 wrong);
  in 2 the fixer switched to read_file and never edited (12942, 15589: repro printed "FIXED" before any edit, the
  model kept reading). read_file is not behind the clock -> it is the escape route.
- rich_3521: only 9 tool calls; two model calls took 131 s and 109 s (thinking 10.9k / 9.7k chars, ~4k tokens each;
  thinking_budget 4096) -> 345 s gone with no edit, compaction, time-out. No refusal (no shell call after 270 s).
  Every failed run except 4075 had a model call > 60 s; of the 17 runs with none, 16 solved.
- Next candidates (not built): (1) reads behind the clock: drop read_file from the fixer, read through run.py
  (sed -n / cat), so REFUSED covers everything but edits; (2) lower thinking_budget (4096 -> 2048) to cut the
  >60 s calls; risk: shallower reasoning on hard tasks. Measure one at a time on q12.

### RUN BUILT r31: sq1c2 alone on e24 (2026-10-30)
- sq1c2 = sq1c with the shell call reshaped: run_skill_script skill_name work, file_path scripts/run.py,
  positional_args = [one string, the whole command]; "Do not use the args parameter"; plus a line: a "required"
  argument error = malformed call, resend it written out plainly, never the same broken call twice. Same run.py,
  everything else = sq1c. scripts/make_skill_arms.py sq1c2 (CLOCK_VARIANT); pack OK.
- kaggle/cells_skill_c24: ARMS ["sq1c2"], TASKS e24 (same 24 as r28 sq2 19/24). Sim (SIM_CELLS=cells_skill_c24):
  positional_args reached run.py, clock line in each output.
- Read it: (1) garbled run_skill_script calls (r30: 76%); (2) the 12 easy e24 tasks still solved (clock must not hurt
  them); (3) solves vs sq2 19/24 (r28) and q12 history; no-patch count; refusals and what followed.

### RESULT r30: sq1c (clock) 6/12 vs sq1 4/12 on q12 (2026-10-30)
- data/results/2026-10-30_skill_c12, one notebook, 24 runs, no crash, no undeclared-tool call (no run_command).
- sq1c 6/12, no patch 2 (14419, 4075), mean 461 s; sq1 4/12, no patch 6, mean 423 s. Earlier on q12: sq1 3 (7 no
  patch), sq2 4 (7) and 7 (5). Per task sq1c / sq1: 11194 Y/Y, 12942 Y/Y, 14349 Y/Y, 14419 -/-, 14873 -/-, 15589 -/-,
  3278 -/-, 3506 Y/-, 3521 -/-, 3676 Y/-, 4075 -/-, 4079 Y/Y.
- Clock events (all requests scanned): warning in 9/12 runs (187-393 s), REFUSED in 8/12 (271-456 s); after a refusal
  an edit followed in 6 (11194 313->359 solved, 3506 279->396 solved, 4079 277->edit solved, 15589, 14873, 11194),
  none in 14419 (refused at 393) and 4075 (328).
- BUG: 259/343 run_skill_script calls garbled: {"args": {"cmd": ...}, "file_path": "scripts/run.py`,skill_name:"}.
  Over all runs: run_skill_script WITHOUT args 0/698 garbled, WITH args (nested object first) 256/341; the same
  backtick glitch after a path value: edit_file 11.4%, write_file 3.4%, read_file 1.0%, run_command 0/17,699 (one
  argument). The fixer repeated the same broken call up to 59 times (12942) -> lost time.
- Next: a call shape without the nested object before file_path. ADK sorts nothing; the model writes keys
  alphabetically (args < file_path < skill_name). positional_args (an array) sorts AFTER file_path, so file_path is
  written before any nesting; run.py already accepts positional args.

### RUN BUILT r30: sq1c (clock shell) vs sq1 on q12, 4 shards (2026-10-30)
- sq1c = sq1 whose fixer has NO run_command: its shell is skills/work scripts/run.py (scripts/agent_clock/run.py)
  via run_skill_script args cmd. Every output ends "[clock] N s of 480 used | source edited: FILES / no source edit
  yet"; no edit at 180 s -> "NO SOURCE EDIT YET ... make your best edit now"; at 270 s -> REFUSED until a source file
  is edited (edit commands pass). Clock = git log _swegemma_baseline (tagged at sandbox start; sim shows 0 s at start).
  Output cut at 5000 chars, timeout min(150, left - 10), stdin DEVNULL. Fixer prompt rewritten (time plan by the clock
  instead of call numbers); read_file kept (the harness task message names it). Risk: a hallucinated run_command =
  undeclared tool = patch lost (0 undeclared calls in 25,578 earlier calls, but run_command was always declared).
- Cells: ARMS ["sq1c", "sq1"], one notebook (user: one account), SHARDS None, STOP_H None (10.5). cell3b digest unchanged (run.py calls count as 'install'); read clock
  warnings / refusals from requests.jsonl. Sim (SIM_CELLS=cells_skill_c12_s1, armsim role fixer_c): run.py found the
  workspace, clock line in each output, git apply through the shell counted as the edit.
- Read it: no-patch runs (r29: sq1 7/12, sq2 7/12) and solves; refusals and what the fixer did right after; crashes.

### ANALYSIS: why runs end with no patch (2026-10-29, 804 skill-arm runs 10-25 -> 10-29 with requests.jsonl)
- 291 solved, 313 wrong patch, 200 NO patch. No patch: 113 never tried an edit (95 ended at the time limit, median 23
  calls of reading); 66 had their edit REFUSED because max_tool_calls was used up (28/32-call arms: pub024 8, sk_a2_32
  8, ...) even though the harness warns at <= 10 calls left ("Finalize your edits") -> that warning does NOT force an
  edit; 72 edit attempts were refused/failed in total, malformed calls (missing filepath) are as common in solved runs.
- First edit: solved median 156 s (call 14), wrong 266 s (call 20). Solve rate by first-edit time: < 120 s 76%,
  120-180 51%, 180-240 34%, > 240 s 22-32%. Same task (19 tasks with both kinds): early (<= 240 s) 59% vs late/no
  edit 47% -> part of the gap is NOT task difficulty.
- Thinking budget is not the cause: tokens per reply are similar for no-patch and solved runs at 1024/2048/4096;
  no-patch runs just keep reading (~12 s per call).
- Harness: the only built-in warning is call-based (swegemma tools/base.py _attach_low_budget_warning, <= 10 left);
  no time warning. run_skill_script accepts args (ADK skill_toolset.py script_args) -> a script of ours can wrap
  commands and print a clock / refuse reads when the tree is still unedited late (idea, not built).

### RESULT r29: sq1 vs sq2 on q12 (2026-10-29)
- data/results/2026-10-29_skill_q12_s1..s4 (s1-s3 from results.zip, s4 via kernels output fatmazenhom/generation-
  shard-4-gpu). Each shard ~32 min wall, no crash, no time-guard skips.
- Per task (sq1 / sq2 / r28 sq2): 12942 - / Y / - | 14349 - / - / Y | 4075 - / - / - | 11194 Y / Y / Y | 14419 - / - / - |
  3521 - / - / Y | 14873 Y / Y / Y | 3278 Y / - / Y | 4079 - / - / - | 15589 - / - / Y | 3506 - / Y / - | 3676 - / - / Y.
- sq1 3/12 mean 444 s, no patch 7 (6 at the limit), wrong 2; sq2 4/12 mean 457 s, no patch 7 (all at the limit), wrong 1.
- Second attempt: never ran (sq2's finisher reached in 3 runs, each SUBMIT NOW at 335-420 s). sq1's 14349 = the one
  case it was built for (fixer handed over an EMPTY tree at 124 s, sq1 submitted it).
- New failure: sq2 14349 called write_file 7x in a row without filepath (same error each time) until time ran out.
- Model speed same as r28 (~11-15k output tokens per 8 min); few tool calls = long thinking per call.
- Verdict: every single-fixer design is the same level; on hard tasks luck dominates (sq2 itself 7 -> 4). The loss
  is no-edit timeouts.

### RUN BUILT r29: sq1 vs sq2 on q12, 4 shards (2026-10-29)
- sq1 (user) = sq2 without the second attempt: same fixer prompt / tools / budgets (80 calls, 400 turns), the finisher
  (include_contents none, 48 words) only calls submit_patch. scripts/make_skill_arms.py sq1 (sq2() with second=False);
  pack OK. Question: is sq2's 19/24 the structure (fixer -> fresh finisher) or the second attempt?
- q12 = the 12 e24 tasks NOT solved in >= 8 of 9 earlier runs (the other 12 are solved by every arm): before on q12 ->
  pub024 3, sk_a2_32 3, sa2 6, sq2 7 (r28). Shards (snake by r28 time): s1 fastapi_12942 fastapi_14349 rich_4075 | s2
  fastapi_11194 fastapi_14419 rich_3521 | s3 fastapi_14873 rich_3278 rich_4079 | s4 fastapi_15589 rich_3506 rich_3676.
- Builder: make_skill_arms_cells.py SHARDS (list of task lists -> OUT_s1..) and STOP_H (None = 10.5). Timing: setup
  ~10 min (vLLM up at 594 s in r28), these tasks ~430 s each -> 3 rounds of 2 = ~22 min -> ~34 min wall (~1.1 h quota).
- Sim (SIM_CELLS=cells_skill_q12_s1, armsim role 'submitter'): sq1 14786 submits the fixer's wrong edit, sq2 next.py
  -> second_fixer -> pick.py WINNER B (gold); 15588 gold both. Local resolved=False as always (uv venv, no pip).
- Read it: combine the 4 outputs; sq1 vs sq2 solves and mean time on q12 (the other 12 count as solved for both).

### RESULT r28: sq2 on e24 19/24 (2026-10-29)
- data/results/2026-10-29_skill_sq2 (concurrency 2). 19/24, mean 365 s (pub024 287, sk_a2_32 322), 9 tasks hit 480 s,
  0 crashes. Lost: fastapi_12942 (5/9 before), fastapi_14419 (10/49), rich_3506 (2/9), rich_4075 (2/9),
  rich_4079 (10/49). Notable wins: rich_3676 (1/9 before), fastapi_15589 (19/49), rich_3521 (14/49).
- Structure worked: the fixer handed over in 23/24 (only rich_3518 self-submitted); the finisher ran next.py in
  every task that reached it (17); 7 tasks ended at the limit before the finisher (patch kept by the fallback
  capture; 3 of them solved).
- Second attempt: SECOND ATTEMPT in 11, SUBMIT NOW in 6. pick.py ran in 8 (A won 7: same or tied repro scores;
  B won fastapi_14492 because A broke 1 existing test there, but 14492 is 9/9 before -> no outcome change).
  12942: A made no patch, B started at 188 s and ran out of time. 14301: B still editing at 480 s, A's patch kept,
  solved. -> the second attempt added 0 solves here; it costs time (mean +80 s vs pub024).
- Reading: 19 vs fair 14/15/18 is promising, not proven. The candidate cause is the fixer prompt + no-submit hand-over
  (sa2's lead had a similar prompt: 18).

### RESULT r27 (bo3 + sa2 on e24, concurrency 1, 3.85 h) and RUN BUILT: sq2 (2026-10-29)
- data/results/2026-10-29_skill_bo3_sa2. bo3 13/24, mean 251 s, 11/24 ended 'sandbox' = the ParallelAgent compaction
  crash (patch dropped); judge picked A in 9 (all solved). -> ParallelAgent is out.
- sa2 18/24, mean 306 s, 5 time ends: the lead NEVER ran its setup call (0/24, went straight to git grep) and ran
  judge.py next in only 5/24, submitting directly in the rest -> no second attempt ever ran; 18 = a single agent
  with the new prompt (single-agent e24 readings 14-20, mean 16.9).
- sq2 = the same idea by structure: SequentialAgent [fixer (pub024 procedure, repro_a.py, never submits, ends with a
  plain-text line), finisher (include_contents none; run_skill_script team scripts/next.py -> SECOND ATTEMPT ->
  second_fixer agent_tool -> scripts/pick.py -> submit_patch)]. next.py / pick.py = judge.py with MODE "next" /
  "pick" as skill scripts (no setup to forget): next.py copies itself to .git/agent/judge.py (for the second
  fixer's 'done b'), makes wt_0 / wt_b, start time = git log -1 _swegemma_baseline (tagged at sandbox start); a
  second attempt when < 240 s used (300 s if the first made no patch).
- Sim: 14786 fixer wrong edit -> next.py SECOND ATTEMPT -> second_fixer (max_tokens 4096) gold in wt_b -> pick.py
  WINNER B -> patch = gold; 15588 -> A. pack.py OK.
- kaggle/cells_skill_sq2 (only cell2 differs from bo3_sa2): sq2 alone on e24, 1 pass, CONCURRENCY 2 (as the single-
  agent e24 readings), ~1.6 h wall / ~3.2 h quota.

### RUN BUILT: bo3 (budget 300) + sa2 on e24, 1 pass, concurrency 1 (2026-10-29, NEWEST — read first)
- User: bo3 had 6/8 solved when stopped -> rerun it, with max_tool_calls 300 / max_turns 400 (100 ran out from judge
  polling); the ParallelAgent compaction crash stays (to measure). Plus option 2 = sa2.
- sa2 (scripts/make_skill_arms.py sa2): one pub024-style lead (normal session + compaction) fixes in /workspace,
  writes .git/agent/repro_a.py, runs judge.py next: under SECOND_BEFORE = 240 s after setup -> SECOND ATTEMPT = the
  agent_tool second_fixer (fresh session, no compaction: told 10 calls, max_output 4096 / thinking 2048 so its whole
  history stays far under 32k) in the git worktree wt_b (made by setup_lead.py), repro_b.py, judge.py done b; then
  judge.py --no-wait keeps the better patch; else SUBMIT NOW. If time runs out, /workspace holds the first patch.
  max_tool_calls 80, max_turns 400 (the notebook needs equal budgets except calls).
- Sim (SIM_CELLS=cells_skill_bo3_sa2): sa2 14786: lead wrong edit -> SECOND ATTEMPT -> second fixer (max_tokens
  4096) applies the gold in wt_b -> WINNER B -> patch = gold; NO_EDIT -> WINNER A. bo3 as before. pack.py OK for both.
- kaggle/cells_skill_bo3_sa2: only cell2 differs from cells_skill_bo3. 48 runs x ~400 s at concurrency 1 =
  ~5.5 h wall / ~11 h quota -> set STOP_NEW_TASKS_AFTER_H = quota/2 - 0.4 (tasks alternate arms).

### RESULT bo3 (stopped by the user after 4 tasks) + why parallel attempts break in ADK 1.36.1 (2026-10-29)
- First 4 tasks (concurrency 1): rich_3278 S (judge A, 453 s, 20 s/model call, 5 compactions); fastapi_9555 CRASH
  "ValueError: No function call event found for function responses ids" (contents.py
  _rearrange_events_for_latest_function_response) -> exception -> patch dropped; rich_3067 S but tools 100/100 (A
  polled the judge 30x, no WINNER); fastapi_14372 S but tools 100/100, setup at call 44, 9 compactions.
- ParallelAgent = ONE shared session: compaction (harness EventsCompactionConfig, token_threshold 14,336) summarises
  events of all branches and can separate a tool call from its response across branches -> the crash. Not ours to
  turn off.
- AgentTool fixers get their own session but NO compaction (google/adk/tools/agent_tool.py: child Runner(...,
  InMemorySessionService()), no App/compaction config). pub024 uncompacted peak (prompt + reply, rebuilt from the 24
  e24 requests logs): median 22.9k, p75 28.6k, max 38.4k vs max_model_len 32,768 incl. max_output (8192) -> 9/24 runs
  would overflow (5/24 with max_output 4096) -> error -> patch dropped.
- Options given to the user: (1) agent-tool fixers capped ~14 calls; (2) sequential second attempt in a fresh git
  copy when the first finishes early, judge picks (no parallel ADK features); (3) single agent + judge-style self
  check. Recommended (2).

### STDIN HANG = a LOCAL artifact; fixed in the notebook, not in the agent (2026-10-29)
- Cause: our notebooks use the harness's subprocess sandbox (no Docker on Kaggle); adk_eval_core
  sandbox/subprocess_sandbox.py starts commands with subprocess.Popen and no stdin -> they inherit the notebook's open,
  silent stdin -> input() (rich_3882's Prompt.ask) waits to the 240 s timeout (r18 sk_a2b, r25 sk_a2_32).
- The LB runs agent commands in Docker (rules page: "the competition's persistent Docker container"); swegemma
  sandbox/docker.py exec uses container.exec_run without stdin -> input() gets EOF at once: no hang on the LB.
- First fix (commit 6797663) put a stdin guard into the sandbox venv from the skill setup scripts: REVERTED. The
  scorer reuses Docker containers between tasks (HARNESS_README "warm pooling"), so an agent writing into the
  container's site-packages could reach grading = the "tampers with the submission process" rule. Agents must not
  modify the environment outside /workspace.
- Fix now: the cells (make_skill_arms_cells.py, next to ood.patch_harness()) wrap the subprocess module of
  adk_eval_core's subprocess sandbox so Popen defaults to stdin=DEVNULL = the LB's behaviour. Sim with a silent
  stdin: "EOF after 0.0 s". All future skill-arm notebooks get it; the bo3 run started before it does not.

### RESULT r25: e24 pass 1 = pub024 14/24 (287 s), sk_a2_32 15/24 (322 s); pass 2 skipped (2026-10-29, NEWEST)
- data/results/2026-10-29_skill_e24x2, 2.15 h, concurrency 2. Only 5 of 24 differ (pub: 11194, 3521; a2_32: 14372,
  15589, 3278). Readings on these 24: pub024 20 (r23+r24) and 14 -> 17.0; sk_a2_32 18 (r21+r24) and 15 -> 16.5.
  -> No real difference; pub024's earlier +2 was noise. The same agent scores 14-20 on the same 24 tasks.
- For bo3 (1 pass on e24): a single-agent run is ~16.5-17 here with a spread of about +-3; bo3 needs ~20+ to mean
  something, and a second pass to be sure.

### RUN BUILT: bo3 = best of three (2026-10-29)
- submissions/bo3 (scripts/make_skill_arms.py team()): root ParallelAgent [fix_a, fix_b, fix_c], pub024 recipe
  (tools incl. graph tools, sampling 0.2 / 0.95 / thinking 4096), prompts written fresh around pub024's procedure;
  each fixer told 18 calls, edit by call 10, writes .git/agent/repro_<x>.py (exit != 0 while the bug is there).
  Fixer A works in /workspace; B / C in git worktrees .git/agent/wt_b / wt_c (skill team, scripts/setup_<x>.py: the
  three made at the same moment without conflicts). B / C finish with judge.py done <x>; A finishes with judge.py
  (scripts/agent_team/judge.py) and submit_patch. eval_config: max_tool_calls 100, max_turns 240, 8 min.
- Judge rules: non-empty source patch; drop patches that make more existing tests (<= 3 files importing the changed
  modules, 60 s) fail than wt_0 (clean copy) does; best repro score (all fixers' scripts, 20 s each, no patch vs
  candidate); ties -> A, then the smaller. Winner applied to /workspace (A's patch restored if apply fails).
- HARNESS FACT: swegemma runs ONE tool call at a time per task (ctx.tool_lock, tools/base.py budget_gated); model
  calls stay parallel. So the judge never waits inside a call: it answers WAITING at once until B and C are done or
  WAIT_UNTIL = 300 s after setup; Fixer A re-runs it. (First version slept: the sim froze B for 140 s.)
- Checked: local judge on the real rich_3882 repo (A harmless edit, B reference, C test-breaking): C dropped
  (1 test failing), B repro score 1, WINNER B, repo = reference patch. Sim through the harness (SIM_CELLS=
  cells_skill_bo3): 3 fixers each see only their own branch; WAITING -> judge -> WINNER B -> final patch = gold
  (404 chars); NO_EDIT task -> A. Parallel-run end after A's submit = GeneratorExit noise (patch kept). pack.py OK.
- kaggle/cells_skill_bo3: bo3 alone on e24 (24 ever-solved d40 tasks), 1 pass, CONCURRENCY 1 (like the LB);
  cell2, cell3b (digest: judge waits, winner) and cell5 differ from e24x2. ~2.9 h wall / ~5.8 h quota.
  Compare with pub024 on the same 24 (r23 + r24 + e24x2 readings, those at concurrency 2).

### RESULT repro signal (CPU, ziad23samer/fork-of-test-signal-cpu) (2026-10-29)
- data/results/2026-10-29_repro: 243 variants (39 baseline, 39 reference, 165 candidates), 1 without results.
  scripts/repro_signal.py: per script vs no patch: fixes (exit !=0 -> 0), breaks, changed output, marker score (more
  FIXED/PASS, fewer BUG/FAIL/Traceback). The reference changes ~3.9 scripts per task, "fixes" 0.74, score>0 in 22/39.
- Candidates: score 2+ -> 73/118 solved (62%), score 0 -> 15/41 (37%); fixes 2+ -> 67% vs 0 -> 51%. Moderate.
- Picker (solved of 40): k=3: any non-empty 19.5, + test filter 20.0, + repro score 20.3 (oracle 22.1); k=2 19.7;
  k=4 20.6. Optimistic: the scripts pool all 5+ runs of a task, a real best-of-3 has only its 3 attempts' scripts.
- So best-of-3 + (non-empty, no test-breakers, best repro score) ~ +2.5 of 40 over one attempt (17.8): ~+6 pp.

### RUN BUILT: repro signal CPU notebook (kaggle/cells_repro) (2026-10-29)
- The agents' own scripts as a "fixed?" signal: 333 distinct scripts (write_file .py in /tmp|.git/agent, python3 - <<
  heredocs) for 39 d40 tasks, from the request logs of the 8 arm-runs (no new GPU run needed) -> data/testsignal/
  scripts.jsonl, uploaded as a new version of the private dataset ziad23samer/testsignal-candidates.
- scripts/train/make_repro_cells.py: per task, every script runs (20 s, no stdin, PYTHONPATH=repo, PYTHONSAFEPATH
  removed) against no patch / reference / each distinct candidate, via verify_task with test_patch = a new file
  tests/test_zz_probe.py that writes results/repro/<task>__<variant>.json (exit, last 400 chars of out/err).
- Local check (rich_3882, real repo + pytest): without the import fix every script failed (No module named 'rich');
  fixed. Most scripts PRINT rather than assert (exit 0 either way), but 7/10 change their output with the reference
  fix, often "FIXED" / "NOT REPRODUCED" markers -> analyse exit + changed output + markers.
- Same inputs and cell1/cell2 as cells_testsignal; ~2-3 h CPU.

### RESULT test signal (CPU, ziad23samer/test-signal-cpu) (2026-10-29)
- data/results/2026-10-29_testsignal: 39 tasks with selected existing tests (fastapi_14786: none found); baseline
  passes in 38 (14953 fails already); the REFERENCE fix breaks existing tests in 3 (14492, 14609, rich_3470: the old
  behaviour is asserted).
- Candidates (195): keep existing tests passing -> 79/171 solved (46%); break them -> 5/24 (21%), and all 5 are
  fastapi_14492 (reference breaks the same test); without it 0/19. A strong REJECT filter, no "is it fixed" signal.
- Picker (scripts/picker_offline.py, solved of 40): k=2 any non-empty 19.0, +test filter 19.45; k=3 19.5 -> 20.0
  (oracle 22.1); k=4 19.7 -> 20.2 (oracle 23.2); k=5 same 20.2 (oracle 24.0). Best-of-3 + test filter = +2.2 over
  one attempt (17.8). The rest of the oracle gap needs a "fixed?" signal (e.g. a reproduction test from the issue).

### RUN BUILT: e24x2 = pub024 vs sk_a2_32, 2 passes on the 24 ever-solved d40 tasks (2026-10-29)
- User: s20 + the u20 tasks solved in r24 (fastapi_14419, rich_3506, rich_3676, rich_4079) = 24 (dev 6, val 9,
  test 9). kaggle/cells_skill_e24x2 (only cell2 differs): 96 runs, ~3.9 h wall / ~7.8 h quota; 1 pass ~2 h / ~4 h.
  The 16 never-solved tasks are left out (no arm separates there). Refs on these 24: pub024 20 (r23+r24),
  sk_a2_32 18 (r21) + 0 (r24).
- User: pass 2 only if pub024 beats sk_a2_32 in pass 1: PASS2_IF_BEATS = ("pub024", "sk_a2_32") in cell2, checked in
  cell4 after pass 1 (tie or worse -> "PASS 2 SKIPPED", run ends, ~2 h / ~4 h quota). Sim: both branches OK (the sim's
  pub024 ValueError = the fake model calls run_skill_script, which pub024 does not declare; the real prompt never does).

### RUN BUILT: d40x2 = pub024 vs sk_a2_32, 2 passes on the 40 (2026-10-29)
- kaggle/cells_skill_d40x2 (only cell2 differs from u20): 160 runs, ~7.2 h wall / ~14.4 h quota (1 pass of both
  ~3.6 h wall). Pass 1 completes before pass 2, so a STOP_NEW_TASKS_AFTER_H = quota/2 - 0.4 keeps a full pass 1.
  Question: is pub024's ~+2 of 40 (fresh: 20 vs ~17-18) real?

### PACKED pub024 for the LB (2026-10-29): dist/submission.zip = dist/pub024.zip (public LB-0.24 package unchanged;
  validated: LlmAgent, 9 tools incl. the 3 graph tools, 4 files). User submits. Local: 20/40 fresh, never below ours.
  Expect anything in 0.12-0.26 (binomial); one score cannot rank it against sk_a2 (0.18) / sk_a2_32 (0.17).

### RUN BUILT: test-signal CPU notebook (kaggle/cells_testsignal) (2026-10-29, NEWEST — read first)
- Question: does "the EXISTING tests of the changed modules still pass" pick the solved patch (picker 19.5 -> ~22?).
- scripts/train/make_testsignal_cells.py: per d40 task, baseline (no patch) + reference patch (calibration: existing
  tests may assert the OLD behaviour, e.g. rich_3470) + 117 distinct candidate patches from the 8 arm-runs, each through
  the harness's verify_task with a SelTask (test_patch '' and test_files = up to 4 existing tests/ files that import a
  changed module or are named after it). rows.jsonl: ok / exit / passed / failed / errors per run, + hidden 'resolved'.
- Candidates = data/testsignal/candidates.jsonl (local, gitignored) uploaded as the PRIVATE dataset
  ziad23samer/testsignal-candidates. Inputs: competition, wheelhouse, gold-check output (ziad23samer/test-gemma-comp,
  test_deps_wheels), that dataset. CPU, internet off, ~200 runs x ~20 s = ~1.1 h. Local dry run (2 tasks): selection
  works (rich/prompt.py -> tests/test_prompt.py), tests not run locally (sandbox venv has no pytest: local env only).

### OFFLINE PICKER CHECK (scripts/picker_offline.py, no GPU) (2026-10-29)
- 5 runs per d40 task (r20, r21, r22 / r23, r24). Expected solved of 40 when picking 1 of k random runs' patches:
  k=2: pass@1 17.8, oracle 20.5, any non-empty 19.0, smallest 19.0, agreement 19.0.
  k=3: oracle 22.1, any non-empty 19.5, smallest 19.3, largest 18.9, agreement (Jaccard of changed lines, small
  tie-break) 19.6.
- So best-of-3 with a naive pick = +1.7; most of it is "never keep an empty patch when another attempt edited"
  (rich_3521, rich_4075: 0.4 -> 0.9). Agreement adds ~0.1. The remaining 2.5 (to the oracle) needs an execution
  signal (existing tests / repro) - not measurable offline here (local grading has no pip; needs a sandbox).
- Cost: k parallel fixers = k x tokens. VERIFIED (forum 743063, host Ryan Holbrook): "Sequentially" - the LB scorer
  runs one task at a time, so the GPU serves 1 sequence most of the time and parallel attempts batch in vLLM.
  Local parallel arms must run at CONCURRENCY 1 to match.

### RESULT r24: u20 = sk_a2_32 0/20 (376 s), sk_fr2 2/20 (420 s), pub024 2/20 (411 s) (2026-10-29)
- data/results/2026-10-29_skill_u20, 3.61 h. sk_fr2 solved rich_3506 (no review reached) and rich_4079 (review at
  call 35, 0 reviewer edits) -> both by the fixer; reviewer edited in 2 runs (14371, 14964), both failed; 9/20 runs
  never reached the review (fixer used the time). pub024: 14419, 3676. No reviewer rescue on the hard half.
- Fresh totals on d40 (s20 r23 + u20 r24): sk_fr2 19, pub024 20; sk_a2_32 18 (r21). All arms tie.
- Ceiling from 5 runs per d40 task: 13 always solved, 16 never, 11 sometimes (rates 0.2-0.8); ever solved 24/40,
  expected per run 17.8. A clear lead must come from making the 11 "sometimes" tasks reliable (best-of-k + a good
  selector: up to ~24) or from capability on the 16 "never" (most need hidden names / big features; LoRA v1 failed:
  0/7 vs base 3/7 on dev16, 10-25).
- Harness facts for a parallel design: README: ParallelAgent runs sub_agents concurrently in isolated branches
  (conversation, not filesystem: one /workspace); swegemma default concurrency 1 (config.py); whether the LB scorer
  runs tasks one at a time is UNVERIFIED (our "sequential scorer" note is an inference).

### LB: sk_a2_32 = 0.17 (sk_a2 0.18) (2026-10-29)
- 0.17 vs 0.18 = ~1 task of 58. Binomial at ~10.5/58: sd 2.9 tasks (0.05); 90% of single scores fall in 7-15 tasks
  (0.12-0.26); P(one submission >= 0.24) = 0.15, so among 10 forks of a ~0.18 agent P(some 0.24) = 0.81.
  pub024 = our level on every local set (r18 3/8 vs sk_a2 4,3; s20 18 vs 17/18). The LB cannot rank our arms;
  only local sets of 40+ tasks with paired controls can.

### RUN BUILT: u20 = the 20 d40 tasks unsolved in r20 and r21; sk_a2_32 (fresh control), sk_fr2, pub024 (2026-10-29)
- kaggle/cells_skill_u20 (only cell2 differs from s20_fr2_pub). Dev 4 (14419, 3180, 3470, 4079), val 8, test 8.
  60 runs, ~3.5 h wall / ~7 h quota. Fresh control needed: the set was picked as failures, a rerun regains some by
  luck. Question: does the reviewer rescue partial fixes / no-edit runs (r23: rich_3521)?

### RESULT r23: s20 = sk_fr2 17/20 (330 s), pub024 18/20 (270 s) (2026-10-29)
- data/results/2026-10-29_skill_s20_fr2_pub (ziad23samer/fork-of-fork-of-generation-all-shards-gpu v363262706),
  1.77 h. Refs on s20: sk_a2 17 (232 s), sk_a2_32 18 (252 s), sk_fr 15 (371 s). All within noise on a set chosen
  as solved (ceiling 20).
- sk_fr2 vs sk_fr: handover via a.py in 18/20 (PATCH IN PLACE seen in 13 runs), review reached 19/20, reviewer
  replies mean 6.4 (told 3; sk_fr ~14), no test-file / stray-file REVERTs needed, 0 fixer self-submits; mean -41 s.
  Reviewer edited in 4 runs: 14786 S, 3006 S, rich_3521 S (fixer handed over at call 4 with no edit, the reviewer
  made the fix: a rescue; sk_a2 / sk_fr had no patch), rich_4075 E (5 edits, review began at call 42).
  Losses: 14349 E, 15589 E (handover at call 33), 4075.
- pub024 on s20: 18, fast (270 s); loses 14349 (time), 3521 (no patch). pub024 = sk_a2 level again (r18: 3/8).

### RUN BUILT: sk_fr2 on s20 (2026-10-29)
- submissions/sk_fr2 = sk_fr structure, prompts rewritten. a.py (commands.txt adds handoff handover review):
  handoff = after the first change every a.py output ends ">>> PATCH IN PLACE ... your next call is a.py handover";
  handover = the fixer's last call (patch stat, stray/test files, the HANDOVER format, "next reply: plain text");
  review = the reviewer's first call (whole diff, new files, REVERT lines with commands for test files and new
  files outside the package, then: one edit for a missing item or submit). Fixer told 20 calls, reviewer told 3
  ("never run tests or write scripts", "never undo the fixer's edits", "never submit twice"); 34 real.
- Digest adds handoff_seen / handover / review / revert_lines. Sim (SIM_FR2=1): PATCH IN PLACE seen, handover ->
  review -> rm repro.py -> submit, patch = the gold only; empty-diff task: reviewer made the edit.
- User: run it together with pub024 (public LB-0.24 package) = kaggle/cells_skill_s20_fr2_pub (only cell2 differs
  from s20_fr2; 2 arms x 20 tasks, ~2.3 h wall / ~4.6 h quota). sk_fr2 alone: kaggle/cells_skill_s20_fr2: cell2 + cell3b differ from s20_fr. ~1 h wall / ~2 h quota. Refs: sk_a2 17, sk_a2_32
  18, sk_fr 15 (371 s).

### RESULT r22: sk_fr on s20 = 15/20 (sk_a2 17, sk_a2_32 18), mean 371 s vs 232/252 (2026-10-29)
- data/results/2026-10-29_skill_s20_fr, 1.12 h. Fixer obeyed the structure: 16/20 handed over, 0 self-submits;
  4 timed out inside the fixer (12942 reverted its own edit, 15589/3521 no edit, 3278). Losses vs both refs: 12942,
  15589, 3278 (time). s/request unchanged (9.9 vs 9.7) -> the cost is more calls: fixer told 20 used up to 34-40
  (review_at 35-37 in 4 runs = no budget left), reviewer told 6 used 4-25 replies (median ~14).
- Reviewer misbehaviour: test-file edits in 5 runs (14492, 14786, 3006 x3, 3067 x4), scratch repro.py written IN the
  repo (9555), revert + re-apply of the fixer's correct line (3006, 3905), submit loop (14786: 5 submits + git add/
  restore). No case seen where the reviewer corrected a wrong fix. Still solved those (grader resets test files).

### RUN BUILT: sk_fr (fixer -> reviewer) on d40, 1 pass (2026-10-29)
- submissions/sk_fr: root SequentialAgent [fixer.yaml, reviewer.yaml], both = sk_a2 tools + skill + sampling. Fixer
  prompt (fresh): sk_a2 workflow, told 20 calls, never submit, end with a plain-text HANDOVER (CHANGED / TASK ITEMS /
  CHECKED / UNSURE, or WHERE / WHAT with no edit). Reviewer (include_contents none, {problem_description}): told 6
  calls; git diff -> item-by-item check vs the issue -> one test -> change only a missing/wrong item -> git status ->
  submit. max_tool_calls 34 (user: tell lower numbers than the real budget), 8 min. submit_patch declared on both
  (the harness task message names it; undeclared -> ValueError -> runner's outer except -> patch dropped).
- Digest: review_at / review_calls / review_edits / fixer_submit; cell 5 prints REVIEW reached / fixer submitted.
- Sim (data/sim/armsim.py, SIM_CELLS=cells_skill_d40_fr): reviewer's first request = 2 messages (system with the task
  + the HANDOVER), no fixer tool history; empty diff -> reviewer applied the fix; SIM_FR_SUBMIT=1 -> fixer submits,
  patch kept, no review. pack.py: compile_submission OK. Not simulated: reviewer ending without submit -> harness nudge
  re-runs the SequentialAgent from the fixer (full history); the working-tree diff is captured on limits anyway.
- kaggle/cells_skill_d40_fr: cell2, cell3b (digest) and cell5 differ from d40. ~2 h wall, ~4 h quota.
- User (quota): run it on s20 instead = the 20 d40 tasks solved by sk_a2 or sk_a2_32 (dev 4, val 8, test 8):
  kaggle/cells_skill_s20_fr (only cell2 differs from d40_fr), ~1 h wall / ~2 h quota. Reference: sk_a2 17/20,
  sk_a2_32 18/20. Measures breakage + time + handover rate; cannot show rescues of never-solved tasks.

### ANALYSIS d40 (r20 + r21, 80 runs) (2026-10-29)
- Union of the two runs = 20/40 (pass@2) vs 17-18 per run. 35 wrong patches: 33 in the gold file, 25 within 15
  lines -> place found, change wrong. Kinds: hidden exact text/names (14479: task text shows a DIFFERENT message than
  the tests; 15588 message; 13713 param named openapi_external_docs, task says external_docs); partial fix (rich_3535
  fixed one regex error, missed the second); big features (14246, 14962, 3772, 4006, 14609 = 2047 gold lines);
  over-edit (rich_3006: sk_a2_32 added a 2nd change and broke sk_a2's exact gold fix).
- Budget left unused: 20 of 35 wrong runs submitted early with ~150-220 s and ~7 calls left (S runs: 219 s mean,
  first edit 13; E: 326 s, 17; no patch: 425 s, 32). pytest after editing is rare (E 6/35, S 11/35).
- Harness allows SequentialAgent / LoopAgent / ParallelAgent and LlmAgent include_contents: none (adk_submission
  compiler.py, schema.py). ADK 1.36 contents.py: 'none' = context starts at the previous agent's last reply ->
  a fresh-context stage. swegemma agent_runner: the run continues until submit_patch + a final text; a fixer stage
  WITHOUT submit_patch hands over to the next stage; on timeout the working-tree diff is captured anyway.
  Idea: root SequentialAgent [fixer (no submit) -> reviewer (include_contents none, has submit)] uses that budget.
  Risks: reviewer breaks correct fixes (over-edit), +time per task (LB mean must stay <~340 s; sk_a2_32 d40 312 s).

### RESULT r21: sk_a2_32 on d40 = 18/40 (dev 3, val 8, test 7), 1.87 h, mean 312 s (2026-10-29)
- data/results/2026-10-29_skill_d40_32 (notebook ziad23samer/fork-of-fork-of-generation-all-shards-gpu). vs sk_a2
  17/40: 9 tasks changed. Thanks to calls 29-32: fastapi_12942 (32 calls), rich_4075 (31) solved. Noise both ways:
  +rich_3521, -fastapi_15589, -rich_3006 (used 32 calls, wrong). 3 runs went E -> no patch using all 32 calls
  (14099, 3470, 4079: the extra calls went to reading). Mean +40 s/task (still < ~340 s LB budget). Prediction 18 hit.

### RESULT r20: sk_a2 on d40 = 17/40 (dev 3/8, val 7/16, test 7/16), 1.71 h, mean 272 s (2026-10-29)
- data/results/2026-10-29_skill_d40. Same per-task outcome as earlier runs on 14/16 val (mix T0.2 7/16) and 15/16
  test (gen T1.0): most val/test tasks are near-deterministic, so the d40 noise is mostly the 8 dev tasks + ~2-3 flips.
- 28-call cap ended 8 unsolved runs with 1-4 min left (12942, 13713, 14099, 14246, 14479, rich_3063, 4075, 4079):
  what sk_a2_32 (cells_skill_d40_32, running) can change. Prediction: 18 (17-20).

### RUN BUILT: sk_a2 on d40 (8 winnable dev + val 16 + test 16), 1 pass (2026-10-29)
- r19 result first: sk_a2b2k 2/8 (11194, 3882), 0.47 h; thinking 2048 brought calls back to 13.0 s / 382 tokens, but
  3 of 8 still hit the wall without a patch (3521, 3180 never edited; 4079 edit at call 33). Every arm stays 2-5/8.
- d40 baseline: sk_a2 (the LB-0.18 package, 28 calls) once on 40 tasks, kaggle/cells_skill_d40 (cell2 + cell5 differ),
  ~2.4 h wall. References embedded: mix T0.2 8 min = dev 3.67/8 per pass, val 7/16 (1 run); test only gen T1.0 15 min
  6/16. Expect ~16-17/40. Cell 5 prints solved per split. Sim passes (local grading fails: .venv has no pip; env only).

### PROPOSED (built below): a 40-task eval set (2026-10-29)
- Public 129 = dev16 + val 16 + test 16 + train 52 + 29 not gradable. The 84 non-dev tasks have 1 mix run each
  (2026-10-24_gen_combined, T1.0, 15 min, regrade.json): 32/84 = 38% (train 19/52, val 7/16, test 6/16); val's two
  runs (+ gemma_val) agree 16/16. dev16 is the hard end (mix 23%/pass) and matches the LB (0.17) better.
- Problem is sample size: on 8 tasks two arms differ by +-2 from chance. Proposal: 8 winnable dev + val + test = 40
  tasks, ~2.4 h wall (~5 h quota) per arm-pass; first run a baseline (sk_a2 or mix) at LB settings on it.

### RUN BUILT: sk_a2b2k alone, 8 tasks x 2 passes, early stop 3 (2026-10-29)
- User: tweak sk_a2b, thinking 2048. sk_a2b2k = sk_a2b with thinking_budget 2048 (only change; max output 8192,
  T0.2, top_p 0.95, 32 calls, batch). kaggle/cells_skill_b2k (only cell2 differs). 8-16 runs, ~0.6-1.2 h.

### RESULT r18: pub024 3/8, sk_a2b 2/8, early stop after pass 1 (2026-10-29)
- data/results/2026-10-29_skill_b, 16 runs, 1.1 h. pub024 solved 14419, 3180, 3882 (missed 11194, 15589);
  sk_a2b solved 11194, 15589 (missed 3882: its repro called Prompt.ask, read stdin and hit the 240 s command timeout
  twice, 408 s inside tools). sk_a2_32's sibling sk_a2 scored 4 and 3 on the same 8: pub024 is not better here;
  the 0.24 fits LB noise (+ 3 lucky tasks of 58).
- Thinking 4096 costs time: ~500 output tokens/call and 17.6-18 s/call vs ~370 tokens and 13 s at 2048/1024
  (r16/r17). Mean 410-428 s; sk_a2b 5 of 8 ended on the 8 min wall, pub024 2 (its hard runs used ~14k tokens).
- sk_a2b batch: finds used 2-3 terms (3/3 visible), batched shows never (0/20 visible) -> show batching unused.
- Command timeouts (240 s) are rare: 5 in ~450 runs over all results, so stdin-hang guards are a small lever.

### RUN BUILT: pub024 vs sk_a2b, 8 tasks x 2 passes (2026-10-29)
- Research (forum + public notebooks): LB public is ~58 tasks (0.24 = 14, our 0.18 = ~10-11); identical packages
  scored 0.17/0.15/0.13/0.15 (748051), the score spread fits binomial noise; most 0.22s are forks.
  honghanhhh/gemma-4-baseline-lb-0-24 = prompt-only fork of flexonafft v2 (0.22): plain tools, thinking 4096,
  max output 8192, 28 calls / 8 min, "edit by call 12", batches up to 3 greps / sed regions per call.
  Forum 746250: 50 vs 25 tool calls solved 14 more of 129 public tasks.
- The study before it (292 runs on the 8 winnable): failed patches sit in the gold file, mostly within 15 lines of the
  gold edit: the change is wrong (behaviour misread on terse PR titles), not the place. A post-edit test does not help
  (42% vs 41% with first edit by 18). "Show the existing tests" (a.py option tests, kept opt-in, unused) is unreliable:
  internal helpers have no tests by name, and rich_3470's existing test_capture_and_record asserts the OLD behaviour.
  a.py option diffview (YOUR PATCH after an edit) built and tested, unused.
- pub024 = the public 0.24 package unchanged (submissions/pub024, from research/raw/notebooks/honghanhhh_0.24).
  sk_a2b = sk_a2_32 + a.py batch (show up to 3 places per call, find up to 3 terms, one look per call) + thinking
  4096 / out 8192; prompt rewritten from sk_a2's to read in batches.
- kaggle/cells_skill_b (cell2 differs; cell2 tolerates an arm without a skill), EARLY_STOP_MAX 3 (user: an arm with 3 or fewer after pass 1 stops),
  16-32 runs, saved version, about 1.3-2.5 h = about 2.5-5 h quota. Sim clean.

### PACKED for LB: sk_a2_32 = sk_a2 + 32-call config, prompt unchanged (2026-10-29, NEWEST — read first)
- submissions/sk_a2_32 differs from the submitted sk_a2 (byte-identical to dist/sk_a2_submitted.zip) only in
  eval_config max_tool_calls 32 (+ agent.yaml comment). dist/submission.zip = dist/sk_a2_32.zip, pack.py OK.
  The scorer reads max_tool_calls from eval_config.yaml (HARNESS_README 7.1). Never ran on dev: time risk (sk_a2 dev
  331-413 s, LB OK at 343; le5 timed out at 347).

### sk_a2n / sk_a2nr RESULT: 3/8 and 3/8, 388 s (2026-10-29, NEWEST — read first)
- data/results/2026-10-29_skill_a2n, 16 runs, 0.9 h. sk_a2 on the same 8 (r3): 4 then 3, 331 / 413 s.
- vs sk_a2: + rich_3180 (sk_a2nr, edit at 13); - fastapi_15589 (both: no edit, timeout; sk_a2 solved it once at call
  13). rich_3470: the 32 calls let both edit (call 29, 30) but the fix was wrong. 14419 still E.
- Navigate in sk_a2's prompt turns into walking: rich_3470 showed 15-16 whole functions one after another
  (_enter_buffer, _exit_buffer, _check_buffer, _write_buffer, ...), 3 compactions; 15589 re-showed
  _get_multidict_value 3-4 times after compactions and ran 3-4 own scripts (check.py, which sk_a2's prompt invites).

### NEXT RUN BUILT: sk_a2n / sk_a2nr, back to sk_a2 + navigate + 32 calls, 8 tasks, 1 pass (2026-10-29)
- Fix arms undone (commit 7adcc55). top_p/top_k: old 0.95/none 4.00 per 8 (24 runs) vs 0.8/20 3.50 (32), same T and
  thinking: no effect. Back to sk_a2 (LB 0.18), keeping the two nav pieces behind the new solves:
  every nav solve of rich_3470 made its first edit at call 28-32 (sk_a2's config refuses them; its own two runs edited
  at 29 and 30, no patch); every nav solve of fastapi_14419 (sk_a2 0/3) used CALLED FROM 3-5 times.
- sk_a2n: sk_a2's prompt rewritten + a CALLED FROM / DECIDE section (one hop to a caller, PING-PONG), a.py navigate,
  config 32 calls (prompt says 28 / 8 min), sk_a2's sampling and edit_file. sk_a2nr: the same + a.py replace (sk_a5r's
  edit paragraph instead of edit_file's). a.py DECIDE says "(replace)" only when replace is installed.
- kaggle/cells_skill_a2n (only cell2 differs), 16 runs, saved version, about 1 h = about 2 h quota. Sim clean.

### FIX ARMS RESULT: control 3/8, tmpl 3/8, brake 4/8 (2026-10-29, NEWEST — read first)
- data/results/2026-10-29_skill_fix, 24 runs, 1.3 h. Mean agent s: control (r_n2k rerun) 356, tmpl 392 (4 timeouts),
  brake 374 (1 timeout). r_n2k over 3 passes on these 8 tasks: 5, 3, 3.
- Install at call 1 in all 24 runs (control too: the r15 fastapi_15589 miss was not repeated). tmpl solved fastapi_15589.
- Template (EDIT NOW appended to whole-function shows): fired 12 times in 3 runs; the next call was an edit once
  (rich_3180, and a different file). Ignored, like the other stop-signals. Drop it.
- Brake (reading BLOCKED until the first edit): fired in 4 runs, 7 times; next call an edit 3 of 7, and every run it
  fired in made an edit at calls 18-21 except rich_3180, where the model read around it with
  python3 -c inspect.getsource and timed out with no patch. All 4 runs it fired in failed: the extra solves vs control
  (fastapi_14419 with first edit 16, rich_3521 with first edit 11) had no block, so they are prompt or noise.
- Brake gap: it blocks a.py reads only; probes (inspect.getsource, python - << EOF) and grep/sed get around it.

### NEXT RUN BUILT: fix arms sk_nav_tmpl / sk_nav_brake vs sk_nav_s6_32r_n2k, 8 tasks, 1 pass (2026-10-29)
- Signal check (3 runs, next call after each a.py signal): STOP READING -> edit 12%, NO EDIT YET 3%, DECIDE 6%,
  PING-PONG -> show/outline 65%. The prompt already said "your next call is the edit": the model obeys read-signals only.
- F1 (both fix arms): new prompt HEAD_FIX in scripts/make_skill_arms.py (full text): "Tool call 1: run_skill_script,
  whatever the issue says" as the first section; a section listing a.py's signals as orders for the next call.
- F2a sk_nav_tmpl: a.py option template = after STOP READING (15 looks / 300 s, no change) a whole-function show ends
  with "EDIT NOW" + the replace command for those lines. F2b sk_nav_brake: option brake = find/outline/show BLOCKED
  until the first edit; the message carries the same replace command (scripts/agent_skill/a.py, scratch-repo tested).
- Prompt review fix: NO EDIT YET / ALREADY SHOWN conditional like a.py's own text; the closing evidence line is measured
  (204 nav runs: first edit by call 20 solved 50%, 21-24 29%, 25+ 13%, no edit 0%).
- Both: base sk_nav_s6_32r_n2k (n2k sampling, 32 calls / 8 min). kaggle/cells_skill_fix (only cell2 differs from
  cells_skill_rn2k), 24 runs on the 8 tasks, saved version, about 1.5 h = about 3 h quota.

### sk_nav_s6_32r_n2k on ALL 16: 3/16, 353 s/task (2026-10-29, NEWEST — read first)
- data/results/2026-10-29_skill_rn2k, reference r15. Solved rich_3882, fastapi_11194, rich_3521. Ends ok 12, time 4.
- Failure groups: (a) never installed: fastapi_15589 + fastapi_14487 (same 2 tasks as s6_32i 19/25 and s6_32r 22 for
  14487); first thought goes straight to "Let's start by searching for X" from the issue text. (b) first edit at call
  25-33 in 6 runs (14306, 15280, 15800, 3470, 3934, 4079) after 16-22 whole-function shows; 3934 / 4079 no patch.
  (c) slow thinking 17-32 s/call: rich_3180 (no edit), fastapi_14419, rich_3468 timed out.
- User: rerun it for consistency next to a variant that fixes the errors (design under discussion).

### NEXT RUN BUILT: sk_nav_s6_32r_n2k alone, all 16, 1 pass (2026-10-29)
- User picks s6_32r + n2k (T0.2, top_p 0.8, top_k 20, thinking 2048, max_output 4096) for a full dev16 pass.
- kaggle/cells_skill_rn2k (only cell2 differs from cells_skill_think), 16 runs, saved version, about 1 h = about 2 h quota.
  Sim: requests carry the n2k sampling. Compare with s6_32 (6, 2), s6_32i 3, s6_32r 4 on all 16; watch mean agent s.

### THINKING 2048 / 4096 RESULT: 13/32 (2026-10-29, NEWEST — read first)
- Kernel ziad23samer/fork-of-generation-all-shards-gpu, 116 min. data/results/2026-10-29_skill_think, reference r14.
- On the 8 tasks: s6_32_n2k 3, s6_32_n4k 2, s6_32r_n2k 5 (incl. rich_4079 + rich_3521), s6_32r_n4k 3.
- Pooled over all 12 arm-runs on these 8 tasks (per 8 tasks): thinking 1024 2.5 (10/32), 2048 3.83 (23/48),
  4096 2.5 (5/16). top_p/top_k at 2048: old 0.95/none 3.75 (15/32) vs 0.8/20 4.0 (8/16) = no effect.
  Prompt: s6_32 3.17 (19/48) vs s6_32r 3.2 (16/40) = no difference.
- 4096 gave 3 replies of 4,000+ tokens per arm and no hard-task solves. fastapi_14419 solved 3x here (0 in the 8 earlier
  nav runs). Time unchanged everywhere: mean agent s 375-405, 2-4 time-outs per 8 tasks.
- Keep: thinking 2048. top_p 0.8 / top_k 20 are harmless, not a gain. The remaining problem is time per task.

### NEXT RUN BUILT: n sampling with thinking 2048 / 4096 on s6_32 and s6_32r, 8 tasks, 1 pass (2026-10-28, NEWEST — read first)
- top_p/top_k analysis of r13: g (T0) and n (T0.2, top_p 0.8, top_k 20) behave the same on every measure (reply length,
  cap hits, calls, probes, first edit); both moved away from old by the same amount, so the shift was the 1024 cap.
  At T0.2 probabilities are raised to the 5th power, so top_p 0.8-0.95 / top_k 20 almost never cut a likely word.
- Arms (SAMPLING n2k / n4k in scripts/make_skill_arms.py; only configs/sampling.yaml differs from the base):
  sk_nav_s6_32_n2k, sk_nav_s6_32r_n2k = T0.2, top_p 0.8, top_k 20, thinking 2048, max_output 4096;
  sk_nav_s6_32_n4k, sk_nav_s6_32r_n4k = same with thinking 4096, max_output 6144.
- kaggle/cells_skill_think (only cell2 differs from cells_skill_samp), 32 runs on the 8 tasks, saved version, about 4 h
  quota (n4k may be slower). Sim: requests carry thinking_token_budget 2048 / 4096 and max_completion_tokens 4096 / 6144.
- Read: n2k vs old (15/32 over 4 runs) checks that the 1024 cap explained r13; n4k tests more room on hard steps.

### SAMPLING ARMS RESULT: 10/32, worse than old sampling (2026-10-28, NEWEST — read first)
- Kernel ziad23samer/fork-of-generation-all-shards-gpu (2nd account), 112.8 min. data/results/2026-10-28_skill_samp, r13.
- On the 8 tasks: g 3, n 3, r_g 1, r_n 3 = 10/32. Old sampling (4 runs of s6_32 / i / r) = 15/32.
  Hard tier (rich_4079, rich_3521, rich_3180): old 4/12, new 0/12. Easy tier unchanged.
- Thinking cap 1024 did not save time: mean agent s 373-391 (old 344-406), output tokens about the same (10.4-11.0k);
  the 2,000+ token replies vanished but replies of 1,000+ tokens rose from 22-27 to 29-37 per arm (same total seconds).
  The model splits the same thinking over more calls and loses depth on hard steps.
- Temperature 0 did not loop (2 back-to-back repeats per arm, as before) and was no better than n.
- Decision basis: revert to thinking 2048; sampling is not the lever for time. sk_a2 (0.18) stays the LB best.

### NEXT RUN BUILT: sampling arms g / n on s6_32 and s6_32r, 8 tasks, 1 pass (2026-10-28, NEWEST — read first)
- User: s6_32's 6 (first rich_3180 solve in months) shows the method can work; control variance and time via sampling.
- scripts/make_skill_arms.py SAMPLING / SAMPLING_VARIANTS: file-for-file copies, only configs/sampling.yaml replaced:
  g = temperature 0.0, top_p 1.0 (greedy: top_p/top_k do nothing), thinking_budget 1024;
  n = temperature 0.2, top_p 0.8, top_k 20, thinking_budget 1024. Old: 0.2 / 0.95 / no top_k / 2048. max_output 4096 kept.
- Arms sk_nav_s6_32_g, _n, sk_nav_s6_32r_g, _n on the 8 tasks solved at least once (WINNABLE7 + rich_3180):
  kaggle/cells_skill_samp (only cell2 differs from cells_skill_s6r), 32 runs, saved version, about 2 h = about 4 h quota.
- Sim: requests carry temperature 0.0 / thinking_token_budget 1024 / top_p 1.0 (g) and 0.2 / 0.8 / top_k 20 / 1024 (n).
- Baseline on these 8 tasks (old sampling): s6_32 6 then 2, s6_32i 3, s6_32r 4 (all from the 16-task runs).

### sk_nav_s6_32 RERUN 2/16 + sk_nav_s6_32r 4/16 (2026-10-28, NEWEST — read first)
- kaggle/cells_skill_s6r, 32 runs, 116 min. Results data/results/2026-10-28_skill_s6r; reference column r12.
- **The identical arm sk_nav_s6_32 went 6 -> 2.** Its 6 was luck; over 2 passes it is 4.0 per pass. s6_32r 4, s6_32i 3,
  mix 3.67. Dev noise for one 16-task pass is about +-2: one pass cannot rank these arms.
- Time is the real problem: mean agent s per run s6_32 344 / 401, s6_32i 386, s6_32r 370 (sk_a2, scored 0.18 on LB: 343).
  2,000+ token replies: 12 / 26 (s6_32), 17 (i), 16 (r). Compactions 28 / 32 / 37 / 33.
- sk_nav_s6_32 NOT submitted (slot free). At 370-400 s/task it risks the 12 h LB limit (le5 at 347 s timed out).

### LB: sk_a2 = 0.18 (best so far; mix 0.17) + NEXT RUN BUILT: sk_nav_s6_32 vs sk_nav_s6_32r (2026-10-28, NEWEST — read first)
- sk_a2 (submitted 10-26 09:16 UTC) COMPLETE, public 0.18. The slot is free: dist/submission.zip = sk_nav_s6_32.
- s6_32i analysis: after call 1 the route is the same as s6_32 (install mentioned in 2/470 later replies); the runs split
  on hard reasoning steps. s6_32i had more 2,000+ token replies (17 vs 12, 1,226 s vs 894 s) and more compactions
  (37 vs 28; rich_3521 1 -> 3, rich_4079 2 -> 3).
- User: drop the contract timing, the new Avoid line and the new example; keep only install as route step 1 =
  sk_nav_s6_32r (scripts/make_skill_arms.py ROUTE_EDITS). Rerun it next to sk_nav_s6_32 unchanged (is the 6 luck?).
- kaggle/cells_skill_s6r: 2 arms x 16 tasks, 1 pass, 2 at once, saved version; about 110 min = about 3.6 h quota.
  Sim (armsim) OK.

### sk_nav_s6_32i RESULT: 3/16 (2026-10-28, NEWEST — read first)
- Run: kaggle/cells_skill_s6i, 16 runs, 61.9 min session (about 2 h quota), mean agent 386 s (s6_32: 344 s), ends ok 11, time 5
  (s6_32: 0 time-outs). Results in data/results/2026-10-28_skill_s6i; reference column r11.
- The install fix worked: 14/16 installed at call 1 (s6_32: 0/16). The two misses (fastapi_15589 at 19, fastapi_14487 at 25)
  started with run_command grep anyway. fastapi_15589's patch is only a stray repro.py (no source edit).
- Solved: rich_3882, fastapi_11194, rich_3470. Lost vs s6_32: rich_3180 (solved once in all history), rich_3521 and
  rich_4079 (coin flips across arms). No new solves.
- Call 1 is not the cost (100-270 output tokens, about 5-10 s, same as s6_32). The runs wrote more overall: 10.7k vs 9.1k
  output tokens per run, 374 vs 334 model s, so 5 hit the 8-minute cap (13920, 14419, 15280, 3468, 3180).
- Read: install-first does not raise the score; 6 vs 3 is mostly dev noise on the 3 hard rich tasks, and s6_32i is slower
  (386 s is over the about 345 s LB safety line). Keep dist/submission.zip = sk_nav_s6_32.

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
