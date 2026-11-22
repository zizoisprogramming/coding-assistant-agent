"""Which agent has the fewest wrong-place / wrong-logic failures? (user 2026-11-22: 'i need to know what agent that had least of
those failure patterns'). Every logged 31B run with a saved patch (data/analysis/ska2_deep_runs.jsonl rows + results/gen/patches/*.diff)
is put in one bucket by comparing its patch with the real fix (data/tasks.jsonl 'patch'):
  solved | no source change (time end / ended ok) | WRONG FILE (no file of the real fix touched) |
  WRONG SPOT (right file, no changed line within NEAR lines of a real-fix line) | RIGHT SPOT, WRONG LOGIC (near the real-fix lines, not solved)
Only REACHABLE tasks count: tasks solved by at least MIN_SOLVERS different agents (drops most 'hidden exact text' / 'big feature' tasks,
which no prompt change reaches). Rates are raw and task-matched against sk_a2. Run: python3 -I scripts/mine_bank/fail_place.py"""
import collections, json, re, statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NEAR, MIN_SOLVERS, MIN_RUNS = 5, 2, 30
TEST_RE = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)conftest\.py$|^docs/|\.md$|\.rst$|\.txt$")


def changed(diff):
    """{file: set(old-line positions of removed / inserted lines)} for source files."""
    out, f, old = collections.defaultdict(set), None, 0
    for line in diff.split("\n"):
        if line.startswith("diff --git"):
            f = None
        elif line.startswith("+++ "):
            p = line[4:].strip()
            f = p[2:] if p.startswith("b/") else None
            if f and (TEST_RE.search(f) or not f.endswith(".py") or "/.git/" in f or "repro" in f or f.startswith(".git/")):
                f = None
        elif line.startswith("@@"):
            m = re.match(r"@@ -(\d+)", line)
            old = int(m.group(1)) if m else 0
        elif f is None or line.startswith("--- "):
            continue
        elif line.startswith("-"):
            out[f].add(old)
            old += 1
        elif line.startswith("+"):
            out[f].add(old)
        elif line.startswith(" "):
            old += 1
    return {k: v for k, v in out.items() if v}


T = {}
for l in open(ROOT / "data/tasks.jsonl"):
    t = json.loads(l)
    T[t["instance_id"]] = changed(t["patch"])
rows = [json.loads(l) for l in open(ROOT / "data/analysis/ska2_deep_runs.jsonl")]
solvers = collections.defaultdict(set)
for r in rows:
    if r["solved"]:
        solvers[r["task"]].add(r["arm"])
reach = {t for t, s in solvers.items() if len(s) >= MIN_SOLVERS and T.get(t)}
B = collections.defaultdict(list)
missing = 0
for r in rows:
    if r["task"] not in reach:
        continue
    att = None
    d = ROOT / "data/results" / r["folder"] / "results/gen/patches"
    if r["solved"]:
        b = "solved"
    else:
        gold = T[r["task"]]
        pf = list(d.glob(f"{r['task']}__a{r['arm']}.*.diff")) if d.exists() else []
        if not pf and r["patch"] > 0:
            missing += 1
            continue
        ch = changed(pf[0].read_text(errors="replace")) if pf else {}
        if not ch:
            b = "no source: time" if r["end"] == "time" else "no source: ended"
        elif not set(ch) & set(gold):
            b = "WRONG FILE"
        elif not any(abs(x - y) <= NEAR for f in set(ch) & set(gold) for x in ch[f] for y in gold[f]):
            b = "WRONG SPOT"
        else:
            b = "RIGHT SPOT, WRONG LOGIC"
    r["bucket"] = b
    B[r["arm"]].append(r)
KEYS = ["solved", "RIGHT SPOT, WRONG LOGIC", "WRONG SPOT", "WRONG FILE", "no source: ended", "no source: time"]
print(f"reachable tasks (solved by >= {MIN_SOLVERS} agents): {len(reach)}; runs skipped for a missing patch file: {missing}")
print(f"\n== agents with >= {MIN_RUNS} runs on reachable tasks (raw shares)")
print(f"{'arm':18}{'runs':>5}{'tasks':>6}" + "".join(f"{k[:14]:>16}" for k in KEYS) + f"{'wrong place':>13}")
arms = sorted((a for a in B if len(B[a]) >= MIN_RUNS), key=lambda a: sum(x["bucket"] in ("WRONG FILE", "WRONG SPOT") for x in B[a]) / len(B[a]))
for a in arms:
    rs = B[a]
    c = collections.Counter(x["bucket"] for x in rs)
    wp = (c["WRONG FILE"] + c["WRONG SPOT"]) / len(rs)
    print(f"{a:18}{len(rs):5}{len({x['task'] for x in rs}):6}" + "".join(f"{c[k] / len(rs):16.0%}" for k in KEYS) + f"{wp:13.0%}")


def matched(a, o):
    ta, to = collections.defaultdict(list), collections.defaultdict(list)
    for x in B[a]:
        ta[x["task"]].append(x)
    for x in B[o]:
        to[x["task"]].append(x)
    com = sorted(set(ta) & set(to))
    if len(com) < 6:
        return None
    res = {}
    for k, fn in (("solved", lambda x: x["bucket"] == "solved"), ("wrong place", lambda x: x["bucket"] in ("WRONG FILE", "WRONG SPOT")),
                  ("wrong logic", lambda x: x["bucket"] == "RIGHT SPOT, WRONG LOGIC"), ("no source", lambda x: x["bucket"].startswith("no source"))):
        res[k] = (st.mean(st.mean(map(fn, ta[t])) for t in com), st.mean(st.mean(map(fn, to[t])) for t in com))
    return len(com), sum(len(ta[t]) for t in com), res


print("\n== task-matched vs sk_a2 (agent | sk_a2), agents with >= 6 common reachable tasks, sorted by wrong place + wrong logic")
out = []
for a in B:
    if a == "sk_a2" or len(B[a]) < 16:
        continue
    m = matched(a, "sk_a2")
    if m:
        out.append((m[2]["wrong place"][0] + m[2]["wrong logic"][0] - m[2]["wrong place"][1] - m[2]["wrong logic"][1], a, m))
for d, a, (nt, na, res) in sorted(out):
    print(f"  {a:18} tasks {nt:2} runs {na:3} | solved {res['solved'][0]:.0%}/{res['solved'][1]:.0%} | wrong place {res['wrong place'][0]:.0%}/{res['wrong place'][1]:.0%}"
          f" | wrong logic {res['wrong logic'][0]:.0%}/{res['wrong logic'][1]:.0%} | no source {res['no source'][0]:.0%}/{res['no source'][1]:.0%} | wrong edits total {d:+.0%}")
