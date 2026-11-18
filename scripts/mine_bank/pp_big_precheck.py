"""Planning numbers for the bigger presence_penalty 1.5 run (user 2026-11-18: 'yes plan the bigger penalty run').
Run: python3 -I scripts/mine_bank/pp_big_precheck.py   (repo root; logs only)
Task set: the 24 SWE-rebench test tasks (RTEST24, never used to pick agents) minus geopandas-3240 (one of r115's 4
picked tasks) = 23. From every earlier sb1 run on them (requests + digest / gen_per_task): per task solve rate,
time ends, no patch, tokens per reply, long-reply share, cut-apart calls; and the spread of a 2-pass run (46 runs)
by resampling two bank runs per task, so the bars can be set against what sb1 does by chance."""
import collections, glob, json, random, re, statistics as st, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
src = (ROOT / "scripts/mine_bank/r115_pp.py").read_text()
ns = {}
exec(src[:src.index("new = {}")].replace('TASKS = ("rich_3521", "geopandas__geopandas-3240", "fastapi_14419", "rich_4079")', "TASKS = ()"), ns)
cells = (ROOT / "scripts/train/make_skill_arms_cells.py").read_text()
RT = eval(re.search(r"RTEST24 = (\[.*?\])", cells, re.S).group(1))
TASKS = tuple(t for t in RT if t != "geopandas__geopandas-3240")
ns["TASKS"] = TASKS
ns["load"].__globals__["TASKS"] = TASKS
bank = {}
for d in sorted(glob.glob(str(ROOT / "data/results/2026-11-1*"))):
    if glob.glob(f"{d}/requests/requests.jsonl"):
        try:
            bank.update(ns["load"](d, ("sb1",)))
        except Exception as e:
            print("skip", d, e)
B = collections.defaultdict(list)
for r in bank.values():
    B[r["task"]].append(r)
print(f"tasks {len(TASKS)} | with bank sb1 runs {sum(1 for t in TASKS if B[t])} | runs per task {sorted(len(B[t]) for t in TASKS)}")
A = ns["agg"]([r for v in B.values() for r in v])
print(ns["line"]("bank sb1", A))
for t in TASKS:
    v = B[t]
    if v:
        a = ns["agg"](v)
        print(f"  {t[:44]:44} runs {a['n']:2} solved {a['solved']:2} time {a['time']:2} nop {a['nop']:2} tok {a['tok']:4.0f} long {a['long']:3.0f}% cut {a['fails']:.1f}")
random.seed(0)
ts = [t for t in TASKS if B[t]]
sims = [(ns["agg"]([random.choice(B[t]) for t in ts for _ in range(2)]), ns["agg"]([random.choice(B[t]) for t in ts for _ in range(2)])) for _ in range(5000)]
print(f"\n2-pass run = {2 * len(ts)} runs per arm; sb1 vs sb1 by chance (5th-95th percentile of arm A - arm B):")
for m in ("solved", "time", "nop", "tok", "long", "wait", "fails", "agent"):
    v = sorted(a[m] - b[m] for a, b in sims)
    print(f"  {m:6} sb1 mean {st.mean(a[m] for a, _ in sims):7.2f} | difference [{v[len(v) // 20]:7.2f}, {v[-len(v) // 20]:7.2f}]")
