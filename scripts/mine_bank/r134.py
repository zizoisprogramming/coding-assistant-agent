"""r134: sb1hl vs sb1hlc (36 calls + the harness 'Finalize your edits' note as an event) on the 8 solvable dev16 in two shards
(docs/PLAN.md RUN BUILT r134, bars there). Run: python3 -I scripts/mine_bank/r134.py
Per run: outcome, end, calls, agent s, first applied edit (time, call index), the call index of the first harness note, what the run did in
the 3 calls after the note (edit attempt / read / search / submit), empty submit (submit_patch with no source change), final reply."""
import ast, collections, glob, json, re, statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
T = {json.loads(l)["instance_id"]: json.loads(l) for l in open(ROOT / "data/tasks.jsonl")}
A = collections.defaultdict(lambda: collections.Counter()); TIMES = collections.defaultdict(list)
def kind(n, a):
    c = a.get("command", "") if n == "run_command" else ""
    return "EDIT" if "OLD_TEXT" in c else {"read_file": "R", "submit_patch": "P"}.get(n, "s")
for d in sorted(glob.glob(str(ROOT / "data/results/2026-11-21_skill_r134_s*"))):
    G = {json.loads(l)["instance_id"] + " " + json.loads(l)["arm"]: json.loads(l) for l in open(f"{d}/results/gen_per_task.jsonl")}
    by = collections.defaultdict(list)
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        r = json.loads(l)
        if len(r["request"]["messages"]) > 1:
            by[r["job"].split("#")[0] + " " + r["job"].split("#a")[1].split(".")[0]].append(r)
    for k in sorted(G, key=lambda x: (x.split()[1], x)):
        iid, arm = k.split(); g = G[k]; rs = sorted(by[k], key=lambda r: float(r["t"])); t0 = float(rs[0]["t"])
        calls = []; first_edit = None; note_at = None; last = ""
        for r in rs:
            out = str(r["request"]["messages"][-1].get("content")).replace("\\n", "\n")
            if note_at is None and "Finalize your edits" in out: note_at = len(calls)
            if first_edit is None and re.search(r"(?m)^EDITED ", out): first_edit = (float(r["t"]) - t0, len(calls))
            m = ast.literal_eval(str(r["reply"])).get("message") or {}
            if not m.get("tool_calls"): last = (m.get("content") or "")[:80]
            for c in m.get("tool_calls") or []:
                try: a = json.loads(c["function"]["arguments"])
                except Exception: a = {}
                calls.append(kind(c["function"]["name"], a))
        pf = list(Path(d).glob(f"results/gen/patches/{iid}__a{arm}.*.diff"))
        files = re.findall(r"^\+\+\+ b/(\S+)", pf[0].read_text(errors="replace"), re.M) if pf else []
        src = [f for f in files if f.endswith(".py") and "test" not in f and "repro" not in f]
        solved = g.get("resolved") in (True, "True"); sub = "P" in calls
        after = "".join(calls[note_at:note_at + 3]) if note_at is not None else "-"
        c = A[arm]; c["runs"] += 1; c["solved"] += solved; c["never edited"] += first_edit is None and not src
        c["empty submit"] += sub and not src; c["time ends"] += g.get("end") == "time"
        c["note seen"] += note_at is not None; c["note seen, unedited at the note"] += note_at is not None and (first_edit is None or first_edit[1] > note_at)
        c["edit within 3 calls after the note (unedited runs)"] += note_at is not None and (first_edit is None or first_edit[1] > note_at) and "EDIT" in calls[note_at:note_at + 3]
        TIMES[arm].append(float(g.get("agent_s") or 0))
        print(f"{Path(d).name[-2:]} {arm:6} {iid:14} {'SOLVED' if solved else 'failed'} end {g.get('end'):5} calls {g.get('tool_calls'):>2} agent {float(g.get('agent_s', 0)):3.0f}s "
              f"first edit {('%.0f s @call %d' % first_edit) if first_edit else 'never':16} note @call {note_at if note_at is not None else '-':>3} next {after:6} src {src} | {last!r}")
print()
for arm in ("sb1hl", "sb1hlc"):
    print(f"  {arm}: " + " | ".join(f"{k} {v}" for k, v in A[arm].items()) + f" | mean agent s {st.mean(TIMES[arm]):.0f}")
