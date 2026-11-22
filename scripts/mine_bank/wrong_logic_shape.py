"""Shape of wrong-logic patches vs solved ones (user 2026-11-23, follow-up to wrong_place_why.py). For every run with a saved patch on a task
solved by >= 2 agents: real-fix hunks covered by the agent's patch (a hunk = a run of changed lines within 5 lines in one file; covered = an
agent change within 5 lines), files of the real fix covered, patch size / real-fix size, by bucket; per task, the solved vs wrong-logic
coverage. Run: python3 -I scripts/mine_bank/wrong_logic_shape.py"""
import collections, glob, json, statistics as st, sys, io, contextlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/mine_bank")); sys.argv = [sys.argv[0]]
with contextlib.redirect_stdout(io.StringIO()):
    from fail_place import changed  # noqa: E402
T = {}
for l in open(ROOT / "data/tasks.jsonl"):
    t = json.loads(l); T[t["instance_id"]] = (changed(t["patch"]), len(t["patch"]))


def hunks(ch):
    out = []
    for f, ls in ch.items():
        cur = []
        for x in sorted(ls):
            if cur and x - cur[-1] > 5: out.append((f, cur)); cur = []
            cur.append(x)
        if cur: out.append((f, cur))
    return out


rows = []
for d in sorted(glob.glob(str(ROOT / "data/results/*/"))):
    pdir = Path(d) / "results/gen/patches"; gp = Path(d) / "results/gen_per_task.jsonl"
    if not pdir.exists() or not gp.exists(): continue
    for l in open(gp, errors="replace"):
        try: g = json.loads(l)
        except Exception: continue
        task = g.get("instance_id")
        if task not in T or not T[task][0]: continue
        pf = list(pdir.glob(f"{task}__a{g.get('attempt')}.diff")) or list(pdir.glob(f"{task}__a{g.get('arm')}.*.diff"))
        if not pf: continue
        txt = pf[0].read_text(errors="replace"); ch = changed(txt)
        if not ch: continue
        gold, glen = T[task]
        solved = g.get("resolved") in (True, "True")
        gh = hunks(gold)
        cov = sum(any(f2 == f and any(abs(x - y) <= 5 for x in ls2 for y in ls) for f2, ls2 in [(f2, ls2) for f2, ls2 in ch.items()]) for f, ls in gh)
        right_spot = any(abs(x - y) <= 5 for f in set(ch) & set(gold) for x in ch[f] for y in gold[f])
        if not solved and not right_spot: continue
        rows.append(dict(task=task, arm=g.get("arm"), solved=solved, gh=len(gh), cov=cov, gfiles=len(gold), cfiles=len(set(ch) & set(gold)),
                         size=len(txt) / glen))
solvers = collections.defaultdict(set)
for r in rows:
    if r["solved"]: solvers[r["task"]].add(r["arm"])
rows = [r for r in rows if len(solvers[r["task"]]) >= 2]
for lab, sel in (("solved", [r for r in rows if r["solved"]]), ("right spot, wrong logic", [r for r in rows if not r["solved"]])):
    print(f"== {lab}: {len(sel)} runs on {len({r['task'] for r in sel})} tasks")
    print(f"   all real-fix hunks covered {sum(r['cov'] == r['gh'] for r in sel) / len(sel):.0%} | mean share of hunks covered {st.mean(r['cov'] / r['gh'] for r in sel):.0%}"
          f" | all real-fix files touched {sum(r['cfiles'] == r['gfiles'] for r in sel) / len(sel):.0%} | patch size / real fix median {st.median(r['size'] for r in sel):.2f}")
print("\n== per task (tasks with >= 3 solved and >= 3 wrong-logic runs): hunks covered, solved vs wrong logic; real-fix hunks / files")
by = collections.defaultdict(lambda: ([], []))
for r in rows: by[r["task"]][0 if r["solved"] else 1].append(r)
for t, (s, w) in sorted(by.items()):
    if len(s) >= 3 and len(w) >= 3:
        print(f"  {t:16} real fix {s[0]['gh']} hunks / {s[0]['gfiles']} files | solved {len(s):3} cover all {sum(r['cov'] == r['gh'] for r in s) / len(s):4.0%} size {st.median(r['size'] for r in s):.2f}"
              f" | wrong {len(w):3} cover all {sum(r['cov'] == r['gh'] for r in w) / len(w):4.0%} size {st.median(r['size'] for r in w):.2f}")
