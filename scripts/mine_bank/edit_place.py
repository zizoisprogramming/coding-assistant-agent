"""Right file, but the right PLACE in it? (2026-11-12, user: "it gets the file then the problem is where").
Run: python3 -I scripts/mine_bank/edit_place.py SNAPSHOT_DIR [SNAPSHOT_DIR ...] [--only=FOLDER_SUBSTR]   (extracted data/snapshots/*.tgz;
--only limits to results folders whose name contains the substring and adds a per-arm line)

For every logged 31B run with a patch (solved or failed) on a task whose base is found in a local snapshot
(fix_line_age.find_base), each edit_file call on a real-fix file is placed in the file as it was at the base (its
old_string located in the base text; edits whose old_string is not in the base text, e.g. edits of earlier edits, are
placed by their first line if it is unique, else skipped). Compared with the lines the real fix changes:
  on the lines   = the edit's lines overlap a changed line (or the insertion point) of the real fix,
  near           = within 15 lines,
  same function  = inside the same innermost def / class as some real-fix change (python ast on the base file),
  elsewhere      = same file, another function, more than 15 lines away.
Per run the best (closest) edit counts. Pooled and within the same task (solved vs failed), plus the read side:
whether the run had READ the real-fix lines (read_file / sed -n / cat ranges) before its first edit in that file, and
whether off-target failed runs ever read them; split by whether the real-fix lines sit past line 150 (beyond one read)."""
import ast, collections, glob, importlib.util, json, math, os, re, statistics as st, sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("fla", os.path.join(HERE, "fix_line_age.py"))
fla = importlib.util.module_from_spec(spec); spec.loader.exec_module(fla)
T = {json.loads(l)["instance_id"]: json.loads(l) for l in open("data/tasks.jsonl")}
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)conftest\.py$")
NEAR = 15


def norm(p):
    p = str(p or "").strip()
    return p[len("/workspace/"):] if p.startswith("/workspace/") else p[2:] if p.startswith("./") else p


def changed_lines(task):
    """file -> set of base line numbers the real fix removes, or the line before an insertion."""
    out = collections.defaultdict(set)
    for f, start, old, removed in fla.hunks(task["patch"]):
        if TEST.search(f):
            continue
        if removed:
            out[f].update(removed)
        else:  # pure insertion: the hunk's context lines around it
            out[f].update(range(start, start + max(1, len(old))))
    return out


