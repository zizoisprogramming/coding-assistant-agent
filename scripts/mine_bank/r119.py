"""r119: sb1h vs sbA (history printed by every edit) vs sbB (history printed by every read, read_file removed) on 4 tasks,
2 passes (docs/PLAN.md RUN BUILT r119, bars set there).
Run: python3 -I scripts/mine_bank/r119.py CLONE_DIR   (repo root; CLONE_DIR = the blob-less clones used by hist_at_edit_check.py;
     git log only, to find the real-fix commits; nothing from the repositories is executed)
1. outcomes per arm and per task, time ends, agent seconds, tool calls;
2. heredoc edit results per arm (EDITED / found 0 / found >= 2 / cut-apart / error / other), cut-apart results;
3. sbA: EDITED results with history (commits shown) / header but no commit / the no-history line; the next reply names a shown
   commit or a case; a real-fix commit shown; second edits after history (printed in full for hand reading);
4. sbB / sb1h reads: the read command (exact form), other read commands, read_file; git errors; a real-fix commit shown before
   the first edit; the reasoning names a shown commit or a case before the first edit."""
import ast, collections, glob, json, re, statistics as st, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIRS = sorted(glob.glob(str(ROOT / "data/results/2026-11-19_skill_r119_p*")))
ARMS = ("sb1h", "sbA", "sbB")
TASKS = ("fastapi_15589", "geopandas__geopandas-3240", "klen__peewee_migrate-203", "rich_3521")
solved = lambda g: g["resolved"] in (True, "True")
CLONES = Path(sys.argv[1])
src = (ROOT / "scripts/mine_bank/single_cmd_precheck.py").read_text()
ns = {"__name__": "x"}
exec(src[:src.index("# the model's names and picks")].replace("CLONES = Path(sys.argv[1])", "CLONES = Path(" + repr(str(CLONES)) + ")"), ns)
GOLD = {t: ns["gold_commits"](ns["T"][t], CLONES / ns["T"][t]["repo"].replace("/", "__")) for t in TASKS}
print("real-fix commits (last 3 of each real-fix region):", {t[:14]: sorted(v) for t, v in GOLD.items()})

print("\n#### 1. outcomes")
G = []
for d in DIRS:
    for l in open(f"{d}/results/gen_per_task.jsonl"):
        g = json.loads(l)
        if g.get("arm") in ARMS:
            g["p"] = d[-2:]
            G.append(g)
for a in ARMS:
    A = [g for g in G if g["arm"] == a]
    print(f"  {a:5} runs {len(A):2} | solved {sum(map(solved, A)):2} | no patch {sum(not g.get('patch_chars') for g in A):2}"
          f" | ends {dict(collections.Counter(g['end'] for g in A))} | agent s mean {st.mean(g['agent_s'] for g in A):4.0f}"
          f" | tool calls mean {st.mean(g['tool_calls'] for g in A):4.1f} | llm calls mean {st.mean(g['llm_calls'] for g in A):4.1f}"
          f" | by pass {[sum(solved(g) for g in A if g['p'] == p) for p in ('p1', 'p2')]}")
print("  per task (S solved, E edited no solve, 0 no patch, . not run; p1 p2):")
for t in TASKS:
    row = []
    for a in ARMS:
        cell = ""
        for p in ("p1", "p2"):
            xs = [g for g in G if g["instance_id"] == t and g["arm"] == a and g["p"] == p]
            cell += ("S" if solved(xs[0]) else ("E" if xs[0].get("patch_chars") else "0")) if xs else "."
        row.append(f"{a} {cell}")
    print(f"    {t[:30]:30} " + " | ".join(f"{r:8}" for r in row))


def msg(reply):
    try:
        return ast.literal_eval(reply).get("message") or {}
    except Exception:
        return {}


def calls_of(reply):
    m = msg(reply)
    out = []
    for c in m.get("tool_calls") or []:
        try:
            a = json.loads(c["function"]["arguments"])
        except Exception:
            a = {}
        out.append((c["function"]["name"], a))
    return out


def words_of(reply):
    m = msg(reply)
    return (m.get("reasoning_content") or m.get("reasoning") or "") + "\n" + (m.get("content") or "")


R = collections.defaultdict(list)
for d in DIRS:
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        try:
            r = json.loads(l)
        except Exception:
            continue
        msgs = r["request"]["messages"]
        if len(msgs) == 1:  # the compaction summary request: not a step of the agent
            continue
        k = len(msgs)
        while k > 0 and msgs[k - 1].get("role") == "tool":
            k -= 1
        R[(d[-2:], r["job"])].append(dict(t=float(r["t"]), s=float(r.get("seconds") or 0), tools=[str(m.get("content")).replace("\\n", "\n").replace('\\"', '"') for m in msgs[k:]],
                                           reply=str(r["reply"])))
CUT = "mandatory input parameters are not present"
A_HEAD = "== HOW THESE LINES CHANGED BEFORE"
A_NOHIST = "== NO HISTORY FOR THESE LINES"
CASE = re.compile(r"same kind|complains about|nothing to follow|only (changed |change )?formatting|unrelated|regression|correct(s|ing)? that change"
                  r"|same way|introduced the (bug|change|problem)", re.I)
