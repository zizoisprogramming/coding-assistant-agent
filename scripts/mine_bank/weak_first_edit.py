"""Title-only weak tasks (rich_3470, rich_4079, rich_3521): first source-edit time and call index in solved vs failed runs, over every
logged run with requests. An edit = edit_file / write_file to a non-scratch .py, a heredoc OLD_TEXT edit, sed -i, or git apply / patch.
Run: python3 -I scripts/mine_bank/weak_first_edit.py"""
import ast, collections, glob, json, re, statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TASKS = ("rich_3470", "rich_4079", "rich_3521")
SCR = re.compile(r"(repro|reproduce|test_|debug|check_|scratch|tmp|\.git/agent/(?!old|new))")
def is_edit(name, a):
    if name in ("edit_file", "write_file"):
        fp = a.get("filepath", "") or a.get("path", "")
        return fp.endswith(".py") and not SCR.search(fp)
    cmd = a.get("command", "") if isinstance(a, dict) else ""
    return "OLD_TEXT" in cmd or re.search(r"sed -i|git apply|patch -p", cmd) is not None
R = collections.defaultdict(lambda: {"solved": [], "failed": []})
for f in glob.glob(str(ROOT / "data/results/*/requests/requests.jsonl")):
    gp = Path(f).parent.parent / "results/gen_per_task.jsonl"
    if not gp.exists():
        continue
    G = {}
    for l in open(gp):
        try:
            g = json.loads(l); G[g["instance_id"] + "#a" + g.get("attempt", "")] = g
        except Exception:
            pass
    by = collections.defaultdict(list)
    for l in open(f, errors="replace"):
        if not any(t in l for t in TASKS):
            continue
        try:
            r = json.loads(l)
        except Exception:
            continue
        if "job" in r and len(r["request"]["messages"]) > 1:
            by[r["job"]].append(r)
    for job, rs in by.items():
        iid = job.split("#")[0]
        if iid not in TASKS:
            continue
        g = G.get(job)
        if not g:
            continue
        rs.sort(key=lambda r: float(r["t"])); t0 = float(rs[0]["t"]); n = 0; first = None
        for r in rs:
            try:
                m = ast.literal_eval(str(r["reply"])).get("message") or {}
            except Exception:
                continue
            for c in m.get("tool_calls") or []:
                n += 1
                try:
                    a = json.loads(c["function"]["arguments"])
                except Exception:
                    a = {}
                if first is None and is_edit(c["function"]["name"], a):
                    first = (float(r["t"]) - t0, n)
        R[iid]["solved" if g.get("resolved") in (True, "True") else "failed"].append(first)
for iid in TASKS:
    for k in ("solved", "failed"):
        X = R[iid][k]; E = [x for x in X if x]
        if X:
            print(f"  {iid} {k:6} runs {len(X):3} | edited {len(E):3} ({100*len(E)/len(X):.0f}%) | first edit median {st.median([e[0] for e in E]) if E else 0:5.0f} s, call {st.median([e[1] for e in E]) if E else 0:4.0f}"
                  + (f" | edited by 150 s {sum(e[0] <= 150 for e in E)}" if E else ""))
