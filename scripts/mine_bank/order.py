import collections, glob, json, os, re
C=collections.Counter(); tail=collections.Counter(); runs=collections.defaultdict(lambda: collections.Counter())
for D in sorted(glob.glob("data/results/2026-*")):
    if "e4b" in D or "probe" in D or "replay" in D: continue
    rq=D+"/requests/requests.jsonl"
    if not os.path.exists(rq): continue
    R={}; calls=[]
    for l in open(rq):
        try: r=json.loads(l)
        except Exception: continue
        if not (isinstance(r.get("reply"),dict) and r.get("job")): continue
        for m in r["request"]["messages"]:
            if m.get("role")=="tool": R.setdefault(m.get("tool_call_id"),str(m.get("content")))
        for c in r["reply"]["message"].get("tool_calls") or []:
            if c["function"]["name"]=="edit_file": calls.append((r["job"],c))
    for job,c in calls:
        raw=c["function"]["arguments"]; res=R.get(c.get("id"),"")
        io=raw.find('"old_string"'); inn=raw.find('"new_string"')
        order="old first" if (io>=0 and (inn<0 or io<inn)) else "new first" if inn>=0 else "?"
        st="bad" if "mandatory" in res else "fail" if '"error' in res[:30] else "ok"
        C[order,st]+=1; runs[job][order]+=1
        if st=="bad":
            m=re.search(r'(.{0,3})(,old_string:)',raw); tail[(m.group(1) if m else "no ',old_string:' inside")]+=1
for o in ["old first","new first"]:
    tot=sum(v for (a,b),v in C.items() if a==o)
    print(f"{o:10} calls {tot:5}  broken {C[o,'bad']:4} ({C[o,'bad']/max(1,tot):5.1%})  other failure {C[o,'fail']/max(1,tot):5.1%}")
print("chars just before ',old_string:' in broken calls:", tail.most_common(8))
mixed=sum(1 for v in runs.values() if v["old first"] and v["new first"]); nf=sum(1 for v in runs.values() if v["new first"])
print(f"runs with any edit {len(runs)}, runs that ever wrote new first {nf}, runs using both orders {mixed}")
