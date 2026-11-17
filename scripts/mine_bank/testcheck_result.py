"""testcheck result (CPU notebook ziad23samer/regrade-cpu, kaggle/cells_testcheck_rt). Run: python3 -I scripts/mine_bank/testcheck_result.py
Runs cell4's summary on data/results/2026-11-17_testcheck_rt, then splits the tasks by the real fix: keeps the picked
existing tests passing (a clean signal) or breaks one (old tests that encode the old behaviour; the hidden test patch
rewrites them), with the NEW failures of wrong / solved patches in each group."""
import collections, json
from pathlib import Path
RESULTS = Path("data/results/2026-11-17_testcheck_rt/results")
exec(open("kaggle/cells_testcheck_rt/cell4_summary.py").read())
TC = [json.loads(l) for l in open(RESULTS / "testcheck.jsonl")]
gold = {r["iid"]: r for r in TC if r["kind"] == "gold"}
clean = {i for i, g in gold.items() if g["files"] and not g["new_fail"]}
broke = {i for i, g in gold.items() if g["new_fail"]}
print(f"\ntasks: real fix keeps the picked tests passing {len(clean)}, breaks one {len(broke)}, nothing picked {len(gold) - len(clean) - len(broke)}")
for name, S in (("real fix clean", clean), ("real fix breaks old tests", broke)):
    for k in ("wrong", "solved"):
        x = [r for r in TC if r["iid"] in S and r["kind"] == k]
        print(f"  {name:26} {k:6}: {len(x):3} patches, NEW failure {sum(bool(r['new_fail']) for r in x):2} on {len({r['iid'] for r in x if r['new_fail']})} tasks")
