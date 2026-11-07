"""Compactions per run from request logs, what survives them, and checklist use. Prints no task text."""
import collections, glob, json, random, re, statistics as st
T = {json.loads(l)["instance_id"]: json.loads(l) for l in open("data/tasks.jsonl")}
random.seed(11)
ROWS = []
for f in sorted(glob.glob("data/results/*/requests/requests.jsonl")):
    d = f.split("/")[2]; per = glob.glob(f"data/results/{d}/**/gen_per_task.jsonl", recursive=True)
    if not per or "e4b" in d: continue
    res = {(r["instance_id"], str(r.get("attempt"))): r for r in map(json.loads, open(per[0]))}
    J = collections.defaultdict(list)
    for line in open(f):
        r = json.loads(line)
        if isinstance(r.get("reply"), dict) and r.get("job"):
            m = r["request"]["messages"]
            iid = r["job"].split("#a")[0]
            words = T.get(iid, {}).get("problem_statement", "").split()[:8]
            txt_sys = str(m[0].get("content")); rest = " ".join(str(x.get("content")) for x in m[1:])
            head = " ".join(words)
            J[r["job"]].append(dict(tools=bool(r["request"].get("tools")), t=r["t"], s=r["seconds"], n=len(m), ptok=r["reply"]["usage"]["prompt_tokens"], issue_sys=bool(head) and head in " ".join(txt_sys.split()), issue_rest=bool(head) and head in " ".join(rest.split()),
                                    summary=("summary" in rest.lower()[:3000] or "summar" in rest.lower()[:3000]), checklist="issue.md" in rest, shown="[issue checklist]" in rest, sysch=len(txt_sys)))
    for job, q in J.items():
        iid, _, att = job.partition("#a"); g = res.get((iid, att))
        if not g or iid not in T: continue
        q.sort(key=lambda x: x["t"])
        comp = [i for i in range(len(q)) if not q[i]["tools"]]  # the summarizer: a model call with no tools
        main = [x for x in q if x["tools"]]
        if not main: continue
        t0 = q[0]["t"]
        lost = []
        ROWS.append(dict(iid=iid, arm=g.get("arm"), folder=d, res=bool(g["resolved"]), patch=g["patch_chars"], comps=len(comp), first=(q[comp[0]]["t"] - t0) if comp else None, ptok_max=max(x["ptok"] for x in main), issue_sys=main[-1]["issue_sys"], issue_first=main[0]["issue_sys"] or main[0]["issue_rest"], lost_any=(main[0]["issue_sys"] or main[0]["issue_rest"]) and not (main[-1]["issue_sys"] or main[-1]["issue_rest"]), lost_after=len(lost), wrote=any(x["checklist"] for x in q), shown=any(x["shown"] for x in q), s=g["agent_s"]))
def fam(a):
    if not a: return None
    if a == "pub024": return "pub"
    if a.startswith("sk_a2"): return "skA2"
    if a in ("sq1", "sq2"): return "seq"
    if a in ("sq1c", "sq1c2", "sq1c3", "sq1c4", "sq1c2a8", "sq1c2a8ra", "sq1c2t7"): return "clock7-8"
    if a == "sq1c2a8rc": return "a8rc"
    if a in ("sq1c2f6rc", "sq1c2a6rc", "sq1c2a6c"): return "6min checklist"
    if a in ("sq1c2t6", "sq1c2f6", "sq1c2f6ra", "sq1c2a6", "sq1c2a6rn", "sq1c2a6rnt", "sq1c2a6i"): return "6min no checklist"
    if a == "sq1c2a6info": return "info"
    return None
for r in ROWS: r["f"] = fam(r["arm"])
X = [r for r in ROWS if r["f"] and r["f"] != "info"]
print("runs", len(X))
print("\n== how often, how big")
for f in ("pub", "skA2", "seq", "clock7-8", "a8rc", "6min no checklist", "6min checklist"):
    x = [r for r in X if r["f"] == f]
    if not x: continue
    c = collections.Counter(min(r["comps"], 4) for r in x)
    fi = [r["first"] for r in x if r["first"] is not None]
    print(f"{f:18} runs {len(x):4} compactions mean {st.mean(r['comps'] for r in x):.1f} | runs with 0/1/2/3/4+: {[c[i] for i in range(5)]} | first at {st.median(fi) if fi else 0:.0f} s | issue in system prompt {sum(r['issue_sys'] for r in x)/len(x):.0%} | a later request has no issue text {sum(r['lost_any'] for r in x)/len(x):.0%}")
