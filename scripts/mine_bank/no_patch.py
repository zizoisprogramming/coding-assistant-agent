"""What do runs that end with NO patch do? (2026-11-12, user "go for it" on the no-patch discussion after r84-r86.)
Run: python3 -I scripts/mine_bank/no_patch.py [ARM_SUBSTR,...]   (default: the evidence family)

Per logged run of the chosen agents (requests.jsonl + gen_per_task.jsonl): how it ended (time cap = agent_s >= 470;
call budget = a 'Tool call budget exhausted' result; stopped early = neither), how many fixer replies it made, its mean
seconds per model reply and completion tokens per reply (thinking dominates), seconds inside tools, whether it ever read
the real fix's file / lines (read_file ranges, sed -n, cat; the real fix from tasks.jsonl), whether it tried an edit that
failed (no match, cut-apart call, refused after the budget), and what its last five calls were (read / search / run /
test / edit). Solved runs on the same tasks are the comparison. No task text is printed."""
import collections, glob, json, re, statistics as st, sys

ARMS = [a for a in (sys.argv[1].split(",") if len(sys.argv) > 1 else [])] or ["evidc", "evide", "evidd", "evidcfs", "evidefs", "evmap", "evtrace", "evall", "evtrace2", "evgraph", "evid3", "evid4"]
T = {json.loads(l)["instance_id"]: json.loads(l) for l in open("data/tasks.jsonl")}
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)conftest\.py$")
STAGE = "Your only job is one search"


def gold(iid):
    files, lines, cur = [], collections.defaultdict(set), None
    for l in T[iid]["patch"].splitlines():
        if l.startswith("--- a/"):
            cur = l[6:]
        m = re.match(r"@@ -(\d+)(?:,(\d+))?", l)
        if m and cur and not TEST.search(cur):
            a = int(m.group(1)); n = int(m.group(2) or 1)
            lines[cur].update(range(a, a + max(n, 1)))
            if cur not in files:
                files.append(cur)
    return files, lines


def kind(name, a):
    cmd = str(a.get("command") or "")
    if name in ("edit_file", "write_file"):
        return "edit"
    if name == "read_file" or re.search(r"\b(sed -n|cat|head|tail|nl)\b", cmd):
        return "read"
    if re.search(r"pytest|unittest", cmd):
        return "test"
    if re.search(r"\bpython3?\b", cmd):
        return "run"
    if re.search(r"\b(grep|rg|find|ls|git grep|git log|git show)\b", cmd):
        return "search"
    return name if name != "run_command" else "other"


rows = []
for f in sorted(glob.glob("data/results/2026-*/requests/requests.jsonl")):
    d = f.split("/")[2]
    per = glob.glob(f"data/results/{d}/**/gen_per_task.jsonl", recursive=True)
    if not per:
        continue
    res = {(r["instance_id"], str(r.get("attempt"))): r for r in map(json.loads, open(per[0]))}
    if not any(str(r.get("arm")) in ARMS for r in res.values()):
        continue
    J = collections.defaultdict(list)
    for l in open(f, errors="replace"):
        try:
            r = json.loads(l)
        except Exception:
            continue
        if isinstance(r.get("reply"), dict) and r.get("job"):
            J[r["job"]].append(r)
    for job, q in J.items():
        iid, _, att = job.partition("#a")
        g = res.get((iid, att))
        if g is None or iid not in T or str(g.get("arm")) not in ARMS:
            continue
        q.sort(key=lambda r: r["t"])
        fix = [r for r in q if STAGE not in str(r["request"]["messages"][0].get("content"))]
        if not fix:
            continue
        gf, gl = gold(iid)
        results = {}
        for r in fix:
            for m in r["request"]["messages"]:
                if m.get("role") == "tool":
                    results.setdefault(m.get("tool_call_id"), str(m.get("content")))
        kinds, read_file_, read_lines, failed_edit, budget, tool_s = [], False, False, 0, False, 0.0
        for r in fix:
            for c in r["reply"]["message"].get("tool_calls") or []:
                fn = c.get("function") or {}
                a = fn.get("arguments") or {}
                if isinstance(a, str):
                    try:
                        a = json.loads(a)
                    except Exception:
                        a = {}
                a = a if isinstance(a, dict) else {}
                k = kind(fn.get("name"), a)
                kinds.append(k)
                out = results.get(c.get("id"), "")
                if "Tool call budget exhausted" in out:
                    budget = True
                if k == "edit" and re.search(r'"status": "error"|error_type|mandatory input', out[:400]):
                    failed_edit += 1
                path = str(a.get("filepath") or a.get("file_path") or a.get("path") or "")
                cmd = str(a.get("command") or "")
                for gfile in gf:
                    if gfile in path or gfile in cmd:
                        if k == "read":
                            read_file_ = True
                            m = re.search(r"sed -n ['\"]?(\d+),(\d+)p", cmd)
                            lo, hi = (int(m.group(1)), int(m.group(2))) if m else (int(a.get("start_line") or 1) if str(a.get("start_line") or "1").isdigit() else 1, int(a.get("end_line") or 0) if str(a.get("end_line") or "").isdigit() else 0)
                            hi = hi or lo + 149
                            if "cat " in cmd or any(lo <= x <= hi for x in gl[gfile]):
                                read_lines = True
        secs = [r.get("seconds") or 0 for r in fix]
        toks = [(r["reply"].get("usage") or {}).get("completion_tokens") or 0 for r in fix]
        agent_s = g.get("agent_s") or 0
        end = "time cap" if agent_s >= 470 else "call budget" if budget else "stopped early"
        outcome = "solved" if g.get("resolved") else "wrong patch" if g.get("patch_chars") else "no patch"
        rows.append(dict(iid=iid, arm=g.get("arm"), outcome=outcome, end=end, replies=len(fix), s_per=st.mean(secs) if secs else 0,
                         tok=st.mean(toks) if toks else 0, model_s=sum(secs), agent_s=agent_s, read_file=read_file_, read_lines=read_lines,
                         failed_edit=failed_edit, edited=("edit" in kinds), last5=kinds[-5:]))

