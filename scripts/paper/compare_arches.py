"""Task-paired comparison of agent families from data/analysis/run_table.jsonl. Prints no task text."""
import collections, json, random, re, statistics as st, sys
R = [json.loads(l) for l in open("data/analysis/run_table.jsonl")]
T = {json.loads(l)["instance_id"]: json.loads(l) for l in open("data/tasks.jsonl")}
SP = json.load(open("data/splits_public.json")); DEV = set(SP["dev16"])
random.seed(7)
C8 = {"sq1c", "sq1c2", "sq1c3", "sq1c4", "sq1c2a8", "sq1c2a8ra", "sq1c2a8rc"}
C6 = {"sq1c2t6", "sq1c2f6", "sq1c2f6ra", "sq1c2f6rc", "sq1c2a6", "sq1c2a6c", "sq1c2a6rc", "sq1c2a6rn", "sq1c2a6rnt", "sq1c2a6i"}
def group(a):
    if a == "bf": return "bf"
    if a in ("mix", "mix_r1", "mix_r2"): return "mix"
    if a == "pub024": return "pub"
    if a in ("sk_a2", "sk_a2_32"): return "skA2"
    if a in C8: return "clock8"
    if a == "sq1c2t7": return "clock7"
    if a in C6: return "clock6"
    if a in ("sq1", "sq2"): return "seq"
    if a in ("srep7", "srep8"): return "srep"
    if a and re.match(r"le\d", a) or a == "le": return "le"
    if a and a.startswith("sk_nav"): return "nav"
    return None
for r in R: r["g"] = group(r["arm"])
R = [r for r in R if r["g"]]
G = ["bf", "mix", "pub", "skA2", "le", "nav", "seq", "clock8", "clock7", "clock6", "srep"]
by = lambda g: [r for r in R if r["g"] == g]
def tm(rows, f):
    d = collections.defaultdict(list)
    for r in rows:
        v = f(r)
        if v is not None: d[r["iid"]].append(v)
    return {t: st.mean(v) for t, v in d.items()}
def boot(diffs, n=4000):
    if not diffs: return (0, 0)
    xs = sorted(st.mean(random.choices(diffs, k=len(diffs))) for _ in range(n))
    return xs[int(.025 * n)], xs[int(.975 * n)]
print("== A. runs and tasks per group")
for g in G:
    x = by(g); print(f"{g:7} runs {len(x):4} tasks {len({r['iid'] for r in x}):3} dev16 runs {sum(r['iid'] in DEV for r in x):3} solved {sum(r['resolved'] for r in x)}")
print("\n== B. dev16 (same 16 hard tasks): solves per 16, by per-task rate; groups with all or most of dev16")
for g in G:
    x = [r for r in by(g) if r["iid"] in DEV]
    m = tm(x, lambda r: float(r["resolved"]))
    if len(m) < 8: print(f"{g:7} only {len(m)} dev16 tasks"); continue
    lo, hi = boot(list(m.values()))
    n = len(x)
    oc = collections.Counter(r["outcome"] for r in x)
    w = [r for r in x if r["outcome"] == "wrong_edit"]
    print(f"{g:7} tasks {len(m):2} runs {n:3}: {sum(m.values()):.1f} of {len(m)} ({lo*len(m):.1f}-{hi*len(m):.1f}) | solved {oc['solved']/n:.0%} wrong {oc['wrong_edit']/n:.0%} none {oc['no_patch']/n:.0%} | wrong in gold file {sum(r['edited_gold']>0 for r in w)}/{len(w)} | s {st.mean(r['agent_s'] for r in x):.0f}")
print("\n== C. each group vs pub on the tasks both ran (paired by task; CI by resampling tasks)")
pm = tm(by("pub"), lambda r: float(r["resolved"]))
for g in G:
    if g == "pub": continue
    m = tm(by(g), lambda r: float(r["resolved"]))
    com = sorted(set(m) & set(pm))
    if not com: continue
    d = [m[t] - pm[t] for t in com]
    lo, hi = boot(d)
    tmS = tm(by(g), lambda r: r["agent_s"]); pS = tm(by("pub"), lambda r: r["agent_s"])
    print(f"{g:7} common {len(com):2} tasks: {g} {st.mean(m[t] for t in com):.0%} pub {st.mean(pm[t] for t in com):.0%} diff {st.mean(d)*100:+.0f} pts ({lo*100:+.0f} to {hi*100:+.0f}) | seconds {st.mean(tmS[t] for t in com):.0f} vs {st.mean(pS[t] for t in com):.0f}")
