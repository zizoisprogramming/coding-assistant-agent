"""Statistical model of every 31B agent-comparison run (user 2026-11-11: "data oriented approach from now on").

    .venv/bin/python scripts/stats/run_model.py [OUT.json]      (repo root; numpy only; ~1-2 min)

Solve model (hierarchical logistic regression, Laplace approximation, variance components by maximising the Laplace marginal likelihood):
    logit P(solved) = mu + task[t] + agent[a] + draw[d] + agent_x_task[a,t]
  task          how hard the task is
  agent         how good the agent is on an average task
  draw          one notebook run (a results folder = one draw of GPU speed, server load, sampling luck); shared by every
                arm in that run, so same-run comparisons cancel it
  agent_x_task  an agent that helps on some tasks only (e.g. the evidence arms on the mid-rate four)
  each ~ Normal(0, sigma_group^2); sigmas estimated from the data (Laplace-EM, as lme4's glmer does approximately).
Time model (same structure, Gaussian): agent_s = mu + task + agent + draw + agent_x_task + noise.

Outputs (JSON): variance components and shares; per agent: runs, solved, solve rate on an average task and on dev16 with
95% intervals; per draw: luck effect with interval; pairwise contrasts on dev16 (difference in solve rate, 95% interval,
P(better)); luck checks for recent draws (observed vs posterior-predictive, leave-the-draw-out); power curves (runs per arm
for 80% power) and the A/A noise band; time effects per agent.
Excluded: E4B / 12B runs, the info arm (sq1c2a6info: the task text was changed)."""
import collections, glob, json, math, os, sys
import numpy as np

RNG = np.random.default_rng(20261111)
OUT = sys.argv[1] if len(sys.argv) > 1 else "data/analysis/stats_model.json"
EXCLUDE_ARMS = {"sq1c2a6info"}
DEV16 = json.load(open("data/splits_public.json"))["dev16"]
MIN_AGENT_RUNS = 16
PAIRS = [("evidc", "combo1"), ("evidd", "evidc"), ("evide", "evidc"), ("combo1", "pub024"), ("evidc", "pub024"), ("evid3", "pub024"),
         ("sk_a2", "pub024"), ("sk_a2_32", "pub024"), ("nn32", "pub024"), ("nn36p", "pub024"), ("kf2", "pub024"), ("combo1en", "combo1"),
         ("combo1en2", "combo1"), ("combo2", "combo1"), ("evid4", "pub024"), ("hunch", "pub024"), ("race3", "combo1"), ("race2", "combo1"),
         ("nn32rcf", "combo1"), ("allplus", "combo1"), ("evgate", "combo1"), ("t7rc", "combo1"),
         ("pub024fs", "pub024"), ("combo1fs", "combo1"), ("evid3fs", "evid3"), ("evidcfs", "evidc")]
# a new arm that is a changed copy of a known agent is scored in the luck check as that agent (the null: the change does nothing)
NULL_AS = {"pub024fs": "pub024", "combo1fs": "combo1", "evid3fs": "evid3", "evidcfs": "evidc", "evidd": "evidc", "evide": "evidc"}


def load():
    rows, seen = [], set()
    for f in sorted(glob.glob("data/results/2026-*/results/gen_per_task.jsonl")):
        if "e4b" in f or "12b" in f:
            continue
        folder = f.split("/")[2]
        for l in open(f):
            try:
                r = json.loads(l)
            except Exception:
                continue
            k = (folder, r.get("instance_id"), r.get("attempt"))
            if k in seen or r.get("mode") != "skill_arms" or r.get("arm") in EXCLUDE_ARMS:
                continue
            seen.add(k)
            rows.append(dict(folder=folder, task=r["instance_id"], arm=r["arm"], y=int(bool(r.get("resolved"))),
                             agent_s=float(r.get("agent_s") or 0), end=r.get("end"), nopatch=not r.get("patch_chars")))
    return rows


