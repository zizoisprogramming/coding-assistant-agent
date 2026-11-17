# Run: python3 -I scripts/mine_bank/wrong_cases.py   (prints issue / real fix / hidden-test asserts / one wrong patch for the 10 test-set tasks with most wrong patches; local only)
import json, glob, os, re, collections, random
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)conftest\.py$")
C = {json.loads(l)["instance_id"]: json.loads(l) for l in open("data/swe_rebench/candidates.jsonl")}
T = {json.loads(l)["instance_id"] for l in open("data/tasks.jsonl")}
RT = set(C) - T
def srcdiff(p, n=14):
    out, keep = [], False
    for l in p.splitlines():
        if l.startswith("diff --git"):
            f = l.split(" b/")[-1]; keep = f.endswith(".py") and not TEST.search(f)
            if keep: out.append("  ## " + f)
        elif keep and (l.startswith("+") or l.startswith("-")) and not l.startswith(("+++", "---")):
            out.append("  " + l[:120])
    return out[:n] + (["  ..."] if len(out) > n else [])
def testdiff(p, n=8):
    out, keep = [], False
    for l in p.splitlines():
        if l.startswith("diff --git"):
            keep = True
        elif keep and l.startswith("+") and not l.startswith("+++") and re.search(r"assert|raises|==", l):
            out.append("  " + l[:130])
    return out[:n]
runs = collections.defaultdict(list)
for per in glob.glob("data/results/2026-11-1*/**/gen_per_task.jsonl", recursive=True):
    pdir = os.path.dirname(per)
    for l in open(per):
        g = json.loads(l)
        if g["instance_id"] in RT and g.get("arm") in ("pub024", "sa2", "sb1") and g.get("resolved") not in (True, "True"):
            pf = os.path.join(pdir, "gen/patches", f"{g['instance_id']}__a{g.get('attempt')}.diff")
            if os.path.exists(pf) and open(pf).read().strip():
                runs[g["instance_id"]].append(open(pf, errors="replace").read())
random.seed(1)
for iid in sorted(runs, key=lambda k: -len(runs[k]))[:10]:
    c = C[iid]
    print("=" * 100); print(iid, "| wrong patches in bank:", len(runs[iid]))
    print("ISSUE:", re.sub(r"\s+", " ", c["problem_statement"])[:420])
    print("REAL FIX:"); print("\n".join(srcdiff(c["patch"])))
    print("HIDDEN TEST asserts:"); print("\n".join(testdiff(c["test_patch"])))
    print("ONE WRONG PATCH:"); print("\n".join(srcdiff(random.choice(runs[iid]))))
