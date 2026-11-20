"""Do runs loop (Google's 'cyclical reasoning loops')? sb1h / sb1hl / sb1hlf runs (r118-r132): repeated tool calls (the same read_file
file + start line, or the same run_command text) before vs after the first compaction, by outcome and by whether the run ever edited.
Run: python3 -I scripts/mine_bank/repeat_loops.py"""
import ast, collections, glob, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARMS = {"sb1h", "sb1hl", "sb1hlf"}
S = collections.defaultdict(lambda: collections.Counter())
for f in sorted(glob.glob(str(ROOT / "data/results/2026-11-*_skill_r1[123][0-9]_p*/requests/requests.jsonl"))):
    G = {}
    for l in open(Path(f).parent.parent / "results/gen_per_task.jsonl"):
        g = json.loads(l); G[g["instance_id"] + "#a" + g["attempt"]] = g
    by = collections.defaultdict(list)
    for l in open(f, errors="replace"):
        r = json.loads(l)
        if r["job"].split("#a")[1].split(".")[0] in ARMS:
            by[r["job"]].append(r)
    for job, rs in by.items():
        g = G.get(job)
        if not g:
            continue
        rs.sort(key=lambda r: float(r["t"]))
        seen = set(); phase = "before"; edited = False; c = collections.Counter()
        for r in rs:
            if len(r["request"]["messages"]) == 1:
                phase = "after"; continue
            if "EDITED " in str(r["request"]["messages"][-1].get("content")):
                edited = True
            try:
                m = ast.literal_eval(str(r["reply"])).get("message") or {}
            except Exception:
                continue
            for cl in m.get("tool_calls") or []:
                try:
                    a = json.loads(cl["function"]["arguments"])
                except Exception:
                    a = {}
                key = (cl["function"]["name"], a.get("filepath"), a.get("start_line")) if cl["function"]["name"] == "read_file" else (cl["function"]["name"], a.get("command", "").strip())
                c[phase + " calls"] += 1
                if key in seen:
                    c[phase + " repeats"] += 1
                seen.add(key)
        grp = ("solved" if g.get("resolved") in (True, "True") else "failed, edited" if edited else "failed, never edited")
        S[grp]["runs"] += 1; S[grp]["runs compacted"] += phase == "after"
        for k, v in c.items():
            S[grp][k] += v
for grp in ("solved", "failed, edited", "failed, never edited"):
    c = S[grp]
    if not c["runs"]:
        continue
    rb = c["before repeats"] / max(1, c["before calls"]); ra = c["after repeats"] / max(1, c["after calls"])
    print(f"  {grp:22} runs {c['runs']:3} (compacted {c['runs compacted']}) | repeated calls before compaction {c['before repeats']}/{c['before calls']} ({100*rb:.0f}%) | after {c['after repeats']}/{c['after calls']} ({100*ra:.0f}%)")
