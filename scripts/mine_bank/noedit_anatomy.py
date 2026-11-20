"""Where do the calls of sb1h-family runs that never changed the source go? (r118-r133 logs; arms sb1h / sb1hl / sb1hlf.)
Per never-edited run: call kinds (read_file, search = git grep / grep / find / ls / cat / sed -n, own script runs = python, pytest, edit
attempts = OLD_TEXT heredocs and their results: found 0 / found 1 / EDITED / fence error), how the run ended, elapsed time at the 28th call.
Then the same for solved runs (first-edit call index). Run: python3 -I scripts/mine_bank/noedit_anatomy.py"""
import ast, collections, glob, json, re, statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARMS = {"sb1h", "sb1hl", "sb1hlf"}
def kind(name, a):
    if name != "run_command":
        return name
    c = a.get("command", "")
    if "OLD_TEXT" in c: return "EDIT-ATTEMPT"
    if re.search(r"\bpytest\b", c): return "pytest"
    if re.search(r"(^|\s)(git grep|grep|rg|find|ls)\b", c): return "search"
    if re.search(r"(^|\s)(cat|sed -n|head|tail|nl|awk)\b", c): return "read-cmd"
    if re.search(r"\bpython3?\b", c): return "own python"
    if re.search(r"\bgit (log|show|diff|status|blame)\b", c): return "git"
    return "other"
agg = {"never": collections.Counter(), "solved": collections.Counter()}
ends = collections.Counter(); attempts = collections.Counter(); t28 = []; solved_first = []; never_n = 0; solved_n = 0
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
        calls = []; edited = False; first_edit_idx = None
        for i, r in enumerate(rs):
            out = str(r["request"]["messages"][-1].get("content")).replace("\\n", "\n")
            if calls and calls[-1][0] == "EDIT-ATTEMPT":
                res = "EDITED" if re.search(r"(?m)^EDITED ", out) else "found 0" if "found 0 times" in out else "fence/EOF" if "unexpected EOF" in out else "other"
                attempts[res] += 1 if not edited else 0
            if re.search(r"(?m)^EDITED ", out) and not edited:
                edited = True; first_edit_idx = len(calls)
            try:
                m = ast.literal_eval(str(r["reply"])).get("message") or {}
            except Exception:
                continue
            for c in m.get("tool_calls") or []:
                try: a = json.loads(c["function"]["arguments"])
                except Exception: a = {}
                calls.append((kind(c["function"]["name"], a), float(r["t"]) - t0))
        solved = g.get("resolved") in (True, "True")
        if solved:
            solved_n += 1; solved_first.append(first_edit_idx or 0)
            for k, _ in calls: agg["solved"][k] += 1
        elif not edited:
            never_n += 1; ends[g.get("end")] += 1
            for k, _ in calls: agg["never"][k] += 1
            if len(calls) >= 28: t28.append(calls[27][1])
print(f"never-edited failed runs {never_n} | ends {dict(ends)} | elapsed s at the 28th call: median {st.median(t28) if t28 else 0:.0f} (n {len(t28)}), 25-75% {sorted(t28)[len(t28)//4] if t28 else 0:.0f}-{sorted(t28)[3*len(t28)//4] if t28 else 0:.0f}")
print("  their edit attempts before any applied edit:", dict(attempts))
for grp, n in (("never", never_n), ("solved", solved_n)):
    c = agg[grp]; tot = sum(c.values())
    print(f"  {grp:6} calls per run {tot/max(1,n):.1f}: " + " | ".join(f"{k} {v/max(1,n):.1f}" for k, v in c.most_common()))
print(f"solved runs {solved_n}: first applied edit at call index median {st.median(solved_first):.0f}, 25-75% {sorted(solved_first)[len(solved_first)//4]}-{sorted(solved_first)[3*len(solved_first)//4]}, after call 24: {sum(x > 24 for x in solved_first)}")
