"""r52 screen: arms on the same tasks, against pub024 in the same run. Usage: analyze_screen.py FOLDER. Prints no task text."""
import collections, json, random, re, statistics as st, sys
D = sys.argv[1]; random.seed(6)
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$|pytest\.ini$")
G = {}
for r in map(json.loads, open(D + "/results/gen_per_task.jsonl")): G[r["arm"], r["instance_id"]] = r
print(json.dumps(json.load(open(D + "/results/phases.json"))).replace(" ", "")[:220])
CTRL = __import__("os").environ.get("CTRL", "pub024")  # the control arm (r73: combo1)
ARMS = list(dict.fromkeys(a for a, _ in G)); ARMS = [CTRL] + [a for a in ARMS if a != CTRL]; TASKS = sorted({t for _, t in G})
print(len(G), "runs", len(TASKS), "tasks", ARMS)
J = collections.defaultdict(list)
for l in open(D + "/requests/requests.jsonl"):
    r = json.loads(l)
    if isinstance(r.get("reply"), dict) and r.get("job"): J[r["job"]].append(r)
M = {}
for job, q in J.items():
    iid, _, att = job.partition("#a"); arm = att.split(".")[0]
    q.sort(key=lambda r: r["t"]); t0 = q[0]["t"]; R = {}
    for r in q:
        for m in r["request"]["messages"]:
            if m.get("role") == "tool": R.setdefault(m.get("tool_call_id"), str(m.get("content")))
    x = collections.Counter(); first = last = sub = None; summ = 0; toks = 0; pend = None; nxt = collections.Counter(); places = False; test_after = False; wrote_list = False
    for r in q:
        if not r["request"].get("tools"): summ += r["seconds"]; continue
        toks += r["reply"]["usage"]["completion_tokens"]
        for c in r["reply"]["message"].get("tool_calls") or []:
            n = c["function"]["name"]; x[n] += 1
            try: a = json.loads(c["function"]["arguments"])
            except Exception: a = {}
            res = R.get(c.get("id"), ""); t = r["t"] + r["seconds"] - t0
            if pend: nxt[pend, n] += 1; pend = None
            if n == "edit_file":
                p = str(a.get("filepath") or "")
                if "mandatory" in res: x["bad_edit"] += 1
                elif "error_type" in res: x["fail_edit"] += 1
                elif p and not TEST.search(p) and not p.startswith("/tmp"):
                    first = first if first is not None else t; last = t
            if n == "write_file" and ".git/agent/issue.md" in str(a.get("filepath")): wrote_list = True
            if n in ("run_skill_script", "run_command"):
                cmd = str(a.get("command", "")) + " ".join(map(str, a.get("positional_args") or [])) if isinstance(a.get("positional_args", []), list) else ""
                if n == "run_skill_script" and ('"error_code"' in res): x["bad_shell"] += 1
                else: x["good_shell"] += 1
                if re.search(r"pytest|unittest", cmd) and first is not None: test_after = True
                if "REFUSED: no source file" in res: x["ref_late"] += 1; pend = "late"
                if "REFUSED: your last source edit" in res: x["ref_stop"] += 1; pend = "stop"
                if "REFUSED: first write" in res: x["ref_list"] += 1
                if "[other places]" in res or "[related tests]" in res: places = True
            if n == "submit_patch" and sub is None: sub = t
    g = G.get((arm, iid))
    if g: M[arm, iid] = dict(x=x, first=first, last=last, sub=sub, summ=summ, toks=toks, nxt=nxt, places=places, test=test_after, lst=wrote_list, s=g["agent_s"], w=g["wall_s"], res=g["resolved"], patch=g["patch_chars"], calls=g["tool_calls"], end=g["end"])
