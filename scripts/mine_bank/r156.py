"""r156: sk_a2 (control) vs sk_a2o2n (sk_a2 + YOUR EDIT / SAME LINES ELSEWHERE) on 4 tasks x 2 accounts; same counts as r155.py plus pre-edit scripts.
r155 doc: sk_a2 (control) vs sk_a2c2 (heredoc a.py check, before/after-edit verdicts) vs sk_a2o (YOUR EDIT / SAME LINES ELSEWHERE,
EDIT MATERIAL at STOP READING) on 6 tasks x 2 accounts (bars in docs/PLAN.md RUN BUILT r155).
Per run: outcome, time, first source edit (call, second), python runs via a.py check vs other, verdicts and the call after each,
YOUR EDIT / EDIT MATERIAL seen and the call after EDIT MATERIAL. Run: python3 -I scripts/mine_bank/r155.py"""
import ast, collections, glob, json, re, statistics as st
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SRC = re.compile(r"(repro|check|debug|scratch|\.git/agent|/tmp/|test)")
VERD = re.compile(r">>> (GREEN|RED again|RED|BUG SHOWN|YOUR CHECK PASSES BEFORE ANY EDIT|NO CHECK CODE)")


def parse(x):
    if isinstance(x, dict): return x
    try: return ast.literal_eval(str(x))
    except Exception:
        try: return json.loads(str(x))
        except Exception: return {}


rows = []
for d in sorted(glob.glob(str(ROOT / "data/results/2026-11-24_skill_r156_s*"))):
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
        seq, fe, fe_s, verdicts, after, pending = [], None, None, [], [], None
        pyc, pyo, your_edit, material, last_own, pre = 0, 0, 0, 0, None, 0
        for r in rs:
            for c in ((parse(r.get("reply")) or {}).get("message") or {}).get("tool_calls") or []:
                fn = c.get("function") or {}; a = fn.get("arguments") or ""; out = res.get(c.get("id"), "")
                try: ad = json.loads(a)
                except Exception: ad = {}
                if not isinstance(ad, dict): ad = {}
                n = fn.get("name"); cmd = str(ad.get("command", ""))
                if "YOUR EDIT:" in out: your_edit += 1
                mat = "EDIT MATERIAL:" in out
                if n == "edit_file" and not SRC.search(str(ad.get("filepath", ""))) or ("OLD_TEXT" in cmd or ".replace(" in cmd) and "a.py" not in cmd:
                    k = "EDIT" if '"status": "error"' not in out and "BudgetExceeded" not in out else "EDIT-fail"
                elif "a.py check" in cmd:
                    pyc += 1
                    v = VERD.search(out); k = "check[" + (v.group(1)[:12] if v else "?") + "]"
                    if v: verdicts.append(v.group(1)); last_own = v.group(1) if fe is not None else last_own
                elif "a.py" in cmd: k = cmd.split("a.py", 1)[1].split()[0]
                elif "pytest" in cmd or "python" in cmd:
                    k = "pytest" if "pytest" in cmd else "RUN"
                    if k == "RUN": pyo += 1
                    if fe is None: pre += 1
                    if fe is not None: last_own = "red-run" if re.search(r"Traceback|Error|failed|\"exit_code\": [1-9]", out) else "green-run"
                else: k = n if n != "run_command" else "shell"
                if pending is not None: after.append((pending, k)); pending = None
                if k.startswith("check[RED") and k != "check[RED again]": pending = "RED"
                elif k.startswith("check[BUG"): pending = "BUG"
                elif k.startswith("check[YOUR"): pending = "PASSPRE"
                elif mat: pending = "MATERIAL"; material += 1
                if k == "EDIT" and fe is None: fe, fe_s = len(seq), float(r["t"]) - t0
                seq.append(k + ("+MAT" if mat else ""))
        rows.append(dict(s=Path(d).name[-2:], arm=g["arm"], task=g["instance_id"], ok=g.get("resolved") in (True, "True"), end=g["end"],
                         agent=float(g["agent_s"]), patch=int(g.get("patch_chars") or 0), fe=fe, fe_s=fe_s, verdicts=verdicts,
                         after=after, last_own=last_own, seq=seq, pyc=pyc, pyo=pyo, your_edit=your_edit, material=material, pre=pre))
for r in sorted(rows, key=lambda r: (r["arm"], r["task"], r["s"])):
    print(f"{r['arm']:8}{r['task']:14}{r['s']} {'SOLVED' if r['ok'] else 'failed'} {r['end']:4} {r['agent']:3.0f}s patch {r['patch']:4} first edit {r['fe']} "
          f"({'-' if r['fe_s'] is None else round(r['fe_s'])}s) py via check {r['pyc']} other {r['pyo']} | verdicts {r['verdicts']} | after {r['after']} | YOUR EDIT seen {r['your_edit']} MATERIAL {r['material']}")
    print("      " + " ".join(r["seq"]))
print()
for arm in ("sk_a2", "sk_a2o2n"):
    R = [r for r in rows if r["arm"] == arm]; E = [r for r in R if r["fe"] is not None]
    W = [r for r in R if r["patch"] > 0 and not r["ok"]]
    aft = collections.defaultdict(list)
    for r in R:
        for p, k in r["after"]: aft[p].append(k)
    print(f"{arm:8} solved {sum(r['ok'] for r in R)}/{len(R)} | time ends {sum(r['end'] == 'time' for r in R)} | no patch {sum(r['patch'] == 0 for r in R)} | mean agent {st.mean(r['agent'] for r in R):.0f}s"
          f" | edited {len(E)} | median first edit {round(st.median([r['fe_s'] for r in E])) if E else '-'}s | pre-edit scripts {sum(r['pre'] for r in R)} | py runs via check {sum(r['pyc'] for r in R)} other {sum(r['pyo'] for r in R)}"
          f" | YOUR EDIT seen in edited runs {sum(r['your_edit'] > 0 for r in E)}/{len(E)} | after: " + "; ".join(f"{p} -> {collections.Counter(v)}" for p, v in aft.items())
          + f" | wrong kept edits {len(W)} last own {collections.Counter(r['last_own'] for r in W)}")
# pre-edit script work incl. write_file / pytest (whole run when no edit), and seconds per call (thinking)
for arm in ("sk_a2", "sk_a2o2n"):
    R = [r for r in rows if r["arm"] == arm]
    pre = [sum(k in ("RUN", "write_file", "pytest") for k in (r["seq"][:r["fe"]] if r["fe"] is not None else r["seq"])) for r in R]
    print(f"{arm:8} pre-edit RUN+write_file+pytest {sum(pre)} per run {pre} | calls per run {[len(r['seq']) for r in R]} | s per call {st.mean(r['agent'] / max(1, len(r['seq'])) for r in R):.1f}")
