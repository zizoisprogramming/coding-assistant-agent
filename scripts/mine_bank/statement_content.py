"""What the task statements contain vs what the hidden test grades (user 2026-11-20: 'tell me what bug fixes or reports contain
exactly? do they contain the grading criteria or do they need the behaviour of the problem'). CPU, read-only on data/tasks.jsonl
(129 public tasks) + data/analysis/task_anatomy.json (solve rates). Per task:
  ENTRY  - the test's entry points (names the added test lines call: obj.method( / Name( / func(, minus pytest / builtins /
           test helpers) named anywhere in the statement;
  INPUT  - the statement shows an example call / input (a code block, or an inline `name(...)`);
  BEHAV  - the statement says the wanted behaviour in words (should / expected / instead / now returns / raise / must / ...);
  VALUES - every exact value the test asserts (string / number literals on assert / match / == lines) appears in the statement.
Run: python3 -I scripts/mine_bank/statement_content.py"""
import collections, json, re, statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
T = [json.loads(l) for l in open(ROOT / "data/tasks.jsonl")]
A = {r["iid"]: r for r in json.load(open(ROOT / "data/analysis/task_anatomy.json"))}
X = json.load(open(ROOT / "data/analysis/task_exact_text.json"))
SKIP = set("""assert print len str int float dict list set tuple isinstance range repr type open sorted any all getattr setattr hasattr
super pytest raises mark parametrize fixture approx warns match TestClient get post put delete patch app client response json
Depends FastAPI APIRouter Console Text Segment Style render Path Query Header Cookie Body Form File""".split())
rows = []
for t in T:
    ps = t["problem_statement"]
    tl = [l[1:] for l in t["test_patch"].splitlines() if l.startswith("+") and not l.startswith("+++")]
    body = "\n".join(tl)
    calls = set(re.findall(r"\.(\w{3,})\(", body)) | set(re.findall(r"(?<![\w.])([A-Za-z_]\w{2,})\(", body))
    calls = {c for c in calls if c not in SKIP and not c.startswith(("test", "_")) and not c.isupper()}
    entry = {c for c in calls if re.search(r"\b" + re.escape(c) + r"\b", ps)}
    inp = bool("```" in ps or re.search(r"`[^`\n]*\w\([^`\n]*\)`", ps))
    behav = bool(re.search(r"\bshould\b|\bexpected\b|\binstead\b|\bmust\b|\bnow (returns?|raises?|shows?|uses?|accepts?|supports?|works?)\b|\braises?\b|\breturns?\b|\bwrong\b|\bincorrect\b|\bbroken\b|\bfails?\b|\bcrash", ps, re.I))
    vals = set()
    for l in tl:
        if re.search(r"\bassert\b|match=|==", l):
            vals |= set(re.findall(r"""['"]([^'"\n]{3,120})['"]""", l)) | set(re.findall(r"(?<![\w.])(\d{2,})(?![\w.])", l))
    vin = {v for v in vals if v in ps}
    a = A[t["instance_id"]]
    rows.append(dict(iid=t["instance_id"], entry=bool(entry), n_calls=len(calls), inp=inp, behav=behav, vals=len(vals), vals_all=bool(vals) and vin == vals,
                     vals_some=bool(vin), rate=a["rate"], n=a["n"], kind=a["kind"], exact=X[t["instance_id"]],
                     core=a["src_files"] <= 1 and X[t["instance_id"]] != "exact text only the test knows"))
n = len(rows)
print(f"tasks {n}")
for k, lab in (("entry", "ENTRY  names what the test calls"), ("inp", "INPUT  shows an example call / input"), ("behav", "BEHAV  says the wanted behaviour in words"),
               ("vals_some", "VALUES some asserted value in the text"), ("vals_all", "VALUES every asserted value in the text")):
    yes = [r for r in rows if r[k]]
    no = [r for r in rows if not r[k]]
    ry = [r["rate"] for r in yes if r["n"] >= 4]
    rn = [r["rate"] for r in no if r["n"] >= 4]
    print(f"  {lab:46} {len(yes):3}/{n} ({100 * len(yes) / n:3.0f}%) | solve rate with {100 * st.mean(ry) if ry else 0:3.0f}% ({len(ry)}) vs without {100 * st.mean(rn) if rn else 0:3.0f}% ({len(rn)})")
print("\ncombinations (what the text gives), with solve rates:")
combo = collections.defaultdict(list)
for r in rows:
    key = ("names entry" if r["entry"] else "no entry") + " + " + ("example" if r["inp"] else "no example") + " + " + ("behaviour" if r["behav"] else "no behaviour")
    combo[key].append(r)
for k, xs in sorted(combo.items(), key=lambda x: -len(x[1])):
    rs = [x["rate"] for x in xs if x["n"] >= 4]
    print(f"  {k:45} tasks {len(xs):3} | solve rate {100 * st.mean(rs) if rs else 0:3.0f}% ({len(rs)})")
C = [r for r in rows if r["core"]]
print(f"\nwinnable core (1 source file, no hidden exact text): {len(C)} tasks")
for k in ("entry", "inp", "behav", "vals_all"):
    ry = [r["rate"] for r in C if r[k] and r["n"] >= 4]
    rn = [r["rate"] for r in C if not r[k] and r["n"] >= 4]
    print(f"  {k:8} yes {sum(r[k] for r in C):3} solve {100 * st.mean(ry) if ry else 0:3.0f}% ({len(ry)}) | no {sum(not r[k] for r in C):3} solve {100 * st.mean(rn) if rn else 0:3.0f}% ({len(rn)})")
json.dump(rows, open(ROOT / "data/analysis/statement_content.json", "w"))
