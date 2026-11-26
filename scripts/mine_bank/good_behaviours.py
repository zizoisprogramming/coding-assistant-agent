"""Which step-level behaviours go with SUCCESS on the same task, for the same agent? (user 2026-11-26: 'these only are the
ones that are good? are there any more else contributing to good behaviour?'). Every logged run in the bank; per run:
  quick_after_warning  the first banner / budget warning (no edit yet) is followed by an applied source edit within 3 calls
  obey_budget          the first 'tool call(s) remaining' warning (no edit yet) is followed by an edit or submit_patch next
  early_edit           the first applied source edit comes within the first 12 calls
  repro_before_edit    a script / python run (not a.py, not pytest) before the first applied edit
  check_after_edit     a test or script run after the LAST applied source edit
  pytest_any           a targeted pytest run at some point
  diff_before_submit   git diff / git status before the first submit_patch
  multi_edit_sites     applied edits in 2+ different places (files or distinct old texts)
  maxed_thinking       a reply whose thinking is >= 12,000 characters (~ the 4,096-token thinking cap)
  long_run_no_edit_25  25+ calls without any applied source edit
Comparison: within (agent, task) cells holding both solved and failed runs, the share of solved vs failed runs showing the
behaviour; sign test over cells (failed-more vs solved-more). Correlation, not proof (e.g. a check after the edit needs an
edit; quick edits happen on tasks where the fix is found).
Run: data/venv_train/bin/python -I scripts/mine_bank/good_behaviours.py"""
import ast, collections, glob, json, re, sys
from math import comb
sys.path.insert(0, "scripts/train")
from selfdistill_episodes import failed
ARM = sys.argv[1] if len(sys.argv) > 1 else None  # one agent only (e.g. sk_a2)
EDIT_RUN = re.compile(r"sed\s+-i|git\s+apply|patch\s+-p|OLD_TEXT|\.replace\(|old_string")
SRC_SKIP = re.compile(r"(^|/)(\.git/|tmp/|tests?/|test_[^/]*\.py$|conftest\.py$)|repro|check|debug|scratch")
def parse(x):
    if isinstance(x, dict): return x
    try: return ast.literal_eval(str(x))
    except Exception:
        try: return json.loads(str(x))
        except Exception: return {}
def is_edit(n, a):
    p, cmd = str(a.get("filepath", a.get("path", ""))), str(a.get("command", ""))
    if n in ("edit_file", "write_file"): return bool(p) and not SRC_SKIP.search(p) and not p.startswith("/tmp")
    return n == "run_command" and "a.py" not in cmd and bool(EDIT_RUN.search(cmd))
rows = []
for d in sorted(glob.glob("data/results/*")):
    try: G = {}; [G.__setitem__(json.loads(l)["instance_id"] + "#a" + str(json.loads(l)["attempt"]), json.loads(l)) for l in open(f"{d}/results/gen_per_task.jsonl")]
    except (OSError, ValueError, KeyError): continue
    G = {k: g for k, g in G.items() if g.get("resolved") is not None and g.get("end") in ("ok", "time", "tool_budget", "turns", "no_submit")}
    by = collections.defaultdict(list)
    try:
        with open(f"{d}/requests/requests.jsonl", errors="replace") as fh:
            for l in fh:
                try: r = json.loads(l)
                except ValueError: continue
                if r.get("job") in G: by[r["job"]].append(r)
    except OSError: continue
    for job, rs in by.items():
        g = G[job]; rs.sort(key=lambda r: float(r["t"]))
        res = {m.get("tool_call_id"): str(m.get("content")) for r in rs for m in r["request"]["messages"] if m.get("role") == "tool"}
        calls, maxed = [], False
        for r in rs:
            m = (parse(r.get("reply")) or {}).get("message") or {}
            if len(m.get("reasoning_content") or "") >= 12000: maxed = True
            for c in m.get("tool_calls") or []:
                fn = c.get("function") or {}
                try: a = json.loads(fn.get("arguments") or "{}")
                except Exception: a = {}
                a = a if isinstance(a, dict) else {}
                o = res.get(c.get("id"), "")
                try: od = json.loads(o)
                except Exception: od = {"raw": o}
                bad = failed(fn.get("name"), a, od if isinstance(od, dict) else {"raw": o})
                calls.append((fn.get("name"), a, o, bad))
        if not calls: continue
        ed = [i for i, (n, a, o, b) in enumerate(calls) if is_edit(n, a) and not b]
        first_edit, last_edit = (ed[0], ed[-1]) if ed else (None, None)
        cmd = lambda i: str(calls[i][1].get("command", ""))
        runs_code = lambda i: calls[i][0] == "run_command" and "a.py" not in cmd(i) and bool(re.search(r"\bpython3?\b|\bpytest\b", cmd(i))) and not EDIT_RUN.search(cmd(i))
        warn = next((i for i, (n, a, o, b) in enumerate(calls) if re.search(r"NO EDIT YET|STOP READING|ALREADY SHOWN|tool call\(s\) remaining", o) and (first_edit is None or i < first_edit)), None)
        bud = next((i for i, (n, a, o, b) in enumerate(calls) if "tool call(s) remaining" in o and (first_edit is None or i < first_edit)), None)
        sub = next((i for i, c in enumerate(calls) if c[0] == "submit_patch"), len(calls))
        sites = {(str(calls[i][1].get("filepath", "")), str(calls[i][1].get("old_string", cmd(i)))[:60]) for i in ed}
        f = {"quick_after_warning": warn is not None and first_edit is not None and 0 < first_edit - warn <= 3,
             "obey_budget": bud is not None and bud + 1 < len(calls) and (is_edit(*calls[bud + 1][:2]) or calls[bud + 1][0] == "submit_patch"),
             "early_edit": first_edit is not None and first_edit < 12,
             "repro_before_edit": any(runs_code(i) and "pytest" not in cmd(i) for i in range(first_edit if first_edit is not None else len(calls))),
             "check_after_edit": last_edit is not None and any(runs_code(i) for i in range(last_edit + 1, len(calls))),
             "pytest_any": any("pytest" in cmd(i) for i in range(len(calls))),
             "diff_before_submit": any(re.search(r"git\s+(diff|status)", cmd(i)) for i in range(sub)),
             "multi_edit_sites": len(sites) >= 2,
             "maxed_thinking": maxed,
             "long_run_no_edit_25": (first_edit if first_edit is not None else len(calls)) >= 25}
        # 'warning' features only count for runs that saw a warning before any edit
        f["_saw_warning"], f["_saw_budget"] = warn is not None, bud is not None
        f["_edited"] = first_edit is not None
        if ARM and g["arm"] != ARM: continue
        rows.append(dict(cell=(g["arm"], g["instance_id"]), ok=g["resolved"] in (True, "True"), f=f))
