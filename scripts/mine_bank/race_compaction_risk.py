"""Race of k full single agents in one ADK ParallelAgent session: how often does any branch reach compaction
(issue text dropped from its request = token threshold hit) before the race ends (first branch to end with a patch)?
Each such compaction can crash the whole task in ADK 1.36.1 (bo3, 2026-10-29: 11/24 crashed).
Usage: python3 -I scripts/mine_bank/race_compaction_risk.py"""
import json, glob, collections, random, itertools, statistics as st
ARMS = {"pub024", "combo1"}
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
        q = [r for r in sorted(q, key=lambda r: r["t"]) if r["request"].get("tools")]
        if not q: continue
        t0 = q[0]["t"]
        fu = next((m.get("content") for m in q[0]["request"]["messages"] if m.get("role") == "user"), None)
        if not isinstance(fu, str) or len(fu) < 50: continue
        probe = fu[:200]; comp = None
        for r in q:
            if not any(isinstance(m.get("content"), str) and probe in m["content"] for m in r["request"]["messages"]):
                comp = r["t"] - t0; break
        runs[iid].append(dict(s=R["agent_s"], patched=(R.get("patch_chars") or 0) > 0, comp=comp))
tasks = {t: v for t, v in runs.items() if len(v) >= 3}
random.seed(3)
print(len(tasks), "tasks;", "compaction in", sum(r["comp"] is not None for v in tasks.values() for r in v), "of", sum(len(v) for v in tasks.values()), "runs; onset median",
      st.median([r["comp"] for v in tasks.values() for r in v if r["comp"] is not None]), "s")
for k in (2, 3):
    risk = []
    for t, v in tasks.items():
        for cmb in list(itertools.combinations(range(len(v)), k))[:60]:
            br = [v[i] for i in cmb]
            ends = [r["s"] for r in br if r["patched"] and r["s"] < 479]
            end = min(ends) if ends else 480
            risk.append(any(r["comp"] is not None and r["comp"] < end for r in br))
    print(f"race of {k}: some branch compacts before the race ends in {st.mean(risk):.0%} of tasks")
