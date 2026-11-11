"""Evidence-stage reads (evid3 / evid4 / evidc): per run, the names the stage chose, whether the script's output and the
stage's reply reach the gold patch's files / functions, whether the reply was empty, and the fixer's outcome. Also, per
task, which identifiers from the issue text appear in the gold patch (names a better choice could have used).
Usage: python3 -I scripts/mine_bank/evidence_reads.py [--runs] FOLDER...   (run from the repo root)"""
import collections, json, re, sys

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
SHOW_RUNS = "--runs" in sys.argv
STAGE = "Your only job is one search of the repository"
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$")
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")
TASKS = {}
for l in open("data/tasks.jsonl"):
    r = json.loads(l); TASKS[r["instance_id"]] = r


def gold(task):
    """files, enclosing functions (hunk headers), identifiers on changed lines of the gold source patch."""
    files, funcs, idents, cur = [], set(), set(), None
    for ln in TASKS[task]["patch"].splitlines():
        if ln.startswith("+++ b/"):
            cur = ln[6:]
            if not TEST.search(cur): files.append(cur)
        elif ln.startswith("@@") and cur and not TEST.search(cur):
            m = re.search(r"@@.*@@\s*(?:async\s+)?(?:def|class)\s+([A-Za-z_][A-Za-z0-9_]*)", ln)
            if m: funcs.add(m.group(1))
        elif ln[:1] in "+-" and not ln.startswith(("+++", "---")) and cur and not TEST.search(cur):
            idents.update(IDENT.findall(ln))
    return files, funcs, idents


def issue_names(task):
    """identifiers in the issue that look like code: backticked, snake_case, CamelCase, dotted, or called()."""
    t = TASKS[task]["problem_statement"]
    out = set()
    for m in re.findall(r"`([^`\n]{2,80})`", t): out.update(IDENT.findall(m))
    out.update(m for m in IDENT.findall(t) if "_" in m.strip("_") or re.search(r"[a-z][A-Z]", m))
    out.update(re.findall(r"([A-Za-z_][A-Za-z0-9_]{2,})\(", t))
    out.update(p for m in re.findall(r"\b\w+(?:\.\w+)+\b", t) for p in m.split(".") if len(p) >= 3)
    return out


rows = []
for D in ARGS:
    J = collections.defaultdict(list)
    for l in open(D + "/requests/requests.jsonl"):
        r = json.loads(l)
        if isinstance(r.get("reply"), dict) and r.get("job"): J[r["job"]].append(r)
    res = {}
    try:
        for l in open(D + "/results/digest.jsonl"):
            r = json.loads(l); res[r["job"]] = r
    except FileNotFoundError:
        pass
    for job, q in sorted(J.items()):
        q = sorted(q, key=lambda r: r["t"])
        st = [r for r in q if STAGE in str(r["request"]["messages"][0].get("content") or "")[:300]]
        if not st: continue
        task = job.partition("#a")[0]; arm = job.partition("#a")[2].split(".")[0]
        names, out, nstage_calls = [], "", 0
        R = {}
        for r in st:
            for m in r["request"]["messages"]:
                if m.get("role") == "tool": R.setdefault(m.get("tool_call_id"), str(m.get("content")))
        # the tool result of the last stage call is only in the next request (the fixer's or the stage's own)
        for r in q:
            for m in r["request"]["messages"]:
                if m.get("role") == "tool": R.setdefault(m.get("tool_call_id"), str(m.get("content")))
        for r in st:
            for c in r["reply"]["message"].get("tool_calls") or []:
                nstage_calls += 1
                try: a = json.loads(c["function"]["arguments"])
                except Exception: a = {}
                if c["function"]["name"] == "run_skill_script" and not names:
                    pa = a.get("positional_args") or a.get("args") or []
                    names = [str(x) for x in (pa if isinstance(pa, list) else [pa])]
                    out = R.get(c.get("id"), "")
        reply = ""
        for r in q:
            s = str(r["request"]["messages"][0].get("content") or "")
            if "# REPOSITORY EVIDENCE (found" in s:
                reply = s.split("# REPOSITORY EVIDENCE (found", 1)[1].split("\n", 2)[-1]
                reply = reply.split("\n", 1)[1] if reply.startswith("Lines copied") else reply
                reply = reply.strip(); break
        if not reply:  # stage reply text as a fallback
            reply = str(st[-1]["reply"]["message"].get("content") or "").strip()
        files, funcs, idents = gold(task)
        base = lambda f: f.rsplit("/", 1)[-1]
        out_file = any(f in out or base(f) in out for f in files)
        rep_file = any(f in reply or base(f) in reply for f in files)
        rep_func = any(re.search(rf"\b{re.escape(fn)}\b", reply) for fn in funcs)
        hit_names = [n for n in names if n in funcs or n in idents]
        stage_s = (next((r["t"] for r in q if r not in st), q[-1]["t"]) - q[0]["t"])
        d = res.get(job, {})
        rlines = [l for l in reply.splitlines() if l.strip()]
        empty = (not rlines) or reply.strip().upper().startswith("NOTHING RELEVANT") or len(rlines) <= 1
        rows.append(dict(folder=D.rsplit("/", 1)[-1], job=job, task=task, arm=arm, names=names, hit_names=hit_names,
                         out_chars=len(out), out_file=out_file, rep_file=rep_file, rep_func=rep_func, empty=empty,
                         rep_lines=len(rlines), stage_s=round(stage_s), stage_calls=nstage_calls,
                         resolved=d.get("resolved"), done_in=(re.findall(r"\[done in (\d+) s\]", out) or ["?"])[0],
                         skipped=("skipped: time" in out), gold_files=files, gold_funcs=sorted(funcs), reply=reply, out=out))

