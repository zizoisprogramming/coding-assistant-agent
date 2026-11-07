"""Single-change comparisons (same task, usually same run), call-limit what-if, edit failures. Prints no task text."""
import collections, glob, json, random, re, statistics as st
R = [json.loads(l) for l in open("data/analysis/run_table.jsonl")]
random.seed(3)
def tm(a, f=lambda r: float(r["resolved"]), folder=None):
    d = collections.defaultdict(list)
    for r in R:
        if r["arm"] == a and (folder is None or r["folder"] in folder): d[r["iid"]].append(f(r))
    return {k: st.mean(v) for k, v in d.items()}
def pair(name, a, b):
    A, B = tm(b), tm(a); c = sorted(set(A) & set(B))
    if not c: print(name, "no common"); return
    d = [A[t] - B[t] for t in c]
    xs = sorted(st.mean(random.choices(d, k=len(d))) for _ in range(3000))
    sA, sB = tm(b, lambda r: r["agent_s"]), tm(a, lambda r: r["agent_s"])
    fold = lambda x: {r["folder"] for r in R if r["arm"] == x}
    same = bool(fold(a) & fold(b))
    print(f"{name:44} {a}->{b}: {st.mean(B[t] for t in c):.0%}->{st.mean(A[t] for t in c):.0%} ({st.mean(d)*100:+.0f} pts, {xs[75]*100:+.0f} to {xs[2925]*100:+.0f}) | {st.mean(sB[t] for t in c):.0f}->{st.mean(sA[t] for t in c):.0f} s | {len(c)} tasks | {'same run' if same else 'different runs'}")
print("== single changes")
for n, a, b in [("clock added to fixer/finisher", "sq1", "sq1c"), ("clock + call-shape fix", "sq1", "sq1c2"), ("fixer/finisher split added to pub", "pub024", "sq1"), ("clock+split vs pub", "pub024", "sq1c2"),
    ("second attempt added", "sq1", "sq2"), ("reads through clock", "sq1c2", "sq1c3"), ("thinking 4096->2048 (clock)", "sq1c2", "sq1c4"), ("thinking 4096->2048 (rn)", "sq1c2a6rn", "sq1c2a6rnt"),
    ("cap 8->7 min", "sq1c2", "sq1c2t7"), ("cap 8->6 min + finish rule", "sq1c2a8", "sq1c2a6"), ("finish window on (6 min)", "sq1c2t6", "sq1c2f6"),
    ("repeat block (8 min)", "sq1c2a8", "sq1c2a8ra"), ("checklist+repeat (8 min)", "sq1c2a8ra", "sq1c2a8rc"), ("repeat block (6 min)", "sq1c2f6", "sq1c2f6ra"), ("checklist (6 min f)", "sq1c2f6ra", "sq1c2f6rc"),
    ("checklist (6 min a)", "sq1c2a6", "sq1c2a6c"), ("checklist+repeat (6 min a)", "sq1c2a6", "sq1c2a6rc"), ("no-bug note", "sq1c2a6", "sq1c2a6rn"),
    ("28->32 calls (skill)", "sk_a2", "sk_a2_32"), ("reader skill vs pub", "pub024", "sk_a2"), ("nav skill vs reader skill", "sk_a2", "sk_nav_s6_32"), ("fixer+reviewer", "pub024", "sk_fr"), ("fixer+reviewer 2", "pub024", "sk_fr2"),
    ("read skill+lead vs pub", "pub024", "sa2"), ("3 parallel fixers vs pub", "pub024", "bo3"), ("bf -> mix (rule, thinking 2048)", "bf", "mix"), ("locator-editor vs mix", "mix", "le5"), ("reporter vs pub", "pub024", "srep7"), ("reporter2 vs pub", "pub024", "srep8")]:
    pair(n, a, b)
print("\n== how each arm ends: budget-counted calls and the 28-call limit")
for lab, arms in (("pub", ["pub024"]), ("mix", ["mix", "mix_r1", "mix_r2"]), ("skA2", ["sk_a2"]), ("sq1c2 (8m,80)", ["sq1c2"]), ("a8 family", ["sq1c2a8", "sq1c2a8ra", "sq1c2a8rc"]), ("t7", ["sq1c2t7"]), ("a6 family", ["sq1c2a6", "sq1c2a6c", "sq1c2a6rc", "sq1c2a6i"])):
    x = [r for r in R if r["arm"] in arms]; n = len(x)
    so = [r for r in x if r["resolved"]]; fa = [r for r in x if not r["resolved"]]
    over = [r for r in x if r["budget_calls"] >= 28]
    print(f"{lab:14} runs {n:4} mean calls {st.mean(r['budget_calls'] for r in x):.0f} | reach 28 calls: {len(over)/n:.0%} | solved runs past 28 calls {sum(r['budget_calls']>28 for r in so)}/{len(so)} | seconds at call 28 median {st.median([r['time_at_28'] for r in over] or [0]):.0f} | mean s failed {st.mean(r['agent_s'] for r in fa):.0f} solved {st.mean(r['agent_s'] for r in so):.0f}")
