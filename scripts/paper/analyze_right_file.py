"""Runs that edited the right file: file size, where the edit landed vs the real fix, what was read first. Prints no task text."""
import ast, bisect, collections, glob, json, os, random, re, statistics as st
T = {json.loads(l)["instance_id"]: json.loads(l) for l in open("data/tasks.jsonl")}
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$|pytest\.ini$")
random.seed(5)
def gold_regions(patch):
    """file -> list of (first, last) changed base lines."""
    out = {}
    cur = None
    for line in patch.splitlines():
        m = re.match(r"\+\+\+ b/(\S+)", line)
        if m: cur = out.setdefault(m.group(1), []); continue
        if line.startswith("--- "): continue
        m = re.match(r"@@ -(\d+)(?:,\d+)? ", line)
        if m: ln = int(m.group(1)); lo = hi = None; cur.append([None, None]); continue
        if cur is None or not cur or line[:1] not in " +-\\": continue
        if line[:1] == "-":
            cur[-1][0] = cur[-1][0] or ln; cur[-1][1] = ln; ln += 1
        elif line[:1] == "+":
            cur[-1][0] = cur[-1][0] or ln; cur[-1][1] = max(cur[-1][1] or ln, ln)
        elif line[:1] == " ": ln += 1
    return {f: [(a, b) for a, b in r if a] for f, r in out.items()}
class FileInfo:
    def __init__(self, text):
        self.text = text; self.lines = text.split("\n"); self.n = len(self.lines)
        self.off = [0]
        for l in self.lines: self.off.append(self.off[-1] + len(l) + 1)
        self.scopes = []
        try:
            for node in ast.walk(ast.parse(text)):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    self.scopes.append((node.lineno, node.end_lineno, node.name, isinstance(node, ast.ClassDef)))
        except Exception: pass
    def line_of(self, s):
        for cand in (s, s.strip(), next((x for x in s.split("\n") if x.strip()), "")):
            if cand:
                i = self.text.find(cand)
                if i >= 0:
                    a = bisect.bisect_right(self.off, i) - 1
                    return a + 1, a + 1 + cand.count("\n")
        return None
    def scope(self, ln):
        best = None
        for a, b, nm, cl in self.scopes:
            if a <= ln <= b and not cl and (best is None or a > best[0]): best = (a, b, nm)
        return best
    def by_name(self, name):
        nm = name.split(".")[-1]
        for a, b, x, _ in self.scopes:
            if x == nm: return (a, b)
FILES = {}
def info(i, f):
    k = (i, f)
    if k not in FILES:
        p = f"data/analysis/gold_files/{i}/{f}"
        FILES[k] = FileInfo(open(p, errors="replace").read()) if os.path.exists(p) else None
    return FILES[k]
def reads_of(name, a, res):
    """[(file, first, last)] line ranges read by one call; last None = to the end."""
    out = []
    if name == "read_file":
        p = str(a.get("filepath") or a.get("path") or "")
        s = a.get("start_line"); e = a.get("end_line")
        try: rs = json.loads(res) if res and res.startswith("{") else {}
        except Exception: rs = {}
        if rs.get("start_line"): s, e = rs["start_line"], rs.get("end_line")
        out.append((p, int(s or 1), int(e) if e else None))
    return out
def shell_reads(cmd):
    out = []
    for m in re.finditer(r"sed -n\s+['\"]?(\d+)(?:,(\d+))?p['\"]?\s+(\S+)", cmd): out.append((m.group(3), int(m.group(1)), int(m.group(2) or m.group(1))))
    for m in re.finditer(r"(?:^|[;&|]\s*)cat\s+([\w./-]+\.py)", cmd): out.append((m.group(1), 1, None))
    for m in re.finditer(r"head -n?\s*(\d+)\s+([\w./-]+\.py)", cmd): out.append((m.group(2), 1, int(m.group(1))))
    for m in re.finditer(r"a\.py show\s+([\w./-]+\.py)\s+(\d+)\s+(\d+)", cmd): out.append((m.group(1), int(m.group(2)), int(m.group(3))))
    for m in re.finditer(r"a\.py show\s+([\w./-]+\.py)\s+([A-Za-z_][\w.]*)", cmd): out.append((m.group(1), "name", m.group(2)))
    return out