class Design:
    """index maps for the four random-effect groups; column 0 = intercept."""

    def __init__(self, rows):
        self.groups = {}
        col = 1
        for g, key in (("task", lambda r: r["task"]), ("agent", lambda r: r["arm"]), ("draw", lambda r: r["folder"]),
                       ("axt", lambda r: (r["arm"], r["task"]))):
            levels = sorted({key(r) for r in rows}, key=str)
            self.groups[g] = (col, {lv: col + i for i, lv in enumerate(levels)})
            col += len(levels)
        self.p = col
        self.idx = np.array([[0] + [self.groups[g][1][k(r)] for g, k in (("task", lambda r: r["task"]), ("agent", lambda r: r["arm"]),
                              ("draw", lambda r: r["folder"]), ("axt", lambda r: (r["arm"], r["task"])))] for r in rows])
        self.gid = np.zeros(self.p, dtype=int)  # 0 = intercept, 1..4 = group
        for i, g in enumerate(("task", "agent", "draw", "axt"), 1):
            for c in self.groups[g][1].values():
                self.gid[c] = i

    def eta(self, theta):
        return theta[self.idx].sum(axis=1)


def fit_logistic(rows, d, iters=60, sig0=(1.0, 0.3, 0.3, 0.3)):
    y = np.array([r["y"] for r in rows], float)
    n, p = len(rows), d.p
    sig2 = np.array([0.0] + [s * s for s in sig0])
    theta = np.zeros(p); theta[0] = math.log(y.mean() / (1 - y.mean()))
    for it in range(iters):
        lam = np.where(d.gid == 0, 0.0, 1.0 / sig2[d.gid])
        for _ in range(30):  # Newton for the MAP given the sigmas
            eta = d.eta(theta); pr = 1 / (1 + np.exp(-eta)); w = pr * (1 - pr)
            g = np.zeros(p); np.add.at(g, d.idx, (y - pr)[:, None] * np.ones((1, d.idx.shape[1])))
            g -= lam * theta
            H = np.zeros((p, p))
            for a in range(d.idx.shape[1]):
                for b in range(d.idx.shape[1]):
                    np.add.at(H, (d.idx[:, a], d.idx[:, b]), w)
            H += np.diag(lam)
            step = np.linalg.solve(H, g)
            theta += step
            if np.abs(step).max() < 1e-7:
                break
        Hinv = np.linalg.inv(H)
        new = sig2.copy()
        for gi in range(1, 5):
            m = d.gid == gi
            new[gi] = max((theta[m] ** 2).sum() + np.diag(Hinv)[m].sum(), 1e-6) / m.sum()
        if np.max(np.abs(np.sqrt(new[1:]) - np.sqrt(sig2[1:]))) < 1e-4:
            sig2 = new
            break
        sig2 = new
    return theta, Hinv, np.sqrt(sig2[1:]), it + 1


def _map(rows_y, d, sig, theta0=None):
    """MAP of the effects for fixed sigmas (Newton), returning theta, H, log-likelihood and the penalty pieces."""
    y = rows_y; p = d.p
    sig2 = np.array([0.0] + [float(x) ** 2 for x in sig])
    with np.errstate(divide="ignore"):
        lam = np.where(d.gid == 0, 0.0, 1.0 / sig2[d.gid])
    theta = np.zeros(p) if theta0 is None else theta0.copy()
    if theta0 is None:
        theta[0] = math.log(y.mean() / (1 - y.mean()))
    k = d.idx.shape[1]
    for _ in range(50):
        eta = d.eta(theta); pr = 1 / (1 + np.exp(-eta)); w = pr * (1 - pr)
        g = np.zeros(p); np.add.at(g, d.idx, (y - pr)[:, None] * np.ones((1, k)))
        g -= lam * theta
        H = np.zeros((p, p))
        for a in range(k):
            for b in range(k):
                np.add.at(H, (d.idx[:, a], d.idx[:, b]), w)
        H += np.diag(lam)
        step = np.linalg.solve(H, g)
        theta += step
        if np.abs(step).max() < 1e-8:
            break
    eta = d.eta(theta)
    ll = float((y * eta - np.logaddexp(0, eta)).sum())
    return theta, H, lam, ll


def laplace_marginal(rows_y, d, logsig, theta0=None):
    """Laplace approximation of log p(y | sigmas) = ll(theta^) - 1/2 theta^T Lam theta^ + 1/2 sum log lam - 1/2 log|H| (+const)."""
    sig = np.exp(logsig)
    theta, H, lam, ll = _map(rows_y, d, sig, theta0)
    m = d.gid > 0
    sign, logdet = np.linalg.slogdet(H)
    val = ll - 0.5 * float((lam * theta * theta).sum()) + 0.5 * float(np.log(lam[m]).sum()) - 0.5 * logdet
    return val, theta, H


