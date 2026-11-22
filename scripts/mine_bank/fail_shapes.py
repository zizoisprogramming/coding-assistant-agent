"""Failure shapes of the sk_a2 family (user 2026-11-23: 'from the failure patterns, what can we fewshot?'). Every sk_a2* run with requests:
each FAILED run gets one shape, from tool results (not only call kinds):
  no edit, STOP READING ignored | no edit, never reached STOP READING | edit refused by the call budget |
  edit failed to apply, never recovered | edit applied then undone (patch empty) | red check after the edit, ended unchanged |
  edit kept, wrong (patch non-empty)
Run: python3 -I scripts/mine_bank/fail_shapes.py"""
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


C = collections.Counter(); ARM = collections.defaultdict(collections.Counter); N = collections.Counter(); EX = collections.defaultdict(list)
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
        if not g or not str(g.get("arm", "")).startswith("sk_a2"): continue
        rs = sorted([r for r in rs if len((r.get("request") or {}).get("messages") or []) > 1], key=lambda r: float(r["t"]))
        if not rs or "31b" not in str(rs[0]["request"].get("model", "")).lower(): continue
        N[g["arm"]] += 1
        if g.get("resolved") in (True, "True"): continue
        # tool results by id from every request
        res = {}
        for r in rs:
            for m in r["request"]["messages"]:
                if m.get("role") == "tool": res[m.get("tool_call_id")] = str(m.get("content"))
        stop = any("STOP READING" in v for v in res.values())
        ok_edit = refused = failed = 0; red_after = False
        for r in rs:
            for c in ((parse(r.get("reply")) or {}).get("message") or {}).get("tool_calls") or []:
                fn = c.get("function") or {}
                try: a = json.loads(fn.get("arguments") or "{}")
                except Exception: a = {}
                if not isinstance(a, dict): a = {}
                out = res.get(c.get("id"), "")
                if is_edit(fn.get("name"), a):
                    if "BudgetExceeded" in out: refused += 1
                    elif '"status": "error"' in out or "AssertionError" in out or "Traceback" in out: failed += 1
                    else: ok_edit += 1
                elif ok_edit and ("pytest" in str(a.get("command", "")) or "python" in str(a.get("command", ""))) and re.search(r"\b(failed|Error|Traceback)\b", out):
                    red_after = True
        patch = int(g.get("patch_chars") or 0)
        if patch > 0: s = "edit kept, wrong"
        elif ok_edit and red_after: s = "red check after edit, ended unchanged"
        elif ok_edit: s = "edit applied, ended unchanged"
        elif refused: s = "edit refused by call budget"
        elif failed: s = "edit failed to apply, never recovered"
        elif stop: s = "no edit, STOP READING ignored"
        else: s = "no edit, before STOP READING (time)" if g.get("end") == "time" else "no edit, before STOP READING"
        C[s] += 1; ARM[g["arm"]][s] += 1; EX[s].append(f"{Path(d).name[-12:]}:{g['instance_id']}")
tot = sum(C.values())
print(f"sk_a2 family: {sum(N.values())} runs, {tot} failed")
for s, n in C.most_common():
    print(f"  {s:42}{n:5}  {n / tot:5.0%}   e.g. {', '.join(EX[s][-3:])}")