READ_CMD = re.compile(r"^sed -n (\d+),(\d+)p (\S+)\necho '== HOW THESE LINES CHANGED BEFORE")
OTHER_READ = re.compile(r"^\s*(cat (?!>)|head |tail |nl |sed -n |awk |less |more )")


def steps(rs):
    """(reply, [(name, args, result)]) per request; a call's result is in the next request's trailing tool messages."""
    out = []
    for i, x in enumerate(rs):
        cs = calls_of(x["reply"])
        res = rs[i + 1]["tools"] if i + 1 < len(rs) else []
        out.append((x, [(n, a, res[k] if k < len(res) else None) for k, (n, a) in enumerate(cs)]))
    return out


def kind(res):
    if res is None:
        return "none"
    if "EDITED " in res:
        return "edited"
    if re.search(r"old text found 0 times", res):
        return "found0"
    if re.search(r"old text found ([2-9]|\d\d+) times", res):
        return "found2+"
    if CUT in res:
        return "cut"
    if '"status": "error"' in res:
        return "error"
    return "other"


def shown(res):
    k = res.find(A_HEAD)
    return [h[:7] for h in re.findall(r"^commit ([0-9a-f]{7,})", res[k:], re.M)] if k >= 0 else []


runs = {}
for (p, job), rs in R.items():
    rs.sort(key=lambda x: x["t"])
    arm = job.split("#a")[1].split(".")[0]
    if arm in ARMS:
        runs[(p, job)] = (arm, job.split("#")[0], steps(rs))

print("\n#### 2. edit results (% of heredoc edit calls) and cut-apart")
for a in ARMS:
    res, cut, n = collections.Counter(), 0, 0
    for (p, job), (arm, iid, S) in runs.items():
        if arm != a:
            continue
        n += 1
        for x, cs in S:
            for name, args, r in cs:
                cut += bool(r and CUT in r)
                if name == "run_command" and "OLD_TEXT" in args.get("command", ""):
                    res[kind(r)] += 1
                    if kind(r) not in ("edited", "found0", "found2+"):
                        print(f"    {a} {p} {job.split('#')[0][:24]} non-EDITED result: {(r or 'NO RESULT (run ended)')[:240]!r}")
    tot = sum(res.values())
    print(f"  {a:5} runs {n} | heredoc edits {tot} ({tot / n:.1f}/run): " + ", ".join(f"{k} {v} ({100 * v / tot:.0f}%)" for k, v in res.most_common())
          + f" | non-EDITED {100 * (tot - res['edited']) / tot:.0f}% | found0 {100 * res['found0'] / tot:.0f}% | cut-apart results {cut}")

print("\n#### 3. sbA: history at the edit")
ed = hist = head_nocommit = nohist = 0
got, named, case_only, gold_runs, second = 0, 0, 0, 0, []
for (p, job), (arm, iid, S) in sorted(runs.items()):
    if arm != "sbA":
        continue
    run_hist = run_named = run_case = run_gold = False
    for i, (x, cs) in enumerate(S):
        for name, args, r in cs:
            if not (name == "run_command" and "OLD_TEXT" in args.get("command", "")) or kind(r) != "edited":
                continue
            ed += 1
            hs = shown(r)
            if hs:
                hist += 1
            elif A_HEAD in r:
                head_nocommit += 1
            if A_NOHIST in r:
                nohist += 1
            if not hs:
                continue
            run_hist = True
            run_gold |= bool(set(hs) & GOLD[iid])
            if i + 1 < len(S):
                w = words_of(S[i + 1][0]["reply"])
                run_named |= any(h in w for h in hs)
                run_case |= bool(CASE.search(w))
                # the next heredoc edit in the run after this history, for hand reading
                for j in range(i + 1, len(S)):
                    nxt = [(n2, a2, r2) for n2, a2, r2 in S[j][1] if n2 == "run_command" and "OLD_TEXT" in a2.get("command", "")]
                    if nxt:
                        second.append((p, iid, r, words_of(S[i + 1][0]["reply"]), j - i, nxt[0][1]["command"], kind(nxt[0][2])))
                        break
    got += run_hist
    named += run_hist and run_named
    case_only += run_hist and run_case and not run_named
    gold_runs += run_gold
    print(f"  {p} {iid[:28]:28} history {'Y' if run_hist else '-'} | real-fix commit shown {'Y' if run_gold else '-'}"
          f" | next reply names a shown commit {'Y' if run_named else '-'} case words {'Y' if run_case else '-'}")
