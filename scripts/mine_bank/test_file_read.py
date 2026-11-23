"""Do agents read the test file the hidden test will extend (100% of public tasks extend an existing one)? Within-task: solved vs failed
runs (all 31B agents, then the sk_a2 family). A run 'read' it when any tool call argument names that file (path or basename), and
'read before the edit' when that happened before the first source edit. Run: python3 -I scripts/mine_bank/test_file_read.py"""
import ast, collections, glob, json, math, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
TF = {}
for l in open(ROOT / "data/tasks.jsonl"):
    t = json.loads(l)
    TF[t["instance_id"]] = {m for m in re.findall(r"^\+\+\+ b/(\S+\.py)", t["test_patch"], re.M) if "conftest" not in m}
SRC = re.compile(r"(repro|check|debug|scratch|\.git/agent|/tmp/|test)")


def parse(x):
    if isinstance(x, dict): return x
    try: return ast.literal_eval(str(x))
    except Exception:
        try: return json.loads(str(x))
        except Exception: return {}


RUNS = []
for d in sorted(glob.glob(str(ROOT / "data/results/*/"))):
    gp, rp = Path(d) / "results/gen_per_task.jsonl", Path(d) / "requests/requests.jsonl"
    if not gp.exists() or not rp.exists(): continue
    G = {}
    for l in open(gp, errors="replace"):
        try: g = json.loads(l); G[g["instance_id"] + "#a" + str(g["attempt"])] = g
        except Exception: pass
    by = collections.defaultdict(list)
    for l in open(rp, errors="replace"):
        try: r = json.loads(l)
        except Exception: continue
        by[r.get("job", "")].append(r)
    for job, rs in by.items():
        g = G.get(job)
        if not g or not TF.get(g["instance_id"]): continue
        rs = sorted([r for r in rs if len((r.get("request") or {}).get("messages") or []) > 1], key=lambda r: float(r["t"]))
        if not rs or "31b" not in str(rs[0]["request"].get("model", "")).lower(): continue
        names = TF[g["instance_id"]] | {Path(f).name for f in TF[g["instance_id"]]}
        read = read_pre = False; edited = False
        for r in rs:
            for c in ((parse(r.get("reply")) or {}).get("message") or {}).get("tool_calls") or []:
                fn = c.get("function") or {}
                a = fn.get("arguments") or ""
                try: ad = json.loads(a)
                except Exception: ad = {}
                if not isinstance(ad, dict): ad = {}
                if fn.get("name") == "edit_file" and not SRC.search(str(ad.get("filepath", ""))): edited = True
                if any(n in a for n in names) and "pytest" not in a:
                    read = True; read_pre = read_pre or not edited
        RUNS.append(dict(task=g["instance_id"], arm=str(g.get("arm", "")), ok=g.get("resolved") in (True, "True"), read=read, read_pre=read_pre))


def sign_p(a, b):
    n = a + b
    return min(1.0, 2 * sum(math.comb(n, j) for j in range(min(a, b) + 1)) / 2 ** n) if n else 1.0


for fam, sel in (("ALL 31B agents", lambda r: True), ("sk_a2 family", lambda r: r["arm"].startswith("sk_a2"))):
    R = [r for r in RUNS if sel(r)]
    print(f"\n== {fam}: {len(R)} runs; read the hidden test's file (not via pytest) {sum(r['read'] for r in R) / len(R):.0%}, before the first edit {sum(r['read_pre'] for r in R) / len(R):.0%}")
    by = collections.defaultdict(lambda: ([], []))
    for r in R: by[r["task"]][0 if r["ok"] else 1].append(r)
    mixed = {t: v for t, v in by.items() if len(v[0]) >= 2 and len(v[1]) >= 2}
    for k in ("read", "read_pre"):
        up = dn = 0; ms = []; mf = []
        for t, (s, f) in mixed.items():
            a = sum(x[k] for x in s) / len(s); b = sum(x[k] for x in f) / len(f); ms.append(a); mf.append(b)
            up += a > b; dn += a < b
        print(f"   within {len(mixed)} mixed tasks, {k:9}: solved {sum(ms) / len(ms):.0%} vs failed {sum(mf) / len(mf):.0%} | tasks solved>failed {up}, < {dn}, sign p {sign_p(up, dn):.3f}")
    # solve rate by whether read before edit, within task (pooled weights)
    for k in ("read_pre",):
        diffs = []
        for t, (s, f) in mixed.items():
            allr = s + f
            y = [x["ok"] for x in allr if x[k]]; n = [x["ok"] for x in allr if not x[k]]
            if len(y) >= 2 and len(n) >= 2: diffs.append((sum(y) / len(y), sum(n) / len(n), len(y) + len(n)))
        if diffs:
            print(f"   solve rate when {k} vs not, same task ({len(diffs)} tasks with both): {sum(a for a, _, _ in diffs) / len(diffs):.0%} vs {sum(b for _, b, _ in diffs) / len(diffs):.0%}"
                  f" (tasks higher {sum(a > b for a, b, _ in diffs)}, lower {sum(a < b for a, b, _ in diffs)})")
