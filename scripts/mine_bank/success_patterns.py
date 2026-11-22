"""Patterns of success in trajectories (user 2026-11-23: 'study the patterns of success, how agents trajectories, is there a pattern
followed in successful runs'; and 'things that are solved should always be solved, not bounce'). WITHIN-TASK comparison only: tasks with
both solved and failed runs of the same agent family; per feature, per task mean(solved) vs mean(failed), counted over tasks (sign test),
so task difficulty cannot explain a difference. Families: sk_a2 (all sk_a2* arms) and all agents. Features describe the run up to and at its
first source edit, plus what came after. Also: the first-8-call kind sequence of solved vs failed runs on the same tasks.
Run: python3 -I scripts/mine_bank/success_patterns.py"""
import ast, collections, glob, json, math, re, statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = re.compile(r"(repro|reproduce|check|debug|scratch|\.git/agent|/tmp/|test)")
GOLD = {}
for l in open(ROOT / "data/tasks.jsonl"):
    t = json.loads(l)
    GOLD[t["instance_id"]] = set(re.findall(r"^\+\+\+ b/(\S+)", t["patch"], re.M))


def parse(x):
    if isinstance(x, dict): return x
    try: return ast.literal_eval(str(x))
    except Exception:
        try: return json.loads(str(x))
        except Exception: return {}


def kind(n, a):
    c = str(a.get("command", "")) if isinstance(a, dict) else ""
    if n == "run_skill_script": return "install"
    if n == "edit_file":
        return "edit" if not SRC.search(str(a.get("filepath", ""))) else "scratch"
    if n == "write_file": return "write"
    if n in ("submit_patch", "get_status"): return n[:6]
    if n == "read_file": return "read"
    if ("OLD_TEXT" in c or ".replace(" in c or "sed -i" in c) and "a.py" not in c and "repro" not in c and "check.py" not in c: return "edit"
    if "a.py show" in c: return "show"
    if "a.py find" in c or re.search(r"(^|\s)(git grep|grep|rg)\b", c): return "find"
    if "a.py outline" in c: return "outline"
    if re.search(r"(^|\s)(cat|sed -n|head|tail|nl)\b", c): return "read"
    if "pytest" in c: return "pytest"
    if "python" in c: return "script"
    return "shell"


def paths_in(n, a):
    s = json.dumps(a)
    return set(re.findall(r"[\w./-]+\.py", s))


RUNS = []
for d in sorted(glob.glob(str(ROOT / "data/results/*/"))):
    rp, gp = Path(d) / "requests/requests.jsonl", Path(d) / "results/gen_per_task.jsonl"
    if not rp.exists() or not gp.exists(): continue
    G = {}
    for l in open(gp, errors="replace"):
        try: g = json.loads(l); G[g["instance_id"] + "#a" + g["attempt"]] = g
        except Exception: pass
    by = collections.defaultdict(list)
    for l in open(rp, errors="replace"):
        try: r = json.loads(l)
        except Exception: continue
        if "31b" not in str((r.get("request") or {}).get("model", "")).lower(): continue
        by[r.get("job", "")].append(r)
    for job, rs in by.items():
        g = G.get(job); task = job.split("#")[0]
        if not g or task not in GOLD: continue
        rs = sorted([r for r in rs if len((r.get("request") or {}).get("messages") or []) > 1], key=lambda r: float(r["t"]))
        if not rs: continue
        t0 = float(rs[0]["t"]); budget = ((rs[0]["request"].get("kwargs") or {}).get("extra_body") or {}).get("thinking_token_budget") or 4096
        calls = []  # (kind, t_end_of_reply, out_tokens_of_reply, touched_gold_file)
        caps = 0
        for r in rs:
            rep = parse(r.get("reply")) or {}
            o = (rep.get("usage") or {}).get("completion_tokens") or 0
            if o >= 0.88 * budget: caps += 1
            for c in (rep.get("message") or {}).get("tool_calls") or []:
                fn = c.get("function") or {}
                try: a = json.loads(fn.get("arguments") or "{}")
                except Exception: a = {}
                if not isinstance(a, dict): a = {}
                k = kind(fn.get("name"), a)
                gold_touch = any(p.lstrip("./").replace("/workspace/", "") in GOLD[task] or any(gf.endswith(p.lstrip("./")) for gf in GOLD[task]) for p in paths_in(fn.get("name"), a))
                calls.append((k, float(r["t"]) - t0 + float(r["seconds"]), o, gold_touch, caps))
        if not calls: continue
        ks = [c[0] for c in calls]
        fe = next((i for i, k in enumerate(ks) if k == "edit"), None)
        pre = ks[:fe] if fe is not None else ks
        first_gold = next((i for i, c in enumerate(calls) if c[3]), None)
        f = dict(
            first_edit_call=fe if fe is not None else len(ks),
            first_edit_s=calls[fe][1] if fe is not None else float(g.get("agent_s") or 480),
            edited=fe is not None,
            reads_before_edit=sum(k in ("show", "read", "outline") for k in pre),
            finds_before_edit=sum(k == "find" for k in pre),
            scripts_before_edit=sum(k in ("script", "pytest", "write") for k in pre),
            capped_before_edit=calls[fe][4] if fe is not None else caps,
            first_gold_call=first_gold if first_gold is not None else len(ks),
            calls_gold_to_edit=(fe - first_gold) if (fe is not None and first_gold is not None and fe >= first_gold) else None,
            edits_total=ks.count("edit"),
            checks_after_edit=sum(k in ("script", "pytest") for k in ks[fe + 1:]) if fe is not None else 0,
            calls_total=len(ks),
        )
        RUNS.append(dict(arm=g.get("arm") or "", task=task, solved=g.get("resolved") in (True, "True"), seq=ks, **f))


