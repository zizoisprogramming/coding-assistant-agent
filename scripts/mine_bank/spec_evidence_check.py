"""Offline check 1 for the expected-result card (user 2026-11-25: 'run the two offline check'): at each task's base commit,
is there evidence in the repo's EXISTING tests of how the functions the real fix changes are expected to behave?
Per task (tasks.jsonl; fastapi / rich / requests / httpx):
  fixed functions = the smallest enclosing def of each real-fix source line (a.py's outline rules, file at base_commit);
  called  = an existing test file IN THE HIDDEN TEST'S DIRECTORIES (at base) mentions the function's name as a word (methods: the method name);
  called_or_class = the same, or the enclosing class name (for private helpers that tests reach through the class);
  test_file_exists = the hidden test patch modifies a test file that already exists at base (vs only new files);
  same_test_fn = the hidden test patch edits inside a test function that already exists (a neighbouring example).
Bar (agreed 2026-11-25): an existing test reaches a fixed function in >= 40% of tasks.
Run: python3 -I scripts/mine_bank/spec_evidence_check.py CLONE_DIR   (blob-less clones owner__repo; checks test trees out
into CLONE_DIR/../wt_spec; writes nothing in the repo)"""
import ast, collections, json, os, re, shutil, subprocess, sys
from pathlib import Path

CLONES = Path(sys.argv[1])
WT = CLONES.parent / "wt_spec"
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)conftest\.py$")
GIT = ["git", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false"]


def git(repo, *args, timeout=300):
    r = subprocess.run(GIT + list(args), cwd=repo, capture_output=True, text=True, timeout=timeout)
    return r.stdout if r.returncode == 0 else None


def changed(patch):
    """{file: set(old lines changed)} and {file: set(new-file lines changed)} for a unified diff."""
    old_l, new_l, f, o, n = collections.defaultdict(set), collections.defaultdict(set), None, 0, 0
    for ln in patch.split("\n"):
        if ln.startswith("--- "):
            continue
        if ln.startswith("+++ "):
            f = ln[6:] if ln.startswith("+++ b/") else None; continue
        m = re.match(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", ln)
        if m:
            o, n = int(m.group(1)), int(m.group(3)); continue
        if f is None:
            continue
        if ln.startswith("-"):
            old_l[f].add(o); o += 1
        elif ln.startswith("+"):
            new_l[f].add(n); old_l[f].update({max(o - 1, 1), o}); n += 1
        elif ln.startswith(" "):
            o += 1; n += 1
    return old_l, new_l


def outline(src):
    items = []
    try:
        tree = ast.parse(src)
    except (SyntaxError, ValueError):
        return items
    def walk(node, cls):
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                start = min([d.lineno for d in ch.decorator_list] + [ch.lineno])
                items.append((ch.name, start, ch.end_lineno, cls, isinstance(ch, ast.ClassDef)))
                walk(ch, ch.name if isinstance(ch, ast.ClassDef) else cls)
    walk(tree, None)
    return items


rows = []
tasks = [json.loads(l) for l in open("data/tasks.jsonl")]
for t in tasks:
    repo = CLONES / t["repo"].replace("/", "__")
    if not repo.exists():
        continue
    old_l, _ = changed(t["patch"])
    funcs = set()
    for f, lines in old_l.items():
        if TEST.search(f) or not f.endswith(".py"):
            continue
        src = git(repo, "show", f"{t['base_commit']}:{f}")
        if src is None:
            continue
        items = outline(src)
        for x in lines:
            best = None
            for name, s, e, cls, is_cls in items:
                if not is_cls and s <= x <= e and (best is None or e - s < best[2] - best[1]):
                    best = (name, s, e, cls)
            if best:
                funcs.add((f, best[0], best[3]))
    # existing test files at base, checked out once per task (batch blob fetch)
    if WT.exists():
        shutil.rmtree(WT)
    WT.mkdir(parents=True)
    tree = git(repo, "ls-tree", "-r", "--name-only", t["base_commit"]) or ""
    t_old0, t_new0 = changed(t["test_patch"])
    tdirs = {os.path.dirname(p) for p in set(t_old0) | set(t_new0)}  # 2026-11-25: only the hidden test's directories (a full
    # fastapi test tree is fetched blob by blob: ~4 min per task)
    tfiles = [p for p in tree.split("\n") if p.endswith(".py") and TEST.search(p) and os.path.dirname(p) in tdirs]
    texts = {}
    if tfiles:
        subprocess.run(GIT + ["--work-tree", str(WT), "checkout", t["base_commit"], "--"] + tfiles[:4000], cwd=repo,
                       capture_output=True, text=True, timeout=900)
        for p in tfiles:
            try:
                texts[p] = (WT / p).read_text(errors="replace")
            except OSError:
                pass
        subprocess.run(GIT + ["reset", "-q"], cwd=repo, capture_output=True, timeout=120)  # the index only; the clone has no work tree
    def mentioned(word):
        rx = re.compile(r"\b" + re.escape(word) + r"\b")
        return [p for p, s in texts.items() if rx.search(s)]
    called = [fn for fn in funcs if mentioned(fn[1])]
    called_cls = [fn for fn in funcs if mentioned(fn[1]) or (fn[2] and mentioned(fn[2]))]
    t_old, t_new = changed(t["test_patch"])
    t_files = set(t_old) | set(t_new)
    exists = [p for p in t_files if p in texts]
    same_fn = False
    for p in exists:
        items = outline(texts[p])
        if any(s <= x <= e for x in t_old.get(p, ()) for name, s, e, cls, is_cls in items if not is_cls and name.startswith("test")):
            same_fn = True
    rows.append(dict(task=t["instance_id"], repo=t["repo"], funcs=len(funcs), called=bool(called), called_cls=bool(called_cls),
                     test_file_exists=bool(exists), same_test_fn=same_fn, fns=sorted(f"{fn[1]}" for fn in funcs)[:4]))
    print(f"{t['instance_id']:28} fixed fns {len(funcs)} {','.join(rows[-1]['fns'])[:60]:60} called {rows[-1]['called']!s:5} "
          f"or-class {rows[-1]['called_cls']!s:5} test-file-exists {rows[-1]['test_file_exists']!s:5} in-existing-test-fn {same_fn}",
          flush=True)
if WT.exists():
    shutil.rmtree(WT)
n = len(rows)
print(f"\n{n} tasks | fixed function found {sum(r['funcs'] > 0 for r in rows)} | an existing test names a fixed function "
      f"{sum(r['called'] for r in rows)} ({sum(r['called'] for r in rows) / n:.0%}) | or its class "
      f"{sum(r['called_cls'] for r in rows)} ({sum(r['called_cls'] for r in rows) / n:.0%}) | hidden test goes into an existing "
      f"test file {sum(r['test_file_exists'] for r in rows)} ({sum(r['test_file_exists'] for r in rows) / n:.0%}) | edits an "
      f"existing test function {sum(r['same_test_fn'] for r in rows)}")
for repo in sorted({r["repo"] for r in rows}):
    rr = [r for r in rows if r["repo"] == repo]
    print(f"  {repo:18} {len(rr):3} tasks | called {sum(r['called'] for r in rr) / len(rr):4.0%} | or-class "
          f"{sum(r['called_cls'] for r in rr) / len(rr):4.0%} | existing test file {sum(r['test_file_exists'] for r in rr) / len(rr):4.0%}")
