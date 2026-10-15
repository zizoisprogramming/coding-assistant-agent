# Dev set v2 (2026-10-13): 16 tasks that grade correctly on Kaggle

Gold check on Kaggle (CPU session, scorer's verify_task, subprocess sandbox; data/results/2026-10-13_gold_check):
25 checked, 20 usable (gold PASS + empty FAIL). Not gradable on Kaggle: fastapi_14583, fastapi_14978,
fastapi_14266, fastapi_15023 (test collection errors), rich_3296 (4 syntax tests fail, likely pygments version).
Chosen 16 (wave A of research/dev_tasks_feasibility.md; failures replaced from wave B in the same stratum;
fastapi_15588 dropped: never solved, hidden error message):
- fastapi S: 15589, 13920, 14258, 11194, 14487 | M: 15280, 14419 | L: 15800, 14306
- rich S: 3882, 3470, 4079 | M: 3521, 3934, 3468 | L: 3180
Spare usable: fastapi_15588, fastapi_14372, rich_3506, rich_3782.

## Rung-3a: r4_budget vs r4b_think_t02 on the 16 tasks, 1 run each, concurrency 2

### Results (2026-10-13)
r4_budget **3/16** (rich_4079, rich_3882, rich_3521), mean 314 s/task; r4b_think_t02 **3/16** (fastapi_15589,
rich_3882, fastapi_11194), mean 400 s/task. Union 5/16; only rich_3882 in both.
| Outcome | r4_budget | r4b_think_t02 |
|---|---|---|
| solved | 3 | 3 |
| wrong fix | 6 | 4 |
| no edit: edit attempted after the 28-call cap (BudgetExceeded) | 2 | 4 |
| no edit: time limit | 1 | 3 |
| no edit: never got an edit in (incl. failing edit_file calls) | 4 | 2 |
- Half the tasks end with an empty patch. In every one the "10 calls left" warning came at call 18 and the agent
  kept reading/scripting (8–19 reads, 10–18 greps); edits then came at calls 24–29, several rejected at 29.
- Runtime: 314 s/task → ~10.5 h for 120 sequential tasks; think_t02 400 s → ~13.3 h (over the 12-h limit; not
  submittable as is). Measured with concurrency 2 (~5–10 % slower), on harder-than-old tasks.
- Next idea: an event-anchored rule ("when a tool result says only N calls remain, the very next call is your best
  edit"), since event-triggered rules are the ones the model follows.

## Rung-3b design (2026-10-13): two new arms, compared with rung-3a (no unchanged repeat, user)
rung-3a split: r4_budget fastapi 0/9, rich 3/7 (edits more, more wrong fixes); r4b_think_t02 fastapi 2/9, rich 1/7.
Most wrong fixes miss one test: fastapi ones on the exact interface/wording (expected "Validation errors:", a
`prompt=` parameter, another exception), rich ones on a behaviour detail.
- **af**: SequentialAgent [analyst → fixer] in one session. Analyst: read-only tools (run_command, read_file,
  get_status), thinking 4096 / T 0.2, prompt prompts/analyst.md (345 words): find LOCATION + exact CONTRACT
  (names/params/messages/status codes, from task + sibling code) + FIX, hand over after ~8–12 calls or at the
  low-budget warning. Fixer: r4_budget prompt + "start from the plan: read LOCATION once, next call is the edit"
  (fixer.md), r4_budget sampling. Shared 8 min / 28 calls. Risk: a nudge after a text-only fixer turn restarts
  the sequence at the analyst.
- **r4b_warn**: r4_budget + "When a tool result says only a few tool calls remain, your very next call is your
  best edit, even if you are unsure. Use the calls left to check it and adjust it."
Watch: analyst calls before hand-over, plan quality, fixer first-edit call, no-edit count, mean s/task (12-h limit).

### Rung-3b results (2026-10-13)
| Arm | Solved | Wrong fix | No edit | Mean s/task |
|---|---|---|---|---|
| af (analyst → fixer) | 3/16 (fastapi_15589, rich_3882, fastapi_11194) | 2 | 11 | 418 |
| r4b_warn | 2/16 (rich_3882, fastapi_11194) | 10 | 4 | 272 |
| rung-3a r4_budget | 3/16 | 6 | 7 | 314 |
| rung-3a r4b_think_t02 | 3/16 | 4 | 9 | 400 |
- af: the analyst ignored "hand over after ~8–12 calls": 16–29 calls (median ~21; 7 tasks used the whole 28),
  hand-over at 197–478 s, never in 3 tasks; the fixer got 0–19 calls (mostly ≤ 5). No restarts. It behaved like
  the deep-thinking arm and solved the same 3 tasks. Per-agent call limits do not exist in the YAML schema, so the
  split cannot be enforced; another self-monitoring rule that is ignored.
- r4b_warn: the warning rule works mechanically (no-edit 7 → 4, wrong fixes 6 → 10) but the forced edits are
  guesses; solved did not rise. By call 18 the agent usually does not know the right change yet.
- Six arms on dev16 all score 2–3/16; union of solved tasks over all arms: fastapi_15589, fastapi_11194,
  rich_3882, rich_4079, rich_3521 (5/16). Prompt/budget/structure changes have plateaued on this set; the limit is
  finding the right change (location + exact interface), not editing.

## Rung-3c design (2026-10-13): af2 = af with the analyst prompt rewritten for few calls (user)
New analyst.md (scout role; "every call you spend is a call the fixer loses"; three questions in ~6 calls; no
reproducing/running/editing; call 1 = git grep -A 25 to search and read at once; whole-function reads of 80–150
lines; stop as soon as the three answers are known; one-call example; same LOCATION/CONTRACT/FIX hand-over).
Fixer, sampling (analyst 4096/T 0.2), tools and budget unchanged. Measure: analyst calls before hand-over,
hand-over time, fixer calls, solved/no-edit, mean s/task.

### Rung-3c result (2026-10-13): af2 3/16 (rich_3882, fastapi_11194, rich_3521), mean 420 s/task
- The rewrite did not reduce analyst calls: median 21.5 (af: ~21); 13–28 calls; only rich_3882 (5 calls, hand-over
  at 66 s, solved in 97 s) followed the "about 6 calls" plan. No hand-over in 4 tasks; 8 tasks hit the time limit.
- Second cost: single deep-thinking steps of 4–7k tokens taking 130–242 s (rich_3521: 7 analyst calls but hand-over
  at 369 s; rich_3180: one step 242 s / 7,343 tokens). With thinking 4096 / max_output 8192 the analyst can burn
  half the 8 minutes in one or two steps.
- Conclusion: under 8 min / 28 shared calls, the analyst → fixer split does not fit: call count is not controllable
  by wording (third time), and deep steps are too slow. Would need a tool-enforced cap and a smaller analyst
  thinking budget (e.g. 1024–2048) to be viable.

## LB anchor (2026-10-14): r4_budget = **0.15** on the LB ↔ 3/16 on dev v2.

## Rung-3d design (2026-10-14): bf calibration + thinking middle ground
- bf: public Budget-Fit v4, unchanged (LB 0.18; never run on dev v2) → second calibration point.
- r4_mid: r4_budget + T 0.2 + thinking 2048 (max_output 4096). r4_mid1k: same with thinking 1024 (max_output 2048).
  Hypothesis: low temperature + moderate thinking solves the reasoning-heavy fastapi tasks (think_t02 did at 4096)
  while keeping steps short enough to edit in time and stay under ~330 s/task (12-h limit).
Later (user): a bf × r4 prompt mix.

## Rung-3e design (2026-10-14, built while rung-3d runs; thinking budgets to be set from rung-3d)
- **mix**: bf bundle (6 tools, T 0.2) with bf's call-count rules ("edit by call 12", "no exploration after call 20")
  replaced by r4's scoring + one decision rule, r4's fast-path example and r4's edit fallback; 783 words.
  Placeholder thinking 2048 / max_output 4096.
- **le** (locator → editor, user design): root locator (T 0.2, deep thinking, placeholder 2048 / max_output 4096)
  reads ONLY through the scout skill (skills_src/scout: find = git grep + following code, show = ≤150 numbered
  lines, both counted, 16 reading calls then refusal with a countdown from 13; plan = writes /tmp/plan.md; check =
  git diff + targeted pytest; free). It writes FILE / WHAT IT DOES / CHANGE (exact old → new lines) / CONTRACT,
  calls the editor (agent_tool, "Apply /tmp/plan.md"; thinking 256 / max_output 1024 / T 1.0 = r4 halved; tools
  run_command, read_file, edit_file; answers EDITED/FAILED per file), checks, allows one correction, submits.
  Budget 8 min / 36 calls / 90 turns. Locator has no run_command/read_file, so the reading cap cannot be bypassed.
  scout tested locally through an ADK-style wrapper (workspace found via the wrapper's _orig_cwd frame; counter in
  the task's TMPDIR); ADK leaves {"mode": ...} examples in instructions untouched (not valid state names).
- Added after the design review (user): scout `history` mode (git log -S NAME + 8 latest commits, or one commit's
  change; counted) for title-only tasks; correction guard in le ("correct only if the diff is not what you planned,
  the editor answered FAILED, or a test fails because of an error in the new code; a test asserting the old
  behaviour the task changes is expected"); control arm **lo** = the same locator + scout + settings + 36 calls,
  editing itself with edit_file (no editor). le vs lo separates the reading cap from the editor.

## rung-3d + rung-3e results (2026-10-14; one run each, 16 tasks; both notebooks ran tasks serially despite CONCURRENCY=2, cause unknown; per-task times normal)

| arm | solved | no-edit | mean s | timeouts | turn-limit |
|---|---|---|---|---|---|
| r4_budget (LB 0.15) | 3 | 7 | 314 | 2 | 0 |
| r4b_think_t02 | 3 | 9 | 400 | 6 | 0 |
| bf (public 0.17-0.18) | 4 | 5 | 321 | 3 | 6 |
| r4_mid (T0.2, think 2048) | 3 | 3 | 311 | 3 | 0 |
| r4_mid1k (T0.2, think 1024) | 3 | 4 | 299 | 2 | 0 |
| le (locator -> editor) | 3 | 7 | 430 | 7 | 0 |
| lo (locator edits) | 2 | 6 | 385 | 8 | 1 |
| mix (bf + r4 decision rule) | 4 | 4 | 346 | 3 | 7 |

- Solved: bf = 14419, 3882, 11194, 3521; mix = 15589, 14419, 3882, 11194; r4_mid = 14419, 3882, 11194;
  r4_mid1k = 3882, 11194, 3470; le = 3882, 11194, 3521; lo = 3882, 3521.
- Union over all arms = 7/16 (11194, 14419, 15589, 3470, 3521, 3882, 4079); best single arm 4.
- T 0.2 + thinking >= 1024 solves fastapi_11194 every time; T 1.0 never. fastapi_14419 needs thinking >= 2048 at T 0.2.
- Low temperature leaves fewer tasks without an edit (3-5 vs 7-9); the bottleneck is now wrong edits (mix: 10 wrong).
- le vs lo: +1 task for the editor at +45 s/task; both below mix/bf. Locator design parked.
- Differences of 1 task are within run-to-run noise (single runs).

## rung-3f design (2026-10-15): le2 + lo2 = le/lo with a fixed scout parser (only change)
le traces: of ~400 scout calls, 240 read OK, **123 (~30%) were argument-format errors**, 19 limit refusals, 17 plans.
Causes: `show` rejected start 0 / missing start (`if not (a.file and a.start)`); the model used 4 argument shapes
(dict, nested {"args": {...}} → `--args "{repr}"`, list, positional_args after `--`). Every error cost one of the 36
calls; 5/16 tasks never reached the editor, the rest only at call 22-29. New parser replayed on all 738 le/lo scout
calls: 732 parse (the 6 left are empty or garbled by the tool-call parser). Defaults: show 1-150, start 0 → 1.
