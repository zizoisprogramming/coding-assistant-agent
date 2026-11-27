# Training requirements: adapters P and O (draft 2026-11-27)

What must be true before, during and after we train, so that nothing teaches the model a bad habit and nothing
breaks on the scorer. Each requirement has an id, the reason, and **how it is checked**. "Checked" means a script
or a test that prints PASS / FAIL, not "I looked at it". Status: DRAFT, to agree with the user before any build.

Decisions this builds on (docs/PLAN.md, 2026-11-26): adapter **P** = copy the best-process sk_a2 passes;
adapter **O** = P's copy + one step rule on every run (good / bad / masked, the same in solved and failed runs);
final test **base vs P vs O** in one notebook; then the LB.

---

## A. Goal and time

| id | requirement | why | checked by |
|---|---|---|---|
| A1 | The only success measure is solves on tasks the adapter never trained on (RTEST24), same notebook as the base. Validation loss is a guard, not a success measure. | October: loss went down, the test went 0/7 vs 3/7. | final test report |
| A2 | Schedule fits the deadline (Dec 2): train Sat 11-28 (quota reset), test Sun 11-29, LB submission Mon 11-30 at the latest (scoring takes ~1 day, one pending at a time). | Missing a step = no adapter on the LB. | dated plan in PLAN.md |
| A3 | sk_a2 stays the fallback submission; an adapter replaces it only if it passes the final-test bar (section G). | sk_a2 = 0.18 / 0.17, our best. | G3 |

## B. Data in

