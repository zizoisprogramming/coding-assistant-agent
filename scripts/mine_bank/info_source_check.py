"""Path 2 offline check (user 2026-11-25: 'yes start both offline steps'): the oracle information test (r45 / r61, sq1c2a6i vs
sq1c2a6info, 38 tasks x 2 passes) proved information moves solves (39% vs 8%). Could that information be found INSIDE the sandbox?
Per task: the info text = the info arm's system prompt minus the base arm's (hidden-test lines or the linked GitHub report);
facts = string literals (>= 4 chars) and specific names (snake_case / CamelCase / dotted, >= 4 chars) in the info that the issue
text does not already contain (test scaffolding words dropped). Each fact is searched in the repo at base_commit: source code
(non-test .py), existing tests, docs (.md / .rst / docs_src), and commit messages before base_commit (git log --all at base).
Reported: per task the share of new facts found anywhere / in source / tests / docs / history, and for the tasks info turned
from fail to solve. Run: python3 -I scripts/mine_bank/info_source_check.py CLONE_DIR   (blob-less clones owner__repo; checks the
base tree out into CLONE_DIR/../wt_info, batch blob fetch; writes nothing in the repo)"""
import collections, difflib, json, keyword, os, re, shutil, subprocess, sys
from pathlib import Path
CLONES = Path(sys.argv[1]); WT = CLONES.parent / "wt_info"
GIT = ["git", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false"]
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)conftest\.py$")
STOP = set(keyword.kwlist) | {"assert", "pytest", "TestClient", "tmp_path", "response", "status_code", "monkeypatch", "capsys", "self",
       "None", "True", "False", "import", "from", "def", "class", "return", "client", "json", "text", "write_file", "write_text",
       "parent", "mkdir", "parents", "exist_ok", "content", "path", "Path", "test", "tests", "value", "result", "expected",
       "print", "isinstance", "raises", "match", "fixture", "parametrize", "mark", "params", "description", "https", "github",
       "com", "pull", "issues", "issue", "Fixes", "fixes", "should", "would", "could", "there", "which", "their", "about"}
def git(repo, *a, timeout=900):
    r = subprocess.run(GIT + list(a), cwd=repo, capture_output=True, text=True, timeout=timeout, errors="replace")
    return r.stdout if r.returncode == 0 else ""
tasks = {json.loads(l)["instance_id"]: json.loads(l) for l in open("data/tasks.jsonl")}
info, base, res = {}, {}, collections.defaultdict(lambda: collections.defaultdict(list))
for d in ("2026-11-05_skill_info38", "2026-11-08_skill_info38_p2"):
    for l in open(f"data/results/{d}/results/gen_per_task.jsonl"):
        g = json.loads(l); res[g["instance_id"]][g["arm"]].append(g.get("resolved") in (True, "True"))
    for l in open(f"data/results/{d}/requests/requests.jsonl", errors="replace"):
        r = json.loads(l); t, arm = r["job"].split("#a"); arm = arm.split(".")[0]
        c = r["request"]["messages"][0]["content"]; c = c if isinstance(c, str) else json.dumps(c)
        (info if arm.endswith("info") else base).setdefault(t, c)
def added(a, b):
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return "".join(b[j1:j2] for op, i1, i2, j1, j2 in sm.get_opcodes() if op in ("insert", "replace"))
def facts(txt, issue):
    lits = {m.strip() for m in re.findall(r"\"([^\"\n]{4,80})\"|'([^'\n]{4,80})'", txt) for m in m if m}
    names = set(re.findall(r"\b(?:[A-Za-z_]\w*\.)+[A-Za-z_]\w*\b|\b[a-z]+_[a-z0-9_]+\b|\b[A-Z][a-z]+[A-Z]\w*\b", txt))
    out = set()
    for f in lits | names:
        f = f.strip()
        if len(f) < 4 or f in STOP or f.split(".")[0] in STOP or f in issue: continue
        if re.fullmatch(r"[\W\d_]+", f): continue
        out.add(f)
    return sorted(out)
