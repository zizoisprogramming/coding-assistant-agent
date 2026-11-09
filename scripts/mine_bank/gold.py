import collections, json, re, statistics as st, sys
T={}
for l in open("data/tasks.jsonl"):
    t=json.loads(l); T[t["instance_id"]]=set(re.findall(r"^--- a/(\S+)",t["patch"],re.M))
rows=[json.loads(l) for l in open(sys.argv[1])]
rows=[r for r in rows if "e4b" not in r["folder"] and "replay" not in r["folder"] and "probe" not in r["folder"] and r["task"] in T]
def touch(c,gold):
    s=json.dumps(c["a"])
    if c["n"]=="read_file": return any(str(c["a"].get("filepath","")).endswith(g) or g.endswith(str(c["a"].get("filepath","")).lstrip("./")) for g in gold)
    if c["n"]=="run_command": return any(g in c["r"] or g in s for g in gold)
    return False
def tread(c,gold): return c["n"]=="read_file" and any(str(c["a"].get("filepath","")).lstrip("./").endswith(g) or g.endswith(str(c["a"].get("filepath","")).lstrip("./")) for g in gold)
grp=collections.defaultdict(list)
for r in rows: grp[r["task"],r["arm"]].append(r)
mixed=[r for v in grp.values() if any(x["resolved"] for x in v) and not all(x["resolved"] for x in v) for r in v]
cls=collections.defaultdict(list)
for r in mixed:
    gold=T[r["task"]]; c=r["calls"]
    ft=next((x["t"] for x in c if touch(x,gold)),None); fr=next((x["t"] for x in c if tread(x,gold)),None)
    k="solved" if r["resolved"] else ("wrong patch" if r["patch"] else "no patch")
    cls[k].append((ft,fr,r))
for k,v in cls.items():
    seen=[a for a,b,_ in v if a is not None]; rd=[b for a,b,_ in v if b is not None]
    print(f"{k:12} n={len(v):4}  gold file seen {len(seen)/len(v):4.0%} (median at {st.median(seen) if seen else 0:4.0f}s)  gold file read {len(rd)/len(v):4.0%} (median at {st.median(rd) if rd else 0:4.0f}s)")
# no-patch runs: what happens after the gold file is read
np=[(a,b,r) for a,b,r in cls["no patch"] if b is not None]
after=[]
for a,b,r in np:
    after.append(dict(left=480-b, calls_after=sum(1 for x in r["calls"] if x["t"]>b), long_after=sum(1 for q in r["reqs"] if q["t"]>b and q["s"]>=30),
                      out_after=sum(q["out"] or 0 for q in r["reqs"] if q["t"]>b), budget=int(any("budget" in x["r"].lower() and "exhaust" in x["r"].lower() for x in r["calls"])),
                      tried_edit=int(any(x["n"]=="edit_file" for x in r["calls"]))))
print(f"\nno-patch runs that read the gold file: {len(np)}; after reading it: time left median {st.median(x['left'] for x in after):.0f}s, calls {st.mean(x['calls_after'] for x in after):.1f}, long replies {st.mean(x['long_after'] for x in after):.1f}, tokens {st.mean(x['out_after'] for x in after):.0f}; budget-exhausted {sum(x['budget'] for x in after)}; tried an edit (failed/refused) {sum(x['tried_edit'] for x in after)}")
ends=collections.Counter(r["end"] for _,_,r in cls["no patch"]); print("no-patch end reasons:",ends)
