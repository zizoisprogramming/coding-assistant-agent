import collections, json, re, statistics as st, sys
rows=[json.loads(l) for l in open(sys.argv[1])]
P=[r for r in rows if r["arm"]=="pub024" and "e4b" not in r["folder"] and "replay" not in r["folder"] and "probe" not in r["folder"]]
def kind(cmd):
    c=cmd.strip()
    if re.search(r"pytest",c): return "pytest"
    if re.search(r"pip ",c): return "pip"
    if re.search(r"<<|cat >|> /tmp/.*\.py|echo .*> .*\.py",c): return "write+run script"
    if re.search(r"python3? -c",c):
        if re.search(r"inspect|getsource|__file__|print\(open",c): return "python -c (read code)"
        return "python -c (try code)"
    if re.search(r"python3? \S+\.py",c): return "python file"
    if re.search(r"^(grep|rg|git grep)|\| *grep",c): return "grep"
    if re.search(r"^(sed|cat|head|tail|nl|awk)",c): return "print file"
    if re.search(r"^(find|ls|tree)",c): return "list"
    if c.startswith("git"): return "git"
    return "other"
K=collections.defaultdict(lambda: collections.Counter())
errs=collections.Counter(); pyerr=collections.Counter()
for r in P:
    for c in r["calls"]:
        if c["n"]!="run_command": continue
        k=kind(str(c["a"].get("command",""))); err='"error_type"' in c["r"] or '"error"' in c["r"][:20]
        K[k]["n"]+=1; K[k]["err"]+=err; K[k]["nopatch_runs"]+= (r["patch"]==0)
        if err and k.startswith("python") or (err and k in("write+run script","python file")):
            m=re.search(r"(\w+Error|\w+Exception)[:\\]",c["r"]); pyerr[m.group(1) if m else "?"]+=1
        if err and k=="grep": errs["grep exit1 (no match)" if '"exit_code": 1' in c["r"] or "exit_code\": 1" in c["r"] else "grep other"]+=1
tot=sum(v["n"] for v in K.values())
print(f"pub024 runs {len(P)}, run_command calls {tot} ({tot/len(P):.1f}/run)")
for k,v in sorted(K.items(),key=lambda x:-x[1]["n"]):
    print(f"  {k:24} {v['n']:5} ({v['n']/len(P):4.1f}/run)  errors {v['err']/v['n']:4.0%}")
print("python errors:",pyerr.most_common(12))
print("grep:",errs)
