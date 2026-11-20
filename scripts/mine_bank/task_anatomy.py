"""Task anatomy (user 2026-11-20: 'analyze if we can by any means give the agent the correct direction, maybe the repos have
common patterns or a rulebook ... analyze the tasks themselves'). CPU, read-only: data/tasks.jsonl (129 public competition
tasks with patch + test_patch) and every logged run (data/results/*/results/gen_per_task.jsonl) for per-task solve rates.
For each task:
  - statement kind: one-liner + link / PR that describes its change ('This PR', 'we now', 'instead of', 'now ...') / bug
    report (traceback, 'expected', 'actual', 'should') / other; length; code blocks; links to issues;
  - does the statement name the code the fix touches (changed file names, changed function / class names, in backticks or not);
  - does it contain what the hidden test checks: string / number literals and exception names on the test's added lines;
  - fix shape: files, hunks, added / removed lines, new defs, raises added, parameters added (def lines changed);
  - hidden test shape: in an existing test file or a new one; new test functions vs edited / parametrized ones;
  - per-task solve rate over all logged runs (31B agents, all arms).
Run: python3 -I scripts/mine_bank/task_anatomy.py"""
import collections, glob, json, re, statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
T = [json.loads(l) for l in open(ROOT / "data/tasks.jsonl")]
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$")

runs = collections.defaultdict(list)
for f in glob.glob(str(ROOT / "data/results/*/results/gen_per_task.jsonl")):
    for l in open(f, errors="replace"):
        try:
            g = json.loads(l)
        except Exception:
            continue
        if g.get("instance_id") and "resolved" in g and not str(g.get("arm", "")).endswith(("e4b", "12b")):
            runs[g["instance_id"]].append(g["resolved"] in (True, "True"))


def files_of(patch):
    return [m for m in re.findall(r"(?m)^\+\+\+ b/(\S+)", patch)]


def added(patch):
    return [l[1:] for l in patch.splitlines() if l.startswith("+") and not l.startswith("+++")]


def removed(patch):
    return [l[1:] for l in patch.splitlines() if l.startswith("-") and not l.startswith("---")]


def changed_names(patch):
    """function / class names whose body the fix touches (hunk headers) or defines anew."""
    names = set(re.findall(r"(?m)^@@[^@]*@@\s*(?:async\s+)?(?:def|class)\s+(\w+)", patch))
    names |= set(re.findall(r"(?m)^[+-]\s*(?:async\s+)?(?:def|class)\s+(\w+)", patch))
    return {n for n in names if not n.startswith("test")}


def kind(ps):
    p = ps.lower()
    words = len(re.findall(r"\w+", ps))
    link = bool(re.search(r"github\.com/\S+/(issues|pull|discussions)/\d+|#\d{3,}", ps))
    if words <= 25 and link:
        return "one-liner + link"
    if words <= 25:
        return "one-liner"
    if re.search(r"traceback|error:|exception|expected|actual|should (be|return|not)|instead of|currently|bug", p) and not re.search(r"this pr|in this pr|i (have )?(updated|added|changed)|we now|now (uses|returns|raises|accepts|supports)", p):
        return "bug / behaviour description"
    return "PR describes its change"


