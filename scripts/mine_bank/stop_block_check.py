"""Offline check for an a.py read block after STOP READING (user 2026-11-23: 'plan the a.py read block after STOP READING').
Every sk_a2-family run whose a.py printed STOP READING before any source edit. For each: had the real-fix lines been shown before the
first STOP READING (a.py show output line numbers within NEAR of a real-fix line, in a real-fix file)? how many calls came after it,
of what kind? solved runs: was the real-fix region first shown only AFTER the STOP (a block would have cut it off)?
Run: python3 -I scripts/mine_bank/stop_block_check.py"""
import ast, collections, glob, json, re, statistics as st
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
NEAR = 3
SRC = re.compile(r"(repro|check|debug|scratch|\.git/agent|/tmp/|test)")


def changed(diff):
    out, f, old = collections.defaultdict(set), None, 0
    for line in diff.split("\n"):
        if line.startswith("diff --git"): f = None
        elif line.startswith("+++ "):
            p = line[4:].strip(); f = p[2:] if p.startswith("b/") else None
            if f and (not f.endswith(".py") or re.search(r"(^|/)tests?/|test_|conftest", f)): f = None
        elif line.startswith("@@"):
            m = re.match(r"@@ -(\d+)", line); old = int(m.group(1)) if m else 0
        elif f is None or line.startswith("--- "): continue
        elif line.startswith("-"): out[f].add(old); old += 1
        elif line.startswith("+"): out[f].add(old)
        elif line.startswith(" "): old += 1
    return {k: v for k, v in out.items() if v}


GOLD = {json.loads(l)["instance_id"]: changed(json.loads(l)["patch"]) for l in open(ROOT / "data/tasks.jsonl")}


def parse(x):
    if isinstance(x, dict): return x
    try: return ast.literal_eval(str(x))
    except Exception:
        try: return json.loads(str(x))
        except Exception: return {}


def is_edit(n, a):
    c = str(a.get("command", ""))
    if n == "edit_file": return not SRC.search(str(a.get("filepath", "")))
    return ("OLD_TEXT" in c or ".replace(" in c or "sed -i" in c) and "a.py" not in c and "repro" not in c


def kind(n, a):
    c = str(a.get("command", ""))
    if is_edit(n, a): return "EDIT"
    if n in ("submit_patch", "get_status"): return "free"
    if n == "read_file": return "raw read"
    if n in ("write_file", "edit_file"): return "scratch"
    if "a.py show" in c or "a.py outline" in c: return "a.py show/outline"
    if "a.py find" in c: return "a.py find"
    if re.search(r"(^|\s)(cat|sed -n|head|tail|nl|grep|git grep|rg)\b", c): return "raw read"
    if "pytest" in c: return "pytest"
    if "python" in c: return "RUN"
    return "shell"


def shown_gold(task, cmd, out):
    m = re.search(r"a\.py show\s+(\S+)", cmd)
    if not m: return False
    path = m.group(1).lstrip("./")
    g = GOLD.get(task, {})
    gf = [f for f in g if f == path or f.endswith("/" + path) or path.endswith(f)]
    if not gf: return False
    nums = {int(x) for x in re.findall(r"(?:^|\\n|\n)\s*(\d+)\| ", out)}
    return any(abs(n - y) <= NEAR for f in gf for n in nums for y in g[f])


S = collections.defaultdict(list)
for d in sorted(glob.glob(str(ROOT / "data/results/*/"))):
    gp, rp = Path(d) / "results/gen_per_task.jsonl", Path(d) / "requests/requests.jsonl"
    if not gp.exists() or not rp.exists(): continue
    G = {}
    for l in open(gp, errors="replace"):
        try: g = json.loads(l); G[g["instance_id"] + "#a" + str(g["attempt"])] = g
        except Exception: pass
    by = collections.defaultdict(list)
    for l in open(rp, errors="replace"):
        try: r = json.loads(l)
        except Exception: continue
        by[r.get("job", "")].append(r)
    for job, rs in by.items():
        g = G.get(job)
        if not g or not str(g.get("arm", "")).startswith("sk_a2") or g["instance_id"] not in GOLD: continue
        rs = sorted([r for r in rs if len((r.get("request") or {}).get("messages") or []) > 1], key=lambda r: float(r["t"]))
        if not rs: continue
        res = {}
        for r in rs:
            for m in r["request"]["messages"]:
                if m.get("role") == "tool": res[m.get("tool_call_id")] = str(m.get("content"))
        calls = []
        for r in rs:
            for c in ((parse(r.get("reply")) or {}).get("message") or {}).get("tool_calls") or []:
                fn = c.get("function") or {}
                try: a = json.loads(fn.get("arguments") or "{}")
                except Exception: a = {}
                if not isinstance(a, dict): a = {}
                out = res.get(c.get("id"), "")
                calls.append((kind(fn.get("name"), a), "BudgetExceeded" in out, shown_gold(g["instance_id"], str(a.get("command", "")), out), "STOP READING" in out))
        fe = next((i for i, c in enumerate(calls) if c[0] == "EDIT" and not c[1]), None)
        stop = next((i for i, c in enumerate(calls) if c[3]), None)
        if stop is None or (fe is not None and fe < stop): continue
        ok = g.get("resolved") in (True, "True")
        seen_before = any(c[2] for c in calls[:stop + 1])
        seen_after = any(c[2] for c in calls[stop + 1:(fe if fe is not None else len(calls))])
        after = [c[0] for c in calls[stop + 1:(fe if fe is not None else len(calls))] if c[0] != "free"]
        S["solved" if ok else "failed"].append(dict(task=g["instance_id"], arm=g["arm"], seen_before=seen_before, only_after=seen_after and not seen_before,
                                                     n_after=len(after), kinds=collections.Counter(after), edited=fe is not None, stop=stop))
tot_runs = sum(len(v) for v in S.values())
print(f"sk_a2-family runs with STOP READING before any applied source edit: {tot_runs}")
for k in ("solved", "failed"):
    R = S[k]
    if not R: continue
    K = collections.Counter()
    for r in R: K.update(r["kinds"])
    print(f"\n== {k}: {len(R)} runs (STOP at call {st.mean(r['stop'] for r in R):.1f} on average; edited later {sum(r['edited'] for r in R)})")
    print(f"  real-fix lines shown BEFORE the first STOP: {sum(r['seen_before'] for r in R)} ({sum(r['seen_before'] for r in R) / len(R):.0%});"
          f" shown ONLY AFTER it: {sum(r['only_after'] for r in R)}; never shown: {sum(not r['seen_before'] and not r['only_after'] for r in R)}")
    print(f"  calls after the STOP until the edit / end: mean {st.mean(r['n_after'] for r in R):.1f}; kinds: " + ", ".join(f"{a} {b / len(R):.1f}" for a, b in K.most_common()))
    if k == "solved":
        print("  solved runs that saw the fix only after the STOP (a block would have cut them):", [(r["task"], r["arm"]) for r in R if r["only_after"]])
