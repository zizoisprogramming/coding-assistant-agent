"""Agents ranked by runs lost to TIME (the run hit its time cap) or to BAD CALLS, and how the two are linked (MINING
2026-11-11f). Usage: python3 -I scripts/mine_bank/time_vs_bad.py [MIN_RUNS] [--dev16]   (repo root)

Per run (31B, folders with request logs + gen_per_task.jsonl):
  capped        end == "time" (the arm's session cap: 6-8 min)
  lost_time     capped and no patch
  lost_bad      no patch, explained by a bad call (an edit refused after the budget with no working edit before, a garbled
                edit never fixed, or the last reply a call written as text; as bad_call_losses.py)
  bad_any       at least one bad call before the budget ran out (garbled, edit no-match, inline python, read range, /tmp,
                tool name / python in shell, shell quoting, text call, skill args, unknown tool)
  bad_s         model seconds producing those calls; tail_s = seconds from the first call refused by the budget to the end
Link: cap rate in runs WITH a bad call vs WITHOUT, raw and within the same task (task-weighted difference over tasks that
have runs of both kinds), since hard tasks cause both."""
import collections, glob, importlib.util, json, os, re, sys

spec = importlib.util.spec_from_file_location("bc", os.path.join(os.path.dirname(os.path.abspath(__file__)), "bad_calls.py"))
bc = importlib.util.module_from_spec(spec); spec.loader.exec_module(bc)
MIN_RUNS = int(next((a for a in sys.argv[1:] if a.isdigit()), 40))
DEV16 = "--dev16" in sys.argv  # only the 16 dev16 tasks (agents ran different task sets; e24 = tasks picked for being solved)
SPLIT = set(json.load(open("data/splits_public.json"))["dev16"]) if DEV16 else None
ALWAYS = ["combo1", "evidc", "evidd", "evide"]
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
        if not o or (SPLIT and o["instance_id"] not in SPLIT): continue
        q.sort(key=lambda r: r["t"])
        worked = budget_edit = garble_open = last_text = budget_on = False
        bad_n = 0; bad_s = 0.0; tail_s = 0.0
        for r in q:
            msg = r["reply"]["message"]; cl = msg.get("tool_calls") or []; sec = r.get("seconds") or 0
            if budget_on:
                tail_s += sec
            if not cl:
                last_text = bool(bc.TEXT_CALL.search(str(msg.get("content") or "")))
                if last_text and not budget_on: bad_n += 1; bad_s += sec
                continue
            last_text = False
            for c in cl:
                name = c["function"]["name"]; raw = c["function"].get("arguments") or ""; res = res_of.get(c.get("id"), "")
                try: a = json.loads(raw)
                except Exception: a = {}
                k = bc.kind_of(name, raw, res, "")
                if name not in bc.TOOLS: k = k or "unknown_tool"
                if k == "after_budget":
                    if not budget_on: tail_s += sec
                    budget_on = True
                    if name in ("edit_file", "write_file") and not worked: budget_edit = True
                elif k and not budget_on:
                    bad_n += 1; bad_s += sec / len(cl)
                if k == "garbled_args": garble_open = True
                fp = str(a.get("filepath") or "")
                if name in ("edit_file", "write_file") and '"status": "ok"' in res[:30] and fp and not TEST.search(fp) and not fp.startswith(("/tmp", ".git")):
                    worked = True; garble_open = False
        nopatch = not o.get("patch_chars")
        cause = ("budget_edit" if budget_edit else "garble_end" if garble_open else "text_end" if last_text else None) if nopatch else None
        runs.append(dict(arm=o.get("arm") or job.partition("#a")[2].rsplit(".", 1)[0], task=o["instance_id"], end=o.get("end"),
                         resolved=bool(o.get("resolved")), nopatch=nopatch, cause=cause, bad_any=bad_n > 0, bad_s=bad_s,
                         tail_s=tail_s, budget=budget_on, agent_s=o.get("agent_s") or 0))


def link(x):
    """cap rate with / without a bad call: raw, and the task-weighted within-task difference."""
    w = [r for r in x if r["bad_any"]]; wo = [r for r in x if not r["bad_any"]]
    cap = lambda rr: sum(r["end"] == "time" for r in rr) / max(1, len(rr))
    T = collections.defaultdict(lambda: ([], []))
    for r in x: T[r["task"]][0 if r["bad_any"] else 1].append(r)
    num = den = 0
    for t, (a, b) in T.items():
        if a and b:
            num += len(a) * (cap(a) - cap(b)); den += len(a)
    return cap(w), len(w), cap(wo), len(wo), (num / den if den else None), den


A = collections.defaultdict(list)
for r in runs: A[r["arm"]].append(r)
agents = [a for a, x in A.items() if len(x) >= MIN_RUNS] + [a for a in ALWAYS if a in A and len(A[a]) < MIN_RUNS]
rows = []
for arm in agents:
    x = A[arm]; n = len(x)
    cap = sum(r["end"] == "time" for r in x); lt = sum(r["end"] == "time" and r["nopatch"] for r in x)
    lb = sum(r["cause"] is not None for r in x)
    either = sum(r["nopatch"] and (r["end"] == "time" or r["cause"] is not None) for r in x)
    both = sum(r["nopatch"] and r["end"] == "time" and r["cause"] is not None for r in x)
    cw, nw, cwo, nwo, d, dn = link(x)
    rows.append((either / n, arm, n, sum(r["resolved"] for r in x), cap, lt, lb, either, both,
                 sum(r["bad_s"] + r["tail_s"] for r in x) / n, cw, nw, cwo, nwo, d, sum(r["agent_s"] for r in x) / n))
print(f"{'agent':12s} {'runs':>4s} {'solved':>6s} {'hit time cap':>12s} {'capped, no patch':>16s} {'no patch from bad calls':>23s}"
      f" {'LOST (time or bad)':>18s} {'both':>5s} {'bad-call s/run':>14s} {'agent s':>7s}   cap rate: with bad call vs without (same task)")
for e, arm, n, sv, cap, lt, lb, either, both, bs, cw, nw, cwo, nwo, d, ag in sorted(rows, reverse=True):
    same = f"{d:+.0%}" if d is not None else "n/a"
    print(f"{arm:12s} {n:4d} {sv / n:6.0%} {cap / n:12.0%} {lt / n:16.0%} {lb / n:23.0%} {either / n:18.0%} {both:5d} {bs:14.1f} {ag:7.0f}"
          f"   {cw:4.0%} (n={nw}) vs {cwo:4.0%} (n={nwo}); same task {same}")
cw, nw, cwo, nwo, d, dn = link(runs)
print(f"\nALL {len(runs)} runs: cap rate with a bad call {cw:.0%} (n={nw}) vs without {cwo:.0%} (n={nwo}); within the same task {d:+.1%} ({dn} runs with bad calls on tasks that have both)")
for lab, sel in (("hit the budget", lambda r: r["budget"]), ("did not hit the budget", lambda r: not r["budget"])):
    rr = [r for r in runs if sel(r)]
    print(f"  runs that {lab}: {len(rr)}, capped {sum(r['end'] == 'time' for r in rr) / max(1, len(rr)):.0%}, no patch {sum(r['nopatch'] for r in rr) / max(1, len(rr)):.0%}")
