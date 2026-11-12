"""What in a failed run's history steered it off course? (2026-11-12, user: "analysis of the failed runs, what evidence or
like text or whatever that was in the history of it that may have steered its way off shore").
Run: python3 -I scripts/mine_bank/steering.py [--examples]   (repo root; reads every data/results/*/requests/requests.jsonl)

Per logged 31B run (outcome from gen_per_task.jsonl, real fix from data/tasks.jsonl) the history is replayed in order:
messages the model was sent (system prompt, the issue, the evidence stage's copied lines and script output, tool results
by the kind of call that produced them) and what the model wrote (its text and its calls).
(1) WRONG FILE: for a failed run whose tracked edits touch no file of the real fix, where the first file it edited first
    appeared before that edit (the issue text, evidence, a search / read / test / git output, or the model's own text or call
    = a guess). The harness's task message is split into the issue text, its instructions and the workspace file listing;
    the listing names every file, so it is skipped when looking for what pointed the run at a file. Baseline: for a solved run, where the real-fix file first appeared.
(1b) FIRST EDIT OFF: runs whose first edit is outside the real-fix files (any outcome): where that file first appeared.
(2) EVIDENCE: runs whose fixer prompt carries the evidence stage's copied lines: did those lines name a real-fix file,
    only other source files, or nothing ('NOTHING RELEVANT' / no path)? Solve rate per class, pooled and within task.
(3) OLD TESTS: tasks whose real test change rewrites existing test lines (the old expectations contradict the fix).
    Runs that, after their first source edit, ran one of those test files and saw it fail: did they edit the source
    again afterwards (changed course)? Solve rate vs runs on the same tasks that did not run them.
--examples prints a few short excerpts per finding (local terminal only; nothing is written)."""
import collections, glob, hashlib, json, math, re, sys

EXAMPLES = "--examples" in sys.argv
T = {json.loads(l)["instance_id"]: json.loads(l) for l in open("data/tasks.jsonl")}
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)conftest\.py$")


def files_of(patch):
    return re.findall(r"^\+\+\+ b/(\S+)", patch, re.M)


GOLD = {i: [f for f in files_of(t["patch"]) if not TEST.search(f)] for i, t in T.items()}


def conflict_tests(task):
    """test files of the real test change that rewrite or remove existing lines (old expectations)."""
    out, cur = set(), None
    for ln in task["test_patch"].splitlines():
        if ln.startswith("--- a/"):
            cur = ln[6:]
        elif ln.startswith("--- /dev/null"):
            cur = None
        elif ln.startswith("-") and not ln.startswith("---") and cur and ln[1:].strip():
            out.add(cur)
    return out


CONFLICT = {i: conflict_tests(t) for i, t in T.items()}


def norm(p):
    p = str(p or "").strip()
    for pre in ("/workspace/", "./"):
        if p.startswith(pre):
            p = p[len(pre):]
    return p


def mentions(text, path):
    if not text or not path:
        return False
    mod = path[:-3].replace("/", ".") if path.endswith(".py") else None
    return path in text or (mod is not None and len(mod) > 6 and mod in text)


def call_kind(name, args):
    if name == "read_file":
        return "read output"
    if name in ("edit_file", "write_file"):
        return "edit result"
    if name == "run_skill_script" and str(args.get("skill_name")) == "evidence":
        return "evidence script output"
    cmd = str(args.get("command") or args.get("cmd") or "")
    if name == "run_skill_script":  # the clock family runs every command through a skill script
        pa = args.get("positional_args") or args.get("args") or []
        cmd = " ".join(map(str, pa)) if isinstance(pa, list) else str(pa)
    if re.search(r"pytest|unittest", cmd):
        return "test output"
    if re.search(r"\bgit (log|show|blame|diff)\b", cmd):
        return "git output"
    if re.search(r"\b(grep|rg|find|git grep|ls)\b", cmd):
        return "search output"
    if re.search(r"\b(sed -n|cat|head|tail|nl|awk)\b", cmd):
        return "read output"
    if re.search(r"\bpython", cmd):
        return "script output (python)"
    return "other tool output"


