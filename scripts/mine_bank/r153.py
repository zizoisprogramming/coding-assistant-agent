"""r153: sk_a2 (control) vs sk_a2ge4 (handover agent_tool ends the gatherer stage; a.py check GREEN / RED) on 4 tasks x 2 accounts (bars in
docs/PLAN.md RUN BUILT r153). Per sk_a2ge4 run: stage order and times (gather / handover / editor), the gatherer's calls and thinking per reply,
READING CLOSED count, whether handover was called, the editor's calls with a.py check verdicts. Run: python3 -I scripts/mine_bank/r153.py"""
import ast, collections, glob, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]


def parse(x):
    if isinstance(x, dict): return x
    try: return ast.literal_eval(str(x))
    except Exception:
        try: return json.loads(str(x))
        except Exception: return {}


for d in sorted(glob.glob(str(ROOT / "data/results/2026-11-2[45]_skill_r153_s*"))):
    G = {}
    for l in open(f"{d}/results/gen_per_task.jsonl"):
        g = json.loads(l); G[g["instance_id"] + "#a" + g["attempt"]] = g
    by = collections.defaultdict(list)
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        r = json.loads(l); by[r["job"]].append(r)
    for job, rs in sorted(by.items()):
        g = G.get(job)
        if not g or g["arm"] != "sk_a2ge4": continue
        rs = sorted(rs, key=lambda r: float(r["t"])); t0 = float(rs[0]["t"])
        res = {}
        for r in rs:
            for m in r["request"]["messages"]:
                if m.get("role") == "tool": res[m.get("tool_call_id")] = str(m.get("content"))
        stages = collections.defaultdict(lambda: dict(n=0, s=0.0, first=None, last=None, calls=[], toks=[]))
        closed = 0
        for r in rs:
            msgs = r["request"]["messages"]; sysm = str(msgs[0].get("content")) if msgs and msgs[0].get("role") == "system" else ""
            st = ("editor" if "second of two engineers" in sysm else "gather" if "first of two engineers" in sysm else
                  "handover" if "You pass a colleague" in sysm else "summary")
            S = stages[st]; t = float(r["t"]) - t0; secs = float(r.get("seconds") or 0)
            S["n"] += 1; S["s"] += secs; S["first"] = t if S["first"] is None else S["first"]; S["last"] = t + secs
            rep = parse(r.get("reply")) or {}
            S["toks"].append((rep.get("usage") or {}).get("completion_tokens") or 0)
            for c in (rep.get("message") or {}).get("tool_calls") or []:
                fn = c.get("function") or {}; a = fn.get("arguments") or ""; out = res.get(c.get("id"), "")
                k = fn.get("name")
                if k == "run_command":
                    k = "a.py " + a.split("a.py", 1)[1].split()[0].strip('"}\\') if "a.py" in a else ("pytest" if "pytest" in a else "RUN" if "python" in a else "shell")
                if "READING CLOSED" in out: closed += 1
                v = re.search(r">>> (GREEN|RED again|RED|NO EDIT YET|NO CHECK SCRIPT)", out)
                S["calls"].append(k + (f"[{v.group(1)}]" if v and k == "a.py check" else ""))
        print(f"\n{Path(d).name[-2:]} {g['instance_id']}: {'SOLVED' if g['resolved'] in (True, 'True') else 'failed'} end={g['end']} patch={g['patch_chars']}")
        for st in ("gather", "handover", "editor", "summary"):
            S = stages.get(st)
            if not S: continue
            print(f"  {st:8} {S['n']:2} replies, {S['first']:.0f}-{S['last']:.0f}s, model {S['s']:.0f}s, max reply {max(S['toks'])} tok | {' '.join(S['calls'])[:300]}")
        print(f"  READING CLOSED x{closed}; handover called: {'handover' in stages['gather']['calls']}")
