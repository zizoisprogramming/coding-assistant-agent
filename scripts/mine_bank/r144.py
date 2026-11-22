"""r144: sk_a2_60x alone (prompt rewritten around LOOK -> RUN once -> EDIT -> LOOK AGAIN + RUN) on the 8 solvable dev16, 2 passes
(bars in docs/PLAN.md RUN BUILT r144). Per run: outcome, end, agent s, call-kind sequence, first source edit call, code runs before /
after the edit, rhythm (run -> edit -> run), compactions, capped replies, last reply text for no-edit runs.
Run: python3 -I scripts/mine_bank/r144.py"""
import ast, collections, glob, json, re, statistics as st, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SRC = re.compile(r"(repro|reproduce|check|debug|scratch|\.git/agent|/tmp/|test)")


def parse(x):
    if isinstance(x, dict): return x
    try: return ast.literal_eval(str(x))
    except Exception:
        try: return json.loads(str(x))
        except Exception: return {}


def kind(n, a):
    c = str(a.get("command", ""))
    if n == "run_skill_script": return "install"
    if n == "edit_file": return "EDIT" if not SRC.search(str(a.get("filepath", ""))) else "scratch"
    if n == "write_file": return "write"
    if n in ("submit_patch", "get_status"): return n[:6]
    if n == "read_file": return "read"
    if ("OLD_TEXT" in c or ".replace(" in c or "sed -i" in c) and "a.py" not in c: return "EDIT"
    if "a.py show" in c: return "show"
    if "a.py find" in c or re.search(r"(^|\s)(git grep|grep|rg)\b", c): return "find"
    if "a.py outline" in c: return "outline"
    if "pytest" in c: return "pytest"
    if "python" in c: return "RUN"
    if re.search(r"(^|\s)(cat|sed -n|head|tail|nl)\b", c): return "read"
    return "shell"


rows = []
for d in sorted(glob.glob(str(ROOT / "data/results/2026-11-23_skill_r144_s*"))):
    G = {}
    for l in open(f"{d}/results/gen_per_task.jsonl"):
        g = json.loads(l); G[g["instance_id"] + "#a" + g["attempt"]] = g
    by = collections.defaultdict(list)
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        r = json.loads(l); by[r["job"]].append(r)
    for job, rs in by.items():
        g = G.get(job)
        if not g: continue
        allr = sorted(rs, key=lambda r: float(r["t"]))
        summ = sum(len(r["request"]["messages"]) <= 1 for r in allr)
        rs = [r for r in allr if len(r["request"]["messages"]) > 1]
        budget = ((rs[0]["request"].get("kwargs") or {}).get("extra_body") or {}).get("thinking_token_budget") or 4096
        ks, comp, cap, last_p, last_txt = [], 0, 0, 0, ""
        for r in rs:
            rep = parse(r.get("reply")) or {}
            u = rep.get("usage") or {}
            p = u.get("prompt_tokens") or 0
            if last_p and p < 0.7 * last_p: comp += 1
            last_p = p
            if (u.get("completion_tokens") or 0) >= 0.88 * budget: cap += 1
            m = rep.get("message") or {}
            if m.get("content"): last_txt = str(m["content"])[-200:]
            for c in m.get("tool_calls") or []:
                fn = c.get("function") or {}
                try: a = json.loads(fn.get("arguments") or "{}")
                except Exception: a = {}
                ks.append(kind(fn.get("name"), a if isinstance(a, dict) else {}))
        fe = next((i for i, k in enumerate(ks) if k == "EDIT"), None)
        pre, post = (ks[:fe], ks[fe + 1:]) if fe is not None else (ks, [])
        runs_pre = sum(k in ("RUN", "write") for k in pre)
        rhythm = fe is not None and runs_pre >= 1 and any(k in ("RUN", "pytest") for k in post)
        rows.append(dict(s=Path(d).name[-2:], task=g["instance_id"], ok=g.get("resolved") in (True, "True"), end=g.get("end"),
                         agent=float(g.get("agent_s") or 0), patch=int(g.get("patch_chars") or 0), fe=fe, runs_pre=runs_pre,
                         runs_post=sum(k in ("RUN", "pytest") for k in post), rhythm=rhythm, comp=comp, summ=summ, cap=cap, ks=ks, last=last_txt))
for r in sorted(rows, key=lambda r: (r["task"], r["s"])):
    print(f"{r['task']:14}{r['s']} {'SOLVED' if r['ok'] else 'failed':7}{r['end']:5}{r['agent']:5.0f}s patch {r['patch']:4} fe {str(r['fe']):4} "
          f"runs pre/post {r['runs_pre']}/{r['runs_post']} rhythm {'Y' if r['rhythm'] else '-'} comp {r['comp']} sum {r['summ']} cap {r['cap']}")
    print("    " + " ".join(k for k in r["ks"]))
    if r["fe"] is None: print("    last text:", repr(r["last"][-160:]))
n = len(rows)
print(f"\nsolved {sum(r['ok'] for r in rows)}/{n}; mean agent {st.mean(r['agent'] for r in rows):.0f} s; compactions/run {st.mean(r['comp'] for r in rows):.2f}"
      f" (summary calls {st.mean(r['summ'] for r in rows):.2f}); rhythm {sum(r['rhythm'] for r in rows)}/{n}; edited {sum(r['fe'] is not None for r in rows)}/{n}")
ed = [r for r in rows if r["fe"] is not None]
print(f"edited runs: solved {sum(r['ok'] for r in ed)}/{len(ed)}; runs before edit <= 1: {sum(r['runs_pre'] <= 1 for r in ed)}/{len(ed)}; mean first edit call {st.mean(r['fe'] for r in ed):.1f}")
ne = [r for r in rows if r["fe"] is None]
print(f"no-edit runs {len(ne)}: mean RUNs {st.mean(sum(k == 'RUN' for k in r['ks']) for r in ne):.1f}, shows {st.mean(r['ks'].count('show') for r in ne):.1f}, calls {st.mean(len(r['ks']) for r in ne):.1f}")
