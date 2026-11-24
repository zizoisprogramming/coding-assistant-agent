"""Option 2 data check (user 2026-11-25: 'do the option 2 data check first'): when the EDIT CANDIDATES (3 most-read spots at
STOP READING) miss the real fix, would the NEXT / PREVIOUS function in the same file have held it?
r161: g3's frozen candidates held the real-fix lines in 6/10 closed runs (g2 13/16); both shell-escape runs were misses
(fastapi_11194 s1: fix in _extract_form_body 872+, the model had read the function just before it, 846-867).

For every sk_a2-family run (arm starts with sk_a2) on a tasks.jsonl task that reached STOP READING before any edit:
reads = (file, first, last numbered line) of every a.py show output up to and including the STOP output (gate answers
with candidate code are not reads, as in a.py); spots = smallest enclosing function of each read (a.py's spot_of, with
a.py's outline_items on the file at base_commit); gold = old-file lines the real patch removes or inserts at (non-test).
Variants (hit = a gold line inside a candidate's range):
  top3     the 3 most-read spots (g3)                    +next    top3 + the next function after each
  +prevnext  top3 + previous and next function            allread  every read spot
  allread+next  every read spot + next function           file     every function in every read file (upper bound)
Also: the gold file read at all; mean candidate count / lines per variant.
Run: python3 -I scripts/mine_bank/cand_neighbor_check.py CLONE_DIR   (blob-less clones named owner__repo; writes nothing)"""
import ast, collections, glob, json, re, subprocess, sys
from pathlib import Path

CLONES = Path(sys.argv[1])
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)conftest\.py$")
T = {}
for l in open("data/tasks.jsonl"):
    t = json.loads(l); T[t["instance_id"]] = t


def gold_lines(patch):
    out, f, old = collections.defaultdict(set), None, 0
    for ln in patch.split("\n"):
        if ln.startswith("--- "):
            continue
        if ln.startswith("+++ b/"):
            f = ln[6:]; continue
        m = re.match(r"^@@ -(\d+)(?:,(\d+))? ", ln)
        if m:
            old = int(m.group(1)); continue
        if f is None or TEST.search(f) or not f.endswith(".py"):
            continue
        if ln.startswith("-"):
            out[f].add(old); old += 1
        elif ln.startswith("+"):
            out[f].update({max(old - 1, 1), old})
        elif ln.startswith(" "):
            old += 1
    return out


SRC = {}


def source(task, path):
    k = (task, path)
    if k not in SRC:
        t = T[task]
        r = subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false", "show", f"{t['base_commit']}:{path}"],
                           cwd=CLONES / t["repo"].replace("/", "__"), capture_output=True, text=True, timeout=120)
        SRC[k] = r.stdout if r.returncode == 0 else None
    return SRC[k]


OUT = {}


def outline(task, path):
    k = (task, path)
    if k not in OUT:
        s = source(task, path); items = []
        try:
            tree = ast.parse(s) if s else None
        except SyntaxError:
            tree = None
        def walk(node, prefix):
            for ch in ast.iter_child_nodes(node):
                if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    start = min([d.lineno for d in ch.decorator_list] + [ch.lineno])
                    items.append((prefix + ch.name, start, ch.end_lineno, prefix))
                    walk(ch, prefix + ch.name + ".")
        if tree:
            walk(tree, "")
        OUT[k] = items
    return OUT[k]


def spot_of(task, path, a, b):
    mid, best = (a + b) // 2, None
    for name, s, e, pre in outline(task, path):
        if s <= mid <= e and (best is None or e - s < best[2] - best[1]):
            best = (name, s, e, pre)
    return (path,) + (best or ("module level", a, b, None))


def neighbours(task, spot, prev=False):
    path, name, a, b, pre = spot
    if pre is None:
        return []
    items = [it for it in outline(task, path) if it[3] == pre]
    nxt = [it for it in items if it[1] > b]
    out = [(path,) + min(nxt, key=lambda it: it[1])] if nxt else []
    if prev:
        prv = [it for it in items if it[2] < a]
        out += [(path,) + max(prv, key=lambda it: it[2])] if prv else []
    return out


def dec(x):
    try:
        return str(json.loads(x).get("stdout", x))
    except Exception:
        return str(x)


