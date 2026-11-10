"""Per arm: thinking budget and max output from its submission files, and what replies actually look like in the bank.
Usage: python3 -I scripts/mine_bank/thinking.py OUT_runs.jsonl"""
import collections, glob, json, os, re, statistics as st, sys
cfg = {}
for d in glob.glob("submissions/*"):
    a = os.path.basename(d); tb = mo = None
    for f in glob.glob(d + "/configs/*.yaml") + glob.glob(d + "/*.yaml"):
        t = open(f).read()
        if "fixer" in f or f.endswith("configs/sampling.yaml") or (tb is None and "thinking_budget" in t):
            m = re.search(r"thinking_budget:\s*(\d+)", t); n = re.search(r"max_output_tokens:\s*(\d+)", t)
            if m and (f.endswith("configs/sampling.yaml") or tb is None): tb = int(m.group(1)); mo = int(n.group(1)) if n else None
    cfg[a] = (tb, mo)
rows = [json.loads(l) for l in open(sys.argv[1])]
A = collections.defaultdict(list)
for r in rows:
    if "e4b" in r["folder"] or "replay" in r["folder"] or "probe" in r["folder"]: continue
    A[r["arm"]].append(r)
print(f"{'arm':14}{'think':>6}{'maxout':>7}{'runs':>5}{'p99 out':>8}{'max out':>8}{'>=30s/run':>10}{'model s':>8}{'agent s':>8}{'solve':>6}")
for a, R in sorted(A.items(), key=lambda x: (cfg.get(x[0], (0, 0))[0] or 0, x[0])):
    if len(R) < 12: continue
    outs = sorted(q["out"] or 0 for r in R for q in r["reqs"] if q["tools"])
    if not outs: continue
    print(f"{a:14}{str(cfg.get(a, ('?',))[0]):>6}{str(cfg.get(a, (0, '?'))[1]):>7}{len(R):>5}{outs[int(.99 * len(outs))]:>8}{outs[-1]:>8}"
          f"{st.mean(sum(q['s'] >= 30 for q in r['reqs'] if q['tools']) for r in R):>10.2f}{st.mean(sum(q['s'] for q in r['reqs']) for r in R):>8.0f}"
          f"{st.mean(r['agent_s'] or 0 for r in R):>8.0f}{st.mean(r['resolved'] for r in R):>6.0%}")
