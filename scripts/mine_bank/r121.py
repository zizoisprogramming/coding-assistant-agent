"""r121: sb1h vs sbF2 (every edit prints the history of the enclosing function, 3 commits, titles and +/- lines only) on 4 tasks, 2 passes
(docs/PLAN.md RUN BUILT r121, bars set there). Useful commits: scripts/mine_bank/hist_useful_commits.json (my labels).
Run: python3 -I scripts/mine_bank/r121.py CLONE_DIR   (repo root; CLONE_DIR = the blob-less clones used by hist_at_edit_check.py;
     git log only, to find the real-fix commits; nothing from the repositories is executed)
1. outcomes per arm and per task, time ends, agent seconds, tool calls;
2. heredoc edit results per arm (EDITED / found 0 / found >= 2 / cut-apart / error / other), cut-apart results;
3. sbF: EDITED results with history / the no-history line; useful commits shown (labels); the next reply names a shown commit
   or a case; every history output with the next reply and the next edit printed for hand reading;
4. compactions, prompt size, reply length; runs that changed an existing source file."""
import ast, collections, glob, json, re, statistics as st, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIRS = sorted(glob.glob(str(ROOT / "data/results/2026-11-20_skill_r121_p*")))
ARMS = ("sb1h", "sbF2")
TASKS = ("fastapi_11194", "klen__peewee_migrate-203", "rich_3506", "rich_3521")
solved = lambda g: g["resolved"] in (True, "True")
CLONES = Path(sys.argv[1])
src = (ROOT / "scripts/mine_bank/single_cmd_precheck.py").read_text()
ns = {"__name__": "x"}
exec(src[:src.index("# the model's names and picks")].replace("CLONES = Path(sys.argv[1])", "CLONES = Path(" + repr(str(CLONES)) + ")"), ns)
# real-fix commits by hash are not printed: Kaggle's task repos carry different hashes (the labels file holds 'DATE TITLE')

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
A_HEAD = "== HOW THIS FUNCTION CHANGED BEFORE"
A_NOHIST = "== NO HISTORY FOR THIS CODE"
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
    """titles of the commits under the history header"""
    k = res.find(A_HEAD)
    return [(d + " " + m.strip())[:121] for d, m in re.findall(r"^commit [0-9a-f]{7,} (\S+) (.*)$", res[k:], re.M)] if k >= 0 else []


def hashes(res):
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

print("\n#### 3. sbF2: history at the edit (U = useful, w = weak, ? = not labelled yet)")
LAB = json.loads((ROOT / "scripts/mine_bank/hist_useful_commits.json").read_text())
# Kaggle's task repos carry different hashes than the public clones (rewritten history; dates kept): match labels by 'DATE TITLE'
USE = {t: set(LAB[t]["useful_titles"]) for t in TASKS}
WEAK = {t: set(LAB[t]["weak_titles"]) for t in TASKS}
print("  useful:", {t[:14]: sorted(v) for t, v in USE.items()})
ed = hist = nohist = 0
got = got_u = named_u = case_u = second_n = 0
unl = collections.defaultdict(set)
hand = []
for (p, job), (arm, iid, S) in sorted(runs.items()):
    if arm != "sbF2":
        continue
    rh = ru = rn = rc = r2 = False
    for i, (x, cs) in enumerate(S):
        for name, args, r in cs:
            if not (name == "run_command" and "OLD_TEXT" in args.get("command", "")) or kind(r) != "edited":
                continue
            ed += 1
            hs = shown(r)
            hist += bool(hs)
            nohist += A_NOHIST in r
            if not hs:
                continue
            rh = True
            u = bool(set(hs) & USE[iid])
            ru |= u
            for h in hs:
                if h not in USE[iid] | WEAK[iid]:
                    unl[iid].add(h[:90])
            w = words_of(S[i + 1][0]["reply"]) if i + 1 < len(S) else ""
            nxt = calls_of(S[i + 1][0]["reply"]) if i + 1 < len(S) else []
            if u:
                rn |= any(h in w for h in hashes(r)) or any(len(h) > 23 and h[11:51] in w for h in hs)
                rc |= bool(CASE.search(w))
            later = [(j, a2["command"]) for j in range(i + 1, len(S)) for n2, a2, r2_ in S[j][1] if n2 == "run_command" and "OLD_TEXT" in a2.get("command", "")]
            hand.append((p, iid, u, r, w, nxt, later[:1]))
    got += rh
    got_u += ru
    named_u += ru and rn
    case_u += ru and rc and not rn
    print(f"  {p} {iid[:28]:28} history {'Y' if rh else '-'} | useful commit shown {'Y' if ru else '-'} | next reply names a shown commit {'Y' if rn else '-'} case words {'Y' if rc else '-'}")
print(f"  EDITED {ed} | history with commits {hist} ({100 * hist / max(ed, 1):.0f}%) | no-history line {nohist}")
print(f"  runs with history {got} | with a useful commit {got_u} | of those, the next reply names a shown commit {named_u}, case words only {case_u}")
print("  commits shown that are not labelled yet:", {k: sorted(v) for k, v in unl.items()} or "none")
print("\n  ---- every history output (for hand reading) ----")
for p, iid, u, r, w, nxt, later in hand:
    print(f"\n  ## {p} {iid} | useful commit shown {u}")
    print("  HISTORY:\n" + "\n".join("    " + l for l in r[r.find(A_HEAD):][:2200].splitlines()))
    print("  NEXT REPLY WORDS:\n" + "\n".join("    " + l for l in w.strip()[:1200].splitlines()))
    print("  NEXT CALLS:", [(n, (a.get("command") or json.dumps(a))[:160]) for n, a in nxt])
    if later:
        j, cmd = later[0]
        print(f"  NEXT EDIT ({j} replies later):\n" + "\n".join("    " + l for l in cmd.split("rm -f .git/agent/range")[0][:1500].splitlines()))

print("\n#### 5. where the time went: compactions, prompt size, reply length, ")
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
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$")
for a in ARMS:
    n = 0
    for d in DIRS:
        for f in glob.glob(f"{d}/results/gen/patches/*__a{a}.1.diff"):
            t = open(f, errors="replace").read()
            files = re.findall(r"^diff --git a/(\S+) b/", t, re.M)
            new = set(re.findall(r"^diff --git a/(\S+) b/\S+\nnew file", t, re.M))
            n += any(x.endswith(".py") and not TEST.search(x) and x not in new for x in files)
    print(f"  {a:5} runs that changed an existing source file: {n}")