def runs():
    for f in sorted(glob.glob("data/results/*/requests/requests.jsonl")):
        d = f.split("/")[2]
        if "e4b" in d or "12b" in d:
            continue
        per = glob.glob(f"data/results/{d}/**/gen_per_task.jsonl", recursive=True)
        if not per:
            continue
        res = {(r["instance_id"], str(r.get("attempt"))): r for r in map(json.loads, open(per[0]))}
        J = collections.defaultdict(list)
        for line in open(f, errors="replace"):
            try:
                r = json.loads(line)
            except Exception:
                continue
            if isinstance(r.get("reply"), dict) and r.get("job"):
                J[r["job"]].append(r)
        for job, reqs in J.items():
            iid, _, att = job.partition("#a")
            g = res.get((iid, att))
            if g is None or iid not in T or "e4b" in str(g.get("arm")) or "12b" in str(g.get("arm")):
                continue
            reqs.sort(key=lambda r: r["t"])
            yield d, iid, g, reqs


HARNESS_SECTIONS = ("\n## Hints:\n", "\n## Task Budget (Session", "\n## Execution Environment Rules", "\n## Instructions:", "\n## Workspace Layout")


def split_task(text):
    """the harness task message -> (problem statement, everything after it: hints, budget, rules, instructions, file listing)."""
    body = text.split("Problem Statement:", 1)[1]
    cut = min([body.find(h) for h in HARNESS_SECTIONS if h in body] or [len(body)])
    return body[:cut], body[cut:]


def replay(reqs):
    """ordered events (source, text, call) and the evidence section of the fixer's system prompt."""
    seen, calls, events, evid = set(), {}, [], None
    for r in reqs:
        msgs = r["request"]["messages"]
        for m in msgs:
            c = m.get("content")
            text = c if isinstance(c, str) else json.dumps(c) if c is not None else ""
            key = hashlib.md5((str(m.get("role")) + str(m.get("tool_call_id")) + text).encode("utf-8", "replace")).hexdigest()
            if key in seen:
                continue
            seen.add(key)
            role = m.get("role")
            if role == "system":
                if "# REPOSITORY EVIDENCE" in text:
                    head, _, ev = text.partition("# REPOSITORY EVIDENCE")
                    if evid is None and "Your only job is one search" not in text:
                        evid = ev
                    events.append(("system prompt", head, None))
                    events.append(("evidence copied into the prompt", ev, None))
                else:
                    events.append(("system prompt", text, None))
            elif role == "user":
                if "Problem Statement:" in text:
                    issue, rest = split_task(text)
                    events.append(("the issue text", issue, None))
                    instr, _, listing = rest.partition("## Workspace Layout")
                    events.append(("harness instructions", instr, None))
                    events.append(("workspace file listing", listing, None))
                else:
                    src = "evidence script output" if "REPOSITORY EVIDENCE for" in text else "other harness / context message"
                    events.append((src, text, None))
            elif role == "tool":
                nm, a = calls.get(m.get("tool_call_id"), ("?", {}))
                events.append((call_kind(nm, a), text, (nm, a)))
            elif role == "assistant":
                events.append(("model's own text", text, None))
        msg = r["reply"]["message"]
        events.append(("model's own text", (msg.get("reasoning_content") or msg.get("reasoning") or "") + "\n" + (msg.get("content") or ""), None))
        for c in msg.get("tool_calls") or []:
            fn = c.get("function") or {}
            try:
                a = json.loads(fn.get("arguments") or "{}") if isinstance(fn.get("arguments"), str) else (fn.get("arguments") or {})
            except Exception:
                a = {}
            a = a if isinstance(a, dict) else {}
            calls[c.get("id")] = (fn.get("name"), a)
            events.append(("model's own call", json.dumps(a), (fn.get("name"), a)))
    return events, evid