print("\n== what-if: clock arms stopped at the 28th budget call (patch so far stands; solve lost if any edit after it, or if not yet edited)")
for lab, arms in (("sq1c2", ["sq1c2"]), ("a8", ["sq1c2a8"]), ("a8ra", ["sq1c2a8ra"]), ("a8rc", ["sq1c2a8rc"]), ("t7", ["sq1c2t7"]), ("a6", ["sq1c2a6", "sq1c2a6i"])):
    x = [r for r in R if r["arm"] in arms]
    new = []; lost = 0
    for r in x:
        t = r["time_at_28"]
        if t is None: new.append(r["agent_s"]); continue
        new.append(min(r["agent_s"], t))
        if r["resolved"] and (r["last_edit"] is None or r["last_edit"] > t): lost += 1
    print(f"{lab:6} runs {len(x):3} solved {sum(r['resolved'] for r in x):3} lost {lost:2} | mean agent s {st.mean(r['agent_s'] for r in x):.0f} -> {st.mean(new):.0f}")
print("\n== phases: mean seconds per run (paired tasks not applied)")
for lab, arms in (("bf", ["bf"]), ("mix", ["mix", "mix_r1", "mix_r2"]), ("pub", ["pub024"]), ("skA2", ["sk_a2", "sk_a2_32"]), ("sq1", ["sq1"]), ("sq1c2", ["sq1c2"]), ("a8", ["sq1c2a8"]), ("t7", ["sq1c2t7"]), ("a6", ["sq1c2a6"])):
    x = [r for r in R if r["arm"] in arms]; n = len(x)
    pre = sum((r["first_edit"] if r["n_edits"] else r["agent_s"]) or 0 for r in x) / n
    mid = sum((r["last_edit"] - r["first_edit"]) for r in x if r["n_edits"] and r["last_edit"] is not None) / n
    end = sum(max(0, ((r["first_submit"] or r["agent_s"]) - r["last_edit"])) for r in x if r["n_edits"] and r["last_edit"] is not None) / n
    sub = sum((r["end_turn"] - r["first_submit"]) for r in x if r["first_submit"] is not None) / n
    print(f"{lab:6} n={n:3} before 1st edit {pre:4.0f} | between edits {mid:4.0f} | last edit to submit/end {end:4.0f} | after submit {sub:4.0f} | total {st.mean(r['agent_s'] for r in x):.0f}")
print("\n== time on tasks nobody solves vs tasks someone solves (pub, mix, clock)")
allr = collections.defaultdict(list)
for r in R: allr[r["iid"]].append(r["resolved"])
never = {t for t, v in allr.items() if sum(v) == 0 and len(v) >= 6}
print("tasks never solved in any logged run with 6+ runs:", len(never), "of", sum(len(v) >= 6 for v in allr.values()))
for lab, arms in (("pub", ["pub024"]), ("mix", ["mix", "mix_r1", "mix_r2"]), ("a8", ["sq1c2a8"]), ("a6", ["sq1c2a6"])):
    x = [r for r in R if r["arm"] in arms]; a = [r["agent_s"] for r in x if r["iid"] in never]; b = [r["agent_s"] for r in x if r["iid"] not in never]
    print(f"{lab:4} never-solved tasks {st.mean(a) if a else 0:.0f} s (n={len(a)}) | others {st.mean(b) if b else 0:.0f} s (n={len(b)})")
print("\n== edit_file failures: messages (first 60 chars of the error), all logged request runs")
msg = collections.Counter(); oldlen = collections.defaultdict(list); nm = collections.Counter()
for f in sorted(glob.glob("data/results/*/requests/requests.jsonl"))[-16:]:
    for line in open(f):
        r = json.loads(line)
        if not isinstance(r.get("reply"), dict): continue
        ms = r["request"]["messages"]
        calls = {}
        for m in ms:
            for c in m.get("tool_calls") or []: calls[c.get("id")] = c
        if ms and ms[-1].get("role") == "tool":
            c = calls.get(ms[-1].get("tool_call_id"))
            if c and c["function"]["name"] == "edit_file":
                t = str(ms[-1].get("content")); arm = (r.get("job") or "").split("#a")[-1].split(".")[0]
                try: a = json.loads(c["function"]["arguments"])
                except Exception: a = {}
                ok = '"error"' not in t and "error_type" not in t
                nm["ok" if ok else "fail"] += 1
                oldlen["ok" if ok else "fail"].append(len(str(a.get("old_string", ""))))
                if not ok:
                    m_ = re.search(r'"(?:error|message)"\s*:\s*"([^"]{0,70})', t)
                    msg[re.sub(r"[`'\w/.]*\.py|\d+", "#", (m_.group(1) if m_ else t[:60]))[:60]] += 1
print(dict(nm)); print({k: (round(st.median(v)), len(v)) for k, v in oldlen.items()})
for k, v in msg.most_common(10): print(f"  {v:5} {k}")
