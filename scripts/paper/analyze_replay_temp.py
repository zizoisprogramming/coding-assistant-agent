"""Score kaggle/cells_replay_temp output: per temperature, is the first call an edit, is it well formed, does it match the file, is it on the real fix's lines?
Usage: python3 -I scripts/paper/analyze_replay_temp.py results.jsonl   (needs data/analysis/gold_files, scripts/paper/fetch_gold_files.py). Prints no task text."""
import ast, bisect, collections, json, os, random, re, statistics as st, sys
T = {json.loads(l)["instance_id"]: json.loads(l) for l in open("data/tasks.jsonl")}
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$|pytest\.ini$")
random.seed(9)
def regions(patch):
    out = {}; cur = None; ln = 0
    for line in patch.splitlines():
        m = re.match(r"\+\+\+ b/(\S+)", line)
        if m: cur = out.setdefault(m.group(1), []); continue
        if line.startswith("--- "): continue
        m = re.match(r"@@ -(\d+)(?:,\d+)? ", line)
        if m: ln = int(m.group(1)); cur.append([None, None]); continue
        if not cur or line[:1] not in " +-": continue
        if line[:1] == "-": cur[-1][0] = cur[-1][0] or ln; cur[-1][1] = ln; ln += 1
        elif line[:1] == "+": cur[-1][0] = cur[-1][0] or ln; cur[-1][1] = max(cur[-1][1] or ln, ln)
        else: ln += 1
    return {f: [(a, b) for a, b in r if a] for f, r in out.items() if not TEST.search(f)}
def where(iid, path, old):
    reg = regions(T[iid]["patch"])
    if path not in reg: return "other file"
    p = f"data/analysis/gold_files/{iid}/{path}"
    if not os.path.exists(p): return "gold file, unknown line"
    text = open(p, errors="replace").read()
    i = text.find(old) if old else -1
    if i < 0: return "gold file, old_string not in file"
    a = text.count("\n", 0, i) + 1; b = a + old.count("\n")
    if any(a <= y + 2 and b >= x - 2 for x, y in reg[path]): return "on the real lines"
    try:
        defs = [n for n in ast.walk(ast.parse(text)) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    except SyntaxError:
        defs = []
    def scope(l):
        h = [n for n in defs if n.lineno <= l <= n.end_lineno]
        return max(h, key=lambda n: n.lineno).name if h else None
    if scope(a) and scope(a) in {scope(x) for r in reg.values() for x, _ in r}: return "same function"
    return "gold file, elsewhere"
R = [json.loads(l) for l in open(sys.argv[1])]
errs = sum("error" in r for r in R); R = [r for r in R if "error" not in r]
print(len(R), "calls,", errs, "errors,", len({r["ctx"] for r in R}), "contexts")
rows = collections.defaultdict(list)
for r in R:
    iid = r["job_id"].split("#")[0]; c = r["calls"][0] if r["calls"] else None
    k = "text, no call"
    if c:
        if c["name"] != "edit_file": k = "other tool: looks further"
        else:
            try: a = json.loads(c["arguments"])
            except ValueError: a = {}
            old, path = a.get("old_string"), str(a.get("filepath") or "")
            if not old or "old_string" in str(a.get("new_string", "")): k = "malformed edit"
            elif TEST.search(path): k = "test file"
            else: k = where(iid, path, old)
    r["k"] = k; rows[r["T"]].append(r)
keys = ["on the real lines", "same function", "gold file, elsewhere", "gold file, old_string not in file", "gold file, unknown line", "other file", "test file", "malformed edit", "other tool: looks further", "text, no call"]
print(f"{'':36}" + "".join(f"T={t:<8}" for t in sorted(rows)))
for k in keys:
    print(f"{k:36}" + "".join(f"{sum(r['k']==k for r in rows[t])/len(rows[t]):<10.0%}" for t in sorted(rows)))
print(f"{'tokens, mean':36}" + "".join(f"{st.mean(r['tokens'] or 0 for r in rows[t]):<10.0f}" for t in sorted(rows)))
print(f"{'seconds, mean':36}" + "".join(f"{st.mean(r['seconds'] for r in rows[t]):<10.0f}" for t in sorted(rows)))
print("original call on the real lines:", f"{st.mean(where(r['job_id'].split('#')[0], r['orig']['filepath'], r['orig'].get('old_string'))=='on the real lines' for r in R):.0%}")
print("\npaired by context, share on the real lines vs T=0.2 (95% by resampling tasks):")
by = collections.defaultdict(lambda: collections.defaultdict(list))
for r in R: by[r["ctx"]][r["T"]].append(r["k"] == "on the real lines")
base = min(rows)
task = {r["ctx"]: r["job_id"].split("#")[0] for r in R}
for t in sorted(rows):
    if t == base: continue
    d = collections.defaultdict(list)
    for c, v in by.items():
        if v.get(t) and v.get(base): d[task[c]].append(st.mean(v[t]) - st.mean(v[base]))
    m = [st.mean(x) for x in d.values()]
    xs = sorted(st.mean(random.choices(m, k=len(m))) for _ in range(3000))
    print(f"  T={t}: {st.mean(m)*100:+.0f} pts ({xs[75]*100:+.0f} to {xs[2925]*100:+.0f}), {len(m)} tasks")
print("does any sample land on the real lines when the original did not? (exploring)")
hit = collections.Counter()
for c, v in by.items():
    q = next(r for r in R if r["ctx"] == c)
    if where(task[c], q["orig"]["filepath"], q["orig"].get("old_string")) != "on the real lines":
        for t in rows: hit[t, any(v.get(t, []))] += 1
for t in sorted(rows): print(f"  T={t}: {hit[t, True]} of {hit[t, True] + hit[t, False]} contexts")
