"""r132: sb1hl alone on the 8 solvable dev16, 2 passes (docs/PLAN.md RUN BUILT r132). Run: python3 -I scripts/mine_bank/r132.py
Per run: outcome, end, calls, compactions, first edit time, the patch's files (real-fix file or not, scratch files), whether submit_patch was
called, text-form replies, and the final reply."""
import ast, collections, glob, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
T = {json.loads(l)["instance_id"]: json.loads(l) for l in open(ROOT / "data/tasks.jsonl")}
TXT = re.compile(r"<\|tool_call>|call:\w+\{")
tot = collections.Counter()
for d in sorted(glob.glob(str(ROOT / "data/results/2026-11-20_skill_r132_p*"))):
    G = {json.loads(l)["instance_id"]: json.loads(l) for l in open(f"{d}/results/gen_per_task.jsonl")}
    by = collections.defaultdict(list); comp = collections.Counter()
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        r = json.loads(l); k = r["job"].split("#")[0]
        if len(r["request"]["messages"]) == 1: comp[k] += 1
        else: by[k].append(r)
    for iid in sorted(G):
        g = G[iid]; rs = sorted(by[iid], key=lambda r: float(r["t"])); t0 = float(rs[0]["t"]) if rs else 0
        first = None; sub = False; tx = 0; last = ""
        for r in rs:
            if first is None and re.search(r"(?m)^EDITED ", str(r["request"]["messages"][-1].get("content")).replace("\\n", "\n")):
                first = float(r["t"]) - t0
            m = ast.literal_eval(str(r["reply"])).get("message") or {}
            sub |= any(c["function"]["name"] == "submit_patch" for c in m.get("tool_calls") or [])
            if not m.get("tool_calls"):
                tx += bool(TXT.search(m.get("content") or "")); last = (m.get("content") or "")[:90]
        gold = set(re.findall(r"^\+\+\+ b/(\S+)", T[iid]["patch"], re.M))
        pf = list(Path(d).glob(f"results/gen/patches/{iid}__*.diff"))
        files = re.findall(r"^\+\+\+ b/(\S+)", pf[0].read_text(errors="replace"), re.M) if pf else []
        cls = "SOLVED" if g.get("resolved") in (True, "True") else ("no source change" if not [f for f in files if f in gold or (f.endswith(".py") and "test" not in f and "repro" not in f)] else "real-fix file" if set(files) & gold else "other file")
        tot[cls] += 1; tot["text-call runs"] += tx > 0; tot["submitted"] += sub
        print(f"{Path(d).name[-2:]} {iid:14} {cls:16} end {g.get('end'):5} calls {g.get('tool_calls'):>2} comp {comp[iid]} first edit {('%.0f s' % first) if first is not None else 'never':6} submit {sub!s:5} text {tx} | patch files {files} | last reply {last!r}")
print("\n", dict(tot))
