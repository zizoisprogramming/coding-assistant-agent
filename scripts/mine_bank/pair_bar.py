"""Arm vs its same-run control, run by run (r81 bar: few-shot-fixed copies vs the originals). Usage:
    python3 -I scripts/mine_bank/pair_bar.py FOLDER [FOLDER ...] [--pairs=new:control,...]   (repo root)
Default pairs: every arm NAMEfs next to NAME. Per side (pooled over the pairs and per pair):
  solved, no patch, capped (end == time), mean agent seconds
  form-error runs / calls: edit text not in file, broken inline python, /tmp write_file, tool name or python typed in the
      shell, shell quoting, reversed read range (bad_calls.kind_of; counted before the budget ran out)
  garbled edits (a backtick closes a string; not a form error the examples target, shown for reference)
  after budget: runs with a refused call, refused calls, seconds from the first refusal to the end
  adoption of the examples: heredoc python (python3 - <<), python -c, sed -n prints, edits whose old_string was copied
      from an earlier tool output (its first line appears verbatim in one)
Then the same-task pairs (new + / control +) with an exact sign test. Prints no task text."""
import collections, importlib.util, json, math, os, re, sys

spec = importlib.util.spec_from_file_location("bc", os.path.join(os.path.dirname(os.path.abspath(__file__)), "bad_calls.py"))
bc = importlib.util.module_from_spec(spec); spec.loader.exec_module(bc)
FOLDERS = [a.rstrip("/") for a in sys.argv[1:] if not a.startswith("--")]
PAIRS_ARG = next((a[8:] for a in sys.argv[1:] if a.startswith("--pairs=")), None)
FORM = {"edit_nomatch", "inline_py_syntax", "tool_as_shell", "code_as_shell", "shell_quote", "write_outside", "read_range"}
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$")

runs = {}
for D in FOLDERS:
    out = {}
    for l in open(D + "/results/gen_per_task.jsonl"):
        r = json.loads(l); out[f"{r['instance_id']}#a{r['attempt']}"] = r
    res_of, jobs = {}, collections.defaultdict(list)
    for l in open(D + "/requests/requests.jsonl"):
        try: r = json.loads(l)
        except Exception: continue
        if not (isinstance(r.get("reply"), dict) and r.get("job")): continue
        for m in r["request"]["messages"]:
            if m.get("role") == "tool": res_of.setdefault(m.get("tool_call_id"), str(m.get("content")))
        jobs[r["job"]].append(r)
    for job, o in out.items():
        q = sorted(jobs.get(job, []), key=lambda r: r["t"])
        x = dict(folder=D, task=o["instance_id"], arm=o["arm"], solved=bool(o.get("resolved")), nopatch=not o.get("patch_chars"),
                 capped=o.get("end") == "time", agent_s=o.get("agent_s") or 0, kinds=collections.Counter(), form=0, garbled=0,
                 refused=0, tail_s=0.0, heredoc=0, pyc=0, sedn=0, edits=0, copied=0)
        seen_out = ""; budget_on = False
        for r in q:
            msg = r["reply"]["message"]; sec = r.get("seconds") or 0
            if budget_on: x["tail_s"] += sec
            for c in msg.get("tool_calls") or []:
                name = c["function"]["name"]; raw = c["function"].get("arguments") or ""; res = res_of.get(c.get("id"), "")
                try: a = json.loads(raw)
                except Exception: a = {}
                k = bc.kind_of(name, raw, res, "")
                if k == "after_budget":
                    if not budget_on: x["tail_s"] += sec
                    budget_on = True; x["refused"] += 1
                elif k and not budget_on:
                    x["kinds"][k] += 1
                    x["form"] += k in FORM; x["garbled"] += k == "garbled_args"
                if name == "run_command":
                    cmd = str(a.get("command") or "")
                    x["heredoc"] += bool(re.search(r"python3?\s+-\s*<<", cmd)); x["pyc"] += bool(re.search(r"python3?\s+-c\s", cmd))
                    x["sedn"] += bool(re.search(r"\bsed\s+-n\b", cmd))
                if name == "edit_file" and k != "after_budget" and not TEST.search(str(a.get("filepath") or "")):
                    first = next((s for s in str(a.get("old_string") or "").splitlines() if s.strip()), "")
                    if first:
                        x["edits"] += 1; x["copied"] += first.strip() in seen_out
                if k != "after_budget": seen_out += bc.flat(res)
        runs[(D, job)] = x

arms = sorted({x["arm"] for x in runs.values()})
pairs = [tuple(p.split(":")) for p in PAIRS_ARG.split(",")] if PAIRS_ARG else [(a, a[:-2]) for a in arms if a.endswith("fs") and a[:-2] in arms]


def side(rr):
    n = len(rr); f = lambda k: sum(x[k] for x in rr)
    return dict(n=n, solved=f("solved"), nopatch=f("nopatch"), capped=f("capped"), agent_s=f("agent_s") / max(1, n),
                form_runs=sum(x["form"] > 0 for x in rr), form=f("form"), garbled=f("garbled"),
                budget_runs=sum(x["refused"] > 0 for x in rr), refused=f("refused"), tail_s=f("tail_s") / max(1, n),
                heredoc=f("heredoc"), pyc=f("pyc"), sedn=f("sedn"), edits=f("edits"), copied=f("copied"))


def line(lab, s):
    return (f"{lab:10s} {s['n']:3d} {s['solved']:6d} {s['nopatch']:7d} {s['capped']:6d} {s['agent_s']:7.0f} {s['form_runs']:9d} {s['form']:10d}"
            f" {s['garbled']:7d} {s['budget_runs']:10d} {s['refused']:7d} {s['tail_s']:9.1f} {s['heredoc']:7d} {s['pyc']:9d} {s['sedn']:5d}"
            f" {s['copied']:3d}/{s['edits']:<3d}")


print(f"{'arm':10s} {'n':>3s} {'solved':>6s} {'nopatch':>7s} {'capped':>6s} {'agent_s':>7s} {'form runs':>9s} {'form calls':>10s}"
      f" {'garbled':>7s} {'budget runs':>10s} {'refused':>7s} {'tail s/run':>9s} {'heredoc':>7s} {'python -c':>9s} {'sed -n':>5s} copied/edits")
NEW, CTRL = [], []
for a, b in pairs:
    ra = [x for x in runs.values() if x["arm"] == a]; rb = [x for x in runs.values() if x["arm"] == b]
    NEW += ra; CTRL += rb
    print(line(a, side(ra))); print(line(b, side(rb)))
    kinds = lambda rr: dict(sum((x["kinds"] for x in rr), collections.Counter()))
    print(f"{'':10s} kinds {a}: {kinds(ra)} | {b}: {kinds(rb)}")
print("POOLED"); sn, sc = side(NEW), side(CTRL)
print(line("new", sn)); print(line("control", sc))
plus = minus = 0
for (D, job), x in runs.items():
    for a, b in pairs:
        if x["arm"] == a:
            y = next((z for z in runs.values() if z["folder"] == D and z["task"] == x["task"] and z["arm"] == b), None)
            if y:
                plus += x["solved"] and not y["solved"]; minus += y["solved"] and not x["solved"]
m = plus + minus
p = min(1.0, 2 * sum(math.comb(m, i) for i in range(min(plus, minus) + 1)) / 2 ** m) if m else 1.0
print(f"same-task pairs: new solved and control not {plus}, control solved and new not {minus}; exact sign test p = {p:.2f}")
print(f"agent time: new - control = {sn['agent_s'] - sc['agent_s']:+.1f} s/run")