print("\n== D. behaviour per run, paired with pub on common tasks (group value / pub value)")
F = {"turns": lambda r: r["turns"], "tokens": lambda r: r["tokens"], "tok/turn": lambda r: r["tokens"] / max(1, r["turns"]), "long turns>=2k": lambda r: r["long_turns"],
     "tok before 1st edit": lambda r: r["tok_pre"] if r["n_edits"] else None, "1st edit s": lambda r: r["first_edit"], "1st edit call": lambda r: r["first_edit_call"],
     "search pre": lambda r: r["pre"].get("search", 0), "read pre": lambda r: r["pre"].get("read", 0), "read tests pre": lambda r: r["pre"].get("read_tests", 0), "exec pre": lambda r: r["pre"].get("exec", 0), "test pre": lambda r: r["pre"].get("test", 0), "scratch pre": lambda r: r["pre"].get("write_scratch", 0),
     "exec all": lambda r: r["kinds"].get("exec", 0), "test all": lambda r: r["kinds"].get("test", 0), "edits": lambda r: r["n_edits"], "edit_fail": lambda r: r["kinds"].get("edit_fail", 0), "git": lambda r: r["kinds"].get("git", 0),
     "reread": lambda r: r["reread"], "repeat cmd": lambda r: r["repeat_cmd"], "garbled": lambda r: r["kinds"].get("garbled", 0), "refused": lambda r: r["kinds"].get("refused", 0),
     "submit calls": lambda r: r["kinds"].get("submit", 0), "s after submit": lambda r: (r["end_turn"] - r["first_submit"]) if r["first_submit"] is not None else 0,
     "s after last edit": lambda r: (r["agent_s"] - r["last_edit"]) if r["last_edit"] is not None and not r["first_submit"] else ((r["first_submit"] - r["last_edit"]) if r["last_edit"] is not None else None),
     "no patch %": lambda r: 100.0 * (not r["patch"]), "wrong %": lambda r: 100.0 * (r["outcome"] == "wrong_edit"), "read gold %": lambda r: 100.0 * r["read_gold"], "edit gold % (of edits)": lambda r: (100.0 * (r["edited_gold"] > 0)) if r["n_edits"] else None}
GG = ["bf", "mix", "skA2", "seq", "clock8", "clock6"]
print(f"{'feature':24}" + "".join(f"{g:>14}" for g in GG))
for name, f in F.items():
    out = []
    p = tm(by("pub"), f)
    for g in GG:
        m = tm(by(g), f); c = set(m) & set(p)
        out.append(f"{st.mean(m[t] for t in c):.1f}/{st.mean(p[t] for t in c):.1f}" if c else "-")
    print(f"{name:24}" + "".join(f"{o:>14}" for o in out))
print("\n== E. within the same task and group: does a behaviour go with solving? (runs with vs without; Mantel-Haenszel style, CI by resampling tasks)")
GS = {"pub", "mix", "bf", "skA2", "seq", "clock8", "clock7", "clock6", "le"}
def mh(rows, feat):
    st_ = collections.defaultdict(lambda: [[0, 0], [0, 0]])
    for r in rows:
        v = feat(r)
        if v is None: continue
        c = st_[r["iid"], r["g"]][int(bool(v))]; c[0] += r["resolved"]; c[1] += 1
    items = [(k, v) for k, v in st_.items() if v[0][1] and v[1][1]]
    def est(it):
        n = sum(v[0][1] * v[1][1] / (v[0][1] + v[1][1]) for _, v in it)
        if not n: return 0
        return sum((v[1][0] / v[1][1] - v[0][0] / v[0][1]) * v[0][1] * v[1][1] / (v[0][1] + v[1][1]) for _, v in it) / n
    tasks = sorted({k[0] for k, _ in items})
    bt = collections.defaultdict(list)
    for k, v in items: bt[k[0]].append((k, v))
    xs = []
    for _ in range(1500):
        it = [i for t in random.choices(tasks, k=len(tasks)) for i in bt[t]]
        xs.append(est(it))
    xs.sort()
    wn = sum(v[1][1] for _, v in items); won = sum(v[0][1] for _, v in items)
    return est(items), xs[int(.025 * 1500)], xs[int(.975 * 1500)], wn, won, len(tasks)
