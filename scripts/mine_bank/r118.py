"""r118: sb1 vs sb1h vs sb1hpp vs sb7h on r117's 12 tasks, 2 passes (docs/PLAN.md RUN BUILT r118, bars set there).
Run: python3 -I scripts/mine_bank/r118.py   (repo root; logs only)
1. outcomes per arm and per task (gen_per_task);
2. r115_pp.py's penalty measures (tokens per reply, long-reply share, ...) for the four arms + matched bank sb1 resample;
3. edit mechanics per arm, from requests.jsonl: cut-apart results ('mandatory input parameters are not present'),
   the longest run of back-to-back cut-apart results, edit_file / write_file calls and their failed results (sb1),
   heredoc edit commands (run_command with OLD_TEXT) and their results: EDITED / found 0 / found >= 2 / error / none;
4. sb7h's stage: requests, seconds, calls, calls sent inside ``` fence lines, error results, how the stage ended
   (real history pinned / 'No history' / typed call / other), the fixer naming a pinned commit before its first edit,
   the run's calls used when the fixer starts, a real-fix function among the pinned ones."""
import ast, collections, glob, json, random, re, statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIRS = sorted(glob.glob(str(ROOT / "data/results/2026-11-19_skill_r118_p*")))
ARMS = ("sb1", "sb1h", "sb1hpp", "sb7h")
TASKS = ("cta-observatory__pyirf-193", "RDFLib__pySHACL-285", "Netflix-Skunkworks__policyuniverse-147", "terryyin__lizard-144",
         "lucianopaz__compress_pickle-28", "terryyin__lizard-370", "klen__peewee_migrate-203", "hgrecco__pint-pandas-264",
         "fastapi_11194", "rich_3278", "rich_3676", "rich_3506")
solved = lambda g: g["resolved"] in (True, "True")

print("#### 1. outcomes")
G = []
for d in DIRS:
    for l in open(f"{d}/results/gen_per_task.jsonl"):
        g = json.loads(l)
        if g.get("arm") in ARMS:
            g["p"] = d[-2:]
            G.append(g)
for a in ARMS:
    A = [g for g in G if g["arm"] == a]
    print(f"  {a:7} runs {len(A):2} | solved {sum(map(solved, A)):2} | no patch {sum(not g.get('patch_chars') for g in A):2}"
          f" | ends {dict(collections.Counter(g['end'] for g in A))} | agent s mean {st.mean(g['agent_s'] for g in A):4.0f}"
          f" | tool calls mean {st.mean(g['tool_calls'] for g in A):4.1f} | by pass {[sum(solved(g) for g in A if g['p'] == p) for p in ('p1', 'p2')]}")
print("  per task (S solved, E edited no solve, 0 no patch, . not run; p1 p2):")
for t in TASKS:
    row = []
    for a in ARMS:
        cell = ""
        for p in ("p1", "p2"):
            xs = [g for g in G if g["instance_id"] == t and g["arm"] == a and g["p"] == p]
            cell += ("S" if solved(xs[0]) else ("E" if xs[0].get("patch_chars") else "0")) if xs else "."
        row.append(f"{a} {cell}")
    print(f"    {t[:34]:34} " + " | ".join(f"{r:9}" for r in row))

print("\n#### 2. penalty measures (r115_pp.py)")
src = (ROOT / "scripts/mine_bank/r115_pp.py").read_text()
ns = {}
exec(src[:src.index("new = {}")].replace('TASKS = ("rich_3521", "geopandas__geopandas-3240", "fastapi_14419", "rich_4079")', "TASKS = " + repr(TASKS)), ns)
new = {}
for d in DIRS:
    new.update(ns["load"](d, ARMS))
for a in ARMS:
    print(ns["line"](a, ns["agg"]([r for r in new.values() if r["arm"] == a])))
bank = {}
for d in sorted(glob.glob(str(ROOT / "data/results/2026-11-1*"))):
    if d not in DIRS and glob.glob(f"{d}/requests/requests.jsonl"):
        try:
            bank.update(ns["load"](d, ("sb1",)))
        except Exception as e:
            print("skip", d, e)
B = collections.defaultdict(list)
for r in bank.values():
    B[r["task"]].append(r)
