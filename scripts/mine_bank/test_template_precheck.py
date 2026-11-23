"""Step 0c (user 2026-11-23: 'run 0c'): is the hidden test shaped like a test that already exists, and does it check variants beyond the
issue's one example? Run: python3 -I scripts/mine_bank/test_template_precheck.py SNAPSHOT_DIR [...]   (read only via git show, hooks and
fsmonitor off; the base is found as in docs_precheck.py).
Per task: the hidden test's NEW test functions (added 'def test_*' in test_patch) vs the existing test functions in the same file at base:
  called names = names called in the function body (foo(...), obj.meth(...) -> meth), minus generic ones (assert helpers, client verbs, builtins)
  DIRECT template: an existing test in that file calls a name the real fix defines / changes (its def / class lines, hunk headers)
  SHAPE template: an existing test whose called-name set overlaps the new test's by Jaccard >= 0.5
  VARIANTS: >= 2 new test functions, or parametrize in the added lines, or >= 2 asserting calls of the target with different arguments.
Writes data/analysis/test_template_precheck.jsonl."""
import ast, collections, glob, json, re, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/mine_bank"))
from docs_precheck import git, hunks, find_base  # noqa: E402  (safe git: hooks + fsmonitor off)
GENERIC = {"get", "post", "put", "delete", "patch", "json", "raises", "TestClient", "len", "str", "int", "list", "dict", "set", "print", "isinstance",
           "assert_called_once", "warns", "mark", "parametrize", "fixture", "Console", "StringIO", "export_text", "getvalue", "items", "keys", "values",
           "append", "join", "split", "strip", "format", "dumps", "loads", "type", "repr", "range", "open", "read", "write", "sorted", "tuple", "bool",
           "snapshot", "dirty_equals", "IsDict", "IsOneOf", "include_router", "FastAPI", "APIRouter", "Depends", "BaseModel", "Field"}


def called(node):
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            nm = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else None
            if nm and nm not in GENERIC and not nm.startswith("assert"): out.add(nm)
    return out


def test_funcs(src):
    try: tree = ast.parse(src)
    except SyntaxError: return {}
    return {n.name: n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test")}


def fix_names(task):
    t = set()
    for f, s, o, head in hunks(task["patch"]):
        if "test" in f: continue
        for m in re.finditer(r"(?:def|class)\s+(\w+)", head + "\n" + "\n".join(o)): t.add(m.group(1))
    for l in task["patch"].split("\n"):
        m = re.match(r"\+\s*(?:async\s+)?(?:def|class)\s+(\w+)", l)
        if m: t.add(m.group(1))
    return t


def main(dirs):
    snaps = {re.sub(r"_\d+$", "", Path(d).name): git(d, "rev-parse", "--show-toplevel").strip() for d in dirs}
    rate = collections.defaultdict(lambda: [0, 0])
    for f in glob.glob(str(ROOT / "data/results/*/results/gen_per_task.jsonl")):
        for l in open(f, errors="replace"):
            try: g = json.loads(l)
            except Exception: continue
            rate[g["instance_id"]][0] += g.get("resolved") in (True, "True"); rate[g["instance_id"]][1] += 1
    rows = []
    for l in open(ROOT / "data/tasks.jsonl"):
        t = json.loads(l); repo = t["instance_id"].split("_")[0]
        if repo not in snaps: continue
        top = snaps[repo]; base = find_base(top, t)
        if not base: continue
        fixn = fix_names(t)
        tfiles = [f for f in re.findall(r"^\+\+\+ b/(\S+\.py)", t["test_patch"], re.M) if "conftest" not in f]
        added = "\n".join(x[1:] for x in t["test_patch"].split("\n") if x.startswith("+") and not x.startswith("+++"))
        new_tests, direct, shape, best = 0, False, False, 0.0
        for tf in tfiles:
            old_src = git(top, "show", f"{base}:{tf}")
            old = test_funcs(old_src)
            # new file content = apply test_patch? approximate: new test funcs are those named in added 'def test' lines
            new_names = set(re.findall(r"^\s*(?:async\s+)?def\s+(test\w*)", added, re.M)) - set(old)
            # parse new functions from the added text, dedented per function
            for nm in new_names:
                m = re.search(r"^([ \t]*)(?:async\s+)?def\s+" + re.escape(nm) + r"\b.*?(?=^\1(?:async\s+)?def\s|^\1@|^\S|\Z)", added, re.M | re.S)
                if not m: continue
                body = "\n".join(x[len(m.group(1)):] if x.startswith(m.group(1)) else x for x in m.group(0).split("\n"))
                try: fn = ast.parse(body).body[0]
                except (SyntaxError, IndexError): continue
                new_tests += 1
                cn = called(fn)
                for on, of in old.items():
                    oc = called(of)
                    if oc & fixn: direct = True
                    if cn | oc:
                        j = len(cn & oc) / len(cn | oc)
                        best = max(best, j)
            if any(called(of) & fixn for of in old.values()): direct = True
        shape = best >= 0.5
        variants = new_tests >= 2 or "parametrize" in added
        rows.append(dict(task=t["instance_id"], rate=rate[t["instance_id"]], new_tests=new_tests, direct=direct, shape=shape, best=round(best, 2), variants=variants))
    with open(ROOT / "data/analysis/test_template_precheck.jsonl", "w") as f:
        for r in rows: f.write(json.dumps(r) + "\n")
    R14 = {"fastapi_14419", "fastapi_15589", "rich_3521", "rich_4079", "fastapi_14349", "fastapi_12942", "rich_3278", "rich_3506", "fastapi_15588",
           "fastapi_14873", "rich_3676", "fastapi_14479", "fastapi_5624", "rich_3480"}
    def summ(name, R):
        n = len(R) or 1
        print(f"  {name:40} {len(R):3} tasks | DIRECT template {sum(r['direct'] for r in R) / n:4.0%} | SHAPE template (J>=0.5) {sum(r['shape'] for r in R) / n:4.0%}"
              f" | either {sum(r['direct'] or r['shape'] for r in R) / n:4.0%} | VARIANTS {sum(r['variants'] for r in R) / n:4.0%} | new test fns found {sum(r['new_tests'] > 0 for r in R)}")
    summ("all with a base", rows)
    summ("often failing (rate < 85%, >= 6 runs)", [r for r in rows if r["rate"][1] >= 6 and r["rate"][0] / r["rate"][1] < 0.85])
    summ("the 14 discriminating (r148)", [r for r in rows if r["task"] in R14])
    for r in rows:
        if r["task"] in R14: print(f"     {r['task']:15} new tests {r['new_tests']} direct {r['direct']!s:5} best J {r['best']:.2f} variants {r['variants']}")


if __name__ == "__main__":
    main(sys.argv[1:])
