import collections, glob, json, os, re, statistics as st
S=collections.defaultdict(list); W=collections.Counter(); kinds=collections.Counter(); pos=collections.Counter()
res={}
for D in sorted(glob.glob("data/results/2026-*")):
    if "e4b" in D or "probe" in D or "replay" in D: continue
    gp=D+"/results/gen_per_task.jsonl"; rq=D+"/requests/requests.jsonl"
    if not (os.path.exists(rq) and os.path.exists(gp)): continue
    G={r["instance_id"]+"#a"+r["attempt"]:r for r in map(json.loads,open(gp))}
    for l in open(rq):
        try: r=json.loads(l)
        except Exception: continue
        if not (isinstance(r.get("reply"),dict) and r.get("job") in G and G[r["job"]]["arm"]=="pub024"): continue
        m=r["reply"]["message"]; rc=m.get("reasoning_content") or ""; ct=m.get("content") or ""
        tc=m.get("tool_calls") or []; args=sum(len(c["function"]["arguments"]) for c in tc)
        out=(r["reply"].get("usage") or {}).get("completion_tokens") or 0
        b="long" if r["seconds"]>=30 else "short"
        S[b,"reason_chars"].append(len(rc)); S[b,"arg_chars"].append(args); S[b,"content_chars"].append(len(ct)); S[b,"out"].append(out)
        if b=="long":
            for w in ["Wait","Actually","Let me","Hmm","But ","re-read","double-check","However"]: W[w]+=rc.count(w)
            W["_n"]+=1
            nm=tc[0]["function"]["name"] if tc else "none"
            if nm=="run_command":
                cmd=json.loads(tc[0]["function"]["arguments"]).get("command","") if tc[0]["function"]["arguments"].startswith("{") else ""
                nm="run_command:"+("heredoc/py-script" if ("<<" in cmd or "cat >" in cmd) else "python -c" if "python" in cmd else "other")
            kinds[nm]+=1
            pos[r["reply"].get("finish_reason")]+=1
for b in ["short","long"]:
    print(b, {k[1]:round(st.mean(v)) for k,v in S.items() if k[0]==b}, "n",len(S[b,"out"]))
print("long request emits:",kinds.most_common())
print("finish:",pos)
n=W.pop("_n"); print("per long request, words in thinking:",{k:round(v/n,1) for k,v in W.items()})
