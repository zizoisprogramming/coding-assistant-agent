"""Do winnable-core runs that never change the source fail to see the bug? (user 2026-11-20 failure study). Read-only: runs of
data/analysis/failure_study.json that have a requests log. Per run: the model's own words saying the code already works / it
cannot reproduce ('cannot reproduce', 'works correctly', 'no bug', 'seems to work', 'already handled', 'is correct', 'expected
output' + 'matches', 'not able to reproduce', 'did not reproduce', 'behaves as expected'), and the first time it says it found
the cause ('the bug is', 'the problem is', 'the issue is', 'the cause', 'root cause', 'this is why', 'found it', 'that is the bug').
Run: python3 -I scripts/mine_bank/noedit_repro.py"""
import ast, collections, json, re, statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
F = json.load(open(ROOT / "data/analysis/failure_study.json"))
NOBUG = re.compile(r"can(no|')t reproduce|not able to reproduce|did not reproduce|does(n't| not) reproduce|could(n't| not) reproduce|works correctly|"
                   r"works as expected|behaves as expected|no bug|seems to work|already (handled|works|correct)|is correct\b|output is correct|"
                   r"(test|it) passed|bug is not (present|there)|not a bug", re.I)
CAUSE = re.compile(r"the (bug|problem|issue) is (that|in|caused)|root cause|the cause is|this is why|that's the bug|found the (bug|issue|problem)|"
                   r"this explains|the culprit", re.I)
logs = collections.defaultdict(list)
dirs = {r["d"] for r in F}
for d in dirs:
    p = ROOT / "data/results" / d / "requests/requests.jsonl"
    if not p.exists():
        continue
    for l in open(p, errors="replace"):
        try:
            r = json.loads(l)
        except Exception:
            continue
        logs[(d, r["job"])].append(r)
out = []
for r in F:
    rs = logs.get((r["d"], f"{r['iid']}#a{r['att']}"))
    if not rs:
        continue
    rs.sort(key=lambda x: float(x["t"]))
    t0 = float(rs[0]["t"])
    nobug = 0
    cause_t = None
    for x in rs:
        try:
            m = ast.literal_eval(str(x["reply"])).get("message") or {}
        except Exception:
            continue
        w = (m.get("reasoning_content") or "") + " " + (m.get("content") or "")
        nobug += len(NOBUG.findall(w))
        if cause_t is None and CAUSE.search(w):
            cause_t = float(x["t"]) - t0
    out.append(dict(cls=r["cls"], ok=r["ok"], nobug=nobug, cause_t=cause_t, iid=r["iid"]))
print(f"core runs with a requests log: {len(out)}")
for name, grp in (("solved", [o for o in out if o["ok"]]), ("failed, never changed the source", [o for o in out if not o["ok"] and o["cls"] == "no source edit"]),
                  ("failed, changed the source", [o for o in out if not o["ok"] and o["cls"] != "no source edit"])):
    if not grp:
        continue
    c = [o["cause_t"] for o in grp if o["cause_t"] is not None]
    print(f"  {name:34} runs {len(grp):3} | says 'works / cannot reproduce' at least once {sum(o['nobug'] > 0 for o in grp):3} ({100 * sum(o['nobug'] > 0 for o in grp) / len(grp):3.0f}%),"
          f" 3+ times {sum(o['nobug'] >= 3 for o in grp):3} | names a cause {len(c):3} ({100 * len(c) / len(grp):3.0f}%) at median {st.median(c) if c else 0:.0f} s")
