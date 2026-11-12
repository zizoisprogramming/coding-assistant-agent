"""One row per logged agent run, from every data/results folder with call-level logs (requests.jsonl or traces/).
Writes data/analysis/run_table.jsonl (gitignored; holds no task text). Run: python3 scripts/paper/build_run_table.py

Each tool call is classified (search, read, test, exec, edit...), and edits and reads are compared with the files the
real fix changed (tasks.jsonl 'patch'), which separates wrong-place from right-place-wrong-content failures."""
import collections
import glob
import json
import os
import re

OUT = "data/analysis/run_table.jsonl"
T = {json.loads(l)["instance_id"]: json.loads(l) for l in open("data/tasks.jsonl")}
GOLD = {i: re.findall(r"^\+\+\+ b/(\S+)", t["patch"], re.M) for i, t in T.items()}
TEST_RE = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)conftest\.py$|(^|/)pytest\.ini$")
SHELL_EDIT = re.compile(r"sed -i|git apply|\bpatch\b -|write_text\(|open\([^)]*['\"][wa]['\"]")
SEARCH = re.compile(r"\b(git grep|grep|rg|git ls-files|find|ag)\b|a\.py find")
READ = re.compile(r"\b(sed -n|cat|head|tail|nl|awk)\b|a\.py (show|outline|reshow)|inspect\.getsource")
TESTCMD = re.compile(r"pytest|unittest")
EXEC = re.compile(r"\bpython[\d.]*\s+(-c\b|-\s|<<|[^-\s])")
GIT = re.compile(r"\bgit (status|diff|log|show|checkout)\b")


def family(arm):
    a = arm or ""
    if "e4b" in a or "12b" in a:
        return None
    if a == "bf":
        return "bf"
    if a in ("mix", "mix_r1", "mix_r2"):
        return "mix"
    if a.startswith("mix_"):
        return "mix-variant"
    if a == "pub024":
        return "pub"
    if a.startswith("sq1c"):
        return "clock"
    if a in ("sq1", "sq2"):
        return "seq-noclock"
    if a.startswith("srep"):
        return "srep"
    if a in ("sa2", "bo3", "sk_fr", "sk_fr2"):
        return "team"
    if a.startswith("sk_nav"):
        return "skill-nav"
    if a.startswith("sk_"):
        return "skill-reader"
    if re.match(r"le\d?|lo\d?", a):
        return "locator-editor"
    if a.startswith(("r4", "af", "1a", "1b", "1c")):
        return "early"
    return "other"


def shell_of(name, args):
    if name == "run_command":
        return str(args.get("command", ""))
    if name == "run_skill_script":
        pa = args.get("positional_args") or []
        cmd = " ".join(map(str, pa)) if isinstance(pa, list) else str(pa)
        if not cmd and isinstance(args.get("args"), dict):
            cmd = " ".join(map(str, args["args"].values()))
        if not cmd and args.get("skill_name") == "agent":
            return "install"
        return cmd
    return None


def path_of(args):
    return str(args.get("filepath") or args.get("file_path") or args.get("path") or "")


def is_source(p):
    return bool(p) and not p.startswith("/tmp") and ".git/agent" not in p and not TEST_RE.search(p) and "repro" not in os.path.basename(p)


