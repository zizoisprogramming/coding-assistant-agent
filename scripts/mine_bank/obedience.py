"""Did each sk_a2 run do what it was told? (user 2026-11-25: 'what are agents in our bank that have success but if and only
if the model followed what it was told, either tool output or else'). Per run, from the request logs, the instructions
sk_a2's prompt and tools give, each counted as followed / broken:
  install   call 1 is run_skill_script (scripts/install.py)
  reads     code is read only with .git/agent/a.py (no cat / sed -n / head / tail / grep / read_file to read source)
  banner    after a.py prints NO EDIT YET, STOP READING or ALREADY SHOWN, the NEXT call is the edit (each event counted)
  pip       never pip / install
  pytest    pytest only targeted and under timeout (never bare 'pytest' / 'pytest .')
  tests     never edits test files
  stop      after submit_patch returns patch_size > 0, no further tool calls (submit / get_status excepted)
  budget    after the harness 'Only N tool call(s) remaining' warning, the next call is an edit or submit_patch
A run is OBEDIENT when it breaks none (banner/budget: followed at every event it saw).
Run: python3 -I scripts/mine_bank/obedience.py [arm]"""
import ast, collections, glob, json, re, sys
ARM = sys.argv[1] if len(sys.argv) > 1 else "sk_a2"
SRC = re.compile(r"(repro|check|debug|scratch|\.git/agent|/tmp/|test)")
READ = re.compile(r"^\s*(cat|sed\s+-n|head|tail|grep|egrep|rg|less|nl|awk)\b|python3?\s+-c\s+.*open\(")
TEST = re.compile(r"(^|/)(tests?/|test_[^/]*\.py$|conftest\.py$)")
def parse(x):
    if isinstance(x, dict): return x
    try: return ast.literal_eval(str(x))
    except Exception:
        try: return json.loads(str(x))
        except Exception: return {}
rows = []
for d in sorted(glob.glob("data/results/*skill*")):
    try: G = {json.loads(l)["instance_id"] + "#a" + json.loads(l)["attempt"]: json.loads(l) for l in open(f"{d}/results/gen_per_task.jsonl")}
    except OSError: continue
    G = {k: g for k, g in G.items() if g["arm"] == ARM and g.get("resolved") is not None}
    if not G: continue
    by = collections.defaultdict(list)
    try:
        for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
            r = json.loads(l)
            if r["job"] in G: by[r["job"]].append(r)
    except OSError: continue
    for job, rs in by.items():
        rs.sort(key=lambda r: float(r["t"])); g = G[job]
        res = {m.get("tool_call_id"): str(m.get("content")) for r in rs for m in r["request"]["messages"] if m.get("role") == "tool"}
        calls = []
        for r in rs:
            for c in ((parse(r.get("reply")) or {}).get("message") or {}).get("tool_calls") or []:
                fn = c.get("function") or {}
                try: a = json.loads(fn.get("arguments") or "{}")
                except Exception: a = {}
                if not isinstance(a, dict): a = {}
                calls.append((fn.get("name"), a, res.get(c.get("id"), "")))
        br = collections.Counter(); ev = collections.Counter()
        is_edit = lambda n, a, o: (n == "edit_file" and not SRC.search(str(a.get("filepath", "")))) or \
            (n == "run_command" and ("OLD_TEXT" in str(a.get("command")) or ".replace(" in str(a.get("command"))) and "a.py" not in str(a.get("command")))
        if not calls or calls[0][0] != "run_skill_script": br["install"] += 1
        submitted = False
        for i, (n, a, o) in enumerate(calls):
            cmd = str(a.get("command", ""))
            if n == "read_file" and not str(a.get("filepath", a.get("path", ""))).startswith(".git/agent"): br["reads"] += 1
            if n == "run_command" and READ.search(cmd) and "a.py" not in cmd and "git " not in cmd[:6]: br["reads"] += 1
            if re.search(r"\bpip3?\s+install\b|python3?\s+-m\s+pip\b", cmd): br["pip"] += 1
            if re.search(r"(^|[;&|]\s*)(python3?\s+-m\s+)?pytest(\s*$|\s+\.(\s|$)|\s+-)", cmd) and "timeout" not in cmd: br["pytest"] += 1
            if n in ("edit_file", "write_file") and TEST.search(str(a.get("filepath", ""))): br["tests"] += 1
            nxt = calls[i + 1] if i + 1 < len(calls) else None
            if any(b in o for b in ("NO EDIT YET", "STOP READING", "ALREADY SHOWN")) and "a.py" in cmd and not ev["banner"] \
                    and not any(is_edit(*c) for c in calls[:i]):  # the FIRST banner before any edit (it repeats on every output)
                ev["banner"] += 1
                later = [j for j in range(i + 1, len(calls)) if is_edit(*calls[j])]
                ev["banner_gap"] = (later[0] - i) if later else 99
                if nxt is None or not is_edit(*nxt): br["banner"] += 1
            if "tool call(s) remaining" in o and not ev["budget"] and not any(is_edit(*c) for c in calls[:i + 1]):
                ev["budget"] += 1  # the first harness warning while still without an edit
                if nxt is not None and not (is_edit(*nxt) or nxt[0] == "submit_patch"): br["budget"] += 1
            if submitted and n not in ("submit_patch", "get_status"): br["stop"] += 1
            if n == "submit_patch" and re.search(r'"patch_size":\s*[1-9]', o): submitted = True
        rows.append(dict(task=g["instance_id"], ok=g["resolved"] in (True, "True"), br=br, ev=ev))
