import collections, json, re, statistics as st, sys
rows=[json.loads(l) for l in open(sys.argv[1])]
arm=sys.argv[2] if len(sys.argv)>2 else "pub024"
P=[r for r in rows if (r["arm"]==arm or arm=="all") and "e4b" not in r["folder"] and "replay" not in r["folder"] and "probe" not in r["folder"]]
NP=[r for r in P if not r["patch"]]
print(f"{arm}: runs {len(P)}, no patch {len(NP)} ({len(NP)/len(P):.0%}), solved {sum(r['resolved'] for r in P)}")
cat=collections.Counter(); errt=collections.Counter(); ex=collections.defaultdict(list)
for r in NP:
    E=[c for c in r["calls"] if c["n"] in ("edit_file","write_file")]
    budget=any("exhaust" in c["r"].lower() for c in r["calls"])
    if E:
        for c in E:
            m=re.search(r'"error_type": "(\w+)"',c["r"]); em=re.search(r'"error_message": "([^"]{0,60})',c["r"])
            k=(m.group(1) if m else ("mandatory-missing" if "mandatory" in c["r"] else "ok?"))
            if k=="ok?" and "exhaust" in c["r"].lower(): k="budget refused"
            errt[k+(" | "+em.group(1)[:50] if em and m else "")]+=1
        ok=[c for c in E if '"error' not in c["r"][:40] and "mandatory" not in c["r"] and "exhaust" not in c["r"].lower()]
        k="edits only to tests/tmp (no src)" if ok else ("edit refused by call budget" if all("exhaust" in c["r"].lower() for c in E) else "edit attempts all failed")
    else:
        k=f"never tried an edit, end={r['end']}"+(" (budget hit)" if budget else "")
    cat[k]+=1; ex[k].append(r)
for k,v in cat.most_common(): print(f"  {v:4} ({v/len(NP):4.0%})  {k}")
print("edit errors in no-patch runs:"); [print("   ",v,k) for k,v in errt.most_common(10)]
# end=ok, never tried an edit: what did the model's last message say?
k=[x for x in ex if x.startswith("never tried an edit, end=ok")]
print("\nlast replies when the model stopped without editing (first 6):")
for kk in k:
    for r in ex[kk][:6]:
        print("  -", r["task"], r["folder"][:22], "| last call:", r["calls"][-1]["n"] if r["calls"] else None, "| reqs", len(r["reqs"]), "| last req s", r["reqs"][-1]["s"], "fin", r["reqs"][-1]["fin"])
