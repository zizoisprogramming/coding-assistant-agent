"""Writes kaggle/cells_skill_s6i/: sk_nav_s6_32i (sk_nav_s6_32 + install as route step 1) alone on all 16 dev16
tasks, 1 pass (user 2026-10-28; the 7-task set: TASKS = WINNABLE7, PASSES = 2). Earlier: kaggle/cells_skill_s6 =
b57d56d (sk_nav_s6 3/16, sk_nav_s6_32 6/16). Earlier: kaggle/cells_skill_nav32 = 8750b35 (sk_nav_32 4/16, 387 s/task). Arms may differ only in
max_tool_calls. Earlier: kaggle/cells_skill_nav2 = 8220cc6 (sk_nav2 2/7, sk_nav2_32 3/7, pass 1 only). Earlier: kaggle/cells_skill_nav = 329307b (sk_nav 5 + 3 of 7). Earlier: kaggle/cells_skill_a5 = 3bef97a (sk_a5 3/16, sk_a5r 3/16).
Earlier: kaggle/cells_skill_a4p1 = 32f7f2a (sk_a4 2/16, sk_p1 6/32, sk_a2_t05 3/16). Earlier runs: kaggle/cells_skill_a3 = 6c5d224 (sk_a3 2/16), kaggle/cells_skill_a2 = 6216e2e
(sk_a2 7/32, sk_ad2 3/32), kaggle/cells_skill_ad = 333285f, kaggle/cells_skill_arms = 82c8d56.

    python3 scripts/make_skill_arms.py && python3 scripts/train/make_skill_arms_cells.py

After pass 1, an arm that solved EARLY_STOP_MAX or fewer tasks is dropped from pass 2; with none left the run ENDS BY
ITSELF (a cancelled saved version loses all output files). After every run, the log gets a DIGEST line from the model replies (survives a cancel):
reading-tool use (find / outline / show / note / pin), raw reads (cat, sed, grep, read_file), NOT SHOWN AGAIN
refusals, the call of the first edit, compactions, model seconds vs tool seconds per call; results/digest.jsonl too.

Conditions = mix's 64 earlier dev16 runs (rung 3e-3m): T0.2, 8 min, 28 calls, 80 turns, 2 tasks at once, so those
runs are the control (embedded per task; no new mix runs). PASS 1 = every arm once on all 16 tasks (48 runs) before
PASS 2 starts (early stopping: stop the session after pass 1 and the comparison is complete). Attempts are
"<arm>.<pass>" (job tag task#a<arm>.<pass>), so scripts/triage.py reads the run. Everything else is the test notebook
(kaggle/cells_test_31b): the combined-run sandbox setup (competition setup + pins + test deps for public tasks).

Inputs: as the test notebook, minus the adapter: the competition, the wheelhouse, the model google/gemma-4 ->
gemma-4-31b-it-qat-w4a16-ct, rodrigospalma/ood45-bugfix-split, rebench-new-cp312, the gold-check output
(test_deps_wheels). GPU L4x4, Python 3.12, INTERNET OFF.
"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/train"))
import make_gen_cells as G  # noqa: E402
from make_test_cells import must_replace  # noqa: E402

OUT = ROOT / "kaggle/cells_skill_r166"  # r166: LoRA data run 2 = sk_a2 x 3 passes, notebook 1 = r165 shard s2 (never ran) + 26 mix-unsolved tasks, notebook 2 = 66 mix-unsolved tasks (cells_skill_r166_s1 / _s2); r165: r165 (user 2026-11-25 "go with B" / "yes build step 1"): LoRA pass/fail data = sk_a2 alone x 4 passes on RTRAIN110 (110 rebench_new tasks, 97 repos), 4 shards (cells_skill_r165_s1..s4); r164: r164 (user 2026-11-25 "build A on 4 tasks 2 rich 2 fast, also increase total tools call"): sk_a2 vs sk_a2s3 (late hold 18 looks / 330 s + 36 calls; scripts/make_ska2s3.py) on the 4 mid-rate dev16; r163: r163 (user 2026-11-25 "build it with the one-time hold on the 8 tasks"): sk_a2 vs sk_a2s2 (card + one-time hold; scripts/make_ska2s2.py) on the 8 solvable dev16; r162: r162 (user 2026-11-25 "build it on the 8 tasks"): sk_a2 vs sk_a2s (the expected-result card; scripts/make_ska2s.py) on the 8 solvable dev16; r161: r161 (user 2026-11-24 "build it on the 8 tasks"): sk_a2 vs sk_a2p2g3 (frozen candidates, close only after real reads, empty-submit example, install keeps memory; scripts/make_ska2p2g3.py) on the 8 solvable dev16; r160 (user 2026-11-24 "we can increase the set for 8 and rerun the same notebook and see"): sk_a2 vs sk_a2p2g2 (Example 3 de-leaked) on the 8 solvable dev16; r159 (user 2026-11-24 "build it with all five fixes on the 4 tasks"): sk_a2 (control) vs sk_a2p2g2 (sk_a2p2 + the late gate with fixes 1-5, scripts/make_ska2p2g2.py) on r157's 4 tasks; r158 (user 2026-11-24 "before it build notebook of sk_a2p2 vs sk_a2 on 8 solvable tasks"): sk_a2 (control) vs sk_a2p2 on the 8 solvable dev16; r157 (user 2026-11-24 "build it, all three arms on the 4 tasks"): sk_a2 (control) vs sk_a2p2 (prompt: no experiments + failure examples) vs sk_a2p2g (+ late gate: READING CLOSED + EDIT CANDIDATES after STOP READING); r156: r156 (user 2026-11-24 "make only sk_a2 and sk_a2o2n and on 4 tasks only"): sk_a2 (control) vs sk_a2o2n (sk_a2 + YOUR EDIT / SAME LINES ELSEWHERE, no check, no EDIT MATERIAL); r155: r155 (user 2026-11-24 "build both on the 6 tasks"): sk_a2 (control) vs sk_a2c2 (a.py check takes the check code as a heredoc) vs sk_a2o (single agent + a.py outputs: YOUR EDIT / SAME LINES ELSEWHERE, EDIT MATERIAL at STOP READING) on r154's 6 tasks, ONE notebook run on both accounts = 2 passes, 18 runs per notebook. r154: ROOT / "kaggle/cells_skill_r154"  # r154 (user 2026-11-24 "build sk_a2c on the 6 tasks"): sk_a2 (control) vs sk_a2c (post-edit check.py + a.py check GREEN / RED) on 6 tasks, ONE notebook run on both accounts = 2 passes, 12 runs per notebook. r153: ROOT / "kaggle/cells_skill_r153"  # r153 (user 2026-11-24 "yes build"): sk_a2 (control) vs sk_a2ge4 (handover tool ends the gatherer stage; a.py check GREEN / RED) on r149's 4 tasks, ONE notebook run on both accounts = 2 passes, 8 runs per notebook. r152: ROOT / "kaggle/cells_skill_r152"  # r152 (user 2026-11-23 "build it with both"): sk_a2 (control) vs sk_a2ge3 (a.py-built BRIEF + the editor reads it first) on r149's 4 tasks, ONE notebook run on both accounts = 2 passes, 8 runs per notebook. r151: ROOT / "kaggle/cells_skill_r151"  # r151 (user 2026-11-23 "i think we need to make it faster" -> "build it"): sk_a2 (control) vs sk_a2ge2 (gatherer reads only, closed at 8 looks or 150 s) on r149's 4 tasks, ONE notebook run on both accounts = 2 passes, 8 runs per notebook. r150: ROOT / "kaggle/cells_skill_r150"  # r150 (user 2026-11-23 "build it" the gatherer -> editor): sk_a2 (control) vs sk_a2ge on r149's 4 tasks, ONE notebook run on both accounts = 2 passes, 8 runs per notebook. r149: ROOT / "kaggle/cells_skill_r149"  # r149 (user 2026-11-23 "build it, all 3 arms but on 4 only for each"): sk_a2 (control) vs sk_a2tm (a.py TESTS THAT USE template) vs sk_a2tr (+ test the rule) on 4 tasks, ONE notebook run on both accounts = 2 passes, 12 runs per notebook. r148: ROOT / "kaggle/cells_skill_r148"  # r148 (user 2026-11-23 "build it, all 4 arms on the 14 tasks"): sk_a2 (control, 240 s) vs sk_a2_60 (= sk_a2 at 60 s: the timeout test) vs sk_a2xt (sk_a2_60x at 240 s) vs sk_a2x2t (sk_a2_60x2 at 240 s) on the 14 discriminating fastapi / rich tasks, ONE notebook run on both accounts = 2 passes, 56 runs per notebook. r147: ROOT / "kaggle/cells_skill_r147"  # r147 (user 2026-11-23 "build it, all three arms with 240 timeout"): sk_a2x2t (control = sk_a2_60x2 at 240 s) vs sk_a2x2p (issue pinned via {problem_description}) vs sk_a2x2p40 (+ 40 calls) on the 8 solvable dev16, ONE notebook run on both accounts = 2 passes, 24 runs per notebook. r146: ROOT / "kaggle/cells_skill_r146"  # r146 (user 2026-11-23 "build it, K=4, 8 tasks on both notebooks"): sk_a2_60x2 (control) vs sk_a2_60xb (a.py READING CLOSED 4 reads after STOP READING until an edit) on the 8 solvable dev16, ONE notebook run on both accounts = 2 passes, 16 runs per notebook. r145: ROOT / "kaggle/cells_skill_r145"  # r145 (user 2026-11-23 "build it, 2 notebooks with sk_a2_60x as control on only 4 tasks ... same for both notebooks"): sk_a2_60x (control) vs sk_a2_60x2 (+ STOP READING / remaining-calls and repair-forward worked examples) on the 4 mid-rate dev16, ONE notebook run on both accounts = 2 passes. r144: ROOT / "kaggle/cells_skill_r144"  # r144 (user 2026-11-23 "drop the ctrl ... the worked example only ... full prompt reformatting"): sk_a2_60x alone on all 8 solvable dev16, ONE notebook run on both accounts = 2 passes; baseline = the 48 same-task sk_a2 / sk_a2_60 runs of r138-r143. r143: ROOT / "kaggle/cells_skill_r143"  # r143 (user 2026-11-23 "yes build it with 9 minutes"): sk_a2_60 (control) vs sk_a2_60t9 (9 min / 32 calls, prompt unchanged) on the 8 solvable dev16 in two shards, guard 0.9 h. r142: ROOT / "kaggle/cells_skill_r142"  # r142 (user 2026-11-23 "yes build sk_a2v32 with the 60s timeout"): sk_a2_60 (control = sk_a2 + 60 s command timeout) vs sk_a2v32 (sk_a2v + 32 calls + 60 s) on the 8 solvable dev16 in two shards, guard 0.8 h. r141: ROOT / "kaggle/cells_skill_r141"  # r141 (user 2026-11-22 "yes fail-first in, build it now"): sk_a2 (control) vs sk_a2r (replicate r140 5/8) vs sk_a2v (repro check, fail-first) on the 8 solvable dev16 in two shards, guard 1.2 h. r140: ROOT / "kaggle/cells_skill_r140"  # r140 (user 2026-11-22 "yes build it, 2 notebooks with sk_a2 control"): sk_a2 (control) vs sk_a2r (RUN IT after show) on the 8 solvable dev16 in two shards, guard 0.8 h. r139: ROOT / "kaggle/cells_skill_r139"  # r139 (user 2026-11-21 "only make the cells for sk_a2m and sk_a2 and drop the rest"): sk_a2 (control) vs sk_a2m on the 8 solvable dev16 in two shards, guard 0.8 h. r138 (built, not run): OUT = ROOT / "kaggle/cells_skill_r138"  # r138 (user 2026-11-21 "i need many arms man, as many as u can ... what more can we add to sk_a2"; replaces the unrun r136 / r137): sk_a2 (control) vs six one-change arms (sk_a2h, sk_a2p, sk_a2g, sk_a2t, sk_a2e, sk_a2_32) on the 8 solvable dev16 in r134's two shards, one per account, CONCURRENCY 2, guard 1.9 h. r137 (built, not run): OUT = ROOT / "kaggle/cells_skill_r137"  # r137 (user 2026-11-21 "if breaking my rule can produce arm, lets do that"; replaces the unrun r136): sk_a2 (control) vs sk_a2h (heredoc edits) vs sk_a2p (+ the public 0.22 call plan) on the 8 solvable dev16 in r134's two shards, one per account, CONCURRENCY 2, guard 1.1 h. r136 (built, not run): OUT = ROOT / "kaggle/cells_skill_r136"  # r136 (user 2026-11-21 "go"; control = sk_a2 from 11-21): sk_a2 (control) vs sk_a2h (heredoc edits) on the 8 solvable dev16 in r134's two shards, one per account, CONCURRENCY 2, guard 0.8 h. r135: OUT = ROOT / "kaggle/cells_skill_r135"  # r135 (user 2026-11-21 "go" on combining sk_a2 with the proven parts): sb1hl (control) vs sc1 on the 8 solvable dev16 in r134's two shards (_s1 / _s2, one per account = 1 pass per arm), CONCURRENCY 2, guard 0.8 h. r134: OUT = ROOT / "kaggle/cells_skill_r134"  # r134 (user 2026-11-20 "yes raise the tool calls with the example as well"): sb1hl (control) vs sb1hlc (36 calls + the Finalize note as an event) on the 8 solvable dev16 split in two balanced shards (_s1 / _s2, one per account = 1 pass per arm), CONCURRENCY 2, guard 0.8 h. r133: OUT = ROOT / "kaggle/cells_skill_r133"  # r133 (user 2026-11-20 "yes" to reopening the E tier with one arm): sb1hl (control) vs sbE7 (expectation by write_file after reading) on r128's 4 tasks, one notebook on both accounts = 2 passes, CONCURRENCY 2, guard 0.8 h. r132: OUT = ROOT / "kaggle/cells_skill_r132"  # r132 (user 2026-11-20 "i need first run on solvable 8 of dev16 please, only sb1hl"): sb1hl alone on R60_8, one notebook (both accounts = 2 passes), CONCURRENCY 2, guard 0.8 h. r131: OUT = ROOT / "kaggle/cells_skill_r131"  # r131 (user 2026-11-20 "on 2 tasks only please and yes build"): sb1hl (control) vs sb1hlf (fence-free examples) vs sbE6 (search -> expectation writer -> solver) on fastapi_15589 + fastapi_11194, one notebook on both accounts = 2 passes, CONCURRENCY 2, guard 0.6 h. r130: OUT = ROOT / "kaggle/cells_skill_r130"  # r130 (user 2026-11-20 "do what u proposed + few shot, on 2 tasks only please and yes besides sb1 and sb1hl"): sb1 vs sb1hl vs sbE5f (fence-free examples) vs sbE5w (+ write_file expectation) on fastapi_15589 + fastapi_11194, one notebook on both accounts = 2 passes, CONCURRENCY 2, guard 0.8 h. r129: OUT = ROOT / "kaggle/cells_skill_r129"  # r129 (user 2026-11-20 "we try both A and B with the rest of fixes and yes E3 + backslash alone as well"): sbE3b vs sbE4A (search stage) vs sbE4B (text-call / failing-test examples) on r128's 4 tasks, one notebook on both accounts = 2 passes, CONCURRENCY 2, guard 1.1 h. r128: OUT = ROOT / "kaggle/cells_skill_r128"  # r128 (user 2026-11-20 "yes build E3 alone on 4 tasks to run"): sbE3 alone (no control, user) on fastapi_15589, rich_3278, fastapi_11194, fastapi_12942, one notebook on both accounts = 2 passes, CONCURRENCY 2, guard 0.5 h. r127: OUT = ROOT / "kaggle/cells_skill_r127"  # r127 (user 2026-11-20 "skip the control, also i need only 2 task set"): sbE1 vs sbE2 vs sbX1 (expectation arms) on fastapi_15589 + rich_3278, one notebook on both accounts = 2 passes, CONCURRENCY 2, guard 0.6 h. r126: OUT = ROOT / "kaggle/cells_skill_r126"  # r126 (user 2026-11-20 "give it first then build the trial"): sb1hl (control) vs sb1hlg (T 1.0 / top_k 64) on the 4 tasks with the most maxed-thinking replies, one notebook on both accounts = 2 passes, CONCURRENCY 2, guard 0.8 h. r125: OUT = ROOT / "kaggle/cells_skill_r125"  # r125 (user 2026-11-20 "give me A and give me sample of 4 to test on"): sb1hl (control) vs sb1hlt (the edit runs the matching existing test file before and after) on 4 tasks, one notebook on both accounts = 2 passes, CONCURRENCY 2, guard 0.8 h. r124: OUT = ROOT / "kaggle/cells_skill_r124"  # r124 (user 2026-11-20 "yes do option 1, build the 12 task run"): sb1h (control) vs sb1hl on r117 / r118's 12 tasks, one notebook on both accounts = 2 passes, CONCURRENCY 2, guard 1.8 h. r123: OUT = ROOT / "kaggle/cells_skill_r123"  # r123 (user 2026-11-20 "yes please"): sb1h (control) vs sb1hl (sb1h-lite: prompt parts used in 0-1 of 94 runs dropped, fence-error event added) on r120's 4 tasks, one notebook on both accounts = 2 passes, CONCURRENCY 2, guard 0.8 h. r122: OUT = ROOT / "kaggle/cells_skill_r122"  # r122 (user 2026-11-20 "yes verify the timing and build it on sb1h"): sb1h (control) vs sbG (time-aware history-first gate: the first edit into a function early in the run is held and shows the function's last commits) on r120's 4 tasks, one notebook on both accounts = 2 passes, CONCURRENCY 2, guard 0.8 h. r121: OUT = ROOT / "kaggle/cells_skill_r121"  # r121 (user 2026-11-19 "yes build it with the changed lines filter"): sb1h (control) vs sbF2 (sbF whose history keeps only each commit's title and +/- lines) on r120's 4 tasks, one notebook on both accounts = 2 passes, CONCURRENCY 2, guard 0.8 h. r120: OUT = ROOT / "kaggle/cells_skill_r120"  # r120 (user 2026-11-19 "yes build it with the function window, 4 tasks"): sb1h (control) vs sbF (every edit prints the history of the enclosing function, 3 commits) on 4 tasks where the offline window check shows a useful commit, one notebook on both accounts = 2 passes, CONCURRENCY 2, guard 0.8 h. r119: OUT = ROOT / "kaggle/cells_skill_r119"  # r119 (user 2026-11-19 "yes build it with all 3 arms, keep them clean, only 4 tasks please, just proof of concept"): sb1h (control) vs sbA (history printed by every edit) vs sbB (history printed by every read, read_file removed) on 4 history-related mid-rate tasks, one notebook on both accounts = 2 passes, CONCURRENCY 2, guard 1.1 h. r118: ROOT / "kaggle/cells_skill_r118"  # r118 (user 2026-11-19 "yes build it with all 4 arms"): sb1 vs sb1h (heredoc edits) vs sb1hpp (+ presence 1.5) vs sb7h (one-call history) on r117's 12 tasks, one notebook on both accounts = 2 passes, CONCURRENCY 2, guard 2.8 h. r117: OUT = ROOT / "kaggle/cells_skill_r117"  # r117 (user 2026-11-18 "yes build it with those 12"): sb1 (control) vs sb1pp15 vs sb7g on 12 mid-rate tasks, one notebook on both accounts = 2 passes, CONCURRENCY 2, guard 2.1 h. r116: OUT = ROOT / "kaggle/cells_skill_sb7fh4"  # r116 (user 2026-11-18 "yes build sb7f ... few shot add example of solving it using history"): sb1 (control) vs sb7f on r112-r114's 4 tasks, one notebook on both accounts = 2 passes, CONCURRENCY 2, guard 0.8 h; r115: ROOT / "kaggle/cells_skill_pp4"  # r115 (user 2026-11-18 "yes build the penalty trial"): sb1 (control) vs sb1pp05 vs sb1pp15 (presence_penalty 0.5 / 1.5) on 4 long-reply tasks, one notebook on both accounts = 2 passes, CONCURRENCY 2, guard 1.1 h; r114: ROOT / "kaggle/cells_skill_sb7sh4"  # r114 (user 2026-11-18 "yes build the sb7 retry"): sb1 (control) vs sb7s (sb7 with a history stage that stops) on r112's 4 tasks, one notebook on both accounts = 2 passes, CONCURRENCY 2, guard 0.8 h; r113: ROOT / "kaggle/cells_skill_sb78h4"  # r113 (user 2026-11-18 "do both options, lets try both"): sb1 (control) vs sb7 (pinned up-front line history) vs sb8 (explore -> history -> editor) on r112's 4 tasks, one notebook on both accounts = 2 passes, CONCURRENCY 2, guard 1.1 h; r112: ROOT / "kaggle/cells_skill_sb6h4"  # r112 (user 2026-11-18 "yes build sb6 with those 4 tasks"): sb1 (control) vs sb6 (read -> git log -L on the lines to change -> edit) small first trial, one notebook on both accounts = 2 passes, CONCURRENCY 2, guard 0.8 h; r111: ROOT / "kaggle/cells_skill_sb1t12"  # r111 (user 2026-11-17 "yes build r111 sb1 vs sb1t"): sb1 (control) vs sb1t (thinking 2048) on 12 tasks where runs often end without an edit, mostly by time, one notebook on both accounts = 2 passes, CONCURRENCY 2, guard 1.9 h; r110: kaggle/cells_skill_sb5h12  # r110 (user 2026-11-17 "yes build it with the NEXT line and the trial"): sb1 (control) vs sb5 on r108's 12 tasks, one notebook on both accounts = 2 passes, CONCURRENCY 2, guard 1.8 h; r109: kaggle/cells_skill_sb4h12  # r109 (user 2026-11-17 "yes build sb4 with both fixes and the trial"): sb1 (control) vs sb4 on r108's 12 tasks, one notebook on both accounts = 2 passes, CONCURRENCY 2, guard 1.8 h; r108: kaggle/cells_skill_sb3h12  # r108 (user 2026-11-16 "yes build sb3 and the trial"): sb1 (control) vs sb3 (fixer -> history check stage) on 12 tasks where Step 0 shows history is relevant (8 test + 4 dev16), one notebook on both accounts = 2 passes, CONCURRENCY 2, guard 1.8 h; r107: kaggle/cells_skill_sb2sf  # r107 (user 2026-11-16 "round 2 of sb1 is useless until we verify what works ... test the other tasks on history on"): sb1 (control) vs sb2 on the 15 single-file test tasks, one notebook on both accounts = 2 passes, CONCURRENCY 2, guard 2.0 h; r106 (built, shelved by the user): kaggle/cells_skill_sb1tf8  # r106 (user 2026-11-16 "prepare another one ... other than multi file"): round 2 of the sb1 plan, sb1 (control) vs sb1t (thinking 2048) vs sb1f (T 1.0 / top_k 64) on 8 single-file test tasks with mixed outcomes, one notebook on both accounts = 2 passes, CONCURRENCY 2, guard 1.8 h; r105: kaggle/cells_skill_sb2mf  # r105 (user 2026-11-16 "lets go"): sb1 (control) vs sb2 (forced history stage) on the 9 test tasks whose real fix spans 2+ source files, one notebook on both accounts = 2 passes, CONCURRENCY 2, guard 1.4 h; r104: kaggle/cells_skill_sb1rt  # r104 (user 2026-11-16, plan approved): sa2 (control) vs sb1 on all 24 SWE-rebench test tasks, one notebook run on both accounts = 2 passes, CONCURRENCY 2, guard 2.75 h; r102 rebuilt: kaggle/cells_skill_sa2dev10  # r102 (rebuilt, user 2026-11-16 "I need 10 of dev16 the ones that can be solved and both notebooks same 10"): pub024 vs sa2 on the 10 dev16 tasks solved at least twice in the bank (= r80's set), the same notebook on both accounts = 2 passes, CONCURRENCY 2, guard 1.45 h; r103: kaggle/cells_skill_sa3mf9  # r103: sa2 vs sa3 on the 9 test tasks whose real fix spans 2+ source files, one notebook, 1 pass, CONCURRENCY 2, guard 1.3 h; r102: kaggle/cells_skill_sa2dev  # r102: pub024 vs sa2 on the full dev16, 2 notebooks of 8 (_s1, _s2), 1 pass, CONCURRENCY 2, guard 1.1 h; r101: kaggle/cells_skill_sa2rt12  # r101: pub024 vs sa2 on 12 of the 24 SWE-rebench test tasks (the 9 with mixed outcomes in r99 / r100 + 3 always solved as a regression guard), one notebook, CONCURRENCY 2, guard 1.65 h; r100: kaggle/cells_skill_sa1rt  # r100: pub024 vs sa1 on the 24 SWE-rebench test tasks, 2 notebooks of 12 (same split as r99), 1 pass, CONCURRENCY 2, guard 1.65 h; r99: kaggle/cells_skill_rtest  # r99: pub024 vs evidc on the 24 SWE-rebench test tasks (21 repos, never used for selection), 2 shards of 12 tasks (_s1, _s2), 1 pass, CONCURRENCY 2, guard 1.65 h from cell 2; r98b: kaggle/cells_skill_tb3b  # r98b: evidc vs evtb vs evtb9 on fastapi_14419 only, all three at once (CONCURRENCY 3, set in cell2), one account each (user: two accounts with 50 min of quota); r97: kaggle/cells_skill_tb2  # r97: kaggle/cells_skill_tb2  # r97: evidc (control) vs evtb (thinking 2048) vs evtb9 (+ 9 min / 33 calls) on the 2 easiest dev16 (user has 1h21 of quota), 1 pass, CONCURRENCY 2, time guard 0.3 h; r96: kaggle/cells_skill_exval8  # r96: evidc (control) vs evex_m on the 8 solvable dev16 (R60_8, as r91 / r94), 1 pass per notebook, CONCURRENCY 2, time guard 1.0 h; r95b: kaggle/cells_skill_ex3b  # r95b: second half of r95 without evbrief (closed): evidc vs evex_f vs evex_m on the same 4 mid-rate dev16, 1 pass, CONCURRENCY 2, time guard 0.85 h; r95: kaggle/cells_skill_ex4  # r95: evidc (control) vs evex_f (fixed solved example) vs evex_m (matched solved example) vs evbrief (think briefly on routine calls) on the 4 mid-rate dev16, 1 pass per notebook, CONCURRENCY 2, time guard 1.0 h; r94: kaggle/cells_skill_precval8  # r94: evidc (control) vs evidc_p on the 8 solvable dev16 (R60_8, as r91), 1 pass per notebook, CONCURRENCY 2, time guard 1.0 h; r93: kaggle/cells_skill_prec4  # r93: evidc (control) vs evidc_nt (past thoughts stripped) vs evidc_p (past changes in the evidence), 4 tasks, 1 pass per notebook, CONCURRENCY 2, time guard 0.85 h; r92: kaggle/cells_skill_struct4  # r92: evidc (control) vs evpipe / evloop / evroute (the three structures never built) on the 4 mid-rate dev16, 1 pass per notebook, CONCURRENCY 2, time guard 1.0 h; r91: kaggle/cells_skill_val8  # r91: evidc (control) vs evval on the 8 solvable dev16 (R60_8), 1 pass per notebook, CONCURRENCY 2, time guard 1.0 h; r90: kaggle/cells_skill_team4  # r90: evidc (control) vs evval (code-path tool with runtime values) vs evteam (two-fixer team + test vote) on 4 of r88's tasks where evidc is mid-rate, 1 pass, CONCURRENCY 2, time guard 0.85 h; r89: kaggle/cells_skill_samp6  # r89: evidc (control) vs evidc_g (Google's Gemma 4 sampling for the fixer) on r88's 6 tasks, 1 pass, CONCURRENCY 2, time guard 0.85 h; r88: kaggle/cells_skill_draft6  # r88: evidc (control) vs evdraft (draft-first stage) on 6 tasks with many no-patch runs, 1 pass, CONCURRENCY 2, time guard 0.85 h; r87: kaggle/cells_skill_plan4  # r87: evide (control) vs evide_nonum (call plan numbers taken out) vs evide_warn (few-shot: edit on the first harness budget warning) on the 4 mid-rate dev16, 1 pass, CONCURRENCY 2, time guard 0.85 h; r86: kaggle/cells_skill_conf6  # r86: evide vs evtrace on 6 mid-rate tasks outside dev16 that evtrace was never tuned on, 1 pass, CONCURRENCY 2, time guard 0.85 h; r85 final: kaggle/cells_skill_graph3  # r85 final (user 2026-11-12 "yes go for option 2"): evidefs vs evtrace vs evtrace2 vs evgraph on r84's 3 tasks (fastapi_14419, rich_3521, rich_4079), 1 pass, CONCURRENCY 2, time guard 0.85 h; first r85 build (superseded, not run): kaggle/cells_skill_trace4  # r85: evidefs (control) vs evtrace (r84 bundle, replication of the prompt effect) vs evtrace2 (few-shot fixes: every Python example through the code-path tool, how-to line, imports first) on the 4 mid-rate dev16, 1 pass, CONCURRENCY 2, cell 2 time guard 0.85 h (accounts with >= 2h20m quota); r84: kaggle/cells_skill_loc4  # r84: evidefs (control, the LB submission) vs evmap / evtrace / evall (location aids, scripts/make_r84_arms.py) on the 4 mid-rate dev16, 1 pass per notebook, CONCURRENCY 2; r82: kaggle/cells_skill_a8rc8  # r82: sq1c2a8rc (second look: 40/48 on e24 in one run) vs evidc (control) on the 8 dev16 tasks any agent ever solved, 2 passes per notebook (2 accounts = 4 passes), CONCURRENCY 2; r81: kaggle/cells_skill_fs4  # r81: pub024, combo1, evid3, evidc each next to its few-shot-fixed copy (scripts/make_fewshot_arms.py) on 4 tasks where these agents make the fixable form errors, CONCURRENCY 2; r80: kaggle/cells_skill_evide16  # r80: evidc (control) vs evidd vs evide on dev16 minus its 4 never-solved and 2 lowest-rate tasks (10 tasks), 1 pass per notebook, CONCURRENCY 2 (both passed r79); r79: kaggle/cells_skill_evide4, r79 small first trial: combo1, evidc, evidd, evide on the 4 mid-rate dev16, CONCURRENCY 2; r78b: kaggle/cells_skill_race3_4, r78b small first trial: combo1 vs race3 on the 4 mid-rate dev16, CONCURRENCY 1 (r78a: kaggle/cells_skill_gate4, built with ARMS ["combo1", "evidc", "evgate", "evgate1"], CONCURRENCY 2); r78a small first trial: combo1, evidc, evgate, evgate1 on the 4 mid-rate dev16 (r78b: kaggle/cells_skill_race3_4, combo1 vs race3, CONCURRENCY 1); r77: kaggle/cells_skill_evidc16, r77: combo1 (control) vs evidc on the full dev16 (evidc passed r76: 3/4 vs 0/4, +12 s); r76: kaggle/cells_skill_plus4, r76 small first trial: combo1 (control) vs nn32rcf, evidc, t7rc, allplus on the 4 mid-rate dev16; r75: kaggle/cells_skill_race4, r75 small first trial: combo1 (control) vs race2 on the 4 mid-rate dev16; r74: kaggle/cells_skill_en2_16, r74 combo1 (control) vs combo1en2 on the full dev16; r73: kaggle/cells_skill_combo3_16, r73 combo1 (control) vs combo1en vs combo2 on the full dev16; r72: kaggle/cells_skill_combo16, combo1 vs pub024 on the full dev16; r71: kaggle/cells_skill_kf2_16, kf2 vs pub024 on the full dev16; r70: kaggle/cells_skill_kf2c6, small first trial of kf2 / kf2c; r69: kaggle/cells_skill_kf6, small first trial of kf; r68: kaggle/cells_skill_ev4_16 (run twice on one account = 2 passes); r67: kaggle/cells_skill_ev4_6; r66: kaggle/cells_skill_ev16 (same notebook on two accounts = 2 passes); r65: kaggle/cells_skill_ctx6; r64: kaggle/cells_skill_fix6; r63: kaggle/cells_skill_mine4; r62: kaggle/cells_skill_hunch16; r60 small: kaggle/cells_skill_scout4, r60 ran: kaggle/cells_skill_scout8  # SHARDS set: one folder per shard, OUT + "_s1" ...
MODEL_NAME = "gemma-4-31b-it-qat-w4a16-ct"  # r49; r47 E4B: "gemma-4-e4b-it-qat-w4a16-ct"; cell 3 serves this; 31B runs: "gemma-4-31b-it-qat-w4a16-ct"
INFO_ARM = None  # r45: "sq1c2a6info"
ARMS = ["sk_a2"]  # r165 (data for the LoRA: sk_a2 alone); r164 ARMS = ["sk_a2", "sk_a2s3"]  # r164; r163 ARMS = ["sk_a2", "sk_a2s2"]  # r163; r162 ARMS = ["sk_a2", "sk_a2s"]  # r162; r161 ARMS = ["sk_a2", "sk_a2p2g3"]  # r161; r160 ARMS = ["sk_a2", "sk_a2p2g2"]  # r160 = r159; r158 ARMS = ["sk_a2", "sk_a2p2"]  # r158; r157 ARMS = ["sk_a2", "sk_a2p2", "sk_a2p2g"]  # r157 (scripts/make_ska2p2.py); r156 ARMS = ["sk_a2", "sk_a2o2n"]  # r156 (scripts/make_ska2o2n.py); r155 ARMS = ["sk_a2", "sk_a2c2", "sk_a2o"]  # r155 (scripts/make_ska2c2o.py); r154 ARMS = ["sk_a2", "sk_a2c"]  # r154 (scripts/make_ska2c.py); r153 ARMS = ["sk_a2", "sk_a2ge4"]  # r153 (scripts/make_ska2ge4.py); r152 ARMS = ["sk_a2", "sk_a2ge3"]  # r152 (scripts/make_ska2ge3.py); r151 ARMS = ["sk_a2", "sk_a2ge2"]  # r151 (scripts/make_ska2ge2.py); r150 ARMS = ["sk_a2", "sk_a2ge"]  # r150 (scripts/make_ska2ge.py); r149 ARMS = ["sk_a2", "sk_a2tm", "sk_a2tr"]  # r149 (scripts/make_ska2_tests.py); r148 ARMS = ["sk_a2", "sk_a2_60", "sk_a2xt", "sk_a2x2t"]  # r148 (scripts/make_ska2xt.py); r147 ARMS = ["sk_a2x2t", "sk_a2x2p", "sk_a2x2p40"]  # r147 (scripts/make_ska2x2_pin.py); r146 ARMS = ["sk_a2_60x2", "sk_a2_60xb"]  # r146 (scripts/make_ska2_60xb.py); r145 ARMS = ["sk_a2_60x", "sk_a2_60x2"]  # r145 (scripts/make_ska2_60x2.py); r144 ARMS = ["sk_a2_60x"]  # r144 (scripts/make_ska2_60x.py); r143 ARMS = ["sk_a2_60", "sk_a2_60t9"]  # r143 (scripts/make_ska2_60t9.py); r142 ARMS = ["sk_a2_60", "sk_a2v32"]  # r142 (scripts/make_ska2v32.py); r141 ARMS = ["sk_a2", "sk_a2r", "sk_a2v"]  # r141 (scripts/make_ska2v.py); r140 ARMS = ["sk_a2", "sk_a2r"]  # r140 (scripts/make_ska2r.py); r139 ARMS = ["sk_a2", "sk_a2m"]  # r139; r138 ARMS = ["sk_a2", "sk_a2h", "sk_a2p", "sk_a2g", "sk_a2t", "sk_a2e", "sk_a2_32", "sk_a2m"]  # r138 (+ sk_a2m, scripts/make_ska2m.py): scripts/make_ska2h.py, make_ska2p.py, make_ska2_arms.py; sk_a2_32 existing; r137 ARMS = ["sk_a2", "sk_a2h", "sk_a2p"]  # r137: scripts/make_ska2h.py, scripts/make_ska2p.py; r136 ARMS = ["sk_a2", "sk_a2h"]  # r136: scripts/make_ska2h.py; r135 ARMS = ["sb1hl", "sc1"]  # r135: scripts/make_sc1.py; r134 ARMS = ["sb1hl", "sb1hlc"]  # r134: scripts/make_sb1hlc.py; r133 ARMS = ["sb1hl", "sbE7"]  # r133: scripts/make_expect_e7.py; r132 ARMS = ["sb1hl"]  # r132: the base before an LB submission; r131 ARMS = ["sb1hl", "sb1hlf", "sbE6"]  # r131: scripts/make_sb1hlf.py, scripts/make_expect_e6.py; r130 ARMS = ["sb1", "sb1hl", "sbE5f", "sbE5w"]  # r130: scripts/make_expect_e5.py (+ the two bases); r129 ARMS = ["sbE3b", "sbE4A", "sbE4B"]  # r129: scripts/make_expect_e4.py; r128 ARMS = ["sbE3"]  # r128: scripts/make_expect_arms.py build_e3; r127 ARMS = ["sbE1", "sbE2", "sbX1"]  # r127: scripts/make_expect_arms.py; r126 ARMS = ["sb1hl", "sb1hlg"]  # r126: scripts/make_sb1hlg.py; r125 ARMS = ["sb1hl", "sb1hlt"]  # r125: scripts/make_sb1hlt.py; r124 ARMS = ["sb1h", "sb1hl"]  # r124: as r123; r123: scripts/make_sb1hl.py; r122 ARMS = ["sb1h", "sbG"]  # r122: scripts/make_sbG.py; r121 ARMS = ["sb1h", "sbF2"]  # r121: scripts/make_sbF.py sbF2; r120 ARMS = ["sb1h", "sbF"]  # r120: scripts/make_sbF.py; r119 ARMS = ["sb1h", "sbA", "sbB"]  # r119: scripts/make_sbab.py; r118 ARMS = ["sb1", "sb1h", "sb1hpp", "sb7h"]  # r118: scripts/make_sb1h.py; r117 ARMS = ["sb1", "sb1pp15", "sb7g"]  # r117: scripts/make_sb1pp.py, scripts/make_sb7g.py; r116 ARMS = ["sb1", "sb7f"]  # r116: scripts/make_sb7f.py; r115 ARMS = ["sb1", "sb1pp05", "sb1pp15"]  # r115: scripts/make_sb1pp.py; r114 ARMS = ["sb1", "sb7s"]  # r114: scripts/make_sb7s.py; r113 ARMS = ["sb1", "sb7", "sb8"]  # r113: scripts/make_sb78.py; r112 ARMS = ["sb1", "sb6"]  # r112: scripts/make_sb6.py; r111 ARMS = ["sb1", "sb1t"]  # r111: scripts/make_sb1.py (sb1t = sb1 with thinking_budget 2048); r110 ARMS = ["sb1", "sb5"]  # r110: scripts/make_sb5.py; r109 ARMS = ["sb1", "sb4"]  # r109: scripts/make_sb4.py; r108 ARMS = ["sb1", "sb3"]  # r108: scripts/make_sb3.py; r107 ARMS = ["sb1", "sb2"]  # r107: scripts/make_sb2.py; r106 ARMS = ["sb1", "sb1t", "sb1f"]  # r106: scripts/make_sb1.py; r105 ARMS = ["sb1", "sb2"]  # r105: scripts/make_sb2.py; r104 ARMS = ["sa2", "sb1"]  # r104; r102 rebuilt ARMS = ["pub024", "sa2"]  # r102 rebuilt; r103 ARMS = ["sa2", "sa3"]  # r103 (user 2026-11-16 "build sa3 while they run"): scripts/make_sa3.py; r102 ARMS = ["pub024", "sa2"]  # r102 (user 2026-11-16 "lets try it on dev16 first, both of them and if okay, submit"); r101 ARMS = ["pub024", "sa2"]  # r101 (user 2026-11-16 "do it but lets do it on only 12 of these tasks"): scripts/make_sa2.py; r100 ARMS = ["pub024", "sa1"]  # r100 (user 2026-11-15 "build it"): scripts/make_sa1.py; r99 ARMS = ["pub024", "evidc"]  # r99: calibrate the out-of-family test set against the LB (pub024 11/58, evidc 9 and 7/58); r97 ARMS = ["evidc", "evtb", "evtb9"]  # r97 (user 2026-11-13 "build that"): scripts/make_r97_arms.py; r96 ARMS = ["evidc", "evex_m"]  # r96 (r95 + r95b bar passed by evex_m: 4/8 vs evidc 2/8, pairs +3/-1, time +5 s in the refit); r95b ARMS = ["evidc", "evex_f", "evex_m"]  # r95b (user 2026-11-13 "i re run same notebook or try another sample?": same tasks, evbrief dropped); r95 ARMS = ["evidc", "evex_f", "evex_m", "evbrief"]  # r95 (user 2026-11-13 "build these yes"): scripts/make_r95_arms.py; r94 ARMS = ["evidc", "evidc_p"]  # r94 (user 2026-11-13 "I may run both on 8 solvable dev16 and see evidc vs evidc_p"); r93 ARMS = ["evidc", "evidc_nt", "evidc_p"]  # r93 (user 2026-11-13 "yes build this"): scripts/make_r93_arms.py; r92 ARMS = ["evidc", "evpipe", "evloop", "evroute"]  # r92 (user 2026-11-13 "build all actually and i will run them, test them on 4 samples all dev16, the solvable hard ones"): scripts/make_r92_arms.py; r91 ARMS = ["evidc", "evval"]  # r91 (user 2026-11-12 "yes we need another runs, get me the solvable 8 of dev16"): evval confirmation; r90 ARMS = ["evidc", "evval", "evteam"]  # r90 (user 2026-11-12 "i want to try everything"): scripts/make_r90_arms.py; r89 ARMS = ["evidc", "evidc_g"]  # r89 (user 2026-11-12 "lets go with 1"): scripts/make_r89_arms.py; r88 ARMS = ["evidc", "evdraft"]  # r88 (user 2026-11-12 "build it"): scripts/make_r88_arms.py; r87 ARMS = ["evide", "evide_nonum", "evide_warn"]  # r87 (user 2026-11-12 "yes 2 and 3"): scripts/make_r87_arms.py; r86 ARMS = ["evide", "evtrace"]  # r86 (user 2026-11-12 "build yes"): confirm evtrace (r84 + r85: 5/12 vs evidefs 1/12) against evide (evidefs's parent; the bank model puts evidefs below it, P 0.22) on unseen tasks; r85 final ARMS = ["evidefs", "evtrace", "evtrace2", "evgraph"]  # r85 final: each differs from the one before by one thing (prompt, few-shot tool fix, call graph); first r85 build ARMS = ["evidefs", "evtrace", "evtrace2"]  # r85 (user 2026-11-12 "favor few shot man if it helps and we try again, make this strategy see the fixes that can be applied, tool, prompt, etc."): scripts/make_r85_arms.py; r84 ARMS = ["evidefs", "evmap", "evtrace", "evall"]  # r84 (user 2026-11-12 "yes please and add any idea or arm that even has a slight chance of winning, all in"): each = evidefs + one location aid (MAP in the evidence, the code-path tool + its fixer prompt, both); r82 ARMS = ["evidc", "sq1c2a8rc"]  # r82 (user 2026-11-11 "lets re run it again on dev16 for 2 passes and see if this is luck or good and update the stats artifact"): sq1c2a8rc as it ran in r41 (bundle unchanged since b2c6fdb), evidc the same-run control; r81 ARMS = ["pub024", "pub024fs", "combo1", "combo1fs", "evid3", "evid3fs", "evidc", "evidcfs"]  # r81 (user 2026-11-11 "keep 1,2,5,6 in a clean notebook with the prompt fixes on subset of tasks the gain is expected and i will run it"); r80 ARMS = ["evidc", "evidd", "evide"]  # r80 (r79 bar: an arm passing goes to the full dev16 x 2 passes; evidc is the control and the LB-pending agent); r79 ARMS = ["combo1", "evidc", "evidd", "evide"]  # r79 (user 2026-11-11 "now lets continue building"; checkpoint agenda: richer evidence stage, small first trial vs evidc): scripts/make_evid_arms.py; evidd = evidc + whole-history search + name cleaning, evide = evidd + source lines for parameters; r78b ARMS = ["combo1", "race3"]  # r78b; r78a ARMS = ["combo1", "evidc", "evgate", "evgate1"]  # r78a (user 2026-11-11 "yes please do so and after the trial we see what to submit"): scripts/make_gate_arms.py; r78b ARMS = ["combo1", "race3"]; r77 ARMS = ["combo1", "evidc"]  # r77 (r76 bar: an arm passing both goes to the full dev16): evidc = cheap evidence stage (thinking off, 8 s script) + combo1; r76 ARMS = ["combo1", "nn32rcf", "evidc", "t7rc", "allplus"]  # r76 (user 2026-11-10 "lets make the agent of the nn32rc family + evid3 cheaper + sq1c2t7 on run_command in one run as well as trying to merge all the pluses of table in a single agent"): scripts/make_plus_arms.py; r75 ARMS = ["combo1", "race2"]  # r75 (user 2026-11-10 "lets test it yeah build"): race2 = scout -> ParallelAgent [engineer_a in /workspace, engineer_b in a git worktree]; the first submit ends the task (scripts/make_race_arm.py); small first trial; r74 ARMS = ["combo1", "combo1en2"]  # r74 (user 2026-11-10 "if it can be fixed with few shot, do it"): combo1en2 = combo1en + a few-shot example of the move after a refusal (edit_file, not read_file); r73 ARMS = ["combo1", "combo1en", "combo2"]  # r73 (user 2026-11-10 "make both please as new arms on the full dev16, so we have combo ctrl, combo1 + edit now, combo2"): combo1 is the control (no pub024 this run, user choice); scripts/make_combo_arm.py; r72 ARMS = ["pub024", "combo1"]  # r72 (user 2026-11-10 "get the best of agents into one"): combo1 = pub024 + garbled-call rule + /tmp line fix - 3 unused graph tools (scripts/make_combo_arm.py); r71 ARMS = ["pub024", "kf2"]  # r71 (user 2026-11-10 "lets go"): kf2 passed r70 (3 vs 2, -40 s; hint never triggered), full dev16 before any LB submission; r70 ARMS = ["pub024", "kf2", "kf2c"]  # r70 (user 2026-11-10 "yes do so and try to add checklist to this pub as well"): kf2 = pub024 + the garbled-call entry only (~110 tokens); kf2c = kf2 + a no-tool checklist stage kept in the system prompt (scripts/make_mine_arms.py ARMS_R70), same 6 tasks as r69; r69 ARMS = ["pub024", "kf"]  # r69 (user 2026-11-09 "build"): kf = pub024 + KNOWN TOOL FAILURES section (scripts/make_kf_arm.py); r68 ARMS = ["pub024", "evid4"]  # r68 (user 2026-11-09 "build"): evid4 passed r67 (5/6 vs evid3 3, pub024 3), full dev16; r67 ARMS = ["pub024", "evid3", "evid4"]  # r67 (user 2026-11-09 "yes build"): evid4 = evid3 + source lines + the definition's history, small first trial on the r65 tasks; r66 ARMS = ["pub024", "evid3"]  # r66 (user 2026-11-09 "build"): evid3 passed r65's bar (4 vs 3, +25 s), the bigger run; r65 ARMS = ["pub024", "evid3", "autochk3", "evchk"]  # r65 (user 2026-11-08 "build"): the evidence lines and the check note go into the fixer's system prompt via output_key (r64 lost them at compaction), scripts/make_mine_arms.py ARMS_R65; r64 ARMS = ["pub024", "evid2", "autochk2", "cap2k32"]  # r64 (user 2026-11-08 "build it"): r63 arms with their mechanism fixed (evidence refuses a 2nd call; checker thinks less; cap2k gets 32 calls); r63 ARMS = ["pub024", "hpub", "cap2k", "autochk", "evid1", "evhunch"]  # r63 (user 2026-11-08 "do so"): data-mining arms, scripts/make_mine_arms.py, small first trial; r62 ARMS = ["pub024", "hunch"]  # r62 (user rule 2026-11-08: the promising arm goes bigger): hunch passed the r60 bar (4 vs pub024 3, no patch 1 vs 4); r60 ARMS = ["pub024", "sc_none", "sc_tests", "sc_hist", "sc_both", "hunch"] # r60 (user 2026-11-08): scout -> fixer agents (scripts/make_scout_arms.py), the scout's quoted repo evidence in the fixer's system prompt; sc_none = fixer alone (structure control); 8 winnable dev16, 1 pass; r59 = kaggle/cells_skill_dev8rcn2: ["pub024", "nn32rcn2"]; r59 (user 2026-11-07): nn32rcn2 again before a possible LB submission, the 8 winnable dev16, 1 pass, pub024 control; r58 = kaggle/cells_skill_setup8b: ["pub024", "nn32rc3", "nn32rcn3", "sq1c2a8rcx3"]; r58 (user 2026-11-07): r57 with the setup agent no longer told to use run_command (it looped on it), same 8 tasks; r57 = kaggle/cells_skill_setup8: ["pub024", "nn32rc2", "nn32rcn2", "sq1c2a8rcx2"]; r57 (user 2026-11-07): setup agent installs the script first (r55/r56 skipped the install), same 8 tasks; r56 = kaggle/cells_skill_clockrc8: ["pub024", "sq1c2x", "sq1c2a8rcx"]; r56 (user 2026-11-07): the 8-min clock agents through run_command, same 8 tasks, pub024 control; r55 = kaggle/cells_skill_rc8: ["pub024", "nn32rc", "nn32rcn", "nn32rcs"]; r55 (user 2026-11-07): run_command + installed script, small set, pub024 control only; r54 = kaggle/cells_skill_filter26: ["pub024", "nn36p", "nn32", "nn36c"]; r54 (user 2026-11-06): filter rule after r52: no patch nn36p 2, then tie at 5, broken by mean wall (nn32 362, nn36c 394, nn36 400), on tasks not in the screen; r52 = kaggle/cells_skill_screen16: ["pub024", "pubclock", "nn36", "nn32", "nn36c", "nn36p"]; r52 screen (user 2026-11-06): separate arms on few tasks, then the best on bigger sets; r51 = kaggle/cells_skill_pubstop: ["pubstop", "pub024"]; r51 (user 2026-11-06): pub024 + stop 60 s after the last source edit, same 38 tasks; r50 = kaggle/cells_skill_srep8: ["srep8", "pub024"]; r50 (user 2026-11-06): srep7 with the reporter cut to 90 s and thinking 1024, detailed issues hand over at once, same tasks; r49 = kaggle/cells_skill_srep: ["srep7", "pub024"]; r49 (user 2026-11-05): the agent writes its own bug report first, vs the best fitting LB agent, on the short issues + full dev16, 1 pass; r47 = kaggle/cells_skill_dev16e4b: ["sq1c2a6e4b", "pub024e4b"]; r47 (user 2026-11-04): E4B for the small-model bonus: the clock agent vs the public agent, full dev16 x 2; r45 = kaggle/cells_skill_info38: ["sq1c2a6i", "sq1c2a6info"]; r45 (user 2026-11-04): same agent (sq1c2a6 + issue in the system prompt, so compaction cannot drop it), task text with the missing information added (info arm) vs as given; r44 = kaggle/cells_skill_e34rn: ["sq1c2a6rn", "sq1c2a6rnt"]; r44 (user 2026-11-04): a6rc + REPRO SHOWS NO BUG, with thinking 4096 / 2048, on e24 + the rest of dev16 = 34 tasks x 2; r43 = kaggle/cells_skill_dev16a6: ["sq1c2a6", "pub024"]; r43 (user 2026-11-04, after sq1c2a6 scored 0.12): head to head on the full dev16 x 2, tasks not picked for being solved; r42 = kaggle/cells_skill_e24a6c: ["sq1c2a6rc", "sq1c2a6c"]; r42 (user 2026-11-02): a6 + checklist with / without the issue text in the system prompt, repeat block without the /tmp scan, e24 x 2 (a6 r40 = 17.0 is the bar); r41 = kaggle/cells_skill_e24a8r: ["sq1c2a8ra", "sq1c2a8rc"]; r40 = kaggle/cells_skill_e24a6: ["sq1c2a6"] (user 2026-11-02, 6-min a8, e24 x 2; built with OUT/ARMS swapped); r38b (user 2026-11-02, second account, replaces r38): a8 + repeat block + issue in system prompt (ra) / + checklist (rc), e24 x 2; r39 = kaggle/cells_skill_e24a8: ["sq1c2a8"] (user 2026-11-02, stopped r37): sq1c2 8 min + event A only, e24 x 2; r38 = kaggle/cells_skill_e24f6r: ["sq1c2f6ra", "sq1c2f6rc"]  # r38 (user 2026-11-02, second account): f6 + repeat block + issue in the system prompt (ra) / + checklist file shown by the clock (rc), e24 x 2; r37 = kaggle/cells_skill_e24f6: sq1c2f6 (finish events, 6-min cap) alone, e24 x 2 passes (sq1c2 8-min history is the bar); r36 = kaggle/cells_skill_d40t6: sq1c2t6 alone on d40 (sq1c2 and sq1c2t7 timed out on the scorer); r35 = kaggle/cells_skill_e24t7: pub024 vs sq1c2t7 on e24, 1 pass; r34 = kaggle/cells_skill_d40t7: sq1c2 on 7 min, alone on d40 (score vs pub024 ~20/40 + LB time check); r33 pub024 x 2 on q12 = kaggle/cells_skill_p12; r32 = kaggle/cells_skill_c36 on q12: sq1c3 = reads through the clock, sq1c4 = thinking 2048, sq1c2 = control; r31 sq1c2 alone on e24 = kaggle/cells_skill_c24; sq1c2 = sq1c with positional_args (user 2026-10-30); r30 sq1c vs sq1 = kaggle/cells_skill_c12; sq1c = sq1 with the clock shell (user 2026-10-30), fresh sq1 control; r29 sq1 vs sq2 = kaggle/cells_skill_q12_s1..s4; sq1 = sq2 without the second attempt (user 2026-10-29); sq2 alone (r28 19/24) = kaggle/cells_skill_sq2; bo3 + sa2 (r27) = kaggle/cells_skill_bo3_sa2; bo3 alone = kaggle/cells_skill_bo3 (stopped after 8 tasks, 6 solved); e24x2 = pub024 vs sk_a2_32 (kaggle/cells_skill_e24x2); d40x2 (user: is pub024 really ahead?); u20 (r24) = kaggle/cells_skill_u20 with sk_fr2; s20 (r23) = kaggle/cells_skill_s20_fr2_pub; sk_fr2 alone = kaggle/cells_skill_s20_fr2; sk_fr = kaggle/cells_skill_s20_fr (r22 15/20); d40: sk_a2 = kaggle/cells_skill_d40 (17/40), sk_a2_32 = kaggle/cells_skill_d40_32 (18/40), pub024 = kaggle/cells_skill_d40_pub
# the winnable dev16 tasks: tier 1 (mix 55-95%) + tier 2 (14-35% over all arms); the other 9 were 0 in ~150 runs
WINNABLE7 = ["rich_3882", "fastapi_15589", "fastapi_11194", "rich_4079", "rich_3521", "fastapi_14419", "rich_3470"]
SPLITS = json.load(open(ROOT / "data/splits_public.json"))
# d40 (user 2026-10-29): the 8 winnable dev16 + val 16 + test 16 = 40 tasks; 8 tasks alone are +-2 noise per pass
SPLIT_OF = {t: k for k in ("dev16", "val", "test", "train") for t in SPLITS[k]}
# r99 (user 2026-11-15 "prepare me the 24 test notebook so i know before submitting how to evaluate my agents"): the
# SWE-rebench test split (24 tasks, 21 repos outside fastapi / rich; never used to train or to pick agents; in the attached
# task set = the verification output). All earlier selection was on fastapi / rich only and did not transfer to the LB.
RTEST24 = ["All-Hands-AI__openhands-resolver-123", "AzureAD__microsoft-authentication-library-for-python-730",
           "AzureAD__microsoft-authentication-library-for-python-795", "NVIDIA__hpc-container-maker-472",
           "Netflix-Skunkworks__policyuniverse-147", "Qiskit__qiskit-bot-29", "RDFLib__pySHACL-285", "cta-observatory__pyirf-193",
           "ftnext__diy-googledrive-operate-5", "geopandas__geopandas-3240", "googlefonts__glyphsLib-1015", "hgrecco__pint-pandas-264",
           "klen__peewee_migrate-203", "lightstep__lightstep-tracer-python-106", "lucianopaz__compress_pickle-28", "mesonbuild__meson-12210",
           "python-wheel-build__fromager-142", "stefmolin__data-morph-264", "terryyin__lizard-144", "terryyin__lizard-174",
           "terryyin__lizard-370", "tonioo__sievelib-113", "wemake-services__wemake-python-styleguide-2619", "whatshap__whatshap-501"]
assert len(RTEST24) == 24 and not set(RTEST24) & set(SPLIT_OF)
SPLIT_OF.update({t: "rtest" for t in RTEST24})
# r165 (user 2026-11-25 "go with B" -> "yes build step 1"): LoRA pass/fail data. The 110 rebench_new tasks (97 repos) the October
# generation (mix, T1.0, 1 run each) solved, minus every held-out test id (RTEST24 + data/rebench_test): sk_a2 x 4 passes each.
RTRAIN110 = ["ARM-software__mango-42", "Axelrod-Python__Axelrod-1458", "BQSKit__bqskit-267", "CrossGL__crosstl-95", "DCC-Lab__RayTracing-141", "DCC-Lab__RayTracing-258", "DanielSank__constraintula-14", "European-XFEL__EXtra-data-287", "European-XFEL__EXtra-data-375", "Hanaasagi__pymem-2", "IdentityPython__JWTConnect-Python-CryptoJWT-170", "Instagram__MonkeyType-318", "OSeMOSYS__otoole-236", "OpenSourceEconomics__estimagic-222", "PyCQA__pyflakes-745", "QuantEcon__QuantEcon.py-705", "RDFLib__rdflib-1044", "RDFLib__rdflib-2112", "ReactiveX__RxPY-357", "RemDelaporteMathurin__h-transport-materials-249", "ResearchObject__ro-crate-py-109", "ResearchObject__ro-crate-py-163", "TRoboto__Maha-103", "TeamGraphix__graphix-154", "TeamGraphix__graphix-225", "Wortmeister-HQ__zahlwort2num-6", "aio-libs__aiosmtpd-106", "algorand__pyteal-234", "ali-ramadhan__matplotloom-7", "amjith__fuzzyfinder-19", "angr__claripy-436", "arrow-py__arrow-1035", "arrow-py__arrow-986", "asottile__dead-204", "asottile__pyupgrade-545", "asottile__setup-cfg-fmt-54", "asottile__yesqa-44", "avilum__linqit-8", "barrust__pyspellchecker-132", "celery__billiard-372", "climlab__climlab-251", "conan-io__conan-4965", "daviddrysdale__python-phonenumbers-182", "deppen8__pandas-vet-127", "django__asgiref-196", "django__asgiref-211", "doccano__doccano-1557", "feder-observatory__stellarphot-311", "fgmacedo__python-statemachine-425", "frictionlessdata__frictionless-py-512", "gitpython-developers__GitPython-1687", "gouline__dbt-metabase-158", "joke2k__faker-1164", "juaAI__stationbench-41", "kaste__mockito-python-54", "keis__base58-46", "kinegratii__borax-23", "kjd__idna-112", "lipoja__URLExtract-138", "log2timeline__dftimewolf-612", "lyft__cartography-1087", "maciej-gol__tenant-schemas-celery-78", "manmartgarc__stochatreat-26", "marcosschroh__dataclasses-avroschema-835", "matchms__matchms-212", "matthewwithanm__python-markdownify-110", "matthewwithanm__python-markdownify-167", "microsoft__electionguard-python-189", "microsoft__electionguard-python-404", "mkdocs__mkdocs-3700", "mozilla__bleach-722", "mrkwjc__einsumt-2", "narwhals-dev__narwhals-1159", "nilearn__nilearn-4804", "numpy__numpydoc-429", "optuna__optuna-3545", "ovasquez__mkdocs-merge-18", "pckroon__pysmiles-28", "physiopy__phys2bids-189", "pre-commit__pre-commit-hooks-469", "prefab-cloud__prefab-cloud-python-62", "projectmesa__mesa-1439", "psf__pyperf-199", "pydap__pydap-423", "pydicom__pydicom-1256", "pydicom__pydicom-1562", "pystorm__pystorm-42", "python-metar__python-metar-149", "python-metar__python-metar-152", "python-visualization__folium-1428", "reata__sqllineage-90", "reframe-hpc__reframe-3058", "remix__partridge-69", "sayanarijit__expandvars-41", "scikit-hep__scikit-hep-333", "scipp__plopp-373", "scrapy__w3lib-192", "sdispater__pendulum-174", "sdispater__pendulum-593", "sealor__junkie-4", "sosw__sosw-343", "spulec__freezegun-161", "streamlink__streamlink-5844", "streamlink__streamlink-5908", "tefra__xsdata-400", "terrencepreilly__darglint-24", "tophat__syrupy-672", "wimglenn__advent-of-code-data-154", "wireservice__csvkit-800", "zalando-stups__senza-535"]
SPLIT_OF.update({t: "rtrain" for t in RTRAIN110})
# r166 (user 2026-11-26 "yes build the second data run on the unsolved tasks"): r165 notebook A and B both ran shard s1, so the 55
# shard-s2 tasks never ran; they go first, then 92 rebench_new tasks mix tried but never solved (not held out, not RTRAIN110),
# easiest level first (core d0, then d1). Notebook 1: s2 55 + 26 unsolved; notebook 2: 66 unsolved; 3 passes each.
RTRAIN166_N1 = ["ASPP__pelita-798", "BQSKit__bqskit-267", "CrossGL__crosstl-95", "DCC-Lab__RayTracing-141", "DCC-Lab__RayTracing-258", "DanielSank__constraintula-14", "DataDog__datadogpy-555", "Hanaasagi__pymem-2", "PyCQA__pyflakes-745", "QuantEcon__QuantEcon.py-705", "RemDelaporteMathurin__h-transport-materials-169", "ResearchObject__ro-crate-py-152", "Sage-Bionetworks__challengeutils-247", "TeamGraphix__graphix-225", "Wortmeister-HQ__zahlwort2num-6", "aai-institute__nnbench-171", "ali-ramadhan__matplotloom-7", "amjith__fuzzyfinder-19", "arrow-py__arrow-1035", "arrow-py__arrow-986", "asottile__dead-204", "auth0__auth0-python-273", "avilum__linqit-8", "awsdocs__aws-doc-sdk-examples-tools-39", "celery__billiard-372", "climlab__climlab-251", "daviddrysdale__python-phonenumbers-182", "dgasmith__opt_einsum-196", "django__asgiref-196", "feder-observatory__stellarphot-311", "fgmacedo__python-statemachine-425", "frictionlessdata__frictionless-py-512", "getsentry__sentry-python-3729", "gitpython-developers__GitPython-1687", "gmr__pamqp-52", "google__docker-explorer-64", "googleapis__google-resumable-media-python-290", "googleapis__python-datastore-115", "googleapis__python-spanner-316", "joke2k__faker-1416", "kaste__mockito-python-54", "kjd__idna-112", "log2timeline__dftimewolf-612", "lyft__cartography-1087", "maciej-gol__tenant-schemas-celery-78", "magpylib__magpylib-789", "matchms__matchms-212", "matthewwithanm__python-markdownify-167", "mkdocs__mkdocs-3700", "mozman__steputils-3", "mrkwjc__einsumt-2", "narwhals-dev__narwhals-1159", "nilearn__nilearn-4804", "optuna__optuna-3545", "ovasquez__mkdocs-merge-18", "pckroon__pysmiles-28", "pepkit__peppy-494", "physiopy__phys2bids-189", "pre-commit__pre-commit-hooks-469", "pre-commit__pre-commit-hooks-582", "projectmesa__mesa-1439", "pydicom__pydicom-1562", "pypa__twine-131", "python-metar__python-metar-149", "python-metar__python-metar-152", "python-visualization__folium-1428", "pyvisa__pyvisa-780", "radiasoft__pykern-408", "reata__sqllineage-90", "reframe-hpc__reframe-3058", "sayanarijit__expandvars-41", "scrapy__scrapy-5384", "scrapy__w3lib-192", "sdispater__pendulum-174", "serge-sans-paille__beniget-70", "sosw__sosw-343", "tefra__xsdata-400", "terrencepreilly__darglint-24", "tophat__syrupy-672", "wimglenn__advent-of-code-data-154", "wimglenn__advent-of-code-data-86"]
RTRAIN166_N2 = ["DHI__mikeio-427", "DakaraProject__dakara-base-63", "M0r13n__pyais-137", "PEtab-dev__libpetab-python-287", "PyCQA__flake8-1642", "PyCQA__flake8-1648", "RockefellerArchiveCenter__DACSspace-51", "Shoobx__mypy-zope-80", "SpikeInterface__spikeinterface-961", "adamjstewart__fiscalyear-9", "allo-media__text2num-113", "allo-media__text2num-96", "altair-viz__altair-2975", "arrow-py__arrow-1077", "asottile__pyupgrade-313", "asottile__pyupgrade-568", "aspuru-guzik-group__selfies-125", "bsatrom__py-conway-40", "canonical__charmcraft-1891", "conan-io__conan-13284", "dask__dask-11803", "devsnd__tinytag-171", "dimitarOnGithub__temporals-6", "enthought__traits-futures-255", "exxamalte__python-georss-qld-bushfire-alert-client-30", "frictionlessdata__frictionless-py-1137", "frictionlessdata__frictionless-py-983", "gaogaotiantian__coredumpy-61", "geomet__geomet-101", "gitpython-developers__GitPython-1224", "google__GiftStick-137", "google__mobly-328", "googleapis__python-api-core-178", "googleapis__python-api-core-546", "googleapis__python-cloud-core-100", "googleapis__python-pubsub-738", "holoviz__holoviews-5950", "karllark__dust_extinction-229", "levitsky__pyteomics-144", "lightkurve__lightkurve-1426", "lipoja__URLExtract-140", "makhidkarun__traveller_pyroute-58", "mkdocs__mkdocs-3010", "mkdocs__mkdocs-497", "mwaskom__seaborn-3451", "ncclient__ncclient-412", "physiopy__phys2bids-346", "ppizarror__pygame-menu-324", "ppizarror__pygame-menu-357", "pre-commit__pre-commit-hooks-480", "protolambda__remerkleable-21", "pymzml__pymzML-156", "pynamodb__PynamoDB-862", "python-metar__python-metar-125", "python-visualization__branca-90", "reata__sqllineage-550", "robotframework__SeleniumLibrary-1677", "scieloorg__xylose-91", "scikit-learn-contrib__imbalanced-learn-1115", "serge-sans-paille__beniget-78", "skypilot-org__skypilot-3792", "streamlink__streamlink-6439", "symbol-management__symbol-exporter-105", "tobymao__sqlglot-446", "vertexproject__synapse-3940", "zwicker-group__py-pde-683"]
SPLIT_OF.update({t: "rtrain" for t in RTRAIN166_N1 + RTRAIN166_N2})
TASKS = sorted(WINNABLE7 + ["rich_3180"] + SPLITS["val"] + SPLITS["test"])  # the 8 winnable only: sorted(WINNABLE7 + ["rich_3180"])
# d40 solved (user 2026-10-29, saves quota): only the d40 tasks that sk_a2 (r20) or sk_a2_32 (r21) solved = 20 tasks
SOLVED_D40 = sorted({r["instance_id"] for d in ("2026-10-29_skill_d40", "2026-10-29_skill_d40_32")
                     for r in map(json.loads, open(ROOT / f"data/results/{d}/results/gen_per_task.jsonl")) if r["resolved"]})
# u20 (user 2026-10-29): the other 20 d40 tasks (wrong or no patch in both r20 and r21), to see rescues; with a fresh
# sk_a2_32 control (those tasks were picked as failures, so a rerun regains some by luck)
D40 = sorted(WINNABLE7 + ["rich_3180"] + SPLITS["val"] + SPLITS["test"])
UNSOLVED_D40 = [t for t in D40 if t not in SOLVED_D40]
# e24 (user 2026-10-29): s20 + the u20 tasks solved by at least one arm in r24 = every d40 task ever solved (24)
SOLVED_U20 = sorted({r["instance_id"] for r in map(json.loads, open(ROOT / "data/results/2026-10-29_skill_u20/results/gen_per_task.jsonl"))
                     if r["resolved"]})
TASKS = sorted(SOLVED_D40 + SOLVED_U20)  # d40x2: D40, u20: UNSOLVED_D40, s20: SOLVED_D40
# q12 (user 2026-10-29, 4 accounts x 1.5 h quota): the 12 e24 tasks NOT solved in >= 8 of 9 earlier runs (the
# others are solved by every arm and cannot separate sq1 from sq2). Before: pub024 3, sk_a2_32 3, sa2 6, sq2 7.
Q12 = ["fastapi_11194", "fastapi_12942", "fastapi_14349", "fastapi_14419", "fastapi_14873", "fastapi_15589",
       "rich_3278", "rich_3506", "rich_3521", "rich_3676", "rich_4075", "rich_4079"]
# r45: tasks whose issue lacks what is needed. Reports: short issues with a linked report (data/info_experiment/gh/issues.json, public GitHub,
# title + first post, no comments; checkboxes dropped, each cut at 3000 characters). Tests: flagged tasks (a test string or new name that the gold patch
# adds and the issue never says), by hand without false flags; the notebook reads their added test lines from tasks.jsonl (never committed).
_GH = json.load(open(ROOT / "data/info_experiment/gh/issues.json"))
def _report(x):
    body = "\n".join(l for l in (x.get("body") or "").splitlines() if not l.lstrip().startswith(("- [", "<!--")))
    return f"# {x['title']}\n{body.strip()[:3000]}"
INFO_REPORTS = {t: "\n\n".join(_report(x) for x in g if "body" in x) for t, g in _GH.items() if any("body" in x for x in g)}
INFO_TESTS = ["fastapi_13786", "fastapi_14099", "fastapi_14258", "fastapi_14262", "fastapi_14479", "fastapi_14487", "fastapi_14609", "fastapi_14953", "fastapi_14962",
              "fastapi_14964", "fastapi_15030", "fastapi_15280", "fastapi_15588", "fastapi_15661", "fastapi_15800", "rich_3061", "rich_3105", "rich_3180", "rich_3930"]
assert not set(INFO_REPORTS) & set(INFO_TESTS)
_TEXT = {t["instance_id"]: t["problem_statement"] for t in map(json.loads, open(ROOT / "data/tasks.jsonl"))}
TASKS = sorted(set(SPLITS["dev16"]) | {t for k in ("val", "test", "train") for t in SPLITS[k] if len(_TEXT[t]) < 150})  # r49 short gradable issues + full dev16; r47 full dev16 = sorted(SPLITS["dev16"]); r45 = sorted(set(INFO_REPORTS) | set(INFO_TESTS)); r44 e24 + full dev16 = sorted(set(SOLVED_D40 + SOLVED_U20 + SPLITS["dev16"])); r43 full dev16 = sorted(SPLITS["dev16"]); r42 e24 = sorted(SOLVED_D40 + SOLVED_U20)  # r37 e24; r36 D40; r35 e24 = sorted(SOLVED_D40 + SOLVED_U20); r34 D40; Q12 = r32/r33; e24 = sorted(SOLVED_D40 + SOLVED_U20) (r31: sq1c2); Q12 = r29 / r30
# r52 screen: 15 tasks solved 10-90% of the time across all logged runs (6+ runs, pub024 included), where an agent can change the outcome, + rich_4077 (short issue). Picked, so only for filtering.
SCREEN16 = ["rich_3063", "rich_3180", "rich_3506", "rich_4075", "rich_3470", "rich_3521", "rich_4079", "fastapi_14419", "rich_3676", "fastapi_15589", "fastapi_12942", "rich_3278", "fastapi_11194", "fastapi_14873", "fastapi_14372", "rich_4077"]
TASKS = sorted(set(SPLITS["dev16"]) | {t for k in ("val", "test", "train") for t in SPLITS[k] if len(_TEXT[t]) < 150})
TASKS = sorted(set(TASKS) - set(SCREEN16))  # r54: the 38-task set minus the screen's tasks; r52: sorted(SCREEN16)
assert len(TASKS) == 26  # r54
R60_8 = sorted(WINNABLE7 + ["rich_3180"])  # the 8 tasks r60 ran on (second pass for these)
MID8 = ["fastapi_14349", "fastapi_14873", "fastapi_5624", "fastapi_12942", "rich_3278", "rich_3676", "rich_3480", "rich_3506"]  # not in r60, pooled solve rate 0.21-0.81 over >=12 runs (run_table)
TASKS = sorted(["cta-observatory__pyirf-193", "RDFLib__pySHACL-285", "Netflix-Skunkworks__policyuniverse-147", "terryyin__lizard-144", "lucianopaz__compress_pickle-28", "terryyin__lizard-370", "klen__peewee_migrate-203", "hgrecco__pint-pandas-264", "fastapi_11194", "rich_3278", "rich_3676", "rich_3506"])  # r117: 12 tasks solved 19-83% by all logged agents (8 never-picked test tasks + 4 dev16), none used to pick pp1.5
TASKS = sorted(["rich_3521", "geopandas__geopandas-3240", "fastapi_15589", "klen__peewee_migrate-203"])  # r119: r112-r116's 4 mid-rate tasks; the offline check (hist_at_edit_check.py) shows related history on their real-fix lines
TASKS = sorted(["klen__peewee_migrate-203", "rich_3521", "rich_3506", "fastapi_11194"])  # r120: the window check (hist_window_check.py) shows a useful commit after the first edit with the function window; sb1 bank 3/20, 4/16, 1/6, 2/6
TASKS = sorted(["cta-observatory__pyirf-193", "RDFLib__pySHACL-285", "Netflix-Skunkworks__policyuniverse-147", "terryyin__lizard-144", "lucianopaz__compress_pickle-28", "terryyin__lizard-370", "klen__peewee_migrate-203", "hgrecco__pint-pandas-264", "fastapi_11194", "rich_3278", "rich_3676", "rich_3506"])  # r124: r117 / r118's 12 tasks (sb1 / sb1h have 22-24 runs each there)
TASKS = sorted(["klen__peewee_migrate-203", "lucianopaz__compress_pickle-28", "rich_3676", "rich_3278"])  # r125: tasks with wrong fixes in r123 / r124 whose test file the name rule finds (test_auto, test_utils, test_traceback, test_ansi); bank sb1 family 5/33, 8/16, 2/6, 4/8
TASKS = sorted(["rich_3506", "rich_3521", "fastapi_11194", "klen__peewee_migrate-203"])  # r126: the tasks with the most maxed-thinking / never-edit runs (noedit_study.py: rich_3506 21 runs with a maxed reply, rich_3521 12, fastapi_11194 5 no-edit of 8, peewee 4)
TASKS = sorted(["fastapi_15589", "rich_3278"])  # r127: winnable-core small fixes with mid solve rates (46% / 47%) whose failures are mostly never-edit runs (58% / 67%); text describes the change / the behaviour
TASKS = sorted(["fastapi_15589", "rich_3278", "fastapi_11194", "fastapi_12942"])  # r128: r127's two + two more winnable-core small fixes (1 source file, 3-7 lines) with mid solve rates (task_anatomy 64% / 62%) whose failures are mostly never-edit runs (failure_study 36 of 41 / 9 of 10)
TASKS = sorted(["fastapi_15589", "fastapi_11194"])  # r130: the two tasks with the most expectation text-calls in r127-r129 (73% / 50%); fastapi_15589 also shows the largest sb1 vs heredoc-family gap in the bank (13/16 vs 1/2)
TASKS = sorted(["fastapi_15589", "fastapi_11194"])  # r131: as r130 (same-task comparison with r130's arms)
TASKS = sorted(R60_8)  # r132: the 8 solvable dev16 (as r91 / r94 / r96)
TASKS = sorted(R60_8)  # r144: the 8 solvable dev16 in one notebook (r134-r143 used them via SHARDS)
TASKS = sorted(["fastapi_14419", "fastapi_15589", "rich_3521", "rich_4079"])  # r145: the 4 mid-rate dev16 (as r95); r144 fails here: rich_3521 (undone / unapplied edit), rich_4079 (STOP READING ignored)
TASKS = sorted(R60_8)  # r146: the 8 solvable dev16 in one notebook (as r144)
TASKS = sorted(["fastapi_14419", "fastapi_15589", "rich_3521", "rich_4079", "fastapi_14349", "fastapi_12942", "rich_3278", "rich_3506", "fastapi_15588", "fastapi_14873", "rich_3676", "fastapi_14479", "fastapi_5624", "rich_3480"])  # r148: the 14 fastapi / rich tasks solved 15-85% of the time over the whole bank (dev16 4, val 5, test 3, train 2)
TASKS = sorted(["rich_3521", "rich_3480", "rich_3278", "fastapi_15589"])  # r149: two rich tasks where the TESTS THAT USE template fires (3521 split_cells, 3480 append), rich_3278 and fastapi_15589 (hidden tests check the rule: variants)
TASKS = sorted(["rich_3521", "rich_3480", "rich_3278", "fastapi_15589", "fastapi_14419", "rich_4079"])  # r154: r149's 4 + two mid-rate dev16 (fastapi_14419 35%, rich_4079 24% over the bank)
TASKS = sorted(["fastapi_14419", "fastapi_15589", "rich_3278", "rich_3521"])  # r156: the 4 r155 tasks where sk_a2 solved 1 of 2 (the most room to move either way)
TASKS = sorted(R60_8)  # r158: the 8 solvable dev16 (as r144 / r146); r157 = r156's 4
TASKS = sorted(["fastapi_14419", "fastapi_15589", "rich_3278", "rich_3521"])  # r159: r157's 4 (STOP READING fired in 4/8 p2g runs there)
TASKS = sorted(R60_8)  # r160: the 8 solvable dev16 (as r158)
TASKS = sorted(R60_8)  # r161: the 8 solvable dev16 (as r160)
TASKS = sorted(R60_8)  # r162: the 8 solvable dev16 (as r161)
TASKS = sorted(R60_8)  # r163: the 8 solvable dev16 (as r162)
TASKS = sorted(["fastapi_14419", "fastapi_15589", "rich_3521", "rich_4079"])  # r164: the 4 mid-rate dev16 (as r145), 2 fastapi + 2 rich
TASKS = sorted(RTRAIN110)  # r165: LoRA pass/fail data (sharded below)
TASKS = sorted(RTRAIN166_N1 + RTRAIN166_N2)  # r166 (sharded below)
# r133: TASKS = sorted(["fastapi_15589", "rich_3278", "fastapi_11194", "fastapi_12942"])  # r133: r128's 4 winnable-core tasks (sb1hl is 6/8 on fastapi_15589 + 11194 alone: little room to show a gain there)
# r116: TASKS = sorted(["rich_3521", "geopandas__geopandas-3240", "klen__peewee_migrate-203", "fastapi_15589"])  # r116: r112-r114's 4 tasks (same-task comparison with sb6 / sb7 / sb7s)
# r115: TASKS = sorted(["rich_3521", "geopandas__geopandas-3240", "fastapi_14419", "rich_4079"])  # r115: mid-rate tasks with the most model time in replies >= 60 s (sb1 bank: 70 / 42 / 34 / 25%)
# r112-r114: TASKS = sorted(["rich_3521", "geopandas__geopandas-3240", "klen__peewee_migrate-203", "fastapi_15589"])  # r112: 4 mid-rate tasks with related line history (Step 0 11-18; current line 24% / 22% / 19% / 47%)
# r111: TASKS = sorted(["rich_3521", "rich_3180", "geopandas__geopandas-3240", "fastapi_14419", "rich_3278", "rich_3506", "fastapi_15589", "fastapi_11194", "Netflix-Skunkworks__policyuniverse-147", "fastapi_14873", "rich_4079", "rich_3470"])  # r111: tasks with >= 2 solved and >= 2 no-edit runs in the current line (scripts/mine_bank/pre_edit_calls.py), time-bound ones first
# r108-r110: TASKS = sorted(["Netflix-Skunkworks__policyuniverse-147", "lucianopaz__compress_pickle-28", "tonioo__sievelib-113", "Qiskit__qiskit-bot-29", "wemake-services__wemake-python-styleguide-2619", "geopandas__geopandas-3240", "RDFLib__pySHACL-285", "klen__peewee_migrate-203", "fastapi_14419", "fastapi_15589", "rich_3521", "rich_4079"])  # r108: LIST 1 names a missing real-fix file (policyuniverse, compress_pickle, sievelib, qiskit-bot, fastapi_14419) or LIST 2 is related (wemake, geopandas, pySHACL, peewee_migrate, fastapi_15589, rich_3521, rich_4079); r107: TASKS = sorted(set(RTEST24) - set(["Netflix-Skunkworks__policyuniverse-147", "lucianopaz__compress_pickle-28", "AzureAD__microsoft-authentication-library-for-python-730", "ftnext__diy-googledrive-operate-5", "stefmolin__data-morph-264", "terryyin__lizard-174", "Qiskit__qiskit-bot-29", "python-wheel-build__fromager-142", "tonioo__sievelib-113"]))  # r107: the 15 single-file test tasks (RTEST24 minus r105's 9); r106: TASKS = sorted(["cta-observatory__pyirf-193", "RDFLib__pySHACL-285", "geopandas__geopandas-3240", "terryyin__lizard-144", "terryyin__lizard-370", "klen__peewee_migrate-203", "hgrecco__pint-pandas-264", "googlefonts__glyphsLib-1015"])  # r106: the 8 single-file test tasks with bank solve rates 17-92% (5/12, 5/12, 5/12, 8/12, 8/11, 2/12, 10/12, 11/12); r105: TASKS = sorted(["Netflix-Skunkworks__policyuniverse-147", "lucianopaz__compress_pickle-28", "AzureAD__microsoft-authentication-library-for-python-730", "ftnext__diy-googledrive-operate-5", "stefmolin__data-morph-264", "terryyin__lizard-174", "Qiskit__qiskit-bot-29", "python-wheel-build__fromager-142", "tonioo__sievelib-113"])  # r105: the 9 multi-file test tasks (as r103 / history_precheck.py); r104: TASKS = sorted(RTEST24)  # r104; r102 rebuilt: TASKS = ["fastapi_11194", "fastapi_14419", "fastapi_14487", "fastapi_15280", "fastapi_15589", "rich_3180", "rich_3470", "rich_3521", "rich_3882", "rich_4079"]  # r102 rebuilt: dev16 minus its 4 never-solved and 2 solved-once tasks (bank: 134/142 .. 2/67); r103: the 9 SWE-rebench test tasks whose real fix spans 2+ source files (pub024 2/18 there vs 17/30 on 1-file tasks); r102: sorted(SPLITS["dev16"])  # r102: the full dev16 (sanity check before an LB submission); r101: mixed-outcome tasks of r99 / r100 (9; outcomes of all four agents counted alike) + the 3 fastest always-solved; r99: sorted(RTEST24)  # r99: the SWE-rebench test split; r98b: sorted(["fastapi_14419"])  # r98b: where evidc's replies > 2,000 tokens take most model time; r97: sorted(["rich_3882", "fastapi_11194"])  # r97: sorted(["rich_3882", "fastapi_11194"])  # r97: the two easiest dev16 for evidc (13/13 at ~152 s, 11/13 at ~353 s; user: 1h21 of quota, "choose few easy tasks"): time is the main measure; r96: sorted(R60_8)  # r96: the 8 solvable dev16 (r95 bar); r95: sorted(["fastapi_15589", "fastapi_14419", "rich_3521", "rich_4079"])  # r95: the 4 mid-rate dev16 (small first trial rule); r94: sorted(R60_8)  # r94: the 8 solvable dev16 (user), as r91; r93: sorted(["fastapi_15589", "fastapi_14419", "fastapi_13920", "rich_3934"])  # r93: two mid-rate dev16 where the precedent names the real-fix function + two never-solved dev16 where it names the real-fix function (precedent_offline.py); r92: sorted(["fastapi_15589", "fastapi_14419", "rich_3521", "rich_4079"])  # r92: the 4 mid-rate dev16 (solvable, hard; user); r91: sorted(R60_8)  # r91: the 8 solvable dev16 (user); r90: sorted(["fastapi_14873", "fastapi_15589", "rich_3521", "rich_3676"])  # r90: r88's tasks where evidc is mid-rate over r88 + r89 (2/4, 2/4, 3/4, 1/4; fastapi_14419 4/4 and rich_4079 0/4 left out); r88: sorted(["fastapi_14419", "fastapi_15589", "rich_3521", "rich_4079", "rich_3676", "fastapi_14873"])  # r88: the 4 mid-rate dev16 + rich_3676 and fastapi_14873 (no patch common in the evidence family); r87: sorted(["fastapi_15589", "fastapi_14419", "rich_3521", "rich_4079"])  # r87: the 4 mid-rate dev16 (small first trial rule; many no-patch runs there); r86: sorted(["rich_3278", "fastapi_14873", "rich_3676", "fastapi_12942", "rich_3506", "rich_3480"])  # r86: non-dev16 tasks with a 31B solve rate of 20-70% over >= 10 runs (the 5 other solvable dev16 are near 0 / 100% for the evidence family: power 7% vs 24% here); r85 final: sorted(["fastapi_14419", "rich_3521", "rich_4079"])  # r85 final: r84's 3 tasks (pooled with r84; fits a 2h20m account); first r85 build: sorted(["fastapi_15589", "fastapi_14419", "rich_3521", "rich_4079"])  # r85 (as r84 full): the 4 mid-rate dev16; r84 small first trial: the 4 mid-rate dev16 (user rule 2026-11-08); r82: TASKS = sorted(["fastapi_11194", "fastapi_14419", "fastapi_15589", "rich_3180", "rich_3470", "rich_3521", "rich_3882", "rich_4079"])  # r82 (user chose this over the full dev16 x 2 at the same GPU time: power 44% vs 26% if sq1c2a8rc is as good as its e24 run, scripts/stats/expect_run.py): dev16 minus the 8 tasks no agent ever solved (fastapi_13920 0/57, 14258 0/59, 14306 0/57, 14487 0/65, 15280 0/65, 15800 0/59, rich_3468 0/59, rich_3934 0/59); r81: TASKS = sorted(["fastapi_14873", "fastapi_15589", "rich_3278", "rich_3676"])  # r81: where pub024 / combo1 / evid3 / evidc make the few-shot-fixable form errors most (runs with one: 57% / 37% / 50% / 92%) and the task is solved sometimes (43% / 49% / 56% / 25%); rich_3934 has the most but was never solved; r80: TASKS = sorted(set(SPLITS["dev16"]) - {"rich_3468", "fastapi_13920", "fastapi_14306", "fastapi_15800", "fastapi_14258", "rich_3934"})  # r80 (user 2026-11-11 "drop 2 more"): also the two lowest-rate tasks (fastapi_14258 1/65, rich_3934 1/65; evidc and evidd give them the same evidence); before (user "drop another 2"): dev16 minus all four never-solved tasks (fastapi_14306 0/61, fastapi_15800 0/65 added); first cut (user 2026-11-11 "drop 2 tasks please that are never solved of the 16 because of limited quota"): dev16 minus the two slowest never-solved tasks (rich_3468 0/65 runs, 476 s mean wall; fastapi_13920 0/61, 420 s; both 0 in evid3's full-history runs too); r80 first build: TASKS = sorted(SPLITS["dev16"])  # the full dev16 (12 of its tasks were not in r79); r79 / r78: TASKS = sorted(["fastapi_15589", "fastapi_14419", "rich_3521", "rich_4079"])  # r79, r78 small first trials; r77: TASKS = sorted(SPLITS["dev16"])  # r77: the full dev16 (12 of its tasks were not in r76); r75-r76: TASKS = sorted(["fastapi_15589", "fastapi_14419", "rich_3521", "rich_4079"])  # r75 small first trial: the 4 mid-rate dev16 (user rule 2026-11-08); r71-r74: TASKS = sorted(SPLITS["dev16"])  # r71: the full dev16 (not picked for kf2); r69/r70 TASKS = sorted(["fastapi_14873", "rich_3278", "fastapi_15589", "fastapi_12942", "rich_3676", "rich_4079"])  # r69: pub024 solved 13-64% of each and made the targeted tool mistakes in 58-100% of its runs (scripts/mine_bank/pertask.py); r68 TASKS = sorted(SPLITS["dev16"])  # r68; r67 = r65's tasks = sorted(["fastapi_11194", "fastapi_14873", "fastapi_15589", "fastapi_14419", "rich_3278", "rich_3521"]); r66 TASKS = sorted(SPLITS["dev16"])  # r66: the full dev16, not picked for being solved (4 of them were in r65); r64 / r65 = sorted(["fastapi_11194", "fastapi_14873", "fastapi_15589", "fastapi_14419", "rich_3278", "rich_3521"])  # r64: pub024 solved 27-71% of each historically (expect ~2.9 of 6; r63's 4 tasks gave 4/24 in all); r63 small first trial = sorted(["fastapi_15589", "fastapi_14419", "rich_3521", "rich_4079"])  # r63 small first trial: the 4 mid-rate dev16; r62: sorted(R60_8 + MID8), 16 tasks, pub024 vs hunch
assert all(x in SPLIT_OF for x in TASKS)
# r60 small: TASKS = sorted(["fastapi_15589", "fastapi_14419", "rich_3521", "rich_4079"])  # r60 small first trial (user 2026-11-08: first trials small, promising arms go bigger): the 4 mid-rate dev16 (solved ~20-40% historically; the easy and near-never tasks cannot separate arms); r59: the 8 winnable dev16 (r55-r58 had 6 of them + 2 val)
# r55-r58: TASKS = sorted(["fastapi_14419", "rich_3521", "rich_4079", "rich_3278", "fastapi_15589", "fastapi_12942", "fastapi_11194", "rich_3470"])  # r55: 8 screen tasks, solved 0-4 of 6 in r52
# one notebook per account: 3 tasks x 2 arms = 6 runs each; tasks dealt slow/fast by sq2's r28 time (snake order)
_BY_TIME = ["fastapi_12942", "fastapi_14419", "fastapi_14873", "fastapi_15589", "rich_3506", "rich_4079",
            "fastapi_11194", "rich_4075", "fastapi_14349", "rich_3521", "rich_3278", "rich_3676"]
_SHARDS4 = [sorted(_BY_TIME[k] for k in (i, 7 - i, 8 + i)) for i in range(4)]  # r29 / c12_s1..s4
assert sorted(sum(_SHARDS4, [])) == sorted(Q12)
SHARDS = None  # r103: one notebook; r102: two shards of 8 dev16 tasks; 2 x 8 dev16 tasks balanced by pub024 bank rates (1.61 / 1.38 expected solves per pass); r101: None, one notebook; r99 (user 2026-11-15 "make them 2 notebooks only") used two shards of 12: 12 tasks each = the first 4-shard deal merged 1+4 / 2+3 (mix solves 5 / 6); None before; r30
_R = sorted(RTRAIN110); random.Random(165).shuffle(_R)
SHARDS = [sorted(RTRAIN166_N1), sorted(RTRAIN166_N2)]  # r166: notebook 1 / notebook 2
SHARDS_R165 = [sorted(_R[k::2]) for k in range(2)]  # r165 (user: 'only 2 accounts ... each 10 hours'): 2 notebooks x 55 tasks x 3 passes (165 runs each, ~9.2 h at ~400 s wall, 2 at once); was 4 x 27-28 x 4
SHARDS_R144 = None  # r144: one notebook with all 8 tasks (run on both accounts); r134-r143: [sorted(["rich_3882", "fastapi_14419", "rich_4079", "rich_3470"]), sorted(["fastapi_11194", "fastapi_15589", "rich_3521", "rich_3180"])]  # r134: the 8 solvable dev16 in two shards balanced by evidc bank rates (1.79 / 1.83 expected solves per pass); one shard per account
# 1.5 h quota = 45 min wall on L4x4 (bills 2x): setup ~10 min; no new run after 0.5 h from cell 2 -> ends by ~42 min
STOP_H = 9.4  # r165: 165 runs per notebook, no new run after 9.4 h from cell 2 (setup included) -> ends by ~9.6 h, under the 10 h the user has per account; was 6.0; r164: 8 runs per notebook (as r159); r163: as r162; r162: as r161; r161: as r160 (60 / 63 min); r160: 16 runs per notebook (as r158: 62 / 55 min); r159: 1.2  # r159: 8 runs per notebook (2 arms x 4 tasks, 2 at once, ~420 s each ~ 0.5 h + setup); r158: 1.6  # r158: 16 runs per notebook (2 arms x 8 tasks, 2 at once, ~420 s each ~ 0.95 h + setup); r157: 1.4  # r157: 12 runs per notebook (3 arms x 4 tasks, 2 at once, ~420 s each ~ 0.7-0.8 h + setup); r156: 1.2, 8 runs per notebook (2 arms x 4 tasks, 2 at once, ~400 s each ~ 0.5 h + setup); r155: 1.6, 18 runs per notebook (3 arms x 6 tasks, 2 at once, ~400 s each ~ 1.0-1.1 h + setup); r154: 12 runs per notebook (2 arms x 6 tasks, 2 at once, ~400 s each ~ 0.7 h + setup); before: r150: 8 runs per notebook (2 arms x 4 tasks); r149: 12 runs per notebook (3 arms x 4 tasks, 2 at once, ~350 s each ~ 0.6-0.7 h + setup); r148: 56 runs per notebook (4 arms x 14 tasks, 2 at once, ~400 s each ~ 3.1-3.4 h + setup); r147: 24 runs per notebook (3 arms x 8 tasks, 2 at once, ~400 s each ~ 1.4-1.6 h + setup); r146: 16 runs per notebook (2 arms x 8 tasks, 2 at once, ~400 s each ~ 0.9-1.1 h + setup); r145: 8 runs per notebook (2 arms x 4 tasks); r144: 8 runs per notebook; r143: 8 runs per shard notebook, one arm runs to 9 min; r142: 8 runs per shard notebook; r141: 12 runs per shard notebook; r140: 8 runs per shard notebook; r139: 8 runs per shard notebook; r138 with sk_a2m: 2.1  # r138 with sk_a2m: 32 runs per shard notebook; r138 before sk_a2m: 1.9  # r138: 28 runs per shard notebook (7 arms x 4 tasks) at 2 at once (14 rounds, sk_a2 mean ~5 min) + setup ~0.2 h; r137: 1.1  # r137: 12 runs per shard notebook (3 arms x 4 tasks) at 2 at once (6 rounds of <= 8 min) + setup ~0.2 h; r136: 0.8  # r136: as r134 / r135; r135: 0.8  # r135: as r134; r134: 0.8  # r134: 8 runs per shard notebook (2 arms x 4 tasks) at 2 at once, sb1hlc may use up to 8 min per run + setup ~0.2 h; r133: 0.8  # r133: 8 runs per notebook at 2 at once (4 rounds of <= 8 min) + setup ~0.2 h; r132: 0.8  # r132: 8 runs per notebook at 2 at once (4 rounds of <= 8 min) + setup ~0.2 h; r131: 0.6  # r131: 6 runs per notebook at 2 at once (3 rounds of <= 8 min) + setup ~0.2 h; r130: 0.8  # r130: 8 runs per notebook at 2 at once (4 rounds of <= 8 min) + setup ~0.2 h; r129: 1.1  # r129: 12 runs per notebook at 2 at once (6 rounds of <= 8 min) + setup ~0.2 h; r128: 0.5  # r128: 4 runs per notebook at 2 at once (2 rounds of <= 8 min) + setup ~0.2 h; r127: 0.6  # r127: 6 runs per notebook at 2 at once (3 rounds of <= 8 min) + setup ~0.2 h; r126: 0.8  # r126: as r125; r125: 8 runs per notebook, as r120-r123; r124: 1.8  # r124: 24 runs per notebook at 2 at once (12 rounds of <= 8 min, ~1.5 h) + setup ~0.2 h, as r109 / r110; r123: 0.8  # r123: as r120-r122; r122: as r120 / r121; r121: as r120; r120: 8 runs per notebook at 2 at once (4 rounds of <= 8 min) + setup ~0.2 h, as r116; r119: 1.1  # r119: 12 runs per notebook at 2 at once (6 rounds of <= 8 min) + setup ~0.2 h, as r113 / r115; r118: 2.8  # r118: 48 runs per notebook at 2 at once (24 rounds of ~6.5 min) + setup ~0.2 h; r117: 2.1  # r117: 36 runs per notebook at 2 at once (18 rounds of ~7 min) + setup ~0.2 h; r116: 0.8  # r116: 8 runs per notebook; r115: 1.1  # r115: 12 runs per notebook, as r113; r114: 0.8  # r114: 8 runs per notebook, as r112; r113: 1.1  # r113: 12 runs per notebook at 2 at once (~6 rounds of <= 8 min) + setup ~0.2 h; r112: 0.8  # r112: 8 runs per notebook at 2 at once (~4 rounds of <= 8 min) + setup ~0.2 h; r111: 1.9  # r111: 24 runs per notebook on slower tasks (no-edit runs go to the 8-min cap); r110: 1.8  # r110: as r109 (24 runs per notebook); r109: as r108 (24 runs took ~1.5 h); r108: 1.8  # r108: 24 runs at ~3.3-3.5 min each at 2 at once ~1.4 h + setup ~0.2 h; r107: 2.0  # r107: 30 runs at ~3.3 min each at 2 at once (r104: 48 in 2.63-2.69 h) ~1.65 h + setup ~0.2 h; r106: 1.8  # r106: 24 runs, ~380 s agent + ~55 s overhead at 2 at once ~1.45 h + setup ~0.2 h; r105: 1.4  # r105: 18 runs, sb runs ~330-355 s at 2 at once ~1.0-1.1 h + setup ~0.2 h; r104: 2.75  # r104: 48 runs ~2.4-2.6 h of runs (r101: 24 runs in 1.15-1.27 h) + setup ~0.2 h; r102 rebuilt: 1.45  # r102 rebuilt: 20 runs ~1.2 h + setup ~0.2 h; r103: 1.3  # r103: 18 runs ~1.0 h + setup ~0.2 h; r102: 1.1  # r102: 16 runs ~0.85-0.9 h + setup ~0.2 h; r99: 1.65  # r99: no new run after 1.65 h from cell 2 (setup ~0.2 h + 24 runs at 2 at once ~1.4 h); r98 and before: None = 10.5 (whole-session runs); 0.5 for a 1.5 h-quota shard
PASSES = 3  # r165: 3 attempts per task (pass/fail pairs; 4 did not fit 2 x 10 h); r84 (small first trial; the same notebook on a second account = a second pass); r82: 2  # r82: 2 per notebook, run on both accounts = 4 passes; r81 and before: 1  # r49; r47: 2; r45: 1 pass, 2 arms; r37 (user: two passes for steadier estimates); r33 pub024 x 2: 2; bo3: one pass at concurrency 1 (the LB runs tasks one at a time)
CONCURRENCY = 2  # r84 single-sequence arms, 2 at once as r76-r82; r82 as r77 / r80 (dev16, 2 at once; sq1c2a8rc ran r41 at 2 at once too); r81 single-sequence arms, 2 at once; r80 as r77 (dev16, 2 at once); r79: single-sequence arms, 2 at once as r76-r78a; r78b CONCURRENCY = 1  # r78b race3: 1 so its two engineers share the GPU as on the scorer (r78a gate4: 2); r76: single-sequence arms, 2 at once as r72-r74; r75 CONCURRENCY = 1  # r75: 1 so race2's two branches share the GPU as on the scorer (one task at a time) and combo1 runs alone; r74 and before: 2  # sq2: as the single-agent e24 runs it is compared with (r25 pub024 14, sk_a2_32 15); bo3 used 1
PASS2_IF_BEATS = None  # e24x2: ("pub024", "sk_a2_32"); user (e24x2): pass 2 only if pass 1 of the first arm solved MORE than the second; None = off
EARLY_STOP_MAX = -1  # r45: one pass; r44: 12 of 34 (the 12 tasks every clock run solved; user: 3 was set for the hard dev16); r43: -1, off (user asked 2 passes; mix solves 3-4 of dev16, so 3 would drop arms); r42: 3; r33: -1 (off); user: after pass 1, an arm that solved 3 or fewer stops (mix: 3.67 per pass)


def arm_files(arm):
    base = ROOT / "submissions" / arm
    return {p.relative_to(base).as_posix(): p.read_text() for p in sorted(base.rglob("*")) if p.is_file()}


def gen_reference():
    """val/test: the 10-24 generation run (mix, T1.0, 15 min, 1 run each), re-graded on CPU: task -> solved."""
    g = json.load(open(ROOT / "data/results/2026-10-24_gen_combined/regrade.json"))
    ref = {t: int(g[t]["resolved"]) for t in sorted(TASKS) if t in g}
    mp = ROOT / "data/exemplars/raw/selfdistill/datasets_ziadsamer_gen-extra-all/metrics.jsonl"  # r99: mix T1.0 15 min on the rebench test split
    if mp.exists():
        for l in open(mp):
            m = json.loads(l)
            if m["instance_id"] in TASKS and m.get("split") == "test" and m["instance_id"] not in ref:
                ref[m["instance_id"]] = int(bool(m["resolved"]))
    return ref


def mix_reference():
    """Pure mix (arms mix, mix_r1, mix_r2) on dev16: task -> [solved, no patch, runs]."""
    dev = set(TASKS)
    ref = {}
    for f in sorted((ROOT / "data/results").glob("*/results/*/task_results.jsonl")):
        if f.parent.name not in ("mix", "mix_r1", "mix_r2"):
            continue
        for r in map(json.loads, open(f)):
            if r["instance_id"] in dev:
                x = ref.setdefault(r["instance_id"], [0, 0, 0])
                x[0] += bool(r["resolved"])
                x[1] += not (r.get("agent_patch_size") or 0)
                x[2] += 1
    return dict(sorted(ref.items()))


BLOCK = '''
# SKILL ARMS (scripts/train/make_skill_arms_cells.py): a dev16 task set, pass 1 before pass 2.
ATTEMPTS = {passes!r}  # passes; after pass 1 an arm with EARLY_STOP_MAX or fewer solved is dropped (none left: the run ends)
EARLY_STOP_MAX = {early_stop_max!r}
PASS2_IF_BEATS = {pass2_if_beats!r}  # (a, b): pass 2 runs only if a solved more than b in pass 1
ARMS = {arms!r}
ARM_FILES = {arm_files!r}
TASK_SET = {dev16!r}
MIX_REF = {mix_ref!r}  # mix (T0.2, 8 min, 2 at once) on these tasks: task -> [solved, no patch, runs]
GEN_REF = {gen_ref!r}  # val/test: mix at T1.0, 15 min, 1 run each (2026-10-24 generation run, re-graded): task -> solved
SPLIT_OF = {split_of!r}
_RB = dict(ROWS)  # r99: the attached task set's own tasks (SWE-rebench), loaded above
ROWS = {{}}
for l in open(DATA_DIR / 'tasks.jsonl'):
    r = json.loads(l)
    if r['instance_id'] in TASK_SET:
        _sp = SPLIT_OF[r['instance_id']]
        ROWS[r['instance_id']] = {{**r, 'src': 'public', 'level': _sp, 'domain': 'public', 'text_kind': 'public',
                                   'leak': False, 'unfair_names': [], 'env_partial': False, 'split': _sp}}
for _t in TASK_SET:  # r99: SWE-rebench tasks come from the task set (their snapshots and wheels are there; cell 4 routes by 'src')
    if _t not in ROWS and _t in _RB:
        ROWS[_t] = {{**_RB[_t], 'split': SPLIT_OF[_t]}}
_miss = sorted(set(TASK_SET) - set(ROWS))  # r165: tasks absent from the attached task set are skipped, not fatal
if _miss:
    print(f'SKIPPED {{len(_miss)}} tasks not in the attached task set: {{_miss}}')
assert len(ROWS) >= 0.75 * len(TASK_SET), f'too many tasks missing from the attached task set: {{_miss}}'
TASK_SET = sorted(ROWS)
print(f"SKILL ARMS: {{len(ROWS)}} tasks {{dict(Counter(SPLIT_OF[t] for t in ROWS))}} {{sorted(ROWS)}} | arms {{ARMS}} | {{ATTEMPTS}} passes | {{CONCURRENCY}} at once | "
      f"after pass 1, arms solving {{EARLY_STOP_MAX}} or fewer stop")
INFO_ARM = {info_arm!r}  # this arm's task text gets the missing information; the other arm sees the issue as given
INFO_REPORTS = {info_reports!r}
INFO_TESTS = {info_tests!r}
def info_text(iid):
    if iid in INFO_REPORTS:
        return "\\n\\n---\\nThe linked report from the project's issue tracker (title and first post):\\n\\n" + INFO_REPORTS[iid]
    if iid in INFO_TESTS:
        added = "\\n".join(l[1:] for l in ROWS[iid]['test_patch'].splitlines() if l.startswith('+') and not l.startswith('+++'))
        return "\\n\\n---\\nWhat the hidden tests contain (their added lines):\\n\\n" + added[:3000]
    return ''
def info_row(r, attempt):
    return {{**r, 'problem_statement': r['problem_statement'] + info_text(r['instance_id'])}} if INFO_ARM and attempt.split('.')[0] == INFO_ARM else r
if INFO_ARM:
    assert all(info_text(t) for t in ROWS), 'every task of the information test needs added text'
    print(f"INFO TEST: {{INFO_ARM}} | reports {{len(INFO_REPORTS)}}, test lines {{len(INFO_TESTS)}} | added characters, median {{sorted(len(info_text(t)) for t in ROWS)[len(ROWS) // 2]}}, max {{max(len(info_text(t)) for t in ROWS)}}")
SUB_ROOT = WORKING_DIR / 'submissions'
shutil.rmtree(SUB_ROOT, ignore_errors=True)
for arm, files in ARM_FILES.items():
    for rel, text in files.items():
        (SUB_ROOT / arm / rel).parent.mkdir(parents=True, exist_ok=True)
        (SUB_ROOT / arm / rel).write_text(text, encoding='utf-8')
    _ev = (SUB_ROOT / arm / 'eval_config.yaml').read_text()
    _cp = SUB_ROOT / arm / 'skills/agent/scripts/commands.txt'
    _cmds = _cp.read_text().split() if _cp.exists() else ['(no skill)']
    print(arm, '| tools', [l.split('#')[0].strip()[2:] for l in (SUB_ROOT / arm / 'agent.yaml').read_text().splitlines() if l.strip().startswith('- ')][:8],
          '| skill commands', _cmds, '| budgets', ' '.join(l.strip() for l in _ev.splitlines() if ':' in l and 'evaluation' not in l))
    assert any(('max_time_minutes: ' + m) in _ev for m in '9876'), 'arms run with the 8-minute limit (as mix\\'s dev16 runs), 7 or 6 (sq1c2t7, sq1c2t6), or 9 (r97 evtb9)'
'''

CELL5 = r'''# 5. SKILL ARMS SUMMARY (paste this output to Claude): per pass, per arm vs mix's 64 dev16 runs, per task.
rows = [json.loads(l) for l in open(PER_TASK)] if PER_TASK.exists() else []
mix_solved = sum(s / n for s, _, n in MIX_REF.values())
mix_nopatch = sum(p / n for _, p, n in MIX_REF.values())
print(f'{len(rows)} runs | {(time.time() - T_START) / 3600:.1f} h | mix reference per pass over these tasks: solved {mix_solved:.2f}, '
      f'no patch {mix_nopatch:.2f}')
for n in range(1, ATTEMPTS + 1):
    rs = [r for r in rows if r['attempt'].endswith(f'.{n}')]
    if not rs:
        continue
    print(f'\n== PASS {n}: {len(rs)} runs')
    for arm in ARMS:
        a = [r for r in rs if r['arm'] == arm]
        print('  ' + arm + ' by split: ' + ' | '.join(f"{sp} {sum(r['resolved'] for r in a if SPLIT_OF[r['instance_id']] == sp)}/"
              f"{sum(1 for r in a if SPLIT_OF[r['instance_id']] == sp)}" for sp in ('dev16', 'val', 'test', 'rtest'))
              + ' | reference: mix T0.2 8 min ' + ' '.join(f"{sp} {sum(s / n for t, (s, _, n) in MIX_REF.items() if SPLIT_OF.get(t) == sp):.1f}"
                                                       for sp in ('dev16', 'val'))
              + f" | gen T1.0 15 min test {sum(v for t, v in GEN_REF.items() if SPLIT_OF.get(t) in ('test', 'rtest'))}")
        print(f"  {arm:8} solved {sum(r['resolved'] for r in a):2}/{len(a):2} (mix {mix_solved:.1f}) | no patch "
              f"{sum(not r['patch_chars'] for r in a):2} (mix {mix_nopatch:.1f}) | ends {dict(Counter(r['end'] for r in a))} "
              f"| median tools {sorted(r['tool_calls'] or 0 for r in a)[len(a) // 2] if a else '-'}")
print('\nper task: mix solved/runs (no patch) | ' + ' | '.join(ARMS) + '   (S = solved, E = edited, 0 = no patch)')
for iid in sorted(ROWS):
    s, p, n = MIX_REF.get(iid, [0, 0, 0])
    cells = []
    for arm in ARMS:
        a = sorted((r for r in rows if r['arm'] == arm and r['instance_id'] == iid), key=lambda r: r['attempt'])
        cells.append(''.join('S' if r['resolved'] else ('E' if r['patch_chars'] else '0') for r in a) or '-')
    ref = f'mix {s}/{n} ({p})' if n else f"gen {'S' if GEN_REF.get(iid) else '-'}"
    print(f'  {iid:16} {SPLIT_OF.get(iid, "?"):5} {ref:12}  ' + '   '.join(f'{c:>4}' for c in cells))
dig = [json.loads(l) for l in open(RESULTS / 'digest.jsonl')] if (RESULTS / 'digest.jsonl').exists() else []
print('\nper arm, mean per run (from the model replies; see the DIGEST lines):')
for arm in ARMS:
    d = [x for x in dig if x['arm'] == arm]
    if d:
        m = lambda k: sum(x.get(k) or 0 for x in d) / len(d)
        fe = sorted(x['first_edit'] for x in d if x.get('first_edit'))
        print(f"  {arm:8} runs {len(d)} | a.py find {m('find'):.1f} outline {m('outline'):.1f} show {m('show'):.1f} "
              f"| replace {m('replace'):.1f} run {m('run'):.1f} failed edits {m('edit_fail'):.1f} "
              f"| callers shown {m('callers'):.1f} ping-pong {m('pingpong'):.1f} WHERE written {sum(1 for x in d if x.get('where_at'))}/{len(d)} "
              f"| plan {m('plan'):.1f} blocked {m('blocked'):.1f} debug flags {m('debug_flag'):.1f} "
              f"| raw reads {m('raw_read') + m('read_file'):.1f} | scripts/tests before edit {m('pre_edit_runs'):.1f} | reshown {m('reshown'):.1f} | banner runs "
              f"{sum(1 for x in d if x.get('banner') or x.get('stop_banner'))} | call 1 wrong "
              f"{sum(1 for x in d if x.get('call1_wrong'))} | pip {m('pip'):.1f} | repro {m('repro'):.1f} pytest {m('pytest'):.1f} | edited {len(fe)}/{len(d)}, median "
              f"first edit at call {fe[len(fe) // 2] if fe else '-'} | compactions {m('compactions'):.1f} | model "
              f"{m('model_s'):.0f}s + tools {m('tool_s'):.0f}s")
        jw = [x for x in d if x.get('winner_a') or x.get('winner_b') or x.get('winner_c')]
        if jw or any(x.get('judge_waits') for x in d):  # bo3: best of three
            for w in 'abc':
                ws_ = [x for x in jw if x.get('winner_' + w)]
                print(f"  {arm:8} JUDGE picked {w.upper()} in {len(ws_)} runs (solved {sum(1 for x in ws_ if x.get('resolved'))})")
            print(f"  {arm:8} judge reached in {len(jw)}/{len(d)} runs | waits per run {sum(x.get('judge_waits') or 0 for x in d) / len(d):.1f}")
        rv = [x for x in d if x.get('review_at')]
        if rv or any(x.get('fixer_submit') for x in d):  # sk_fr: fixer -> reviewer
            sv = lambda xs: sum(1 for x in xs if x.get('resolved'))
            print(f"  {arm:8} REVIEW reached {len(rv)}/{len(d)} (solved {sv(rv)}), fixer submitted itself "
                  f"{sum(1 for x in d if x.get('fixer_submit'))}, neither {sum(1 for x in d if not x.get('review_at') and not x.get('fixer_submit'))} "
                  f"| review at call median {sorted(x['review_at'] for x in rv)[len(rv) // 2] if rv else '-'} | reviewer replies "
                  f"{sum(x['review_calls'] for x in rv) / max(len(rv), 1):.1f}, edited in {sum(1 for x in rv if x.get('review_edits'))} runs")
req = WORKING_DIR / 'requests' / 'requests.jsonl'
print('request log:', f'{req.stat().st_size / 1e6:.0f} MB' if req.exists() else 'MISSING')
'''


DIGEST = r'''

# DIGEST (make_skill_arms_cells.py): per run (job task#a<arm>.<pass>), counted from the model replies as they come:
# what the agent did with its calls and where the time went. Cell 4 prints one line after each run (it stays in the
# log even if the session is cancelled) and appends it to results/digest.jsonl.
import collections, re
from google.adk.models import lite_llm as _ll

DIGEST = collections.defaultdict(collections.Counter)
_A_PY = re.compile(r'\.git/agent/a\.py\s+(\w+)')
_RAW = re.compile(r'(^|[;&|(]\s*)(cat|sed|head|tail|grep|nl|less|awk)\s|git grep|git show \S+:')


def _dump(o):
    if hasattr(o, 'model_dump'):
        try:
            return o.model_dump()
        except Exception:
            return {}
    return o if isinstance(o, dict) else {}


def _text(content):
    if isinstance(content, list):
        return ' '.join(str(_dump(c).get('text') or c) for c in content)
    return str(content or '')


def _digest(job, messages, resp, seconds):
    d = DIGEST[job]
    d['model_calls'] += 1
    first = _dump(messages[0]) if messages else {}
    review = first.get('role') == 'system' and 'You are the REVIEWER' in _text(first.get('content'))
    if review:  # sk_fr: the reviewer stage (fresh context) of a SequentialAgent [fixer -> reviewer]
        d['review_calls'] += 1
        if not d['review_at']:
            d['review_at'] = d['tool_calls'] + 1  # the first reviewer reply comes after this many tool calls
            d['last_prompt'] = 0  # its short fresh context is not a compaction
    d['model_ms'] += int(seconds * 1000)
    last = _dump(messages[-1]) if messages else {}
    if last.get('role') == 'tool':
        out = _text(last.get('content'))
        d['refused'] += 'NOT SHOWN AGAIN' in out
        d['reshown'] += 'ALREADY SHOWN' in out
        d['banner'] += 'NO EDIT YET' in out
        d['stop_banner'] += 'STOP READING' in out
        d['blocked'] += 'BLOCKED: ' in out
        d['debug_flag'] += 'DEBUG LINE IN YOUR DIFF' in out
        d['callers'] += 'CALLED FROM' in out
        d['pingpong'] += 'PING-PONG:' in out
        d['handoff_seen'] += 'PATCH IN PLACE' in out
        d['revert_lines'] += out.count('REVERT ')
        d['judge_waits'] += 'WAITING: Fixer' in out  # bo3: the judge asked Fixer A to come back
        _w = re.search(r'WINNER: ([ABC])\b', out)
        if _w:
            d['winner_' + _w.group(1).lower()] += 1
        d['edit_fail'] += any(k in out for k in ('FileEditError', 'old_string not found', 'REPLACE FAILED'))
    r = _dump(resp)
    usage = r.get('usage') or {}
    pt = usage.get('prompt_tokens') or 0
    if d['last_prompt'] and pt < 0.7 * d['last_prompt']:
        d['compactions'] += 1
    d['last_prompt'] = pt
    d['max_prompt'] = max(d['max_prompt'], pt)
    d['out_tokens'] += usage.get('completion_tokens') or 0
    msg = ((r.get('choices') or [{}])[0] or {}).get('message') or {}
    if msg.get('tool_calls') and 'WHERE:' in _text(msg.get('content')) + str(msg.get('reasoning_content') or '') and not d['where_at']:
        d['where_at'] = d['tool_calls'] + 1  # the call that came with the first WHERE / WHY / CHANGE lines
    for tc in msg.get('tool_calls') or []:
        fn = (tc or {}).get('function') or {}
        name, args = fn.get('name') or '?', fn.get('arguments') or ''
        try:
            a = json.loads(args) if isinstance(args, str) else (args or {})
        except Exception:
            a = {}
        d['tool_calls'] += 1
        n = d['tool_calls']
        edit = False
        if name == 'run_command':
            cmd = str(a.get('command', ''))
            subs = _A_PY.findall(cmd)
            for c in subs:
                d[c if c in ('find', 'outline', 'show', 'note', 'pin', 'impact', 'check', 'plan', 'replace', 'run', 'handover', 'review') else 'a_other'] += 1
            if not subs and _RAW.search(cmd):
                d['raw_read'] += 1
            if 'pytest' in cmd:
                d['pytest'] += 1
            if not d['first_edit'] and (('run' in subs) or (re.search(r'pytest|python3?\s+(-c\b|-\s*<<|-m\b|\S+\.py)', cmd)
                                                            and not subs)):
                d['pre_edit_runs'] += 1  # a script or test run before the first edit (solved 8/17 at 0-4, 2/11 at 5+)
            if re.search(r'\bpip\b', cmd):
                d['pip'] += 1
            if 'repro.py' in cmd:
                d['repro'] += 1
            edit = 'git apply' in cmd or 'sed -i' in cmd or ('.write' in cmd and '<<' in cmd) or 'replace' in subs
        elif name in ('edit_file', 'write_file'):
            path = str(a.get('filepath') or a.get('file_path') or a.get('path') or '')
            if '.git/agent/' in path:
                d['repro'] += 1
            else:
                d[name] += 1
                edit = True
        elif name == 'run_skill_script':
            d['install'] += 1
            d['install_at'] = d['install_at'] or n
        else:
            d[name] += 1
            if name == 'submit_patch' and not review and not d['review_at']:
                d['fixer_submit'] = 1  # the fixer submitted itself: the run ended as plain sk_a2
        if review and edit:
            d['review_edits'] += 1
        if n == 1 and name != 'run_skill_script':
            d['call1_wrong'] = 1
        if edit and not d['first_edit']:
            d['first_edit'] = n


_inner = _ll.LiteLLMClient.acompletion
if not getattr(_inner, '_digest', False):
    async def _acompletion_digest(self, model, messages, tools, **kwargs):
        t0 = time.time()
        resp = await _inner(self, model, messages, tools, **kwargs)
        try:
            _digest(JOB.get(), messages, resp, time.time() - t0)
        except Exception as e:  # never break a run over the digest
            DIGEST[JOB.get()]['digest_errors'] += 1
        return resp
    _acompletion_digest._digest = True
    _ll.LiteLLMClient.acompletion = _acompletion_digest


def digest_row(job, agent_s):
    d = DIGEST.get(job) or collections.Counter()
    model_s = d['model_ms'] / 1000
    n = max(d['tool_calls'], 1)
    keys = ('install', 'install_at', 'find', 'outline', 'show', 'note', 'pin', 'impact', 'check', 'a_other', 'raw_read',
            'read_file', 'pre_edit_runs', 'plan', 'blocked', 'debug_flag', 'replace', 'run', 'callers', 'pingpong', 'where_at', 'edit_fail', 'refused', 'reshown', 'banner', 'stop_banner', 'pip', 'call1_wrong', 'repro', 'pytest', 'edit_file', 'write_file', 'first_edit', 'compactions',
            'max_prompt', 'out_tokens', 'model_calls', 'tool_calls', 'get_status', 'submit_patch', 'digest_errors',
            'review_at', 'review_calls', 'review_edits', 'fixer_submit', 'handover', 'review', 'handoff_seen', 'revert_lines',
            'judge_waits', 'winner_a', 'winner_b', 'winner_c')
    row = {k: d[k] for k in keys}
    row.update(model_s=round(model_s), tool_s=round(max(agent_s - model_s, 0)),
               model_s_per_call=round(model_s / max(d['model_calls'], 1), 1),
               tool_s_per_call=round(max(agent_s - model_s, 0) / n, 1))
    return row


def digest_line(r):
    return (f"      DIGEST install@{r['install_at'] or '-'} | a.py find {r['find']} outline {r['outline']} show "
            f"{r['show']} note {r['note']} pin {r['pin']} | raw reads {r['raw_read']} read_file {r['read_file']} | "
            f"scripts/tests before edit {r['pre_edit_runs']} | a.py replace {r['replace']} run {r['run']} | failed edits "
            f"{r['edit_fail']} | navigator: callers {r['callers']} ping-pong {r['pingpong']} WHERE at call {r['where_at'] or '-'} | plan {r['plan']} blocked {r['blocked']} debug flags "
            f"{r['debug_flag']} | refused {r['refused']} reshown {r['reshown']} | banners {r['banner']}+{r['stop_banner']} stop | pip {r['pip']} | "
            f"edit_file/write_file {r['edit_file'] + r['write_file']}, first edit at call {r['first_edit'] or '-'} | "
            f"repro {r['repro']} pytest {r['pytest']} | compactions {r['compactions']} max prompt {r['max_prompt']} | "
            f"model {r['model_s']}s ({r['model_s_per_call']}s/call) tools {r['tool_s']}s ({r['tool_s_per_call']}s/call) "
            f"| out tokens {r['out_tokens']}" + (f" | JUDGE waits {r['judge_waits']}, winner " + ('A' if r['winner_a'] else 'B' if r['winner_b'] else 'C' if r['winner_c'] else 'none')
                                              if r['judge_waits'] or r['winner_a'] or r['winner_b'] or r['winner_c'] else '') + (f" | PATCH IN PLACE seen {r['handoff_seen']}x, a.py handover {r['handover']} review {r['review']}, REVERT lines {r['revert_lines']}" if r['handoff_seen'] or r['handover'] or r['review'] else '')
            + (f" | REVIEW at call {r['review_at']}, {r['review_calls']} replies, {r['review_edits']} edits"
                                              if r['review_at'] else (' | fixer submitted itself' if r['fixer_submit'] else '')) + (f" | DIGEST ERRORS {r['digest_errors']}" if r['digest_errors'] else ''))
print('DIGEST on: one line per run after its result line (results/digest.jsonl)')
'''


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    src, comb = ROOT / "kaggle/cells_gen", ROOT / "kaggle/cells_gen_combined"
    (OUT / "cell1.py").write_text((src / "cell1.py").read_text())

    c2 = G.CELL2.format(submission=G.submission(), embedded_prev=[], sample=[], sub_name="mix")
    mode_line = next(l for l in c2.splitlines() if l.startswith("MODE = "))
    c2 = c2.replace(mode_line, "MODE = 'skill_arms'  # skill arms on a dev16 task set (make_skill_arms_cells.py)")
    c2 = must_replace(c2, "CONCURRENCY = 6  # full / retry: trial 2026-10-21: 40.9 attempts/h at 6 vs 31.4 at 4\n",
                      f"CONCURRENCY = {CONCURRENCY}  # tasks at once (make_skill_arms_cells.py CONCURRENCY; the LB runs 1)\n")
    c2 = must_replace(c2, "STOP_NEW_TASKS_AFTER_H = 10.5  # Kaggle ends GPU sessions at 12 h; a task takes <= ~10 min\n",
                      f"STOP_NEW_TASKS_AFTER_H = {STOP_H or 10.5}  # = min(10.5, this account's GPU quota in hours / 2 - 0.4): L4x4 bills 2x,\n"
                      "# a run ends within 8 min, Kaggle ends sessions at 12 h; a killed run loses its output\n")
    c2 = must_replace(c2, "for p in sorted(glob.glob('/kaggle/input/**/results/gen_per_task.jsonl', recursive=True)) + ([str(PER_TASK)] if PER_TASK.exists() else []):\n",
                      "for p in ([str(PER_TASK)] if PER_TASK.exists() else []):\n")
    c2 = must_replace(c2, "ood.patch_harness()\n",
                      "from swegemma.harness import container_setup as _cs0\n"
                      "_HARNESS_INSTALL, _HARNESS_COMPAT = _cs0.install_test_dependencies, _cs0._is_wheel_compatible_py313  # public tasks\n"
                      "# like the LB (Docker exec_run attaches no stdin): commands of the local subprocess sandbox get none either;\n"
                      "# it inherited the notebook's open, silent stdin, so input() (rich_3882's Prompt.ask) hung to the 240 s timeout\n"
                      "import adk_eval_core.sandbox.subprocess_sandbox as _ss0\n"
                      "class _NoStdinSubprocess:\n"
                      "    def __getattr__(self, name):\n"
                      "        return getattr(subprocess, name)\n"
                      "    def Popen(self, *a, **k):\n"
                      "        k.setdefault('stdin', subprocess.DEVNULL)\n"
                      "        return subprocess.Popen(*a, **k)\n"
                      "_ss0.subprocess = _NoStdinSubprocess()\n"
                      "ood.patch_harness()\n")
    host = "print('host pytest plugins:', [Path(p).name for p in _host], '-> exit', _r.returncode, _r.stderr[-200:])\n"
    dev16 = sorted(TASKS)
    assert set(TASKS) <= set(SPLIT_OF)
    c2 = must_replace(c2, host, host + BLOCK.format(passes=PASSES, arms=ARMS, early_stop_max=EARLY_STOP_MAX, pass2_if_beats=PASS2_IF_BEATS, info_arm=INFO_ARM, info_reports=INFO_REPORTS, info_tests=INFO_TESTS, arm_files={a: arm_files(a) for a in ARMS}, dev16=dev16,
                                                    mix_ref=mix_reference(), gen_ref=gen_reference(),
                                                    split_of={t: SPLIT_OF[t] for t in dev16}))
    (OUT / "cell2.py").write_text(c2 + "\n" + G.sandbox_env())
    (OUT / "cell2c_public_setup.py").write_text((comb / "cell2c_public_setup.py").read_text())
    (OUT / "cell3.py").write_text(must_replace((src / "cell3.py").read_text(), "TARGET_MODEL_NAME = 'gemma-4-31b-it-qat-w4a16-ct'", f"TARGET_MODEL_NAME = {MODEL_NAME!r}"))  # vLLM as the scorer (LoRA on, no adapter)
    (OUT / "cell3b_request_logger.py").write_text((src / "cell3b_request_logger.py").read_text().replace(
        "(training data: tagged task#attempt)", "(skill arms: tagged task#a<arm>.<pass>)") + DIGEST)

    c4 = (comb / "cell4_run.py").read_text()
    for old, new in (
        ("elif MODE == 'prompt':",
         "elif MODE == 'skill_arms':  # one PHASE per pass (phases run one after another: pass 1 ends before pass 2);\n"
         "    # inside a pass, the first arm rotates from task to task\n"
         "    PHASES = [(CONCURRENCY, [(i, f'{ARMS[(k + j) % len(ARMS)]}.{n}') for k, i in enumerate(ORDER)\n"
         "                             for j in range(len(ARMS)) if (i, f'{ARMS[(k + j) % len(ARMS)]}.{n}') not in DONE_JOBS])\n"
         "              for n in range(1, ATTEMPTS + 1)]\n"
         "elif MODE == 'prompt':"),
        ("MANIFEST = discover_adapters(str(SUB_DIR), adapter_extensions=ALLOWED_ADAPTER_EXTENSIONS)\n",
         "MANIFESTS = {a: discover_adapters(str(SUB_ROOT / a), adapter_extensions=ALLOWED_ADAPTER_EXTENSIONS) for a in ARMS}\n"),
        ("EVAL_CFG = read_eval_config(SUB_DIR)\n",
         "EVAL_CFGS = {a: read_eval_config(SUB_ROOT / a) for a in ARMS}  # per arm (Evaluator below); r35: calls, time, turns may differ\n"
         "EVAL_CFG = EVAL_CFGS[ARMS[0]]\n"
         "_same = lambda c: {**c, 'max_tool_calls': 0, 'max_time_minutes': 0, 'max_turns': 0, 'timeout_seconds': 0}  # r148: the timeout may differ too (each arm's Evaluator gets its own; also the grading run's)\n"
         "assert all(_same(c) == _same(EVAL_CFG) for c in EVAL_CFGS.values()), "
         "'arms differ in budgets other than max_tool_calls / max_time_minutes / max_turns / timeout_seconds'\n"),
        ("display_mode='quiet', **EVAL_CFG))", "display_mode='quiet', **EVAL_CFGS[arm]))"),
        ("def evaluator_for(iid):\n", "def evaluator_for(iid, arm):\n"),
        ("results_dir=RESULTS / 'gen', submission_dir=SUB_DIR,", "results_dir=RESULTS / 'gen', submission_dir=SUB_ROOT / arm,"),
        ("adapter_manifest=MANIFEST,", "adapter_manifest=MANIFESTS[arm],"),
        ("evaluator_for(ORDER[0])  # fail before any task if the submission does not build into a config\n"
         "print('budgets', EVAL_CFG, '| adapters', list(MANIFEST.adapters))\n",
         "for _a in ARMS:  # fail before any task if a submission does not build into a config\n"
         "    evaluator_for(ORDER[0], _a)\n"
         "    print(_a, '| budgets', EVAL_CFGS[_a], '| adapters', list(MANIFESTS[_a].adapters))\n"),
        ("evaluator_for(iid), time.time()", "evaluator_for(iid, attempt.split('.')[0]), time.time()"),
        ("task, evaluator, w0 = as_task(r),", "task, evaluator, w0 = as_task(info_row(r, attempt)),"),
        ("row = {'instance_id': iid, 'attempt': attempt, 'mode': MODE,",
         "row = {'instance_id': iid, 'attempt': attempt, 'arm': attempt.split('.')[0], 'mode': MODE,"),
        ("    await asyncio.gather(*(one(i, a) for i, a in jobs))\n",
         "    await asyncio.gather(*(one(i, a) for i, a in jobs))  # jobs are queued in pass order (pass 1 first)\n"),
        # watchdog (2026-11-02: a run froze, 3 tasks in a row got 0 model calls in 480 s each): after 2 finished runs
        # in a row with 0 model calls start no new task, so the run ends by itself with its outputs saved
        ("STOP_AT = T_START + STOP_NEW_TASKS_AFTER_H * 3600\n",
         "STOP_AT = T_START + STOP_NEW_TASKS_AFTER_H * 3600\n"
         "DEAD_SERVER, ZERO_LLM = [False], [0]  # watchdog: 2 runs in a row with 0 model calls -> no new tasks\n"),
        ("                if time.time() > STOP_AT:\n                    return\n",
         "                if time.time() > STOP_AT or DEAD_SERVER[0]:\n                    return\n"),
        ("            DONE.append(row)\n",
         "            DONE.append(row)\n"
         "            ZERO_LLM[0] = ZERO_LLM[0] + 1 if row['llm_calls'] == 0 else 0\n"
         "            if ZERO_LLM[0] >= 2 and not DEAD_SERVER[0]:\n"
         "                DEAD_SERVER[0] = True\n"
         "                print('WATCHDOG: 2 runs in a row got 0 model calls (model server or sandbox stuck) -> no new '\n"
         "                      'tasks; the run ends by itself after the running ones (outputs saved)', flush=True)\n"),
    ):
        c4 = must_replace(c4, old, new)
    # a line when a pass ends; after pass 1 the run ends by itself unless an arm solved more than EARLY_STOP_MAX
    c4 = must_replace(c4, "    print('PHASE', json.dumps(PHASE_STATS[-1]), flush=True)\n",
                      "    print('PHASE', json.dumps(PHASE_STATS[-1]), flush=True)\n"
                      "    print('=' * 20, f'PASS {phase_no} COMPLETE: every arm ran once more on all {len(ROWS)} tasks', '=' * 20, flush=True)\n")
    c4 = must_replace(c4, "async def run_all():\n    for k, (conc, jobs) in enumerate(PHASES, 1):\n"
                          "        await run_phase(conc, jobs, k)\n",
                      "async def run_all():\n    global N_JOBS\n    for k, (conc, jobs) in enumerate(PHASES, 1):\n"
                      "        await run_phase(conc, jobs, k)\n"
                      "        if DEAD_SERVER[0]:  # watchdog fired: no further pass\n"
                      "            break\n"
                      "        if k == 1 and len(PHASES) > 1:  # per arm: only arms above EARLY_STOP_MAX get pass 2\n"
                      "            per_arm = {a: sum(r['resolved'] for r in DONE if r['arm'] == a and r['phase'] == 1) for a in ARMS}\n"
                      "            _cond = globals().get('PASS2_IF_BEATS')\n"
                      "            if _cond and per_arm[_cond[0]] <= per_arm[_cond[1]]:\n"
                      "                print(f'PASS 2 SKIPPED: pass 1 solved {per_arm}; {_cond[0]} did not beat {_cond[1]} -> '\n"
                      "                      'the run ends here (outputs saved)', flush=True)\n"
                      "                break\n"
                      "            keep = [a for a in ARMS if per_arm[a] > EARLY_STOP_MAX]\n"
                      "            if not keep:\n"
                      "                print(f'EARLY STOP: pass 1 solved {per_arm}, no arm above {EARLY_STOP_MAX} -> pass 2 skipped, '\n"
                      "                      'the run ends here (outputs saved)', flush=True)\n"
                      "                break\n"
                      "            dropped = [a for a in ARMS if a not in keep]\n"
                      "            PHASES[1:] = [(c, [(i, at) for i, at in js if at.split('.')[0] in keep]) for c, js in PHASES[1:]]\n"
                      "            N_JOBS = len(DONE) + sum(len(js) for _, js in PHASES[1:])\n"
                      "            print(f'pass 1 solved {per_arm}: pass 2 runs {keep}' + (f'; dropped {dropped} '\n"
                      "                  f'({EARLY_STOP_MAX} or fewer)' if dropped else ''), flush=True)\n")
    # the DIGEST line after each run's result line (cell 3b counts it from the model replies)
    c4 = must_replace(c4, "                  + (f\"\\n      err: {row['error'][:200]!r}\" if row['end'] not in ('ok', 'time', 'tool_budget') else ''),\n"
                          "                  flush=True)\n",
                      "                  + (f\"\\n      err: {row['error'][:200]!r}\" if row['end'] not in ('ok', 'time', 'tool_budget') else ''),\n"
                          "                  flush=True)\n"
                          "            dg = {'job': f'{iid}#a{attempt}', 'instance_id': iid, 'arm': row['arm'], 'attempt': attempt,\n"
                          "                  'resolved': row['resolved'], 'end': row['end'], 'patch_chars': row['patch_chars'],\n"
                          "                  **digest_row(f'{iid}#a{attempt}', row['agent_s'])}\n"
                          "            print(digest_line(dg), flush=True)\n"
                          "            with open(RESULTS / 'digest.jsonl', 'a', encoding='utf-8') as fh:\n"
                          "                fh.write(json.dumps(dg) + '\\n')\n")
    (OUT / "cell4_run.py").write_text(c4)
    (OUT / "cell5_summary.py").write_text(CELL5)
    print("wrote", OUT.relative_to(ROOT), sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    if SHARDS:
        base = OUT
        for k, part in enumerate(SHARDS, 1):
            OUT, TASKS = base.with_name(f"{base.name}_s{k}"), part
            main()
    else:
        main()
