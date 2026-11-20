"""Where sb1h / sb1hl runs fail (user 2026-11-20: 'but can't we make it better? the sb1h lite'). Read-only on r123 + r124.
Per run: solved / changed an existing source file / ended by time / hit 'Tool call budget exhausted' / submitted; calls used;
a pytest run after the last source edit; the reproduce heredoc re-run after the last edit; the longest reply.
Run: python3 -I scripts/mine_bank/fail_modes.py"""
import ast, collections, glob, json, re, statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIRS = sorted(glob.glob(str(ROOT / "data/results/2026-11-20_skill_r12[34]_p*")))
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$")
G, src, R = {}, {}, collections.defaultdict(list)
for d in DIRS:
    k = Path(d).name
    for l in open(f"{d}/results/gen_per_task.jsonl"):
        g = json.loads(l)
        G[(k, g["instance_id"], g["arm"])] = g
    for f in glob.glob(f"{d}/results/gen/patches/*.diff"):
        iid, arm = Path(f).name[:-len(".1.diff")].rsplit("__a", 1)
        t = open(f, errors="replace").read()
        files = re.findall(r"^diff --git a/(\S+) b/", t, re.M)
        new = set(re.findall(r"^diff --git a/(\S+) b/\S+\nnew file", t, re.M))
        src[(k, iid, arm)] = any(x.endswith(".py") and not TEST.search(x) and x not in new for x in files)
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        r = json.loads(l)
        R[(k, r["job"].split("#")[0], r["job"].split("#a")[1].split(".")[0])].append(r)
rows = []
for key, g in G.items():
    rs = sorted(R.get(key, []), key=lambda r: float(r["t"]))
    budget = calls = 0
    last_edit = None
    after = []
    longest = max([float(r.get("seconds") or 0) for r in rs] or [0])
    seq = []
    for r in rs:
        m = r["request"]["messages"]
        if len(m) == 1:
            continue
        if m[-1].get("role") == "tool" and "Tool call budget exhausted" in str(m[-1].get("content")):
            budget = 1
        try:
            cs = (ast.literal_eval(str(r["reply"])).get("message") or {}).get("tool_calls") or []
        except Exception:
            cs = []
        for c in cs:
            calls += 1
            a = str(c["function"]["arguments"])
            seq.append(("edit" if "OLD_TEXT" in a else "pytest" if "pytest" in a else "repro" if re.search(r"python3? (- <<|reproduce|repro)", a) else "other"))
    li = max([i for i, x in enumerate(seq) if x == "edit"], default=None)
    tail = seq[li + 1:] if li is not None else []
    rows.append(dict(arm=key[2], iid=key[1], solved=g["resolved"] in (True, "True"), src=src.get(key, False), end=g["end"], budget=budget,
                     calls=calls, longest=longest, pytest_after="pytest" in tail, repro_after="repro" in tail, agent_s=g["agent_s"]))
for arm in ("sb1h", "sb1hl", None):
    X = [r for r in rows if arm is None or r["arm"] == arm]
    n = len(X)
    S = [r for r in X if r["solved"]]
    W = [r for r in X if not r["solved"] and r["src"]]
    N = [r for r in X if not r["solved"] and not r["src"]]
    print(f"#### {arm or 'both'}: runs {n} | solved {len(S)} | WRONG FIX (changed source, not solved) {len(W)} | NO SOURCE EDIT {len(N)}")
    print(f"   no-edit runs: ended by time {sum(r['end'] == 'time' for r in N)}, hit the call budget {sum(r['budget'] for r in N)}, longest reply median {st.median([r['longest'] for r in N] or [0]):.0f} s")
    for name, grp in (("solved", S), ("wrong fix", W)):
        if grp:
            print(f"   {name:9}: pytest after the last edit {sum(r['pytest_after'] for r in grp)}/{len(grp)}, reproduce after it {sum(r['repro_after'] for r in grp)}/{len(grp)},"
                  f" hit the call budget {sum(r['budget'] for r in grp)}/{len(grp)}, ended by time {sum(r['end'] == 'time' for r in grp)}/{len(grp)}, calls median {st.median(r['calls'] for r in grp):.0f}, agent s median {st.median(r['agent_s'] for r in grp):.0f}")
print("\nper task (both arms, r123 + r124): solved / wrong fix / no edit")
for t in sorted({r["iid"] for r in rows}):
    X = [r for r in rows if r["iid"] == t]
    print(f"  {t[:34]:34} {sum(r['solved'] for r in X):2} / {sum(not r['solved'] and r['src'] for r in X):2} / {sum(not r['solved'] and not r['src'] for r in X):2}   of {len(X)}")
