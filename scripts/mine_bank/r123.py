"""r123: sb1h vs sb1hl (sb1h-lite) on 4 tasks, 2 passes (docs/PLAN.md RUN BUILT r123, bars set there).
Run: python3 -I scripts/mine_bank/r123.py
Per arm: solves, ends, agent s, compactions per run, prompt tokens per request, heredoc edit results (EDITED at a line start,
found 0, fence errors 'unexpected EOF while looking for matching', other), runs changing an existing source file, no-patch
runs, first-edit time, longest single reply; per task outcomes."""
import ast, collections, glob, json, re, statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIRS = sorted(glob.glob(str(ROOT / "data/results/2026-11-2*_skill_r123_p*")))
ARMS = ("sb1h", "sb1hl")
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$")
print("dirs:", [Path(d).name for d in DIRS])
G = []
for d in DIRS:
    for l in open(f"{d}/results/gen_per_task.jsonl"):
        g = json.loads(l)
        g["p"] = Path(d).name[-2:]
        G.append(g)
src = {}
for d in DIRS:
    for f in glob.glob(f"{d}/results/gen/patches/*.diff"):
        iid, arm = Path(f).name[:-len(".1.diff")].rsplit("__a", 1)
        t = open(f, errors="replace").read()
        files = re.findall(r"^diff --git a/(\S+) b/", t, re.M)
        new = set(re.findall(r"^diff --git a/(\S+) b/\S+\nnew file", t, re.M))
        src[(Path(d).name[-2:], iid, arm)] = any(x.endswith(".py") and not TEST.search(x) and x not in new for x in files)
R = collections.defaultdict(list)
for d in DIRS:
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        try:
            r = json.loads(l)
        except Exception:
            continue
        R[(Path(d).name[-2:], r["job"])].append(r)
M = collections.defaultdict(lambda: collections.defaultdict(list))
for (p, job), rs in R.items():
    arm = job.split("#a")[1].split(".")[0]
    if arm not in ARMS:
        continue
    rs.sort(key=lambda r: float(r["t"]))
    t0 = float(rs[0]["t"])
    comp = 0
    res = collections.Counter()
    first = None
    longest = 0
    pending = 0
    for r in rs:
        s = float(r.get("seconds") or 0)
        longest = max(longest, s)
        msgs = r["request"]["messages"]
        if len(msgs) == 1:
            comp += 1
            continue
        M[arm]["prompt_tok"].append((ast.literal_eval(str(r["reply"])).get("usage") or {}).get("prompt_tokens", 0) if str(r["reply"]).startswith("{") else 0)
        last = msgs[-1]
        t = str(last.get("content")).replace("\\n", "\n") if last.get("role") == "tool" else ""
        if pending:
            if re.search(r"(?m)^EDITED ", t):
                res["EDITED"] += 1
            elif "old text found 0 times" in t:
                res["found 0"] += 1
            elif re.search(r"old text found ([2-9]|\d\d+) times", t):
                res["found 2+"] += 1
            else:
                res["other"] += 1
            pending = 0
        if "unexpected EOF while looking for matching" in t:
            res["fence error"] += 1
        try:
            cs = (ast.literal_eval(str(r["reply"])).get("message") or {}).get("tool_calls") or []
        except Exception:
            cs = []
        if any("OLD_TEXT" in str(c["function"]["arguments"]) for c in cs):
            pending = 1
            res["edits"] += 1
            if first is None:
                first = float(r["t"]) + s - t0
    M[arm]["comp"].append(comp)
    M[arm]["res"].append(res)
    M[arm]["first"].append(first)
    M[arm]["longest"].append(longest)
print("\n#### per arm")
for a in ARMS:
    A = [g for g in G if g["arm"] == a]
    res = sum(M[a]["res"], collections.Counter())
    fs = [x for x in M[a]["first"] if x is not None]
    print(f"  {a:6} runs {len(A)} | solved {sum(g['resolved'] in (True, 'True') for g in A)} (by pass {[sum(g['resolved'] in (True, 'True') for g in A if g['p'] == p) for p in ('p1', 'p2')]})"
          f" | ends {dict(collections.Counter(g['end'] for g in A))} | agent s mean {st.mean(g['agent_s'] for g in A):.0f}"
          f" | compactions {sum(M[a]['comp'])} ({sum(M[a]['comp']) / max(len(A), 1):.2f}/run) | prompt tokens/request mean {st.mean(M[a]['prompt_tok'] or [0]):.0f}")
    print(f"         heredoc edits {res['edits']}: EDITED {res['EDITED']} ({100 * res['EDITED'] / max(res['edits'], 1):.0f}%), found 0 {res['found 0']}, found 2+ {res['found 2+']}, other {res['other']}"
          f" | fence errors {res['fence error']} | changed an existing source file {sum(src.get((g['p'], g['instance_id'], a), False) for g in A)}"
          f" | no patch {sum(not g['patch_chars'] for g in A)} | first edit: runs {len(fs)}, median {st.median(fs) if fs else 0:.0f} s"
          f" | longest reply median {st.median(M[a]['longest'] or [0]):.0f} s")
print("\n#### per task (S solved, E changed source no solve, - neither; p1 p2)")
for t in sorted({g["instance_id"] for g in G}):
    cells = []
    for a in ARMS:
        c = ""
        for p in ("p1", "p2"):
            xs = [g for g in G if g["instance_id"] == t and g["arm"] == a and g["p"] == p]
            c += ("S" if xs[0]["resolved"] in (True, "True") else ("E" if src.get((p, t, a)) else "-")) if xs else "."
        cells.append(f"{a} {c}")
    print(f"  {t[:30]:30} " + " | ".join(cells))
