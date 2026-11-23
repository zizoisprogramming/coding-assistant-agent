"""Do wrong kept edits fix only SOME of the places the real fix changes the same line? (2026-11-23, from r149 rich_3480: sk_a2tm fixed the line in
append but not the identical line in append_text.) For tasks whose real fix removes the same non-trivial line in >= 2 places: every saved
patch (results/gen/patches/*.diff) of a failed / solved run -> how many of those places it changed. Run: python3 -I scripts/mine_bank/partial_dup_fix.py"""
import collections, glob, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]


def removed(diff):
    c = collections.Counter()
    for ln in diff.split("\n"):
        if ln.startswith("-") and not ln.startswith("---"):
            s = ln[1:].strip()
            if len(s) > 12: c[s] += 1
    return c


DUP = {}
for l in open(ROOT / "data/tasks.jsonl"):
    t = json.loads(l)
    d = {s: c for s, c in removed(t["patch"]).items() if c >= 2}
    if d: DUP[t["instance_id"]] = d
res = {}
for d in glob.glob(str(ROOT / "data/results/*")):
    try: G = [json.loads(l) for l in open(d + "/results/gen_per_task.jsonl", errors="replace")]
    except (FileNotFoundError, NotADirectoryError, json.JSONDecodeError): continue
    for g in G:
        if g["instance_id"] in DUP: res[(d, g["instance_id"], str(g.get("arm")))] = g.get("resolved") in (True, "True")
C = collections.Counter()
for p in glob.glob(str(ROOT / "data/results/*/results/gen/patches/*.diff")):
    name = Path(p).name; task = name.split("__")[0]
    if task not in DUP: continue
    arm = name.split("__a", 1)[1].rsplit(".", 2)[0] if "__a" in name else "?"
    d = str(Path(p).parents[3])
    ok = res.get((d, task, arm))
    if ok is None: continue
    rm = removed(Path(p).read_text(errors="replace"))
    touched = [s for s in DUP[task] if rm.get(s)]
    if not touched: k = "none of the repeated line"
    elif all(rm[s] >= DUP[task][s] for s in touched) and len(touched) == len(DUP[task]): k = "all places"
    else: k = "SOME places only"
    C[("solved" if ok else "failed", k)] += 1
for o in ("failed", "solved"):
    n = sum(v for k, v in C.items() if k[0] == o)
    print(f"{o:7} {n:5} patches on {len(DUP)} repeated-line tasks: " + ", ".join(f"{k[1]} {v} ({v / n:.0%})" for k, v in sorted(C.items()) if k[0] == o))