print("  bank sb1 runs per task:", {t[:14]: len(B[t]) for t in TASKS})
random.seed(0)
for a in ARMS:
    rs = [r for r in new.values() if r["arm"] == a and B[r["task"]]]
    sims = [ns["agg"]([random.choice(B[r["task"]]) for r in rs]) for _ in range(10000)]
    x = ns["agg"](rs)
    cells = []
    for m in ("tok", "long", "time", "nop", "solved", "agent"):
        v = sorted(s[m] for s in sims)
        cells.append(f"{m} {x[m]:.1f} [{v[len(v) // 20]:.1f}, {v[-len(v) // 20]:.1f}] p<= {sum(y <= x[m] for y in v) / len(v):.2f}")
    print(f"  {a:7} vs bank sb1 on the same tasks ({len(rs)} runs): " + " | ".join(cells))


def calls_of(reply):
    """(name, arguments-string) of each tool call in a reply; [] for a text reply."""
    try:
        d = ast.literal_eval(reply)
        return [(c["function"]["name"], c["function"]["arguments"]) for c in (d.get("message") or {}).get("tool_calls") or []]
    except Exception:
        return [(m.group(1), "") for m in re.finditer(r"'name': '(\w+)'", reply)]


def text_of(reply):
    try:
        return ((ast.literal_eval(reply).get("message") or {}).get("content")) or ""
    except Exception:
        return ""


R = collections.defaultdict(list)
for d in DIRS:
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        try:
            r = json.loads(l)
        except Exception:
            continue
        msgs = r["request"]["messages"]
        k = len(msgs)
        while k > 0 and msgs[k - 1].get("role") == "tool":
            k -= 1
        R[(d[-2:], r["job"])].append(dict(t=float(r["t"]), s=float(r.get("seconds") or 0), sys=msgs[0]["content"],
                                           tools=[str(m.get("content")) for m in msgs[k:]], reply=str(r["reply"])))
for v in R.values():
    v.sort(key=lambda x: x["t"])

print("\n#### 3. edit mechanics (per run means; % of heredoc edit results)")
CUT = "mandatory input parameters are not present"
OLDFAIL = re.compile(r"old_string not found|occurs \d+ times|flexibly match")
E = collections.defaultdict(list)
for (p, job), rs in R.items():
    arm = job.split("#a")[1].split(".")[0]
    if arm not in ARMS:
        continue
    cut = run = longest = 0
    ef = ef_fail = hd = 0
    res = collections.Counter()
    pending = 0
    for x in rs:
        for tc in x["tools"]:
            if CUT in tc:
                cut += 1
                run += 1
                longest = max(longest, run)
            else:
                run = 0
            ef_fail += bool(OLDFAIL.search(tc))
            if pending:
                if "EDITED " in tc:
                    res["edited"] += 1
                elif re.search(r"old text found 0 times", tc):
                    res["found0"] += 1
                elif re.search(r"old text found ([2-9]|\d\d+) times", tc):
                    res["found2+"] += 1
                elif CUT in tc:
                    res["cut"] += 1
                elif '"status": "error"' in tc:
                    res["error"] += 1
                else:
                    res["other"] += 1
                pending -= 1
        pending = 0
        for name, args in calls_of(x["reply"]):
            if name in ("edit_file", "write_file"):
                ef += 1
            if name == "run_command" and "OLD_TEXT" in args:
                hd += 1
                pending += 1
    E[arm].append(dict(cut=cut, longest=longest, ef=ef, ef_fail=ef_fail, hd=hd, res=res))
for a in ARMS:
    xs = E[a]
    n = len(xs)
    res = sum((x["res"] for x in xs), collections.Counter())
    tot = sum(res.values())
    print(f"  {a:7} runs {n:2} | cut-apart results/run {sum(x['cut'] for x in xs) / n:4.2f} (runs with any {sum(x['cut'] > 0 for x in xs):2},"
          f" longest loop {max(x['longest'] for x in xs):2}) | edit_file+write_file calls/run {sum(x['ef'] for x in xs) / n:4.1f}, failed results/run"
          f" {sum(x['ef_fail'] for x in xs) / n:4.2f} | heredoc edits/run {sum(x['hd'] for x in xs) / n:4.1f}: "
          + (", ".join(f"{k} {v} ({100 * v / tot:.0f}%)" for k, v in res.most_common()) if tot else "none"))

