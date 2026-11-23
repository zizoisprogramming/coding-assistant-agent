"""When a run kept a wrong edit (patch > 0, not solved), did its own last check after the edit look green? (user 2026-11-23: 'knowing the
tests and the issue are the missing points ... how do you yourself get that'). A green own check + a failed hidden test = the agent's reading
of the issue differs from the grader's (interpretation / variant gap), not a failure to verify. sk_a2 family + all 31B agents.
Run: python3 -I scripts/mine_bank/own_check_vs_hidden.py"""
import ast, collections, glob, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SRC = re.compile(r"(repro|check|debug|scratch|\.git/agent|/tmp/|test)")


def parse(x):
    if isinstance(x, dict): return x
    try: return ast.literal_eval(str(x))
    except Exception:
        try: return json.loads(str(x))
        except Exception: return {}


def is_edit(n, a):
    c = str(a.get("command", ""))
    if n == "edit_file": return not SRC.search(str(a.get("filepath", "")))
    return ("OLD_TEXT" in c or ".replace(" in c or "sed -i" in c) and "a.py" not in c and "repro" not in c


C = {k: collections.Counter() for k in ("sk_a2", "all")}
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
        if not g or int(g.get("patch_chars") or 0) == 0: continue
        rs = sorted([r for r in rs if len((r.get("request") or {}).get("messages") or []) > 1], key=lambda r: float(r["t"]))
        if not rs or "31b" not in str(rs[0]["request"].get("model", "")).lower(): continue
        res = {}
        for r in rs:
            for m in r["request"]["messages"]:
                if m.get("role") == "tool": res[m.get("tool_call_id")] = str(m.get("content"))
        edited, last = False, None
        for r in rs:
            for c in ((parse(r.get("reply")) or {}).get("message") or {}).get("tool_calls") or []:
                fn = c.get("function") or {}
                try: a = json.loads(fn.get("arguments") or "{}")
                except Exception: a = {}
                if not isinstance(a, dict): a = {}
                if is_edit(fn.get("name"), a): edited = True; continue
                cmd = str(a.get("command", ""))
                if edited and ("pytest" in cmd or ("python" in cmd and "a.py" not in cmd)):
                    out = res.get(c.get("id"), "")
                    bad = bool(re.search(r"\b\d+ failed\b|Traceback|Error\b|AssertionError|\"exit_code\": [1-9]|FAILED", out))
                    last = "red" if bad else "green"
        ok = g.get("resolved") in (True, "True")
        key = ("solved" if ok else "wrong kept edit", last or "no check after the edit")
        C["all"][key] += 1
        if str(g.get("arm", "")).startswith("sk_a2"): C["sk_a2"][key] += 1
for fam, c in C.items():
    print(f"== {fam}")
    for outcome in ("wrong kept edit", "solved"):
        n = sum(v for k, v in c.items() if k[0] == outcome)
        print(f"   {outcome:16} {n:5} runs: " + ", ".join(f"last own check {k[1]} {v / n:.0%}" for k, v in sorted(c.items()) if k[0] == outcome))
