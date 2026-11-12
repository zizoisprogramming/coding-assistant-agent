"""Would a file map put the real fix's function in front of the agent? (2026-11-12, offline check 1 before any arm.)
Run: python3 -I scripts/mine_bank/file_map_offline.py SNAPSHOT_DIR [SNAPSHOT_DIR ...]

Per public task whose base is found in a local snapshot (fix_line_age.find_base):
  names      = the names the real evidence stage chose (bank logs) or, if none, code-like names from the issue that the
               repository's source actually contains (URL parts dropped), at most 4;
  files      = non-test, non-docs Python files that define or use those names, ranked by name hits (top 3);
  map        = per file, its functions / classes (python ast) with line ranges; 'marked' = the innermost ones whose body
               holds a name (word match), ranked by hits;
  real fn    = the innermost def / class around the lines the real fix changes (module-level changes: none).
Reports: real-fix file among the top-3 files; real fn marked, its rank among marked, how many are marked vs how many
functions the file has; whether evidefs's evidence output already points at a line inside the real fn (file:line
references from submissions/evidefs/skills/evidence/scripts/evidence.py run on the same base); split by depth (real-fix
lines past line 150)."""
import collections, importlib.util, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def mod(name, file):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, file))
    m = importlib.util.module_from_spec(spec)
    old = sys.argv
    sys.argv = [old[0], "/dev/null"]
    try:
        spec.loader.exec_module(m)
    finally:
        sys.argv = old
    return m


fla = mod("fla", "fix_line_age.py")
ep = mod("ep", "edit_place.py")
eo = mod("eo", "evidence_offline.py")
T = {json.loads(l)["instance_id"]: json.loads(l) for l in open("data/tasks.jsonl")}
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)conftest\.py$")
SKIP = re.compile(r"^(docs|docs_src|examples|scripts|tools|benchmarks)/")
EVID = os.path.abspath("submissions/evidefs/skills/evidence/scripts/evidence.py")
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")


def spans(text):
    """[(first, last, name)] of every def / class, innermost resolved by the caller."""
    import ast
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    return [(n.lineno, getattr(n, "end_lineno", n.lineno), n.name) for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]


def innermost(sp, line):
    c = [s for s in sp if s[0] <= line <= s[1]]
    return min(c, key=lambda s: s[1] - s[0]) if c else None


def repo_names(top, base, task):
    t = re.sub(r"https?://\S+", " ", task["problem_statement"])
    cand = []
    for m in re.findall(r"`([^`\n]{2,80})`", t):
        cand += IDENT.findall(m)
    cand += [m for m in IDENT.findall(t) if "_" in m.strip("_") or re.search(r"[a-z][A-Z]", m)]
    cand += re.findall(r"([A-Za-z_][A-Za-z0-9_]{2,})\(", t)
    out = []
    for n in cand:
        if n in out:
            continue
        hit = fla.git(top, "grep", "-l", "-w", "-F", "-e", n, base, "--", "*.py")
        if any(not TEST.search(h.split(":", 1)[-1]) for h in hit.splitlines()):
            out.append(n)
        if len(out) == 4:
            break
    return out