def sign_p(a, b):
    n = a + b
    return min(1.0, 2 * sum(math.comb(n, j) for j in range(min(a, b) + 1)) / 2 ** n) if n else 1.0


FEATS = ["first_edit_call", "first_edit_s", "reads_before_edit", "finds_before_edit", "scripts_before_edit", "capped_before_edit",
         "first_gold_call", "calls_gold_to_edit", "edits_total", "checks_after_edit", "calls_total"]
for fam, sel in (("sk_a2 family", lambda r: r["arm"].startswith("sk_a2")), ("ALL agents", lambda r: True)):
    rows = [r for r in RUNS if sel(r) and r["edited"]]  # among runs that edited (no-edit runs always fail)
    by = collections.defaultdict(lambda: ([], []))
    for r in rows: by[r["task"]][0 if r["solved"] else 1].append(r)
    mixed = {t: v for t, v in by.items() if len(v[0]) >= 2 and len(v[1]) >= 2}
    print(f"\n==== {fam}: runs that EDITED, {len(mixed)} tasks with >= 2 solved and >= 2 failed ({sum(len(a) + len(b) for a, b in mixed.values())} runs)")
    print(f"  {'feature':22}{'solved':>9}{'failed':>9}   tasks solved<failed / solved>failed   sign p")
    for ft in FEATS:
        lo = hi = 0; ms, mf = [], []
        for t, (s, f) in mixed.items():
            vs = [r[ft] for r in s if r[ft] is not None]; vf = [r[ft] for r in f if r[ft] is not None]
            if not vs or not vf: continue
            a, b = st.mean(vs), st.mean(vf); ms.append(a); mf.append(b)
            lo += a < b; hi += a > b
        if ms:
            print(f"  {ft:22}{st.mean(ms):9.1f}{st.mean(mf):9.1f}   {lo:3} / {hi:3}{'':22}{sign_p(lo, hi):.3f}")
    # no-edit share on the same tasks (all runs)
    allr = [r for r in RUNS if sel(r)]
    byall = collections.defaultdict(list)
    for r in allr: byall[r["task"]].append(r)
    bounce = {t: v for t, v in byall.items() if 0 < sum(x["solved"] for x in v) < len(v) and len(v) >= 4}
    fails = [x for v in bounce.values() for x in v if not x["solved"]]
    print(f"  bouncing tasks (solved in some runs, failed in others, >= 4 runs): {len(bounce)}; their failed runs {len(fails)}: never edited {sum(not x['edited'] for x in fails) / len(fails):.0%}, edited {sum(x['edited'] for x in fails) / len(fails):.0%}")
    # first-8 call patterns
    pat = collections.defaultdict(lambda: [0, 0])
    for t, v in mixed.items():
        for r in v[0] + v[1]:
            p = " ".join(k for k in r["seq"][:8] if k not in ("submit", "get_st"))
            pat[p][0 if r["solved"] else 1] += 1
print()
