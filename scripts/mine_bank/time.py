import collections, json, statistics as st, sys
rows=[json.loads(l) for l in open(sys.argv[1])]
rows=[r for r in rows if "e4b" not in r["folder"] and "probe" not in r["folder"] and "replay" not in r["folder"]]
print(len(rows),"runs (31B)", sum(r["arm"]=="pub024" for r in rows),"pub024")
P=[r for r in rows if r["arm"]=="pub024"]
def br(R,label):
    model=[sum(q["s"] for q in r["reqs"]) for r in R]; tool=[sum((q["gap"] or 0) for q in r["reqs"]) for r in R]
    print(f"{label}: n={len(R)} agent {st.mean(r['agent_s'] or 0 for r in R):.0f}s  model {st.mean(model):.0f}s  between-requests {st.mean(tool):.0f}s  requests {st.mean(len(r['reqs']) for r in R):.1f}")
    # model time split: long generations
    big=[sum(q["s"] for q in r["reqs"] if q["s"]>=30) for r in R]
    print(f"   model time in requests >=30s: {st.mean(big):.0f}s; requests>=30s per run {st.mean(sum(q['s']>=30 for q in r['reqs']) for r in R):.2f}")
    outs=[q["out"] or 0 for r in R for q in r["reqs"]]; secs=[q["s"] for r in R for q in r["reqs"]]
    print(f"   output tokens/run {st.mean(sum(q['out'] or 0 for q in r['reqs']) for r in R):.0f}, tok/s overall {sum(outs)/sum(secs):.1f}")
br(P,"pub024"); br(rows,"all")
# per tool gap
g=collections.defaultdict(list)
for r in P:
    for c in r["calls"]:
        if c["gap"] is not None: g[c["n"]].append(c["gap"])
for k,v in sorted(g.items(),key=lambda x:-sum(x[1])):
    print(f"   {k:22} n={len(v):5} mean gap {st.mean(v):5.1f}s  median {st.median(v):4.1f}  total/run {sum(v)/len(P):5.1f}s")
# run_command slow ones: what commands
sl=collections.Counter()
for r in P:
    for c in r["calls"]:
        if c["n"]=="run_command" and (c["gap"] or 0)>=10:
            cmd=str(c["a"].get("command",""))
            k="pytest" if "pytest" in cmd else "pip" if "pip" in cmd else "python" if "python" in cmd else "grep" if "grep" in cmd else "find" if "find" in cmd else "other"
            sl[k]+=1
print("run_command >=10s by kind:", dict(sl))
