"""pub024-family runs: is the issue text still in the request when the first source edit is written / at the last edit? Within-task outcome split."""
import json, glob, collections, re
ARMS = {"pub024", "combo1", "combo2", "kf", "kf2", "kf2c"}
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$")
OUT = {}
for d in glob.glob("data/results/2026-11-*/"):
    try: G = {(r["arm"] + "." + str(r["attempt"]).split(".")[-1], r["instance_id"]): r for r in map(json.loads, open(d + "results/gen_per_task.jsonl"))}
    except FileNotFoundError: continue
    res = {}
    for r in map(json.loads, open(d + "results/gen_per_task.jsonl")): res[(r["instance_id"], r["attempt"])] = r
    J = collections.defaultdict(list)
    try: fh = open(d + "requests/requests.jsonl")
    except FileNotFoundError: continue
    for l in fh:
        try: r = json.loads(l)
        except Exception: continue
        if isinstance(r.get("reply"), dict) and r.get("job"): J[r["job"]].append(r)
    for job, q in J.items():
        iid, _, att = job.partition("#a"); arm = att.split(".")[0]
        if arm not in ARMS or (iid, att) not in res: continue
        q = [r for r in sorted(q, key=lambda r: r["t"]) if r["request"].get("tools")]
        if not q: continue
        first_user = next((m.get("content") for m in q[0]["request"]["messages"] if m.get("role") == "user"), None)
        if not isinstance(first_user, str) or len(first_user) < 50: continue
        probe = first_user[:200]
        comp = None; first_edit = None; n_comp = 0; prev_has = True
        for i, r in enumerate(q):
            has = any(isinstance(m.get("content"), str) and probe in m["content"] for m in r["request"]["messages"])
            if prev_has and not has: n_comp += 1; comp = comp if comp is not None else i
            prev_has = has
            for c in r["reply"]["message"].get("tool_calls") or []:
                if c["function"]["name"] in ("edit_file", "write_file") and first_edit is None:
                    try: a = json.loads(c["function"]["arguments"])
                    except Exception: a = {}
                    p = str(a.get("filepath") or a.get("path") or "")
                    if p and not TEST.search(p) and not p.startswith("/tmp"): first_edit = (i, has)
        R = res[(iid, att)]
        OUT[(d, job)] = dict(task=iid, arm=arm, solved=bool(R.get("resolved")), patched=(R.get("patch_chars") or 0) > 0,
                            issue_lost=comp is not None, lost_at=comp, n=len(q), edit=first_edit)
rows = list(OUT.values()); print(len(rows), "runs")
print("issue text lost at some point:", sum(r["issue_lost"] for r in rows), "| first edit written without the issue in context:", sum(1 for r in rows if r["edit"] and not r["edit"][1]), "of", sum(1 for r in rows if r["edit"]), "runs with an edit")
# within-task: among runs with an edit, solved rate with vs without issue at first edit
by = collections.defaultdict(lambda: {True: [0, 0], False: [0, 0]})
for r in rows:
    if r["edit"]: b = by[r["task"]][r["edit"][1]]; b[0] += r["solved"]; b[1] += 1
mixed = {t: v for t, v in by.items() if v[True][1] and v[False][1]}
a = [0, 0]; b = [0, 0]
for t, v in mixed.items(): a[0] += v[True][0]; a[1] += v[True][1]; b[0] += v[False][0]; b[1] += v[False][1]
print(f"tasks with both kinds: {len(mixed)} | first edit WITH issue in context solved {a[0]}/{a[1]} = {a[0]/max(1,a[1]):.0%} | WITHOUT {b[0]}/{b[1]} = {b[0]/max(1,b[1]):.0%}")
# task-weighted difference
diffs = [v[True][0]/v[True][1] - v[False][0]/v[False][1] for v in mixed.values()]
print(f"task-weighted mean diff {sum(diffs)/len(diffs):+.0%}; tasks + {sum(x>0 for x in diffs)} / - {sum(x<0 for x in diffs)} / 0 {sum(x==0 for x in diffs)}")
nopatch_lost = [r for r in rows if not r["patched"]]
print("no-patch runs:", len(nopatch_lost), "issue lost in", sum(r["issue_lost"] for r in nopatch_lost))

# control for timing: stratify by the call index of the first edit (same task, same call-index band)
print("\nstratified by first-edit call index (request number):")
for lo, hi in ((0, 10), (10, 14), (14, 18), (18, 22), (22, 40)):
    sub = [r for r in rows if r["edit"] and lo <= r["edit"][0] < hi]
    w = [r for r in sub if r["edit"][1]]; wo = [r for r in sub if not r["edit"][1]]
    print(f"  requests {lo}-{hi-1}: with issue {sum(r['solved'] for r in w)}/{len(w)} = {sum(r['solved'] for r in w)/max(1,len(w)):.0%} | without {sum(r['solved'] for r in wo)}/{len(wo)} = {sum(r['solved'] for r in wo)/max(1,len(wo)):.0%}")
# within task AND band
pairs = collections.defaultdict(lambda: {True: [0, 0], False: [0, 0]})
for r in rows:
    if r["edit"]:
        band = min(r["edit"][0] // 5, 5)
        b = pairs[(r["task"], band)][r["edit"][1]]; b[0] += r["solved"]; b[1] += 1
mx = [v for v in pairs.values() if v[True][1] and v[False][1]]
d = [v[True][0]/v[True][1] - v[False][0]/v[False][1] for v in mx]
print(f"same task + same 5-request band: {len(mx)} cells, mean diff {sum(d)/max(1,len(d)):+.0%}, + {sum(x>0 for x in d)} / - {sum(x<0 for x in d)} / 0 {sum(x==0 for x in d)}")
# what triggers the loss: tokens. Median request index at loss
L = [r["lost_at"] for r in rows if r["lost_at"] is not None]; L.sort()
print("issue lost at request index: median", L[len(L)//2], "p25", L[len(L)//4], "p75", L[3*len(L)//4])
