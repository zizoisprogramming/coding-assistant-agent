"""Same task: solved vs wrong patches - size relative to the real fix, new defs/classes, changed signatures, new files, scratch files in the patch."""
import json, glob, os, re, collections, statistics as st, sys
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)conftest\.py$")
G = {}
for f in ("data/swe_rebench/candidates.jsonl", "data/tasks.jsonl"):
    for l in open(f):
        j = json.loads(l); G[j["instance_id"]] = j["patch"]
ARMS = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else None
def feats(p):
    files, cur, add, rem = set(), None, 0, 0
    newdef = sig = scratch = newfile = 0
    lines = p.splitlines()
    for i, l in enumerate(lines):
        if l.startswith("diff --git"):
            cur = l.split(" b/")[-1]
            if not cur.endswith(".py") or TEST.search(cur): cur = None
            elif re.search(r"(^|/)(repro|reproduce|debug|scratch|test_issue|check)[\w-]*\.py$", l.split(" b/")[-1]): scratch += 1; cur = None
            else: files.add(cur)
        elif cur and l == "--- /dev/null": newfile += 1
        elif cur and l.startswith("+") and not l.startswith("+++"):
            add += 1
            if re.match(r"\+\s*(async )?(def|class) ", l):
                nm = re.findall(r"(?:def|class) (\w+)", l)[0]
                if not any(re.match(r"-\s*(async )?(def|class) " + nm + r"\b", m) for m in lines): newdef += 1
                else: sig += 1
        elif cur and l.startswith("-") and not l.startswith("---"):
            rem += 1
    return dict(changed=add + rem, files=len(files), newdef=newdef, sig=sig, scratch=scratch, newfile=newfile)
per = collections.defaultdict(lambda: {"S": [], "W": []})
for pt in glob.glob("data/results/2026-1*/**/gen_per_task.jsonl", recursive=True):
    pdir = os.path.dirname(pt)
    for l in open(pt):
        g = json.loads(l)
        if g["instance_id"] not in G or not g.get("arm") or (ARMS and g["arm"] not in ARMS): continue
        pf = os.path.join(pdir, "gen/patches", f"{g['instance_id']}__a{g.get('attempt')}.diff")
        if not os.path.exists(pf): continue
        p = open(pf, errors="replace").read()
        if not p.strip(): continue
        per[g["instance_id"]]["S" if g.get("resolved") in (True, "True") else "W"].append(feats(p))
mix = {k: v for k, v in per.items() if len(v["S"]) >= 2 and len(v["W"]) >= 2}
print(f"tasks with >= 2 solved and >= 2 wrong patches: {len(mix)} (solved {sum(len(v['S']) for v in mix.values())}, wrong {sum(len(v['W']) for v in mix.values())})")
for k in ("changed", "files", "newdef", "sig", "newfile", "scratch"):
    d = [(st.mean(x[k] for x in v["W"]), st.mean(x[k] for x in v["S"])) for v in mix.values()]
    print(f"  {k:8} wrong {st.mean(a for a, b in d):5.2f} vs solved {st.mean(b for a, b in d):5.2f} | tasks wrong higher {sum(a > b for a, b in d)}, lower {sum(a < b for a, b in d)}")
gs = {k: feats(G[k]) for k in mix}
over = [(sum(x["changed"] > 2 * gs[k]["changed"] for x in v["W"]) / len(v["W"]), sum(x["changed"] > 2 * gs[k]["changed"] for x in v["S"]) / len(v["S"])) for k, v in mix.items()]
print(f"  share of patches more than 2x the real fix's changed lines: wrong {st.mean(a for a, b in over):.2f} vs solved {st.mean(b for a, b in over):.2f}")
allw = [x for v in per.values() for x in v["W"]]
print(f"all wrong patches {len(allw)}: with a scratch file {sum(x['scratch'] > 0 for x in allw)}, with a new def/class {sum(x['newdef'] > 0 for x in allw)}, with a changed def line {sum(x['sig'] > 0 for x in allw)}")
