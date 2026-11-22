"""Every agent with a leaderboard score vs its local numbers, all task-matched against pub024 (the most-run agent), plus
sk_a2's call anatomy vs pub024 / sb1hl / sk_a2_32 / sa2. Reads data/analysis/ska2_deep_runs.jsonl (scripts/mine_bank/ska2_deep.py).
Run: python3 -I scripts/mine_bank/ska2_lb.py"""
import collections, json, statistics as st, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/mine_bank"))
sys.argv = [sys.argv[0]]
import ska2_deep as D  # noqa: E402
LB = {"sk_a2": [0.18], "mix": [0.17], "sk_a2_32": [0.17], "sb1hl": [0.15], "combo1": [0.15], "evidc": [0.15, 0.12], "le6_t6": [0.15],
      "sa2": [0.12], "nn32rcn2": [0.12], "sq1c2a6": [0.12, 0.10], "evidefs": [0.10], "pub024": [0.18], "evid3": [], "le5": [], "r4_budget": []}
print("\n== LB agents: local numbers task-matched vs pub024 (arm | pub024)")
for a, s in LB.items():
    if a not in D.A:
        print(f"  {a:10} LB {s}: no request-logged runs in the bank"); continue
    if a == "pub024":
        x = D.summ(D.A[a]); print(f"  {a:10} LB {s}: runs {x['n']} solve {x['solve']:.0%} nopatch {x['nopatch']:.0%} time {x['timeend']:.0%} agent {x['agent_s']:.0f}s"); continue
    m = D.matched(a, "pub024")
    if not m: print(f"  {a:10} LB {s}: no common tasks"); continue
    nt, na, no, o, w, l = m
    print(f"  {a:10} LB {str(s):12} tasks {nt:3} runs {na:4} | solve {o['solve'][0]:.0%} vs {o['solve'][1]:.0%} ({o['solve'][0]-o['solve'][1]:+.0%}) | nopatch {o['nopatch'][0]:.0%} vs {o['nopatch'][1]:.0%} | time {o['timeend'][0]:.0%} vs {o['timeend'][1]:.0%} | agent {o['agent_s'][0]:.0f} vs {o['agent_s'][1]:.0f}s")
print("\n== call anatomy per run (mean count of each call kind)")
K = ["install", "search", "outline", "show", "raw_read", "read_file", "src_edit", "scratch_write", "run_code", "other", "submit_patch", "get_status"]
print(f"{'arm':10}" + "".join(f"{k[:9]:>10}" for k in K))
for a in ("sk_a2", "sk_a2_32", "pub024", "sb1hl", "sa2", "combo1", "evidc"):
    rs = D.A[a]; c = collections.Counter(k for r in rs for k in r["calls"])
    print(f"{a:10}" + "".join(f"{c[k] / len(rs):10.1f}" for k in K))
print("\n== where the time goes (per run): replies, mean s/reply, capped replies (>= 88% of thinking budget), compactions, nudges")
for a in ("sk_a2", "sk_a2_32", "pub024", "sb1hl", "sa2"):
    rs = D.A[a]
    print(f"  {a:9} replies {st.mean(r['replies'] for r in rs):5.1f}  s/reply {st.mean(r['s_reply'] for r in rs):5.1f}  out tok {st.mean(r['out_mean'] for r in rs):4.0f}  max out {st.median(r['out_max'] for r in rs):5.0f} (median)  capped {st.mean(r['capped'] for r in rs):.2f}  comp {st.mean(r['comp'] for r in rs):.1f}  nudges {st.mean(r['nudges'] for r in rs):.1f}")
print("\n== outcome by whether the run edited source / when (sk_a2 vs pub024 vs sb1hl)")
for a in ("sk_a2", "pub024", "sb1hl"):
    rs = D.A[a]
    for lab, sel in (("never edited", [r for r in rs if not r["edited"]]), ("first edit <= call 12", [r for r in rs if r["edited"] and r["first_edit"] <= 12]),
                     ("first edit 13-20", [r for r in rs if r["edited"] and 13 <= r["first_edit"] <= 20]), ("first edit > 20", [r for r in rs if r["edited"] and r["first_edit"] > 20])):
        if sel: print(f"  {a:7} {lab:22} {len(sel):4} runs ({len(sel)/len(rs):4.0%}) solved {sum(r['solved'] for r in sel)/len(sel):4.0%}  no patch {sum(r['patch']==0 for r in sel)/len(sel):4.0%}")
print("\n== sk_a2 runs by folder (when / where it ran)")
for f, n in sorted(collections.Counter(r["folder"] for r in D.A["sk_a2"]).items()): print(f"  {f} {n}")
