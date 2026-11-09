import collections, json, re, statistics as st, sys
rows=[json.loads(l) for l in open(sys.argv[1])]
arm=sys.argv[2]
P=[r for r in rows if r["arm"]==arm and "e4b" not in r["folder"] and "replay" not in r["folder"] and "probe" not in r["folder"]]
def secs(r,c):
    q=r["reqs"][c["i"]]; n=sum(1 for x in r["calls"] if x["i"]==c["i"]); return q["s"]/max(1,n)
modes={
 "edit: old_string lost (garbled)": lambda r,c,p: c["n"]=="edit_file" and "mandatory" in c["r"],
 "write_file outside /workspace": lambda r,c,p: c["n"]=="write_file" and "traversal" in c["r"],
 "edit: old_string not found / ambiguous": lambda r,c,p: c["n"]=="edit_file" and "FileEditError" in c["r"],
 "python -c SyntaxError": lambda r,c,p: c["n"]=="run_command" and "SyntaxError" in c["r"],
 "grep found nothing (exit 1)": lambda r,c,p: c["n"]=="run_command" and re.search(r"grep",str(c["a"].get("command",""))) and '"exit_code": 1' in c["r"].replace("\\",""),
 "exact repeat of an earlier call": lambda r,c,p: (c["n"],json.dumps(c["a"],sort_keys=True)) in p,
 "read_file truncated at 150 lines": lambda r,c,p: c["n"]=="read_file" and '"is_truncated": true' in c["r"],
 "call refused: budget exhausted": lambda r,c,p: "exhaust" in c["r"].lower(),
 "unknown/dead tool": lambda r,c,p: c["n"] in ("search_similar_code","get_code_neighbors","get_code_subgraph"),
}
A={k:collections.Counter() for k in modes}
for r in P:
    prev=set(); hit=collections.Counter(); sec=collections.Counter()
    for c in r["calls"]:
        for k,f in modes.items():
            if f(r,c,prev): hit[k]+=1; sec[k]+=secs(r,c)
        prev.add((c["n"],json.dumps(c["a"],sort_keys=True)))
    for k in modes:
        if hit[k]:
            A[k]["runs"]+=1; A[k]["calls"]+=hit[k]; A[k]["sec"]+=sec[k]; A[k]["nopatch"]+= r["patch"]==0; A[k]["solved"]+=r["resolved"]
print(f"{arm}: {len(P)} runs, solved {sum(r['resolved'] for r in P)/len(P):.0%}, no patch {sum(r['patch']==0 for r in P)/len(P):.0%}")
print(f"{'mistake':40}{'runs':>6}{'% runs':>8}{'calls/run':>10}{'s/run hit':>10}{'no patch':>9}{'solved':>8}")
for k,v in A.items():
    n=max(1,v["runs"]); print(f"{k:40}{v['runs']:>6}{v['runs']/len(P):>8.0%}{v['calls']/n:>10.1f}{v['sec']/n:>10.0f}{v['nopatch']/n:>9.0%}{v['solved']/n:>8.0%}")
