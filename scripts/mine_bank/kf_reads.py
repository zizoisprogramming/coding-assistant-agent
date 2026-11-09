"""r69 mechanism reads for kf vs pub024 (the bar in docs/PLAN.md "RUN BUILT r69").
Usage: python3 -I scripts/mine_bank/extract.py /tmp_dir/r69.jsonl data/results/FOLDER && python3 -I scripts/mine_bank/kf_reads.py /tmp_dir/r69.jsonl
Bank baselines for pub024 (442 runs) are printed alongside: compare kf with the same-run pub024 first."""
import collections, json, re, statistics as st, sys
BASE = {"edit calls new_string first": "99%", "edit calls garbled": "21.7%", "garbled calls resent identically": "73%",
        "runs with write_file /tmp error": "15%", "runs with python SyntaxError": "13%", "reads without end_line": "28%",
        "exact repeats per run": "3.2*0.77=2.5", "runs with budget refusal": "31%", "runs with a heredoc edit": "~4%"}
rows = [json.loads(l) for l in open(sys.argv[1])]
A = collections.defaultdict(list)
for r in rows: A[r["arm"]].append(r)
def reads(R):
    o = collections.OrderedDict(); n = len(R)
    E = [c for r in R for c in r["calls"] if c["n"] == "edit_file"]
    nf = [c for c in E if "new_string" in c["alen"] and ("old_string" not in c["alen"] or list(c["a"]).index("new_string") < list(c["a"]).index("old_string"))]
    bad = [c for c in E if "mandatory" in c["r"]]
    o["runs"] = n; o["solved"] = sum(r["resolved"] for r in R); o["no patch"] = sum(not r["patch"] for r in R)
    o["mean agent s"] = round(st.mean(r["agent_s"] or 0 for r in R)); o["runs at 478 s+"] = sum((r["agent_s"] or 0) >= 478 for r in R)
    o["edit calls"] = len(E)
    o["edit calls new_string first"] = f"{len(nf)/max(1,len(E)):.0%}"
    o["edit calls garbled"] = f"{len(bad)}/{len(E)} = {len(bad)/max(1,len(E)):.1%}"
    rs = 0; nb = 0
    for r in R:
        prev = None
        for c in r["calls"]:
            if c["n"] == "edit_file" and "mandatory" in c["r"]:
                nb += 1; rs += prev is not None and prev["n"] == "edit_file" and "mandatory" in prev["r"] and prev["a"] == c["a"]
            prev = c
    o["garbled calls resent identically"] = f"{rs}/{nb}"
    o["runs with write_file /tmp error"] = sum(any(c["n"] == "write_file" and "traversal" in c["r"] for c in r["calls"]) for r in R)
    o["runs with python SyntaxError"] = sum(any(c["n"] == "run_command" and "SyntaxError" in c["r"] for c in r["calls"]) for r in R)
    RD = [c for r in R for c in r["calls"] if c["n"] == "read_file"]
    o["reads without end_line"] = f"{sum(c['a'].get('end_line') is None for c in RD)}/{len(RD)}"
    rep = 0
    for r in R:
        seen = set()
        for c in r["calls"]:
            k = (c["n"], json.dumps(c["a"], sort_keys=True)); rep += k in seen; seen.add(k)
    o["exact repeats per run"] = round(rep / max(1, n), 1)
    o["runs with budget refusal"] = sum(any("exhaust" in c["r"].lower() for c in r["calls"]) for r in R)
    o["runs with a heredoc edit"] = sum(any(c["n"] == "run_command" and "<<" in str(c["a"].get("command", "")) and re.search(r"\.replace\(|open\([^)]*['\"]w", str(c["a"].get("command", ""))) for c in r["calls"]) for r in R)
    o["grep no-match then same pattern again"] = sum(1 for r in R for a, b in zip(r["calls"], r["calls"][1:]) if a["n"] == b["n"] == "run_command" and a["a"] == b["a"] and '"exit_code": 1' in a["r"])
    o["calls per run"] = round(st.mean(len(r["calls"]) for r in R), 1)
    return o
arms = sorted(A, key=lambda a: a != "pub024"); res = {a: reads(A[a]) for a in arms}
print(f"{'read':40}" + "".join(f"{a:>16}" for a in arms) + f"{'bank pub024':>16}")
for k in res[arms[0]]:
    print(f"{k:40}" + "".join(f"{str(res[a][k]):>16}" for a in arms) + f"{BASE.get(k, ''):>16}")
T = sorted({r["task"] for r in rows})
print("\nper task (Y solved, e wrong patch, . no patch; agent s)")
for t in T:
    print(f"  {t:16}" + "".join(f"{(lambda r: ('Y' if r['resolved'] else 'e' if r['patch'] else '.') + str(round(r['agent_s'] or 0)))(next(r for r in A[a] if r['task'] == t)):>10}" if any(r['task'] == t for r in A[a]) else f"{'-':>10}" for a in arms))
