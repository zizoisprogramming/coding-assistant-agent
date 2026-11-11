"""One shared effect of a change applied to several agents (e.g. the few-shot copies NAMEfs of r81), estimated inside the
bank model (run_model.py): every run of a changed copy counts as its original agent (same agent and agent x task effects)
plus a treatment effect beta, with no prior on beta (flat), so beta is not pulled toward zero the way a new agent's effect
is. Task, draw and agent effects keep the spreads fitted by run_model.py (read from its JSON).

    .venv/bin/python scripts/stats/treatment_effect.py [SUFFIX=fs] [FOLDER_SUBSTR ...]   (repo root; ~1 min)

Prints beta (logit) with its 95% interval, the odds ratio, and the implied change in solve rate on the tasks and agents
the copies ran (and on dev16 for each original); FOLDER_SUBSTR limits which runs of the copies are used (default: all)."""
import importlib.util, json, math, os, sys
import numpy as np

spec = importlib.util.spec_from_file_location("rm", os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_model.py"))
rm = importlib.util.module_from_spec(spec); spec.loader.exec_module(rm)
SUF = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("SUFFIX=")), "fs")
ONLY = [a for a in sys.argv[1:] if not a.startswith("SUFFIX=")]
m = json.load(open("data/analysis/stats_model.json"))
sig = [m["sigma"][k] for k in ("task", "agent", "draw", "agent_x_task")]

rows = rm.load()
arms = {r["arm"] for r in rows}
treated = []
keep = []
for r in rows:
    base = r["arm"][:-len(SUF)] if r["arm"].endswith(SUF) and r["arm"][:-len(SUF)] in arms else None
    if base and ONLY and not any(s in r["folder"] for s in ONLY):
        continue  # a copy's run outside the chosen folders
    keep.append(dict(r, arm=base or r["arm"])); treated.append(base is not None)
rows = keep; t = np.array(treated)
d = rm.Design(rows)
p = d.p + 2  # beta, then a dummy column held at 0 for untreated runs
idx = np.concatenate([d.idx, np.where(t, d.p, d.p + 1)[:, None]], axis=1)
sig2 = np.array([0.0] + [s * s for s in sig])
lam = np.concatenate([np.where(d.gid == 0, 0.0, 1.0 / sig2[d.gid]), [0.0, 1e12]])
y = np.array([r["y"] for r in rows], float)
theta = np.zeros(p); theta[0] = math.log(y.mean() / (1 - y.mean()))
for _ in range(60):
    eta = theta[idx].sum(axis=1); pr = 1 / (1 + np.exp(-eta)); w = pr * (1 - pr)
    g = np.zeros(p); np.add.at(g, idx, (y - pr)[:, None] * np.ones((1, idx.shape[1]))); g -= lam * theta
    H = np.zeros((p, p))
    for a in range(idx.shape[1]):
        for b in range(idx.shape[1]):
            np.add.at(H, (idx[:, a], idx[:, b]), w)
    H += np.diag(lam)
    step = np.linalg.solve(H, g); theta += step
    if np.abs(step).max() < 1e-9:
        break
Hinv = np.linalg.inv(H)
b, se = theta[d.p], math.sqrt(Hinv[d.p, d.p])
z = b / se
pval = 0.5 * math.erfc(z / math.sqrt(2))  # one-sided, beta > 0
print(f"runs {len(rows)} (changed copies {int(t.sum())}) | beta {b:+.2f} logit, 95% [{b - 1.96 * se:+.2f}, {b + 1.96 * se:+.2f}] | "
      f"odds ratio {math.exp(b):.2f} [{math.exp(b - 1.96 * se):.2f}, {math.exp(b + 1.96 * se):.2f}] | one-sided p {pval:.3f} | P(beta > 0) {1 - pval:.3f}")
S = rm.draws_from(theta, Hinv, 4000)
T, A, AT = (d.groups[g][1] for g in ("task", "agent", "axt"))
cells = sorted({(r["arm"], r["task"]) for r, tr in zip(rows, treated) if tr})
base_eta = np.stack([S[:, 0] + S[:, T[tk]] + S[:, A[ag]] + S[:, AT[(ag, tk)]] for ag, tk in cells], axis=1)
dlt = (rm.logistic(base_eta + S[:, [d.p]]) - rm.logistic(base_eta)).mean(axis=1) * 100
print(f"on the cells the copies ran ({len(cells)} agent x task): {np.median(dlt):+.1f} points [{np.quantile(dlt, .025):+.1f}, {np.quantile(dlt, .975):+.1f}]")
dev = [tk for tk in m["dev16"] if tk in T]
for ag in sorted({c[0] for c in cells}):
    at = np.stack([S[:, AT[(ag, tk)]] if (ag, tk) in AT else np.zeros(len(S)) for tk in dev], axis=1)
    e = S[:, [0]] + S[:, [T[tk] for tk in dev]] + S[:, [A[ag]]] + at
    dd = (rm.logistic(e + S[:, [d.p]]) - rm.logistic(e)).mean(axis=1) * 100
    print(f"  {ag:8s} on dev16: {rm.logistic(e).mean(axis=1).mean() * 100:.1f}% -> {np.median(dd):+.1f} points [{np.quantile(dd, .025):+.1f}, {np.quantile(dd, .975):+.1f}]")
