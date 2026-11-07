"""What survives compaction, by arm type, and what compaction costs. Prints no task text."""
import collections, glob, json, random, re, statistics as st
T = {json.loads(l)["instance_id"]: json.loads(l) for l in open("data/tasks.jsonl")}
TAB = {(r["folder"], r["iid"], str(r["attempt"])): r for r in map(json.loads, open("data/analysis/run_table.jsonl"))}
random.seed(2)
def lits(i):
    s = T[i]["problem_statement"]
    x = set(re.findall(r"`([^`\n]{3,60})`", s)) | set(re.findall(r"\"([^\"\n]{3,60})\"", s)) | set(re.findall(r"'([^'\n]{4,60})'", s))
    return x
TY = {"pub024": "A issue in task message only", "sq1c2": "A issue in task message only", "sq1c2a8": "A issue in task message only", "sq1c2a6": "A issue in task message only", "sq1c2t7": "A issue in task message only", "sq1c2f6": "A issue in task message only", "sk_a2": "A issue in task message only", "sk_a2_32": "A issue in task message only",
      "sq1c2a8ra": "B issue also in system prompt", "sq1c2f6ra": "B issue also in system prompt", "sq1c2a6i": "B issue also in system prompt", "sq1c2a6rn": "B issue also in system prompt",
      "sq1c2a6c": "C checklist, no issue in prompt", "sq1c2a8rc": "D checklist + issue in prompt", "sq1c2f6rc": "D checklist + issue in prompt", "sq1c2a6rc": "D checklist + issue in prompt"}
S = collections.defaultdict(lambda: dict(runs=0, comp=0, head=[], lit=[], head_end=[], lit_end=[], sumS=[], sumTok=[], tot=[]))
ROW = []
for f in sorted(glob.glob("data/results/*/requests/requests.jsonl")):
    d = f.split("/")[2]
    J = collections.defaultdict(list)
    for line in open(f):
        r = json.loads(line)
        if isinstance(r.get("reply"), dict) and r.get("job"): J[r["job"]].append(r)
    for job, q in J.items():
        iid, _, att = job.partition("#a"); arm = att.split(".")[0]
        if iid not in T or arm not in TY: continue
        rr = TAB.get((d, iid, att))
        if not rr: continue
        q.sort(key=lambda r: r["t"])
        s = S[TY[arm]]; s["runs"] += 1
        head = " ".join(T[iid]["problem_statement"].split()[:8]); L = lits(iid)
        summ = [r for r in q if not r["request"].get("tools")]
        s["sumS"].append(sum(r["seconds"] for r in summ)); s["sumTok"].append(sum(r["reply"]["usage"]["completion_tokens"] for r in summ)); s["tot"].append(rr["agent_s"])
        fix = [r for r in q if r["request"].get("tools") and "You submit this task" not in str(r["request"]["messages"][0].get("content"))]
        if not summ or not fix: continue
        s["comp"] += 1
        after = [r for r in fix if r["t"] > summ[0]["t"]]
        if not after: continue
        def text(r): return " ".join(" ".join(str(m.get("content")) + " " + json.dumps(m.get("tool_calls") or "") for m in r["request"]["messages"]).split())
        for lab, r in (("", after[0]), ("_end", after[-1])):
            tx = text(r)
            s["head" + lab].append(head in tx)
            if L: s["lit" + lab].append(sum(" ".join(x.split()) in tx for x in L) / len(L))
        ROW.append(dict(iid=iid, ty=TY[arm], arm=arm, res=rr["resolved"], before_edit=rr["first_edit"] is None or summ[0]["t"] - q[0]["t"] < rr["first_edit"], comps=len(summ), s=rr["agent_s"]))
print("== right after the first compaction / at the fixer's last request: is the issue still in context?")
for k in sorted(S):
    s = S[k]
    m = lambda v: f"{st.mean(v):.0%}" if v else "-"
    print(f"{k:34} runs {s['runs']:4} compacted {s['comp']:4} | issue opening {m(s['head'])} / {m(s['head_end'])} | issue's exact names and strings {m(s['lit'])} / {m(s['lit_end'])} | summarizer {st.mean(s['sumS']):.0f} s, {st.mean(s['sumTok']):.0f} tokens per run ({sum(s['sumS'])/sum(s['tot']):.0%} of run time)")
print("\n== same task + arm: first compaction before the first edit vs after")
def mh(rows, feat, by=("iid", "arm")):
    z = collections.defaultdict(lambda: [[0, 0], [0, 0]])
    for r in rows:
        c = z[tuple(r[b] for b in by)][int(bool(feat(r)))]; c[0] += r["res"]; c[1] += 1
    it = [(k, v) for k, v in z.items() if v[0][1] and v[1][1]]
    def est(w):
        n = sum(v[0][1] * v[1][1] / (v[0][1] + v[1][1]) for _, v in w)
        return sum((v[1][0] / v[1][1] - v[0][0] / v[0][1]) * v[0][1] * v[1][1] / (v[0][1] + v[1][1]) for _, v in w) / n if n else 0
    ts = sorted({k[0] for k, _ in it}); bt = collections.defaultdict(list)
    for k, v in it: bt[k[0]].append((k, v))
    xs = sorted(est([i for t in random.choices(ts, k=len(ts)) for i in bt[t]]) for _ in range(1500))
    return f"{est(it)*100:+.0f} pts ({xs[37]*100:+.0f} to {xs[1462]*100:+.0f}), {sum(v[1][1] for _, v in it)} vs {sum(v[0][1] for _, v in it)} runs, {len(ts)} tasks"
print("  ", mh(ROW, lambda r: r["before_edit"]))
print("\n== same task: issue-text and checklist effects, only runs that compacted before their first edit (where survival matters)")
sub = [r for r in ROW if r["before_edit"]]
def cmp(a, b, rows):
    A = collections.defaultdict(list); B = collections.defaultdict(list)
    for r in rows:
        if r["ty"].startswith(a): A[r["iid"]].append(r["res"])
        if r["ty"].startswith(b): B[r["iid"]].append(r["res"])
    c = sorted(set(A) & set(B))
    d = [st.mean(B[t]) - st.mean(A[t]) for t in c]
    xs = sorted(st.mean(random.choices(d, k=len(d))) for _ in range(2000)) if c else [0] * 2000
    return f"{a}->{b}: {st.mean(st.mean(A[t]) for t in c):.0%} -> {st.mean(st.mean(B[t]) for t in c):.0%} ({st.mean(d)*100:+.0f}, {xs[50]*100:+.0f} to {xs[1950]*100:+.0f}) over {len(c)} tasks" if c else f"{a}->{b}: none"
for a, b in (("A", "B"), ("A", "C"), ("A", "D"), ("B", "D"), ("C", "D")):
    print("  compacted early:", cmp(a, b, sub), "|| all compacted:", cmp(a, b, ROW))
print("\n== seconds and calls for one summarizer call")
sec = []; tok = []; inp = []
for f in sorted(glob.glob("data/results/2026-11-0*_skill_*/requests/requests.jsonl")):
    for line in open(f):
        r = json.loads(line)
        if isinstance(r.get("reply"), dict) and not r["request"].get("tools"): sec.append(r["seconds"]); tok.append(r["reply"]["usage"]["completion_tokens"]); inp.append(r["reply"]["usage"]["prompt_tokens"])
print(f"  {len(sec)} summarizer calls: median {st.median(sec):.0f} s, mean {st.mean(sec):.0f} s, p90 {sorted(sec)[int(.9*len(sec))]:.0f} s; output tokens median {st.median(tok):.0f}, input tokens median {st.median(inp):.0f}")