def edits(events):
    """[(event_index, path)] of tracked source edits (edit_file / write_file outside tests and /tmp)."""
    out = []
    for i, (src, text, call) in enumerate(events):
        if src == "model's own call" and call and call[0] in ("edit_file", "write_file"):
            p = norm(call[1].get("file_path") or call[1].get("path") or call[1].get("filepath"))
            if p and p.endswith(".py") and not p.startswith("/tmp") and not TEST.search(p) and "repro" not in p and ".git/" not in p:
                out.append((i, p))
    return out


def first_source(events, path, before):
    """first event before BEFORE that names PATH, the workspace file listing skipped (it names every file)."""
    listed = False
    for i, (src, text, _) in enumerate(events[:before + 1]):
        if mentions(text, path):
            if src == "workspace file listing":
                listed = True
                continue
            return src, i
    return ("only in the workspace file listing" if listed else "never shown"), None


def sign_p(a, b):
    n = a + b
    return min(1.0, 2 * sum(math.comb(n, j) for j in range(min(a, b) + 1)) / 2 ** n) if n else 1.0


wrong_src, solved_src = collections.Counter(), collections.Counter()
first_off = collections.defaultdict(lambda: [0, 0])  # source of a first edit outside the real-fix files -> [runs, solved]
first_off_files = collections.Counter()
ev_rows, old_rows, ex = [], [], collections.defaultdict(list)
for d, iid, g, reqs in runs():
    solved = bool(g.get("resolved")); patch = bool(g.get("patch_chars"))
    events, evid = replay(reqs)
    ed = edits(events)
    gold = GOLD.get(iid, [])
    if ed and patch and not solved and not any(p in gold for _, p in ed):
        i, p = ed[0]
        src, at = first_source(events, p, i)
        wrong_src[src] += 1
        if len(ex[src]) < 3:
            ex[src].append((iid, g.get("arm"), p, (events[at][1] if at is not None else "")[:0]))
    if ed and patch and gold and ed[0][1] not in gold:
        src, _ = first_source(events, ed[0][1], ed[0][0])
        first_off[src][0] += 1; first_off[src][1] += solved
        first_off_files[("docs/examples" if re.match(r"(docs_src|docs|examples)/", ed[0][1]) else "other source")] += 1
    if solved and gold:
        gi = next((i for i, p in ed if p in gold), None)
        if gi is not None:
            solved_src[first_source(events, next(p for i, p in ed if i == gi), gi)[0]] += 1
    if evid is not None and gold:
        cls = ("names a real-fix file" if any(mentions(evid, f) for f in gold)
               else "NOTHING RELEVANT" if "NOTHING RELEVANT" in evid
               else "names only other source files" if re.search(r"[\w/]+\.py", evid) else "no file named")
        ev_rows.append(dict(iid=iid, arm=g.get("arm"), cls=cls, y=solved, patch=patch,
                            wrong_named=bool(ed) and not solved and any(mentions(evid, p) for _, p in ed if p not in gold)))
    conf = CONFLICT.get(iid) or set()
    if conf and gold:
        first_edit = ed[0][0] if ed else None
        ran_fail, changed = False, False
        if first_edit is not None:
            fail_at = None
            for i in range(first_edit, len(events)):
                src, text, call = events[i]
                if src == "test output" and call and any(c in json.dumps(call[1]) or c.rsplit("/", 1)[-1] in json.dumps(call[1]) for c in conf):
                    if re.search(r"(?<![\d.])\d+ failed|FAILED|AssertionError|\bassert\b.*\bError", text):
                        ran_fail, fail_at = True, i
                        break
            if fail_at is not None:
                changed = any(i > fail_at for i, _ in ed)
        old_rows.append(dict(iid=iid, y=solved, ran_fail=ran_fail, changed=changed, edited=first_edit is not None))

print("(1) WRONG FILE: failed runs whose tracked edits touch no real-fix file; where the first edited file first appeared")
n = sum(wrong_src.values())
for k, v in wrong_src.most_common():
    print(f"   {k:34s} {v:4d} ({100 * v / n:.0f}%)")
