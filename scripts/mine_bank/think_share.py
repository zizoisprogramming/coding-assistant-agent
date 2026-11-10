"""Share of model output and time that is thinking, by thinking budget, over all Nov request logs."""
import json, glob, collections, statistics as st
A = collections.defaultdict(lambda: collections.Counter()); L = collections.defaultdict(list)
for f in glob.glob("data/results/2026-11-*/requests/requests.jsonl"):
    for l in open(f):
        try: r = json.loads(l)
        except Exception: continue
        rep = r.get("reply")
        if not isinstance(rep, dict) or not r.get("request", {}).get("tools"): continue
        kw = r["request"].get("kwargs", {}); eb = kw.get("extra_body") or {}
        key = (eb.get("chat_template_kwargs", {}).get("enable_thinking"), eb.get("thinking_token_budget"))
        m = rep.get("message") or {}
        rc = len(m.get("reasoning_content") or ""); tc = len(json.dumps(m.get("tool_calls") or [])); cc = len(m.get("content") or "")
        tok = (rep.get("usage") or {}).get("completion_tokens") or 0; s = r.get("seconds") or 0
        a = A[key]; a["calls"] += 1; a["think_ch"] += rc; a["args_ch"] += tc; a["text_ch"] += cc; a["tok"] += tok; a["s"] += s
        share = rc / (rc + tc + cc) if rc + tc + cc else 0
        a["think_s"] += s * share; a["no_think_calls"] += rc == 0
        L[key].append((s, tok, rc))
for k, a in sorted(A.items(), key=lambda x: -x[1]["calls"]):
    if a["calls"] < 500: continue
    print(f"thinking={k[0]} budget={k[1]}: {a['calls']} calls | {a['tok']/a['calls']:.0f} tok/call | {a['tok']/a['s']:.1f} tok/s | "
          f"{a['s']/a['calls']:.1f} s/call | thinking share of chars {a['think_ch']/(a['think_ch']+a['args_ch']+a['text_ch']):.0%} | "
          f"est. thinking share of time {a['think_s']/a['s']:.0%} | calls with no thinking {a['no_think_calls']/a['calls']:.0%}")
    xs = sorted(L[k]); n = len(xs)
    print(f"    s/call p50 {xs[n//2][0]:.1f} p90 {xs[int(n*.9)][0]:.1f} p99 {xs[int(n*.99)][0]:.1f}; calls >= 30 s hold {sum(x[0] for x in xs if x[0]>=30)/a['s']:.0%} of time")
