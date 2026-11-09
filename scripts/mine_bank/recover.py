import collections, json, re, sys
rows=[json.loads(l) for l in open(sys.argv[1])]
rows=[r for r in rows if "e4b" not in r["folder"] and "replay" not in r["folder"] and "probe" not in r["folder"]]
nxt=collections.Counter(); single=collections.Counter(); loops=[]
for r in rows:
    c=r["calls"]
    for x in c:
        if "mandatory input parameters" in x["r"]: single[x["n"]]+=1
    i=0
    while i<len(c):
        if c[i]["n"]=="edit_file" and "mandatory" in c[i]["r"]:
            j=i; 
            while j+1<len(c) and c[j+1]["n"]=="edit_file" and "mandatory" in c[j+1]["r"]: j+=1
            loops.append(j-i+1)
            if j+1<len(c):
                y=c[j+1]; ok='"error' not in y["r"][:30] and "mandatory" not in y["r"] and "exhaust" not in y["r"].lower()
                kind=y["n"]+("" if y["n"]!="run_command" else (":python-edit" if re.search(r"open\(.*(write|w\")|\.replace\(|sed -i",str(y["a"].get("command",""))) else ":other"))
                nxt[kind, "ok" if ok else "fail"]+=1
            else: nxt["(run ended)",""]+=1
            i=j+1
        else: i+=1
print("calls that lost a required argument, by tool:", dict(single))
print("garbled-edit streaks:", len(loops), " length distribution:", sorted(collections.Counter(loops).items())[:12])
print("first call after a streak:", nxt.most_common(12))
