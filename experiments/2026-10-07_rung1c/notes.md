# 2026-10-07 — Rung 1c: 1a (unchanged, control) vs 1b round 3 (commit 626536b)

**Setup:** same notebook, L4×4, same 4 tasks; configs 1a + 1b only. 1a prompts identical to rung-1b (30a8c5b).
Raw results: `data/results/2026-10-07_rung1c/` (gitignored).

**Score:** 1a **1/4** (same prompts scored 3/4 in rung-1b), 1b 1/4 (was 2/4). Both solved only rich_3882.

## Main lesson: run-to-run noise is as large as our effects
Identical 1a config: rung-1b 3/4 → rung-1c 1/4 (fastapi_15589 solved → timeout; rich_3470 solved → empty patch).
With 4 tasks × 1 run at temperature 1.0, a ±2-task swing is luck. No config comparison so far is conclusive.
→ D13 (more tasks) and repeated runs become the priority; D10 (temperature) matters for variance.

## Failure patterns (all prompt-fixable, all new)
A. **Malformed edit_file arguments** (1a fastapi_15589, rich_3470): old_string's code was split into junk keys
   (e.g. 'for key in received_params.keys()') → "missing old_string" error → the identical call retried 9× → timeout.
   12 malformed edit_file calls in 1a this run (1 in rung-1b). Same family as the start_line" read_file bug.
B. **Self-revert to an empty diff** (1a and 1b rich_3470): the first edit broke test_capture_and_record; the agent
   (1b: orchestrator told the executor) reverted it completely and submitted an empty patch (patch_size 0).
C. **"No change needed"** (1b fastapi_15589): a wrong repro script "showed" the behaviour already worked; the
   orchestrator submitted an empty patch without calling the executor (Overthinking paper's premature disengagement).

## Round-3 fixes (1b): what worked
- Fix A (sed instead of read_file ranges): read_file calls 56 → 5, malformed read args 17 → 0, no overflow.
- Verifier gave a real FAIL with real test output on rich_3470 (but the orchestrator answered with a full revert, B).
- Fix C (one helper call per reply) only partly obeyed: replies with >1 tool call 12 → 5.

## Candidate next changes
- A: "if edit_file reports a missing parameter, do not retry the same call: use a shorter old_string (1–3 lines)";
  fallback edit via run_command with a python heredoc doing one exact str.replace.
- B: "never revert your change to nothing; if a test breaks, adjust the change. An empty diff is never correct."
- C: "every task needs a source change; if your repro shows no bug, the repro is wrong."
- Evaluation: more tasks / repeated runs before comparing configs.