def overlap(a, b, regions, slack=2):
    return any(a <= y + slack and b >= x - slack for x, y in regions)
ARMS = {"bf": "bf", "mix": "mix", "mix_r1": "mix", "mix_r2": "mix", "pub024": "pub", "sk_a2": "skA2", "sk_a2_32": "skA2", "sq1": "seq", "sq2": "seq"}
for a in "sq1c sq1c2 sq1c3 sq1c4 sq1c2a8 sq1c2a8ra sq1c2a8rc".split(): ARMS[a] = "clock8"
ARMS["sq1c2t7"] = "clock7"
for a in "sq1c2t6 sq1c2f6 sq1c2f6ra sq1c2f6rc sq1c2a6 sq1c2a6c sq1c2a6rc sq1c2a6rn sq1c2a6rnt sq1c2a6i".split(): ARMS[a] = "clock6"
ROWS = []
def analyse(iid, group, res, calls, folder):
    """calls: list of (name, args, result)."""
    t = T[iid]; reg = gold_regions(t["patch"]); src = {f: r for f, r in reg.items() if not TEST.search(f)}
    existing = {f: info(iid, f) for f in src}
    existing = {f: v for f, v in existing.items() if v}
    if not existing: return
    size = max(v.n for v in existing.values())
    read = collections.defaultdict(list); edits = []; first_edit_i = None
    pre_lines = collections.Counter(); trunc = 0
    for idx, (name, a, r) in enumerate(calls):
        r = r or ""
        if name == "edit_file":
            p = str(a.get("filepath") or a.get("file_path") or a.get("path") or "")
            if "mandatory" in r or "error_type" in r: continue
            if p in existing:
                loc = existing[p].line_of(str(a.get("old_string") or ""))
                edits.append((idx, p, loc, str(a.get("old_string") or ""), str(a.get("new_string") or "")))
                if first_edit_i is None: first_edit_i = idx
            elif first_edit_i is None and p and not p.startswith("/tmp") and not TEST.search(p) and ".git/agent" not in p:
                first_edit_i = idx
            continue
        rs = reads_of(name, a, r) if name == "read_file" else []
        if name == "read_file" and '"is_truncated": true' in r: trunc += 1
        cmd = None
        if name == "run_command": cmd = str(a.get("command", ""))
        elif name == "run_skill_script":
            pa = a.get("positional_args") or []
            cmd = " ".join(map(str, pa)) if isinstance(pa, list) else str(pa)
        if cmd: rs += shell_reads(cmd)
        for p, x, y in rs:
            p = p.lstrip("./")
            if p not in existing: continue
            if x == "name":
                sp = existing[p].by_name(y)
                if not sp: continue
                x, y = sp
            y = y or existing[p].n
            if first_edit_i is None: read[p].append((x, y))
    if first_edit_i is None and not edits: return
    if not edits: return  # edited elsewhere only
    def merged(rngs):
        total = 0; last = 0
        for x, y in sorted(rngs):
            x = max(x, last + 1)
            if y >= x: total += y - x + 1; last = y
        return total
    hit = {}
    located = [e for e in edits if e[2]]
    in_hunk = any(overlap(e[2][0], e[2][1], src[e[1]]) for e in located)
    gold_scopes = set()
    for f, r in src.items():
        if f in existing:
            for x, y in r:
                for ln in (x, y):
                    s = existing[f].scope(ln)
                    gold_scopes.add((f, s[2] if s else "<module>"))
    in_fn = any((e[1], (existing[e[1]].scope(e[2][0]) or (0, 0, "<module>"))[2]) in gold_scopes for e in located)
    read_hunk = all(any(overlap(a, b, [(x, y)], slack=0) for x, y in read.get(f, [])) for f in existing for a, b in src[f])
    read_any_hunk = any(any(overlap(a, b, [(x, y)], slack=0) for x, y in read.get(f, [])) for f in existing for a, b in src[f])
    read_hunk_ctx = any(any(x <= a - 10 and y >= b + 10 for x, y in read.get(f, [])) for f in existing for a, b in src[f])
    frac = sum(merged(read.get(f, [])) for f in existing) / max(1, sum(v.n for v in existing.values()))
    gold_lines = sum(1 for l in t["patch"].splitlines() if l[:1] in "+-" and l[:3] not in ("+++", "---"))
    ed_lines = sum(max(o.count("\n"), n.count("\n")) + 1 for _, _, _, o, n in edits[-3:])
    ROWS.append(dict(iid=iid, group=group, folder=folder, res=bool(res["resolved"]), size=size, n_gold=len(src), n_existing=len(existing), located=len(located), edits=len(edits), in_hunk=in_hunk, in_fn=in_fn, read_hunk=read_hunk, read_any=read_any_hunk, read_ctx=read_hunk_ctx, frac=frac, lines_read=sum(merged(read.get(f, [])) for f in existing), gold_lines=gold_lines, ed_lines=ed_lines, first_line=min((min(a for a, b in r) for r in src.values() if r), default=0), trunc=trunc, all_gold=all(f in {e[1] for e in edits} for f in existing), attempt=res.get("attempt")))
