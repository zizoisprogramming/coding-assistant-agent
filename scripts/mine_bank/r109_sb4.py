"""r109: sb1 vs sb4 (fixer hands over after its first edit -> check stage with uses: lines) on r108's 12 tasks, 2 passes.
Checks the bars set before the run (docs/PLAN.md RUN BUILT r109). Run: python3 -I scripts/mine_bank/r109_sb4.py   (repo root; logs only)
Adds to r108_sb3.py: LIST 1 files with uses: lines, a uses-file edited (real-fix / unneeded), check re-runs a heredoc and
pytest, unneeded listed file edited on single-file tasks, fixer calls median and calls left at hand-over.
Per sb3 run: check stage reached (a request with check.md as system prompt), its first call = the history command,
LIST 1 / LIST 2 sizes from that command's output, every LIST 1 file looked at afterwards (named in a later call),
check-stage edits and which files, a LIST 1 file edited (real-fix file = useful, else unneeded), check-stage calls and
seconds, end. Also sb1 vs sb4 solves per task and pass, time, ends."""
import ast, collections, glob, json, os, re

DIRS = sorted(glob.glob("data/results/2026-11-17_skill_sb4h12_p*"))
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$")
GOLD = {json.loads(l)["instance_id"]: json.loads(l)["patch"] for l in open("data/swe_rebench/candidates.jsonl")}
GOLD.update({json.loads(l)["instance_id"]: json.loads(l)["patch"] for l in open("data/tasks.jsonl")})
CHECK = open("submissions/sb4/prompts/check.md").read()[:80]


def src(patch):
    return {f for f in re.findall(r"^\+\+\+ b/(\S+)", patch, re.M) if f.endswith(".py") and not TEST.search(f)}


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
        pf = os.path.join(d, "results/gen/patches", f"{iid}__a{g['attempt']}.diff")
        mine = open(pf, errors="replace").read() if os.path.exists(pf) else ""
        gold = src(GOLD[iid])
        row = dict(pass_=d[-2:], arm=g["arm"], iid=iid, solved=g["resolved"] in (True, "True"), patch=bool(mine.strip()),
                   end=g["end"], agent_s=float(g["agent_s"]), multi=len(gold) >= 2,
                   all_files=bool(gold) and gold <= src(mine))
        if g["arm"] == "sb4":
            toolout, seq, t_check = {}, [], None
            for r in R:
                msgs = r["request"]["messages"] if isinstance(r["request"], dict) else []
                stage = "check" if msgs and CHECK in str(msgs[0].get("content")) else "fixer"
                if stage == "check" and t_check is None:
                    t_check = float(r["t"])
                for m in msgs:
                    if m.get("role") == "tool" and m.get("tool_call_id"):
                        c = m.get("content")
                        for parse in (lambda x: x, json.loads, ast.literal_eval):  # dict, JSON text or Python repr; lists are in stdout
                            try:
                                v = parse(c)
                                if isinstance(v, dict) and "stdout" in v:
                                    c = v["stdout"]
                                    break
                            except Exception:
                                pass
                        c = str(c)
                        toolout[m["tool_call_id"]] = c
                for n, a, cid in calls(r["reply"]):
                    seq.append((stage, n, a, cid))
            ch = [(n, a, cid) for s, n, a, cid in seq if s == "check"]
            hist = [i for i, (n, a, cid) in enumerate(ch) if n == "run_command" and "check_shown" in str(a.get("command", ""))]
            out = toolout.get(ch[hist[0]][2], "") if hist else ""
            if hist and "== LIST 1" not in out:  # call ids do not always match; take the tool result that holds the lists
                out = next((v for v in toolout.values() if "== LIST 1: files" in v), out)
            l1 = re.findall(r"^(\S+\.py): changed together with", out, re.M)
            l2 = len(re.findall(r"^commit [0-9a-f]+ ", out, re.M))
            after = json.dumps([a for n, a, cid in ch[(hist[0] + 1 if hist else 0):]])
            looked = [f for f in l1 if f in after]
            ced = [str(a.get("filepath", a.get("path", ""))).replace("/workspace/", "").lstrip("./") for n, a, cid in ch if n in ("edit_file", "write_file")]
            l1_edited = [f for f in l1 if f in ced or f in src(mine)]
            blocks = re.split(r"^(?=\S+\.py: changed together with)", out.split("== LIST 2")[0], flags=re.M)
            l1u = [b.split(":")[0] for b in blocks if "changed together with" in b and "    uses: " in b]
            cmds = [str(a.get("command", "")) for n, a, cid in ch if n == "run_command"]
            rerun = any(("<<" in c and "python" in c and "pytest" in c) for c in cmds)
            rerun_any = any("<<" in c and "python" in c for c in cmds)
            pyt = any("pytest" in c for c in cmds)
            row.update(reached=bool(ch), cmd_first=bool(hist) and hist[0] == 0, cmd_ran=bool(hist), noedit_msg="No source file is edited yet" in out,
                       l1=len(l1), l2=l2, looked_all=bool(l1) and len(looked) == len(l1), check_edit=bool(ced),
                       l1_useful=bool(set(l1_edited) & gold), l1_unneeded=bool(set(l1_edited) - gold), check_calls=len(ch),
                       fixer_calls=sum(1 for s, *_ in seq if s == "fixer"), submit=any(n == "submit_patch" for n, a, cid in ch),
                       check_s=(float(R[-1]["t"]) - t_check) if t_check else 0.0, calls_left=32 - sum(1 for s_, *_ in seq if s_ == "fixer"), l1u=l1u, uses_useful=bool(set(l1u) & set(l1_edited) & gold), uses_unneeded=bool((set(l1u) & set(l1_edited)) - gold), rerun_both=rerun, rerun_heredoc=rerun_any, check_pytest=pyt, l1_files=l1, l1_edited=l1_edited, gold=sorted(gold))
        rows.append(row)

