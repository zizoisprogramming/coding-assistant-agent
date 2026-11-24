"""r154: sk_a2 (control) vs sk_a2c (post-edit check.py + a.py check GREEN / RED) on 6 tasks x 2 accounts (bars in docs/PLAN.md RUN BUILT r154).
Per run: outcome, time, first source edit (call, second), check.py written, a.py check verdicts and the call after each, the last own check
before the end (GREEN / RED / other run), patch. Run: python3 -I scripts/mine_bank/r154.py"""
import ast, collections, glob, json, re, statistics as st
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SRC = re.compile(r"(repro|check|debug|scratch|\.git/agent|/tmp/|test)")


def parse(x):
    if isinstance(x, dict): return x
    try: return ast.literal_eval(str(x))
    except Exception:
        try: return json.loads(str(x))
        except Exception: return {}


rows = []
for d in sorted(glob.glob(str(ROOT / "data/results/2026-11-2[45]_skill_r154_s*"))):
    G = {}
    for l in open(f"{d}/results/gen_per_task.jsonl"):
        g = json.loads(l); G[g["instance_id"] + "#a" + g["attempt"]] = g
    by = collections.defaultdict(list)
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        r = json.loads(l); by[r["job"]].append(r)
    for job, rs in by.items():
        g = G.get(job)
        if not g: continue
        rs = sorted([r for r in rs if len(r["request"]["messages"]) > 1], key=lambda r: float(r["t"])); t0 = float(rs[0]["t"]) if rs else 0
        res = {}
        for r in rs:
            for m in r["request"]["messages"]:
                if m.get("role") == "tool": res[m.get("tool_call_id")] = str(m.get("content"))
        seq, fe, fe_s, verdicts, after, wrote, pending, last_own = [], None, None, [], [], False, None, None
        for r in rs:
            for c in ((parse(r.get("reply")) or {}).get("message") or {}).get("tool_calls") or []:
                fn = c.get("function") or {}; a = fn.get("arguments") or ""; out = res.get(c.get("id"), "")
                try: ad = json.loads(a)
                except Exception: ad = {}
                if not isinstance(ad, dict): ad = {}
                n = fn.get("name"); cmd = str(ad.get("command", ""))
                if n == "edit_file" and not SRC.search(str(ad.get("filepath", ""))) or ("OLD_TEXT" in cmd or ".replace(" in cmd) and "a.py" not in cmd:
                    k = "EDIT" if '"status": "error"' not in out and "BudgetExceeded" not in out else "EDIT-fail"
                elif n == "write_file" and "check.py" in str(ad.get("filepath", "")): k = "write check.py"; wrote = True
                elif "a.py check" in cmd:
                    v = re.search(r">>> (GREEN|RED again|RED|NO EDIT YET|NO CHECK SCRIPT)", out); k = "check[" + (v.group(1) if v else "?") + "]"
                    if v: verdicts.append(v.group(1)); last_own = v.group(1)
                elif "a.py" in cmd: k = cmd.split("a.py", 1)[1].split()[0]
                elif "pytest" in cmd or "python" in cmd:
                    k = "pytest" if "pytest" in cmd else "RUN"
                    if fe is not None: last_own = "red-run" if re.search(r"Traceback|Error|failed|\"exit_code\": [1-9]", out) else "green-run"
                else: k = n if n != "run_command" else "shell"
                if pending is not None: after.append((pending, k)); pending = None
                if k.startswith("check[RED") and k != "check[RED again]": pending = "RED"
                if k == "EDIT" and fe is None: fe, fe_s = len(seq), float(r["t"]) - t0
                seq.append(k)
        rows.append(dict(s=Path(d).name[-2:], arm=g["arm"], task=g["instance_id"], ok=g.get("resolved") in (True, "True"), end=g["end"],
                         agent=float(g["agent_s"]), patch=int(g.get("patch_chars") or 0), fe=fe, fe_s=fe_s, wrote=wrote, verdicts=verdicts,
                         after=after, last_own=last_own, seq=seq))
for r in sorted(rows, key=lambda r: (r["arm"], r["task"], r["s"])):
    print(f"{r['arm']:7}{r['task']:14}{r['s']} {'SOLVED' if r['ok'] else 'failed'} {r['end']:4} {r['agent']:3.0f}s patch {r['patch']:4} first edit {r['fe']} "
          f"({'-' if r['fe_s'] is None else round(r['fe_s'])}s) verdicts {r['verdicts']} after-RED {r['after']} last own {r['last_own']}")
    print("      " + " ".join(r["seq"]))
print()
for arm in ("sk_a2", "sk_a2c"):
    R = [r for r in rows if r["arm"] == arm]; E = [r for r in R if r["fe"] is not None]
    W = [r for r in R if r["patch"] > 0 and not r["ok"]]
    print(f"{arm:7} solved {sum(r['ok'] for r in R)}/{len(R)} | time ends {sum(r['end'] == 'time' for r in R)} | no patch {sum(r['patch'] == 0 for r in R)} | mean agent {st.mean(r['agent'] for r in R):.0f}s"
          f" | edited {len(E)} | check.py + a.py check in edited runs {sum(r['wrote'] and bool(r['verdicts']) for r in E)}/{len(E)} | RED -> next call edit {sum(k == 'EDIT' for r in R for _, k in r['after'])}/{sum(len(r['after']) for r in R)}"
          f" | wrong kept edits {len(W)}: last own check {collections.Counter(r['last_own'] for r in W)} | median first edit {st.median([r['fe_s'] for r in E]) if E else '-'}s")
