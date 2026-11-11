Run-bank mining (2026-11-09). `python3 -I scripts/mine_bank/extract.py OUT.jsonl` builds one row per run from every
data/results/*/requests/requests.jsonl (outcome + every tool call with args, result head and timing); the other
scripts read that file (`python3 -I scripts/mine_bank/X.py OUT.jsonl [arm]`; garble.py, order.py, longreq.py read the
results folders directly). Results are written up in docs/PLAN.md, "MINING 2026-11-09b".

Added 2026-11-10 (docs/PLAN.md "MINING 2026-11-10b"; these read data/results/2026-1*-*/ directly, run from the repo root):
- think_share.py: share of output characters and model time that is thinking, by thinking budget.
- issue_gone.py: runs whose issue text was compacted away; first edit with / without the issue in context, raw and
  controlled for the call index of the edit.
- first_edit_vs_budget.py: first source-edit call index by max_tool_calls (sk_a2 28 vs sk_a2_32), pub024 hazard by call.
- refusal_next.py FOLDER...: gated-shell arms, move after the first refusal and time to the first working edit.
- decode_vs_inflight.py: decode tok/s by the number of requests in flight on the same server.
- bestof_sim.py: best-of-k and race (first submit ends the task) simulated from real single-agent runs.
- race_compaction_risk.py: how often a branch compacts before a race ends (the ADK ParallelAgent crash condition).

Added 2026-11-11 (docs/PLAN.md "MINING 2026-11-11"):
- evidence_reads.py [--runs] FOLDER...: evidence-stage runs (evid3 / evid4 / evidc and later): names chosen, whether the
  script output and the copied reply reach the gold patch's files / functions, empty (NOTHING RELEVANT / 1-line)
  replies, resolved; per task, the issue's names that appear in the gold patch.
- bad_calls.py [OUT.json]: every malformed or misused tool call over the whole bank (31B runs), by kind (garbled
  arguments, skill arguments, after budget, edit no match, read range, write outside /workspace, tool name / Python as
  shell, shell quoting, inline python syntax, unknown tool, call written as text, same failed call resent), by arm, and
  with / without the prompt rule written against it; the current family (combo1 / evid*) separately. "MINING 2026-11-11b".
