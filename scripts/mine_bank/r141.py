"""r141: sk_a2 vs sk_a2r vs sk_a2v (repro check, fail-first) on the 8 solvable dev16, two shards (bars in docs/PLAN.md RUN BUILT r141).
Per run: outcome, end, agent s, calls, capped replies, probes (sk_a2r), a.py check calls and the events they printed (sk_a2v), repro written,
the place of the patch vs the real fix (fail_place buckets), empty submit. Run: python3 -I scripts/mine_bank/r141.py"""
import ast, collections, glob, json, re, statistics as st, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/mine_bank"))
T = {json.loads(l)["instance_id"]: json.loads(l)["patch"] for l in open(ROOT / "data/tasks.jsonl")}
EV = {"REPRO SHOWS THE BUG": "SHOWS", "YOUR REPRO DOES NOT SHOW THE BUG": "NOT-SHOWN", "STILL BUG": "STILL", "REPRO PASSES": "PASSES", "NO VERDICT": "NOVERDICT", "no .git/agent/repro.py yet": "NO-REPRO"}


def changed(diff):
    out, f, old = collections.defaultdict(set), None, 0
    for line in diff.split("\n"):
        if line.startswith("diff --git"): f = None
        elif line.startswith("+++ "):
            p = line[4:].strip(); f = p[2:] if p.startswith("b/") else None
            if f and (not f.endswith(".py") or re.search(r"(^|/)tests?/|test_|conftest|repro|^\.git/", f)): f = None
        elif line.startswith("@@"):
            m = re.match(r"@@ -(\d+)", line); old = int(m.group(1)) if m else 0
        elif f is None or line.startswith("--- "): continue
        elif line.startswith("-"): out[f].add(old); old += 1
        elif line.startswith("+"): out[f].add(old)
        elif line.startswith(" "): old += 1
    return {k: v for k, v in out.items() if v}


A = collections.defaultdict(collections.Counter); TM = collections.defaultdict(list)
for d in sorted(glob.glob(str(ROOT / "data/results/2026-11-23_skill_r141_s*"))):
    G = {}
    for l in open(f"{d}/results/gen_per_task.jsonl"):
        g = json.loads(l); G[g["instance_id"] + "#a" + g["attempt"]] = g
    by = collections.defaultdict(list)
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        r = json.loads(l); by[r["job"]].append(r)
    for job, rs in sorted(by.items(), key=lambda x: (G.get(x[0], {}).get("arm", ""), x[0])):
        g = G.get(job)
        if not g: continue
        rs = sorted([r for r in rs if len(r["request"]["messages"]) > 1], key=lambda r: float(r["t"])); arm = g["arm"]; task = g["instance_id"]
        calls, events, cap, capsec, probes, repro_w = [], [], 0, 0.0, 0, 0
        for r in rs:
            last = str(r["request"]["messages"][-1].get("content"))
            for k, v in EV.items():
                if k in last and ">>>" in last or (k.startswith("no .git") and k in last): events.append(v); break
            rep = r["reply"] if isinstance(r["reply"], dict) else ast.literal_eval(str(r["reply"]))
            o = (rep.get("usage") or {}).get("completion_tokens") or 0
            if o >= 1800: cap += 1; capsec += float(r["seconds"])
            for c in (rep.get("message") or {}).get("tool_calls") or []:
                n = c["function"]["name"]; a = c["function"]["arguments"]
                if "a.py check" in a: calls.append("CHECK")
                elif "a.py" in a: calls.append("apy")
                elif n == "write_file" and "repro.py" in a: calls.append("W-REPRO"); repro_w += 1
                elif n == "edit_file" and not re.search(r"repro|check|\.git/agent", a): calls.append("EDIT")
                elif n == "run_command" and ("OLD_TEXT" in a or ".replace(" in a) and "repro" not in a: calls.append("EDIT-sh")
                else: calls.append({"run_command": "run", "write_file": "write", "submit_patch": "SUBMIT", "get_status": "st", "run_skill_script": "install"}.get(n, n[:6]))
        pf = list(Path(d).glob(f"results/gen/patches/{task}__a{arm}.*.diff"))
        ch = changed(pf[0].read_text(errors="replace")) if pf else {}
        gold = changed(T[task])
        solved = g["resolved"] in (True, "True")
        if solved: b = "solved"
        elif not ch: b = "no source"
        elif not set(ch) & set(gold): b = "WRONG FILE"
        elif not any(abs(x - y) <= 5 for f in set(ch) & set(gold) for x in ch[f] for y in gold[f]): b = "WRONG SPOT"
        else: b = "RIGHT SPOT, WRONG LOGIC"
        c = A[arm]; c["runs"] += 1; c["solved"] += solved; c["time ends"] += g["end"] == "time"; c["no source change"] += not ch
        c["empty submit"] += ("SUBMIT" in calls) and not ch; c["capped replies"] += cap; c["capped s"] += round(capsec)
        c[b] += 0 if b == "solved" else 1
        if arm == "sk_a2v":
            c["runs with a check"] += "CHECK" in calls; c["checks"] += calls.count("CHECK"); c["repro writes"] += repro_w
            for e in events: c["ev " + e] += 1
            fe = next((i for i, x in enumerate(calls) if x.startswith("EDIT")), None); fc = next((i for i, x in enumerate(calls) if x == "CHECK"), None)
            c["check before first edit"] += fc is not None and (fe is None or fc < fe)
        TM[arm].append(g["agent_s"])
        print(f"{Path(d).name[-6:]} {arm:6} {task:14} {'SOLVED' if solved else 'failed'} {g['end']:4} {g['agent_s']:4.0f}s capped {cap} ({capsec:3.0f}s) {b:24} events {events}")
        print("        " + " ".join(calls))
print()
for arm in sorted(A):
    print(f"  {arm}: " + " | ".join(f"{k} {v}" for k, v in A[arm].items()) + f" | mean agent s {st.mean(TM[arm]):.0f}")