def func_map(text):
    """line -> innermost def / class name (None at module level)."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return {}
    spans = []
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            spans.append((n.lineno, getattr(n, "end_lineno", n.lineno), n.name))
    m = {}
    for a, b, name in sorted(spans, key=lambda s: s[1] - s[0], reverse=True):  # wider first, inner overwrite
        for i in range(a, b + 1):
            m[i] = name
    return m


def locate(text_lines, old):
    """(first, last) base line numbers of OLD in the base file, or None."""
    ol = [l for l in old.splitlines()]
    while ol and not ol[0].strip():
        ol.pop(0)
    while ol and not ol[-1].strip():
        ol.pop()
    if not ol:
        return None
    n = len(ol)
    hits = [i for i in range(len(text_lines) - n + 1) if [x.rstrip() for x in text_lines[i:i + n]] == [x.rstrip() for x in ol]]
    if len(hits) == 1:
        return hits[0] + 1, hits[0] + n
    first = [i for i, x in enumerate(text_lines) if x.strip() == ol[0].strip()] if ol[0].strip() else []
    if len(first) == 1:
        return first[0] + 1, first[0] + n
    return None


def read_ranges(name, args):
    """(path, first, last) a read covers, when it names one; read_file with offsets or sed -n a,bp / cat."""
    if name == "read_file":
        p = norm(args.get("filepath") or args.get("file_path") or args.get("path"))
        a = int(args.get("start_line") or args.get("offset") or 1) if str(args.get("start_line") or args.get("offset") or "1").isdigit() else 1
        b = int(args.get("end_line") or 0) if str(args.get("end_line") or "").isdigit() else a + 149
        return [(p, a, b or a + 149)]
    cmd = str(args.get("command") or "")
    out = [(norm(m.group(3)), int(m.group(1)), int(m.group(2))) for m in re.finditer(r"sed -n ['\"]?(\d+),(\d+)p['\"]?\s+(\S+)", cmd)]
    out += [(norm(m.group(1)), 1, 10 ** 6) for m in re.finditer(r"\bcat\s+(\S+\.py)\b", cmd)]
    return out


ONLY_DIRS = [a[7:] for a in sys.argv[1:] if a.startswith("--only=")]


def main(dirs):
    dirs = [d for d in dirs if not d.startswith("--")]
    snap = fla.snapshots(dirs)
    base_of, text_of, fmap_of = {}, {}, {}
    rows = []
    for f in sorted(glob.glob("data/results/*/requests/requests.jsonl")):
        d = f.split("/")[2]
        if "e4b" in d or "12b" in d or (ONLY_DIRS and not any(o in d for o in ONLY_DIRS)):
            continue
        per = glob.glob(f"data/results/{d}/**/gen_per_task.jsonl", recursive=True)
        if not per:
            continue
        res = {(r["instance_id"], str(r.get("attempt"))): r for r in map(json.loads, open(per[0]))}
        J = collections.defaultdict(list)
        for line in open(f, errors="replace"):
            try:
                r = json.loads(line)
            except Exception:
                continue
            if isinstance(r.get("reply"), dict) and r.get("job"):
                J[r["job"]].append(r)
        for job, reqs in J.items():
            iid, _, att = job.partition("#a")
            g = res.get((iid, att))
            if g is None or iid not in T or not g.get("patch_chars") or "e4b" in str(g.get("arm")) or "12b" in str(g.get("arm")):
                continue
            repo = iid.split("_")[0]
            if repo not in snap:
                continue
            if iid not in base_of:
                top, _, tip = snap[repo]
                base_of[iid] = (top, fla.find_base(top, T[iid], tip))
            top, base = base_of[iid]
            if not base:
                continue
            ch = changed_lines(T[iid])
            for gf in ch:
                if (iid, gf) not in text_of:
                    text_of[(iid, gf)] = fla.git(top, "show", f"{base}:{gf}").splitlines()
                    fmap_of[(iid, gf)] = func_map("\n".join(text_of[(iid, gf)]))
            reqs.sort(key=lambda r: r["t"])
            best, read_before, first_edit_seen, read_ever = None, False, False, False
            for r in reqs:
                for c in (r["reply"]["message"].get("tool_calls") or []):
                    fn = c.get("function") or {}
                    a = fn.get("arguments") or {}
                    if isinstance(a, str):
                        try:
                            a = json.loads(a)
                        except Exception:
                            a = {}
                    if not isinstance(a, dict):
                        continue
                    name = fn.get("name")
                    if name == "edit_file":
                        p = norm(a.get("filepath") or a.get("file_path") or a.get("path"))
                        if p not in ch:
                            continue
                        loc = locate(text_of[(iid, p)], str(a.get("old_string") or ""))
                        if not loc:
                            continue
                        first_edit_seen = True
                        lines = set(range(loc[0], loc[1] + 1))
                        gl = ch[p]
                        dist = 0 if lines & gl else min(abs(x - y) for x in lines for y in gl)
                        fm = fmap_of[(iid, p)]
                        same_fn = bool({fm.get(x) for x in lines} & {fm.get(y) for y in gl} - {None})
                        cls = "on the lines" if dist == 0 else "near (<= 15 lines)" if dist <= NEAR else "same function, farther" if same_fn else "elsewhere in the file"
                        rank = ["on the lines", "near (<= 15 lines)", "same function, farther", "elsewhere in the file"].index(cls)
                        if best is None or rank < best[0]:
                            best = (rank, cls, dist)
                    else:
                        for p, ra, rb in read_ranges(name, a):
                            if p in ch and any(ra <= y <= rb for y in ch[p]):
                                read_ever = True
                                if not first_edit_seen:
                                    read_before = True
            if best:
                gpos = min(min(v) for v in ch.values())
                flen = max(len(text_of[(iid, gf)]) for gf in ch)
                rows.append(dict(iid=iid, arm=str(g.get("arm")), y=bool(g.get("resolved")), cls=best[1], dist=best[2], read=read_before, read_ever=read_ever,
                                 deep=gpos > 150, flen=flen))
    print(f"runs with a placed edit in a real-fix file: {len(rows)} (solved {sum(r['y'] for r in rows)}, failed {sum(not r['y'] for r in rows)}) on {len({r['iid'] for r in rows})} tasks")
    order = ["on the lines", "near (<= 15 lines)", "same function, farther", "elsewhere in the file"]
    for lab, g in (("solved", [r for r in rows if r["y"]]), ("failed", [r for r in rows if not r["y"]])):
        c = collections.Counter(r["cls"] for r in g)
        print(f"  {lab:7s} closest edit: " + " | ".join(f"{k} {100 * c[k] / len(g):.0f}%" for k in order) + f" | read the real-fix lines before editing {100 * sum(r['read'] for r in g) / len(g):.0f}%")
    off = [r for r in rows if not r["y"] and r["cls"] in order[2:]]
    if off:
        print(f"  failed runs whose closest edit is not on / near the real-fix lines: {len(off)}; read those lines at some point {100 * sum(r['read_ever'] for r in off) / len(off):.0f}%, "
              f"never {100 * sum(not r['read_ever'] for r in off) / len(off):.0f}%")
    for lab, g in (("real-fix lines past line 150 of the file", [r for r in rows if r["deep"]]), ("within the first 150 lines", [r for r in rows if not r["deep"]])):
        if g:
            f = [r for r in g if not r["y"]]
            print(f"  {lab:42s} runs {len(g):4d}, solved {100 * sum(r['y'] for r in g) / len(g):3.0f}% | failed runs off the lines {100 * sum(r['cls'] in order[2:] for r in f) / max(1, len(f)):3.0f}%, "
                  f"failed runs that never read them before editing {100 * sum(not r['read'] for r in f) / max(1, len(f)):3.0f}%")
    if ONLY_DIRS:
        for arm in sorted({r["arm"] for r in rows}):
            g = [r for r in rows if r["arm"] == arm]
            c = collections.Counter(r["cls"] for r in g)
            print(f"  {arm:8s} runs with a placed edit {len(g)}: " + ", ".join(f"{k} {c[k]}" for k in order if c[k]) + f" | read the real-fix lines before editing {sum(r['read'] for r in g)}")
    by = collections.defaultdict(lambda: ([], []))
    for r in rows:
        by[r["iid"]][r["y"]].append(r)
    for name, f in (("closest edit on the real-fix lines", lambda r: r["cls"] == "on the lines"),
                    ("closest edit on or near (<= 15 lines)", lambda r: r["cls"] in order[:2]),
                    ("edit elsewhere in the file only", lambda r: r["cls"] == order[3]),
                    ("read the real-fix lines before editing", lambda r: r["read"])):
        hi = lo = 0; sa = fa = 0.0; n = 0
        for iid, (fail, sol) in by.items():
            if len(sol) >= 3 and len(fail) >= 3:
                a = sum(map(f, sol)) / len(sol); b = sum(map(f, fail)) / len(fail)
                sa += a; fa += b; n += 1; hi += a > b; lo += a < b
        if n:
            k = min(hi, lo); tot = hi + lo
            p = min(1.0, 2 * sum(math.comb(tot, j) for j in range(k + 1)) / 2 ** tot) if tot else 1.0
            print(f"  same task ({n} tasks), {name:40s} solved {100 * sa / n:4.0f}% vs failed {100 * fa / n:4.0f}% | tasks {hi} vs {lo}, sign p {p:.3f}")


if __name__ == "__main__":
    main(sys.argv[1:])
