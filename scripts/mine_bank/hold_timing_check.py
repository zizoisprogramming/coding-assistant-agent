"""Hold timing check (2026-11-25, after r163; user: "the new one beats on rich but loses on fast, I need to understand why"):
sk_a2 runs r157-r163: reads (a.py find/outline/show + grep/cat/sed/head + read_file) and seconds before the first source edit,
by repo and outcome; then, for hold thresholds (L reads OR T s), how many solves the hold would interrupt and failures it catches.
Run: python3 -I scripts/mine_bank/hold_timing_check.py"""
import json, glob, collections, re, ast, statistics as S
def parse(x):
    if isinstance(x, dict): return x
    try: return ast.literal_eval(str(x))
    except Exception:
        try: return json.loads(str(x))
        except Exception: return {}
SRC = re.compile(r"(repro|check|debug|scratch|\.git/agent|/tmp/|test)")
out = collections.defaultdict(list)
for d in sorted(glob.glob("data/results/*_skill_r15[7-9]_s*") + glob.glob("data/results/*_skill_r16[0-3]_s*")):
    G = {}
    for l in open(f"{d}/results/gen_per_task.jsonl"):
        g = json.loads(l); G[g["instance_id"] + "#a" + g["attempt"]] = g
    by = collections.defaultdict(list)
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        r = json.loads(l); by[r["job"]].append(r)
    for job, rs in by.items():
        g = G.get(job)
        if not g or g["arm"] != "sk_a2": continue
        rs = sorted([r for r in rs if len(r["request"]["messages"]) > 1], key=lambda r: float(r["t"])); t0 = float(rs[0]["t"])
        looks, fe = 0, None
        for r in rs:
            for c in ((parse(r.get("reply")) or {}).get("message") or {}).get("tool_calls") or []:
                fn = c.get("function") or {}
                try: ad = json.loads(fn.get("arguments") or "")
                except Exception: ad = {}
                if not isinstance(ad, dict): ad = {}
                cmd = str(ad.get("command", ""))
                if re.search(r"a\.py (find|outline|show)", cmd) or re.match(r"\s*(grep|cat|sed|head)", cmd) or fn.get("name") == "read_file": looks += 1
                if fe is None and fn.get("name") == "edit_file" and not SRC.search(str(ad.get("filepath", ""))):
                    fe = (looks, float(r["t"]) - t0)
        ok = g.get("resolved") in (True, "True")
        out[(g["instance_id"].split("_")[0], ok)].append(fe)
for k in sorted(out):
    v = out[k]; e = [x for x in v if x]
    print(f"{k[0]:8} {'SOLVED' if k[1] else 'failed'} n={len(v):2} edited {len(e):2} | reads before 1st edit median {S.median([x[0] for x in e]) if e else '-'} "
          f"{sorted(x[0] for x in e)} | secs median {round(S.median([x[1] for x in e])) if e else '-'} | edit after 10 reads: {sum(x[0] > 10 for x in e)}/{len(e)}")
for T in (210, 240, 270, 300, 330):
    for L in (16, 18):
        fs = out[("fastapi", True)]; rf = out[("rich", False)]; rs_ = out[("rich", True)]
        cut = lambda v: sum(1 for x in v if x and x[0] > L and x[1] > T)  # first edit after BOTH (hold = first of looks>=L or secs>=T... see below)
        hit = lambda v: sum(1 for x in v if x is None or x[0] > L or x[1] > T)  # hold fires before 1st edit if EITHER threshold passed first
        print(f"hold at {L} reads OR {T}s: interrupts fastapi solves {hit(fs)}/{len(fs)}, rich solves {hit(rs_)}/{len(rs_)}, catches rich failures {hit(rf)}/{len(rf)}, fastapi failures {hit(out[('fastapi', False)])}/{len(out[('fastapi', False)])}")
