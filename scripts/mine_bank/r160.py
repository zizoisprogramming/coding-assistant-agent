"""r160 (from r159.py, 8 tasks): sk_a2 vs sk_a2p2g2 (gate + fixes 1-5). Events: !REF = a read answered with a candidate (fix 1), !RESHOW = the one re-show (fix 4), !FIND = find limited to read files (fix 2), !BLOCK = candidates block on the output (fix 3).
Old r157 doc: sk_a2 (control) vs sk_a2p2 (prompt: no experiments before the edit + failure examples) vs sk_a2p2g (+ late gate: READING CLOSED
+ EDIT CANDIDATES after STOP READING) on 4 tasks x 2 accounts (bars in docs/PLAN.md RUN BUILT r157).
Per run: outcome, end, first source edit (call, s), STOP READING (call, s), READING CLOSED refusals and the call after each,
pre-edit script work (RUN + write_file + pytest). Run: python3 -I scripts/mine_bank/r157.py"""
import ast, collections, glob, json, re, statistics as st
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SRC = re.compile(r"(repro|check|debug|scratch|\.git/agent|/tmp/|test)")
ARMS = ("sk_a2", "sk_a2p2g2")


def parse(x):
    if isinstance(x, dict): return x
    try: return ast.literal_eval(str(x))
    except Exception:
        try: return json.loads(str(x))
        except Exception: return {}


rows = []
for d in sorted(glob.glob(str(ROOT / "data/results/2026-11-24_skill_r160_s*"))):
    G = {}
    for l in open(f"{d}/results/gen_per_task.jsonl"):
        g = json.loads(l); G[g["instance_id"] + "#a" + g["attempt"]] = g
    by = collections.defaultdict(list)
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        r = json.loads(l); by[r["job"]].append(r)
    for job, rs in by.items():
        g = G.get(job)
        if not g: continue
        rs = sorted([r for r in rs if len(r["request"]["messages"]) > 1], key=lambda r: float(r["t"])); t0 = float(rs[0]["t"]) if rs else 0
        res = {}
        for r in rs:
            for m in r["request"]["messages"]:
                if m.get("role") == "tool": res[m.get("tool_call_id")] = str(m.get("content"))
        seq, fe, fe_s, stop, stop_s, after, pending, refused, budget = [], None, None, None, None, [], None, 0, 0
        for r in rs:
            for c in ((parse(r.get("reply")) or {}).get("message") or {}).get("tool_calls") or []:
                fn = c.get("function") or {}; a = fn.get("arguments") or ""; out = res.get(c.get("id"), "")
                try: ad = json.loads(a)
                except Exception: ad = {}
                if not isinstance(ad, dict): ad = {}
                n = fn.get("name"); cmd = str(ad.get("command", ""))
                if "BudgetExceeded" in out: budget += 1
                if n == "edit_file" and not SRC.search(str(ad.get("filepath", ""))) or ("OLD_TEXT" in cmd or ".replace(" in cmd) and "a.py" not in cmd:
                    k = "EDIT" if '"status": "error"' not in out and "BudgetExceeded" not in out else "EDIT-fail"
                elif "a.py" in cmd: k = cmd.split("a.py", 1)[1].split()[0]
                elif "pytest" in cmd: k = "pytest"
                elif "python" in cmd: k = "RUN"
                else: k = n if n != "run_command" else "shell"
                if "Instead, here is EDIT CANDIDATE" in out or "Instead, here is nothing" in out: k += "!CLOSED"; refused += 1
                elif "This is EDIT CANDIDATE" in out or "This is code you read before" in out: k += "!RESHOW"; refused += 1
                elif "files you have not read are not searched" in out: k += "!FIND"; refused += 1
                elif "READING CLOSED: no edit yet" in out: k += "!BLOCK"
                if pending is not None: after.append(k); pending = None
                if any(x in k for x in ("!CLOSED", "!RESHOW", "!FIND")): pending = True
                if ">>> STOP READING" in out and stop is None: stop, stop_s = len(seq), float(r["t"]) - t0; k += "!STOP"
                if k == "EDIT" and fe is None: fe, fe_s = len(seq), float(r["t"]) - t0
                seq.append(k)
        pre = sum(x.split("!")[0] in ("RUN", "write_file", "pytest") for x in (seq[:fe] if fe is not None else seq))
        rows.append(dict(s=Path(d).name[-2:], arm=g["arm"], task=g["instance_id"], ok=g.get("resolved") in (True, "True"), end=g["end"],
                         agent=float(g["agent_s"]), patch=int(g.get("patch_chars") or 0), fe=fe, fe_s=fe_s, stop=stop, stop_s=stop_s,
                         refused=refused, after=after, seq=seq, pre=pre, budget=budget))
for r in sorted(rows, key=lambda r: (r["arm"], r["task"], r["s"])):
    print(f"{r['arm']:8} {r['task']:14}{r['s']} {'SOLVED' if r['ok'] else 'failed'} {r['end']:4} {r['agent']:3.0f}s patch {r['patch']:4} "
          f"first edit {r['fe']} ({'-' if r['fe_s'] is None else round(r['fe_s'])}s) STOP {r['stop']} ({'-' if r['stop_s'] is None else round(r['stop_s'])}s) "
          f"refused {r['refused']} after {r['after']} pre-edit scripts {r['pre']} budget-refused {r['budget']}")
    print("      " + " ".join(r["seq"]))
print()
for arm in ARMS:
    R = [r for r in rows if r["arm"] == arm]; E = [r for r in R if r["fe"] is not None]
    aft = [k for r in R for k in r["after"]]
    print(f"{arm:8} solved {sum(r['ok'] for r in R)}/{len(R)} | no patch {sum(r['patch'] == 0 for r in R)} (time {sum(r['patch'] == 0 and r['end'] == 'time' for r in R)}, "
          f"call limit {sum(r['patch'] == 0 and r['end'] != 'time' for r in R)}) | time ends {sum(r['end'] == 'time' for r in R)} | mean agent {st.mean(r['agent'] for r in R):.0f}s"
          f" | edited {len(E)} | median first edit {round(st.median([r['fe_s'] for r in E])) if E else '-'}s | pre-edit scripts {sum(r['pre'] for r in R)} {[r['pre'] for r in R]}"
          f" | STOP reached {sum(r['stop'] is not None for r in R)} (before first edit {sum(r['stop'] is not None and (r['fe'] is None or r['stop'] < r['fe']) for r in R)})"
          f" | refusals {sum(r['refused'] for r in R)} in {sum(r['refused'] > 0 for r in R)} runs, next call {collections.Counter(k.split('!')[0] for k in aft)}")
