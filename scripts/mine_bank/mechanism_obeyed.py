"""Which scaffold mechanisms WORK WHEN OBEYED but lost because the model often did not obey? (user 2026-11-25: 'search in
agent bank for agents that have its solves come from its way like stop or card or something but its problem was that the
model didn't obey this way'). For every logged arm: the FIRST instruction its tools print before any source edit (a.py
banners NO EDIT YET / STOP READING / ALREADY SHOWN, gate answers READING CLOSED / EDIT CANDIDATE, HELD ONCE, CARD SET,
repro / check verdicts, EDIT MATERIAL, any 'your next call is ...' line; the harness's 'tool call(s) remaining' warning is
reported separately as 'budget'). Obeyed = the next call is a source edit (HELD ONCE: the card or an edit). Per arm and
mechanism: adoption (obeyed / events), solve rate obeyed vs not, and the SAME-TASK comparison (tasks with both kinds), so
task ease does not pass as effect. Run: python3 -I scripts/mine_bank/mechanism_obeyed.py [min_events]"""
import ast, collections, glob, json, re, sys
MIN = int(sys.argv[1]) if len(sys.argv) > 1 else 8
MECH = [("banner", re.compile(r"NO EDIT YET|STOP READING|ALREADY SHOWN")), ("held", re.compile(r"HELD ONCE")),
        ("card_set", re.compile(r"CARD SET")), ("gate", re.compile(r"READING CLOSED|EDIT CANDIDATE|This is code you read before")),
        ("repro", re.compile(r"REPRO (SHOWS|PASSES)|BUG SHOWN|SHOWS THE BUG|problem is shown")),
        ("material", re.compile(r"EDIT MATERIAL")), ("next_call", re.compile(r"(?i)your (very )?next call is|make (your|the) (best )?edit"))]
BUDGET = re.compile(r"tool call\(s\) remaining")
SRC = re.compile(r"(repro|check|debug|scratch|\.git/agent|/tmp/|(^|/)tests?/|test_)")
def parse(x):
    if isinstance(x, dict): return x
    try: return ast.literal_eval(str(x))
    except Exception:
        try: return json.loads(str(x))
        except Exception: return {}
def is_edit(n, a):
    cmd, path = str(a.get("command", "")), str(a.get("filepath", a.get("path", "")))
    if n in ("edit_file", "write_file"): return bool(path) and not SRC.search(path) and not path.endswith(".md")
    return n == "run_command" and "a.py" not in cmd and bool(re.search(r"sed\s+-i|git\s+apply|patch\s+-p|OLD_TEXT|\.replace\(|old_string", cmd))
def is_card(n, a): return n == "write_file" and "card" in str(a.get("filepath", ""))
rows = []
for d in sorted(glob.glob("data/results/*")):
    try: G = {}; [G.__setitem__(json.loads(l)["instance_id"] + "#a" + str(json.loads(l)["attempt"]), json.loads(l)) for l in open(f"{d}/results/gen_per_task.jsonl")]
    except (OSError, ValueError, KeyError): continue
    G = {k: g for k, g in G.items() if g.get("resolved") is not None}
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
        calls = []
        for r in rs:
            for c in ((parse(r.get("reply")) or {}).get("message") or {}).get("tool_calls") or []:
                fn = c.get("function") or {}
                try: a = json.loads(fn.get("arguments") or "{}")
                except Exception: a = {}
                calls.append((fn.get("name"), a if isinstance(a, dict) else {}, res.get(c.get("id"), "")))
        first = {}
        for i, (n, a, o) in enumerate(calls):
            if any(is_edit(*c[:2]) for c in calls[:i + 1]): break
            nxt = calls[i + 1] if i + 1 < len(calls) else (None, {}, "")
            for name, rx in MECH + [("budget", BUDGET)]:
                if name not in first and rx.search(o):
                    ok = is_edit(nxt[0], nxt[1]) or (name == "held" and is_card(nxt[0], nxt[1])) or (name == "budget" and nxt[0] == "submit_patch")
                    first[name] = ok
        rows.append(dict(arm=g["arm"], task=g["instance_id"], ok=g["resolved"] in (True, "True"), first=first))
out = []
for arm in sorted({r["arm"] for r in rows}):
    R = [r for r in rows if r["arm"] == arm]
    for name in [m for m, _ in MECH] + ["budget"]:
        E = [r for r in R if name in r["first"]]
        if len(E) < MIN: continue
        ob = [r for r in E if r["first"][name]]; no = [r for r in E if not r["first"][name]]
        T = collections.defaultdict(lambda: [[0, 0], [0, 0]])
        for r in E:
            k = 0 if r["first"][name] else 1
            T[r["task"]][k][0] += r["ok"]; T[r["task"]][k][1] += 1
        both = [v for v in T.values() if v[0][1] and v[1][1]]
        so = sum(v[0][0] for v in both); no_ = sum(v[0][1] for v in both); sn = sum(v[1][0] for v in both); nn = sum(v[1][1] for v in both)
        out.append(dict(arm=arm, mech=name, runs=len(R), events=len(E), obeyed=len(ob), s_ob=sum(r["ok"] for r in ob), s_no=sum(r["ok"] for r in no),
                        n_no=len(no), tasks_both=len(both), st_ob=(so, no_), st_no=(sn, nn),
                        up=sum(v[0][0] / v[0][1] > v[1][0] / v[1][1] for v in both), dn=sum(v[0][0] / v[0][1] < v[1][0] / v[1][1] for v in both)))
json.dump(out, open("data/analysis/mechanism_obeyed.json", "w"), indent=0)
print(f"{len(rows)} runs, {len({r['arm'] for r in rows})} arms; mechanism rows with >= {MIN} events: {len(out)}")
print(f"{'arm':20} {'mechanism':9} {'events':>6} {'obeyed':>10} {'solved|obeyed':>14} {'solved|not':>11} | same task: tasks, obeyed vs not, +/-")
for o in sorted(out, key=lambda o: -((o['s_ob'] / max(o['obeyed'], 1)) - (o['s_no'] / max(o['n_no'], 1))) * min(o['obeyed'], o['n_no'])):
    fo = lambda a, b: f"{a}/{b} {a / b:.0%}" if b else "-"
    print(f"{o['arm'][:20]:20} {o['mech']:9} {o['events']:6} {fo(o['obeyed'], o['events']):>10} {fo(o['s_ob'], o['obeyed']):>14} {fo(o['s_no'], o['n_no']):>11} | "
          f"{o['tasks_both']:3} tasks, {fo(*o['st_ob'])} vs {fo(*o['st_no'])}, {o['up']}+/{o['dn']}-")
