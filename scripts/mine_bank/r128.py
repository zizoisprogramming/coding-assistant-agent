"""r128: sbE3 alone on fastapi_15589, rich_3278, fastapi_11194, fastapi_12942, 2 passes (docs/PLAN.md RUN BUILT r128, bars there).
Run: python3 -I scripts/mine_bank/r128.py
1. r127.py's per-run table, bars and hand reading, re-pointed at r128 and sbE3's event texts (+ the hold-back event);
2. per run: the call sequence (s = search/other run_command, R = read_file, X = expectation, E = edit, C = re-run, P = submit), the
   events after each call, text-form tool calls (replies whose text carries a call), and what followed the hold-back /
   'not the one in the issue'."""
import ast, collections, glob, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
src = (ROOT / "scripts/mine_bank/r127.py").read_text()
reps = [('glob.glob(str(ROOT / "data/results/2026-11-20_skill_r127_p*"))', 'glob.glob(str(ROOT / "data/results/2026-11-20_skill_r128_p*"))'),
        ('("broken", "SCRIPT ITSELF IS BROKEN")', '("broken", "SCRIPT BROKEN"), ("held", "EDIT HELD BACK")'),
        ('("late", "Nothing is edited yet")', '("late", "NOTHING EDITED YET")'),
        ('for a in ("sbE1", "sbE2", "sbX1"):', 'for a in ("sbE3",):'),
        ('if a == "sbE2" else ""))', 'if a == "sbE3" else "") + f" | held back {sum(\'held\' in r[\'ev\'] for r in X)}")'),
        ('"data/analysis/r127_rows.json"', '"data/analysis/r128_rows.json"')]
for a, b in reps:
    assert src.count(a) == 1, a
    src = src.replace(a, b)
exec(compile(src, "r127_on_r128", "exec"), {"__name__": "__main__", "__file__": str(ROOT / "scripts/mine_bank/r127.py")})

print("\n#### call sequences")
EVS = [("shown", "the problem is shown"), ("NOT-ISSUE", "PASSES before any edit"), ("BROKEN", "SCRIPT BROKEN"), ("HELD", "EDIT HELD BACK"),
       ("still", "STILL FAILS with your edit"), ("DONE", "PASSES with your edit"), ("LATE", "NOTHING EDITED YET"), ("f0", "old text found 0 times"),
       ("EDITED", "\nEDITED ")]
TEXTCALL = re.compile(r"tool_call|call:run_command|call:read_file|^tool: run_command", re.M)
for d in sorted(glob.glob(str(ROOT / "data/results/2026-11-20_skill_r128_p*"))):
    runs = collections.defaultdict(list)
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        r = json.loads(l)
        if len(r["request"]["messages"]) > 1:
            runs[r["job"].split("#")[0]].append(r)
    G = {json.loads(l)["instance_id"]: json.loads(l) for l in open(f"{d}/results/gen_per_task.jsonl")}
    for iid, rs in sorted(runs.items()):
        rs.sort(key=lambda r: float(r["t"]))
        t0 = float(rs[0]["t"])
        seq, textcalls = [], 0
        for r in rs:
            last = r["request"]["messages"][-1]
            if last.get("role") == "tool" and seq:
                out = "\n" + str(last.get("content")).replace("\\n", "\n")
                seq[-1] += "[" + ",".join(k for k, p in EVS if p in out) + "]" if any(p in out for _, p in EVS) else ""
            try:
                m = ast.literal_eval(str(r["reply"])).get("message") or {}
            except Exception:
                m = {}
            if not m.get("tool_calls") and TEXTCALL.search(m.get("content") or ""):
                textcalls += 1
            for c in m.get("tool_calls") or []:
                n = c["function"]["name"]
                try:
                    cmd = json.loads(c["function"]["arguments"]).get("command", "")
                except Exception:
                    cmd = ""
                k = ("X" if "<<'EXPECT'" in cmd else "E" if "OLD_TEXT" in cmd else "C" if cmd.strip() == "bash .git/agent/check.sh" else "s") if n == "run_command" else {"read_file": "R", "submit_patch": "P"}.get(n, n[:3])
                seq.append(f"{k}@{float(r['t']) - t0:.0f}")
        g = G.get(iid, {})
        print(f"\n  {Path(d).name[-2:]} {iid} {'SOLVED' if g.get('resolved') in (True, 'True') else 'failed'} end {g.get('end')} | text-form calls {textcalls}\n    " + " ".join(seq))
