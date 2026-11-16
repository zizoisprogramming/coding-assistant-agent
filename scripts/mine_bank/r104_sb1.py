"""r104: sa2 vs sb1 on the 24 test tasks, 2 passes (data/results/2026-11-16_skill_sb1rt_p1, _p2). Checks every bar set
before the run (docs/PLAN.md RUN BUILT r104):
  mechanism: sb1 runs git log / git show in >= 30% of runs; reads a test file before the first edit and runs pytest
             after the last edit in >= 40%; garbled edits ('mandatory input parameters are not present') not above sa2's;
  outcome:   on the 9 multi-file tasks every real-fix source file covered in >= 3 of 18 sb1 runs; solves vs sa2
             (+-4 over ~48 pairs is luck; a submission candidate needs >= +5, or >= +3 with the mechanism bars passed);
  time:      mean agent time <= sa2's + 20 s.
Also: why runs end with no patch (edited then reverted? never edited? time / budget end?), signature changes beyond the
real fix, the same heredoc re-run after the edit, per-task paired solves.
Run: python3 -I scripts/mine_bank/r104_sb1.py [FOLDER_GLOB ARM_A ARM_B]   (repo root; reads logs only, no repository code runs)
r105 / r107 (sb1 vs sb2): python3 -I scripts/mine_bank/r104_sb1.py 'data/results/2026-11-16_skill_sb2*_p*' sb1 sb2
Extra for a history stage (sb2): its command is the first tool call (hist_first), its output names a real-fix file
(hist_gold), the fixer runs git show (fix_show), the patch edits a file the history output listed beyond the files the
name matched (used_cochange)."""
import ast, collections, glob, json, os, re, sys

DIRS = sorted(glob.glob(sys.argv[1] if len(sys.argv) > 1 else "data/results/2026-11-16_skill_sb1rt_p*"))
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$")
GOLD = {json.loads(l)["instance_id"]: json.loads(l) for l in open("data/swe_rebench/candidates.jsonl")}


def src_files(patch):
    return {f for f in re.findall(r"^\+\+\+ b/(\S+)", patch, re.M) if not TEST.search(f)}


def def_changes(patch):
    """def lines removed (signature changed or function removed), source files only."""
    n, f = 0, None
    for line in patch.splitlines():
        m = re.match(r"^\+\+\+ b/(\S+)", line)
        if m:
            f = m.group(1)
        elif f and not TEST.search(f) and re.match(r"^-\s*(async\s+)?def ", line):
            n += 1
    return n


def calls(rep):
    if isinstance(rep, str):
        try:
            rep = ast.literal_eval(rep)
        except Exception:
            return []
    m = (rep or {}).get("message") or {}
    tc = m.get("tool_calls") or []
    if isinstance(tc, str):
        try:
            tc = ast.literal_eval(tc)
        except Exception:
            return []
    out = []
    for c in tc:
        f = c.get("function", {})
        a = f.get("arguments", "")
        try:
            a = json.loads(a) if isinstance(a, str) else a
        except Exception:
            a = {"_raw": a}
        out.append((f.get("name"), a if isinstance(a, dict) else {"_raw": a}, c.get("id")))
    return out


