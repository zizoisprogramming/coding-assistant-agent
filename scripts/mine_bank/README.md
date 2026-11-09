Run-bank mining (2026-11-09). `python3 -I scripts/mine_bank/extract.py OUT.jsonl` builds one row per run from every
data/results/*/requests/requests.jsonl (outcome + every tool call with args, result head and timing); the other
scripts read that file (`python3 -I scripts/mine_bank/X.py OUT.jsonl [arm]`; garble.py, order.py, longreq.py read the
results folders directly). Results are written up in docs/PLAN.md, "MINING 2026-11-09b".