print(f"\n{'arm':10}{'solved':>7}{'only+':>6}{'only-':>6}{'no patch':>9}{'wall':>6}{'vs pub':>16}{'agent':>7}{'overhead':>9}{'first edit':>11}{'at cap':>7}{'calls':>7}{'tokens':>8}{'summ s':>7}")
base = {t: G[CTRL, t] for t in TASKS if (CTRL, t) in G}
for a in ARMS:
    ts = [t for t in TASKS if (a, t) in G and t in base]; v = [G[a, t] for t in ts]
    d = [G[a, t]["wall_s"] - base[t]["wall_s"] for t in ts]; xs = sorted(st.mean(random.choices(d, k=len(d))) for _ in range(3000))
    mv = [M[a, t] for t in ts if (a, t) in M]; fe = [m["first"] for m in mv if m["first"] is not None]
    pl = sum(G[a, t]["resolved"] and not base[t]["resolved"] for t in ts); mn = sum(base[t]["resolved"] and not G[a, t]["resolved"] for t in ts)
    print(f"{a:10}{sum(r['resolved'] for r in v):>7}{pl:>6}{mn:>6}{sum(not r['patch_chars'] for r in v):>9}{st.mean(r['wall_s'] for r in v):>6.0f}{(f'{st.mean(d):+.0f} ({xs[75]:+.0f},{xs[2925]:+.0f})' if a!=CTRL else '-'):>16}{st.mean(r['agent_s'] for r in v):>7.0f}{st.mean(r['wall_s']-r['agent_s'] for r in v):>9.0f}{st.median(fe) if fe else 0:>11.0f}{sum(r['agent_s']>=478 for r in v):>7}{st.mean(r['tool_calls'] or 0 for r in v):>7.1f}{st.mean(m['toks'] for m in mv):>8.0f}{st.mean(m['summ'] for m in mv):>7.0f}")
print("\nfilter (set before the run): solves at least pub024 - 1, mean wall at most pub024 + 10 s")
ps = sum(r["resolved"] for r in base.values()); pw = st.mean(r["wall_s"] for r in base.values())
for a in ARMS[1:]:
    v = [G[a, t] for t in TASKS if (a, t) in G]; s = sum(r["resolved"] for r in v); w = st.mean(r["wall_s"] for r in v)
    print(f"  {a:10} solves {s} ({'ok' if s >= ps - 1 else 'FAIL'}), wall {w:.0f} ({'ok' if w <= pw + 10 else 'FAIL'}) -> {'KEEP' if s >= ps - 1 and w <= pw + 10 else 'drop'}; no patch {sum(not r['patch_chars'] for r in v)}")
print("\nper task (Y solved, e wrong patch, . no patch; seconds)")
print(f"{'':16}" + "".join(f"{a:>10}" for a in ARMS))
for t in TASKS:
    print(f"{t:16}" + "".join((lambda r: f"{('Y' if r['resolved'] else 'e' if r['patch_chars'] else '.')+str(round(r['agent_s'])):>10}" if r else f"{'-':>10}")(G.get((a, t))) for a in ARMS))
print("\nbehaviour: refusals, next move, garbling, tests")
for a in ARMS:
    mv = [M[a, t] for t in TASKS if (a, t) in M]; n = len(mv); xx = collections.Counter(); nx = collections.Counter()
    for m in mv: xx.update(m["x"]); nx.update(m["nxt"])
    ed = [m for m in mv if m["first"] is not None]; ls = [m["s"] - m["last"] for m in ed]
    sh = xx["bad_shell"] + xx["good_shell"]
    print(f"{a:10} runs {n} | edited {len(ed)} | tested after edit {sum(m['test'] for m in ed)} | submit calls in {sum(m['sub'] is not None for m in mv)} | last edit to end median {st.median(ls) if ls else 0:.0f} s | late refusal runs {sum(m['x']['ref_late']>0 for m in mv)} next {dict((k[1],v) for k,v in nx.items() if k[0]=='late')} | stop refusal runs {sum(m['x']['ref_stop']>0 for m in mv)} next {dict((k[1],v) for k,v in nx.items() if k[0]=='stop')} | bad shell {xx['bad_shell']}/{sh} = {xx['bad_shell']/max(1,sh):.0%} | bad edit {xx['bad_edit']} failed edit {xx['fail_edit']} ok edit runs | places shown {sum(m['places'] for m in mv)} | checklist written {sum(m['lst'] for m in mv)} | solved with {sum(m['res'] for m in mv)}")
print("\nby time spent, seconds per run: solved / no patch / wrong")
for a in ARMS:
    v = [G[a, t] for t in TASKS if (a, t) in G]; n = len(v)
    print(f"  {a:10} {sum(r['wall_s'] for r in v if r['resolved'])/n:4.0f} / {sum(r['wall_s'] for r in v if not r['patch_chars'])/n:4.0f} / {sum(r['wall_s'] for r in v if r['patch_chars'] and not r['resolved'])/n:4.0f}")
