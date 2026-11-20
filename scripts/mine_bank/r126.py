"""r126: sb1hl vs sb1hlg (T 1.0 / top_k 64) on rich_3506, rich_3521, fastapi_11194, peewee (docs/PLAN.md RUN BUILT r126, bars there).
Run: python3 -I scripts/mine_bank/r126.py RESULT_DIR [RESULT_DIR ...]
1. r123-style per-arm table on the given folders;
2. per arm: runs with a reply >= 3,800 output tokens (thinking allowance used up), replies at the 8,192 cap, never-edit runs
   (no heredoc edit sent), broken calls ('mandatory input parameters' / fence errors), longest reply median."""
import ast, collections, glob, json, statistics as st, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIRS = sys.argv[1:]
src = (ROOT / "scripts/mine_bank/r123.py").read_text()
src = src.replace('DIRS = sorted(glob.glob(str(ROOT / "data/results/2026-11-2*_skill_r123_p*")))', "DIRS = " + repr([str(Path(d).resolve()) for d in DIRS]))
src = src.replace('ARMS = ("sb1h", "sb1hl")', 'ARMS = ("sb1hl", "sb1hlg")')
exec(compile(src, "r123_on_r126", "exec"), {"__name__": "__main__", "__file__": str(ROOT / "scripts/mine_bank/r123.py")})
M = collections.defaultdict(lambda: collections.defaultdict(list))
for d in DIRS:
    runs = collections.defaultdict(list)
    for l in open(Path(d) / "requests/requests.jsonl", errors="replace"):
        try:
            r = json.loads(l)
        except Exception:
            continue
        runs[r["job"]].append(r)
    for job, rs in runs.items():
        arm = job.split("#a")[1].split(".")[0]
        maxed = capped = broken = 0
        edited = False
        longest = 0
        for r in rs:
            longest = max(longest, float(r.get("seconds") or 0))
            try:
                dd = ast.literal_eval(str(r["reply"]))
            except Exception:
                continue
            t = (dd.get("usage") or {}).get("completion_tokens") or 0
            maxed += t >= 3800
            capped += t >= 8000
            m = dd.get("message") or {}
            edited |= any("OLD_TEXT" in str(c["function"]["arguments"]) for c in m.get("tool_calls") or [])
            last = r["request"]["messages"][-1]
            if last.get("role") == "tool":
                c = str(last.get("content"))
                broken += "mandatory input parameters" in c or "unexpected EOF while looking for matching" in c
        M[arm]["maxed"].append(maxed)
        M[arm]["capped"].append(capped)
        M[arm]["noedit"].append(not edited)
        M[arm]["broken"].append(broken)
        M[arm]["longest"].append(longest)
print("\n#### thinking loops and broken calls")
for a in ("sb1hl", "sb1hlg"):
    x = M[a]
    n = len(x["maxed"])
    if not n:
        continue
    print(f"  {a:7} runs {n} | runs with a reply >= 3,800 tokens {sum(v > 0 for v in x['maxed'])} (replies {sum(x['maxed'])}) | replies at the 8,192 cap {sum(x['capped'])}"
          f" | never sent an edit {sum(x['noedit'])} | broken-call results {sum(x['broken'])} (runs {sum(v > 0 for v in x['broken'])}) | longest reply median {st.median(x['longest']):.0f} s")
