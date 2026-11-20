"""Why do agents fail the low-rate tasks of the 8 solvable dev16 (rich_3180, rich_3470, rich_4079, rich_3521)? Per task: the issue text,
the real fix (files, size, the changed lines), what the hidden test asserts, the bank's failure classes (failure_study.json), and for failed
runs that saved a patch: which files / functions they changed and whether they touched the real-fix lines. Prints competition data to the
terminal only (never committed). Run: python3 -I scripts/mine_bank/weak_tasks.py [TASK ...]"""
import collections, glob, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TASKS = sys.argv[1:] or ["rich_3180", "rich_3470", "rich_4079", "rich_3521"]
T = {json.loads(l)["instance_id"]: json.loads(l) for l in open(ROOT / "data/tasks.jsonl")}
FS = json.load(open(ROOT / "data/analysis/failure_study.json"))
RES = {}
for f in glob.glob(str(ROOT / "data/results/*/results/gen_per_task.jsonl")):
    for l in open(f):
        try:
            g = json.loads(l)
        except Exception:
            continue
        if g["instance_id"] in TASKS:
            RES.setdefault(g["instance_id"], []).append((f, g))


def hunks(patch):
    out = collections.defaultdict(list)
    cur = None
    for l in patch.splitlines():
        if l.startswith("+++ b/"):
            cur = l[6:]
        elif l.startswith("@@"):
            m = re.search(r"@@.*@@\s*(.*)", l)
            out[cur].append(m.group(1).strip()[:60] if m else "")
    return out


for iid in TASKS:
    t = T[iid]
    print("=" * 110 + f"\n{iid}\n--- ISSUE ({len(t['problem_statement'].split())} words):\n" + t["problem_statement"][:900])
    print("--- REAL FIX:\n" + "\n".join(l for l in t["patch"].splitlines() if l[:1] in "+-@" and not l.startswith(("+++", "---")))[:1500])
    asserts = [l[1:].strip() for l in t["test_patch"].splitlines() if l.startswith("+") and not l.startswith("+++") and re.search(r"assert|raises|==", l)]
    print("--- HIDDEN TEST ASSERTS (first 10):\n" + "\n".join("  " + a[:170] for a in asserts[:10]))
    fs = [r for r in FS if r["iid"] == iid]
    print("--- FAILURE CLASSES (bank, runs with a saved patch):", dict(collections.Counter(r["cls"] for r in fs if not r["ok"])), "| solved", sum(r["ok"] for r in fs))
    runs = RES.get(iid, [])
    print(f"--- ALL LOGGED RUNS: {len(runs)} | solved {sum(g.get('resolved') in (True, 'True') for _, g in runs)} | ends {dict(collections.Counter(g.get('end') for _, g in runs))}")
    gold = hunks(t["patch"])
    touched = collections.Counter()
    for f, g in runs:
        if g.get("resolved") in (True, "True"):
            continue
        pd = Path(f).parent / "gen/patches"
        for pf in pd.glob(f"{iid}__*.diff"):
            for fn, hs in hunks(pf.read_text(errors="replace")).items():
                if fn and "test" not in fn and "reproduc" not in fn:
                    for h in hs:
                        touched[(fn, h)] += 1
    print("--- REAL-FIX HUNKS:", {k: v for k, v in gold.items()})
    print("--- FAILED PATCHES, most edited (file, function):")
    for (fn, h), n in touched.most_common(8):
        print(f"   {n:3}  {fn}  {h}" + ("   <- REAL-FIX FILE" if fn in gold else ""))