def analyse(iid, turns, result):
    """turns: list of dicts t_end, tokens, reasoning, seconds, calls [(name, args, result_text)]."""
    gold = GOLD.get(iid, [])
    gold_src = [g for g in gold if not TEST_RE.search(g)]
    k = collections.Counter()
    first_edit = first_edit_call = first_read_gold = None
    edited, read_paths, cmds_seen = [], collections.Counter(), collections.Counter()
    last_test = None
    test_after_edit = 0
    ncall = 0
    last_edit_t = None
    first_submit = None
    edit_times = []
    nbudget = 0
    first_attempt = first_attempt_call = None
    call_times = []
    t28 = None
    edited_by28 = None
    pre = collections.Counter()
    kind_s = collections.Counter()
    tok_pre = 0
    rt = collections.Counter()
    fixed_at = None
    after_refusal = []
    for tn in turns:
        if first_edit is None:
            tok_pre += tn["tokens"]
        for name, args, res in tn["calls"]:
            ncall += 1
            if name not in ("submit_patch", "get_status"):
                nbudget += 1
                call_times.append(round(tn["t_end"]))
                if nbudget == 28 and t28 is None:
                    t28 = tn["t_end"]
                    edited_by28 = first_edit is not None
            before = collections.Counter(k)
            was_pre = first_edit is None
            if res and tn["calls"]:
                r0 = res.lower()
                if "refused:" in r0:
                    typ = ("noedit" if "no source file is edited" in r0 else "finish" if "finish now" in r0 or "since your last source edit" in r0
                           else "repeat" if "exact command" in r0 else "report" if "report now" in r0 else "checklist" if "checklist" in r0 else "other")
                    rt[typ] += 1
                    after_refusal.append((typ, tn["t_end"]))
                if fixed_at is None and "repro passes" in r0:
                    fixed_at = tn["t_end"]
            res = res or ""
            low = res.lower()
            shell = shell_of(name, args)
            if "refused" in low[:300] or "\nrefused:" in low:
                k["refused"] += 1
            if "is required" in low or "invalid_arguments" in low or "missing" in low[:80] and "argument" in low[:120]:
                k["garbled"] += 1
            if was_pre and ((name == "read_file" and TEST_RE.search(path_of(args))) or (shell and TEST_RE.search(shell) and READ.search(shell) and not TESTCMD.search(shell))):
                pre["read_tests"] += 1
            if name == "read_file":
                k["read"] += 1
                k["read_file"] += 1
                p = path_of(args)
                read_paths[p] += 1
                if p in gold_src and first_read_gold is None:
                    first_read_gold = tn["t_end"]
            elif name == "edit_file":
                p = path_of(args)
                ok = '"error"' not in res and "error_type" not in res and not low.startswith("error") and "mandatory input" not in low
                if first_attempt is None:
                    first_attempt, first_attempt_call = tn["t_end"], nbudget
                if not ok:
                    k["em_malformed" if "mandatory input" in low else "em_budget" if "budgetexceeded" in low else "em_mismatch"] += 1
                k["edit_ok" if ok else "edit_fail"] += 1
                if ok and is_source(p):
                    edited.append(p)
                    edit_times.append(tn["t_end"])
                    if first_edit is None:
                        first_edit, first_edit_call = tn["t_end"], ncall
                    last_edit_t = tn["t_end"]
            elif name == "write_file":
                p = path_of(args)
                if is_source(p):
                    k["write_source"] += 1
                    edited.append(p)
                    edit_times.append(tn["t_end"])
                    if first_edit is None:
                        first_edit, first_edit_call = tn["t_end"], ncall
                    last_edit_t = tn["t_end"]
                else:
                    k["write_scratch"] += 1
            elif name == "submit_patch":
                k["submit"] += 1
                if first_submit is None:
                    first_submit = tn["t_end"]
            elif name == "get_status":
                k["status"] += 1
            elif name in ("search_similar_code", "get_code_neighbors", "get_code_subgraph"):
                k["codegraph"] += 1
            elif shell is not None:
                k["shell"] += 1
                cmds_seen[shell] += 1
                if SHELL_EDIT.search(shell) and "repro" not in shell and "/tmp/" not in shell:
                    k["shell_edit"] += 1
                    hit = [g for g in gold_src if g in shell]
                    edited += hit or ["?shell"]
                    edit_times.append(tn["t_end"])
                    if first_edit is None:
                        first_edit, first_edit_call = tn["t_end"], ncall
                    last_edit_t = tn["t_end"]
                elif re.search(r"(^|[\s/])a\.py find", shell):
                    k["search"] += 1
                elif re.search(r"(^|[\s/])a\.py (show|outline|reshow)", shell):
                    k["read"] += 1
                    k["shell_read"] += 1
                elif re.search(r"(^|[\s/])a\.py\b", shell) or shell == "install":
                    k["tool_helper"] += 1
                elif TESTCMD.search(shell):
                    k["test"] += 1
                    if first_edit is not None:
                        test_after_edit += 1
                    last_test = "pass" if re.search(r"(?<![\d.])\d+ passed|(\\n|^)OK\b", res) and not re.search(r"(?<![\d.])\d+ (failed|errors?)\b", res) else ("fail" if re.search(r"(?<![\d.])\d+ (failed|errors?)\b|FAILED|\berror\b", res, re.I) else "unclear")
                elif EXEC.search(shell):
                    k["exec"] += 1
                elif SEARCH.search(shell):
                    k["search"] += 1
                elif READ.search(shell):
                    k["read"] += 1
                    k["shell_read"] += 1
                elif GIT.search(shell):
                    k["git"] += 1
                else:
                    k["shell_other"] += 1
                for g in gold_src:
                    if g in shell and READ.search(shell) and first_read_gold is None:
                        first_read_gold = tn["t_end"]
            else:
                k["other_tool"] += 1
            delta = k - before
            for key in delta:
                if key in ("refused", "garbled"):
                    continue
                if was_pre:
                    pre[key] += delta[key]
                kind_s[key] += (tn["seconds"] or 0) / max(1, len(tn["calls"]))
    toks = [t["tokens"] for t in turns]
    secs = [t["seconds"] for t in turns if t["seconds"] is not None]
    resolved = bool(result["resolved"])
    patch = result["patch_chars"]
    edited_gold = [g for g in gold_src if g in edited]
    outcome = "solved" if resolved else ("wrong_edit" if patch else "no_patch")
    return dict(
        iid=iid, outcome=outcome, resolved=resolved, patch=patch, agent_s=result["agent_s"], wall_s=result["wall_s"],
        turns=len(turns), calls=ncall, tokens=sum(toks), reasoning=sum(t["reasoning"] for t in turns), max_tok=max(toks or [0]),
        long_turns=sum(x >= 2000 for x in toks), secs_long=sum(t["seconds"] or 0 for t in turns if t["tokens"] >= 1000),
        model_s=sum(secs), kinds=dict(k), pre=dict(pre), kind_s={a: round(b) for a, b in kind_s.items()}, tok_pre=tok_pre, refusals=dict(rt), fixed_at=fixed_at,
        first_refusal=after_refusal[0] if after_refusal else None, tc_harness=result.get("tool_calls"), budget_calls=nbudget, first_attempt=first_attempt, first_attempt_call=first_attempt_call, call_times=call_times, last_edit_budget=None, time_at_28=t28, edited_by28=edited_by28, last_edit_call=None, first_edit=first_edit, first_edit_call=first_edit_call, last_edit=last_edit_t,
        first_submit=first_submit, end_turn=turns[-1]["t_end"] if turns else None, n_edits=len(edit_times), files_edited=len(set(edited)), first_read_gold=first_read_gold, read_gold=first_read_gold is not None,
        n_gold=len(gold_src), edited_gold=len(edited_gold), edited_files=sorted(set(edited)), gold_files=sorted(gold_src), first_edit_gold=bool(edited) and edited[0] in gold_src,
        all_gold=bool(gold_src) and len(edited_gold) == len(gold_src), reread=sum(v - 1 for v in read_paths.values() if v > 1),
        repeat_cmd=sum(v - 1 for v in cmds_seen.values() if v > 1), last_test=last_test, test_after_edit=test_after_edit,
        edit_gaps=[round(b - a) for a, b in zip(edit_times, edit_times[1:])], end=result.get("end"),
    )


