"""r127: sbE1 vs sbE2 vs sbX1 (expectation arms) on fastapi_15589 + rich_3278, 2 passes (docs/PLAN.md RUN BUILT r127, bars there).
Run: python3 -I scripts/mine_bank/r127.py
Per run: outcome, end, agent s, compactions; expectation commands sent (and when); the checker's events seen (shown / passes before
edit / broken / still fails / passes with your edit / late); first edit time and whether an edit followed 'shown' within 3 calls;
for sbX1: the expectation agent's time, calls, its final note. Then every run's expect.py versions and the hidden test's asserted
lines, printed for hand reading (failure patterns)."""
import ast, collections, glob, json, re, statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIRS = sorted(glob.glob(str(ROOT / "data/results/2026-11-20_skill_r127_p*")))
T = {json.loads(l)["instance_id"]: json.loads(l) for l in open(ROOT / "data/tasks.jsonl")}
EVK = [("shown", "the problem is shown"), ("nothing", "PASSES before any edit"), ("broken", "SCRIPT ITSELF IS BROKEN"),
       ("still", "STILL FAILS with your edit"), ("done", "PASSES with your edit"), ("late", "Nothing is edited yet")]
EXP = re.compile(r"cat > \.git/agent/expect\.py <<'EXPECT'\n(.*?)EXPECT\n", re.S)
G = {}
for d in DIRS:
    for l in open(f"{d}/results/gen_per_task.jsonl"):
        g = json.loads(l)
        G[(Path(d).name[-2:], g["instance_id"], g["arm"])] = g
runs = collections.defaultdict(list)
comp = collections.Counter()
for d in DIRS:
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        r = json.loads(l)
        key = (Path(d).name[-2:], r["job"].split("#")[0], r["job"].split("#a")[1].split(".")[0])
        if len(r["request"]["messages"]) == 1:
            comp[key] += 1
            continue
        runs[key].append(r)
rows = []
for key, rs in sorted(runs.items()):
    p, iid, arm = key
    rs.sort(key=lambda r: float(r["t"]))
    t0 = float(rs[0]["t"])
    calls = []  # (t, agent, kind, text)
    events = []  # (call index, kind)
    stage_end = None
    note = ""
    for i, r in enumerate(rs):
        sysm = r["request"]["messages"][0]["content"]
        agent = "expect" if sysm.startswith("You write the expectation") else "main"
        try:
            m = ast.literal_eval(str(r["reply"])).get("message") or {}
        except Exception:
            m = {}
        if agent == "expect" and not m.get("tool_calls"):
            stage_end = float(r["t"]) + float(r.get("seconds") or 0) - t0
            note = (m.get("content") or "").strip()
        for c in m.get("tool_calls") or []:
            try:
                a = json.loads(c["function"]["arguments"])
            except Exception:
                a = {}
            cmd = a.get("command", "") if c["function"]["name"] == "run_command" else ""
            kind = "expect" if EXP.search(cmd) else "edit" if "OLD_TEXT" in cmd else "rerun" if cmd.strip() == "bash .git/agent/check.sh" else c["function"]["name"]
            calls.append((float(r["t"]) - t0, agent, kind, EXP.search(cmd).group(1) if kind == "expect" else ""))
        last = r["request"]["messages"][-1]
        if last.get("role") == "tool":
            out = str(last.get("content")).replace("\\n", "\n")
            for k, pat in EVK:
                if pat in out:
                    events.append((len(calls), k))
    g = G.get(key, {})
    ex = [c for c in calls if c[2] == "expect"]
    ed = [i for i, c in enumerate(calls) if c[2] == "edit"]
    shown_i = next((i for i, k in events if k == "shown"), None)
    rows.append(dict(p=p, iid=iid, arm=arm, solved=g.get("resolved") in (True, "True"), end=g.get("end"), agent_s=g.get("agent_s", 0), comp=comp[key],
                     n_exp=len(ex), first_exp=ex[0][0] if ex else None, exps=[c[3] for c in ex], ev=[k for _, k in events],
                     first_edit=calls[ed[0]][0] if ed else None, edit_after_shown=shown_i is not None and any(0 <= i - shown_i + 1 <= 3 for i in ed),
                     shown_before_edit=shown_i is not None and (not ed or shown_i <= ed[0] + 1), stage_end=stage_end, note=note,
                     stage_calls=sum(c[1] == "expect" for c in calls), n_calls=len(calls)))
print("#### per run")
for r in rows:
    print(f"  {r['p']} {r['arm']:5} {r['iid'][:14]:14} {'S' if r['solved'] else '-'} end {r['end']:5} agent {r['agent_s']:4.0f}s comp {r['comp']} | expectations {r['n_exp']}"
          f" (first {('%.0f s' % r['first_exp']) if r['first_exp'] is not None else '-'}) | events {r['ev']} | first edit {('%.0f s' % r['first_edit']) if r['first_edit'] is not None else 'never'}"
          + (f" | stage {r['stage_end']:.0f}s / {r['stage_calls']} calls" if r["arm"] == "sbX1" and r["stage_end"] else (" | stage never ended" if r["arm"] == "sbX1" else "")))
print("\n#### bars per arm")
for a in ("sbE1", "sbE2", "sbX1"):
    X = [r for r in rows if r["arm"] == a]
    n = len(X)
    print(f"  {a}: runs {n} | solved {sum(r['solved'] for r in X)} | expectation written {sum(r['n_exp'] > 0 for r in X)}/{n}"
          f" | shown before the first edit {sum(r['shown_before_edit'] for r in X)}/{n} | edit within 3 calls of 'shown' {sum(r['edit_after_shown'] for r in X)}/{sum('shown' in r['ev'] for r in X)}"
          f" | 'passes with your edit' {sum('done' in r['ev'] for r in X)}/{n} | never edited {sum(r['first_edit'] is None for r in X)}/{n}"
          f" | time ends {sum(r['end'] == 'time' for r in X)}/{n} | agent s mean {st.mean(r['agent_s'] for r in X):.0f} | compactions {sum(r['comp'] for r in X) / n:.1f}/run"
          + (f" | stage median {st.median([r['stage_end'] for r in X if r['stage_end']] or [0]):.0f} s, ended {sum(bool(r['stage_end']) for r in X)}/{n}" if a == "sbX1" else "")
          + (f" | late line {sum('late' in r['ev'] for r in X)}" if a == "sbE2" else ""))
print("\n#### hand reading: expectations vs the hidden test")
for iid in sorted({r["iid"] for r in rows}):
    tl = [l[1:] for l in T[iid]["test_patch"].splitlines() if l.startswith("+") and not l.startswith("+++") and re.search(r"assert|raises|==", l)]
    print(f"\n======== {iid} | hidden test asserts:\n" + "\n".join("    " + l.strip()[:160] for l in tl[:12]))
    for r in [r for r in rows if r["iid"] == iid]:
        print(f"\n  -- {r['p']} {r['arm']} {'SOLVED' if r['solved'] else 'failed'} | events {r['ev']}")
        if r["note"]:
            print("     NOTE: " + r["note"][:500].replace("\n", " / "))
        for k, e in enumerate(r["exps"][:3]):
            print(f"     expect.py #{k + 1}:\n" + "\n".join("        " + l for l in e.splitlines()[:18]))
json.dump(rows, open(ROOT / "data/analysis/r127_rows.json", "w"))
