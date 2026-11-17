# Run: python3 -I scripts/mine_bank/calls_by_outcome.py   (current line pub024, sa2, sb1; builds on big_slices.py)
import re, collections, json, sys, statistics as st
src = open("scripts/mine_bank/big_slices.py").read()
src = src.replace('rows.append(dict(arm=g["arm"]', 'SEQ.append((g["arm"], iid, sl, sub, [(n, a, o) for (n, a, o, t) in seq])); rows.append(dict(arm=g["arm"]')
src = src.split("\ndef report")[0]
SEQ = []
sys.argv = ["x", "pub024,sa2,sb1"]
exec(src)
def k(n, a, o):
    if o and ("mandatory input parameters" in o or "not present" in o): return "garbled"
    cmd = str(a.get("command", ""))
    if n in ("edit_file",): return "edit"
    if n == "write_file": return "write"
    if n == "read_file" or re.search(r"\b(sed -n|cat|head|tail|nl)\b", cmd): return "read"
    if re.search(r"pytest|unittest", cmd): return "test"
    if re.search(r"<<|python3? -c|python3? \S+\.py", cmd): return "run python"
    if re.search(r"\b(grep|rg|find|ls|git grep|git log|git show)\b", cmd): return "search"
    if n == "submit_patch": return "submit"
    return n
def group(sl, sub):
    if sl == "solved": return "solved"
    if sl == "no patch" and sub in ("never tried an edit", "every edit attempt failed"): return "no patch: no edit in time"
    if sl == "no patch": return "no patch: other"
    return "wrong patch"
agg = collections.defaultdict(list)
for arm, iid, sl, sub, s in SEQ:
    if sl == "patch, files not on disk": continue
    c = collections.Counter(k(*x) for x in s)
    # repeated reads of the same file region
    reads = [(x[1].get("filepath"), x[1].get("start_line")) for x in s if x[0] == "read_file"]
    rep = len(reads) - len(set(reads))
    agg[group(sl, sub)].append((c, len(s), rep))
kinds = ["search", "read", "run python", "test", "write", "edit", "garbled", "submit"]
print(f"{'':28}" + "".join(f"{x:>11}" for x in kinds) + "   calls  repeat-reads  runs-with-garbled")
for g, xs in agg.items():
    print(f"{g:28}" + "".join(f"{st.mean(c[x] for c, n, r in xs):11.1f}" for x in kinds) + f"   {st.mean(n for c, n, r in xs):5.1f}  {st.mean(r for c, n, r in xs):8.1f}   {100*st.mean(c['garbled'] > 0 for c, n, r in xs):5.0f}%  (n={len(xs)})")
# garbled cost within task: solved rate of runs with vs without garbled calls, same task
by = collections.defaultdict(lambda: [[0, 0], [0, 0]])
for arm, iid, sl, sub, s in SEQ:
    if sl == "patch, files not on disk": continue
    gb = any(k(*x) == "garbled" for x in s)
    by[iid][gb][0] += sl == "solved"; by[iid][gb][1] += 1
w = [(v[0][0] / v[0][1], v[1][0] / v[1][1], min(v[0][1], v[1][1])) for v in by.values() if v[0][1] >= 2 and v[1][1] >= 2]
print(f"\nsame task, tasks with >= 2 runs with and without a garbled call: {len(w)} tasks; solved rate without {st.mean(a for a, b, n in w):.2f} vs with {st.mean(b for a, b, n in w):.2f}; tasks where garbled runs did worse {sum(b < a for a, b, n in w)}, better {sum(b > a for a, b, n in w)}")