rows = []
# ---- requests.jsonl runs
for f in sorted(glob.glob("data/results/*/requests/requests.jsonl")):
    d = f.split("/")[2]
    per = glob.glob(f"data/results/{d}/**/gen_per_task.jsonl", recursive=True)
    if not per:
        continue
    res = {(r["instance_id"], str(r.get("attempt"))): r for r in map(json.loads, open(per[0]))}
    J = collections.defaultdict(list)
    for line in open(f):
        r = json.loads(line)
        if isinstance(r.get("reply"), dict) and r.get("job"):
            J[r["job"]].append(r)
    for job, reqs in J.items():
        iid, _, att = job.partition("#a")
        g = res.get((iid, att))
        if g is None or iid not in T:
            continue
        fam = family(g.get("arm"))
        if fam is None:
            continue
        reqs.sort(key=lambda r: r["t"])
        results = {}
        for r in reqs:
            for m in r["request"]["messages"]:
                if m.get("role") == "tool" and m.get("tool_call_id") not in results:
                    results[m.get("tool_call_id")] = str(m.get("content"))
        t0 = reqs[0]["t"]
        turns = []
        for r in reqs:
            m = r["reply"]["message"]
            calls = []
            for c in m.get("tool_calls") or []:
                try:
                    a = json.loads(c["function"]["arguments"]) if isinstance(c["function"]["arguments"], str) else c["function"]["arguments"]
                except Exception:
                    a = {"_bad": True}
                calls.append((c["function"]["name"], a if isinstance(a, dict) else {}, results.get(c.get("id"))))
            turns.append(dict(t_end=r["t"] + r["seconds"] - t0, seconds=r["seconds"], tokens=r["reply"]["usage"]["completion_tokens"],
                              reasoning=len(m.get("reasoning_content") or m.get("reasoning") or ""), calls=calls))
        row = analyse(iid, turns, g)
        row.update(arm=g.get("arm"), family=fam, folder=d, attempt=att, source="requests")
        rows.append(row)
