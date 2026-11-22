"""The STEPS successful runs follow (user 2026-11-23: 'what steps the model follows for this success'). Each run's calls are turned into
steps: L = look (find / outline / show / read / cat), X = run code (script, pytest, write a scratch file), E = source edit; repeats collapsed
(L L L -> L). Within-task (tasks with both outcomes): share of solved vs failed runs per step path, and step-level facts: distinct source
files read before the edit, code runs before / after the edit, re-edits. sk_a2 family and all agents. Run: python3 -I scripts/mine_bank/success_steps.py"""
import collections, json, math, statistics as st, sys, io, contextlib, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/mine_bank")); sys.argv = [sys.argv[0]]
with contextlib.redirect_stdout(io.StringIO()):
    import success_patterns as SP
M = {"find": "L", "outline": "L", "show": "L", "read": "L", "script": "X", "pytest": "X", "write": "X", "scratch": "X", "edit": "E"}


def path(seq):
    out = []
    for k in seq:
        s = M.get(k)
        if s and (not out or out[-1] != s): out.append(s)
    return "".join(out)


def shape(p):
    """coarse step shape: where code runs sit relative to the first edit, and whether looking resumes after it"""
    if "E" not in p: return "never edits"
    pre, post = p.split("E", 1)
    a = "look" + (" + run code" if "X" in pre else "")
    b = "edit"
    after = post.replace("E", "")
    if not after: c = "stop"
    elif set(after) == {"X"}: c = "run code to check"
    elif "L" in after and "X" in after: c = "look again + run code"
    else: c = "look again"
    re_edits = post.count("E")
    return f"{a} -> {b} -> {c}" + (" (re-edits)" if re_edits else "")


for fam, sel in (("sk_a2 family", lambda r: r["arm"].startswith("sk_a2")), ("ALL agents", lambda r: True)):
    rows = [r for r in SP.RUNS if sel(r)]
    by = collections.defaultdict(list)
    for r in rows: by[r["task"]].append(r)
    mixed = {t: v for t, v in by.items() if sum(x["solved"] for x in v) >= 2 and sum(not x["solved"] for x in v) >= 2}
    runs = [r for v in mixed.values() for r in v]
    print(f"\n==== {fam}: {len(mixed)} tasks with both outcomes, {len(runs)} runs")
    # per task share of each shape among solved vs failed, then averaged over tasks
    shapes = collections.Counter(shape(path(r["seq"])) for r in runs)
    print(f"  {'step shape':52}{'solved':>8}{'failed':>8}   tasks s>f / s<f")
    for sh, n in shapes.most_common(12):
        a, b, hi, lo = [], [], 0, 0
        for t, v in mixed.items():
            s = [x for x in v if x["solved"]]; f = [x for x in v if not x["solved"]]
            x1 = sum(shape(path(x["seq"])) == sh for x in s) / len(s); x2 = sum(shape(path(x["seq"])) == sh for x in f) / len(f)
            a.append(x1); b.append(x2); hi += x1 > x2; lo += x1 < x2
        print(f"  {sh:52}{st.mean(a):8.0%}{st.mean(b):8.0%}   {hi:3} / {lo:3}")
    # most common exact paths among solved
    P = collections.Counter(path(r["seq"]) for r in runs if r["solved"]); Q = collections.Counter(path(r["seq"]) for r in runs if not r["solved"])
    ns, nf = sum(P.values()), sum(Q.values())
    print("  most common exact step paths (L look, X run code, E edit):")
    for p, n in P.most_common(6): print(f"    {p:14} solved {n / ns:5.0%} | failed {Q[p] / nf:5.0%}")
    for p, n in Q.most_common(4):
        if p not in dict(P.most_common(6)): print(f"    {p:14} solved {P[p] / ns:5.0%} | failed {n / nf:5.0%}   (common in failed)")
