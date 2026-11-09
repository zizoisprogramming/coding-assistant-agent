import collections, glob, json, os, re, statistics as st
bad=[]; good=[]; keysets=collections.Counter(); retry=collections.Counter()
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
            if c["function"]["name"]=="edit_file": calls.append((r["job"],r["t"],c))
    calls.sort(key=lambda x:(x[0],x[1])); prev={}
    for job,t,c in calls:
        raw=c["function"]["arguments"]; res=R.get(c.get("id"),"")
        try: a=json.loads(raw)
        except Exception: a=None
        if "mandatory" in res:
            ks=tuple(sorted(k if k in("filepath","new_string","old_string") else "<other>" for k in (a or {}))); keysets[ks]+=1
            other=[k for k in (a or {}) if k not in("filepath","new_string","old_string")]
            bad.append(dict(raw=raw,a=a,other=other,job=job))
            retry["same as previous call" if prev.get(job)==raw else "new"]+=1
        elif a and "old_string" in a and '"error' not in res[:30]: good.append(a)
        prev[job]=raw
print("bad edit calls", len(bad), "good edit calls", len(good)); print("key sets of bad calls:", keysets.most_common(6)); print("retry:",retry)
def f(s):
    return dict(triple='"""' in s or "'''" in s, dq='"' in s, sq="'" in s, bs="\\" in s, nl3="\n\n\n" in s, nl2="\n\n" in s, brace="{" in s, lines=s.count("\n")+1, chars=len(s))
G=[f(a["old_string"]) for a in good]
B=[]
for b in bad:
    s=b["other"][0] if b["other"] else (b["a"] or {}).get("old_string","")
    B.append(f(s))
for k in ["triple","dq","sq","bs","nl3","nl2","brace"]:
    print(f"  old text has {k:6}: bad {st.mean(x[k] for x in B):4.0%}   good {st.mean(x[k] for x in G):4.0%}")
print(f"  lines: bad median {st.median(x['lines'] for x in B)}, good {st.median(x['lines'] for x in G)}; chars bad {st.median(x['chars'] for x in B)}, good {st.median(x['chars'] for x in G)}")
print("\nexamples of raw bad arguments (first 300 chars, 5):")
for b in bad[:400:80]: print("  ", repr(b["raw"][:300]))