by = {a: [r for r in rows if r["arm"] == a] for a in ("sb1", "sb4")}
for a, xs in by.items():
    print(f"{a}: solved {sum(r['solved'] for r in xs)}/{len(xs)} | no patch {sum(not r['patch'] for r in xs)} | ends {dict(collections.Counter(r['end'] for r in xs))}"
          f" | mean agent {sum(r['agent_s'] for r in xs) / len(xs):.0f} s | multi-file all files {sum(r['all_files'] for r in xs if r['multi'])}/{sum(r['multi'] for r in xs)}")
s3 = by["sb4"]
reached = [r for r in s3 if r["reached"]]
print(f"\nsb4 check stage reached {len(reached)}/{len(s3)} | command first {sum(r['cmd_first'] for r in reached)}/{len(reached)} | command ran {sum(r['cmd_ran'] for r in reached)}"
      f" | 'no edit yet' {sum(r['noedit_msg'] for r in reached)} | LIST 1 non-empty {sum(r['l1'] > 0 for r in reached)} | every listed file looked at {sum(r['looked_all'] for r in reached)}/{sum(r['l1'] > 0 for r in reached)}"
      f" | check edits {sum(r['check_edit'] for r in reached)}/{len(reached)} | a listed real-fix file edited {sum(r['l1_useful'] for r in reached)} | unneeded listed file edited {sum(r['l1_unneeded'] for r in reached)}"
      f" | check submitted {sum(r['submit'] for r in reached)} | check calls mean {sum(r['check_calls'] for r in reached) / max(1, len(reached)):.1f}, seconds mean {sum(r['check_s'] for r in reached) / max(1, len(reached)):.0f}")
import statistics
fc = [r["fixer_calls"] for r in s3]
print(f"fixer calls median {statistics.median(fc)} (bar <= 18) | check reached with >= 4 calls left {sum(r['reached'] and r['calls_left'] >= 4 for r in s3)}/{len(s3)} (bar >= 80%)"
      f" | check re-ran heredoc+pytest in one call {sum(r['rerun_both'] for r in reached)}/{len(reached)}, heredoc any {sum(r['rerun_heredoc'] for r in reached)}, pytest any {sum(r['check_pytest'] for r in reached)} (bar >= 60%)")
wu = [r for r in reached if set(r["l1u"]) & set(r["gold"])]
print(f"runs whose uses-lines name a real-fix file {len(wu)}: that file edited {sum(r['uses_useful'] for r in wu)} (bar >= 50%) | uses-file edited but unneeded (all runs) {sum(r['uses_unneeded'] for r in reached)}")
sf = [r for r in reached if not r["multi"]]
print(f"single-file runs reached {len(sf)}: an unneeded listed file edited {sum(r['l1_unneeded'] for r in sf)} (bar <= 20%)")
for r in s3:
    print(f"  {r['pass_']} {r['iid'][:30]:30} {'S' if r['solved'] else ('E' if r['patch'] else '0')} end={r['end']:5} fixer {r['fixer_calls']:2} check {r['check_calls']:2} calls {r['check_s']:4.0f}s look_all={r['looked_all']!s:5} check_edit={r['check_edit']!s:5}"
          f" | L1 {r['l1_files']} L2 {r['l2']} | uses {r['l1u']} | edited from L1 {r['l1_edited']} rerun={r['rerun_heredoc']:d}{r['check_pytest']:d} | real-fix {r['gold']}")
print("\nper task (p1+p2): sb1 vs sb4")
w = l = 0
for t in sorted({r["iid"] for r in rows}):
    a = sum(r["solved"] for r in by["sb1"] if r["iid"] == t)
    b = sum(r["solved"] for r in by["sb4"] if r["iid"] == t)
    w += b > a
    l += b < a
    print(f"  {'+' if b > a else '-' if b < a else ' '} {t[:46]:46} sb1 {a}/2 sb4 {b}/2")
print(f"tasks sb4 more {w}, fewer {l}")
