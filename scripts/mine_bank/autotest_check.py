"""Offline check for idea A: the edit step runs the matching existing test file right after an applied edit (user 2026-11-20:
'yes do the offline check for idea A'). Read-only on r118-r124 requests of the sb1h family (sb1h, sb1hpp, sbA, sbB, sbF, sbF2,
sbG, sb1hl); no repository code runs here.
1. Would it catch wrong fixes? The model's own pytest runs AFTER a source edit: the reported result ('N failed' / 'error' vs
   all passed) against the run's outcome. A run whose existing tests fail after its edit can be corrected; a wrong fix whose
   existing tests all pass cannot be caught this way (the hidden test is new).
2. Which test file: the name rule test_<module>.py / <module>_test.py for the edited source file vs the file holding the hidden
   test (test_patch), on these tasks; and the files the model itself ran.
3. Cost: pytest's own 'in X.XXs' durations in those outputs.
Run: python3 -I scripts/mine_bank/autotest_check.py"""
import ast, collections, glob, json, re, statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARMS = {"sb1h", "sb1hpp", "sbA", "sbB", "sbF", "sbF2", "sbG", "sb1hl"}
DIRS = sorted(glob.glob(str(ROOT / "data/results/2026-11-19_skill_r1[12][890]_p*")) + glob.glob(str(ROOT / "data/results/2026-11-20_skill_r12[1-4]_p*")))
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$")
T = {}
for f in ("data/swe_rebench/candidates.jsonl", "data/tasks.jsonl"):
    for l in open(ROOT / f):
        j = json.loads(l)
        T[j["instance_id"]] = j
solved = {}
for d in DIRS:
    for l in open(f"{d}/results/gen_per_task.jsonl"):
        g = json.loads(l)
        solved[(d, g["instance_id"], g["arm"])] = g["resolved"] in (True, "True")
runs = collections.defaultdict(list)
for d in DIRS:
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        try:
            r = json.loads(l)
        except Exception:
            continue
        arm = r["job"].split("#a")[1].split(".")[0]
        if arm in ARMS and len(r["request"]["messages"]) > 1:
            runs[(d, r["job"].split("#")[0], arm)].append(r)


def calls(r):
    try:
        cs = (ast.literal_eval(str(r["reply"])).get("message") or {}).get("tool_calls") or []
    except Exception:
        return []
    out = []
    for c in cs:
        try:
            out.append((c["function"]["name"], json.loads(c["function"]["arguments"])))
        except Exception:
            pass
    return out


rows, durs, picked = [], [], collections.Counter()
for key, rs in runs.items():
    d, iid, arm = key
    rs.sort(key=lambda r: float(r["t"]))
    edited = False
    after = []  # pytest results after the first applied source edit: 'fail' / 'pass' / 'error' / 'none'
    for i, r in enumerate(rs):
        res = rs[i + 1]["request"]["messages"][-1] if i + 1 < len(rs) else {}
        t = str(res.get("content")).replace("\\n", "\n") if res.get("role") == "tool" else ""
        for n, a in calls(r):
            cmd = a.get("command", "") if n == "run_command" else ""
            if "OLD_TEXT" in cmd and re.search(r"(?m)^EDITED ", t):
                edited = True
            if "pytest" in cmd and t:
                m = re.search(r"in (\d+\.\d+)s", t)
                if m:
                    durs.append(float(m.group(1)))
                for f in re.findall(r"(\S+\.py)", cmd):
                    picked[(iid, f)] += 1
                if edited:
                    if re.search(r"\d+ (failed|error)", t) or "ERROR" in t[:3000] or "Interrupted" in t:
                        after.append("fail")
                    elif re.search(r"\d+ passed", t):
                        after.append("pass")
                    else:
                        after.append("other")
    rows.append(dict(iid=iid, arm=arm, solved=solved.get(key, False), edited=edited, after=after))

print("#### 1. existing tests after the edit (the model's own pytest runs) vs outcome")
E = [r for r in rows if r["edited"]]
for name, grp in (("solved", [r for r in E if r["solved"]]), ("not solved", [r for r in E if not r["solved"]])):
    ran = [r for r in grp if r["after"]]
    first_fail = sum(r["after"][0] == "fail" for r in ran)
    last_fail = sum(r["after"][-1] == "fail" for r in ran)
    print(f"  {name:10} edited runs {len(grp):3} | ran pytest after an edit {len(ran):3} | first such run shows failures {first_fail:3}"
          f" | last such run still shows failures {last_fail:3} | all passed at the last run {sum(r['after'][-1] == 'pass' for r in ran):3}")
ns = [r for r in E if not r["solved"] and r["after"]]
print(f"  -> of the not-solved edited runs that ran tests, existing tests were green at the last run in {sum(r['after'][-1] == 'pass' for r in ns)}/{len(ns)}"
      " (a wrong fix the existing file cannot catch) and red in " f"{sum(r['after'][-1] == 'fail' for r in ns)}/{len(ns)}")
unt = [r for r in E if not r["solved"] and not r["after"]]
print(f"  not-solved edited runs that never ran pytest after the edit: {len(unt)} (what the step would add)")

print("\n#### 2. which test file")
tasks = sorted({r["iid"] for r in rows})
rule_hit = 0
for t in tasks:
    j = T.get(t, {})
    srcs = [x for x in re.findall(r"^diff --git a/(\S+) b/", j.get("patch", ""), re.M) if x.endswith(".py") and not TEST.search(x)]
    tests = [x for x in re.findall(r"^diff --git a/(\S+) b/", j.get("test_patch", ""), re.M) if x.endswith(".py") and TEST.search(x)]
    mods = {s.rsplit("/", 1)[-1][:-3] for s in srcs}
    names = {x.rsplit("/", 1)[-1] for x in tests}
    hit = any(f"test_{m}.py" in names or f"{m}_test.py" in names for m in mods)
    rule_hit += hit
    mine = sorted(((f, c) for (i, f), c in picked.items() if i == t), key=lambda x: -x[1])[:3]
    print(f"  {t[:34]:34} source {sorted(srcs)} | hidden test in {sorted(tests)} | name rule finds it: {'Y' if hit else '-'} | model ran: {mine}")
print(f"  name rule finds the hidden test's file on {rule_hit}/{len(tasks)} tasks")

print("\n#### 3. cost: pytest durations reported in the outputs")
if durs:
    durs.sort()
    print(f"  {len(durs)} runs: median {st.median(durs):.2f} s, p90 {durs[int(len(durs) * .9)]:.1f} s, max {durs[-1]:.1f} s, > 30 s: {sum(x > 30 for x in durs)}")