for f in sorted(glob.glob("data/results/*/requests/requests.jsonl")):
    d = f.split("/")[2]; per = glob.glob(f"data/results/{d}/**/gen_per_task.jsonl", recursive=True)
    if not per: continue
    res = {(r["instance_id"], str(r.get("attempt"))): r for r in map(json.loads, open(per[0]))}
    J = collections.defaultdict(list)
    for line in open(f):
        r = json.loads(line)
        if isinstance(r.get("reply"), dict) and r.get("job"): J[r["job"]].append(r)
    for job, reqs in J.items():
        iid, _, att = job.partition("#a"); g = res.get((iid, att))
        if not g or iid not in T or g.get("arm") not in ARMS: continue
        reqs.sort(key=lambda r: r["t"]); R = {}
        for r in reqs:
            for m in r["request"]["messages"]:
                if m.get("role") == "tool" and m.get("tool_call_id") not in R: R[m.get("tool_call_id")] = str(m.get("content"))
        calls = []
        for r in reqs:
            for c in r["reply"]["message"].get("tool_calls") or []:
                try: a = json.loads(c["function"]["arguments"])
                except Exception: a = {}
                calls.append((c["function"]["name"], a if isinstance(a, dict) else {}, R.get(c.get("id"))))
        analyse(iid, ARMS[g["arm"]], g, calls, d)
for td in sorted(glob.glob("data/results/*/results/*/traces")):
    p = td.split("/"); d, arm = p[2], p[4]
    if arm not in ARMS: continue
    res = {r["instance_id"]: r for r in map(json.loads, open(os.path.dirname(td) + "/task_results.jsonl"))}
    for f in glob.glob(td + "/trace_*.json"):
        iid = os.path.basename(f)[6:-5]; g = res.get(iid)
        if not g or iid not in T: continue
        calls = []
        for s in json.load(open(f))["steps"]:
            if s.get("source") != "agent": continue
            ob = (s.get("observation") or {}).get("content")
            for c in s.get("tool_calls") or []: calls.append((c.get("function_name"), c.get("arguments") or {}, str(ob)))
        analyse(iid, ARMS[arm], {"resolved": g["resolved"]}, calls, d)
print("runs that edited a gold file:", len(ROWS), "solved", sum(r["res"] for r in ROWS), "tasks", len({r["iid"] for r in ROWS}), "| edits located in the base file", sum(r["located"] for r in ROWS), "of", sum(r["edits"] for r in ROWS))
def rate(x): return f"{sum(r['res'] for r in x)}/{len(x)}={sum(r['res'] for r in x)/max(1,len(x)):.0%}"
def task_rate(x):
    d = collections.defaultdict(list)
    for r in x: d[r["iid"]].append(r["res"])
    return st.mean(st.mean(v) for v in d.values()) if d else 0
