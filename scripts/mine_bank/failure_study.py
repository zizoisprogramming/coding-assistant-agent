"""Failure study on the winnable core (user 2026-11-20: 'yes do the failure study'). CPU, read-only. Core = public tasks with one
source file in the real fix and no exact text only the hidden test knows (data/analysis/statement_content.json, core=True).
Every logged run on a core task that has a saved patch (data/results/*/results/gen/patches/IID__aATTEMPT.diff) is matched to its
outcome (gen_per_task.jsonl) and classed against the real fix (data/tasks.jsonl):
  no source edit   - the patch changes no existing non-test .py file;
  wrong file       - it changes source files, but not the real-fix file;
  right file, wrong place - none of its changed lines is within 6 lines of a real-fix line (old-side line numbers);
  right place      - it changes lines next to the real fix (then: size vs the real fix, signature changes).
Solved runs are classed the same way for comparison. Writes data/analysis/failure_study.json and prints samples for reading.
Run: python3 -I scripts/mine_bank/failure_study.py"""
import collections, glob, json, re, statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$")
T = {json.loads(l)["instance_id"]: json.loads(l) for l in open(ROOT / "data/tasks.jsonl")}
SC = {r["iid"]: r for r in json.load(open(ROOT / "data/analysis/statement_content.json"))}
CORE = {i for i, r in SC.items() if r["core"]}


def old_lines(patch):
    """{file: set of old-side line numbers changed (removed lines, and the insertion point of added lines)}"""
    out, f, ln = collections.defaultdict(set), None, 0
    for l in patch.splitlines():
        if l.startswith("--- "):
            f = l[6:] if l.startswith("--- a/") else None
            continue
        if l.startswith("+++ "):
            if f is None and l.startswith("+++ b/"):
                f = None
            continue
        if l.startswith("diff --git"):
            f = None
            continue
        m = re.match(r"@@ -(\d+)", l)
        if m:
            ln = int(m.group(1))
            continue
        if f is None:
            continue
        if l.startswith("-"):
            out[f].add(ln)
            ln += 1
        elif l.startswith("+"):
            out[f].add(ln)
        elif l.startswith(" "):
            ln += 1
    return out


def size(patch, f=None):
    return sum(1 for l in patch.splitlines() if l[:1] in "+-" and not l.startswith(("+++", "---")))


res = {}
for g in glob.glob(str(ROOT / "data/results/*/results/gen_per_task.jsonl")):
    d = Path(g).parent
    for l in open(g, errors="replace"):
        try:
            x = json.loads(l)
        except Exception:
            continue
        if x.get("instance_id") in CORE:
            res[(str(d), x["instance_id"], x.get("attempt", ""))] = x["resolved"] in (True, "True")
rows = []
for (d, iid, att), ok in res.items():
    pf = Path(d) / "gen/patches" / f"{iid}__a{att}.diff"
    if not pf.exists():
        continue
    p = pf.read_text(errors="replace")
    gold = old_lines(T[iid]["patch"])
    gfile = next(iter(f for f in gold if f.endswith(".py") and not TEST.search(f)), None)
    mine = old_lines(p)
    new_files = set(re.findall(r"^diff --git a/(\S+) b/\S+\nnew file", p, re.M))
    src = {f: v for f, v in mine.items() if f.endswith(".py") and not TEST.search(f) and f not in new_files}
    if not src:
        cls = "no source edit"
    elif gfile not in src:
        cls = "wrong file"
    elif not any(abs(a - b) <= 6 for a in src[gfile] for b in gold[gfile]):
        cls = "right file, wrong place"
    else:
        cls = "right place"
    sig = len(re.findall(r"(?m)^[-+]\s*(?:async\s+)?def \w+\(", p)) - len(re.findall(r"(?m)^[-+]\s*(?:async\s+)?def \w+\(", T[iid]["patch"]))
    rows.append(dict(d=Path(d).parent.name, iid=iid, att=att, ok=ok, cls=cls, size=size(p), gold=size(T[iid]["patch"]), sig_extra=sig,
                     files=len(src), arm=att.split(".")[0]))
print(f"core tasks {len(CORE)} | runs with a saved patch on them {len(rows)} (solved {sum(r['ok'] for r in rows)}) | tasks covered {len({r['iid'] for r in rows})}")
for ok in (True, False):
    X = [r for r in rows if r["ok"] == ok]
    c = collections.Counter(r["cls"] for r in X)
    print(f"\n#### {'SOLVED' if ok else 'FAILED'} runs {len(X)}: " + ", ".join(f"{k} {v} ({100 * v / len(X):.0f}%)" for k, v in c.most_common()))
    RP = [r for r in X if r["cls"] == "right place"]
    if RP:
        print(f"  right place: patch size / real-fix size median {st.median(r['size'] / max(r['gold'], 1) for r in RP):.1f}, larger than 2x the real fix {sum(r['size'] > 2 * r['gold'] for r in RP)},"
              f" changed more def lines than the real fix {sum(r['sig_extra'] > 0 for r in RP)}, edits > 1 source file {sum(r['files'] > 1 for r in RP)}")
print("\n#### failed runs per task (class counts), tasks with >= 5 failed runs")
by = collections.defaultdict(collections.Counter)
for r in rows:
    if not r["ok"]:
        by[r["iid"]][r["cls"]] += 1
for iid, c in sorted(by.items(), key=lambda x: -sum(x[1].values())):
    if sum(c.values()) >= 5:
        tot = sum(1 for r in rows if r["iid"] == iid)
        print(f"  {iid:16} failed {sum(c.values()):3} of {tot:3} | " + ", ".join(f"{k} {v}" for k, v in c.most_common()) + f" | {SC[iid]['kind']}")
json.dump(rows, open(ROOT / "data/analysis/failure_study.json", "w"))
