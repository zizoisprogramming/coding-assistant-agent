"""Are failed patches incomplete or misplaced? (2026-11-12, the 'complete fix' check before any GPU run.)
Run: python3 -I scripts/paper/build_run_table.py && python3 -I scripts/mine_bank/patch_vs_gold.py

Uses data/analysis/run_table.jsonl (edited_files, gold_files, patch chars per run) and data/tasks.jsonl (the real fix).
(1) Size: patch chars / real-fix chars, pooled and WITHIN the same task (tasks with >= 3 solved and >= 3 wrong patches),
    because pooled numbers mix in task difficulty (big real fixes are hard tasks).
(2) Place: among runs whose edits are tracked by path (shell edits are not), the share that touched no file of the real fix."""
import collections, json, math, statistics as st

T = {json.loads(l)["instance_id"]: json.loads(l) for l in open("data/tasks.jsonl")}
R = [json.loads(l) for l in open("data/analysis/run_table.jsonl")]
R = [r for r in R if r["outcome"] in ("solved", "wrong_edit") and r["iid"] in T and r["patch"] and r.get("gold_files")]
ratio = lambda r: r["patch"] / len(T[r["iid"]]["patch"])


def sign_p(a, b):
    n = a + b
    return min(1.0, 2 * sum(math.comb(n, j) for j in range(min(a, b) + 1)) / 2 ** n) if n else 1.0


S = [r for r in R if r["outcome"] == "solved"]; W = [r for r in R if r["outcome"] == "wrong_edit"]
print(f"patches: solved {len(S)}, wrong {len(W)}; pooled size vs real fix: solved {st.median(map(ratio, S)):.2f}x, wrong {st.median(map(ratio, W)):.2f}x")
by = collections.defaultdict(lambda: ([], []))
for r in R:
    by[r["iid"]][r["outcome"] == "wrong_edit"].append(r)
rows = [(i, st.median(map(ratio, s)), st.median(map(ratio, w)), len(s), len(w)) for i, (s, w) in sorted(by.items()) if len(s) >= 3 and len(w) >= 3]
for i, rs, rw, ns, nw in rows:
    print(f"  {i:16s} solved {ns:4d} {rs:5.2f}x | wrong {nw:4d} {rw:5.2f}x")
small = sum(rw < rs for _, rs, rw, _, _ in rows); big = sum(rw > rs for _, rs, rw, _, _ in rows)
print(f"same task ({len(rows)} tasks): wrong patches smaller in {small}, bigger in {big} (sign p {sign_p(small, big):.3f}); "
      f"median wrong/solved size {st.median([rw / rs for _, rs, rw, _, _ in rows]):.2f}")
tracked = [r for r in R if any(not f.startswith("?") for f in r["edited_files"])]
off = lambda r: not any(f in r["gold_files"] for f in r["edited_files"])
for oc in ("solved", "wrong_edit"):
    rr = [r for r in tracked if r["outcome"] == oc]
    print(f"{oc:10s} tracked {len(rr)}: touched no real-fix file {sum(map(off, rr))} ({100 * sum(map(off, rr)) / len(rr):.0f}%)")
print("wrong-file patches by task:", collections.Counter(r["iid"] for r in tracked if r["outcome"] == "wrong_edit" and off(r)).most_common(8))
