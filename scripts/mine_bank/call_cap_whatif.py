"""What if sb1h-family runs had 40 tool calls instead of 28 (the harness's 'Finalize your edits and call submit_patch soon' warning would
start at call 30 instead of 18)? Over r118-r133 sb1h / sb1hl / sb1hlf runs: which runs end at the call cap (28 calls used, not time), when
(elapsed s), with or without an edit; the projected extra time if they continued at their own seconds-per-call up to 40 calls or the 480 s
cap; and the projected mean agent time. Run: python3 -I scripts/mine_bank/call_cap_whatif.py"""
import ast, collections, glob, json, re, statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARMS = {"sb1h", "sb1hl", "sb1hlf"}
rows = []
for f in sorted(glob.glob(str(ROOT / "data/results/2026-11-*_skill_r1[123][0-9]_p*/requests/requests.jsonl"))):
    G = {}
    for l in open(Path(f).parent.parent / "results/gen_per_task.jsonl"):
        g = json.loads(l); G[g["instance_id"] + "#a" + g["attempt"]] = g
    by = collections.defaultdict(list)
    for l in open(f, errors="replace"):
        r = json.loads(l)
        if r["job"].split("#a")[1].split(".")[0] in ARMS and len(r["request"]["messages"]) > 1:
            by[r["job"]].append(r)
    for job, rs in by.items():
        g = G.get(job)
        if not g: continue
        rs.sort(key=lambda r: float(r["t"])); t0 = float(rs[0]["t"])
        edited = any(re.search(r"(?m)^EDITED ", str(r["request"]["messages"][-1].get("content")).replace("\\n", "\n")) for r in rs)
        warned = next((i for i, r in enumerate(rs) if "Finalize your edits" in str(r["request"]["messages"][-1].get("content"))), None)
        agent = float(g.get("agent_s") or 0); calls = int(g.get("tool_calls") or 0)
        rows.append(dict(solved=g.get("resolved") in (True, "True"), edited=edited, end=g.get("end"), agent=agent, calls=calls,
                         capped=calls >= 28 and g.get("end") != "time", spc=agent / max(1, calls)))
n = len(rows)
cap = [r for r in rows if r["capped"]]
print(f"runs {n} | mean agent s {st.mean(r['agent'] for r in rows):.0f} | ended at the 28-call cap (not time) {len(cap)} ({100*len(cap)/n:.0f}%): "
      f"solved {sum(r['solved'] for r in cap)}, edited-but-failed {sum(r['edited'] and not r['solved'] for r in cap)}, never edited {sum(not r['edited'] for r in cap)}; "
      f"their elapsed s median {st.median(r['agent'] for r in cap):.0f}")
proj = []
for r in rows:
    if r["capped"]:
        proj.append(min(480.0, r["agent"] + 12 * r["spc"]))
    else:
        proj.append(r["agent"])
print(f"projected mean agent s with 40 calls (capped runs continue at their own pace, 480 s cap): {st.mean(proj):.0f} (now {st.mean(r['agent'] for r in rows):.0f})")
solved = [r for r in rows if r["solved"]]
print(f"solved runs {len(solved)}: calls used median {st.median(r['calls'] for r in solved):.0f}; at the cap {sum(r['capped'] for r in solved)}")
