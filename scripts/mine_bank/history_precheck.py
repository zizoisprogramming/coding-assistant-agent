"""Pre-check for idea A (2026-11-16, user approved 'check first'): would the repository's own git history show an
agent every file a multi-file fix needs?
Run: python3 -I scripts/mine_bank/history_precheck.py CLONE_DIR   (repo root; network: blob-less clones of PUBLIC repos)

For each of the 9 test-set tasks whose real fix spans 2+ source files (data/swe_rebench/candidates.jsonl, public
SWE-rebench data): clone github.com/<repo> without file contents into CLONE_DIR, then only READ history before
base_commit with git log (git -c core.fsmonitor=false -c core.hooksPath=/dev/null; no repository code runs).
The agent's realistic starting point is ONE real-fix file it has found. From each such file F:
  `git log --oneline -N <base> -- F`  (what the example would show; N from the ranks printed here)
and for each listed commit its touched files (`git show --name-only`, what `git show --stat` would list).
A commit is USEFUL when it touches every other real-fix file that existed at base (and, if the real fix adds a new
file, it also adds a file in that file's folder); PARTIAL when it touches at least one other real-fix file.
Also: the same for the folder of a new file (`git log --oneline --diff-filter=A -- DIR`). Prints the rank of the first
useful / partial commit and the output size of the --oneline list at N = 20 / 40 / 80."""
import json, re, subprocess, sys
from pathlib import Path

TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$")
TASKS = ["Netflix-Skunkworks__policyuniverse-147", "lucianopaz__compress_pickle-28",
         "AzureAD__microsoft-authentication-library-for-python-730", "ftnext__diy-googledrive-operate-5",
         "stefmolin__data-morph-264", "terryyin__lizard-174", "Qiskit__qiskit-bot-29", "python-wheel-build__fromager-142",
         "tonioo__sievelib-113"]
CLONES = Path(sys.argv[1])
G = {}
for line in open("data/swe_rebench/candidates.jsonl"):
    r = json.loads(line)
    if r["instance_id"] in TASKS:
        G[r["instance_id"]] = r


def git(d, *args):
    p = subprocess.run(["git", "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null", "-C", str(d), *args],
                       capture_output=True, text=True, timeout=600)
    return p.stdout


def clone(repo, sha):
    d = CLONES / repo.replace("/", "__")
    if not d.exists():
        subprocess.run(["git", "clone", "-q", "--filter=blob:none", "--no-checkout", f"https://github.com/{repo}.git", str(d)],
                       check=True, timeout=900)
    if not git(d, "cat-file", "-t", sha).strip():
        subprocess.run(["git", "-C", str(d), "fetch", "-q", "--filter=blob:none", "origin", sha], timeout=900)
    return d


def touched(d, sha):
    out = git(d, "show", "--name-status", "--format=", sha)
    files = {}
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            files[parts[-1]] = parts[0][0]
    return files


summary = []
for iid in TASKS:
    g = G[iid]
    new = set(re.findall(r"^diff --git a/(\S+) b/\S+\nnew file mode", g["patch"], re.M))
    gold = [f for f in re.findall(r"^\+\+\+ b/(\S+)", g["patch"], re.M) if not TEST.search(f)]
    old = [f for f in gold if f not in new]
    d = clone(g["repo"], g["base_commit"])
    base = g["base_commit"]
    print(f"\n== {iid} | real-fix files {gold} | new {sorted(new)} | commits before base {git(d, 'rev-list', '--count', base).strip()}")
    best = None
    starts = [("file", f) for f in old] + [("added-in-dir", str(Path(f).parent)) for f in new]
    for kind, path in starts:
        args = ["log", "--oneline", base] + (["--diff-filter=A"] if kind == "added-in-dir" else []) + ["--", path]
        lines = git(d, *args).splitlines()
        first_u = first_p = None
        for rank, ln in enumerate(lines, 1):
            sha = ln.split()[0]
            t = touched(d, sha)
            others = [f for f in old if f != path]
            hit = [f for f in others if f in t]
            adds_sibling = all(any(st == "A" and str(Path(x).parent) == str(Path(n).parent) for x, st in t.items()) for n in new)
            if first_p is None and (hit or (new and adds_sibling and kind == "file")):
                first_p = (rank, ln[:70], sorted(t)[:6])
            if first_u is None and len(hit) == len(others) and (not new or adds_sibling):
                first_u = (rank, ln[:70], sorted(t)[:6])
            if first_u:
                break
        sizes = {n: len("\n".join(lines[:n])) for n in (20, 40, 80)}
        print(f"  from {kind} {path}: {len(lines)} commits | chars at N=20/40/80 {sizes[20]}/{sizes[40]}/{sizes[80]}")
        print(f"     first USEFUL  : {first_u}")
        print(f"     first PARTIAL : {first_p}")
        if first_u and (best is None or first_u[0] < best):
            best = first_u[0]
    summary.append((iid, best))

print("\nSUMMARY: rank of the first useful commit from the best starting file (None = no useful commit)")
for iid, b in summary:
    print(f"  {iid[:50]:50} {b}")
print(f"useful for {sum(b is not None for _, b in summary)} of {len(summary)} tasks; bar >= 3")
