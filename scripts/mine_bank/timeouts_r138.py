"""Where do the 480 s go? r138 + r139 (72 runs). Per run: model seconds (sum of request 'seconds'), tool / harness seconds
(gaps between one request's end and the next request's start), output tokens, tokens/s, longest replies, slowest tool
gaps with the command that caused them, compactions (prompt tokens dropping).
Run: python3 -I scripts/mine_bank/timeouts_r138.py"""
import ast, collections, glob, json, statistics as st, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
VERBOSE = "-v" in sys.argv
rows = []
for d in sorted(glob.glob(str(ROOT / "data/results/2026-11-22_skill_r13[89]_s*"))):
    G = {}
    for l in open(f"{d}/results/gen_per_task.jsonl"):
        g = json.loads(l); G[g["instance_id"] + "#a" + g["attempt"]] = g
    by = collections.defaultdict(list)
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        r = json.loads(l); by[r["job"]].append(r)
    for job, rs in by.items():
        g = G.get(job)
        if not g: continue
        rs.sort(key=lambda r: float(r["t"]))
        model = 0.0; gaps = []; toks = []; ptoks = []; comp = 0; lastcmd = "(start)"
        for i, r in enumerate(rs):
            s = float(r["seconds"]); t = float(r["t"]); model += s
            rep = r["reply"] if isinstance(r["reply"], dict) else ast.literal_eval(str(r["reply"]))
            u = rep.get("usage") or {}; toks.append((u.get("completion_tokens") or 0, s)); p = u.get("prompt_tokens") or 0
            if ptoks and p < ptoks[-1] * 0.7: comp += 1
            ptoks.append(p)
            if i:
                gaps.append((t - (float(rs[i-1]["t"]) + float(rs[i-1]["seconds"])), lastcmd))
            m = rep.get("message") or {}
            tc = m.get("tool_calls") or []
            lastcmd = "; ".join(c["function"]["name"] + " " + c["function"]["arguments"][:90].replace("\n", " ") for c in tc) or "(no tool call: nudge)"
        is_sum = [x for x in rs if len(x["request"]["messages"]) <= 1]
        rows.append(dict(run=Path(d).name[-7:] + " " + job, end=g["end"], solved=g.get("resolved") in (True, "True"), agent=float(g["agent_s"]),
                         n=len(rs), model=model, tool=sum(x for x, _ in gaps), gaps=gaps, toks=toks, ptok_max=max(ptoks), comp=comp, summ=len(is_sum),
                         nudges=sum(1 for _, c in gaps if c.startswith("(no tool"))))
def show(sel, name):
    print(f"== {name}: {len(sel)} runs")
    for k in ("agent", "model", "tool", "n"):
        print(f"  mean {k:6}: {st.mean(r[k] for r in sel):6.1f}")
    out = [t for r in sel for t, _ in r["toks"]]; sec = [s for r in sel for _, s in r["toks"]]
    print(f"  replies {len(out)}, mean out tokens {st.mean(out):.0f}, mean s/reply {st.mean(sec):.1f}, tok/s {sum(out)/sum(sec):.1f}, replies >= 2000 tok {sum(t >= 2000 for t in out)} (their s: {sum(s for t, s in zip(out, sec) if t >= 2000):.0f})")
    print(f"  mean max prompt tokens {st.mean(r['ptok_max'] for r in sel):.0f}, compactions {sum(r['comp'] for r in sel)}, nudges {sum(r['nudges'] for r in sel)}")
    allg = [x for r in sel for x, _ in r["gaps"]]
    print(f"  tool gaps: n {len(allg)}, mean {st.mean(allg):.1f}s, >= 20 s: {sum(x >= 20 for x in allg)} ({sum(x for x in allg if x >= 20):.0f} s)")
T = [r for r in rows if r["end"] == "time"]; O = [r for r in rows if r["end"] != "time"]
show(T, "TIME ENDS"); show(O, "OK ENDS")
print("\n== per time-end run: agent / model / tool s, requests, longest reply (tok, s), slowest tool gap")
for r in sorted(T, key=lambda r: r["run"]):
    lt = max(r["toks"]); sg = max(r["gaps"], default=(0, ""))
    print(f"  {r['run']:40} {r['agent']:4.0f} model {r['model']:4.0f} tool {r['tool']:4.0f} req {r['n']:2} comp {r['comp']} longest {lt[0]}tok/{lt[1]:.0f}s | slowest gap {sg[0]:.0f}s after: {sg[1][:110]}")
print("\n== slowest 25 tool gaps over all runs")
for x, c, run in sorted(((x, c, r["run"]) for r in rows for x, c in r["gaps"]), reverse=True)[:25]:
    print(f"  {x:5.0f}s {run:40} {c[:130]}")