def sign_p(w, l):
    n = w + l
    return 1.0 if n == 0 else min(1, 2 * sum(comb(n, k) for k in range(max(w, l), n + 1)) / 2 ** n)
cells = collections.defaultdict(list)
for r in rows: cells[r["cell"]].append(r)
both = {c: v for c, v in cells.items() if any(r["ok"] for r in v) and not all(r["ok"] for r in v)}
print(f"{len(rows)} runs; {len(both)} (agent, task) cells with both outcomes ({sum(len(v) for v in both.values())} runs)")
print(f"{'behaviour':22} {'solved':>7} {'failed':>7} | cells solved-more / failed-more | p      (warning features: only runs that saw the warning)")
out = []
for k in ["quick_after_warning", "obey_budget", "early_edit", "repro_before_edit", "check_after_edit", "pytest_any", "diff_before_submit", "multi_edit_sites", "maxed_thinking", "long_run_no_edit_25"]:
    need = "_saw_warning" if k == "quick_after_warning" else "_saw_budget" if k == "obey_budget" else None
    S = F = 0; ns = nf = 0; up = dn = 0
    for v in both.values():
        vs = [r for r in v if r["ok"] and (need is None or r["f"][need])]; vf = [r for r in v if not r["ok"] and (need is None or r["f"][need])]
        S += sum(r["f"][k] for r in vs); ns += len(vs); F += sum(r["f"][k] for r in vf); nf += len(vf)
        if vs and vf:
            a, b = sum(r["f"][k] for r in vs) / len(vs), sum(r["f"][k] for r in vf) / len(vf)
            up += a > b; dn += b > a
    out.append((k, S / max(ns, 1), F / max(nf, 1), up, dn, sign_p(up, dn)))
    print(f"{k:22} {S / max(ns, 1):7.0%} {F / max(nf, 1):7.0%} | {up:4} / {dn:4} | {sign_p(up, dn):.4f}")
json.dump(out, open("data/analysis/good_behaviours.json", "w"))
print("\nonly runs that made an applied source edit (the after-edit behaviours need an edit to exist):")
for k in ["check_after_edit", "pytest_any", "diff_before_submit", "multi_edit_sites", "repro_before_edit", "maxed_thinking", "early_edit"]:
    S = F = ns = nf = up = dn = 0
    for v in both.values():
        vs = [r for r in v if r["ok"] and r["f"]["_edited"]]; vf = [r for r in v if not r["ok"] and r["f"]["_edited"]]
        S += sum(r["f"][k] for r in vs); ns += len(vs); F += sum(r["f"][k] for r in vf); nf += len(vf)
        if vs and vf:
            a, b = sum(r["f"][k] for r in vs) / len(vs), sum(r["f"][k] for r in vf) / len(vf)
            up += a > b; dn += b > a
    print(f"{k:22} {S / max(ns, 1):7.0%} {F / max(nf, 1):7.0%} | {up:4} / {dn:4} | {sign_p(up, dn):.4f}   (edited: solved {ns}, failed {nf})")