# ---- traces of the October rung runs
for td in sorted(glob.glob("data/results/*/results/*/traces")):
    parts = td.split("/")
    d, arm = parts[2], parts[4]
    fam = family(arm)
    tr = os.path.join(os.path.dirname(td), "task_results.jsonl")
    if fam is None or not os.path.exists(tr):
        continue
    res = {r["instance_id"]: r for r in map(json.loads, open(tr))}
    for f in glob.glob(td + "/trace_*.json"):
        iid = os.path.basename(f)[6:-5]
        g = res.get(iid)
        if g is None or iid not in T:
            continue
        try:
            steps = json.load(open(f))["steps"]
        except Exception:
            continue
        turns, prev = [], 0.0
        for s in steps:
            if s.get("source") != "agent":
                continue
            obs = s.get("observation") or {}
            tcs = s.get("tool_calls") or []
            el = (obs.get("extra") or {}).get("elapsed_s") or (s.get("extra") or {}).get("elapsed_s") or (tcs[0].get("extra", {}).get("elapsed_s") if tcs else None) or prev
            content = obs.get("content") if isinstance(obs, dict) else None
            calls = [(c.get("function_name"), c.get("arguments") or {}, str(content)) for c in tcs]
            turns.append(dict(t_end=el, seconds=max(0.0, el - prev), tokens=(s.get("metrics") or {}).get("completion_tokens") or 0, reasoning=len(s.get("message") or ""), calls=calls))
            prev = el
        result = dict(resolved=g["resolved"], patch_chars=g.get("agent_patch_size") or 0, agent_s=g.get("duration_seconds"), wall_s=g.get("duration_seconds"), end="ok" if not g.get("error") else "time")
        row = analyse(iid, turns, result)
        row.update(arm=arm, family=fam, folder=d, attempt=arm, source="trace")
        rows.append(row)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w") as h:
    for r in rows:
        h.write(json.dumps(r) + "\n")
c = collections.Counter(r["family"] for r in rows)
print(len(rows), "runs ->", OUT)
for fam, n in c.most_common():
    x = [r for r in rows if r["family"] == fam]
    print(f"{fam:16} {n:5} runs, solved {sum(r['resolved'] for r in x):4}, tasks {len({r['iid'] for r in x}):3}, arms {len({r['arm'] for r in x})}")
