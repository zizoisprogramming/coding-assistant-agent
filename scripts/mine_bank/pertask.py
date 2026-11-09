import collections, json, re, sys
rows=[json.loads(l) for l in open(sys.argv[1])]
rows=[r for r in rows if "e4b" not in r["folder"] and "replay" not in r["folder"] and "probe" not in r["folder"]]
T=collections.defaultdict(collections.Counter)
for r in rows:
    if r["arm"]!="pub024": continue
    t=T[r["task"]]; c=r["calls"]; t["n"]+=1; t["solved"]+=r["resolved"]; t["nopatch"]+=r["patch"]==0
    t["garble"]+=any("mandatory" in x["r"] for x in c); t["tmpw"]+=any(x["n"]=="write_file" and "traversal" in x["r"] for x in c)
    t["syntax"]+=any("SyntaxError" in x["r"] for x in c and x["n"]=="run_command") if False else any(x["n"]=="run_command" and "SyntaxError" in x["r"] for x in c)
    t["budget"]+=any("exhaust" in x["r"].lower() for x in c)
    t["mistake"]+=any(("mandatory" in x["r"]) or (x["n"]=="write_file" and "traversal" in x["r"]) or (x["n"]=="run_command" and "SyntaxError" in x["r"]) or "exhaust" in x["r"].lower() for x in c)
print(f"{'task':16}{'n':>4}{'solve':>7}{'nopatch':>8}{'garble':>7}{'/tmp w':>7}{'syntax':>7}{'budget':>7}{'any':>6}")
for k,t in sorted(T.items(),key=lambda x:-x[1]["mistake"]/x[1]["n"]):
    if t["n"]<5: continue
    n=t["n"]; print(f"{k:16}{n:>4}{t['solved']/n:>7.0%}{t['nopatch']/n:>8.0%}{t['garble']/n:>7.0%}{t['tmpw']/n:>7.0%}{t['syntax']/n:>7.0%}{t['budget']/n:>7.0%}{t['mistake']/n:>6.0%}")
