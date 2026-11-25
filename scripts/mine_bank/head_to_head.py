"""Same-run, same-task head-to-heads for every arm pair (user 2026-11-25 'what made every good arm good'): in each results folder,
for tasks both arms ran, compare solve counts. Pooled over folders; sign test on tasks where one arm solved more.
Run: python3 -I scripts/mine_bank/head_to_head.py [min_matched_runs]"""
import collections, glob, json, sys
from math import comb
MIN = int(sys.argv[1]) if len(sys.argv) > 1 else 16
cell = collections.defaultdict(lambda: [0, 0])  # (dir, arm, task) -> [solved, runs]
for f in glob.glob("data/results/*/results/gen_per_task.jsonl"):
    d = f.split("/")[2]
    for l in open(f):
        try: g = json.loads(l)
        except Exception: continue
        if g.get("resolved") is None: continue
        c = cell[(d, g["arm"], g["instance_id"])]; c[0] += g["resolved"] in (True, "True"); c[1] += 1
by_dir = collections.defaultdict(lambda: collections.defaultdict(dict))
for (d, a, t), v in cell.items(): by_dir[d][a][t] = v
pair = collections.defaultdict(lambda: dict(sa=0, na=0, sb=0, nb=0, wa=0, wb=0, dirs=set()))
for d, arms in by_dir.items():
    names = sorted(arms)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            for t in set(arms[a]) & set(arms[b]):
                (s1, n1), (s2, n2) = arms[a][t], arms[b][t]
                n = min(n1, n2)  # equal weight per task: rates x min runs
                p = pair[(a, b)]; p["sa"] += s1 / n1 * n; p["sb"] += s2 / n2 * n; p["na"] += n; p["nb"] += n; p["dirs"].add(d)
                if s1 / n1 > s2 / n2: p["wa"] += 1
                elif s2 / n2 > s1 / n1: p["wb"] += 1
def sign_p(w, l):
    n = w + l
    return 1.0 if n == 0 else min(1, 2 * sum(comb(n, k) for k in range(max(w, l), n + 1)) / 2 ** n)
rows = [(a, b, p) for (a, b), p in pair.items() if p["na"] >= MIN]
rows.sort(key=lambda x: -abs(x[2]["sa"] - x[2]["sb"]) / x[2]["na"])
print(f"{len(rows)} arm pairs with >= {MIN} matched runs (same folder, same task). diff = A rate - B rate; tasks A>B / B>A; sign-test p")
for a, b, p in rows:
    print(f"{a[:20]:20} vs {b[:20]:20} n {p['na']:4.0f}  A {p['sa']/p['na']:.0%}  B {p['sb']/p['nb']:.0%}  diff {(p['sa']-p['sb'])/p['na']:+.0%}  tasks {p['wa']:2}/{p['wb']:2}  p {sign_p(p['wa'], p['wb']):.2f}  folders {len(p['dirs'])}")