print("\n== solve rate by compactions, raw and same task+family")
for k in range(5):
    x = [r for r in X if min(r["comps"], 4) == k]
    if x: print(f"  {k}{'+' if k == 4 else ''} compactions: {sum(r['res'] for r in x)}/{len(x)} = {sum(r['res'] for r in x)/len(x):.0%} (no patch {sum(not r['patch'] for r in x)/len(x):.0%}, mean s {st.mean(r['s'] for r in x):.0f})")
def mh(rows, feat):
    s = collections.defaultdict(lambda: [[0, 0], [0, 0]])
    for r in rows:
        c = s[r["iid"], r["f"]][int(bool(feat(r)))]; c[0] += r["res"]; c[1] += 1
    it = [(k, v) for k, v in s.items() if v[0][1] and v[1][1]]
    def est(z):
        w = sum(v[0][1] * v[1][1] / (v[0][1] + v[1][1]) for _, v in z)
        return sum((v[1][0] / v[1][1] - v[0][0] / v[0][1]) * v[0][1] * v[1][1] / (v[0][1] + v[1][1]) for _, v in z) / w if w else 0
    ts = sorted({k[0] for k, _ in it}); bt = collections.defaultdict(list)
    for k, v in it: bt[k[0]].append((k, v))
    xs = sorted(est([i for t in random.choices(ts, k=len(ts)) for i in bt[t]]) for _ in range(1500))
    return f"{est(it)*100:+.0f} pts ({xs[37]*100:+.0f} to {xs[1462]*100:+.0f}), {sum(v[1][1] for _, v in it)} vs {sum(v[0][1] for _, v in it)} runs, {len(ts)} tasks"
print("  same task: 1+ compaction", mh(X, lambda r: r["comps"] >= 1)); print("  same task: 2+", mh(X, lambda r: r["comps"] >= 2)); print("  same task: 3+", mh(X, lambda r: r["comps"] >= 3))
print("  same task: issue text gone from a later request", mh(X, lambda r: r["lost_any"]))
print("\n== checklist arms, same run")
def cmp(a, b, folder=None):
    A = collections.defaultdict(list); B = collections.defaultdict(list)
    for r in ROWS:
        if folder and r["folder"] != folder: continue
        if r["arm"] == a: A[r["iid"]].append(r)
        if r["arm"] == b: B[r["iid"]].append(r)
    c = sorted(set(A) & set(B))
    if not c: return print(a, b, "no common")
    m = lambda D, f: st.mean(st.mean(f(x) for x in D[t]) for t in c)
    d = [st.mean(x["res"] for x in B[t]) - st.mean(x["res"] for x in A[t]) for t in c]
    xs = sorted(st.mean(random.choices(d, k=len(d))) for _ in range(3000))
    print(f"  {a:12}->{b:12} tasks {len(c):2} runs {sum(len(v) for v in A.values())}/{sum(len(v) for v in B.values())} : {m(A,lambda r:r['res']):.0%} -> {m(B,lambda r:r['res']):.0%} ({st.mean(d)*100:+.0f}, {xs[75]*100:+.0f} to {xs[2925]*100:+.0f}) | s {m(A,lambda r:r['s']):.0f}->{m(B,lambda r:r['s']):.0f} | no patch {m(A,lambda r:not r['patch']):.0%}->{m(B,lambda r:not r['patch']):.0%} | compactions {m(A,lambda r:r['comps']):.1f}->{m(B,lambda r:r['comps']):.1f} | checklist shown again {m(B,lambda r:r['shown']):.0%}")
print("folders:", {a: sorted({r["folder"] for r in ROWS if r["arm"] == a}) for a in ("sq1c2a8ra", "sq1c2a8rc", "sq1c2f6ra", "sq1c2f6rc", "sq1c2a6c", "sq1c2a6rc", "sq1c2a6", "sq1c2a8")})
cmp("sq1c2a8ra", "sq1c2a8rc"); cmp("sq1c2f6ra", "sq1c2f6rc"); cmp("sq1c2a6c", "sq1c2a6rc")
print("  (cross-run) ", end=""); cmp("sq1c2a8", "sq1c2a8rc")
print("\n== inside checklist arms: written? shown again?")
for a in ("sq1c2a8rc", "sq1c2f6rc", "sq1c2a6rc", "sq1c2a6c"):
    x = [r for r in ROWS if r["arm"] == a]
    w = [r for r in x if r["wrote"]]; s = [r for r in x if r["shown"]]
    print(f"  {a:12} runs {len(x)} solved {sum(r['res'] for r in x)} | issue.md in context {len(w)} | shown again {len(s)} solved {sum(r['res'] for r in s)} | not shown {len(x)-len(s)} solved {sum(r['res'] for r in x if not r['shown'])}")