SHOW = re.compile(r"a\.py\s+show\s+(\S+)")
NUM = re.compile(r"^\s*(\d+)\| ", re.M)
VARS = ["top3", "+next", "+prevnext", "allread", "allread+next", "file"]
agg = {k: collections.Counter() for k in ("all", "solved", "failed")}
size = {v: [] for v in VARS}
misses = []
for d in sorted(glob.glob("data/results/*")):
    try:
        G = {}
        for l in open(f"{d}/results/gen_per_task.jsonl"):
            g = json.loads(l); G[g["instance_id"] + "#a" + str(g["attempt"])] = g
    except (OSError, ValueError, KeyError):
        continue
    by = collections.defaultdict(list)
    try:
        for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
            try:
                r = json.loads(l)
            except ValueError:
                continue
            by[r.get("job")].append(r)
    except OSError:
        continue
    for job, rs in by.items():
        g = G.get(job)
        if not g or not str(g.get("arm", "")).startswith("sk_a2") or g["instance_id"] not in T:
            continue
        task = g["instance_id"]; gold = gold_lines(T[task]["patch"])
        if not gold:
            continue
        rs = sorted(rs, key=lambda r: float(r["t"]))
        res, calls = {}, []
        for r in rs:
            for m in r["request"]["messages"]:
                if m.get("role") == "tool":
                    res.setdefault(m.get("tool_call_id"), dec(m.get("content")))
            rep = r.get("reply") or {}
            if isinstance(rep, str):
                try:
                    rep = json.loads(rep)
                except ValueError:
                    rep = {}
            calls += ((rep.get("message") or {}).get("tool_calls") or [])
        reads, stop = [], False
        for c in calls:
            fn = c.get("function") or {}; out = res.get(c.get("id"), "")
            try:
                ad = json.loads(fn.get("arguments") or "{}")
            except ValueError:
                ad = {}
            ad = ad if isinstance(ad, dict) else {}
            if fn.get("name") == "edit_file" and not TEST.search(str(ad.get("filepath", ""))) and '"status": "error"' not in out:
                break  # an edit before STOP: the gate never closes
            m = SHOW.search(str(ad.get("command", "")))
            if m and "Instead, here is" not in out:
                nums = [int(x) for x in NUM.findall(out)]
                path = re.sub(r"^(\./|/workspace/)", "", m.group(1).split(":")[0])
                if nums and not TEST.search(path):
                    reads.append((path, min(nums), max(nums)))
            if ">>> STOP READING" in out:
                stop = True
                break
        if not stop or not reads:
            continue
        cnt, order = collections.Counter(), []
        for p, a, b in reads:
            k = spot_of(task, p, a, b); cnt[k] += 1
            if k in order:
                order.remove(k)
            order.append(k)
        top3 = sorted(cnt, key=lambda s: (-cnt[s], -order.index(s)))[:3]
        allr = list(cnt)
        V = {"top3": top3,
             "+next": top3 + [n for s in top3 for n in neighbours(task, s)],
             "+prevnext": top3 + [n for s in top3 for n in neighbours(task, s, prev=True)],
             "allread": allr,
             "allread+next": allr + [n for s in allr for n in neighbours(task, s)],
             "file": [(p,) + it for p in {s[0] for s in allr} for it in outline(task, p) if it[3] == ""]}
        ok = g.get("resolved") in (True, "True")
        for v, cands in V.items():
            cands = list(dict.fromkeys(cands))
            hit = any(a <= x <= b for p, _, a, b, _ in cands for x in gold.get(p, ()))
            for k in ("all", "solved" if ok else "failed"):
                agg[k][v] += hit
            size[v].append((len(cands), sum(b - a + 1 for _, _, a, b, _ in cands)))
        for k in ("all", "solved" if ok else "failed"):
            agg[k]["runs"] += 1
            agg[k]["gold file read"] += any(p in gold for p, _, _ in reads)
        top_hit = any(a <= x <= b for p, _, a, b, _ in top3 for x in gold.get(p, ()))
        if not top_hit:
            nh = any(a <= x <= b for p, _, a, b, _ in V["+next"] for x in gold.get(p, ()))
            misses.append((Path(d).name, task, g["arm"], "SOLVED" if ok else "failed", "next-hit" if nh else "-",
                           "gold file read" if any(p in gold for p, _, _ in reads) else "gold file NOT read"))
for k, c in agg.items():
    n = c["runs"] or 1
    print(f"{k:7} runs {c['runs']:4} | gold file read {c['gold file read'] / n:4.0%} | " +
          " | ".join(f"{v} {c[v] / n:4.0%}" for v in VARS))
print("mean candidates / lines: " + " | ".join(f"{v} {sum(x for x, _ in size[v]) / max(len(size[v]), 1):.1f} / "
                                              f"{sum(y for _, y in size[v]) / max(len(size[v]), 1):.0f}" for v in VARS))
print(f"\ntop3 misses: {len(misses)}; rescued by +next: {sum(m[4] == 'next-hit' for m in misses)}; gold file never read: "
      f"{sum(m[5] == 'gold file NOT read' for m in misses)}")
by_task = collections.Counter((m[1], m[4], m[5]) for m in misses)
for (t, nh, gf), n in sorted(by_task.items()):
    print(f"  {t:16} {nh:9} {gf:20} x{n}")
