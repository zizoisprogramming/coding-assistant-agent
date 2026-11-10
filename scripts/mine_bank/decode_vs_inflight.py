"""Decode speed (completion tokens / request seconds) vs the number of requests in flight on the same server at the
same moment, from every requests log (each notebook run = one vLLM server). Usage: python3 -I scripts/mine_bank/decode_vs_inflight.py"""
import json, glob, collections, statistics as st
by = collections.defaultdict(list)
for f in sorted(glob.glob("data/results/2026-1[01]-*/requests/requests.jsonl")):
    R = []
    for l in open(f):
        try: r = json.loads(l)
        except Exception: continue
        rep = r.get("reply")
        if not isinstance(rep, dict) or not r.get("t") or not r.get("seconds"): continue
        tok = (rep.get("usage") or {}).get("completion_tokens") or 0
        pt = (rep.get("usage") or {}).get("prompt_tokens") or 0
        R.append((r["t"], r["t"] + r["seconds"], tok, pt))
    R.sort()
    for i, (a, b, tok, pt) in enumerate(R):
        if tok < 200 or b - a < 3: continue  # decode-dominated requests only
        # time-weighted mean number of OTHER requests overlapping [a, b]
        ov = 0.0
        for j in range(max(0, i - 50), min(len(R), i + 50)):
            if j == i: continue
            a2, b2 = R[j][0], R[j][1]
            ov += max(0.0, min(b, b2) - max(a, a2))
        k = round(1 + ov / (b - a))
        by[min(k, 6)].append(tok / (b - a))
for k in sorted(by):
    v = by[k]
    print(f"in flight ~{k}: {len(v):6d} requests | decode tok/s median {st.median(v):.1f} | p25 {sorted(v)[len(v)//4]:.1f} p75 {sorted(v)[3*len(v)//4]:.1f}")
