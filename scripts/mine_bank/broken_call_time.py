"""Time the cut-apart (broken) tool calls cost (user 2026-11-19: 'i like how broken calls reduced that much, i need the time
of that as well'). Run: python3 -I scripts/mine_bank/broken_call_time.py   (repo root; logs only)
A broken call = a model reply whose tool result says 'mandatory input parameters are not present'. Its cost = the seconds of
the request that produced it (the reply's generation time; the failed tool itself returns at once). Per arm in r118, and for
every sb1 run with requests in the bank (2026-11-1* folders): broken calls per run, seconds per run, share of model time,
runs that ended on time with / without broken calls."""
import collections, glob, json, statistics as st
CUT = "mandatory input parameters are not present"


def runs(d, arms):
    G = {}
    for l in open(f"{d}/results/gen_per_task.jsonl"):
        g = json.loads(l)
        if g.get("arm") in arms:
            G[f"{g['instance_id']}#a{g['attempt']}"] = g
    R = collections.defaultdict(list)
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        try:
            r = json.loads(l)
        except Exception:
            continue
        if r.get("job") in G:
            m = r["request"]["messages"]
            k = len(m)
            while k and m[k - 1].get("role") == "tool":
                k -= 1
            R[r["job"]].append((float(r["t"]), float(r.get("seconds") or 0), any(CUT in str(x.get("content")) for x in m[k:])))
    out = []
    for job, rs in R.items():
        rs.sort()
        bad = [rs[i - 1][1] for i in range(1, len(rs)) if rs[i][2]]  # the reply before a cut-apart result made the broken call
        out.append(dict(arm=G[job]["arm"], n=len(bad), s=sum(bad), model=sum(x[1] for x in rs), end=G[job]["end"]))
    return out


def show(name, xs):
    if not xs:
        return
    n = len(xs)
    hit = [x for x in xs if x["n"]]
    print(f"  {name:22} runs {n:3} | broken calls/run {sum(x['n'] for x in xs) / n:4.2f} | broken-call seconds/run {sum(x['s'] for x in xs) / n:5.1f}"
          f" ({100 * sum(x['s'] for x in xs) / max(1, sum(x['model'] for x in xs)):4.1f}% of model time) | runs with any {len(hit):3}: mean {st.mean([x['s'] for x in hit] or [0]):5.1f} s, max {max([x['s'] for x in hit] or [0]):5.0f} s"
          f" | time ends: with broken {sum(x['end'] == 'time' for x in hit)}/{len(hit)}, without {sum(x['end'] == 'time' for x in xs if not x['n'])}/{n - len(hit)}")


print("#### r118 (same run)")
r118 = [x for d in sorted(glob.glob("data/results/2026-11-19_skill_r118_p*")) for x in runs(d, ("sb1", "sb1h", "sb1hpp", "sb7h"))]
for a in ("sb1", "sb1h", "sb1hpp", "sb7h"):
    show(a, [x for x in r118 if x["arm"] == a])
print("#### bank: every sb1 run with requests (2026-11-1*, r118 included)")
bank = []
for d in sorted(glob.glob("data/results/2026-11-1*")):
    if glob.glob(f"{d}/requests/requests.jsonl") and glob.glob(f"{d}/results/gen_per_task.jsonl"):
        try:
            bank += runs(d, ("sb1",))
        except Exception as e:
            print("skip", d, e)
show("bank sb1", bank)
