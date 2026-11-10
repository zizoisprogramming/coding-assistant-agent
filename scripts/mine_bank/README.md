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
