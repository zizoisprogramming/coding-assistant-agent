"""Step 0b for sb7 (user 2026-11-18: 'do both options, lets try both'): an up-front one-call history stage keyed on
names from the issue. CPU only, git commands only on the blob-less public clones of line_history_precheck.py.
Run: python3 -I scripts/mine_bank/name_history_precheck.py CLONE_DIR   (repo root)

For each of the 40 tasks (24 test + dev16), at base_commit: names = identifiers from the issue (backticked text,
snake_case, camelCase; >= 4 chars) in order of appearance that git grep -w finds in a source .py file; the first 3
(the stage's model picks its own; this is the plain stand-in). Per name: definition lines (def / class NAME) first,
then other hits, at most 2 per name; per hit the line history of hit-2 .. hit+2 (git log -L, 2 commits, 12 lines
each, the format the stage prints). Measures: a hit inside a real-fix region (+-5 lines); a shown commit equal to one
of the last 3 commits on the real-fix lines; output size (cap 3,500 chars)."""
import collections, json, os, re, subprocess, sys
from pathlib import Path

CLONES = Path(sys.argv[1])
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$|^(docs|docs_src|examples?)/")
src = open("scripts/mine_bank/line_history_precheck.py").read()
ns = {"collections": collections, "re": re, "TEST": TEST}
exec(src[src.index("def changed_lines"):src.index("CACHE = {}")], ns)
import ast
s2 = open("scripts/train/make_skill_arms_cells.py").read()
i = s2.index("RTEST24 = [")
RT = ast.literal_eval(s2[i + 10:s2.index("]", i) + 1])
DEV = json.load(open("data/splits_public.json"))["dev16"]
T = {}
for f, ids in (("data/swe_rebench/candidates.jsonl", RT), ("data/tasks.jsonl", DEV)):
    for l in open(f):
        j = json.loads(l)
        if j["instance_id"] in ids:
            T[j["instance_id"]] = j


def git(d, *args):
    return subprocess.run(["git", "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null", "-C", str(d), *args],
                          capture_output=True, text=True, errors="replace", timeout=900).stdout


def names_of(ps):
    xs = re.findall(r"`([A-Za-z_][A-Za-z0-9_.]*)`|\b([A-Za-z_]+(?:_[A-Za-z0-9]+)+)\b|\b([a-z]+[A-Z][A-Za-z0-9]+)\b|\b([A-Z][a-z]+[A-Z][A-Za-z0-9]+)\b", ps)
    out = []
    for g in xs:
        n = next(x for x in g if x).split(".")[-1]
        if len(n) >= 4 and n not in out:
            out.append(n)
    return out


AWK = ["awk", "/^commit /{n=0} !/^(diff|index|---|[+][+][+])/ && n++<12"]
rows = []
for iid in sorted(T):
    t = T[iid]
    d = CLONES / t["repo"].replace("/", "__")
    if not d.exists():
        print(iid, "no clone")
        continue
    base = t["base_commit"]
    gl = ns["changed_lines"](t["patch"])
    gold = set()
    for f, ls in gl.items():
        for s, e in ns["regions"](ls):
            gold |= set(re.findall(r"^COMMIT (\w+)", git(d, "log", f"-L{s},{e}:{f}", "-n3", "--format=COMMIT %h", base), re.M))
    picked, out, hits_all = [], "", []
    for nm in names_of(t["problem_statement"]):
        g = git(d, "grep", "-n", "-w", "-F", "-e", nm, base, "--", "*.py")
        hits = []
        for line in g.splitlines():
            parts = line.split(":", 3)
            if len(parts) < 4 or TEST.search(parts[1]):
                continue
            hits.append((parts[1], int(parts[2]), parts[3]))
        if not hits:
            continue
        hits.sort(key=lambda h: not re.match(r"\s*(async\s+)?(def|class)\s+" + re.escape(nm) + r"\b", h[2]))
        picked.append(nm)
        for f, ln, _ in hits[:2]:
            s, e = max(1, ln - 2), ln + 2
            hits_all.append((f, ln))
            log = subprocess.run(["git", "-c", "core.fsmonitor=false", "-C", str(d), "log", f"-L{s},{e}:{f}", "-n2",
                                  "--format=commit %h %ad %s", "--date=short", base], capture_output=True, text=True, errors="replace").stdout
            log = subprocess.run(AWK, input=log, capture_output=True, text=True).stdout
            out += f"== {f} lines {s}-{e} ({nm})\n" + "\n".join(l[:150] for l in log.splitlines()) + "\n"
        if len(picked) == 3:
            break
    shown = set(re.findall(r"^commit (\w+) ", out[:3500], re.M))
    near = any(f in gl and any(abs(ln - x) <= 5 for x in gl[f]) for f, ln in hits_all)
    in_file = any(f in gl for f, _ in hits_all)
    rows.append(dict(iid=iid, names=picked, near=near, in_file=in_file, share=bool(shown & gold), chars=min(len(out), 3500), raw=len(out), n=len(hits_all)))
    print(f"{iid[:44]:44} names {picked} | hits {len(hits_all)} | real-fix file {in_file} | near real-fix lines {near} | shares a real-fix commit {bool(shown & gold)} | chars {len(out)}", flush=True)

n = len(rows)
print(f"\ntasks {n} | with a name found {sum(bool(r['names']) for r in rows)} | a hit in a real-fix file {sum(r['in_file'] for r in rows)} | within 5 lines of real-fix lines {sum(r['near'] for r in rows)}"
      f" | shows a commit of the real-fix lines' history {sum(r['share'] for r in rows)} | chars median {sorted(r['raw'] for r in rows)[n // 2]}, over 3,500 {sum(r['raw'] > 3500 for r in rows)}")
