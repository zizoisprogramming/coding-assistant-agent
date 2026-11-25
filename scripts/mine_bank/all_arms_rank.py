"""Every arm in the bank on one footing (user 2026-11-25: 'we need to learn what made every good arm good').
Task-adjusted solve rate: each run scores (solved - the task's solve rate over ALL runs); an arm's effect = the mean of its runs'
scores (+- 1.96 SE), so arms run on hard or easy tasks are comparable. Also per arm: no-patch, time ends, mean agent s, tool calls.
Run: python3 -I scripts/mine_bank/all_arms_rank.py [min_runs]"""
import collections, glob, json, statistics as S, sys
MIN = int(sys.argv[1]) if len(sys.argv) > 1 else 30
runs = []
for f in glob.glob("data/results/*/results/gen_per_task.jsonl"):
    d = f.split("/")[2]
    for l in open(f):
        try: g = json.loads(l)
        except Exception: continue
        if g.get("resolved") is None: continue  # keep time-outs (they carry an error field)
        g["dir"] = d; g["ok"] = g["resolved"] in (True, "True"); runs.append(g)
rate = collections.defaultdict(list)
for g in runs: rate[g["instance_id"]].append(g["ok"])
rate = {t: sum(v) / len(v) for t, v in rate.items()}
by = collections.defaultdict(list)
for g in runs: by[g["arm"]].append(g)
rows = []
for arm, R in by.items():
    if len(R) < MIN: continue
    res = [g["ok"] - rate[g["instance_id"]] for g in R]
    m = S.mean(res); se = S.pstdev(res) / len(res) ** 0.5
    rows.append(dict(arm=arm, n=len(R), eff=m, lo=m - 1.96 * se, hi=m + 1.96 * se, solved=sum(g["ok"] for g in R),
                     nopatch=S.mean(int(g.get("patch_chars") or 0) == 0 for g in R), timeend=S.mean(g.get("end") == "time" for g in R),
                     agent=S.mean(float(g.get("agent_s") or 0) for g in R), calls=S.mean(float(g.get("tool_calls") or 0) for g in R),
                     tasks=len({g["instance_id"] for g in R}), first=min(g["dir"][:10] for g in R), last=max(g["dir"][:10] for g in R)))
rows.sort(key=lambda r: -r["eff"])
print(f"{len(runs)} graded runs, {len(by)} arms; arms with >= {MIN} runs: {len(rows)}")
print(f"{'arm':22} {'n':>4} {'tasks':>5} {'solved':>6} {'effect':>7} {'95% range':>16} {'nopatch':>7} {'time':>5} {'agent_s':>7} {'calls':>5}  dates")
for r in rows:
    flag = " *" if r["lo"] > 0 else (" -" if r["hi"] < 0 else "")
    print(f"{r['arm'][:22]:22} {r['n']:4} {r['tasks']:5} {r['solved']:6} {r['eff']:+7.3f} [{r['lo']:+.3f},{r['hi']:+.3f}] {r['nopatch']:7.0%} {r['timeend']:5.0%} {r['agent']:7.0f} {r['calls']:5.1f}  {r['first']}..{r['last']}{flag}")
json.dump(rows, open("data/analysis/all_arms_rank.json", "w"), indent=0)
