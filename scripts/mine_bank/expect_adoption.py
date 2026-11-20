"""r127-r130 expectation arms: per run, was an expectation attempted (heredoc / write_file / as text), when, did the run edit, did it solve;
and for runs WITHOUT an expectation, what they did instead (own repro scripts, debug prints). Run: python3 -I scripts/mine_bank/expect_adoption.py"""
import ast, collections, glob, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
rows = []
for d in sorted(glob.glob(str(ROOT / "data/results/2026-11-20_skill_r1[23][0-9]_p*"))):
    if not re.search(r"r12[789]|r130", d):
        continue
    G = {}
    for l in open(f"{d}/results/gen_per_task.jsonl"):
        g = json.loads(l); G[(g["instance_id"], g["arm"])] = g
    by = collections.defaultdict(list)
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        r = json.loads(l)
        if len(r["request"]["messages"]) > 1 and not r["request"]["messages"][0]["content"].startswith(("Your only job", "You write the expectation")):
            by[r["job"]].append(r)
    for job, rs in by.items():
        iid, arm = job.split("#")[0], job.split("#a")[1].split(".")[0]
        if not arm.startswith("sbE"):
            continue
        rs.sort(key=lambda r: float(r["t"])); t0 = float(rs[0]["t"])
        exp_t = None; edited = False; repro = 0
        for r in rs:
            if "EDITED " in str(r["request"]["messages"][-1].get("content")):
                edited = True
            m = ast.literal_eval(str(r["reply"])).get("message") or {}
            blob = json.dumps(m.get("tool_calls") or []) + (m.get("content") or "")
            if exp_t is None and (".git/agent/expect.py" in blob):
                exp_t = float(r["t"]) - t0
            for c in m.get("tool_calls") or []:
                a = c["function"]["arguments"]
                if re.search(r"(repro|reproduce|check_|debug)\w*\.py", a) and "expect.py" not in a:
                    repro += 1
        g = G.get((iid, arm), {})
        rows.append(dict(arm=arm, iid=iid, exp=exp_t, edited=edited, solved=g.get("resolved") in (True, "True"), repro=repro))
def line(name, X):
    n = len(X)
    if n:
        print(f"  {name:38} runs {n:2} | edited {sum(r['edited'] for r in X):2} ({100*sum(r['edited'] for r in X)/n:.0f}%) | solved {sum(r['solved'] for r in X):2} ({100*sum(r['solved'] for r in X)/n:.0f}%) | own repro-script calls {sum(r['repro'] for r in X)}")
print(f"expectation-arm runs r127-r130: {len(rows)}")
line("expectation by 120 s", [r for r in rows if r["exp"] is not None and r["exp"] <= 120])
line("expectation later than 120 s", [r for r in rows if r["exp"] is not None and r["exp"] > 120])
line("no expectation at all", [r for r in rows if r["exp"] is None])
