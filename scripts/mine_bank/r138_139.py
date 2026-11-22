"""r138 (sk_a2 + 6 one-change arms) and r139 (sk_a2 vs sk_a2m) on the 8 solvable dev16, two shards each (bars in docs/PLAN.md RUN BUILT r138 / r139).
Run: python3 -I scripts/mine_bank/r138_139.py
Per run: outcome, end, calls, agent s; the first call (install? with names?); reads through a.py vs read_file vs raw cat / sed / grep;
first NO EDIT YET / STOP READING (call index) and whether an edit followed (within 2 calls / later); first applied edit; source change in
the patch; empty submit; the call sequence."""
import ast, collections, glob, json, re, statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
A = collections.defaultdict(lambda: collections.Counter()); TIMES = collections.defaultdict(list)
def kind(n, a):
    c = a.get("command", "") if n == "run_command" else ""
    if n == "run_skill_script": return "INSTALL" + ("+names" if a.get("positional_args") else "")
    if "OLD_TEXT" in c: return "EDIT"
    if "a.py" in c: return "apy"
    if n == "read_file": return "read_file"
    if re.search(r"(^|\s)(cat|sed -n|head|tail|grep|git grep)\b", c): return "raw"
    return {"submit_patch": "P", "get_status": "st"}.get(n, "py" if "python" in c else n[:6])
for d in sorted(glob.glob(str(ROOT / "data/results/2026-11-22_skill_r13[89]_s*"))):
    G = {json.loads(l)["instance_id"] + " " + json.loads(l)["arm"]: json.loads(l) for l in open(f"{d}/results/gen_per_task.jsonl")}
    by = collections.defaultdict(list)
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        r = json.loads(l)
        if len(r["request"]["messages"]) > 1: by[r["job"].split("#")[0] + " " + r["job"].split("#a")[1].split(".")[0]].append(r)
    for k in sorted(G, key=lambda x: (x.split()[1], x)):
        iid, arm = k.split(); g = G[k]; rs = sorted(by[k], key=lambda r: float(r["t"])); t0 = float(rs[0]["t"])
        calls = []; first_edit = None; ban = {}; last = ""
        for r in rs:
            out = str(r["request"]["messages"][-1].get("content")).replace("\\n", "\n")
            for b in ("NO EDIT YET", "STOP READING"):
                if b in out and b not in ban: ban[b] = len(calls)
            if "last shown, kept here" in out: ban["lastpin"] = ban.get("lastpin", len(calls))
            if first_edit is None and re.search(r"(?m)^EDITED ", out): first_edit = len(calls)
            m = ast.literal_eval(str(r["reply"])).get("message") or {}
            if not m.get("tool_calls"): last = (m.get("content") or "")[:70]
            for c in m.get("tool_calls") or []:
                try: a = json.loads(c["function"]["arguments"])
                except Exception: a = {}
                calls.append(kind(c["function"]["name"], a))
        pf = list(Path(d).glob(f"results/gen/patches/{iid}__a{arm}.*.diff"))
        files = re.findall(r"^\+\+\+ b/(\S+)", pf[0].read_text(errors="replace"), re.M) if pf else []
        src = [f for f in files if f.endswith(".py") and "test" not in f and "repro" not in f]
        solved = g.get("resolved") in (True, "True"); akey = arm + (" r139" if "r139" in d else " r138") if arm == "sk_a2" else arm; c = A[akey]
        c["runs"] += 1; c["solved"] += solved; c["no source change"] += not src; c["empty submit"] += ("P" in calls) and not src
        c["time ends"] += g.get("end") == "time"; c["install first"] += bool(calls) and calls[0].startswith("INSTALL"); c["install with names"] += "INSTALL+names" in calls
        c["a.py reads"] += calls.count("apy"); c["read_file"] += calls.count("read_file"); c["raw reads"] += calls.count("raw")
        for b, i in ban.items():
            if b == "lastpin": c["lastpin seen"] += 1; continue
            c[b + " seen"] += 1; c[b + " -> edit within 2"] += first_edit is not None and i <= first_edit < i + 2; c[b + " -> edit later"] += first_edit is not None and first_edit >= i
        TIMES[akey].append(float(g.get("agent_s") or 0))
        print(f"{Path(d).name[-7:]} {arm:8} {iid:14} {'SOLVED' if solved else 'failed'} end {g.get('end'):4} calls {g.get('tool_calls'):>2} agent {float(g.get('agent_s', 0)):3.0f}s first edit @{first_edit} banners {ban} src {src} | {' '.join(calls)} | {last!r}")
print()
for arm in sorted(A):
    print(f"  {arm}: " + " | ".join(f"{k} {v}" for k, v in A[arm].items()) + f" | mean agent s {st.mean(TIMES[arm]):.0f}")