rows = []
for t in sorted(info):
    T = tasks[t]; repo = CLONES / T["repo"].replace("/", "__")
    txt = added(base[t], info[t]); kind = "tests" if "hidden tests" in txt[:200] else "report"
    F = facts(txt, T["problem_statement"])
    if WT.exists(): shutil.rmtree(WT)
    WT.mkdir(parents=True)
    tree = [p for p in git(repo, "ls-tree", "-r", "--name-only", T["base_commit"]).split("\n") if p and re.search(r"\.(py|md|rst|txt|toml|cfg)$", p)
            and not re.match(r"docs/(?!en/)[a-z]{2}(-[a-z]+)?/", p)]  # 2026-11-25: English docs only (fastapi's translations were the bulk)
    # one batch fetch of the missing blobs (a checkout of a blob-less clone fetched them one by one: 24 min for one task)
    lst = git(repo, "ls-tree", "-r", T["base_commit"], "--", *tree)
    oids = [l.split()[2] for l in lst.splitlines() if l.split()[1] == "blob"]
    miss = [o for o in subprocess.run(GIT + ["cat-file", "--batch-check=%(objectname) %(objecttype)"], cwd=repo, input="\n".join(oids),
            capture_output=True, text=True, env=dict(os.environ, GIT_NO_LAZY_FETCH="1")).stdout.splitlines() if o.endswith("missing")]
    miss = [o.split()[0] for o in miss]
    if miss:
        subprocess.run(GIT + ["-c", "fetch.negotiationAlgorithm=noop", "fetch", "origin", "--no-tags", "--no-write-fetch-head",
                              "--recurse-submodules=no", "--filter=blob:none", "--stdin"], cwd=repo, input="\n".join(miss),
                       capture_output=True, text=True, timeout=1800)
    subprocess.run(GIT + ["--work-tree", str(WT), "checkout", T["base_commit"], "--"] + tree, cwd=repo, capture_output=True, timeout=1800)
    subprocess.run(GIT + ["reset", "-q"], cwd=repo, capture_output=True, timeout=120)
    texts = {"source": [], "tests": [], "docs": []}
    for p in tree:
        try: s = (WT / p).read_text(errors="replace")
        except OSError: continue
        k = "tests" if TEST.search(p) else ("source" if p.endswith(".py") and not p.startswith("docs_src") else "docs")
        texts[k].append(s)
    blob = {k: "\n".join(v) for k, v in texts.items()}
    blob["history"] = git(repo, "log", "--format=%s%n%b", T["base_commit"])
    found = {f: [k for k in ("source", "tests", "docs", "history") if f in blob[k]] for f in F}
    i, b = res[t]["sq1c2a6info"], res[t]["sq1c2a6i"]
    rows.append(dict(task=t, kind=kind, info=sum(i), base=sum(b), n=len(F), found=found))
    anyf = sum(bool(v) for v in found.values())
    print(f"{t:16} {kind:6} info {sum(i)}/{len(i)} base {sum(b)}/{len(b)} | new facts {len(F):3} found {anyf:3} "
          f"({anyf / max(len(F), 1):4.0%}) src {sum('source' in v for v in found.values()):3} tests {sum('tests' in v for v in found.values()):3} "
          f"docs {sum('docs' in v for v in found.values()):3} hist {sum('history' in v for v in found.values()):3} | missing e.g. "
          f"{[f for f, v in found.items() if not v][:4]}", flush=True)
if WT.exists(): shutil.rmtree(WT)
json.dump(rows, open("data/analysis/info_source_check.json", "w"), indent=0)
def summ(R, lab):
    n = sum(r["n"] for r in R); f = sum(bool(v) for r in R for v in r["found"].values())
    print(f"{lab:40} tasks {len(R):2} | new facts {n:4} found in the sandbox {f:4} ({f / max(n, 1):.0%}) | tasks with >= half found {sum(sum(bool(v) for v in r['found'].values()) >= r['n'] / 2 for r in R if r['n'])}")
print()
summ(rows, "all 38")
summ([r for r in rows if r["info"] > r["base"]], "info helped (info solves > base)")
summ([r for r in rows if r["kind"] == "tests"], "info = hidden-test lines")
summ([r for r in rows if r["kind"] == "report"], "info = GitHub report")
