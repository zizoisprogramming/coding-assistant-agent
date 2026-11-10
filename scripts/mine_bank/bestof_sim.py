"""Simulate parallel best-of-k from real single-agent runs (pub024 family, 28 calls / 8 min): k runs of the same task run
side by side, each slowed by the measured decode loss (1 in flight 32.3 tok/s, k in flight: 2 -> 30.2, 3 -> 26.9;
local runs were at ~2 in flight), each cut at a branch cap C. A cut run counts as solved only if it solved AND its last
working source edit was in place by the cut; it has a patch if its first source edit was in place by the cut.
Task time = slowest branch. Pickers: oracle, random non-empty, the first branch to finish with a patch.
Usage: python3 -I scripts/mine_bank/bestof_sim.py"""
import json, glob, collections, re, random, itertools, statistics as st
ARMS = {"pub024", "combo1"}
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$")
runs = collections.defaultdict(list)
for d in glob.glob("data/results/2026-1[01]-*/"):
    try: res = {(r["instance_id"], r["attempt"]): r for r in map(json.loads, open(d + "results/gen_per_task.jsonl"))}
    except FileNotFoundError: continue
    J = collections.defaultdict(list)
    try:
        for l in open(d + "requests/requests.jsonl"):
            try: r = json.loads(l)
            except Exception: continue
            if isinstance(r.get("reply"), dict) and r.get("job"): J[r["job"]].append(r)
    except FileNotFoundError: continue
    for job, q in J.items():
        iid, _, att = job.partition("#a"); arm = att.split(".")[0]; R = res.get((iid, att))
        if arm not in ARMS or not R or R.get("agent_s") is None: continue
        q.sort(key=lambda r: r["t"]); t0 = q[0]["t"]; ans = {}; first = last = None
        for r in q:
            for m in r["request"]["messages"]:
                if m.get("role") == "tool": ans.setdefault(m.get("tool_call_id"), str(m.get("content")))
        for r in q:
            for c in r["reply"]["message"].get("tool_calls") or []:
                n = c["function"]["name"]
                try: a = json.loads(c["function"]["arguments"])
                except Exception: a = {}
                p = str(a.get("filepath") or ""); cmd = str(a.get("command", "")); rt = ans.get(c.get("id"), "")
                src = n in ("edit_file", "write_file") and p and not TEST.search(p) and not p.startswith("/tmp")
                sh = n == "run_command" and re.search(r"open\([^)]*['\"]w['\"]|\.write\(|sed -i", cmd) and "/tmp/" not in cmd
                if (src or sh) and "mandatory" not in rt and "error_type" not in rt[:200]:
                    t = r["t"] + r["seconds"] - t0; first = t if first is None else first; last = t
        patched = (R.get("patch_chars") or 0) > 0
        runs[iid].append(dict(s=R["agent_s"], solved=bool(R.get("resolved")), patched=patched,
                              first=first if patched else None, last=last if patched else None))
tasks = {t: v for t, v in runs.items() if len(v) >= 3}
print(len(tasks), "tasks with >= 3 runs;", sum(len(v) for v in tasks.values()), "runs")
SPEED = {1: 32.3, 2: 30.2, 3: 26.9}
def cut(run, C):  # C in local seconds
    sol = run["solved"] and (run["s"] <= C or (run["last"] is not None and run["last"] <= C))
    pat = run["patched"] and (run["s"] <= C or (run["first"] is not None and run["first"] <= C))
    return sol, pat, min(run["s"], C)
random.seed(7)
def single(C_scorer):
    C = C_scorer * SPEED[1] / SPEED[2]  # a single agent on the scorer is faster than our local runs
    sol = []; tm = []
    for t, v in tasks.items():
        sol.append(st.mean(cut(r, C)[0] for r in v)); tm.append(st.mean(cut(r, C)[2] * SPEED[2] / SPEED[1] for r in v))
    return sum(sol), st.mean(tm)
def bestof(k, C_scorer, n=60):
    f = SPEED[2] / SPEED[k]  # branch slowdown vs local
    C = C_scorer / f
    o = rn = ff = 0.0; tm = []
    for t, v in tasks.items():
        combos = list(itertools.combinations(range(len(v)), k)); random.shuffle(combos); combos = combos[:n]
        so = sr = sf = 0.0; tt = 0.0
        for cmb in combos:
            cs = [cut(v[i], C) for i in cmb]
            so += any(c[0] for c in cs)
            ne = [c for c in cs if c[1]]
            sr += st.mean(c[0] for c in ne) if ne else 0.0
            sf += min(ne, key=lambda c: c[2])[0] if ne else 0.0
            tt += max(c[2] for c in cs) * f
        o += so / len(combos); rn += sr / len(combos); ff += sf / len(combos); tm.append(tt / len(combos))
    return o, rn, ff, st.mean(tm)
N = len(tasks)
s8, t8 = single(480)
print(f"single, 8 min: solved {s8:.1f}/{N} | mean task time on the scorer {t8:.0f} s")
for k in (2, 3):
    for cap in (480, 420, 390, 360, 330, 300):
        o, rn, ff, tm = bestof(k, cap)
        print(f"best-of-{k}, branch cap {cap} s: oracle {o:.1f} | random non-empty {rn:.1f} | first finished with a patch {ff:.1f} | mean task time {tm:.0f} s")

print("\nrace: the first branch that ENDS (submits) with a patch ends the task and its patch is kept "
      "(swegemma agent_runner breaks when patch_submitted and a final text event arrives); "
      "if no branch submits before the cap, the task runs to the cap and a random non-empty patch is kept")
def race(k, C_scorer, n=60):
    f = SPEED[2] / SPEED[k]; C = C_scorer / f
    tot = 0.0; tm = []; early = 0; cnt = 0
    for t, v in tasks.items():
        combos = list(itertools.combinations(range(len(v)), k)); random.shuffle(combos); combos = combos[:n]
        s = 0.0; tt = 0.0
        for cmb in combos:
            br = [v[i] for i in cmb]; cs = [cut(r, C) for r in br]
            fin = [(min(r["s"], C), c[0]) for r, c in zip(br, cs) if c[1] and r["s"] < C - 1]  # ended early with a patch
            cnt += 1
            if fin:
                tfin, sol = min(fin); s += sol; tt += tfin * f; early += 1
            else:
                ne = [c for c in cs if c[1]]; s += st.mean(c[0] for c in ne) if ne else 0.0
                tt += max(c[2] for c in cs) * f
        tot += s / len(combos); tm.append(tt / len(combos))
    return tot, st.mean(tm), early / cnt
for k in (2, 3):
    for cap in (480, 450, 420):
        sol, tm, e = race(k, cap)
        print(f"race best-of-{k}, branch cap {cap} s: solved {sol:.1f}/{N} (single 8 min {s8:.1f}) | mean task time {tm:.0f} s (single {t8:.0f}) | ended by a submit {e:.0%}")
