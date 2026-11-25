"""Why do the card arms (sk_a2s r162, sk_a2s2 r163, sk_a2s3 r164) lose on fastapi and not on rich vs sk_a2 (same runs)?
(user 2026-11-25: 'so weird man when sk_a2 solves it is fast[api] and when the other it is rich, why, dig deep')
Per run: solved, end, requests, model seconds, mean s / request, thinking chars (reasoning_content) per request, reads before the
first source edit, first-edit second, held / card. Run: python3 -I scripts/mine_bank/card_repo_split.py"""
import ast, collections, glob, json, re, statistics as S
def parse(x):
    if isinstance(x, dict): return x
    try: return ast.literal_eval(str(x))
    except Exception:
        try: return json.loads(str(x))
        except Exception: return {}
SRC = re.compile(r"(repro|check|debug|scratch|\.git/agent|/tmp/|test)")
rows = []
for rnd in ("r162", "r163", "r164"):
    for d in sorted(glob.glob(f"data/results/2026-11-25_skill_{rnd}_s*")):
        G = {}
        for l in open(f"{d}/results/gen_per_task.jsonl"):
            g = json.loads(l); G[g["instance_id"] + "#a" + g["attempt"]] = g
        by = collections.defaultdict(list)
        for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
            r = json.loads(l); by[r["job"]].append(r)
        for job, rs in by.items():
            g = G.get(job)
            if not g: continue
            rs = sorted(rs, key=lambda r: float(r["t"])); t0 = float(rs[0]["t"]) - float(rs[0]["seconds"])
            res = {m.get("tool_call_id"): str(m.get("content")) for r in rs for m in r["request"]["messages"] if m.get("role") == "tool"}
            reads, fe, held, card, think, outc, tool_out = 0, None, False, False, 0, 0, 0
            for r in rs:
                m = (parse(r.get("reply")) or {}).get("message") or {}
                think += len(m.get("reasoning_content") or ""); outc += len(m.get("content") or "")
                for c in m.get("tool_calls") or []:
                    fn = c.get("function") or {}
                    try: ad = json.loads(fn.get("arguments") or "")
                    except Exception: ad = {}
                    if not isinstance(ad, dict): ad = {}
                    cmd = str(ad.get("command", "")); out = res.get(c.get("id"), "")
                    tool_out += len(out)
                    if "HELD ONCE" in out: held = True
                    if "CARD SET" in out and "a.py card" in cmd: card = True
                    if re.search(r"a\.py (find|outline|show)", cmd) or re.match(r"\s*(grep|cat|sed|head)", cmd) or fn.get("name") == "read_file": reads += 1
                    if fe is None and fn.get("name") == "edit_file" and not SRC.search(str(ad.get("filepath", ""))) and '"status": "error"' not in out:
                        fe = (reads, float(r["t"]) - t0)
            n = len(rs)
            rows.append(dict(rnd=rnd, arm="ctl" if g["arm"] == "sk_a2" else "card", repo=g["instance_id"].split("_")[0], task=g["instance_id"],
                             ok=g.get("resolved") in (True, "True"), end=g["end"], n=n, secs=sum(float(r["seconds"]) for r in rs),
                             spr=S.mean(float(r["seconds"]) for r in rs), think=think / n, fe=fe, held=held, card=card,
                             prompt=len(json.dumps(rs[0]["request"]["messages"][0])), tout=tool_out))
def summ(R):
    E = [r for r in R if r["fe"]]
    return (f"n {len(R):2} solved {sum(r['ok'] for r in R):2} ({sum(r['ok'] for r in R)/len(R):.0%}) | time ends {sum(r['end']=='time' for r in R):2} | requests {S.mean(r['n'] for r in R):4.1f}"
            f" | s/request {S.mean(r['spr'] for r in R):4.1f} | think chars/request {S.mean(r['think'] for r in R):5.0f} | edited {len(E):2}"
            f" | 1st edit reads {S.median([r['fe'][0] for r in E]) if E else '-'} at {round(S.median([r['fe'][1] for r in E])) if E else '-'}s"
            f" | held {sum(r['held'] for r in R)} card {sum(r['card'] for r in R)}")
print("system prompt chars: ctl", S.mean(r["prompt"] for r in rows if r["arm"] == "ctl"), "card", S.mean(r["prompt"] for r in rows if r["arm"] == "card"))
for repo in ("fastapi", "rich"):
    for arm in ("ctl", "card"):
        print(f"{repo:8} {arm:4} " + summ([r for r in rows if r["repo"] == repo and r["arm"] == arm]))
print("\nper round:")
for rnd in ("r162", "r163", "r164"):
    for repo in ("fastapi", "rich"):
        print(rnd, repo, " | ".join(f"{a} {sum(r['ok'] for r in rows if r['rnd']==rnd and r['repo']==repo and r['arm']==a)}/{sum(1 for r in rows if r['rnd']==rnd and r['repo']==repo and r['arm']==a)}" for a in ("ctl", "card")))
print("\nper task (pooled r162-r164):")
for t in sorted({r["task"] for r in rows}):
    print(f"  {t:14} " + " | ".join(f"{a} {sum(r['ok'] for r in rows if r['task']==t and r['arm']==a)}/{sum(1 for r in rows if r['task']==t and r['arm']==a)}" for a in ("ctl", "card")))
print("\ncard-arm runs: solved by held/card")
C = [r for r in rows if r["arm"] == "card"]
for repo in ("fastapi", "rich"):
    for h in (False, True):
        R = [r for r in C if r["repo"] == repo and r["held"] == h]
        if R: print(f"  {repo:8} held={h!s:5} n {len(R):2} solved {sum(r['ok'] for r in R)} time ends {sum(r['end']=='time' for r in R)}")
print("\nwithout fastapi_14419:")
for repo in ("fastapi", "rich"):
    for arm in ("ctl", "card"):
        R = [r for r in rows if r["repo"] == repo and r["arm"] == arm and r["task"] != "fastapi_14419"]
        print(f"{repo:8} {arm:4} " + summ(R))
from math import comb
def fisher_le(a, b, n1, n2):
    K = a + b; return sum(comb(n1, x) * comb(n2, K - x) for x in range(0, a + 1)) / comb(n1 + n2, K)
print("\nfastapi_14419 card 0/6 vs ctl 4/6: one-sided P =", round(fisher_le(0, 4, 6, 6), 3), "(one of 8 tasks looked at: x8 for picking the worst ~", round(min(1, 8 * fisher_le(0, 4, 6, 6)), 2), ")")
