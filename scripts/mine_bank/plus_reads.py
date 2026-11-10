"""r76 mechanism reads per arm: share of run_command calls that went through .git/agent/run.py (adoption), refusals and
the next call after each, the first stage's time (setup / evidence: until the main agent's first request), its call
count, setup agents calling tools they lack, evidence lines kept, first source edit time.
Usage: python3 -I scripts/mine_bank/plus_reads.py RESULTS_FOLDER"""
import collections, json, re, statistics as st, sys

D = sys.argv[1]
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$")
STAGE = ("Your only job is", "install the shell and run one search")
J = collections.defaultdict(list)
for l in open(D + "/requests/requests.jsonl"):
    r = json.loads(l)
    if isinstance(r.get("reply"), dict) and r.get("job"): J[r["job"]].append(r)
A = collections.defaultdict(lambda: collections.defaultdict(list))
for job, q in sorted(J.items()):
    arm = job.partition("#a")[2].split(".")[0]
    q = [r for r in sorted(q, key=lambda r: r["t"]) if r["request"].get("tools")]
    if not q: continue
    t0 = q[0]["t"]; R = {}
    for r in q:
        for m in r["request"]["messages"]:
            if m.get("role") == "tool": R.setdefault(m.get("tool_call_id"), str(m.get("content")))
    stage_end = None; wrapped = direct = 0; refusals = 0; nxt = []; first_edit = None; lacking = 0; stage_calls = 0; prev_refused = False
    for r in q:
        sysm = str(r["request"]["messages"][0].get("content") or "")
        is_stage = any(s in sysm[:400] for s in STAGE)
        if not is_stage and stage_end is None: stage_end = r["t"] - t0
        for c in r["reply"]["message"].get("tool_calls") or []:
            n = c["function"]["name"]
            try: a = json.loads(c["function"]["arguments"])
            except Exception: a = {}
            res = R.get(c.get("id"), ""); cmd = str(a.get("command", ""))
            if prev_refused:
                nxt.append("direct run_command" if n == "run_command" and ".git/agent/run.py" not in cmd else "wrapped run_command" if n == "run_command" else n)
                prev_refused = False
            if is_stage:
                stage_calls += 1
                if n not in ("run_skill_script", "get_status", "load_skill", "list_skills", "load_skill_resource"): lacking += 1
                continue
            if n == "run_command":
                if ".git/agent/run.py" in cmd: wrapped += 1
                else: direct += 1
            if "REFUSED" in res:
                refusals += 1; prev_refused = True
            p = str(a.get("filepath") or "")
            if n in ("edit_file", "write_file") and p and not TEST.search(p) and not p.startswith((".git", "/tmp")) and "error_type" not in res[:200] and first_edit is None:
                first_edit = r["t"] + r["seconds"] - t0
    ev = ""
    for r in q:
        sysm = str(r["request"]["messages"][0].get("content") or "")
        if "# REPOSITORY EVIDENCE (found" in sysm:
            ev = sysm.split("# REPOSITORY EVIDENCE (found", 1)[1].split("\n", 3)[-1].strip(); break
    x = A[arm]
    x["wrapped"].append(wrapped); x["direct"].append(direct); x["refusals"].append(refusals); x["next"] += nxt
    x["stage_s"].append(stage_end if stage_end is not None else 0); x["stage_calls"].append(stage_calls); x["lacking"].append(lacking)
    x["first_edit"].append(first_edit); x["ev_lines"].append(len([l for l in ev.splitlines() if l.strip()]) if ev else None)
for arm, x in A.items():
    w, d = sum(x["wrapped"]), sum(x["direct"]); fe = [v for v in x["first_edit"] if v is not None]; evl = [v for v in x["ev_lines"] if v is not None]
    print(f"{arm:9s} runs {len(x['wrapped'])} | through run.py {w}/{w + d} = {w / max(1, w + d):.0%} | refusals {sum(x['refusals'])} in {sum(1 for v in x['refusals'] if v)} runs, next {dict(collections.Counter(x['next']))}"
          f" | first stage median {st.median(x['stage_s']):.0f} s ({sorted(round(v) for v in x['stage_s'])}), calls {x['stage_calls']}, calls to tools it lacks {sum(x['lacking'])}"
          f" | evidence lines {evl} | first source edit median {st.median(fe) if fe else '-'} s")