print(f"runs {len(rows)} | agents {sorted({r['arm'] for r in rows})}")
for oc in ("solved", "wrong patch", "no patch"):
    g = [r for r in rows if r["outcome"] == oc]
    if not g:
        continue
    ends = collections.Counter(r["end"] for r in g)
    print(f"\n{oc}: {len(g)} runs | ends " + ", ".join(f"{k} {v} ({100 * v / len(g):.0f}%)" for k, v in ends.most_common())
          + f" | replies {st.median([r['replies'] for r in g]):.0f} | s per reply {st.median([r['s_per'] for r in g]):.1f} | tokens per reply {st.median([r['tok'] for r in g]):.0f}"
          + f" | model s {st.median([r['model_s'] for r in g]):.0f} of agent s {st.median([r['agent_s'] for r in g]):.0f}")
    print(f"   read the real-fix file {100 * sum(r['read_file'] for r in g) / len(g):.0f}% | read the real-fix lines {100 * sum(r['read_lines'] for r in g) / len(g):.0f}% | tried an edit {100 * sum(r['edited'] for r in g) / len(g):.0f}% | an edit failed {100 * sum(r['failed_edit'] > 0 for r in g) / len(g):.0f}%")
np_ = [r for r in rows if r["outcome"] == "no patch"]
if np_:
    print("\nno-patch runs, by end:")
    for e in ("time cap", "call budget", "stopped early"):
        g = [r for r in np_ if r["end"] == e]
        if g:
            last = collections.Counter(k for r in g for k in r["last5"])
            print(f"  {e:13s} {len(g):3d} runs | replies {st.median([r['replies'] for r in g]):.0f} | s per reply {st.median([r['s_per'] for r in g]):.1f} | tokens {st.median([r['tok'] for r in g]):.0f} | "
                  f"read the real-fix lines {100 * sum(r['read_lines'] for r in g) / len(g):.0f}% | tried an edit {100 * sum(r['edited'] for r in g) / len(g):.0f}% | last five calls: "
                  + ", ".join(f"{k} {v}" for k, v in last.most_common(5)))
by = collections.defaultdict(lambda: collections.defaultdict(list))
for r in rows:
    by[r["iid"]][r["outcome"]].append(r)
tasks = [t for t, v in by.items() if len(v["solved"]) >= 2 and len(v["no patch"]) >= 2]
if tasks:
    s_tok = st.mean(st.median([r["tok"] for r in by[t]["solved"]]) for t in tasks)
    n_tok = st.mean(st.median([r["tok"] for r in by[t]["no patch"]]) for t in tasks)
    s_rep = st.mean(st.median([r["replies"] for r in by[t]["solved"]]) for t in tasks)
    n_rep = st.mean(st.median([r["replies"] for r in by[t]["no patch"]]) for t in tasks)
    s_rl = st.mean(sum(r["read_lines"] for r in by[t]["solved"]) / len(by[t]["solved"]) for t in tasks)
    n_rl = st.mean(sum(r["read_lines"] for r in by[t]["no patch"]) / len(by[t]["no patch"]) for t in tasks)
    print(f"\nsame task ({len(tasks)} tasks with >= 2 solved and >= 2 no-patch runs): tokens per reply solved {s_tok:.0f} vs no patch {n_tok:.0f} | replies {s_rep:.0f} vs {n_rep:.0f} | read the real-fix lines {100 * s_rl:.0f}% vs {100 * n_rl:.0f}%")
