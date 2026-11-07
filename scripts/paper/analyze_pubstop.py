"""r51 pubstop vs pub024. Prints no task text."""
import collections, json, re, statistics as st, random
D = "data/results/2026-11-06_skill_pubstop"
random.seed(4)
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$|pytest\.ini$")
G = {}
for r in map(json.loads, open(D + "/results/gen_per_task.jsonl")): G[r["arm"], r["instance_id"]] = r
J = collections.defaultdict(list)
for l in open(D + "/requests/requests.jsonl"):
    r = json.loads(l)
    if isinstance(r.get("reply"), dict) and r.get("job"): J[r["job"]].append(r)
ROW = {}
for job, q in J.items():
    iid, _, att = job.partition("#a"); arm = att.split(".")[0]
    q.sort(key=lambda r: r["t"]); t0 = q[0]["t"]; R = {}
    for r in q:
        for m in r["request"]["messages"]:
            if m.get("role") == "tool": R.setdefault(m.get("tool_call_id"), str(m.get("content")))
    edits = []; ref = []; after = collections.Counter(); kinds = collections.Counter(); mal = 0; shell_bad = 0; sub = None; toks = 0; summ = 0; pending = False; first_ref = None
    for r in q:
        if not r["request"].get("tools"): summ += r["seconds"]; continue
        toks += r["reply"]["usage"]["completion_tokens"]
        for c in r["reply"]["message"].get("tool_calls") or []:
            n = c["function"]["name"]; kinds[n] += 1
            try: a = json.loads(c["function"]["arguments"])
            except Exception: a = {}
            res = R.get(c.get("id"), "")
            t = r["t"] + r["seconds"] - t0
            if pending: after[n] += 1; pending = False
            if n == "edit_file":
                p = str(a.get("filepath") or "")
                if "mandatory" in res: mal += 1
                elif "error_type" not in res and p and not TEST.search(p) and not p.startswith("/tmp"): edits.append(t)
            if n == "run_skill_script":
                if "mandatory" in res or "is required" in res or not a.get("skill_name") or not a.get("positional_args"): shell_bad += 1
                if "REFUSED" in res:
                    ref.append(t); pending = True
                    if first_ref is None: first_ref = t
            if n == "submit_patch" and sub is None: sub = t
    g = G[arm, iid]
    last = edits[-1] if edits else None
    ROW[arm, iid] = dict(iid=iid, res=g["resolved"], s=g["agent_s"], w=g["wall_s"], patch=g["patch_chars"], end=g["end"], edits=edits, ref=ref, after=after, kinds=kinds, mal=mal, shell_bad=shell_bad, sub=sub, last=last, first=edits[0] if edits else None, toks=toks, summ=summ, first_ref=first_ref, calls=g["tool_calls"], turns=len(q))
A = {i: v for (a, i), v in ROW.items() if a == "pubstop"}; B = {i: v for (a, i), v in ROW.items() if a == "pub024"}
com = sorted(set(A) & set(B)); print("paired tasks", len(com))
print(f"solved pubstop {sum(A[t]['res'] for t in com)} pub {sum(B[t]['res'] for t in com)} | only pubstop {sorted(t for t in com if A[t]['res'] and not B[t]['res'])} only pub {sorted(t for t in com if B[t]['res'] and not A[t]['res'])} | both {sorted(t for t in com if A[t]['res'] and B[t]['res'])}")
d = [A[t]["w"] - B[t]["w"] for t in com]; xs = sorted(st.mean(random.choices(d, k=len(d))) for _ in range(3000))
print(f"wall {st.mean(A[t]['w'] for t in com):.0f} vs {st.mean(B[t]['w'] for t in com):.0f}, diff {st.mean(d):+.0f} ({xs[75]:+.0f} to {xs[2925]:+.0f}); agent {st.mean(A[t]['s'] for t in com):.0f} vs {st.mean(B[t]['s'] for t in com):.0f}; overhead {st.mean(A[t]['w']-A[t]['s'] for t in com):.0f} vs {st.mean(B[t]['w']-B[t]['s'] for t in com):.0f}")
for lab, X in (("pubstop", A), ("pub024", B)):
    v = list(X.values()); e = [x for x in v if x["edits"]]
    print(f"{lab:8} no patch {sum(not x['patch'] for x in v)} edit landed {len(e)} | first edit median {st.median(x['first'] for x in e):.0f} s | seconds last edit to end: mean {st.mean(x['s']-x['last'] for x in e):.0f}, median {st.median(x['s']-x['last'] for x in e):.0f} | to submit {st.mean((x['sub']-x['last']) for x in e if x['sub'] and x['sub']>=x['last']):.0f} | submitted {sum(x['sub'] is not None for x in e)} | at the cap (>=478 s) {sum(x['s']>=478 for x in v)} of which edited {sum(x['s']>=478 and bool(x['edits']) for x in v)} | tokens {st.mean(x['toks'] for x in v):.0f} | summarizer s {st.mean(x['summ'] for x in v):.0f} | calls {st.mean(x['calls'] or 0 for x in v):.1f} | malformed edits {sum(x['mal'] for x in v)}")
print("kinds per run", {lab: {k: round(sum(x['kinds'][k] for x in X.values())/len(X),1) for k in ('run_command','run_skill_script','read_file','edit_file','write_file','submit_patch','get_status')} for lab, X in (("pubstop",A),("pub024",B))})
v = list(A.values())
rr = [x for x in v if x["ref"]]
af = collections.Counter()
for x in rr: af.update(x["after"])
print(f"refusals: runs with one {len(rr)} of {len(v)} (of {sum(bool(x['edits']) for x in v)} that edited), total {sum(len(x['ref']) for x in v)}; next call after a refusal {dict(af)}; end after first refusal, seconds: mean {st.mean(x['s']-x['first_ref'] for x in rr) if rr else 0:.0f}; solved among refused {sum(x['res'] for x in rr)}")
print(f"malformed shell calls {sum(x['shell_bad'] for x in v)} of {sum(x['kinds']['run_skill_script'] for x in v)}")
# edited runs where no shell call came after the 60 s mark: rule cannot fire
nof = [x for x in v if x["edits"] and not x["ref"]]
print("edited, no refusal:", len(nof), "| seconds last edit to end: median", st.median(x["s"] - x["last"] for x in nof) if nof else 0, "| ended within 60 s of last edit", sum(x["s"] - x["last"] <= 70 for x in nof), "| still running at the cap", sum(x["s"] >= 478 for x in nof))
late = [x for x in v if x["edits"] and x["s"] - x["last"] > 70]
print("edited and ran on more than 70 s after the last edit:", len(late), "| solved", sum(x["res"] for x in late), "| at cap", sum(x["s"] >= 478 for x in late), "| sample gaps", sorted(round(x["s"] - x["last"]) for x in late))
print("time budget by outcome, seconds per run across 38 tasks:")
for lab, X in (("pubstop", A), ("pub024", B)):
    v = list(X.values()); n = len(v)
    print(f"  {lab:8} solved {sum(x['w'] for x in v if x['res'])/n:.0f} | no edit {sum(x['w'] for x in v if not x['edits'] and not x['res'])/n:.0f} | wrong edit {sum(x['w'] for x in v if x['edits'] and not x['res'])/n:.0f}")
    pre = sum((x['first'] if x['edits'] else x['s']) for x in v) / n; print(f"           before first edit {pre:.0f} s per run")
pr = [json.loads(l) for l in ()]