| id | requirement | why | checked by |
|---|---|---|---|
| B1 | Only sk_a2 runs (the submitted prompt), from r165, r166 (4 shards), r167 (2 shards). Nothing from Claude / GPT / Gemini (D14). | Train on the exact prompt we submit; user rule. | arm column = sk_a2 on every episode |
| B2 | Every source notebook version is attached and complete: ziad23samer v119 (r165-A), v121 (r166 s1), v122 (r166 s4) and its r167 version; engziadsamer/arms-again r165-B, r166 s2, r167; ziadsamer r166 s3. | The requests.jsonl (the model's real inputs and outputs) live only there. | notebook prints runs per source and asserts each equals the count in our downloaded gen_per_task.jsonl |
| B3 | No held-out task reaches training: RTEST24, data/rebench_test, the 8 dev16 test tasks (scripts/train/heldout_eval.json). | Otherwise the final test measures memory, not skill. | pref_episodes asserts; the notebook re-checks the final sample file's task ids against the list |
| B4 | Only runs whose status is ok; infrastructure ends (sandbox crash, harness error) are dropped, not labelled. | An infra failure is not the model's fault. | counts printed per end type |
| B5 | Training context = exactly what the model saw (prompt + its own replies + tool outputs, rendered with the model's chat template). | Training on a different text teaches a different situation. | build_samples' character check (each prompt extends the previous one) + count of breaks printed |

## C. Labels

### C1. Adapter P: which passes are copied

| id | requirement | why | checked by |
|---|---|---|---|
| C1.1 | Per task, only the best-process passes: no loop (fail streak > 3, repeats > 3), no junk text, no test-file edit, submitted; then most milestones, then fewest steps. Cap K passes per task (proposal K = 2). | "Quality, Not Just Outcome": worst-process passes went BELOW base (21.8 vs 24.4); best ones 27.6. | selection report: per task, kept / rejected and why |
| C1.2 | Inside a kept pass, every reply is trained EXCEPT failed calls, retries and maxed thinking (masked = not trained either way). | Do not copy mistakes even inside a good run. | label counts per category |
| C1.3 | Easy tasks do not dominate: cap tokens per task. | 72 always-solved tasks would otherwise be most of the data. | tokens per task printed, max share |

### C2. Adapter O: one rule on every run

| id | requirement | why | checked by |
|---|---|---|---|
| C2.1 | The same table for solved and failed runs (user: "no difference between solved runs and failed runs"). Good = the 6 milestones (saw the fix, right place, check after edit (ran), diff before submit (ran), quick edit, loop break). Bad = reading on, maxed thinking before the first edit, the final wrong edit of a failed run, junk text, a test-file edit. Masked = failed / retried / repeated / refused calls, a step that is both good and bad, every other step. | One consistent rule; unknown steps are not guessed. | unit tests on hand-made runs, one per row of the table |
| C2.2 | The same weight for a label wherever it appears (the 0.5 milestone discount dropped); same-task weights good 1 - p, bad p kept. | User decision. | weights printed per label |
| C2.3 | O also gets P's copy term on P's chosen passes (C1). | Unlabelled steps of good runs are taught only through the proven copy. | sample file holds both parts, counts printed |
| C2.4 | Rule-breaking solved runs are no longer dropped; their offending steps are labelled bad by the table. | User: label the step, do not leave the run out. | count of such runs printed |

### C3. Labels in general

| id | requirement | why | checked by |
|---|---|---|---|
| C3.1 | A good label only on a step the harness actually ran (no refused / budget-exhausted calls). | Found 11-26: would teach calling after the budget is gone. | test: zero good labels on refused calls over all data |
| C3.2 | Every label category is shown on at least one real run, read by eye before training (a "label gallery"). | The 11-26 bug was found exactly this way. | gallery file, one example per category |
| C3.3 | No label is placed on the system prompt, tool outputs or the compaction summary. | Only the model's own words are trained. | test: graded tokens all inside reply spans |

## D. Samples

| id | requirement | why | checked by |
|---|---|---|---|
| D1 | Cut after the last graded token (done 11-26). | Less memory, same result (causal model). | the 128/128 identical check, repeated in the notebook |
| D2 | No segment longer than 16,384 tokens is silently lost: counted and printed. | Long runs are often the hard ones. | count printed |
| D3 | Train / validation split by TASK (no task in both). | Otherwise validation is memorised. | assert |

## E. Training

| id | requirement | why | checked by |
|---|---|---|---|
| E1 | P = copy term only (no KTO); O = copy + KTO. Same lr (2e-5), rank r16 / alpha16, seed, budget, max length. Only the labels differ. | So the test compares the labels, not other settings. | the two configs printed side by side, diff = labels only |
| E2 | Fits one session and ends by itself before the quota runs out (STOP = quota / 2 - 0.4 h), saving best / last adapters. | A cancelled or killed version loses its outputs. | session-hours guard; dry run with the real timing |
| E3 | Verbose: per step loss / lr / grad norm / tokens per s / ETA; validation every N steps (val loss, good-vs-bad margin for O, passes' NLL). | User rule; problems seen early. | the log |
| E4 | Drift guard: the kept checkpoint is the best one whose passes' validation NLL rose < 10% from the start. | Keep the model close to sk_a2. | in train_pref.py; tested on the tiny model |
| E5 | Step 0 sanity: adapter output = base output (LoRA B = 0), margin 0, loss finite. | Catches a broken setup before hours are spent. | printed check, the run stops if it fails |

## F. Adapter on the scorer

| id | requirement | why | checked by |
|---|---|---|---|
| F1 | Format: adapters/<name>/adapter_config.json + adapter_model.safetensors, PEFT names the scorer's vLLM accepts, rank <= 128, whole bundle < 3 GiB; agent.yaml `adapter: <name>`. | Harness rules (HARNESS_README section 3.4). | pack.py (the competition's own checks) on the real bundle |
| F2 | Served by the scorer's own vLLM settings (enable_lora, max_lora_rank 128, gpu_memory_utilization 0.80, max_model_len 32,768) without running out of memory at start. | Forum (10-14): some LoRA bundles OOM at startup; ours passed the serve check on 10-24 with the same saver (int4_lora.save_adapter). | the final test notebook starts vLLM exactly that way |
| F3 | Time: LoRA decodes ~11% slower (forum). sk_a2 runs must still finish inside the 8-min limit: time-end rate with the adapter not above base + 5 points. | A slower adapter can lose tasks to timeouts even if it is smarter. | time-end counts per arm in the final test |
| F4 | sk_a2's prompt, tools and sampling unchanged in the adapter bundle (only agent.yaml gains `adapter:` and adapters/ is added). | Test one change. | diff -r against submissions/sk_a2 |

## G. Final test

| id | requirement | why | checked by |
|---|---|---|---|
| G1 | base vs P vs O in ONE notebook, same tasks, arms interleaved per task; RTEST24 decides; dev16 reported apart (repo overlap with training). | Same-run control (user rule). | report |
| G2 | Expected ranges written BEFORE the run: base solve rate on RTEST24 from earlier data, and how big a gap 2 runs per task can detect (roughly 4-5 runs out of 48 per arm). | Judge luck vs effect (user rule). | PLAN entry before the run |
| G3 | Bar agreed before the run (proposal): an adapter goes to the LB if it solves >= base on RTEST24, no-patch and time-end rates not up by > 5 points, and the loop report not worse. | Decide by rule, not by mood. | report prints PASS / FAIL per bar |
| G4 | The test notebook ends by itself and prints per-run lines. | User rules. | the log |

## H. Full test sweep and debugging before the GPU handoff

Everything here runs on the laptop (CPU) before the user spends quota.

| id | requirement | checked by |
|---|---|---|
| H1 | Unit tests for every label rule (one hand-made run per table row of C2.1, plus P's selection order). | new tests, PASS |
| H2 | The existing tiny-model trainer test (test_train_pref_tiny.py) passes for P (copy only) and O (copy + KTO), including stop + resume = an unbroken run. | PASS |
| H3 | Full local pipeline on all local sk_a2 data (pref_episodes -> build_samples -> train_pref 1 step on the tiny model). | runs end to end, counts printed |
| H4 | Crash-path audit over ALL data: every run of every source goes through labelling without an exception (odd runs counted, never stop the build). | count of skipped runs = 0 or explained |
| H5 | Notebook simulator: the training and test notebooks run locally with stubbed GPU parts (inputs found, asserts, guards, file names). | sim exit 0 |
| H6 | Label gallery (C3.2) read and agreed by the user. | user OK |
| H7 | A real adapter (from the tiny run, or October's) packed and checked with pack.py. | pack.py OK |

## Open questions for the user

1. Weekly quota per account after the Saturday reset (we need: 2 training sessions + 1 test).
2. Can "Add Input" pick an older version of a notebook? If not, the training notebook downloads the 9 versions with the Kaggle API (needs your token as a Kaggle secret).
3. P's cap: K = 2 best passes per task, or more?
4. The final-test bar G3: OK as written?
