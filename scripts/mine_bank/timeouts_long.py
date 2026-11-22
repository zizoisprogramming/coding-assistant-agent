"""Long replies (>= 1800 output tokens) in r138 + r139: per run count, finish_reason, has tool call, what call came before,
call index, which task; time-end vs ok. Run: python3 -I scripts/mine_bank/timeouts_long.py"""
import ast, collections, glob, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
C = collections.Counter(); per = collections.defaultdict(lambda: [0, 0, 0.0]); ex = []
for d in sorted(glob.glob(str(ROOT / "data/results/2026-11-22_skill_r13[89]_s*"))):
    G = {}
    for l in open(f"{d}/results/gen_per_task.jsonl"):
        g = json.loads(l); G[g["instance_id"] + "#a" + g["attempt"]] = g
    by = collections.defaultdict(list)
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        r = json.loads(l); by[r["job"]].append(r)
    for job, rs in by.items():
        g = G.get(job)
        if not g: continue
        rs.sort(key=lambda r: float(r["t"])); end = g["end"]; prev = "(start)"; ncall = 0
        for r in rs:
            rep = r["reply"] if isinstance(r["reply"], dict) else ast.literal_eval(str(r["reply"]))
            u = rep.get("usage") or {}; ot = u.get("completion_tokens") or 0; m = rep.get("message") or {}
            tc = m.get("tool_calls") or []; summ = len(r["request"]["messages"]) <= 1
            cap = 4096 if "a2t" in job else 2048
            if ot >= 1800 and not summ:
                k = "tool call" if tc else "text only"
                C[(end, k, rep.get("finish_reason"))] += 1
                per[(end, job.split("#")[1].split(".")[0][1:])][0] += 1
                per[(end, job.split("#")[1].split(".")[0][1:])][2] += float(r["seconds"])
                content = (m.get("content") or "")
                ex.append((end, Path(d).name[-7:], job, ncall, ot, float(r["seconds"]), k, prev[:70], len(content), content[:160].replace("\n", " ")))
            if not summ:
                for c in tc: prev = c["function"]["name"] + " " + c["function"]["arguments"][:60].replace("\n", " ")
                if tc: ncall += len(tc)
            else: C[("summary call", end)] += 1
for k, v in sorted(C.items(), key=str): print(k, v)
print()
for k, v in sorted(per.items()): print(k, "long replies", v[0], "seconds", round(v[2]))
print()
for e in ex[:40]: print(e)