print("\n== A. by size of the (largest) real-fix file, in lines: solve rate once the right file is edited")
B = [(0, 200), (200, 500), (500, 1000), (1000, 2000), (2000, 3000), (3000, 99999)]
for a, b in B:
    x = [r for r in ROWS if a <= r["size"] < b]
    if x: print(f"  {a:5}-{b:5} lines: runs {len(x):4} tasks {len({r['iid'] for r in x}):3} solve {rate(x):>16} | mean per task {task_rate(x):.0%} | one-file tasks only {task_rate([r for r in x if r['n_gold']==1]):.0%} (n tasks {len({r['iid'] for r in x if r['n_gold']==1})}) | small fix <=10 lines {task_rate([r for r in x if r['gold_lines']<=10]):.0%} (n {len({r['iid'] for r in x if r['gold_lines']<=10})}) | bigger {task_rate([r for r in x if r['gold_lines']>10]):.0%} (n {len({r['iid'] for r in x if r['gold_lines']>10})})")
print("\n== B. size of the real fix (lines changed), right file edited")
for a, b in [(0, 5), (5, 10), (10, 20), (20, 40), (40, 100), (100, 9999)]:
    x = [r for r in ROWS if a < r["gold_lines"] <= b]
    if x: print(f"  {a:3}-{b:4}: runs {len(x):4} tasks {len({r['iid'] for r in x}):3} solve {rate(x):>16} | per task {task_rate(x):.0%} | mean file {st.mean(r['size'] for r in x):.0f} lines")
print("\n== C. where the edits landed, right file edited; located edits only")
Y = [r for r in ROWS if r["located"]]
for lab, f in (("touching the real fix's lines", lambda r: r["in_hunk"]), ("not on them, same function", lambda r: r["in_fn"] and not r["in_hunk"]), ("other function in the file", lambda r: not r["in_fn"] and not r["in_hunk"])):
    x = [r for r in Y if f(r)]; print(f"  {lab:32} runs {len(x):4} ({len(x)/len(Y):.0%}) solve {rate(x)}")
print("  ...wrong edits only:", {lab: f"{sum(f(r) for r in Y if not r['res'])/sum(not r['res'] for r in Y):.0%}" for lab, f in (("on the lines", lambda r: r["in_hunk"]), ("same function", lambda r: r["in_fn"] and not r["in_hunk"]), ("elsewhere", lambda r: not r["in_fn"] and not r["in_hunk"]))})
print("  by file size, wrong edits: share on the real lines / same function / elsewhere")
for a, b in B:
    x = [r for r in Y if a <= r["size"] < b and not r["res"]]
    if x: print(f"    {a:5}-{b:5}: {len(x):4} runs: {sum(r['in_hunk'] for r in x)/len(x):.0%} / {sum(r['in_fn'] and not r['in_hunk'] for r in x)/len(x):.0%} / {sum(not r['in_fn'] and not r['in_hunk'] for r in x)/len(x):.0%}")
print("  same task: on the real lines vs not:")
def mh(rows, feat):
    s = collections.defaultdict(lambda: [[0, 0], [0, 0]])
    for r in rows:
        c = s[r["iid"], r["group"]][int(bool(feat(r)))]; c[0] += r["res"]; c[1] += 1
    it = [(k, v) for k, v in s.items() if v[0][1] and v[1][1]]
    def est(z):
        w = sum(v[0][1] * v[1][1] / (v[0][1] + v[1][1]) for _, v in z)
        return sum((v[1][0] / v[1][1] - v[0][0] / v[0][1]) * v[0][1] * v[1][1] / (v[0][1] + v[1][1]) for _, v in z) / w if w else 0
    ts = sorted({k[0] for k, _ in it}); bt = collections.defaultdict(list)
    for k, v in it: bt[k[0]].append((k, v))
    xs = sorted(est([i for t in random.choices(ts, k=len(ts)) for i in bt[t]]) for _ in range(1200)) if ts else [0] * 1200
    return f"{est(it)*100:+.0f} pts ({xs[30]*100:+.0f} to {xs[1170]*100:+.0f}), {sum(v[1][1] for _, v in it)} vs {sum(v[0][1] for _, v in it)} runs, {len(ts)} tasks"