def fit_laplace(rows, d, start=(3.5, 0.2, 0.2, 0.25), tol=1e-3, verbose=False):
    """maximise the Laplace marginal likelihood over the four log-sigmas (Nelder-Mead, numpy only)."""
    y = np.array([r["y"] for r in rows], float)
    cache = {"theta": None}

    def f(x):
        x = np.clip(x, math.log(1e-3), math.log(20))
        v, th, H = laplace_marginal(y, d, x, cache["theta"])
        cache["theta"] = th
        return -v
    x0 = np.log(np.array(start))
    simplex = [x0] + [x0 + np.eye(4)[i] * 0.4 for i in range(4)]
    vals = [f(x) for x in simplex]
    for it in range(200):
        order = np.argsort(vals); simplex = [simplex[i] for i in order]; vals = [vals[i] for i in order]
        if abs(vals[-1] - vals[0]) < tol and it > 10:
            break
        c = np.mean(simplex[:-1], axis=0)
        xr = c + (c - simplex[-1]); fr = f(xr)
        if fr < vals[0]:
            xe = c + 2 * (c - simplex[-1]); fe = f(xe)
            simplex[-1], vals[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < vals[-2]:
            simplex[-1], vals[-1] = xr, fr
        else:
            xc = c + 0.5 * (simplex[-1] - c); fc = f(xc)
            if fc < vals[-1]:
                simplex[-1], vals[-1] = xc, fc
            else:
                simplex = [simplex[0]] + [simplex[0] + 0.5 * (s - simplex[0]) for s in simplex[1:]]
                vals = [vals[0]] + [f(s) for s in simplex[1:]]
        if verbose and it % 10 == 0:
            print("  NM", it, np.round(np.exp(simplex[0]), 3), round(-vals[0], 3))
    best = simplex[int(np.argmin(vals))]
    sig = np.exp(np.clip(best, math.log(1e-3), math.log(20)))
    theta, H, lam, ll = _map(y, d, sig, cache["theta"])
    return theta, np.linalg.inv(H), sig, it + 1


def fit_gaussian(vals, d, iters=200):
    """same structure, Gaussian residual: EM for the variance components (REML-like via Laplace = exact here)."""
    n, p = len(vals), d.p
    v = np.array(vals, float)
    X = np.zeros((n, p))
    for a in range(d.idx.shape[1]):
        X[np.arange(n), d.idx[:, a]] = 1.0
    XtX, Xty = X.T @ X, X.T @ v
    sig2 = np.array([0.0, 40.0 ** 2, 20.0 ** 2, 20.0 ** 2, 20.0 ** 2]); s2e = 80.0 ** 2
    for it in range(iters):
        with np.errstate(divide="ignore"): lam = np.where(d.gid == 0, 0.0, s2e / sig2[d.gid])
        A = XtX + np.diag(lam)
        theta = np.linalg.solve(A, Xty)
        Ainv = np.linalg.inv(A)
        resid = v - X @ theta
        new = sig2.copy()
        for gi in range(1, 5):
            m = d.gid == gi
            new[gi] = max((theta[m] ** 2).sum() + s2e * np.diag(Ainv)[m].sum(), 1e-3) / m.sum()
        s2e_new = (resid @ resid + s2e * np.trace(Ainv @ XtX)) / n
        done = np.max(np.abs(np.sqrt(new[1:]) - np.sqrt(sig2[1:]))) < 1e-3 and abs(math.sqrt(s2e_new) - math.sqrt(s2e)) < 1e-3
        sig2, s2e = new, s2e_new
        if done:
            break
    with np.errstate(divide="ignore"): lam = np.where(d.gid == 0, 0.0, s2e / sig2[d.gid])
    A = XtX + np.diag(lam)
    theta = np.linalg.solve(A, Xty)
    cov = s2e * np.linalg.inv(A)
    return theta, cov, np.sqrt(sig2[1:]), math.sqrt(s2e)


def logistic(x):
    return 1 / (1 + np.exp(-x))


def draws_from(theta, Hinv, k):
    L = np.linalg.cholesky(Hinv + 1e-10 * np.eye(len(theta)))
    return theta[None, :] + RNG.standard_normal((k, len(theta))) @ L.T


def main():
    rows = load()
    d = Design(rows)
    theta, Hinv, sig, iters = fit_laplace(rows, d, verbose=True)
    print(f"runs {len(rows)} | tasks {len(d.groups['task'][1])} agents {len(d.groups['agent'][1])} draws {len(d.groups['draw'][1])} "
          f"agent x task cells {len(d.groups['axt'][1])} | Nelder-Mead iters {iters}")
    names = ("task", "agent", "draw", "agent_x_task")
    print("sigma (logit):", {n: round(float(s), 3) for n, s in zip(names, sig)})
    resid = math.pi ** 2 / 3
    tot = float((sig ** 2).sum()) + resid
    shares = {n: float(s * s / tot) for n, s in zip(names, sig)}
    shares["run-level chance"] = resid / tot
    print("variance shares (latent scale):", {k: round(v, 3) for k, v in shares.items()})
    S = draws_from(theta, Hinv, 4000)
    T, A, D, AT = (d.groups[g][1] for g in ("task", "agent", "draw", "axt"))
    dev = [t for t in DEV16 if t in T]

    def dev_rate(samples, arm, sigd=True):
        """expected solve rate on dev16 for ARM in a fresh draw (draw effect integrated), per posterior sample."""
        eta = samples[:, [0]] + samples[:, [T[t] for t in dev]] + samples[:, [A[arm]]]
        cells = [AT.get((arm, t)) for t in dev]
        at = np.stack([samples[:, c] if c is not None else RNG.normal(0, sig[3], len(samples)) for c in cells], axis=1)
        dr = RNG.normal(0, sig[2], (len(samples), 1)) if sigd else 0
        return logistic(eta + at + dr).mean(axis=1)

    per_arm = collections.defaultdict(lambda: [0, 0, 0, 0.0])
    for r in rows:
        x = per_arm[r["arm"]]; x[0] += 1; x[1] += r["y"]; x[2] += r["nopatch"]; x[3] += r["agent_s"]
    agents = []
    for arm, (n, s, npch, ag) in per_arm.items():
        if n < MIN_AGENT_RUNS:
            continue
        b = S[:, 0] + S[:, A[arm]]
        avg = logistic(b)
        dv = dev_rate(S, arm, sigd=False)
        agents.append(dict(agent=arm, runs=n, solved=s, raw_rate=s / n, nopatch=npch / n, mean_agent_s=ag / n,
                           effect=float(theta[A[arm]]), effect_sd=float(math.sqrt(Hinv[A[arm], A[arm]])),
                           avg_task=float(np.median(avg)), avg_lo=float(np.quantile(avg, .025)), avg_hi=float(np.quantile(avg, .975)),
                           dev16=float(np.median(dv)), dev16_lo=float(np.quantile(dv, .025)), dev16_hi=float(np.quantile(dv, .975)),
                           dev16_runs=sum(1 for r in rows if r["arm"] == arm and r["task"] in dev)))
    agents.sort(key=lambda a: -a["dev16"])
    tasks = []
    for t in T:
        n = sum(1 for r in rows if r["task"] == t); s = sum(r["y"] for r in rows if r["task"] == t)
        v = logistic(S[:, 0] + S[:, T[t]])
        tasks.append(dict(task=t, runs=n, solved=s, dev16=t in dev, rate=float(np.median(v)), lo=float(np.quantile(v, .025)), hi=float(np.quantile(v, .975))))
    tasks.sort(key=lambda x: -x["rate"])
    draws = []
    for f in D:
        n = sum(1 for r in rows if r["folder"] == f); s = sum(r["y"] for r in rows if r["folder"] == f)
        e = S[:, D[f]]
        draws.append(dict(draw=f, runs=n, solved=s, effect=float(theta[D[f]]), lo=float(np.quantile(e, .025)), hi=float(np.quantile(e, .975)),
                          arms=sorted({r["arm"] for r in rows if r["folder"] == f})))
    draws.sort(key=lambda x: x["draw"])
    pairs = []
    for a, b in PAIRS:
        if a not in A or b not in A:
            continue
        both = sorted({r["folder"] for r in rows if r["arm"] == a} & {r["folder"] for r in rows if r["arm"] == b})
        da, db = dev_rate(S, a, sigd=False), dev_rate(S, b, sigd=False)
        diff = da - db
        # raw same-run pairs: same folder, task and attempt number
        idx = collections.defaultdict(dict)
        for r in rows:
            if r["folder"] in both and r["arm"] in (a, b):
                idx[(r["folder"], r["task"])].setdefault(r["arm"], []).append(r["y"])
        plus = minus = npair = 0
        for k, v in idx.items():
            if a in v and b in v:
                for ya, yb in zip(v[a], v[b]):
                    npair += 1; plus += ya and not yb; minus += yb and not ya
        sign_p = sum(math.comb(plus + minus, i) for i in range(min(plus, minus) + 1)) * 2 / 2 ** (plus + minus) if plus + minus else 1.0
        pairs.append(dict(a=a, b=b, diff=float(np.median(diff)), lo=float(np.quantile(diff, .025)), hi=float(np.quantile(diff, .975)),
                          p_better=float((diff > 0).mean()), same_run_pairs=npair, plus=plus, minus=minus, sign_p=min(1.0, sign_p)))
    # luck checks: recent draws, leave-the-draw-out fit, posterior predictive of each arm's solves in that draw
    luck = []
    recent = [f for f in D if f >= "2026-11-10"]
    for f in recent:
        sub = [r for r in rows if r["folder"] != f]
        d2 = Design(sub)
        y2 = np.array([r["y"] for r in sub], float)
        th2, H2b, _, _ = _map(y2, d2, sig)  # same sigmas, effects refitted without this draw
        H2 = np.linalg.inv(H2b); sg2 = sig
        S2 = draws_from(th2, H2, 2000)
        T2, A2, AT2 = d2.groups["task"][1], d2.groups["agent"][1], d2.groups["axt"][1]
        here = [r for r in rows if r["folder"] == f]
        drw = RNG.normal(0, sg2[2], (len(S2), 1))  # one fresh draw effect shared by all arms of this run
        total = np.zeros(len(S2))
        for arm in sorted({r["arm"] for r in here}):
            rr = [r for r in here if r["arm"] == arm]
            as_ = arm if arm in A2 else NULL_AS.get(arm) if NULL_AS.get(arm) in A2 else None  # scored as
            eta = np.zeros((len(S2), len(rr)))
            for j, r in enumerate(rr):
                e = S2[:, 0].copy()
                e += S2[:, T2[r["task"]]] if r["task"] in T2 else RNG.normal(0, sg2[0], len(S2))
                e += S2[:, A2[as_]] if as_ else RNG.normal(0, sg2[1], len(S2))
                c = AT2.get((as_, r["task"]))
                e += S2[:, c] if c is not None else RNG.normal(0, sg2[3], len(S2))
                eta[:, j] = e
            sims = (RNG.random(eta.shape) < logistic(eta + drw)).sum(axis=1)
            total += sims
            obs = sum(r["y"] for r in rr)
            pct = float((sims < obs).mean() + 0.5 * (sims == obs).mean())
            luck.append(dict(draw=f, arm=arm, runs=len(rr), observed=obs, expected=float(sims.mean()),
                             lo=int(np.quantile(sims, .05)), hi=int(np.quantile(sims, .95)), percentile=pct,
                             new_agent=arm not in A2, scored_as=as_ if as_ != arm else None))
        obs = sum(r["y"] for r in here)
        luck.append(dict(draw=f, arm="ALL ARMS", runs=len(here), observed=obs, expected=float(total.mean()),
                         lo=int(np.quantile(total, .05)), hi=int(np.quantile(total, .95)),
                         percentile=float((total < obs).mean() + 0.5 * (total == obs).mean()), new_agent=False, scored_as=None))
        print(f"luck check {f}: " + ", ".join(f"{x['arm']} {x['observed']} vs {x['expected']:.1f} [{x['lo']}-{x['hi']}] p{100 * x['percentile']:.0f}" for x in luck if x["draw"] == f))
    # A/A noise band and power on dev16-like task sets: two arms in the same runs, one run per task per pass
    tasks_eff = np.array([theta[T[t]] for t in dev])
    base = theta[0] + theta[A["combo1"]] if "combo1" in A else theta[0]

    def sim_gap(true_gain_logit, passes, k=4000):
        gaps = np.zeros(k)
        for i in range(k):
            tot_a = tot_b = 0
            ata = RNG.normal(0, sig[3], len(dev)); atb = RNG.normal(0, sig[3], len(dev))
            for _ in range(passes):
                dr = RNG.normal(0, sig[2])
                pa = logistic(base + tasks_eff + true_gain_logit + ata + dr); pb = logistic(base + tasks_eff + atb + dr)
                tot_a += (RNG.random(len(dev)) < pa).sum(); tot_b += (RNG.random(len(dev)) < pb).sum()
            gaps[i] = tot_a - tot_b
        return gaps
    noise = {}
    for passes in (1, 2, 4, 8):
        g = sim_gap(0.0, passes)
        noise[passes] = dict(runs_per_arm=passes * len(dev), sd=float(g.std()), band90=[float(np.quantile(g, .05)), float(np.quantile(g, .95))])
    print("A/A gap (same agent twice, dev16):", {k: (v["runs_per_arm"], round(v["sd"], 2), v["band90"]) for k, v in noise.items()})
    power = []
    p0 = float(logistic(base + tasks_eff).mean())
    for gain_pp in (3, 5, 10, 15, 20):
        # find the logit shift that gives +gain_pp points on dev16 for the base agent
        lo_, hi_ = 0.0, 3.0
        for _ in range(40):
            mid = (lo_ + hi_) / 2
            if logistic(base + tasks_eff + mid).mean() - p0 < gain_pp / 100: lo_ = mid
            else: hi_ = mid
        row = dict(gain_pp=gain_pp, logit=lo_)
        for passes in (1, 2, 4, 8, 16):
            null = sim_gap(0.0, passes, 3000)
            c = next(c for c in range(0, 200) if (null >= c).mean() <= 0.05)  # smallest whole-solve gap with alpha <= 5% (one-sided)
            row[f"power_{passes * len(dev)}"] = float((sim_gap(lo_, passes, 3000) >= c).mean())
            row[f"needed_gap_{passes * len(dev)}"] = int(c)
        power.append(row)
        print("power", row)
    # time model
    dt = Design(rows)
    tth, tcov, tsig, terr = fit_gaussian([r["agent_s"] for r in rows], dt)
    tA = dt.groups["agent"][1]
    times = []
    for a in agents:
        c = tA[a["agent"]]
        times.append(dict(agent=a["agent"], effect_s=float(tth[c]), lo=float(tth[c] - 1.96 * math.sqrt(tcov[c, c])), hi=float(tth[c] + 1.96 * math.sqrt(tcov[c, c])),
                          mean_agent_s=a["mean_agent_s"]))
    tshares = {n: float(s * s) for n, s in zip(names, tsig)}; tshares["run-level"] = terr ** 2
    tt = sum(tshares.values()); tshares = {k: v / tt for k, v in tshares.items()}
    print("time sigma (s):", {n: round(float(s), 1) for n, s in zip(names, tsig)}, "residual", round(terr, 1), "shares", {k: round(v, 3) for k, v in tshares.items()})
    tpairs = []
    for a, b in PAIRS:
        if a in tA and b in tA:
            ca, cb = tA[a], tA[b]
            dlt = tth[ca] - tth[cb]; sd = math.sqrt(tcov[ca, ca] + tcov[cb, cb] - 2 * tcov[ca, cb])
            tpairs.append(dict(a=a, b=b, diff_s=float(dlt), lo=float(dlt - 1.96 * sd), hi=float(dlt + 1.96 * sd)))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(dict(n_runs=len(rows), n_tasks=len(T), n_agents=len(A), n_draws=len(D), n_cells=len(AT), sigma=dict(zip(names, map(float, sig))),
                   shares=shares, base_dev16=p0, agents=agents, tasks=tasks, draws=draws, pairs=pairs, luck=luck, noise=noise, power=power,
                   time_sigma=dict(zip(names, map(float, tsig))), time_resid=terr, time_shares=tshares, times=times, time_pairs=tpairs,
                   dev16=dev), open(OUT, "w"), indent=1)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
