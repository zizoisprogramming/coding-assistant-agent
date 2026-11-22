"""How long do tool commands take? (user 2026-11-22: 'how can we fix the hung commands in sk_a2'). Over every logged 31B run: the gap between a
request's end and the next request's start = tool time of the calls in between; per command kind: count, share over 30 / 60 / 90 / 120 s,
timed-out (240 / 300 s) commands, and the outcome of runs with a command over each line. Run: python3 -I scripts/mine_bank/cmd_durations.py"""
import ast, collections, glob, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]


def parse(x):
    if isinstance(x, dict): return x
    try: return ast.literal_eval(str(x))
    except Exception:
        try: return json.loads(str(x))
        except Exception: return {}


def kind(n, a):
    c = str(a.get("command", "")) if isinstance(a, dict) else ""
    if n != "run_command": return n
    if "pytest" in c: return "pytest"
    if "a.py" in c: return "a.py"
    if re.search(r"python3? (-c|-\s|<<)|python3? -\s*<<", c) or "python3 -" in c: return "python inline"
    if re.search(r"python3? \S+\.py", c): return "python script"
    return "other shell"


D = collections.defaultdict(list); OUT = collections.defaultdict(list); TO = collections.Counter(); TOARM = collections.Counter()
G = {}
for f in glob.glob(str(ROOT / "data/results/*/results/gen_per_task.jsonl")):
    for l in open(f, errors="replace"):
        try: g = json.loads(l); G[(f.split("/")[-3], g["instance_id"] + "#a" + g["attempt"])] = g
        except Exception: pass
for f in glob.glob(str(ROOT / "data/results/*/requests/requests.jsonl")):
    folder = f.split("/")[-3]
    by = collections.defaultdict(list)
    for l in open(f, errors="replace"):
        try: r = json.loads(l)
        except Exception: continue
        if "31b" not in str((r.get("request") or {}).get("model", "")).lower(): continue
        by[r.get("job", "")].append(r)
    for job, rs in by.items():
        g = G.get((folder, job))
        if not g: continue
        rs = sorted([r for r in rs if len((r.get("request") or {}).get("messages") or []) > 1], key=lambda r: float(r["t"]))
        solved = g.get("resolved") in (True, "True")
        mx = 0
        for i in range(len(rs) - 1):
            tc = ((parse(rs[i].get("reply")) or {}).get("message") or {}).get("tool_calls") or []
            if len(tc) != 1: continue
            fn = tc[0].get("function") or {}
            try: a = json.loads(fn.get("arguments") or "{}")
            except Exception: a = {}
            gap = float(rs[i + 1]["t"]) - float(rs[i]["t"]) - float(rs[i]["seconds"])
            k = kind(fn.get("name"), a if isinstance(a, dict) else {})
            D[k].append(gap); mx = max(mx, gap)
            nxt = str(((rs[i + 1].get("request") or {}).get("messages") or [{}])[-1].get("content", ""))
            if "TimeoutExceeded" in nxt or "timed out after" in nxt:
                TO[k] += 1; TOARM[job.split("#a")[-1].split(".")[0]] += 1
        OUT[min((x for x in (30, 60, 90, 120, 200, 10 ** 9) if mx < x))].append(solved)
print(f"{'command kind':15}{'n':>7}{'>30s':>8}{'>60s':>8}{'>90s':>8}{'>120s':>8}{'timed out':>11}")
for k, v in sorted(D.items(), key=lambda x: -len(x[1])):
    n = len(v)
    print(f"{k:15}{n:7}" + "".join(f"{sum(x > t for x in v):8}" for t in (30, 60, 90, 120)) + f"{TO[k]:11}")
print("\nruns by their LONGEST tool call: count, solved")
for b in sorted(OUT):
    lab = f"< {b} s" if b < 10 ** 9 else ">= 200 s"
    print(f"  {lab:10} runs {len(OUT[b]):5} solved {sum(OUT[b]) / len(OUT[b]):.0%}")
print("\ntimed-out commands by agent (top 12):", TOARM.most_common(12))
