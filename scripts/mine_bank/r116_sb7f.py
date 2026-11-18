"""r116: sb1 vs sb7f (two-call function-history stage, pinned into the fixer). Checks the stage and fixer bars set before
the run (docs/PLAN.md RUN BUILT r116). Run: python3 -I scripts/mine_bank/r116_sb7f.py 'data/results/2026-11-18_skill_sb7fh4_p*'
(repo root; logs only). r113_sb78.py gives outcomes per run; its 'real-fix file / near' columns parse sb7's '== FILE:LINE'
header and do not apply to sb7f's '== FILE FUNCTION'.
Per sb7f run: history-stage requests / tool calls / seconds, first call wrapped in a ``` fence, bash errors in the stage,
calls made after the first HISTORY DONE output, a restart of the stage after compaction, the run's tool calls used when
the fixer starts (budget_warning), pinned functions vs the real-fix functions (git hunk headers + defs on changed lines
of the real patch), commit titles pinned, fixer replies before its first edit that name a pinned commit hash."""
import collections, glob, json, re, sys

DIRS = sorted(glob.glob(sys.argv[1]))
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$")
GOLD = {}
for f in ("data/swe_rebench/candidates.jsonl", "data/tasks.jsonl"):
    for l in open(f):
        j = json.loads(l)
        GOLD[j["instance_id"]] = j["patch"]
H_KEY, F_KEY = "You run two commands before the engineer starts", "# HOW THE FUNCTIONS OF THIS ISSUE CHANGED BEFORE"


def gold_funcs(p):
    out, f = set(), None
    for l in p.splitlines():
        m = re.match(r"^\+\+\+ b/(\S+)", l)
        if m:
            f = m.group(1) if m.group(1).endswith(".py") and not TEST.search(m.group(1)) else None
            continue
        if f is None:
            continue
        m = re.match(r"^@@ .*? @@\s*(?:async\s+)?(?:def|class)\s+(\w+)", l)
        if m:
            out.add((f, m.group(1)))
        m = re.match(r"^[-+ ]\s*(?:async\s+)?def\s+(\w+)", l)
        if m:
            out.add((f, m.group(1)))
    return out


rows = []
for d in DIRS:
    R = collections.defaultdict(list)
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        r = json.loads(l)
        if "#asb7f." in r["job"]:
            R[r["job"]].append((float(r["t"]), float(r.get("seconds") or 0), r["request"]["messages"], str(r["reply"])))
    for job, rs in sorted(R.items()):
        rs.sort(key=lambda x: x[0])
        iid = job.split("#")[0]
        H = [x for x in rs if x[2][0]["content"].startswith(H_KEY)]
        F = [x for x in rs if x[2][0]["content"].startswith("You are an autonomous") and F_KEY in x[2][0]["content"]]
        calls = [x for x in H if "'name': 'run_command'" in x[3]]
        fence = H[0][3].find("'arguments': '{\"command\": \"```") >= 0 if H else False
        errs = sum('"status": "error"' in str(x[2][-1].get("content")) for x in H if x[2][-1].get("role") == "tool")
        after_done, seen_done = 0, False
        for x in H:
            if seen_done and "'name': 'run_command'" in x[3]:
                after_done += 1
            if x[2][-1].get("role") == "tool" and "HISTORY DONE" in str(x[2][-1].get("content")):
                seen_done = True
        restart = sum(1 for x in H if len(x[2]) <= 2) > 1  # the stage began again from its first message
        used = None
        if F:
            for x in F[:3]:
                m = re.search(r"\((\d+)/28 used\)", json.dumps(x[2][-3:]))
                if m:
                    used = int(m.group(1))
        sysF = F[0][2][0]["content"] if F else ""
        pinned = sysF.split("Each commit's title says why, its diff says how:\n", 1)[-1].split("\n\n# SOLVE IT WITH")[0] if F else ""
        pf = set(re.findall(r"^== (\S+) (\w+)", pinned, re.M))
        gf = gold_funcs(GOLD.get(iid, ""))
        hashes = re.findall(r"^commit ([0-9a-f]{7,})", pinned, re.M)
        titles = re.findall(r"^commit [0-9a-f]{7,} \S+ (.{0,60})", pinned, re.M)
        named, first_edit = 0, None
        for k, x in enumerate(F):
            if re.search(r"'name': '(edit_file|write_file)'", x[3]) and "filepath': 'tests" not in x[3]:
                first_edit = k
                break
            if any(h[:7] in x[3] for h in hashes):
                named += 1
        rows.append(dict(p=d[-2:], iid=iid, hreq=len(H), hcalls=len(calls), hs=sum(x[1] for x in H), fence=fence, errs=errs,
                         after_done=after_done, restart=restart, used=used, pf=pf, gf=gf, hit=bool(pf & gf),
                         titles=titles, named=named, first_edit=first_edit, freq=len(F)))

for r in rows:
    print(f"{r['p']} {r['iid'][:26]:26} stage req {r['hreq']:2} calls {r['hcalls']:2} {r['hs']:4.0f}s | fence {str(r['fence']):5} errors {r['errs']:2}"
          f" calls after DONE {r['after_done']} restart {str(r['restart']):5} | run calls used when fixer starts {r['used']}"
          f" | pinned {sorted(f'{a}:{b}' for a, b in r['pf'])} real-fix fn {'YES' if r['hit'] else 'no'} | fixer names a commit in {r['named']} replies before edit (first edit reply {r['first_edit']})")
    print(f"     real-fix functions {sorted(f'{a}:{b}' for a, b in r['gf'])[:4]} | titles {r['titles'][:5]}")
n = len(rows)
print(f"\nsb7f runs {n} | stage ended after its two calls (<= 3 requests) {sum(r['hreq'] <= 3 for r in rows)} | stage s mean {sum(r['hs'] for r in rows) / n:.0f}"
      f" | first call fenced {sum(r['fence'] for r in rows)} | runs with stage bash errors {sum(r['errs'] > 0 for r in rows)}"
      f" | calls after DONE in {sum(r['after_done'] > 0 for r in rows)} runs | pinned a real-fix function {sum(r['hit'] for r in rows)}"
      f" | fixer named a commit before its first edit in {sum(r['named'] > 0 for r in rows)} runs")
