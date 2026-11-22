"""Plan for sk_a2 + repro check (user 2026-11-22). (1) sq1c2a8 family: did the repro gate catch wrong edits? Per run: first source edit,
repro runs after it, first repro output (FIXED / BUG / error), an edit after a BUG / error output, outcome. (2) sk_a2: after its first
source edit, did it run any check (own script / pytest), what did the first one print, and did it edit again; by outcome and by the
fail_place bucket. Run: python3 -I scripts/mine_bank/repro_gate.py"""
import ast, collections, glob, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SRC = re.compile(r"(repro|reproduce|check|debug|scratch|\.git/agent|/tmp/|test)")


def parse(x):
    if isinstance(x, dict): return x
    try: return ast.literal_eval(str(x))
    except Exception:
        try: return json.loads(str(x))
        except Exception: return {}


def is_src_edit(n, a):
    if n == "edit_file":
        p = str(a.get("filepath") or a.get("path") or ""); return p.endswith(".py") and not SRC.search(p)
    c = json.dumps(a)
    return ("OLD_TEXT" in c or ".replace(" in c or "sed -i" in c) and "a.py" not in c and "repro" not in c and "check.py" not in c


def is_check(a):
    c = json.dumps(a)
    return bool(re.search(r"repro|check\.py|pytest|python3? (-c|-) |python3? \.git/agent", c)) and "a.py" not in c and not ("OLD_TEXT" in c or ".replace(" in c)


def runs(arms, folders):
    out = []
    for d in folders:
        G = {}
        gp = Path(d) / "results/gen_per_task.jsonl"
        for l in open(gp, errors="replace"):
            try: g = json.loads(l); G[g["instance_id"] + "#a" + g["attempt"]] = g
            except Exception: pass
        by = collections.defaultdict(list)
        for l in open(Path(d) / "requests/requests.jsonl", errors="replace"):
            try: r = json.loads(l)
            except Exception: continue
            if r.get("job", "").split("#a")[-1].split(".")[0] in arms: by[r["job"]].append(r)
        for job, rs in by.items():
            g = G.get(job)
            if not g: continue
            rs.sort(key=lambda r: float(r["t"]))
            # flatten: each tool call with the tool output that followed (the next request's last tool message with that id)
            seq = []
            for i, r in enumerate(rs):
                m = (parse(r.get("reply")) or {}).get("message") or {}
                for c in m.get("tool_calls") or []:
                    fn = c.get("function") or {}
                    try: a = json.loads(fn.get("arguments") or "{}")
                    except Exception: a = {}
                    res = ""
                    for r2 in rs[i + 1:i + 3]:
                        for mm in (r2.get("request") or {}).get("messages") or []:
                            if mm.get("role") == "tool" and mm.get("tool_call_id") == c.get("id"): res = str(mm.get("content"))[-600:]
                        if res: break
                    seq.append((fn.get("name"), a if isinstance(a, dict) else {}, res))
            out.append((g, seq, Path(d).name))
    return out


def verdict(res):
    if "REPRO PASSES" in res or re.search(r"(^|\\n|\s)FIXED", res): return "FIXED"
    if re.search(r"\bBUG\b", res): return "BUG"
    if re.search(r"Traceback|Error|error|FAILED|failed|AssertionError", res): return "error/fail"
    if re.search(r"passed|OK\b", res): return "pass"
    return "other"


def study(name, arms, folders):
    R = runs(arms, folders)
    C = collections.Counter()
    print(f"\n==== {name}: {len(R)} runs")
    for g, seq, f in R:
        solved = g.get("resolved") in (True, "True")
        fe = next((i for i, (n, a, _) in enumerate(seq) if is_src_edit(n, a)), None)
        if fe is None:
            C[("no source edit", solved)] += 1; continue
        checks = [(i, verdict(res)) for i, (n, a, res) in enumerate(seq) if i > fe and is_check(a)]
        if not checks:
            C[("edit, no check after", solved)] += 1; continue
        first = checks[0][1]
        edit_after = any(is_src_edit(n, a) for n, a, _ in seq[checks[0][0] + 1:])
        last = checks[-1][1]
        C[(f"first check {first}" + (", edited again" if first != "FIXED" and first != "pass" and edit_after else ""), solved)] += 1
        C[(f"  (last check {last})", solved)] += 1
    keys = sorted({k for k, _ in C})
    for k in keys:
        s, f = C[(k, True)], C[(k, False)]
        print(f"  {k:42} runs {s + f:4} solved {s:3} ({s / max(1, s + f):4.0%})")


SQ = sorted(glob.glob(str(ROOT / "data/results/*e24a8*"))) + sorted(glob.glob(str(ROOT / "data/results/*e34rn*")))
study("sq1c2a8 family (sq1c2a8, a8ra, a8rc, a6rn, a6rnt)", {"sq1c2a8", "sq1c2a8ra", "sq1c2a8rc", "sq1c2a6rn", "sq1c2a6rnt"}, [d for d in SQ if Path(d, "requests/requests.jsonl").exists()])
SK = [d for d in sorted(glob.glob(str(ROOT / "data/results/*"))) if Path(d, "requests/requests.jsonl").exists() and Path(d, "results/gen_per_task.jsonl").exists()
      and ("skill_a2" in d or "d40" in d or "r138" in d or "r139" in d)]
study("sk_a2", {"sk_a2"}, SK)
