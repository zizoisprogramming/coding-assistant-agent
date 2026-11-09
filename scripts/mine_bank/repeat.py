import collections, json, re, statistics as st, sys
rows=[json.loads(l) for l in open(sys.argv[1])]
P=[r for r in rows if r["arm"]=="pub024" and "e4b" not in r["folder"] and "replay" not in r["folder"] and "probe" not in r["folder"]]
C=collections.Counter(); kinds=collections.Counter(); comp=[]; lines=[]; full=0; nread=0
for r in P:
    q=r["reqs"]
    # compaction boundary = request index where message count drops
    cb=[i for i in range(1,len(q)) if q[i]["tools"] and q[i-1]["tools"] and q[i]["nmsg"]<q[i-1]["nmsg"]-2]
    cb2=[i for i in range(1,len(q)) if not q[i]["tools"]]  # summarization requests
    bounds=sorted(set(cb)|set(cb2)); comp.append(len(cb2))
    first={}
    for c in r["calls"]:
        k=(c["n"],json.dumps(c["a"],sort_keys=True))
        if c["n"]=="read_file":
            nread+=1; s=c["a"].get("start_line"); e=c["a"].get("end_line")
            if s is None or e is None: full+=1
            else:
                try: lines.append(int(e)-int(s)+1)
                except Exception: pass
        if k in first:
            j=first[k]; between=any(j<b<=c["i"] for b in bounds)
            C["after compaction" if between else "no compaction between"]+=1; kinds[c["n"],between]+=1
        else: first[k]=c["i"]
print("exact repeats:",dict(C)); print("by tool (tool, compaction between):",kinds.most_common(8))
print(f"summarization requests per run: mean {st.mean(comp):.1f}")
print(f"read_file calls {nread}: without an end line (up to 150 lines) {full/nread:.0%}; ranged reads median {st.median(lines)} lines, mean {st.mean(lines):.0f}")
