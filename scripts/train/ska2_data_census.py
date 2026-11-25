"""Path 1 offline step (user 2026-11-25: 'yes start both offline steps'): what training data does the bank hold for a LoRA on
sk_a2's own behaviour? Per solved sk_a2-family run with request logs: requests, compaction segments (a request whose message count
drops = a new segment), trainable reply tokens (thinking + content + tool-call arguments of every reply) and context tokens, worst
failed-call streak, submit_patch repeats, first-edit request. Curation like the papers (SWE-Prime: the best runs; LoRA curation
study: error-retry rate): clean = fail streak <= 2 and submit_patch <= 2; then a per-task cap. Tokens via data/gemma4_tokenizer.
Run: data/venv_train/bin/python -I scripts/train/ska2_data_census.py"""
import ast, collections, glob, json, os, statistics as S
from tokenizers import Tokenizer
TOK = Tokenizer.from_file("data/gemma4_tokenizer/tokenizer.json")
n_tok = lambda s: len(TOK.encode(s).ids) if s else 0
def parse(x):
    if isinstance(x, dict): return x
    try: return ast.literal_eval(str(x))
    except Exception:
        try: return json.loads(str(x))
        except Exception: return {}
rows = []
for f in glob.glob("data/results/*/results/gen_per_task.jsonl"):
    d = os.path.dirname(os.path.dirname(f)); rq = f"{d}/requests/requests.jsonl"
    if not os.path.exists(rq): continue
    G = {}
    for l in open(f):
        try: g = json.loads(l)
        except Exception: continue
        if g["arm"].startswith("sk_a2") and g.get("resolved") in (True, "True"): G[g["instance_id"] + "#a" + g["attempt"]] = g
    if not G: continue
    by = collections.defaultdict(list)
    for l in open(rq, errors="replace"):
        r = json.loads(l)
        if r["job"] in G: by[r["job"]].append(r)
    for job, rs in by.items():
        rs.sort(key=lambda r: float(r["t"])); g = G[job]
        segs, prev, reply_t, ctx_t, streak, worst, submits = 1, None, 0, 0, 0, 0, 0
        res = {m.get("tool_call_id"): str(m.get("content")) for r in rs for m in r["request"]["messages"] if m.get("role") == "tool"}
        for r in rs:
            n = len(r["request"]["messages"])
            if prev is not None and n < prev: segs += 1
            prev = n
            m = (parse(r.get("reply")) or {}).get("message") or {}
            reply_t += n_tok(m.get("reasoning_content") or "") + n_tok(m.get("content") or "")
            for c in m.get("tool_calls") or []:
                fn = c.get("function") or {}; reply_t += n_tok(str(fn.get("arguments") or "")) + 4
                out = res.get(c.get("id"), "")
                bad = '"status": "error"' in out or "Error" in out[:200]
                streak = streak + 1 if bad else 0; worst = max(worst, streak)
                if fn.get("name") == "submit_patch": submits += 1
        ctx_t = n_tok(json.dumps(rs[-1]["request"]["messages"]))
        rows.append(dict(task=g["instance_id"], arm=g["arm"], req=len(rs), segs=segs, reply_t=reply_t, ctx_t=ctx_t, worst=worst,
                         submits=submits, agent=float(g.get("agent_s") or 0)))
clean = [r for r in rows if r["worst"] <= 2 and r["submits"] <= 2]
print(f"solved sk_a2-family runs with logs: {len(rows)} | tasks {len({r['task'] for r in rows})} | clean {len(clean)}")
print(f"per run: requests median {S.median(r['req'] for r in rows)}, segments median {S.median(r['segs'] for r in rows)}, "
      f"reply tokens median {S.median(r['reply_t'] for r in rows):.0f}, last-request context median {S.median(r['ctx_t'] for r in rows):.0f}")
for cap in (3, 5, 8):
    per = collections.defaultdict(list)
    for r in sorted(clean, key=lambda r: r["agent"]): per[r["task"]].append(r)
    sel = [r for v in per.values() for r in v[:cap]]
    # trained-sequence tokens: every request is one (context + reply) sample in the old pipeline; approximate by segments x ~context
    print(f"cap {cap}/task (fastest first): {len(sel)} runs, {len(per)} tasks, reply tokens {sum(r['reply_t'] for r in sel)/1e6:.2f}M, "
          f"sequence tokens ~{sum(r['ctx_t'] * r['segs'] for r in sel)/1e6:.2f}M, repos {dict(collections.Counter(r['task'].split('_')[0] for r in sel))}")
json.dump(rows, open("data/analysis/ska2_data_census.json", "w"))
