"""Every arm vs the same-run pub024 on the same task and pass, pooled over the whole bank (gen_per_task only, so folders
without requests count too). Usage: python3 -I scripts/mine_bank/arm_table.py [min_pairs]"""
import collections, glob, json, math, os, statistics as st, sys
MIN = int(sys.argv[1]) if len(sys.argv) > 1 else 8
P = collections.defaultdict(list)
for D in sorted(glob.glob("data/results/2026-*")):
    if "e4b" in D or "probe" in D or "replay" in D: continue
    f = D + "/results/gen_per_task.jsonl"
    if not os.path.exists(f): continue
    rows = [json.loads(l) for l in open(f)]
    by = collections.defaultdict(dict)
    for r in rows:
        pas = str(r.get("attempt", "")).rsplit(".", 1)[-1]
        by[(r["instance_id"], pas)][r["arm"]] = r
    for k, arms in by.items():
        if "pub024" not in arms: continue
        b = arms["pub024"]
        for a, r in arms.items():
            if a == "pub024": continue
            P[a].append((os.path.basename(D), k[0], bool(r["resolved"]), bool(b["resolved"]), (r.get("agent_s") or 0) - (b.get("agent_s") or 0),
                         not r.get("patch_chars"), not b.get("patch_chars")))
def sign_p(plus, minus):
    n = plus + minus; k = min(plus, minus)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n) if n else 1.0
print(f"{'arm':16}{'pairs':>6}{'arm':>5}{'pub':>5}{'+':>4}{'-':>4}{'p':>7}{'dTime s':>9}{'noP arm':>8}{'noP pub':>8}  folders")
for a, v in sorted(P.items(), key=lambda x: -(sum(y[2] for y in x[1]) - sum(y[3] for y in x[1]))):
    if len(v) < MIN: continue
    pl = sum(x[2] and not x[3] for x in v); mi = sum(x[3] and not x[2] for x in v)
    print(f"{a:16}{len(v):>6}{sum(x[2] for x in v):>5}{sum(x[3] for x in v):>5}{pl:>4}{mi:>4}{sign_p(pl, mi):>7.2f}{st.mean(x[4] for x in v):>+9.0f}{sum(x[5] for x in v):>8}{sum(x[6] for x in v):>8}  {len({x[0] for x in v})}")
