"""evidc runs: seconds from the first model call to the first edit_file / write_file call; agent_s; resolved."""
import json, glob, collections, ast, statistics as st, sys
def names(rep):
    if isinstance(rep, str):
        try: rep = ast.literal_eval(rep)
        except Exception:
            try: rep = json.loads(rep)
            except Exception: return []
    tc = ((rep or {}).get("message") or {}).get("tool_calls") or []
    if isinstance(tc, str):
        try: tc = ast.literal_eval(tc)
        except Exception: return []
    return [c["function"]["name"] for c in tc]
def load(arm="evidc"):
    res = {}
    for d in glob.glob("data/results/2026-11-*_skill_*"):
        try:
            for l in open(d + "/results/gen_per_task.jsonl"):
                r = json.loads(l)
                if r["arm"] == arm: res[(d, r["instance_id"] + "#a" + r["attempt"])] = r
        except FileNotFoundError: pass
    runs = collections.defaultdict(list)
    for d in glob.glob("data/results/2026-11-*_skill_*"):
        try: f = open(d + "/requests/requests.jsonl", errors="replace")
        except FileNotFoundError: continue
        for l in f:
            if f"#a{arm}." not in l: continue
            r = json.loads(l)
            n = names(r["reply"])
            runs[(d, r["job"])].append((float(r["t"]) - float(r["seconds"]), float(r["t"]), any(x in ("edit_file", "write_file") for x in n), n))
    rows = []
    for k, v in runs.items():
        if k not in res: continue
        v.sort(); t0 = v[0][0]
        fe = next((s - t0 for s, t, e, n in v if e), None)
        rows.append({"fe": fe, "agent_s": res[k]["agent_s"], "solved": bool(res[k]["resolved"]), "end": res[k]["end"], "task": res[k]["instance_id"], "calls": len(v)})
    return rows
if __name__ == "__main__":
    rows = load()
    tot = sum(r["agent_s"] for r in rows)
    print("runs", len(rows), "solved", sum(r["solved"] for r in rows), "| agent h %.1f" % (tot / 3600))
    for t1 in (150, 210, 270, 330, 390):
        ne = [r for r in rows if r["fe"] is None or r["fe"] > t1]
        lost = sum(r["solved"] for r in ne); saved = sum(max(0, r["agent_s"] - t1) for r in ne)
        print(f"no edit by {t1:3}s: {len(ne):3} runs ({len(ne)/len(rows):.0%}) solved {lost:2} ({lost/max(1,len(ne)):.0%}) | their time after {t1}s = {saved/tot:.0%} of all agent time")
    s = [r["fe"] for r in rows if r["solved"] and r["fe"] is not None]
    print("solved runs: first edit at median %.0fs, quartiles %s, max %.0fs" % (st.median(s), [round(x) for x in st.quantiles(s, n=4)], max(s)))
