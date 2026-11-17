# Run: python3 -I scripts/mine_bank/pre_edit_calls.py [ARMS]   (default current line pub024,sa2,sb1; builds on big_slices.py). Calls before the first edit, re-read kinds, same-task first-14-call composition, s/reply, candidate tasks for the no-edit trials.
import re, collections, json, sys, statistics as st
src = open("scripts/mine_bank/big_slices.py").read()
src = src.replace('        for i, r in enumerate(R):\n            cs, _ = calls(r.get("reply") or r.get("response") or {})',
                  '        NPAR.extend(len(calls(r.get("reply") or {})[0]) for r in R)\n        for i, r in enumerate(R):\n            cs, _ = calls(r.get("reply") or r.get("response") or {})')
src = src.replace('rows.append(dict(arm=g["arm"]', 'SEQ.append((g["arm"], iid, sl, sub, [(n, a, o) for (n, a, o, t) in seq])); rows.append(dict(arm=g["arm"]')
src = src.split("\ndef report")[0]
SEQ, NPAR = [], []
sys.argv = ["x", sys.argv[1] if len(sys.argv) > 1 else "pub024,sa2,sb1"]
exec(src)
def k(n, a):
    c = str(a.get("command", ""))
    if n == "read_file": return "read_file"
    if n == "run_command":
        if re.search(r"\b(sed -n|cat |head |tail |nl )", c) and not re.search(r"<<|python", c): return "shell read"
        if re.search(r"pytest", c): return "pytest"
        if re.search(r"<<|python3? -c|python3? \S+\.py", c): return "run python"
        if re.search(r"\b(grep|rg|find|ls|git grep|git log|git show)\b", c): return "search"
        return "other cmd"
    return n
def multi(a):
    c = str(a.get("command", ""))
    parts = [p for p in re.split(r"\n|;|&&", c) if re.search(r"\b(grep|sed -n|cat|head|find|ls)\b", p)]
    return len(parts) >= 2
print(f"replies: {len(NPAR)} | with 0 calls {sum(n == 0 for n in NPAR)}, 1 call {sum(n == 1 for n in NPAR)}, >= 2 calls {sum(n >= 2 for n in NPAR)} ({100 * sum(n >= 2 for n in NPAR) / len(NPAR):.1f}%)")
grp = collections.defaultdict(list)
for arm, iid, sl, sub, s in SEQ:
    if sl == "patch, files not on disk": continue
    ed = [i for i, (n, a, o) in enumerate(s) if n in ("edit_file", "write_file") and not str(path_of(a)).startswith(".git")]
    pre = s[:ed[0]] if ed else s
    g = "solved" if sl == "solved" else ("no patch: no edit in time" if sl == "no patch" and sub in ("never tried an edit", "every edit attempt failed") else ("no patch: other" if sl == "no patch" else "wrong patch"))
    c = collections.Counter(k(n, a) for n, a, o in pre)
    rc = [a for n, a, o in pre if n == "run_command"]
    files_read = [path_of(a) for n, a, o in pre if n == "read_file"]
    grp[g].append(dict(c=c, n=len(pre), multi=sum(multi(a) for a in rc), rc=len(rc), rereads=len(files_read) - len(set(files_read))))
kinds = ["search", "read_file", "shell read", "run python", "pytest", "other cmd", "write_file", "get_status"]
print(f"\ncalls BEFORE the first edit (mean per run)\n{'':28}" + "".join(f"{x:>11}" for x in kinds) + "   total  multi-cmd run_command  same-file re-reads")
for g, xs in grp.items():
    print(f"{g:28}" + "".join(f"{st.mean(x['c'][kk] for x in xs):11.1f}" for kk in kinds) + f"   {st.mean(x['n'] for x in xs):5.1f}   {sum(x['multi'] for x in xs) / max(1, sum(x['rc'] for x in xs)) * 100:5.0f}% of {sum(x['rc'] for x in xs):4}    {st.mean(x['rereads'] for x in xs):5.1f}   (n={len(xs)})")

def rng(a):
    try:
        s, e = int(a.get("start_line") or 1), int(a.get("end_line") or 0)
    except (TypeError, ValueError):
        return None
    return (s, e)
stats = collections.defaultdict(lambda: collections.Counter())
sizes = collections.defaultdict(list)
for arm, iid, sl, sub, s in SEQ:
    if sl == "patch, files not on disk": continue
    g = "solved" if sl == "solved" else ("no edit in time" if sl == "no patch" and sub in ("never tried an edit", "every edit attempt failed") else "other fail")
    ed = [i for i, (n, a, o) in enumerate(s) if n in ("edit_file", "write_file") and not str(path_of(a)).startswith(".git")]
    pre = s[:ed[0]] if ed else s
    seen = {}
    for n, a, o in pre:
        if n != "read_file": continue
        f, r = path_of(a), rng(a)
        if r and r[1] > 0: sizes[g].append(r[1] - r[0] + 1)
        if f in seen:
            prev = seen[f]
            if r in prev: stats[g]["exact repeat"] += 1
            elif r and any(p and p[1] > 0 and r[1] > 0 and not (r[1] < p[0] or r[0] > p[1]) for p in prev): stats[g]["overlapping range"] += 1
            else: stats[g]["new range of a file read before"] += 1
        else:
            stats[g]["first read of the file"] += 1
        seen.setdefault(f, []).append(r)
    stats[g]["runs"] += 1
print()
for g, c in stats.items():
    n = c["runs"]
    print(f"{g:16} per run: " + ", ".join(f"{k} {c[k] / n:.1f}" for k in ("first read of the file", "new range of a file read before", "overlapping range", "exact repeat")) + f" | read size median {st.median(sizes[g]) if sizes[g] else 0:.0f} lines")