rows = []
for d in DIRS:
    res = {}
    for l in open(os.path.join(d, "results/gen_per_task.jsonl")):
        g = json.loads(l)
        res[g["instance_id"] + "#a" + g["attempt"]] = g
    seqs = collections.defaultdict(list)
    for l in open(os.path.join(d, "requests/requests.jsonl"), errors="replace"):
        r = json.loads(l)
        if r.get("job") in res:
            seqs[r["job"]].append(r)
    for job, g in res.items():
        R = sorted(seqs.get(job, []), key=lambda r: float(r["t"]))
        iid = g["instance_id"]
        seq, toolout = [], {}
        for r in R:
            for m in r["request"]["messages"] if isinstance(r["request"], dict) else []:
                if m.get("role") == "tool" and m.get("tool_call_id"):
                    toolout[m["tool_call_id"]] = str(m.get("content"))
            sysm = str((r["request"]["messages"] or [{}])[0].get("content", ""))[:300].lower()
            if "summar" in sysm and "conversation" in sysm:
                continue
            seq.extend(calls(r["reply"]))
        cmd = lambda a: str(a.get("command", ""))
        path = lambda a: str(a.get("filepath", a.get("path", ""))).replace("/workspace/", "").lstrip("./")
        ed = [i for i, (n, a, _) in enumerate(seq) if n in ("edit_file", "write_file") and not path(a).startswith("tmp")]
        fe = ed[0] if ed else len(seq)
        le = ed[-1] if ed else -1
        heredocs = [(i, cmd(a)) for i, (n, a, _) in enumerate(seq) if n == "run_command" and re.search(r"python3? +- *<<", cmd(a))]
        test_read = set()
        for i, (n, a, _) in enumerate(seq[:fe]):
            if n == "read_file" and TEST.search(path(a)):
                test_read.add(path(a))
            if n == "run_command":
                for m in re.finditer(r"(?:cat|sed -n \S+|head(?: -n? ?\d+)?|grep [^|]*?) +(\S*tests?/\S+\.py|\S*test_\w+\.py)", cmd(a)):
                    test_read.add(m.group(1).lstrip("./"))
        pytest_after = [cmd(a) for i, (n, a, _) in enumerate(seq) if n == "run_command" and i > le >= 0 and re.search(r"pytest|unittest", cmd(a))]
        pfile = os.path.join(d, "results/gen/patches", f"{iid}__a{g['attempt']}.diff")
        mine = open(pfile, errors="replace").read() if os.path.exists(pfile) else ""
        gold = GOLD[iid]["patch"]
        hist_i = [i for i, (n, a, cid) in enumerate(seq) if n == "run_command" and "history_shown" in cmd(a)]
        hout = toolout.get(seq[hist_i[0]][2], "") if hist_i else ""
        hfiles = set(re.findall(r"^\s*\d+ (\S+)$", hout, re.M))
        starts = set(re.findall(r"^== (\S+): files changed", hout, re.M))
        garbled = sum("mandatory input parameters are not present" in toolout.get(cid, "") for n, a, cid in seq if n in ("edit_file", "write_file"))
        rows.append(dict(
            pass_=d[-2:], arm=g["arm"], iid=iid, solved=g["resolved"] in (True, "True"), patch=bool(mine.strip()),
            end=g["end"], agent_s=float(g["agent_s"]), calls=len(seq), edited=bool(ed), first_edit=fe,
            git_hist=any(n == "run_command" and re.search(r"git (log|show|blame)", cmd(a)) for n, a, _ in seq),
            full_diff=any(n == "run_command" and "--full-diff" in cmd(a) for n, a, _ in seq),
            show_stat=any(n == "run_command" and re.search(r"git show --stat", cmd(a)) for n, a, _ in seq),
            test_grep=any(n == "run_command" and re.search(r"git grep -l\w* .*test", cmd(a)) for n, a, _ in seq),
            read_test=bool(test_read), pytest_after=bool(pytest_after),
            read_then_run=bool(test_read) and any(any(t.split("/")[-1] in c for t in test_read) for c in pytest_after),
            rerun_same=any(c == c2 for i, c in heredocs if i < fe for j, c2 in heredocs if j > le >= 0),
            heredoc_after=any(i > le >= 0 for i, _ in heredocs),
            garbled=garbled,
            revert=any(n == "run_command" and re.search(r"git (checkout|restore|stash|reset)", cmd(a)) for i, (n, a, _) in enumerate(seq) if i > fe),
            multi=len(src_files(gold)) >= 2, all_files=bool(src_files(gold)) and src_files(gold) <= src_files(mine),
            extra_defs=def_changes(mine) > def_changes(gold),
            hist_first=bool(hist_i) and hist_i[0] == 0, hist_runs=len(hist_i),
            hist_gold=any(f in hout for f in src_files(gold)),
            fix_show=any(n == "run_command" and "git show" in cmd(a) for i, (n, a, _) in enumerate(seq) if i not in hist_i),
            used_cochange=bool((src_files(mine) & hfiles) - starts),
        ))

arms = sys.argv[2:4] if len(sys.argv) > 3 else ["sa2", "sb1"]
by = {a: [r for r in rows if r["arm"] == a] for a in arms}
pct = lambda xs, k: f"{sum(r[k] for r in xs):3d}/{len(xs):2d} ({100 * sum(r[k] for r in xs) / max(1, len(xs)):3.0f}%)"
print("runs", {a: len(by[a]) for a in arms}, "| passes", sorted({r["pass_"] for r in rows}))
for k in ["solved", "patch", "edited", "git_hist", "full_diff", "show_stat", "test_grep", "read_test", "pytest_after",
          "read_then_run", "heredoc_after", "rerun_same", "revert", "extra_defs", "hist_first", "hist_gold", "fix_show", "used_cochange"]:
    print(f"  {k:14}", " | ".join(f"{a} {pct(by[a], k)}" for a in arms))
for a in arms:
    xs = by[a]
    print(f"  {a}: garbled edits {sum(r['garbled'] for r in xs)} in {sum(r['garbled'] > 0 for r in xs)} runs | ends {dict(collections.Counter(r['end'] for r in xs))}"
          f" | mean agent {sum(r['agent_s'] for r in xs) / len(xs):.0f} s | median first edit {sorted(r['first_edit'] for r in xs)[len(xs) // 2]}")
    m = [r for r in xs if r["multi"]]
    print(f"     multi-file tasks: all real-fix files covered {sum(r['all_files'] for r in m)}/{len(m)}, solved {sum(r['solved'] for r in m)}/{len(m)}")
    np_ = [r for r in xs if not r["patch"]]
    print(f"     no patch {len(np_)}: " + "; ".join(f"{r['iid'].split('__')[1]} p{r['pass_'][-1]} edited={r['edited']} revert={r['revert']} end={r['end']} calls={r['calls']}" for r in np_))

print(f"\nper task: solves {arms[0]} vs {arms[1]} (out of the runs each arm has)")
tasks = sorted({r["iid"] for r in rows})
wins = losses = 0
for t in tasks:
    s = {a: [r["solved"] for r in by[a] if r["iid"] == t] for a in arms}
    da, db = sum(s[arms[0]]) / max(1, len(s[arms[0]])), sum(s[arms[1]]) / max(1, len(s[arms[1]]))
    wins += db > da
    losses += db < da
    mark = "+" if db > da else ("-" if db < da else " ")
    print(f"  {mark} {t[:52]:52} " + "  ".join(f"{a} {sum(s[a])}/{len(s[a])}" for a in arms))
print(f"tasks where {arms[1]} solved more: {wins}, fewer: {losses}")

# solved by history / test mechanism within sb1
for k in ["git_hist", "read_then_run", "rerun_same", "pytest_after"]:
    for a in arms:
        w = [r for r in by[a] if r[k]]
        wo = [r for r in by[a] if not r[k]]
        print(f"  {a} {k:14} with: solved {sum(r['solved'] for r in w)}/{len(w)}   without: {sum(r['solved'] for r in wo)}/{len(wo)}")
