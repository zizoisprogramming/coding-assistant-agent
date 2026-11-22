"""r140: sk_a2 vs sk_a2r (RUN IT after show) on the 8 solvable dev16 in two shards (bars in docs/PLAN.md RUN BUILT r140).
Per run: outcome, end, calls, agent s, capped replies (>= 1,800 output tokens), seconds in them, RUN IT shown, probe runs (a python3
heredoc / -c that imports the shown module after a RUN IT), source change, empty submit. Run: python3 -I scripts/mine_bank/r140.py"""
import ast, collections, glob, json, re, statistics as st
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
A = collections.defaultdict(collections.Counter); T = collections.defaultdict(list)
for d in sorted(glob.glob(str(ROOT / "data/results/2026-11-22_skill_r140_s*"))):
    G = {}
    for l in open(f"{d}/results/gen_per_task.jsonl"):
        g = json.loads(l); G[g["instance_id"] + "#a" + g["attempt"]] = g
    by = collections.defaultdict(list)
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        r = json.loads(l); by[r["job"]].append(r)
    for job, rs in sorted(by.items()):
        g = G.get(job)
        if not g: continue
        rs.sort(key=lambda r: float(r["t"])); arm = g["arm"]
        cap = capsec = runit_seen = probes = after_probe_long = 0; mods = set(); calls = []; prev_probe = False
        for r in rs:
            msgs = r["request"]["messages"]
            if len(msgs) <= 1: continue
            last = str(msgs[-1].get("content"))
            if "RUN IT, DO NOT TRACE IT" in last:
                runit_seen += 1
                mods |= set(re.findall(r"from ([\w.]+) import", last.split("RUN IT, DO NOT TRACE IT")[-1]))
            rep = r["reply"] if isinstance(r["reply"], dict) else ast.literal_eval(str(r["reply"]))
            o = (rep.get("usage") or {}).get("completion_tokens") or 0
            if o >= 1800: cap += 1; capsec += float(r["seconds"])
            if prev_probe and o >= 1800: after_probe_long += 1
            prev_probe = False
            for c in (rep.get("message") or {}).get("tool_calls") or []:
                a = c["function"]["arguments"]
                isp = ("python3 -" in a or "python -c" in a or "python3 -c" in a) and any(f"from {m} import" in a or f"import {m}" in a for m in mods) and "OLD_TEXT" not in a and ".replace(" not in a
                probes += isp; prev_probe = prev_probe or isp
                calls.append("PROBE" if isp else c["function"]["name"][:6] if "a.py" not in a else "apy")
        pf = list(Path(d).glob(f"results/gen/patches/{job.split('#')[0]}__a{arm}.*.diff"))
        files = re.findall(r"^\+\+\+ b/(\S+)", pf[0].read_text(errors="replace"), re.M) if pf else []
        src = [f for f in files if f.endswith(".py") and "test" not in f and "repro" not in f]
        solved = g["resolved"] in (True, "True"); c = A[arm]
        c["runs"] += 1; c["solved"] += solved; c["time ends"] += g["end"] == "time"; c["no source change"] += not src
        c["empty submit"] += ("submit" in calls) and not src; c["capped replies"] += cap; c["capped s"] += round(capsec)
        c["runs with RUN IT shown"] += runit_seen > 0; c["runs with a probe run"] += probes > 0; c["probe runs"] += probes
        c["capped reply right after a probe"] += after_probe_long
        T[arm].append(g["agent_s"])
        print(f"{Path(d).name[-6:]} {arm:6} {job.split('#')[0]:14} {'SOLVED' if solved else 'failed'} {g['end']:4} {g['agent_s']:4.0f}s calls {len(calls):2} capped {cap} ({capsec:3.0f}s) RUN IT {runit_seen} probes {probes} src {src}")
        print("        " + " ".join(calls))
print()
for arm in sorted(A):
    print(f"  {arm}: " + " | ".join(f"{k} {v}" for k, v in A[arm].items()) + f" | mean agent s {st.mean(T[arm]):.0f}")
