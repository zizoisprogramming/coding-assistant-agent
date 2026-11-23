"""Step 0b of the missing-information idea (user 2026-11-23: 'yes run step 0b now'): do the repository's own docs, at the task's base, say
WHAT behaviour the fix needs? Run: python3 -I scripts/mine_bank/docs_precheck.py SNAPSHOT_DIR [...]
(each SNAPSHOT_DIR = an extracted data/snapshots/<task>.tgz: the repo with full history; read only through git show / git grep, never
checked out or executed; git runs with hooks and fsmonitor off). Per task: base = newest first-parent commit before created_at holding
the real fix's old lines (as fix_line_age.py); targets = functions / classes the real fix changes (hunk headers, def / class lines it
touches) + identifiers from the statement that also occur in the real fix; docs = prose docs (fastapi docs/en/docs/*.md, rich
docs/source/*.rst, requests docs/*.rst). Prints per-task hit counts and, for hand-reading, the statement head, the hidden test's
asserting lines and the best docs snippets. Writes data/analysis/docs_precheck.jsonl."""
import collections, json, re, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
DOCS = {"fastapi": ("docs/en/docs",), "rich": ("docs/source",), "requests": ("docs",)}
STOPW = {"self", "None", "True", "False", "return", "import", "from", "class", "def", "init", "name", "value", "data", "type", "args", "kwargs",
         "text", "list", "dict", "str", "int", "bool", "test", "tests", "docs", "main", "file", "path", "default", "result", "response", "request"}


def git(top, *a):
    return subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false", "-C", top, *a],
                          capture_output=True, text=True, errors="replace").stdout


def hunks(patch):
    out, f = [], None
    lines = patch.splitlines(); i = 0
    while i < len(lines):
        l = lines[i]
        if l.startswith("--- "): f = l[6:] if l.startswith("--- a/") else None
        m = re.match(r"@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@(.*)", l)
        if m and f:
            start = int(m.group(1)); old, k = [], i + 1
            while k < len(lines) and not lines[k].startswith(("@@", "--- ", "diff ")):
                s = lines[k]
                if s.startswith("-") or s.startswith(" ") or s == "": old.append(s[1:] if s else "")
                k += 1
            out.append((f, start, old, m.group(3))); i = k; continue
        i += 1
    return out


def find_base(top, task, tries=60):
    hs = [h for h in hunks(task["patch"]) if h[2]]
    if not hs: return None
    for c in git(top, "rev-list", "--first-parent", f"--before={task['created_at']}", "-n", str(tries), "HEAD").split():
        if all(git(top, "show", f"{c}:{f}").splitlines()[s - 1:s - 1 + len(o)] == o for f, s, o, _ in hs): return c
    return None


def targets(task):
    t = set()
    for f, s, o, head in hunks(task["patch"]):
        if "/tests/" in f or f.startswith("tests/") or f.startswith("docs"): continue
        for m in re.finditer(r"(?:def|class)\s+(\w+)", head + "\n" + "\n".join(o)): t.add(m.group(1))
    gp = task["patch"]
    for w in set(re.findall(r"`([A-Za-z_][\w.]{3,})`", task["problem_statement"])) | set(re.findall(r"\b([A-Za-z]+_[a-z_]+|[A-Z][a-z]+[A-Z]\w+)\b", task["problem_statement"])):
        w = w.split(".")[-1]
        if w in gp: t.add(w)
    return {x for x in t if x not in STOPW and not x.startswith("test") and len(x) > 3 and not x.startswith("_")}


def main(dirs):
    snaps = {}
    for d in dirs:
        top = git(d, "rev-parse", "--show-toplevel").strip()
        repo = re.sub(r"_\d+$", "", Path(d).name)
        snaps[repo] = (top, int(git(top, "log", "-1", "--format=%ct", "HEAD").strip()))
    rate = collections.defaultdict(lambda: [0, 0])
    import glob
    for f in glob.glob(str(ROOT / "data/results/*/results/gen_per_task.jsonl")):
        for l in open(f, errors="replace"):
            try: g = json.loads(l)
            except Exception: continue
            rate[g["instance_id"]][0] += g.get("resolved") in (True, "True"); rate[g["instance_id"]][1] += 1
    out = []
    for l in open(ROOT / "data/tasks.jsonl"):
        t = json.loads(l); repo = t["instance_id"].split("_")[0]
        if repo not in snaps: continue
        top, _ = snaps[repo]
        base = find_base(top, t)
        tg = sorted(targets(t))
        row = dict(task=t["instance_id"], base=bool(base), targets=tg, rate=rate[t["instance_id"]], hits={}, snippets=[])
        if base and tg:
            for name in tg:
                g = git(top, "grep", "-n", "-w", "-F", "-e", name, base, "--", *DOCS[repo])
                hl = [x for x in g.splitlines() if x]
                if hl: row["hits"][name] = len(hl); row["snippets"] += [(name, x.split(":", 1)[1][:260]) for x in hl[:3]]
        out.append(row)
    with open(ROOT / "data/analysis/docs_precheck.jsonl", "w") as f:
        for r in out: f.write(json.dumps(r) + "\n")
    nb = [r for r in out if r["base"]]
    win = [r for r in nb if r["rate"][1] >= 6 and 0 < r["rate"][0] / r["rate"][1] < 0.85]
    fail = [r for r in nb if r["rate"][1] >= 6 and r["rate"][0] / r["rate"][1] < 0.85]
    print(f"tasks in snapshot repos {len(out)}, base found {len(nb)}, with targets {sum(bool(r['targets']) for r in nb)}")
    for name, R in (("all with a base", nb), ("failing often (bank rate < 85%, >= 6 runs)", fail), ("sometimes solved (0 < rate < 85%)", win)):
        print(f"  {name}: {len(R)} tasks; docs mention a target {sum(bool(r['hits']) for r in R)} ({sum(bool(r['hits']) for r in R) / max(1, len(R)):.0%})")
    by = collections.Counter(r["task"].split("_")[0] for r in nb if r["hits"])
    print("  with docs hits by repo:", dict(by), "of", dict(collections.Counter(r["task"].split("_")[0] for r in nb)))


if __name__ == "__main__":
    main(sys.argv[1:])
