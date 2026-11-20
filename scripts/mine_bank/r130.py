"""r130: sb1 vs sb1hl vs sbE5f vs sbE5w on fastapi_15589 + fastapi_11194, 2 passes (docs/PLAN.md RUN BUILT r130, bars there).
Run: python3 -I scripts/mine_bank/r130.py
Per run: outcome, end, agent s, compactions, text-form replies (and what they hold), expectation attempts (heredoc / write_file) and how many
were real calls, the check events, write_file targets, the hold-back, first applied edit time, and the call sequence."""
import ast, collections, glob, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TXT = re.compile(r"<\|tool_call>|call:\w+\{|```python\n(mkdir|cat|from|import)")
EV = [("shown", "the problem is shown"), ("NOT-ISSUE", "PASSES before any edit"), ("BROKEN", "SCRIPT BROKEN"), ("HELD", "EDIT HELD BACK"),
      ("still", "STILL FAILS with your edit"), ("DONE", "PASSES with your edit"), ("LATE", "NOTHING EDITED YET"), ("f0", "old text found 0 times"),
      ("halved", "double backslashes in your text"), ("nofile", "check.sh: No such file")]
A = collections.defaultdict(lambda: collections.Counter())
for d in sorted(glob.glob(str(ROOT / "data/results/2026-11-20_skill_r130_p*"))):
    G = {json.loads(l)["instance_id"] + " " + json.loads(l)["arm"]: json.loads(l) for l in open(f"{d}/results/gen_per_task.jsonl")}
    by = collections.defaultdict(list); comp = collections.Counter()
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        r = json.loads(l)
        k = r["job"].split("#")[0] + " " + r["job"].split("#a")[1].split(".")[0]
        if len(r["request"]["messages"]) == 1:
            comp[k] += 1
        else:
            by[k].append(r)
    for k, rs in sorted(by.items(), key=lambda x: (x[0].split()[1], x[0])):
        iid, arm = k.split()
        rs.sort(key=lambda r: float(r["t"])); t0 = float(rs[0]["t"]); g = G.get(k, {})
        seq, c = [], A[arm]
        first_edit = None
        for r in rs:
            last = r["request"]["messages"][-1]
            if last.get("role") == "tool" and seq:
                out = str(last.get("content")).replace("\\n", "\n")
                hits = [n for n, p in EV if p in out]
                if hits:
                    seq[-1] += "[" + ",".join(hits) + "]"
                    for h in hits: c["event " + h] += 1
                if first_edit is None and re.search(r"(?m)^EDITED (?!\.git)", out):
                    first_edit = float(r["t"]) - t0
            m = ast.literal_eval(str(r["reply"])).get("message") or {}
            t = float(r["t"]) - t0
            content = m.get("content") or ""
            if not m.get("tool_calls") and TXT.search(content):
                isexp = "expect.py" in content
                seq.append(f"TEXT{'(expect)' if isexp else ''}@{t:.0f}")
                c["text replies"] += 1; c["text replies holding the expectation"] += isexp
                if isexp: c["expectation attempts"] += 1
            for cl in m.get("tool_calls") or []:
                n = cl["function"]["name"]
                try:
                    a = json.loads(cl["function"]["arguments"])
                except Exception:
                    a = {}
                cmd = a.get("command", "")
                if n == "write_file":
                    fp = a.get("filepath", "")
                    c["write_file calls"] += 1; c["write_file to " + ("expect.py" if fp.endswith(".git/agent/expect.py") else "OTHER: " + fp)] += 1
                    if fp.endswith("expect.py"): c["expectation attempts"] += 1; c["expectation real calls"] += 1
                    seq.append(f"WF({Path(fp).name})@{t:.0f}")
                elif n == "run_command" and "<<'EXPECT'" in cmd:
                    c["expectation attempts"] += 1; c["expectation real calls"] += 1; seq.append(f"X@{t:.0f}")
                elif n == "run_command" and "check.sh <<'EOF'" in cmd and "<<'EXPECT'" not in cmd:
                    seq.append(f"CHK@{t:.0f}")
                elif n == "run_command" and "OLD_TEXT" in cmd:
                    seq.append(f"E@{t:.0f}")
                elif n == "edit_file":
                    seq.append(f"EF@{t:.0f}")
                    if first_edit is None: first_edit = t
                else:
                    seq.append({"read_file": "R", "submit_patch": "P", "run_command": "s"}.get(n, n[:3]) + f"@{t:.0f}")
        c["runs"] += 1; c["solved"] += g.get("resolved") in (True, "True"); c["never edited"] += first_edit is None
        print(f"{Path(d).name[-2:]} {arm:6} {iid:14} {'SOLVED' if g.get('resolved') in (True, 'True') else 'failed'} end {g.get('end'):5} agent {float(g.get('agent_s', 0)):3.0f}s comp {comp[k]} "
              f"first edit {('%.0f s' % first_edit) if first_edit is not None else 'never'}\n    " + " ".join(seq))
print("\n#### per arm")
for arm in ("sb1", "sb1hl", "sbE5f", "sbE5w"):
    c = A[arm]
    print(f"  {arm}: " + " | ".join(f"{k} {v}" for k, v in sorted(c.items())))
