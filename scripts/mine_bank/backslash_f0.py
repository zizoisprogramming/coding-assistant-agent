"""How often do heredoc edits (sb1h family and later, r118+) fail with 'old text found 0 times' when the old text carries a doubled
backslash (the model copies the JSON-escaped form of the tool result)? Run: python3 -I scripts/mine_bank/backslash_f0.py"""
import ast, collections, glob, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD = re.compile(r"<<'OLD_TEXT'\n(.*?)OLD_TEXT", re.S)
edits = f0 = f0_bs = 0
runs_bs = set(); runs_all = set(); task = collections.Counter(); lost = set()
for d in sorted(glob.glob(str(ROOT / "data/results/2026-11-*_skill_r1[12][0-9]_p*"))):
    f = Path(d) / "requests/requests.jsonl"
    if not f.exists():
        continue
    by = collections.defaultdict(list)
    for l in open(f, errors="replace"):
        try:
            r = json.loads(l)
        except Exception:
            continue
        if len(r["request"]["messages"]) > 1:
            by[r["job"]].append(r)
    G = {}
    for gp in glob.glob(f"{d}/results/gen_per_task.jsonl"):
        for l in open(gp):
            g = json.loads(l); G[g["instance_id"] + "#a" + g["arm"]] = g
    for job, rs in by.items():
        rs.sort(key=lambda r: float(r["t"]))
        runs_all.add((d, job))
        for i, r in enumerate(rs[:-1]):
            try:
                m = ast.literal_eval(str(r["reply"])).get("message") or {}
            except Exception:
                continue
            for c in m.get("tool_calls") or []:
                try:
                    cmd = json.loads(c["function"]["arguments"]).get("command", "")
                except Exception:
                    continue
                o = OLD.search(cmd)
                if not o:
                    continue
                edits += 1
                out = str(rs[i + 1]["request"]["messages"][-1].get("content"))
                if "old text found 0 times" in out:
                    f0 += 1
                    if "\\\\" in o.group(1):
                        f0_bs += 1; runs_bs.add((d, job)); task[job.split("#")[0]] += 1
print(f"runs {len(runs_all)} | heredoc edits {edits} | found 0 {f0} | found 0 with a doubled backslash in the old text {f0_bs} in {len(runs_bs)} runs")
print("tasks:", dict(task))
