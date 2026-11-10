"""First source-edit call index vs the arm's max_tool_calls (warning starts at max-10). Uses requests logs, Oct+Nov."""
import json, glob, collections, re, statistics as st
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$")
CAP = {}
for f in glob.glob("submissions/*/eval_config.yaml"):
    m = re.search(r"max_tool_calls:\s*(\d+)", open(f).read())
    if m: CAP[f.split("/")[1]] = int(m.group(1))
D = collections.defaultdict(list); W = collections.defaultdict(lambda: collections.Counter())
for f in glob.glob("data/results/2026-1[01]-*/requests/requests.jsonl"):
    J = collections.defaultdict(list)
    for l in open(f):
        try: r = json.loads(l)
        except Exception: continue
        if isinstance(r.get("reply"), dict) and r.get("job"): J[r["job"]].append(r)
    for job, q in J.items():
        arm = job.partition("#a")[2].split(".")[0]
        if arm not in CAP: continue
        q.sort(key=lambda r: r["t"]); k = 0; first = None; warn = None; R = {}
        for r in q:
            for m in r["request"]["messages"]:
                if m.get("role") == "tool": R.setdefault(m.get("tool_call_id"), str(m.get("content")))
        for r in q:
            if not r["request"].get("tools"): continue
            for c in r["reply"]["message"].get("tool_calls") or []:
                k += 1
                n = c["function"]["name"]
                try: a = json.loads(c["function"]["arguments"])
                except Exception: a = {}
                p = str(a.get("filepath") or "")
                if warn is None and "budget_warning" in R.get(c.get("id"), ""): warn = k
                if first is None and n in ("edit_file", "write_file") and p and not TEST.search(p) and not p.startswith("/tmp"): first = k
        D[(CAP[arm], arm)].append((first, warn, k))
by_cap = collections.defaultdict(list)
for (cap, arm), v in D.items(): by_cap[cap] += v
for cap in sorted(by_cap):
    v = by_cap[cap]; fe = [x[0] for x in v if x[0]]; arms = sorted({a for (c, a) in D if c == cap}, key=lambda a: -len(D[(cap, a)]))
    rel = collections.Counter((x[0] - (cap - 9)) for x in v if x[0])  # first edit relative to the first warned call (call cap-9)
    print(f"max_tool_calls {cap}: {len(v)} runs ({', '.join(arms[:5])}{'...' if len(arms) > 5 else ''}) | runs with an edit {len(fe)} | first-edit call median {st.median(fe) if fe else '-'} "
          f"(as share of budget {st.median(fe)/cap:.2f}) | edit within 0-2 calls after warning start {sum(rel[i] for i in (0,1,2))}/{len(fe)}")
print()
for arm in ("sk_a2", "sk_a2_32"):
    for cap in (28, 32):
        v = D.get((cap, arm))
        if not v: continue
        fe = [x[0] for x in v if x[0]]
        print(f"{arm} (cap {cap}): {len(v)} runs | edited {len(fe)} | first-edit call median {st.median(fe)} | quartiles {sorted(fe)[len(fe)//4]}-{sorted(fe)[3*len(fe)//4]} | total calls median {st.median([x[2] for x in v])}")
print()
for arm in ("pub024", "combo1"):
    v = D.get((28, arm)); fe = [x[0] for x in v if x[0]]; ne = sum(1 for x in v if not x[0])
    h = collections.Counter(fe)
    print(f"{arm}: {len(v)} runs, no edit {ne}; first-edit call histogram (call: runs):")
    print("   " + "  ".join(f"{i}:{h.get(i,0)}" for i in range(1, 29)))
    # hazard: P(first edit at call i | not edited before i)
    alive = len(v); hz = []
    for i in range(1, 29):
        e = h.get(i, 0); hz.append((i, e / alive if alive else 0, alive)); alive -= e
    print("   hazard %: " + "  ".join(f"{i}:{100*p:.0f}" for i, p, a in hz if i >= 10))
