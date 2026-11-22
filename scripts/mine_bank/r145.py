"""r145: sk_a2_60x (control) vs sk_a2_60x2 (+ Example 3: STOP READING / remaining-calls -> edit now; Example 4: repair forward, never undo)
on 4 mid-rate dev16 x 2 accounts (bars in docs/PLAN.md RUN BUILT r145). Per run: outcome, time, calls, first edit call, warning moments
(a.py STOP READING or 'Only N tool call(s) remaining' while no source edit exists) and what the next call was, edits refused by the
budget, failed edit applications, undone edits (edit applied, patch empty), compactions. Run: python3 -I scripts/mine_bank/r145.py"""
import ast, collections, glob, json, re, statistics as st, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SRC = re.compile(r"(repro|check|debug|scratch|\.git/agent|/tmp/|test)")


def parse(x):
    if isinstance(x, dict): return x
    try: return ast.literal_eval(str(x))
    except Exception:
        try: return json.loads(str(x))
        except Exception: return {}


def is_edit(n, a):
    c = str(a.get("command", ""))
    if n == "edit_file": return not SRC.search(str(a.get("filepath", "")))
    return ("OLD_TEXT" in c or ".replace(" in c or "sed -i" in c) and "a.py" not in c and "repro" not in c


def short(n, a):
    c = str(a.get("command", ""))
    if is_edit(n, a): return "EDIT"
    if n != "run_command": return n.replace("run_skill_script", "install")[:8]
    if "a.py" in c: return c.split("a.py", 1)[1].split()[0]
    if "pytest" in c: return "pytest"
    if "python" in c: return "RUN"
    return "shell"


rows = []
for d in sorted(glob.glob(str(ROOT / "data/results/2026-11-23_skill_r145_s*"))):
    G = {}
    for l in open(f"{d}/results/gen_per_task.jsonl"):
        g = json.loads(l); G[g["instance_id"] + "#a" + g["attempt"]] = g
    by = collections.defaultdict(list)
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        r = json.loads(l); by[r["job"]].append(r)
    for job, rs in by.items():
        g = G.get(job)
        if not g: continue
        allr = sorted(rs, key=lambda r: float(r["t"]))
        rs = [r for r in allr if len(r["request"]["messages"]) > 1]
        res = {}
        for r in rs:
            for m in r["request"]["messages"]:
                if m.get("role") == "tool": res[m.get("tool_call_id")] = str(m.get("content"))
        seq, comp, last_p, edited = [], 0, 0, False
        moments, moment_next, refused, failed, applied = 0, [], 0, 0, 0
        pending = False
        for r in rs:
            rep = parse(r.get("reply")) or {}
            p = (rep.get("usage") or {}).get("prompt_tokens") or 0
            if last_p and p < 0.7 * last_p: comp += 1
            last_p = p
            for c in (rep.get("message") or {}).get("tool_calls") or []:
                fn = c.get("function") or {}
                try: a = json.loads(fn.get("arguments") or "{}")
                except Exception: a = {}
                if not isinstance(a, dict): a = {}
                k = short(fn.get("name"), a); out = res.get(c.get("id"), "")
                if pending:
                    moment_next.append(k); pending = False
                if k == "EDIT":
                    if "BudgetExceeded" in out: refused += 1
                    elif '"status": "error"' in out or "AssertionError" in out or "Traceback" in out: failed += 1
                    else: applied += 1; edited = True
                if not edited and ("STOP READING" in out or "tool call(s) remaining" in out) and "BudgetExceeded" not in out:
                    moments += 1; pending = True
                seq.append(k)
        rows.append(dict(s=Path(d).name[-2:], arm=g["arm"], task=g["instance_id"], ok=g.get("resolved") in (True, "True"), end=g.get("end"),
                         agent=float(g.get("agent_s") or 0), patch=int(g.get("patch_chars") or 0), seq=seq,
                         fe=next((i for i, k in enumerate(seq) if k == "EDIT"), None), comp=comp, summ=sum(len(r["request"]["messages"]) <= 1 for r in allr),
                         moments=moments, mnext=moment_next, refused=refused, failed=failed, applied=applied,
                         undone=applied > 0 and int(g.get("patch_chars") or 0) == 0))
for r in sorted(rows, key=lambda r: (r["arm"], r["task"], r["s"])):
    print(f"{r['arm']:11}{r['task']:14}{r['s']} {'SOLVED' if r['ok'] else 'failed':7}{r['end']:5}{r['agent']:4.0f}s patch {r['patch']:4} fe {str(r['fe']):4} "
          f"warn-moments {r['moments']} next {'/'.join(r['mnext'][:3]) or '-'} | refused {r['refused']} failed-apply {r['failed']} applied {r['applied']} undone {'Y' if r['undone'] else '-'} comp {r['comp']}")
    print("      " + " ".join(r["seq"]))
print()
for arm in sorted({r["arm"] for r in rows}):
    R = [r for r in rows if r["arm"] == arm]
    first_next = [r["mnext"][0] for r in R if r["mnext"]]
    print(f"{arm:11} solved {sum(r['ok'] for r in R)}/{len(R)} | patch>0 {sum(r['patch'] > 0 for r in R)} | mean agent {st.mean(r['agent'] for r in R):.0f}s | comp/run {st.mean(r['comp'] for r in R):.2f}"
          f" | runs with a warning moment {len(first_next)}: next call EDIT after the first {sum(k == 'EDIT' for k in first_next)}, after any {sum('EDIT' in r['mnext'] for r in R if r['mnext'])}"
          f" | refused {sum(r['refused'] for r in R)} | failed-apply {sum(r['failed'] for r in R)} | undone runs {sum(r['undone'] for r in R)} | mean first edit {st.mean(r['fe'] for r in R if r['fe'] is not None):.1f}")
print("\nper warning moment (every STOP READING / remaining-calls output before any source edit): share whose next call is an edit")
for arm in sorted({r["arm"] for r in rows}):
    R = [r for r in rows if r["arm"] == arm]
    allm = [k for r in R for k in r["mnext"]]
    stop_runs = [r for r in R if r["moments"]]
    print(f"  {arm:11} moments {len(allm)}, next = EDIT {sum(k == 'EDIT' for k in allm)} ({sum(k == 'EDIT' for k in allm) / max(1, len(allm)):.0%}); "
          f"reads after the first warning per run {st.mean(len(r['mnext']) for r in stop_runs):.1f}")
