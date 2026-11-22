"""Which local task subset agrees with the LB? (user 2026-11-22). For each agent with an LB score and local runs: its task-matched solve-rate
difference vs pub024 on a subset (mean over the subset's tasks both ran of per-task rate differences), then the rank correlation with the LB
score over agents, plus how much of the LB spread is noise. Run: python3 -I scripts/mine_bank/lb_subsets.py"""
import collections, glob, json, statistics as st
from math import sqrt
LB = {"sk_a2": [11], "sk_a2_32": [10], "sb1hl": [9], "combo1": [9], "evidc": [9, 7], "sa2": [7], "nn32rcn2": [7], "sq1c2a6": [7, 6],
      "evidefs": [6], "pub024": [11]}  # solved of 58 = floor-consistent with the public scores
R = collections.defaultdict(lambda: collections.defaultdict(list)); SPLIT = {}
for f in glob.glob("data/results/*/results/gen_per_task.jsonl"):
    for l in open(f, errors="replace"):
        try: g = json.loads(l)
        except Exception: continue
        if "31b" not in str(g.get("model", "31b")).lower(): continue
        R[g.get("arm")][g["instance_id"]].append(g.get("resolved") in (True, "True"))
        SPLIT[g["instance_id"]] = g.get("split") or g.get("level")
R8 = {"fastapi_14419", "rich_3470", "rich_3882", "rich_4079", "fastapi_11194", "fastapi_15589", "rich_3180", "rich_3521"}
pubrate = {t: st.mean(v) for t, v in R["pub024"].items()}
SUBSETS = {"all": set(SPLIT), "dev16": {t for t, s in SPLIT.items() if s == "dev16"}, "val": {t for t, s in SPLIT.items() if s == "val"},
           "test": {t for t, s in SPLIT.items() if s == "test"}, "rtest": {t for t, s in SPLIT.items() if s == "rtest"},
           "solvable 8": R8, "hard (pub024 < 20%)": {t for t, p in pubrate.items() if p < 0.2}, "mid (pub024 20-80%)": {t for t, p in pubrate.items() if 0.2 <= p <= 0.8},
           "easy (pub024 > 80%)": {t for t, p in pubrate.items() if p > 0.8}}


def rank(x):
    o = sorted(range(len(x)), key=lambda i: x[i]); r = [0.0] * len(x); i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and x[o[j + 1]] == x[o[i]]: j += 1
        for k in range(i, j + 1): r[o[k]] = (i + j) / 2
        i = j + 1
    return r


def corr(a, b):
    ma, mb = st.mean(a), st.mean(b); va = sum((x - ma) ** 2 for x in a); vb = sum((y - mb) ** 2 for y in b)
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / sqrt(va * vb) if va and vb else float("nan")


lbm = {a: st.mean(v) for a, v in LB.items()}
obs = st.pvariance(list(lbm.values())); p = st.mean(lbm.values()) / 58
noise = 58 * p * (1 - p)
print(f"LB spread of our {len(lbm)} agents: variance {obs:.2f} tasks^2 (SD {sqrt(obs):.2f}); binomial noise of ONE score at p={p:.3f}: variance {noise:.2f} (SD {sqrt(noise):.2f})")
print(f"-> share of the LB spread that can be real skill: {max(0, obs - noise) / obs:.0%} (noise alone predicts a spread this big or bigger)")
print("   (agents with two scores: evidc 9 / 7, sq1c2a6 7 / 6: the same file moved 1-2 tasks)\n")
print(f"{'subset':22}{'tasks':>6}{'agents':>8}{'rank corr':>11}{'pearson':>9}   per agent (local diff vs pub024 -> LB)")
for name, S in SUBSETS.items():
    xs, ys, lab = [], [], []
    for a in lbm:
        if a == "pub024": xs.append(0.0); ys.append(lbm[a]); lab.append("pub024 +0"); continue
        com = [t for t in S if t in R[a] and t in R["pub024"]]
        if len(com) < 4: continue
        d = st.mean(st.mean(R[a][t]) - st.mean(R["pub024"][t]) for t in com)
        xs.append(d); ys.append(lbm[a]); lab.append(f"{a} {d:+.0%}/{len(com)}t")
    if len(xs) >= 5:
        print(f"{name:22}{len(S):6}{len(xs):8}{corr(rank(xs), rank(ys)):11.2f}{corr(xs, ys):9.2f}   " + ", ".join(lab))
