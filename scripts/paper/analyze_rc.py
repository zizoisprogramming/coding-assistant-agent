"""run_command + installed script arms: install, through-script share, garbling, quoting errors, refusals. Usage: analyze_rc.py FOLDER. Prints no task text."""
import collections, json, re, statistics as st, sys
D = sys.argv[1]
G = {(r["arm"], r["instance_id"]): r for r in map(json.loads, open(D + "/results/gen_per_task.jsonl"))}
J = collections.defaultdict(list)
for l in open(D + "/requests/requests.jsonl"):
    r = json.loads(l)
    if isinstance(r.get("reply"), dict) and r.get("job"): J[r["job"]].append(r)
A = collections.defaultdict(list)
for job, q in J.items():
    iid, _, att = job.partition("#a"); arm = att.split(".")[0]
    q.sort(key=lambda r: r["t"]); R = {}
    for r in q:
        for m in r["request"]["messages"]:
            if m.get("role") == "tool": R.setdefault(m.get("tool_call_id"), str(m.get("content")))
    x = collections.Counter(); first_install = None; n = 0; nxt = collections.Counter(); pend = None; tool_s = 0
    for r in q:
        if not r["request"].get("tools"): continue
        for c in r["reply"]["message"].get("tool_calls") or []:
            n += 1; name = c["function"]["name"]; res = R.get(c.get("id"), "")
            try: a = json.loads(c["function"]["arguments"])
            except Exception: a = {}
            if pend: nxt[pend, "through" if name == "run_command" and "agent/run.py" in str(a.get("command", "")) else name]; nxt[pend, ("through" if name == "run_command" and "agent/run.py" in str(a.get("command", "")) else "raw shell" if name == "run_command" else name)] += 1; pend = None
            if name == "run_skill_script":
                if "install.py" in str(a.get("file_path")) and "READY" in res:
                    x["install_ok"] += 1; first_install = first_install or n
                elif '"error_code"' in res: x["skill_garbled"] += 1
                else: x["skill_other"] += 1
            elif name == "run_command":
                cmd = str(a.get("command", ""))
                if not cmd: x["rc_empty"] += 1
                elif "agent/run.py" in cmd:
                    x["through"] += 1
                    if "No such file" in res or "can't open file" in res: x["through_not_installed"] += 1
                    if re.search(r"unexpected EOF|syntax error|unterminated|No closing quotation|bad substitution", res): x["quoting_error"] += 1
                    if "NO COMMAND" in res: x["no_command"] += 1
                    if "REFUSED: no source" in res: x["ref_late"] += 1; pend = "late"
                    if "REFUSED: your last source edit" in res or "REFUSED: FINISH NOW" in res: x["ref_stop"] += 1; pend = "stop"
                    if "REFUSED: first write" in res: x["ref_list"] += 1
                    if "REFUSED: you ran this exact" in res: x["ref_repeat"] += 1
                else:
                    x["raw"] += 1
                    if re.search(r"\b(sed -n|cat |head |tail |grep |git grep|find |ls )", cmd): x["raw_read"] += 1
                if '"error_type"' in res and "CommandError" not in res: x["rc_error"] += 1
            elif name == "edit_file":
                if "mandatory" in res: x["edit_garbled"] += 1
            elif name in ("read_file",):
                x["read_file"] += 1
                if "not found" in res: x["read_file_missing"] += 1
    g = G.get((arm, iid))
    if g: A[arm].append(dict(x=x, inst=first_install, nxt=nxt, res=g["resolved"], patch=g["patch_chars"], s=g["agent_s"], w=g["wall_s"], calls=g["tool_calls"], end=g["end"]))
print(f"{'arm':12}{'solved':>7}{'no patch':>9}{'agent s':>8}{'wall':>6}{'calls':>6}{'at cap':>7}")
for a, v in A.items():
    print(f"{a:12}{sum(r['res'] for r in v):>7}{sum(not r['patch'] for r in v):>9}{st.mean(r['s'] for r in v):>8.0f}{st.mean(r['w'] for r in v):>6.0f}{st.mean(r['calls'] or 0 for r in v):>6.1f}{sum(r['s']>=478 for r in v):>7}")
print()
for a, v in A.items():
    X = collections.Counter(); N = collections.Counter()
    for r in v: X.update(r["x"]); N.update(r["nxt"])
    sh = X["through"] + X["raw"]
    if not sh: continue
    print(f"{a:12} install ok in {sum(r['inst'] is not None for r in v)}/{len(v)} runs (call {st.median([r['inst'] for r in v if r['inst']] or [0]):.0f}) | through script {X['through']}/{sh} = {X['through']/sh:.0%} (raw {X['raw']}, raw reads {X['raw_read']}) | not installed {X['through_not_installed']} | quoting errors {X['quoting_error']} | no command {X['no_command']} | skill garbled {X['skill_garbled']} | edit garbled {X['edit_garbled']} | read_file {X['read_file']} (missing tool {X['read_file_missing']})")
    print(f"{'':12} refusals: late {X['ref_late']}, stop {X['ref_stop']}, checklist {X['ref_list']}, repeat {X['ref_repeat']} | next after late {dict((k[1], c) for k, c in N.items() if k[0]=='late')} | after stop {dict((k[1], c) for k, c in N.items() if k[0]=='stop')}")
print("\nper task (Y solved, e wrong patch, . no patch; agent s)")
arms = list(A); tasks = sorted({t for _, t in G})
print(f"{'':16}" + "".join(f"{a:>12}" for a in arms))
for t in tasks:
    print(f"{t:16}" + "".join((lambda r: f"{('Y' if r['resolved'] else 'e' if r['patch_chars'] else '.')+str(round(r['agent_s'])):>12}")(G[a, t]) if (a, t) in G else f"{'-':>12}" for a in arms))