rows = []
for t in T:
    ps = t["problem_statement"]
    src_files = [f for f in files_of(t["patch"]) if f.endswith(".py") and not TEST.search(f)]
    other_files = [f for f in files_of(t["patch"]) if not (f.endswith(".py") and not TEST.search(f))]
    names = changed_names(t["patch"])
    tadd = added(t["test_patch"])
    lits = set()
    for l in tadd:
        lits |= {m for m in re.findall(r"""['"]([^'"\n]{4,80})['"]""", l) if not re.fullmatch(r"[\w./-]*test[\w./-]*", m)}
    excs = set(re.findall(r"raises\((\w+)", "\n".join(tadd)))
    new_test_file = bool(re.search(r"(?m)^--- /dev/null|^@@ -0,0 ", t["test_patch"]))
    test_defs = re.findall(r"(?m)^\+\s*def (test\w+)", t["test_patch"])
    edited_tests = re.findall(r"(?m)^@@[^@]*@@\s*def (test\w+)", t["test_patch"])
    r = runs.get(t["instance_id"], [])
    rows.append(dict(
        iid=t["instance_id"], repo=t["repo"], kind=kind(ps), words=len(re.findall(r"\w+", ps)), code=ps.count("```") // 2,
        names_in_ps=sum(n in ps for n in names), names=len(names), file_in_ps=any(Path(f).stem in ps for f in src_files),
        lits=len(lits), lits_in_ps=sum(x in ps for x in lits), excs=len(excs), excs_in_ps=sum(e in ps for e in excs),
        src_files=len(src_files), other_files=len(other_files), add=len(added(t["patch"])), rem=len(removed(t["patch"])),
        new_defs=len(re.findall(r"(?m)^\+\s*(?:async\s+)?def \w+", t["patch"])), raises=len(re.findall(r"(?m)^\+.*\braise\b", t["patch"])),
        new_test_file=new_test_file, test_defs=len(test_defs), edited_tests=len(edited_tests), n=len(r), rate=(sum(r) / len(r)) if r else None))

print(f"tasks {len(rows)} | repos {dict(collections.Counter(r['repo'] for r in rows))} | with >= 4 logged runs {sum(r['n'] >= 4 for r in rows)}")
R = [r for r in rows if r["n"] >= 4]


def show(name, key):
    groups = collections.defaultdict(list)
    for r in rows:
        groups[key(r)].append(r)
    print(f"\n#### by {name}")
    for g, xs in sorted(groups.items(), key=lambda x: -len(x[1])):
        rs = [x["rate"] for x in xs if x["n"] >= 4]
        print(f"  {str(g):34} tasks {len(xs):3} | with runs {len(rs):3} | mean solve rate {100 * st.mean(rs) if rs else 0:4.0f}% | median words {st.median(x['words'] for x in xs):4.0f}")


show("statement kind", lambda r: r["kind"])
show("repo", lambda r: r["repo"])
show("statement names a changed function / class", lambda r: "yes" if r["names_in_ps"] else ("no (fix changes named code)" if r["names"] else "fix has no named def"))
show("test literals found in the statement", lambda r: "no literals" if not r["lits"] else ("none in statement" if not r["lits_in_ps"] else ("some" if r["lits_in_ps"] < r["lits"] else "all")))
show("hidden test", lambda r: "new test file" if r["new_test_file"] else ("edits existing tests only" if not r["test_defs"] else "adds tests to an existing file"))
show("fix size (added + removed lines)", lambda r: "<= 5" if r["add"] + r["rem"] <= 5 else "6-20" if r["add"] + r["rem"] <= 20 else "21-60" if r["add"] + r["rem"] <= 60 else "> 60")
show("fix touches non-source files too (docs, config, changelog)", lambda r: "yes" if r["other_files"] else "no")
show("source files changed", lambda r: min(r["src_files"], 3))

print("\n#### overall")
print(f"  statement names a changed def/class: {sum(r['names_in_ps'] > 0 for r in rows)}/{sum(r['names'] > 0 for r in rows)} tasks whose fix changes named code")
print(f"  statement names a changed source file (stem): {sum(r['file_in_ps'] for r in rows)}/{len(rows)}")
L = [r for r in rows if r["lits"]]
print(f"  test literals: tasks with literals {len(L)}, share of literals found in the statement median {100 * st.median(r['lits_in_ps'] / r['lits'] for r in L):.0f}%,"
      f" all found {sum(r['lits_in_ps'] == r['lits'] for r in L)}, none found {sum(r['lits_in_ps'] == 0 for r in L)}")
E = [r for r in rows if r["excs"]]
print(f"  tests expecting an exception: {len(E)}, exception named in the statement {sum(r['excs_in_ps'] > 0 for r in E)}")
json.dump(rows, open(ROOT / "data/analysis/task_anatomy.json", "w"))
