"""Do the per-reply label rules separate success from failure? (user 2026-11-25: 'how are you going to know what steps are
good and what is bad ... since we are tuning it to follow the correct paths'). Every rule of pref_episodes.py is applied to
EVERY sk_a2 run (solved and failed alike), then, on the SAME task, the share of solved vs failed runs showing it:
  mistake (failed call), retry streak, repeat, reading on (>= 3 replies), saw the fix, right place.
A 'bad' rule is backed when failed runs show it more than solved runs of the same task; a 'good' rule when solved runs do.
Run: data/venv_train/bin/python -I scripts/mine_bank/label_rules_check.py"""
import collections, glob, json, sys
from math import comb
sys.path.insert(0, "scripts/train")
import pref_episodes as P
from selfdistill_episodes import tool_results, failed
tasks = {json.loads(l)["instance_id"]: json.loads(l) for l in open("data/tasks.jsonl")}
runs = []
for d in sorted(glob.glob("data/results/*skill*")):
    try:
        rows, recs, patches = P.load_dir(d, {"sk_a2"})
    except OSError:
        continue
    for key, g in rows.items():
        rs = recs.get(key)
        if not rs or key[0] not in tasks or g.get("end") not in P.AGENT_ENDS:
            continue
        runs.append(dict(task=key[0], ok=g["resolved"] in (True, "True"), recs=rs))
by = collections.defaultdict(list)
for r in runs:
    by[r["task"]].append(r)
for t, v in by.items():
    idx = sorted(x for x in (P.reply_index_of_first_edit(r["recs"]) for r in v if r["ok"]) if x is not None)
    sib = idx[len(idx) // 2] if idx else None
    for r in v:
        kept = [dict(x) for x in r["recs"]]
        P.flag_decisions(kept)
        P.label_milestones(kept, tasks[t]["patch"])
        why = P.label_bad_replies(kept, sib)
        res = tool_results(kept)
        mistakes = 0
        for x in kept:
            for c in ((x.get("reply") or {}).get("message") or {}).get("tool_calls") or []:
                fn = c.get("function") or {}
                try:
                    a = json.loads(fn.get("arguments") or "{}") if isinstance(fn.get("arguments"), str) else (fn.get("arguments") or {})
                except ValueError:
                    a = {}
                mistakes += failed(fn.get("name"), a if isinstance(a, dict) else {}, res.get(c.get("id")))
        ms = {x.get("milestone") for x in kept if x.get("milestone")}
        r["f"] = {"mistake": mistakes > 0, "retry streak": why["retry streak"] > 0, "repeat": why["repeat"] > 0,
                  "reading on (>= 3 replies)": why["reading on"] >= 3, "saw the fix": "saw the fix" in ms, "right place": "right place" in ms}
def sign_p(w, l):
    n = w + l
    return 1.0 if n == 0 else min(1, 2 * sum(comb(n, k) for k in range(max(w, l), n + 1)) / 2 ** n)
paired = {t: v for t, v in by.items() if any(r["ok"] for r in v) and not all(r["ok"] for r in v)}
print(f"sk_a2 runs {len(runs)} on {len(by)} tasks; same-task comparison on {len(paired)} tasks with both outcomes")
print(f"{'rule':28} {'intended':8} {'solved runs':>12} {'failed runs':>12} | tasks where failed > solved / solved > failed | p")
for k, kind in (("mistake", "masked"), ("retry streak", "bad"), ("repeat", "bad"), ("reading on (>= 3 replies)", "bad"), ("saw the fix", "good"), ("right place", "good")):
    S = [r["f"][k] for v in paired.values() for r in v if r["ok"]]; F = [r["f"][k] for v in paired.values() for r in v if not r["ok"]]
    up = dn = 0
    for v in paired.values():
        s = sum(r["f"][k] for r in v if r["ok"]) / max(1, sum(r["ok"] for r in v)); f = sum(r["f"][k] for r in v if not r["ok"]) / max(1, sum(not r["ok"] for r in v))
        up += f > s; dn += s > f
    print(f"{k:28} {kind:8} {sum(S)/len(S):12.0%} {sum(F)/len(F):12.0%} | {up:3} / {dn:3} | {sign_p(up, dn):.3f}")