def main(dirs):
    snap = fla.snapshots(dirs)
    real = eo.stage_names()
    rows = []
    for iid, t in sorted(T.items()):
        repo = iid.split("_")[0]
        if repo not in snap:
            continue
        top, _, tip = snap[repo]
        base = fla.find_base(top, t, tip)
        if not base:
            continue
        ch = {f: v for f, v in ep.changed_lines(t).items() if f.endswith(".py")}
        if not ch:
            continue
        gold_fns = {}
        for f, lines in ch.items():
            sp = spans(fla.git(top, "show", f"{base}:{f}"))
            fns = {innermost(sp, x) for x in lines} - {None}
            gold_fns[f] = fns
        names = [n.rsplit(".", 1)[-1] for n in (real.get(iid) or repo_names(top, base, t)) if re.fullmatch(r"[A-Za-z_][\w.]*", n)]
        if not names:
            rows.append(dict(iid=iid, names=[], file3=False, fn_marked=False, rank=None, marked=0, nfun=0, evid_fn=False,
                             deep=min(min(v) for v in ch.values()) > 150, has_fn=any(gold_fns.values())))
            continue
        hits = collections.Counter()
        for n in names:
            for ln in fla.git(top, "grep", "-n", "-w", "-F", "-e", n, base, "--", "*.py").splitlines():
                parts = ln.split(":", 3)
                if len(parts) >= 3 and not TEST.search(parts[1]) and not SKIP.search(parts[1]):
                    hits[parts[1]] += 1
        files = [f for f, _ in hits.most_common(3)]
        gf = next((f for f in ch if f in files), None)
        fn_marked, rank, nmarked, nfun = False, None, 0, 0
        if gf:
            text = fla.git(top, "show", f"{base}:{gf}")
            sp = spans(text); nfun = len(sp)
            lines = text.splitlines()
            score = collections.Counter()
            for i, l in enumerate(lines, 1):
                if any(re.search(rf"\b{re.escape(n)}\b", l) for n in names):
                    s = innermost(sp, i)
                    if s:
                        score[s] += 1
            ranked = [s for s, _ in score.most_common()]
            nmarked = len(ranked)
            for g in gold_fns.get(gf, ()):
                if g in ranked:
                    fn_marked = True
                    r = ranked.index(g) + 1
                    rank = r if rank is None else min(rank, r)
        # does evidefs's evidence already point inside the real fn?
        subprocess.run(["git", "-C", top, "checkout", "-q", "-f", base], capture_output=True)
        subprocess.run(["rm", "-rf", os.path.join(top, ".git", "agent")], capture_output=True)
        out = subprocess.run([sys.executable, "-I", EVID, *names], cwd=top, capture_output=True, text=True, errors="replace", timeout=60).stdout
        evid_fn = False
        for f, fns in gold_fns.items():
            for m in re.finditer(rf"{re.escape(f)}:(\d+)", out):
                if any(a <= int(m.group(1)) <= b for a, b, _ in fns):
                    evid_fn = True
        rows.append(dict(iid=iid, names=names, file3=gf is not None, fn_marked=fn_marked, rank=rank, marked=nmarked, nfun=nfun,
                         evid_fn=evid_fn, deep=min(min(v) for v in ch.values()) > 150, has_fn=any(gold_fns.values())))
        r = rows[-1]
        print(f"{iid:15s} names {names} | real file in top 3 {'Y' if r['file3'] else '-'} | real fn marked {'Y' if r['fn_marked'] else '-'} rank {r['rank']} "
              f"of {r['marked']} marked / {r['nfun']} defs | evidence already inside real fn {'Y' if r['evid_fn'] else '-'} | {'deep' if r['deep'] else 'top'}", flush=True)
    for top, _, tip in snap.values():
        subprocess.run(["git", "-C", top, "checkout", "-q", "-f", tip], capture_output=True)
    g = [r for r in rows if r["has_fn"]]
    print(f"\ntasks {len(rows)} (real fix inside a def / class: {len(g)})")
    for lab, s in (("all", g), ("real-fix lines past line 150", [r for r in g if r["deep"]]), ("within the first 150 lines", [r for r in g if not r["deep"]])):
        if not s:
            continue
        n = len(s)
        m = [r for r in s if r["fn_marked"]]
        print(f"  {lab:30s} tasks {n:3d} | real file in top 3: {100 * sum(r['file3'] for r in s) / n:3.0f}% | real fn marked: {100 * len(m) / n:3.0f}% "
              f"(rank 1: {sum(r['rank'] == 1 for r in m)}, top 3: {sum((r['rank'] or 99) <= 3 for r in m)}) | evidence already inside real fn: "
              f"{100 * sum(r['evid_fn'] for r in s) / n:3.0f}% | map adds the real fn where evidence did not: {sum(r['fn_marked'] and not r['evid_fn'] for r in s)} "
              f"| median marked {sorted(r['marked'] for r in s)[n // 2]} of {sorted(r['nfun'] for r in s)[n // 2]} defs")


if __name__ == "__main__":
    main(sys.argv[1:])
