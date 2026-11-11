"""Expected solves for a planned run, before it runs (data-oriented rule, memory data-oriented-stats). Usage (repo root):
    .venv/bin/python scripts/stats/expect_run.py --arms evidc,sq1c2a8rc --tasks dev16 --passes 2 [--face sq1c2a8rc]

From the bank model (run_model.py's spreads, effects refitted on every run): for each arm, the expected solves over the
planned runs with a 90% range (posterior uncertainty + a fresh notebook-run effect per pass, shared by the arms in it +
run-level chance); the gap between the first two arms with its 90% band; and the smallest gap that luck alone reaches at
most 5% of the time if the two arms were equal (both scored as the first arm = the control).
--face ARM adds a scenario where ARM is exactly as good as its own past runs say (the logit shift that makes the model's
fitted solves on ARM's runs equal its observed solves, on top of the fitted effects) -- the "taken at face value" case.
--tasks: dev16, or a comma list of task ids.
--exclude SUBSTR leaves out the runs of results folders whose name contains SUBSTR (to score a finished run against what
the bank said before it); --gap G adds P(gap <= G) and P(gap >= G) in each scenario (where an observed gap sits)."""
import argparse, importlib.util, json, os
import numpy as np

spec = importlib.util.spec_from_file_location("rm", os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_model.py"))
rm = importlib.util.module_from_spec(spec); spec.loader.exec_module(rm)
ap = argparse.ArgumentParser()
ap.add_argument("--arms", required=True); ap.add_argument("--tasks", default="dev16"); ap.add_argument("--passes", type=int, default=1)
ap.add_argument("--face"); ap.add_argument("--k", type=int, default=4000)
ap.add_argument("--exclude"); ap.add_argument("--gap", type=int)
a = ap.parse_args()
m = json.load(open("data/analysis/stats_model.json"))
sig = [m["sigma"][k] for k in ("task", "agent", "draw", "agent_x_task")]
ARMS = a.arms.split(","); TASKS = m["dev16"] if a.tasks == "dev16" else a.tasks.split(",")
rows = [r for r in rm.load() if not (a.exclude and a.exclude in r["folder"])]; d = rm.Design(rows); y = np.array([r["y"] for r in rows], float)
th, H, _, _ = rm._map(y, d, sig)
S = rm.draws_from(th, np.linalg.inv(H), a.k)
T, A, AT = (d.groups[g][1] for g in ("task", "agent", "axt"))
rng = rm.RNG


def eta(arm, shift=0.0):
    """(k, tasks) logits for ARM on TASKS per posterior sample (new agent / task / cell -> a fresh random effect)."""
    out = np.zeros((a.k, len(TASKS)))
    for j, t in enumerate(TASKS):
        e = S[:, 0] + (S[:, T[t]] if t in T else rng.normal(0, sig[0], a.k))
        e = e + (S[:, A[arm]] if arm in A else rng.normal(0, sig[1], a.k))
        c = AT.get((arm, t))
        out[:, j] = e + (S[:, c] if c is not None else rng.normal(0, sig[3], a.k)) + shift
    return out


def sims(etas):
    """solves per arm over the passes; one notebook-run effect per pass shared by all arms."""
    tot = [np.zeros(a.k) for _ in etas]
    for _ in range(a.passes):
        dr = rng.normal(0, sig[2], (a.k, 1))
        for i, e in enumerate(etas):
            tot[i] += (rng.random(e.shape) < rm.logistic(e + dr)).sum(axis=1)
    return tot


def face_shift(arm):
    rr = [i for i, r in enumerate(rows) if r["arm"] == arm]
    e = d.eta(th)[rr]; obs = y[rr].sum()
    lo, hi = -5.0, 5.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if rm.logistic(e + mid).sum() < obs else (lo, mid)
    return lo, obs, rm.logistic(e).sum()


n = len(TASKS) * a.passes
q = lambda v: f"{v.mean():5.1f} (90% {int(np.quantile(v, .05))}-{int(np.quantile(v, .95))})"
print(f"{len(TASKS)} tasks x {a.passes} passes = {n} runs per arm")
base = sims([eta(x) for x in ARMS])
for x, v in zip(ARMS, base):
    print(f"  model:      {x:12s} {q(v)} of {n}")
if len(ARMS) >= 2:
    g = base[1] - base[0]
    print(f"  model gap {ARMS[1]} - {ARMS[0]}: {g.mean():+.1f} (90% {int(np.quantile(g, .05)):+d} to {int(np.quantile(g, .95)):+d})"
          + (f"; P(gap <= {a.gap:+d}) {(g <= a.gap).mean():.2f}, P(gap >= {a.gap:+d}) {(g >= a.gap).mean():.2f}" if a.gap is not None else ""))
    e0 = eta(ARMS[0]); aa = sims([e0, e0]); ga = aa[1] - aa[0]
    thr = next(c for c in range(0, n + 1) if (ga >= c).mean() <= 0.05)
    print(f"  if equal (both = {ARMS[0]}): gap 90% {int(np.quantile(ga, .05)):+d} to {int(np.quantile(ga, .95)):+d}; luck reaches +{thr} or more "
          f"{100 * (ga >= thr).mean():.1f}% of the time -> a gap >= +{thr} is not luck (one-sided 5%)")
if a.face:
    sh, obs, fit = face_shift(a.face)
    fv = sims([eta(x, sh if x == a.face else 0.0) for x in ARMS])
    print(f"  face value: {a.face} +{sh:.2f} logit (its runs: observed {obs:.0f}, model fitted {fit:.1f})")
    for x, v in zip(ARMS, fv):
        print(f"    {x:12s} {q(v)} of {n}")
    if len(ARMS) >= 2 and a.face == ARMS[1]:
        g = fv[1] - fv[0]
        print(f"    gap {ARMS[1]} - {ARMS[0]}: {g.mean():+.1f} (90% {int(np.quantile(g, .05)):+d} to {int(np.quantile(g, .95)):+d}); "
              f"P(gap >= +{thr}) = {(g >= thr).mean():.2f}  (= the run's power to show it, if it is that good)"
              + (f"; P(gap <= {a.gap:+d}) {(g <= a.gap).mean():.2f}" if a.gap is not None else ""))