print("    edit on the real lines:", mh(Y, lambda r: r["in_hunk"]))
print("    edit in the same function:", mh(Y, lambda r: r["in_fn"] or r["in_hunk"]))
print("\n== D. what was read before the first edit (line-range reads; right file edited)")
print("  read the real lines:", "solved", f"{sum(r['read_any'] for r in ROWS if r['res'])/sum(r['res'] for r in ROWS):.0%}", "wrong", f"{sum(r['read_any'] for r in ROWS if not r['res'])/sum(not r['res'] for r in ROWS):.0%}")
print("  read ALL real regions:", "solved", f"{sum(r['read_hunk'] for r in ROWS if r['res'])/sum(r['res'] for r in ROWS):.0%}", "wrong", f"{sum(r['read_hunk'] for r in ROWS if not r['res'])/sum(not r['res'] for r in ROWS):.0%}")
print("  read with 10 lines around:", "solved", f"{sum(r['read_ctx'] for r in ROWS if r['res'])/sum(r['res'] for r in ROWS):.0%}", "wrong", f"{sum(r['read_ctx'] for r in ROWS if not r['res'])/sum(not r['res'] for r in ROWS):.0%}")
print("  same task: read all regions", mh(ROWS, lambda r: r["read_hunk"]))
print("  same task: read at least one", mh(ROWS, lambda r: r["read_any"]))
print("  same task: all gold files edited", mh(ROWS, lambda r: r["all_gold"]))
print("  by file size: lines read before first edit (median), share of file, read real lines (wrong | solved), read_file truncated runs")
for a, b in B:
    x = [r for r in ROWS if a <= r["size"] < b]
    if x:
        so = [r for r in x if r["res"]]; wr = [r for r in x if not r["res"]]
        pc = lambda z: f"{sum(r['read_any'] for r in z)/max(1,len(z)):.0%}"
        print(f"    {a:5}-{b:5}: {st.median(r['lines_read'] for r in x):5.0f} lines, {st.median(r['frac'] for r in x):.0%} of file, real lines read {pc(wr)} | {pc(so)}, truncated {sum(r['trunc']>0 for r in x)/len(x):.0%}")
print("\n== E. same task: lines read and edit size")
print("  read 150+ lines of the file", mh(ROWS, lambda r: r["lines_read"] >= 150))
print("  read 400+ lines", mh(ROWS, lambda r: r["lines_read"] >= 400))
print("  more than 3 edits to gold files", mh(ROWS, lambda r: r["edits"] > 3))
print("  fix much smaller than gold: edited lines < half gold", mh(ROWS, lambda r: r["ed_lines"] * 2 < r["gold_lines"]))
print("\n== F. tasks: solve rate once right file edited vs file size")
d = collections.defaultdict(list)
for r in ROWS: d[r["iid"]].append(r)
cor = [(st.mean(x["res"] for x in v), v[0]["size"], v[0]["gold_lines"], v[0]["n_gold"]) for v in d.values() if len(v) >= 5]
import math
def rank(a):
    s = sorted(a); return [(s.index(v) + (len(s) - 1 - s[::-1].index(v))) / 2 for v in a]
def spear(a, b):
    ra, rb = rank(a), rank(b); ma, mb = st.mean(ra), st.mean(rb)
    return sum((x - ma) * (y - mb) for x, y in zip(ra, rb)) / math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
print(f"  tasks with 5+ such runs {len(cor)}: Spearman solve vs file lines {spear([c[0] for c in cor],[c[1] for c in cor]):+.2f}, vs fix lines {spear([c[0] for c in cor],[c[2] for c in cor]):+.2f}, vs fix files {spear([c[0] for c in cor],[c[3] for c in cor]):+.2f}")