print("\n#### 4. sb7h stage and fixer")
H_KEY, F_KEY = "You fetch the history of the code this issue is about", "# THE HISTORY IS FETCHED"
s16 = (ROOT / "scripts/mine_bank/r116_sb7f.py").read_text()
ns16 = {}
exec(s16[:s16.index("rows = []")].replace("DIRS = sorted(glob.glob(sys.argv[1]))", "DIRS = []"), ns16)
rows = []
for (p, job), rs in sorted(R.items()):
    if "#asb7h." not in job:
        continue
    iid = job.split("#")[0]
    H = [x for x in rs if x["sys"].startswith(H_KEY)]
    F = [x for x in rs if x["sys"].startswith("You are an autonomous") and F_KEY in x["sys"]]
    hc = [c for x in H for c in calls_of(x["reply"]) if c[0] == "run_command"]
    fenced = sum(a.lstrip().startswith('{"command": "```') for _, a in hc)
    errs = sum('"status": "error"' in tc for x in H for tc in x["tools"])
    cuts = sum(CUT in tc for x in H for tc in x["tools"])
    pinned = F[0]["sys"].split("each with its title (why) and its diff (how):\n", 1)[-1].split("\n\nThe history is fetched and you have all")[0] if F else ""
    if re.search(r"^commit [0-9a-f]{7,}", pinned, re.M):
        kind = "history"
    elif pinned.strip().lower().rstrip(".") == "no history":
        kind = "no history"
    elif re.search(r"tool: run_command|command:|names=|<\|tool_call>|call:run_command", pinned):
        kind = "typed call"
    else:
        kind = "other: " + pinned.strip()[:60].replace("\n", " | ")
    used = None
    for x in F[:3]:
        m = re.search(r"\((\d+)/32 used\)", " ".join(x["tools"]) + x["sys"][-3000:])
        if m:
            used = int(m.group(1))
            break
    hashes = re.findall(r"^commit ([0-9a-f]{7,})", pinned, re.M)
    named, first_edit = 0, None
    for k, x in enumerate(F):
        if any(n == "run_command" and ("OLD_TEXT" in a or "NEW_TEXT" in a) for n, a in calls_of(x["reply"])):
            first_edit = k
            break
        if any(h[:7] in x["reply"] for h in hashes):
            named += 1
    pf = set(re.findall(r"^== (\S+) (\w+)", pinned, re.M))
    gf = ns16["gold_funcs"](ns16["GOLD"].get(iid, ""))
    g = [y for y in G if y["instance_id"] == iid and y["arm"] == "sb7h" and y["p"] == p]
    rows.append(dict(p=p, iid=iid, hreq=len(H), hs=sum(x["s"] for x in H), calls=len(hc), fenced=fenced, errs=errs, cuts=cuts, kind=kind,
                     used=used, named=named, first_edit=first_edit, hit=bool(pf & gf), pf=pf, chars=len(pinned),
                     solved=bool(g and solved(g[0])), freq=len(F)))
for r in rows:
    print(f"  {r['p']} {r['iid'][:28]:28} {'S' if r['solved'] else '-'} | stage req {r['hreq']:2} {r['hs']:4.0f}s calls {r['calls']:2} fenced {r['fenced']:2}"
          f" errors {r['errs']:2} cut {r['cuts']} | {r['kind'][:40]:40} {r['chars']:4} ch | real-fix fn {'Y' if r['hit'] else '-'}"
          f" | fixer: calls used at start {r['used']}, names a commit before edit {r['named']} (first edit reply {r['first_edit']})")
n = len(rows)
print(f"\n  sb7h runs {n} | stage <= 2 requests {sum(r['hreq'] <= 2 for r in rows)} | stage s mean {st.mean(r['hs'] for r in rows):.0f}"
      f" | runs with a fenced call {sum(r['fenced'] > 0 for r in rows)} (fenced calls {sum(r['fenced'] for r in rows)} of {sum(r['calls'] for r in rows)})"
      f" | runs with stage errors {sum(r['errs'] > 0 for r in rows)} | stage ended with {dict(collections.Counter(r['kind'].split(':')[0] for r in rows))}"
      f" | real-fix fn pinned {sum(r['hit'] for r in rows)} | fixer named a commit before its first edit {sum(r['named'] > 0 for r in rows)}"
      f" | calls used at fixer start mean {st.mean([r['used'] for r in rows if r['used'] is not None] or [0]):.1f}")
