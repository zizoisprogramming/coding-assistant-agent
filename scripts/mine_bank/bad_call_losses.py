"""Which agents lose the most to bad tool calls (MINING 2026-11-11c). Per run (31B, folders with request logs + outcomes):
the run ended with NO patch and a bad call explains it:
  budget_edit   an edit_file / write_file refused with 'Tool call budget exhausted' and no working source edit before it
  garble_end    a garbled edit ('mandatory input parameters are not present') and no working source edit after it
  text_end      the agent's last reply was a tool call written as text (never ran)
Lost solves (estimate): each such run counts the task's solve rate among runs of any arm that DID make a patch
(how often a patch on this task is right). Usage: python3 -I scripts/mine_bank/bad_call_losses.py [MIN_RUNS]"""
import collections, glob, importlib.util, json, os, re, sys

spec = importlib.util.spec_from_file_location("bc", os.path.join(os.path.dirname(os.path.abspath(__file__)), "bad_calls.py"))
bc = importlib.util.module_from_spec(spec); spec.loader.exec_module(bc)
MIN_RUNS = int(sys.argv[1]) if len(sys.argv) > 1 else 16
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$")

runs = []
for D in sorted(glob.glob("data/results/2026-*")):
    if any(k in D for k in ("e4b", "probe", "replay", "12b")):
        continue
    rq, gp = D + "/requests/requests.jsonl", D + "/results/gen_per_task.jsonl"
    if not (os.path.exists(rq) and os.path.exists(gp)):
        continue
    out = {}
    for l in open(gp):
        try: r = json.loads(l)
        except Exception: continue
        out[f"{r['instance_id']}#a{r['attempt']}"] = r
    res_of, jobs = {}, collections.defaultdict(list)
    for l in open(rq):
        try: r = json.loads(l)
        except Exception: continue
        if not (isinstance(r.get("reply"), dict) and r.get("job")): continue
        if r["request"].get("model") and "31b" not in str(r["request"]["model"]): continue
        for m in r["request"]["messages"]:
            if m.get("role") == "tool": res_of.setdefault(m.get("tool_call_id"), str(m.get("content")))
        jobs[r["job"]].append(r)
    for job, q in jobs.items():
        o = out.get(job)
        if not o: continue
        q.sort(key=lambda r: r["t"])
        worked = False; budget_edit = False; garble_open = False; last_text_call = False
        for r in q:
            msg = r["reply"]["message"]; calls = msg.get("tool_calls") or []
            if not calls:
                last_text_call = bool(bc.TEXT_CALL.search(str(msg.get("content") or "")))
                continue
            last_text_call = False
            for c in calls:
                name = c["function"]["name"]; res = res_of.get(c.get("id"), "")
                try: a = json.loads(c["function"].get("arguments") or "{}")
                except Exception: a = {}
                k = bc.kind_of(name, c["function"].get("arguments") or "", res, "")
                is_edit = name in ("edit_file", "write_file")
                if is_edit and k == "after_budget" and not worked: budget_edit = True
                if k == "garbled_args": garble_open = True
                fp = str(a.get("filepath") or "")
                if is_edit and '"status": "ok"' in res[:30] and fp and not TEST.search(fp) and not fp.startswith(("/tmp", ".git")):
                    worked = True; garble_open = False
        nopatch = not o.get("patch_chars")
        cause = None
        if nopatch:
            cause = "budget_edit" if budget_edit else "garble_end" if garble_open else "text_end" if last_text_call else None
        runs.append(dict(arm=o.get("arm") or job.partition("#a")[2].rsplit(".", 1)[0], task=o["instance_id"], resolved=bool(o.get("resolved")),
                         nopatch=nopatch, cause=cause, folder=D.rsplit("/", 1)[1]))

# task: how often a patch is right
pt = collections.defaultdict(lambda: [0, 0])
for r in runs:
    if not r["nopatch"]:
        pt[r["task"]][0] += r["resolved"]; pt[r["task"]][1] += 1
rate = {t: a / b for t, (a, b) in pt.items() if b}
A = collections.defaultdict(list)
for r in runs: A[r["arm"]].append(r)
print(f"{len(runs)} runs with outcomes. Columns: runs, solved, no patch, no-patch runs explained by: budget_edit / garble_end / text_end,"
      " share of all runs lost to them, estimated solves lost per 100 runs (task's right-patch rate)")
rows = []
for arm, x in A.items():
    if len(x) < MIN_RUNS: continue
    c = collections.Counter(r["cause"] for r in x if r["cause"])
    lost = sum(c.values()); est = sum(rate.get(r["task"], 0) for r in x if r["cause"])
    rows.append((100 * est / len(x), arm, len(x), sum(r["resolved"] for r in x), sum(r["nopatch"] for r in x), c, lost, est))
for e100, arm, n, sv, npch, c, lost, est in sorted(rows, reverse=True):
    print(f"{arm:20s} runs {n:4d} solved {sv:4d} ({sv / n:5.1%}) no patch {npch:4d} | budget_edit {c['budget_edit']:3d} garble_end {c['garble_end']:3d} text_end {c['text_end']:2d}"
          f" = {lost / n:5.1%} of runs | est. solves lost {est:5.1f} = {e100:4.1f} per 100 runs")
allc = collections.Counter(r["cause"] for r in runs if r["cause"])
print(f"\nALL: {dict(allc)} of {sum(r['nopatch'] for r in runs)} no-patch runs; est. solves lost {sum(rate.get(r['task'], 0) for r in runs if r['cause']):.1f} of {sum(r['resolved'] for r in runs)} solved")
print("tasks where lost runs concentrate (budget_edit + garble_end + text_end):",
      collections.Counter(r["task"] for r in runs if r["cause"]).most_common(10))
