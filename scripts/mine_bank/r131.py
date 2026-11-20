"""r131: sb1hl vs sb1hlf vs sbE6 on fastapi_15589 + fastapi_11194, 2 passes (docs/PLAN.md RUN BUILT r131). Run: python3 -I scripts/mine_bank/r131.py
Per run: outcome, end, calls; text-form replies; for sbE6 the stage / writer timing, the writer's note, the check events and the call sequence."""
import ast, collections, glob, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TXT = re.compile(r"<\|tool_call>|call:\w+\{|```python\n")
EV = [("shown", "the problem is shown"), ("NOT-ISSUE", "PASSES before any edit"), ("BROKEN", "SCRIPT BROKEN"), ("HELD", "EDIT HELD BACK"),
      ("MISSING", "NO EXPECTATION FILE"), ("still", "STILL FAILS with your edit"), ("DONE", "PASSES with your edit"), ("LATE", "NOTHING EDITED YET"),
      ("f0", "old text found 0 times"), ("halved", "double backslashes")]
for d in sorted(glob.glob(str(ROOT / "data/results/2026-11-20_skill_r131_p*"))):
    G = {json.loads(l)["instance_id"] + " " + json.loads(l)["arm"]: json.loads(l) for l in open(f"{d}/results/gen_per_task.jsonl")}
    by = collections.defaultdict(list)
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        r = json.loads(l)
        by[r["job"].split("#")[0] + " " + r["job"].split("#a")[1].split(".")[0]].append(r)
    for k, rs in sorted(by.items(), key=lambda x: (x[0].split()[1], x[0])):
        rs.sort(key=lambda r: float(r["t"])); t0 = float(rs[0]["t"]); g = G.get(k, {}); seq = []; tx = 0
        for r in rs:
            ms = r["request"]["messages"]
            if len(ms) == 1:
                seq.append("COMPACT"); continue
            who = {"Your only job is one search": "S:", "Your only job is to write": "W:"}.get(next((p for p in ("Your only job is one search", "Your only job is to write") if ms[0]["content"].startswith(p)), ""), "")
            if ms[-1].get("role") == "tool" and seq:
                out = str(ms[-1].get("content")).replace("\\n", "\n")
                h = [n for n, p in EV if p in out]
                if h: seq[-1] += "[" + ",".join(h) + "]"
            m = ast.literal_eval(str(r["reply"])).get("message") or {}; t = float(r["t"]) - t0
            if not m.get("tool_calls"):
                c = m.get("content") or ""
                if TXT.search(c): tx += 1
                seq.append(f"{who}{'TEXTCALL' if TXT.search(c) else 'reply'}@{t:.0f}")
            for c in m.get("tool_calls") or []:
                a = c["function"]["arguments"]
                kind = "CHECK" if "check.sh <<'EOF'" in a else "REWRITE" if "<<'EXPECT'" in a else "EDIT" if "OLD_TEXT" in a else c["function"]["name"][:4]
                seq.append(f"{who}{kind}@{t:.0f}")
        print(f"{Path(d).name[-2:]} {k:22} {'SOLVED' if g.get('resolved') in (True, 'True') else 'failed'} end {g.get('end'):9} calls {g.get('tool_calls')} text-calls {tx}\n    " + " ".join(seq)[:1500])