pool = [r for r in R if r["g"] in GS]
edited = [r for r in pool if r["n_edits"]]
TESTS = [("--- before the first edit (all runs that edited)", None, None),
  ("read a gold file before 1st edit", edited, lambda r: r["first_read_gold"] is not None and r["first_read_gold"] <= r["first_edit"]),
  ("read tests before 1st edit", edited, lambda r: r["pre"].get("read_tests", 0) > 0),
  ("ran a script before 1st edit", edited, lambda r: r["pre"].get("exec", 0) > 0),
  ("ran 3+ scripts before 1st edit", edited, lambda r: r["pre"].get("exec", 0) >= 3),
  ("ran tests before 1st edit", edited, lambda r: r["pre"].get("test", 0) > 0),
  ("wrote scratch before 1st edit", edited, lambda r: r["pre"].get("write_scratch", 0) > 0),
  ("6+ reads before 1st edit", edited, lambda r: r["pre"].get("read", 0) >= 6),
  ("6+ searches before 1st edit", edited, lambda r: r["pre"].get("search", 0) >= 6),
  ("1st edit by call 12", edited, lambda r: r["first_edit_call"] <= 12),
  ("1st edit by 120 s", edited, lambda r: r["first_edit"] <= 120),
  ("1st edit by 180 s", edited, lambda r: r["first_edit"] <= 180),
  ("1st edit by 240 s", edited, lambda r: r["first_edit"] <= 240),
  ("1st edit after 300 s", edited, lambda r: r["first_edit"] > 300),
  ("a 2000+ token turn anywhere", edited, lambda r: r["long_turns"] > 0),
  ("--- after the edit (runs that edited)", None, None),
  ("1st edit in a gold file", edited, lambda r: r["first_edit_gold"]),
  ("touched every gold file", edited, lambda r: r["all_gold"]),
  ("ran tests after edit", edited, lambda r: r["test_after_edit"] > 0),
  ("2+ edits", edited, lambda r: r["n_edits"] >= 2),
  ("4+ edits", edited, lambda r: r["n_edits"] >= 4),
  ("edited more files than gold", edited, lambda r: r["files_edited"] > r["n_gold"]),
  ("an edit_file failed", edited, lambda r: r["kinds"].get("edit_fail", 0) > 0),
  ("--- on all runs", None, None),
  ("any edit at all", pool, lambda r: r["n_edits"] > 0),
  ("garbled call", pool, lambda r: r["kinds"].get("garbled", 0) > 0),
  ("reread a file", pool, lambda r: r["reread"] > 0),
  ("repeated a command", pool, lambda r: r["repeat_cmd"] > 0)]
print(f"{'behaviour':38}{'diff pts':>9}{'95% CI':>14}{'runs with':>10}{'without':>8}{'tasks':>6}")
for name, rows, f in TESTS:
    if rows is None: print(name); continue
    e, lo, hi, a, b, t = mh(rows, f)
    print(f"{name:38}{e*100:+9.0f}{f'{lo*100:+.0f} to {hi*100:+.0f}':>14}{a:>10}{b:>8}{t:>6}")
print("\n== F. can the model tell? last test / repro status vs solved (runs that edited)")
for g in ["pub", "mix", "skA2", "clock8", "clock6"]:
    x = [r for r in by(g) if r["n_edits"]]
    for lab, f in (("last test passed", lambda r: r["last_test"] == "pass"), ("last test failed", lambda r: r["last_test"] == "fail"), ("last test unclear", lambda r: r["last_test"] == "unclear"), ("no test", lambda r: r["last_test"] is None), ("repro passes", lambda r: r["fixed_at"] is not None), ("repro not passing", lambda r: r["fixed_at"] is None)):
        y = [r for r in x if f(r)]
        if y and (lab.startswith(("last", "no")) or g.startswith("clock")): print(f"{g:7} {lab:20} {sum(r['resolved'] for r in y):3}/{len(y):3} = {sum(r['resolved'] for r in y)/len(y):.0%}")
print("\n== G. clock refusals")
clock = [r for r in R if r["g"] in ("clock8", "clock7", "clock6")]
ty = collections.Counter(); rs = collections.Counter()
for r in clock:
    for k, v in r["refusals"].items(): ty[k] += v; rs[k] += 1
print("refusal counts", dict(ty), "runs with", dict(rs), "of", len(clock))
for k in ("noedit", "finish", "repeat"):
    e, lo, hi, a, b, t = mh(clock, lambda r: r["refusals"].get(k, 0) > 0)
    print(f"  within task: runs with a {k} refusal vs without: {e*100:+.0f} pts ({lo*100:+.0f} to {hi*100:+.0f}), {a} vs {b} runs, {t} tasks")
ne = [r for r in clock if r["refusals"].get("noedit")]
print("  noedit-refused runs:", len(ne), "then edited", sum(r["n_edits"] > 0 and (r["first_edit"] or 0) >= r["first_refusal"][1] - 1 for r in ne if r["first_refusal"] and r["first_refusal"][0] == "noedit"), "solved", sum(r["resolved"] for r in ne))
print("\n== H. by kind of task: solve rate on tasks all listed groups ran")
def kind(i):
    t = T[i]; n = len(t["problem_statement"]); g = re.findall(r"^\+\+\+ b/(\S+)", t["patch"], re.M); lines = sum(1 for l in t["patch"].splitlines() if l[:1] in "+-" and l[:3] not in ("+++", "---"))
    return ("issue<150" if n < 150 else "issue>=150"), ("1 file" if len(g) == 1 else "2+ files"), ("<=10 lines" if lines <= 10 else "11-40 lines" if lines <= 40 else ">40 lines"), t["repo"].split("/")[-1]
