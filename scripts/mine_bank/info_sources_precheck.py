"""Step 0 for the missing-information idea (user 2026-11-23: 'plan the missing information idea'), task file only (no repo needed):
for each public task, the hidden test (test_patch) vs the real fix (patch):
  - does the hidden test modify an existing test file (the agent can read its neighbours) or add a new file?
  - its asserted literals (strings >= 4 chars, numbers >= 2 digits) in added lines: created by the fix ('+' lines of the patch), or not
    in the fix at all (already somewhere in the repo / test-only), or old values the fix touches?
  - does the statement contain them?
Run: python3 -I scripts/mine_bank/info_sources_precheck.py"""
import collections, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
LIT = re.compile(r"""(['"])((?:(?!\1).){4,120})\1|\b(\d{2,})\b""")
T8 = {"fastapi_11194", "fastapi_14419", "fastapi_15589", "rich_3180", "rich_3470", "rich_3521", "rich_3882", "rich_4079"}
R14 = {"fastapi_14419", "fastapi_15589", "rich_3521", "rich_4079", "fastapi_14349", "fastapi_12942", "rich_3278", "rich_3506", "fastapi_15588",
       "fastapi_14873", "rich_3676", "fastapi_14479", "fastapi_5624", "rich_3480"}


def files(diff, new_only=False):
    out = []
    for m in re.finditer(r"^--- (\S+)\n\+\+\+ b/(\S+)", diff, re.M):
        out.append((m.group(2), m.group(1) == "/dev/null"))
    return out


def lits(lines):
    s = set()
    for l in lines:
        for m in LIT.finditer(l):
            v = m.group(2) or m.group(3)
            if v and not re.fullmatch(r"[\w./-]*test[\w./-]*|utf-8|__main__", v): s.add(v)
    return s


rows = []
for l in open(ROOT / "data/tasks.jsonl"):
    t = json.loads(l)
    tp, gp, st = t["test_patch"], t["patch"], t["problem_statement"]
    tf = [f for f in files(tp) if f[0].endswith(".py")]
    added_test = [x[1:] for x in tp.split("\n") if x.startswith("+") and not x.startswith("+++")]
    gplus = "\n".join(x[1:] for x in gp.split("\n") if x.startswith("+") and not x.startswith("+++"))
    grest = "\n".join(x[1:] for x in gp.split("\n") if x[:1] in ("-", " ") and not x.startswith("---"))
    L = lits([x for x in added_test if "assert" in x or "==" in x or "raises" in x or "match=" in x])
    created = {v for v in L if v in gplus and v not in grest}
    old = {v for v in L if v in grest}
    outside = L - created - old
    rows.append(dict(task=t["instance_id"], repo=t["repo"], n_tf=len(tf), modifies=any(not new for _, new in tf), new_only=bool(tf) and all(new for _, new in tf),
                     lits=len(L), created=len(created), old=len(old), outside=len(outside), in_stmt=sum(v in st for v in L)))


def summ(name, R):
    n = len(R)
    w = [r for r in R if r["lits"]]
    print(f"== {name}: {n} tasks | hidden test modifies an existing test file {sum(r['modifies'] for r in R) / n:.0%}, only new files {sum(r['new_only'] for r in R) / n:.0%}")
    if w:
        tot = lambda k: sum(r[k] for r in w)
        print(f"   {len(w)} tasks with asserted literals ({tot('lits')} literals): created by the fix {tot('created') / tot('lits'):.0%} | old values the fix touches"
              f" {tot('old') / tot('lits'):.0%} | not in the fix (already in the repo or test-only) {tot('outside') / tot('lits'):.0%} | in the statement {tot('in_stmt') / tot('lits'):.0%}")
        print(f"   tasks where EVERY asserted literal is outside the fix (findable in principle): {sum(r['outside'] == r['lits'] for r in w)}/{len(w)};"
              f" tasks with >= 1 literal the fix creates (only the fix knows it): {sum(r['created'] > 0 for r in w)}/{len(w)}")


summ("all 129 public tasks", rows)
summ("the 8 solvable dev16", [r for r in rows if r["task"] in T8])
summ("the 14 discriminating (r148)", [r for r in rows if r["task"] in R14])
for r in rows:
    if r["task"] in R14: print(f"   {r['task']:15} test files {r['n_tf']} modifies {r['modifies']!s:5} literals {r['lits']:2} created {r['created']:2} outside {r['outside']:2} in-statement {r['in_stmt']}")
