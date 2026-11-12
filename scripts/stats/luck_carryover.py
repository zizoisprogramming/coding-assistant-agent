"""How much of a lucky public-board run carries to the private board (2026-11-12). Usage (repo root):
    .venv/bin/python scripts/stats/luck_carryover.py

One scoring run covers ~120 hidden tasks: 58 public, the rest private (docs/PLAN.md 'Scoring'). Per-task chance is
independent between the two halves (different tasks); only a run-wide effect (scorer speed, server state) is shared.
Our 83 notebook runs measure that run-wide effect as draw sd 0.22 logit (stats_model.json); the scorer's may differ,
so 0.5 and 1.0 are shown too. Task difficulties: the bank's fitted task rates, shifted so 58 tasks average 10.4 solves
(one identical public bundle: 9, 10, 8, 13, 12 of 58). Prints the public sd, corr(public, private), and the private
gain of a run that scored >= 3 tasks above its mean on public."""
import json
import numpy as np

m = json.load(open("data/analysis/stats_model.json"))
rng = np.random.default_rng(7)
rates = np.clip(np.array([t["rate"] for t in m["tasks"]]), 1e-4, 1 - 1e-4)
base = np.log(rates / (1 - rates))
lg = lambda x: 1 / (1 + np.exp(-x))
lo, hi = -5.0, 5.0
for _ in range(60):
    mid = (lo + hi) / 2
    lo, hi = (mid, hi) if 58 * lg(base + mid).mean() < 10.4 else (lo, mid)
K = 200000
pt, qt = rng.choice(base, 58) + lo, rng.choice(base, 62) + lo  # one fixed public and private task set
for sdd in (m["sigma"]["draw"], 0.5, 1.0):
    d = rng.normal(0, sdd, (K, 1))
    pub = (rng.random((K, 58)) < lg(pt + d)).sum(1); pri = (rng.random((K, 62)) < lg(qt + d)).sum(1)
    sel = pub >= pub.mean() + 3
    gain = pri[sel].mean() - pri.mean()
    print(f"run-wide sd {sdd:.2f} logit: public sd {pub.std():.2f} tasks | corr(public, private) {np.corrcoef(pub, pri)[0, 1]:.2f} | "
          f"public +3 or more -> private {gain:+.2f} tasks ({100 * gain / 62:+.1f} pts)")