if SHOW_RUNS:
    for r in rows:
        print(f"\n### {r['job']} [{r['folder']}] resolved={r['resolved']} stage {r['stage_s']} s, {r['stage_calls']} calls, script {r['done_in']} s{' TIME-CUT' if r['skipped'] else ''}")
        print(f"  gold files {r['gold_files']} funcs {r['gold_funcs']}")
        print(f"  names {r['names']} -> in gold patch: {r['hit_names']}")
        print(f"  script output reaches gold file: {r['out_file']} | reply reaches gold file: {r['rep_file']}, gold func: {r['rep_func']} | reply lines {r['rep_lines']}{' EMPTY' if r['empty'] else ''}")
        for l in r["reply"].splitlines()[:12]: print("   | " + l[:160])

print("\n== by arm")
for arm in sorted({r["arm"] for r in rows}):
    x = [r for r in rows if r["arm"] == arm]
    n = len(x)
    f = lambda k: sum(1 for r in x if r[k])
    print(f"{arm:7s} runs {n} | names hit gold patch {sum(1 for r in x if r['hit_names'])}/{n} | output reaches gold file {f('out_file')}/{n}"
          f" | reply reaches gold file {f('rep_file')}/{n}, gold func {f('rep_func')}/{n} | empty reply {f('empty')}/{n} | time-cut {f('skipped')}/{n}"
          f" | resolved {sum(1 for r in x if r['resolved'])}/{sum(1 for r in x if r['resolved'] is not None)}")
    for k, lab in (("rep_file", "reply reaches gold file"), ("empty", "empty reply")):
        a = [r for r in x if r[k] and r["resolved"] is not None]; b = [r for r in x if not r[k] and r["resolved"] is not None]
        print(f"    {lab}: resolved {sum(r['resolved'] for r in a)}/{len(a)} vs not: {sum(r['resolved'] for r in b)}/{len(b)}")

print("\n== by task (all arms): runs, names hitting gold, reply reaching gold file, empty, resolved | issue names that are in the gold patch")
for t in sorted({r["task"] for r in rows}):
    x = [r for r in rows if r["task"] == t]
    files, funcs, idents = gold(t)
    good = sorted(n for n in issue_names(t) if n in funcs or n in idents)
    chosen = collections.Counter(n for r in x for n in r["names"])
    print(f"{t:15s} n={len(x):2d} hit={sum(1 for r in x if r['hit_names']):2d} reply_file={sum(r['rep_file'] for r in x):2d} empty={sum(r['empty'] for r in x):2d}"
          f" solved={sum(1 for r in x if r['resolved'])} | gold {files} {sorted(funcs)}")
    print(f"{'':15s} issue names in gold: {good[:12]}")
    print(f"{'':15s} chosen: {dict(chosen.most_common(8))}")
