"""r129: sbE3b vs sbE4A vs sbE4B on r128's 4 tasks, 2 passes (docs/PLAN.md RUN BUILT r129, bars there).
Run: python3 -I scripts/mine_bank/r129.py
1. r128.py's per-run table, bars, hand reading and call sequences re-pointed at r129 (all three arms);
2. per arm: text-form replies split by whether the solver had made any real tool call before (first call vs later), the backslash
   note, 'finished closing' messages and the next reply, edits undone with checkout / stash / reset, stage replies (sbE4A)."""
import ast, collections, glob, json, re, statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
src = (ROOT / "scripts/mine_bank/r128.py").read_text()
src = src.replace("2026-11-20_skill_r128_p*", "2026-11-20_skill_r129_p*")
a = 'src = src.replace(a, b)\nexec('
assert src.count(a) == 1
src = src.replace(a, 'src = src.replace(a, b)\nsrc = src.replace("2026-11-20_skill_r128_p*", "2026-11-20_skill_r129_p*").replace(\'for a in ("sbE3",):\', \'for a in ("sbE3b", "sbE4A", "sbE4B"):\').replace(\'if a == "sbE3" else ""\', \'if a else ""\').replace("r128_rows.json", "r129_rows.json")\nexec(')
src = src.replace('runs[r["job"].split("#")[0]].append(r)', 'runs[r["job"].split("#")[0] + " " + r["job"].split("#a")[1].split(".")[0]].append(r)')
src = src.replace('G = {json.loads(l)["instance_id"]: json.loads(l) for l in open(f"{d}/results/gen_per_task.jsonl")}',
                  'G = {json.loads(l)["instance_id"] + " " + json.loads(l)["arm"]: json.loads(l) for l in open(f"{d}/results/gen_per_task.jsonl")}')
exec(compile(src, "r128_on_r129", "exec"), {"__name__": "__main__", "__file__": str(ROOT / "scripts/mine_bank/r128.py")})

print("\n#### r129 extras per arm")
TXT = re.compile(r"<\|tool_call>|call:run_command|call:read_file")
CLOSING = "finished closing"
WIPE = re.compile(r"git (checkout( -f)? (HEAD|-- |\.|[\w/]+\.py)|stash|reset --hard|restore )")
S = collections.defaultdict(lambda: collections.Counter())
stage_t, stage_nothing = collections.defaultdict(list), collections.Counter()
for d in sorted(glob.glob(str(ROOT / "data/results/2026-11-20_skill_r129_p*"))):
    by = collections.defaultdict(list)
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        r = json.loads(l)
        if len(r["request"]["messages"]) > 1:
            by[r["job"]].append(r)
    for job, rs in by.items():
        arm = job.split("#a")[1].split(".")[0]
        rs.sort(key=lambda r: float(r["t"]))
        real = 0; edited = False; t0 = float(rs[0]["t"])
        for i, r in enumerate(rs):
            sysm = r["request"]["messages"][0]["content"]
            d_ = ast.literal_eval(str(r["reply"])); m = d_.get("message") or {}
            if sysm.startswith("Your only job is one search"):
                if not m.get("tool_calls"):
                    stage_t[arm].append(float(r["t"]) + float(r.get("seconds") or 0) - t0)
                    stage_nothing[arm] += "NOTHING RELEVANT" in (m.get("content") or "")
                continue
            last = str(r["request"]["messages"][-1].get("content"))
            if "double backslashes in your text read as single ones" in last:
                S[arm]["backslash note"] += 1
            if "EDITED " in last:
                edited = True
            c = m.get("content") or ""
            if not m.get("tool_calls") and TXT.search(c):
                S[arm]["text replies, no real call before" if real == 0 else "text replies, after real calls"] += 1
            if CLOSING in last:
                S[arm]["closing messages"] += 1
                S[arm]["  -> next reply a real call" if m.get("tool_calls") else "  -> next reply text again"] += 1
            for cl in m.get("tool_calls") or []:
                real += 1
                try:
                    cmd = json.loads(cl["function"]["arguments"]).get("command", "")
                except Exception:
                    cmd = ""
                if edited and WIPE.search(cmd):
                    S[arm]["edit undone (checkout / stash / reset)"] += 1
        S[arm]["runs"] += 1
for a in ("sbE3b", "sbE4A", "sbE4B"):
    print(f"  {a}: " + " | ".join(f"{k} {v}" for k, v in sorted(S[a].items())))
    if stage_t[a]:
        print(f"     stage replies {len(stage_t[a])} (incl. re-runs), median end {st.median(stage_t[a]):.0f} s, NOTHING RELEVANT {stage_nothing[a]}")