n2 = sum(solved_src.values())
print(f"   baseline, solved runs ({n2}): where the real-fix file first appeared: " + ", ".join(f"{k} {100 * v / n2:.0f}%" for k, v in solved_src.most_common(6)))

nf = sum(v[0] for v in first_off.values())
print(f"\n(1b) FIRST EDIT OUTSIDE THE REAL-FIX FILES (runs with a patch, any outcome): {nf} runs, solved {sum(v[1] for v in first_off.values())}; "
      f"where that file first appeared:")
for k, v in sorted(first_off.items(), key=lambda kv: -kv[1][0]):
    print(f"   {k:34s} {v[0]:4d} ({100 * v[0] / nf:.0f}%), solved {v[1]}")
print("   kind of file: " + ", ".join(f"{k} {v}" for k, v in first_off_files.most_common()))
print("\n(2) EVIDENCE copied into the fixer's prompt (evidence-stage runs)")
by = collections.defaultdict(list)
for r in ev_rows:
    by[r["cls"]].append(r)
for k, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
    print(f"   {k:32s} runs {len(v):4d} | solved {sum(r['y'] for r in v):4d} ({100 * sum(r['y'] for r in v) / len(v):.0f}%) | no patch {sum(not r['patch'] for r in v)}")
wn = [r for r in ev_rows if r["wrong_named"]]
print(f"   failed runs that edited a wrong file the evidence had named: {len(wn)} of {sum(1 for r in ev_rows if not r['y'] and r['patch'])} failed runs with a patch")
pt = collections.defaultdict(lambda: collections.defaultdict(list))
for r in ev_rows:
    pt[r["iid"]][r["cls"] == "names a real-fix file"].append(r["y"])
up = down = 0
for i, v in pt.items():
    if v[True] and v[False]:
        a, b = sum(v[True]) / len(v[True]), sum(v[False]) / len(v[False])
        up += a > b; down += a < b
print(f"   same task: solve rate higher when the copied lines named the real-fix file in {up} tasks, lower in {down} (sign p {sign_p(up, down):.2f})")

print("\n(3) OLD TESTS: tasks whose real test change rewrites existing test lines")
tasks_c = sorted({r["iid"] for r in old_rows})
print(f"   tasks {len(tasks_c)}, runs {len(old_rows)}; runs with an edit {sum(r['edited'] for r in old_rows)}")
rf = [r for r in old_rows if r["ran_fail"]]; nf = [r for r in old_rows if r["edited"] and not r["ran_fail"]]
if rf:
    print(f"   after the first edit ran an old test file and saw it fail: {len(rf)} runs, solved {sum(r['y'] for r in rf)} ({100 * sum(r['y'] for r in rf) / len(rf):.0f}%), "
          f"edited the source again afterwards {sum(r['changed'] for r in rf)} ({100 * sum(r['changed'] for r in rf) / len(rf):.0f}%)")
if nf:
    print(f"   edited, never saw an old test fail:                  {len(nf)} runs, solved {sum(r['y'] for r in nf)} ({100 * sum(r['y'] for r in nf) / len(nf):.0f}%)")
pt3 = collections.defaultdict(lambda: ([], []))
for r in old_rows:
    if r["edited"]:
        pt3[r["iid"]][r["ran_fail"]].append(r["y"])
up = down = 0
for i, (a, b) in pt3.items():
    if a and b:
        ra, rb = sum(a) / len(a), sum(b) / len(b)
        up += rb > ra; down += rb < ra
print(f"   same task: solve rate lower after seeing an old test fail in {down} tasks, higher in {up} (sign p {sign_p(up, down):.2f})")
if EXAMPLES:
    print("\nexamples (task, arm, wrong file) per source:")
    for k, v in ex.items():
        print(f"   {k}: " + "; ".join(f"{a} {b} {c}" for a, b, c, _ in v))