print(f"  EDITED {ed} | history with commits {hist} ({100 * hist / max(ed, 1):.0f}%) | header without commits {head_nocommit} | no-history line {nohist}")
print(f"  runs with history {got} | the next reply names a shown commit {named} | case words only {case_only} | runs shown a real-fix commit {gold_runs}")
print("\n  ---- edits that came after a history output (for hand reading) ----")
for p, iid, r, w, gap, cmd, k in second:
    print(f"\n  ## {p} {iid} | next edit {gap} replies later, result {k}")
    print("  HISTORY:\n" + "\n".join("    " + l for l in r[r.find(A_HEAD):][:1800].splitlines()))
    print("  NEXT REPLY WORDS:\n" + "\n".join("    " + l for l in w.strip()[:900].splitlines()))
    print("  NEXT EDIT:\n" + "\n".join("    " + l for l in cmd.split("\nrm -f .git/agent/range")[0].split("python3 - ")[0][:1500].splitlines()))

print("\n#### 4. reads (sbB read command vs other reads) and history before the first edit")
for a in ARMS:
    c = collections.Counter()
    gold_before = named_before = case_before = nruns = 0
    for (p, job), (arm, iid, S) in sorted(runs.items()):
        if arm != a:
            continue
        nruns += 1
        before = True
        gb = nb = cb = False
        hs_seen = set()
        for x, cs in S:
            if before:
                w = words_of(x["reply"])
                nb |= any(h in w for h in hs_seen)
                cb |= bool(hs_seen) and bool(CASE.search(w))
            for name, args, r in cs:
                cmd = args.get("command", "") if name == "run_command" else ""
                if name == "run_command" and "OLD_TEXT" in cmd:
                    before = False
                elif name == "read_file":
                    c["read_file"] += 1
                elif READ_CMD.match(cmd):
                    c["read cmd"] += 1
                    r = r or ""
                    c["has only N lines"] += "has only" in r
                    c["no path in the commit"] += "There is no path" in r
                    hs = shown(r)
                    c["with commits"] += bool(hs)
                    if before:
                        c["before first edit"] += 1
                        hs_seen |= set(hs)
                        gb |= bool(set(hs) & GOLD[iid])
                elif "git log -L" in cmd:
                    c["other git log -L"] += 1
                elif OTHER_READ.match(cmd):
                    c["other read cmd"] += 1
        gold_before += gb
        named_before += nb
        case_before += cb and not nb
    reads = c["read cmd"] + c["read_file"] + c["other read cmd"]
    print(f"  {a:5} runs {nruns} | reads {reads}: " + ", ".join(f"{k} {v}" for k, v in c.items())
          + f" | read cmd share {100 * c['read cmd'] / max(reads, 1):.0f}%"
          + (f" | runs with a real-fix commit before the first edit {gold_before} | reasoning names a shown commit before the first edit"
             f" {named_before} (case words only {case_before})" if a == "sbB" else ""))

print("\n#### 5. where the time went: compactions, prompt size, reply length, how sbB changed files")
U = collections.defaultdict(lambda: collections.defaultdict(list))
for d in DIRS:
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        try:
            r = json.loads(l)
        except Exception:
            continue
        arm = r["job"].split("#a")[1].split(".")[0]
        if arm not in ARMS:
            continue
        key = (d[-2:], r["job"])
        msgs = r["request"]["messages"]
        try:
            u = ast.literal_eval(str(r["reply"])).get("usage") or {}
        except Exception:
            u = {}
        if len(msgs) == 1:
            U[arm]["compactions"].append(key)
            continue
        U[arm]["sys_words"].append(len(msgs[0]["content"].split()))
        U[arm]["prompt_tok"].append(u.get("prompt_tokens") or 0)
        U[arm]["out_tok"].append(u.get("completion_tokens") or 0)
        U[arm]["sec"].append(float(r.get("seconds") or 0))
for a in ARMS:
    x = U[a]
    nr = len({k for k in runs if runs[k][0] == a})
    print(f"  {a:5} system prompt words {x['sys_words'][0]} | compactions {len(x['compactions'])} ({len(x['compactions']) / nr:.1f}/run)"
          f" | prompt tokens per request mean {st.mean(x['prompt_tok']):5.0f} | output tokens per reply mean {st.mean(x['out_tok']):4.0f}"
          f" median {st.median(x['out_tok']):4.0f} | replies >= 60 s {sum(s >= 60 for s in x['sec'])} of {len(x['sec'])} | reply s total per run {sum(x['sec']) / nr:4.0f}")
WR = re.compile(r"write_text|open\([^)]*['\"]w['\"]|sed -i|\.write\(")
for a in ARMS:
    c = collections.Counter()
    for (p, job), (arm, iid, S) in runs.items():
        if arm != a:
            continue
        for x, cs in S:
            for name, args, r in cs:
                cmd = args.get("command", "") if name == "run_command" else ""
                if "OLD_TEXT" in cmd:
                    c["heredoc edit"] += 1
                elif re.match(r"\s*cat > (?!reproduce|test_|/tmp)", cmd) and not cmd.lstrip().startswith("cat > .git"):
                    c["cat > file"] += 1
                elif cmd.lstrip().startswith("python") and WR.search(cmd):
                    c["python writes a file"] += 1
                elif "sed -i" in cmd:
                    c["sed -i"] += 1
    print(f"  {a:5} file-writing calls: {dict(c)}")
