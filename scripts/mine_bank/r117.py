"""r117: sb1 vs sb1pp15 vs sb7g on 12 mid-rate tasks, 2 passes (docs/PLAN.md RUN BUILT r117).
Run: python3 -I scripts/mine_bank/r117.py   (repo root; logs only)
1. outcomes per arm and per task (gen_per_task); 2. the penalty measures of r115_pp.py for all three arms, with the
matched bank resample (one bank sb1 run per task an arm ran); 3. sb7g's stage and fixer measures of r116_sb7f.py
(its prompt keys and the 32-call budget swapped in)."""
import collections, glob, json, re, statistics as st, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIRS = sorted(glob.glob(str(ROOT / "data/results/2026-11-19_skill_r117_p*")))
ARMS = ("sb1", "sb1pp15", "sb7g")
TASKS = ("cta-observatory__pyirf-193", "RDFLib__pySHACL-285", "Netflix-Skunkworks__policyuniverse-147", "terryyin__lizard-144",
         "lucianopaz__compress_pickle-28", "terryyin__lizard-370", "klen__peewee_migrate-203", "hgrecco__pint-pandas-264",
         "fastapi_11194", "rich_3278", "rich_3676", "rich_3506")

print("#### 1. outcomes")
G = []
for d in DIRS:
    for l in open(f"{d}/results/gen_per_task.jsonl"):
        g = json.loads(l)
        if g.get("arm") in ARMS:
            g["p"] = d[-2:]
            G.append(g)
solved = lambda g: g["resolved"] in (True, "True")
for a in ARMS:
    A = [g for g in G if g["arm"] == a]
    print(f"  {a:8} runs {len(A):2} | solved {sum(map(solved, A)):2} | no patch {sum(not g.get('patch_chars') for g in A):2}"
          f" | ends {dict(collections.Counter(g['end'] for g in A))} | agent s mean {st.mean(g['agent_s'] for g in A):4.0f}"
          f" | by pass {[sum(solved(g) for g in A if g['p'] == p) for p in ('p1', 'p2')]}")
print("  per task (S solved, E edited no solve, 0 no patch; p1 p2):")
for t in TASKS:
    row = []
    for a in ARMS:
        xs = sorted((g for g in G if g["instance_id"] == t and g["arm"] == a), key=lambda g: g["p"])
        row.append(f"{a} " + "".join("S" if solved(g) else ("E" if g.get("patch_chars") else "0") for g in xs))
    print(f"    {t[:34]:34} " + " | ".join(f"{r:12}" for r in row))

print("\n#### 2. penalty measures (r115_pp.py)")
src = (ROOT / "scripts/mine_bank/r115_pp.py").read_text()
ns = {}
exec(src[:src.index("new = {}")].replace('TASKS = ("rich_3521", "geopandas__geopandas-3240", "fastapi_14419", "rich_4079")', "TASKS = " + repr(TASKS)), ns)
new = {}
for d in DIRS:
    new.update(ns["load"](d, ARMS))
for a in ARMS:
    print(ns["line"](a, ns["agg"]([r for r in new.values() if r["arm"] == a])))
bank = {}
for d in sorted(glob.glob(str(ROOT / "data/results/2026-11-1*"))):
    if d not in DIRS and "2026-11-19" not in d and glob.glob(f"{d}/requests/requests.jsonl"):
        try:
            bank.update(ns["load"](d, ("sb1",)))
        except Exception as e:
            print("skip", d, e)
B = collections.defaultdict(list)
for r in bank.values():
    B[r["task"]].append(r)
print("  bank sb1 runs per task:", {t[:14]: len(B[t]) for t in TASKS})
import random
random.seed(0)
for a in ARMS:
    rs = [r for r in new.values() if r["arm"] == a and B[r["task"]]]
    sims = [ns["agg"]([random.choice(B[r["task"]]) for r in rs]) for _ in range(10000)]
    x = ns["agg"](rs)
    cells = []
    for m in ("tok", "long", "wait", "fails", "time", "nop", "solved", "agent"):
        v = sorted(s[m] for s in sims)
        cells.append(f"{m} {x[m]:.1f} [{v[len(v) // 20]:.1f}, {v[-len(v) // 20]:.1f}] p<= {sum(y <= x[m] for y in v) / len(v):.2f}")
    print(f"  {a:8} vs bank sb1 on the same tasks ({len(rs)} runs): " + " | ".join(cells))

print("\n#### 3. sb7g stage and fixer (r116_sb7f.py)")
s16 = (ROOT / "scripts/mine_bank/r116_sb7f.py").read_text()
s16 = s16.replace('DIRS = sorted(glob.glob(sys.argv[1]))', 'DIRS = ' + repr(DIRS))
s16 = s16.replace('H_KEY, F_KEY = "You run two commands before the engineer starts", "# HOW THE FUNCTIONS OF THIS ISSUE CHANGED BEFORE"',
                  'H_KEY, F_KEY = "You fetch the history of the code this issue is about", "# THE HISTORY IS FETCHED"')
s16 = s16.replace('"#asb7f."', '"#asb7g."').replace(r"\((\d+)/28 used\)", r"\((\d+)/32 used\)")
s16 = s16.replace('''split("Each commit's title says why, its diff says how:\\n", 1)[-1].split("\\n\\n# SOLVE IT WITH")[0]''',
                  '''split("each with its title (why) and its diff (how):\\n", 1)[-1].split("\\n\\nThe history is fetched and you have all")[0]''')
s16 = s16.replace('fence = H[0][3].find(', 'fence = H[0][3].find(').replace('"HISTORY DONE"', '"HISTORY FETCHED"')
assert "You fetch the history" in s16 and "#asb7g." in s16 and "/32 used" in s16 and "each with its title (why)" in s16 and '"HISTORY FETCHED"' in s16
exec(compile(s16, "r116_sb7f(sb7g)", "exec"), {"__name__": "r117"})
