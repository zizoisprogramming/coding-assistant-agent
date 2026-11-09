"""One row per run: outcome + full call sequence with timing. Usage: extract.py OUT.jsonl [FOLDER_GLOB] (default: all results)"""
import collections, glob, json, os, sys
out = open(sys.argv[1], "w"); n = 0
for D in sorted(glob.glob(sys.argv[2] if len(sys.argv) > 2 else "data/results/2026-*")):
    rq = D + "/requests/requests.jsonl"; gp = D + "/results/gen_per_task.jsonl"
    if not (os.path.exists(rq) and os.path.exists(gp)): continue
    G = {}
    for r in map(json.loads, open(gp)): G[r["instance_id"] + "#a" + r["attempt"]] = r
    J = collections.defaultdict(list)
    for l in open(rq):
        try: r = json.loads(l)
        except Exception: continue
        if isinstance(r.get("reply"), dict) and r.get("job"):
            J[r["job"]].append(r)
    for job, q in J.items():
        g = G.get(job)
        if not g: continue
        q.sort(key=lambda r: r["t"]); t0 = q[0]["t"]; R = {}
        for r in q:
            for m in r["request"]["messages"]:
                if m.get("role") == "tool": R.setdefault(m.get("tool_call_id"), str(m.get("content")))
        calls = []; reqs = []
        for i, r in enumerate(q):
            nxt = q[i + 1]["t"] if i + 1 < len(q) else None
            gap = (nxt - (r["t"] + r["seconds"])) if nxt else None
            u = r["reply"].get("usage") or {}
            sysm = r["request"]["messages"][0] if r["request"]["messages"] else {}
            reqs.append(dict(t=round(r["t"] - t0, 1), s=round(r["seconds"], 1), gap=gap and round(gap, 1),
                             pin=u.get("prompt_tokens"), out=u.get("completion_tokens"), fin=r["reply"].get("finish_reason"),
                             tools=bool(r["request"].get("tools")), nmsg=len(r["request"]["messages"]),
                             sys=str(sysm.get("content"))[:80] if sysm.get("role") == "system" else ""))
            tcs = r["reply"]["message"].get("tool_calls") or []
            for c in tcs:
                nm = c["function"]["name"]; raw = c["function"]["arguments"]
                try: a = json.loads(raw)
                except Exception: a = {"_bad": raw[:200]}
                res = R.get(c.get("id"), "")
                ak = {k: (v if isinstance(v, (int, float)) or v is None else str(v)[:300]) for k, v in a.items()}
                calls.append(dict(i=i, t=round(r["t"] + r["seconds"] - t0, 1), gap=gap and round(gap / max(1, len(tcs)), 1), n=nm, a=ak,
                                  alen={k: len(str(v)) for k, v in a.items()}, rlen=len(res), r=res[:400]))
        row = dict(folder=os.path.basename(D), job=job, arm=g["arm"], task=g["instance_id"], resolved=bool(g["resolved"]),
                   patch=g.get("patch_chars") or 0, end=g.get("end"), agent_s=g.get("agent_s"), wall_s=g.get("wall_s"),
                   tool_calls=g.get("tool_calls"), calls=calls, reqs=reqs)
        out.write(json.dumps(row) + "\n"); n += 1
print(n, "runs")