def share(R, k): return sum(r["br"][k] == 0 for r in R) / max(len(R), 1)
K = ["install", "reads", "banner", "pip", "pytest", "tests", "stop", "budget"]
for lab, R in (("solved", [r for r in rows if r["ok"]]), ("failed", [r for r in rows if not r["ok"]])):
    ob = [r for r in R if not sum(r["br"].values())]
    print(f"{ARM} {lab:6} runs {len(R):4} | OBEDIENT (no rule broken) {len(ob):4} ({len(ob) / max(len(R), 1):.0%}) | followed: " +
          " ".join(f"{k} {share(R, k):.0%}" for k in K))
    B = [r for r in R if r['ev']['banner']]
    gaps = sorted(r['ev']['banner_gap'] for r in B)
    print(f"   first banner before any edit: {len(B)} runs, edit on the next call {sum(r['br']['banner'] == 0 for r in B)} | calls from it to the "
          f"edit: median {gaps[len(gaps) // 2] if gaps else '-'}, never edited after it {sum(x == 99 for x in gaps)} | first budget warning without an edit: "
          f"{sum(r['ev']['budget'] > 0 for r in R)}, edit / submit next {sum(r['ev']['budget'] > 0 and r['br']['budget'] == 0 for r in R)}")
S = [r for r in rows if r["ok"]]
ob = [r for r in S if not sum(r["br"].values())]
print(f"\nsolved runs breaking nothing: {len(ob)} on {len({r['task'] for r in ob})} tasks | most common breaks in solved runs: "
      f"{collections.Counter(k for r in S for k, v in r['br'].items() if v).most_common()}")
print("solve rate: obedient runs", f"{sum(r['ok'] for r in rows if not sum(r['br'].values()))}/{sum(1 for r in rows if not sum(r['br'].values()))}",
      "| runs breaking something", f"{sum(r['ok'] for r in rows if sum(r['br'].values()))}/{sum(1 for r in rows if sum(r['br'].values()))}")

print("\nsolve rate by what the run did at its FIRST banner (runs with no edit when it came):")
B = [r for r in rows if r["ev"]["banner"]]
for lab, f in (("edit on the next call", lambda r: r["br"]["banner"] == 0), ("edit within 3 calls", lambda r: 1 < r["ev"]["banner_gap"] <= 3),
               ("edit 4+ calls later", lambda r: 3 < r["ev"]["banner_gap"] < 99), ("never edited", lambda r: r["ev"]["banner_gap"] == 99)):
    X = [r for r in B if f(r)]
    print(f"  {lab:24} {sum(r['ok'] for r in X):3}/{len(X):3} solved ({sum(r['ok'] for r in X) / max(len(X), 1):.0%})")
N = [r for r in rows if not r["ev"]["banner"]]
print(f"  {'no banner before edit':24} {sum(r['ok'] for r in N):3}/{len(N):3} solved ({sum(r['ok'] for r in N) / max(len(N), 1):.0%})")
print("\nsame task (task difficulty held fixed): solve rate of obedient vs rule-breaking runs, tasks with both kinds")
T = collections.defaultdict(lambda: [[0, 0], [0, 0]])
for r in rows:
    k = 0 if not sum(r["br"].values()) else 1
    T[r["task"]][k][0] += r["ok"]; T[r["task"]][k][1] += 1
both = {t: v for t, v in T.items() if v[0][1] and v[1][1]}
up = sum(v[0][0] / v[0][1] > v[1][0] / v[1][1] for v in both.values()); dn = sum(v[0][0] / v[0][1] < v[1][0] / v[1][1] for v in both.values())
print(f"  {len(both)} tasks | obedient higher on {up}, lower on {dn} | pooled obedient {sum(v[0][0] for v in both.values())}/{sum(v[0][1] for v in both.values())} "
      f"vs breaking {sum(v[1][0] for v in both.values())}/{sum(v[1][1] for v in both.values())}")
for t, v in sorted(both.items()): print(f"    {t:16} obedient {v[0][0]}/{v[0][1]}  breaking {v[1][0]}/{v[1][1]}")