per = collections.defaultdict(lambda: collections.defaultdict(list))
for arm, iid, sl, sub, s in SEQ:
    if sl == "patch, files not on disk": continue
    g = "S" if sl == "solved" else ("N" if sl == "no patch" and sub in ("never tried an edit", "every edit attempt failed") else None)
    if not g: continue
    ed = [i for i, (n, a, o) in enumerate(s) if n in ("edit_file", "write_file") and not str(path_of(a)).startswith(".git")]
    pre = s[:ed[0]] if ed else s
    rf = sum(1 for n, a, o in pre if n == "read_file")
    srch = sum(1 for n, a, o in pre if k(n, a) == "search")
    per[iid][g].append((rf, srch, len(pre)))
mix = {i: v for i, v in per.items() if len(v["S"]) >= 2 and len(v["N"]) >= 2}
print(f"\nsame task ({len(mix)} tasks with >= 2 solved and >= 2 no-edit-in-time runs), calls before the first edit (or all calls when none):")
for j, nm in ((0, "read_file"), (1, "search"), (2, "all calls")):
    a = [st.mean(x[j] for x in v["S"]) for v in mix.values()]; b = [st.mean(x[j] for x in v["N"]) for v in mix.values()]
    print(f"  {nm:10} solved {st.mean(a):5.1f} vs no edit {st.mean(b):5.1f} | tasks no-edit higher {sum(y > x for x, y in zip(a, b))}, lower {sum(y < x for x, y in zip(a, b))}")
# by the time solved runs make their first edit, how many read_file calls have they made (distribution)?
sv = sorted(x[0] for v in per.values() for x in v["S"])
print(f"solved runs, read_file calls before the first edit: median {st.median(sv)}, 75th {sv[int(.75 * len(sv))]}, 90th {sv[int(.9 * len(sv))]}")

K = 14
comp = collections.defaultdict(lambda: collections.defaultdict(list))
for arm, iid, sl, sub, s in SEQ:
    if iid not in mix or sl == "patch, files not on disk": continue
    g = "S" if sl == "solved" else ("N" if sl == "no patch" and sub in ("never tried an edit", "every edit attempt failed") else None)
    if not g or len(s) < K: continue
    first = s[:K]
    c = collections.Counter(k(n, a) for n, a, o in first)
    fl = [path_of(a) for n, a, o in first if n == "read_file"]
    comp[iid][g].append((c["read_file"], c["search"], c["run python"], c["edit_file"] + c["write_file"], len(fl) - len(set(fl)), len(set(fl))))
names = ["read_file", "search", "run python", "edit attempts", "same-file re-reads", "distinct files read"]
both = {i: v for i, v in comp.items() if v["S"] and v["N"]}
print(f"\nfirst {K} calls, same task ({len(both)} tasks):")
for j, nm in enumerate(names):
    a = [st.mean(x[j] for x in v["S"]) for v in both.values()]; b = [st.mean(x[j] for x in v["N"]) for v in both.values()]
    print(f"  {nm:20} solved {st.mean(a):4.1f} vs no edit {st.mean(b):4.1f} | tasks no-edit higher {sum(y > x for x, y in zip(a, b))}, lower {sum(y < x for x, y in zip(a, b))}")

pr = collections.defaultdict(lambda: collections.defaultdict(list))
for r in rows:
    g = "S" if r["sl"] == "solved" else ("N" if r["sl"] == "no patch" and r["sub"] in ("never tried an edit", "every edit attempt failed") else None)
    if g: pr[r["iid"]][g].append(r)
both = {i: v for i, v in pr.items() if len(v["S"]) >= 2 and len(v["N"]) >= 2}
a = [st.mean(x["s_per_reply"] for x in v["S"]) for v in both.values()]; b = [st.mean(x["s_per_reply"] for x in v["N"]) for v in both.values()]
print(f"\nseconds per reply, same task ({len(both)} tasks): solved {st.mean(a):.1f} vs no edit {st.mean(b):.1f} | tasks no-edit slower {sum(y > x for x, y in zip(a, b))}, faster {sum(y < x for x, y in zip(a, b))}")
tm = [x for v in both.values() for x in v["N"]]
print(f"no-edit runs in these tasks: {len(tm)}; ended by time (agent_s >= 450) {sum(x['agent_s'] >= 450 for x in tm)}, by call budget {sum(x['budget'] for x in tm)}; calls median {st.median(x['calls'] for x in tm)}")

print("\ntask (current line runs): runs, solved, no edit in time (time / budget), s/reply")
allr = collections.defaultdict(list)
for r in rows:
    allr[r["iid"]].append(r)
tot = [0, 0, 0]
for i in sorted(both, key=lambda i: -len(allr[i])):
    x = allr[i]
    ne = [r for r in x if r["sl"] == "no patch" and r["sub"] in ("never tried an edit", "every edit attempt failed")]
    tot[0] += len(x); tot[1] += sum(r["sl"] == "solved" for r in x); tot[2] += len(ne)
    print(f"  {i[:34]:34} {len(x):3} | solved {sum(r['sl'] == 'solved' for r in x) / len(x):4.2f} | no edit {len(ne) / len(x):4.2f} ({sum(r['agent_s'] >= 450 for r in ne)}/{sum(r['budget'] for r in ne)}) | s/reply {st.mean(r['s_per_reply'] for r in x):4.1f}")
print(f"  ALL {tot[0]} runs: solved {tot[1] / tot[0]:.2f}, no edit in time {tot[2] / tot[0]:.2f}")
sb1 = [r for i in both for r in allr[i] if r["arm"] == "sb1"]
print(f"  sb1 only on these tasks: {len(sb1)} runs, solved {sum(r['sl'] == 'solved' for r in sb1)}")