for g in ["mix", "skA2", "clock8", "clock6", "srep"]:
    m = tm(by(g), lambda r: float(r["resolved"])); com = set(m) & set(pm)
    for dim in range(4):
        d = collections.defaultdict(list)
        for t in com: d[kind(t)[dim]].append(t)
        print(f"  {g:7}" + " | ".join(f"{k} n={len(v)}: {st.mean(m[t] for t in v):.0%} vs pub {st.mean(pm[t] for t in v):.0%}" for k, v in sorted(d.items())))
print("\n== I. tools: seconds of model time per kind, per run; edit_file failure; garbled share of shell calls")
KK = ["search", "read", "exec", "test", "edit_ok", "edit_fail", "write_scratch", "git", "submit", "status"]
print(f"{'group':8}" + "".join(f"{k:>11}" for k in KK) + f"{'editfail%':>10}{'garbled%':>9}")
for g in G:
    x = by(g); n = len(x); c = collections.Counter(); ks = collections.Counter()
    for r in x: c.update(r["kind_s"]); ks.update(r["kinds"])
    ef = ks["edit_fail"] / max(1, ks["edit_ok"] + ks["edit_fail"]); gb = ks["garbled"] / max(1, ks["shell"] + ks["garbled"])
    print(f"{g:8}" + "".join(f"{c[k]/n:>11.0f}" for k in KK) + f"{ef:>10.0%}{gb:>9.0%}")
print("\n== J. prompt rules: are they followed? share of runs")
for g in G:
    x = by(g); n = len(x); ed = [r for r in x if r["n_edits"]]
    print(f"{g:8} edit by call 12 {sum(r['first_edit_call']<=12 for r in ed)/n:.0%} | no edit at all {sum(not r['n_edits'] for r in x)/n:.0%} | >2 test runs {sum(r['kinds'].get('test',0)>2 for r in x)/n:.0%} | any test {sum(r['kinds'].get('test',0)>0 for r in x)/n:.0%} | scripts before edit {sum(r['pre'].get('exec',0)>0 for r in x)/n:.0%} | 1st-edit call median {st.median([r['first_edit_call'] for r in ed] or [0]):.0f}, s {st.median([r['first_edit'] for r in ed] or [0]):.0f}")
print("\n== K. how much is task vs agent? variance of solved over runs (per-task + per-group means)")
x = [r for r in R if r["g"] in ("bf", "mix", "pub", "skA2", "le", "seq", "clock8", "clock6", "clock7")]
y = [float(r["resolved"]) for r in x]; mean = st.mean(y); tot = sum((v - mean) ** 2 for v in y)
tmn = tm(x, lambda r: float(r["resolved"])); ss_t = sum((tmn[r["iid"]] - mean) ** 2 for r in x)
res = collections.defaultdict(list)
for r in x: res[r["g"]].append(float(r["resolved"]) - tmn[r["iid"]])
ss_g = sum(len(v) * st.mean(v) ** 2 for v in res.values())
print(f"runs {len(x)}, tasks {len(tmn)}: task explains {ss_t/tot:.0%}, agent family (after task) {ss_g/tot:.1%}, rest {1-ss_t/tot-ss_g/tot:.0%}")
print("per-task solve rate correlation with pub:")
for g in ["mix", "bf", "skA2", "seq", "clock8", "clock6", "srep"]:
    m = tm(by(g), lambda r: float(r["resolved"])); c = sorted(set(m) & set(pm))
    if len(c) > 3:
        a = [m[t] for t in c]; b = [pm[t] for t in c]; sa, sb = st.pstdev(a), st.pstdev(b)
        cr = (sum((p - st.mean(a)) * (q - st.mean(b)) for p, q in zip(a, b)) / len(a) / (sa * sb)) if sa and sb else 0
        print(f"  {g:7} r={cr:.2f} over {len(c)} tasks")
print("tasks solved at least once / attempted, by group:")
for g in G:
    m = tm(by(g), lambda r: float(r["resolved"])); print(f"  {g:7} {sum(v>0 for v in m.values())}/{len(m)}")
allm = tm(x, lambda r: float(r["resolved"]))
print("pooled: never solved", sum(v == 0 for v in allm.values()), "| below 20%", sum(0 < v < .2 for v in allm.values()), "| 20-80%", sum(.2 <= v <= .8 for v in allm.values()), "| above 80%", sum(v > .8 for v in allm.values()), "of", len(allm))
