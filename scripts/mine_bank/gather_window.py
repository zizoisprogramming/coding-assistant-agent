"""Would a ~10-call information gatherer have the real-fix lines? (user 2026-11-23: 'an agent that gathers info for like 10 calls and one that
edits'). sk_a2-family runs: the call index at which an a.py show first printed lines within NEAR of a real-fix line (stop_block_check's
shown_gold), as a share of runs reaching it by call 8 / 10 / 12 / 15 / ever; solved vs failed. Run: python3 -I scripts/mine_bank/gather_window.py"""
import ast, collections, glob, json, re, statistics as st
from pathlib import Path
import runpy, io, contextlib
ROOT = Path(__file__).resolve().parents[2]
_buf = io.StringIO()
with contextlib.redirect_stdout(_buf):
    SB = runpy.run_path(str(ROOT / "scripts/mine_bank/stop_block_check.py"))
shown_gold, parse = SB["shown_gold"], SB["parse"]
R = collections.defaultdict(list)
for d in sorted(glob.glob(str(ROOT / "data/results/*"))):
    gp, rp = Path(d) / "results/gen_per_task.jsonl", Path(d) / "requests/requests.jsonl"
    if not gp.exists() or not rp.exists(): continue
    G = {}
    for l in open(gp, errors="replace"):
        try: g = json.loads(l); G[g["instance_id"] + "#a" + str(g["attempt"])] = g
        except Exception: pass
    by = collections.defaultdict(list)
    for l in open(rp, errors="replace"):
        try: r = json.loads(l)
        except Exception: continue
        by[r.get("job", "")].append(r)
    for job, rs in by.items():
        g = G.get(job)
        if not g or not str(g.get("arm", "")).startswith("sk_a2") or g["instance_id"] not in SB["GOLD"]: continue
        rs = sorted([r for r in rs if len((r.get("request") or {}).get("messages") or []) > 1], key=lambda r: float(r["t"]))
        res = {}
        for r in rs:
            for m in r["request"]["messages"]:
                if m.get("role") == "tool": res[m.get("tool_call_id")] = str(m.get("content"))
        k, first = 0, None
        for r in rs:
            for c in ((parse(r.get("reply")) or {}).get("message") or {}).get("tool_calls") or []:
                fn = c.get("function") or {}
                if fn.get("name") in ("submit_patch", "get_status"): continue
                k += 1
                try: a = json.loads(fn.get("arguments") or "{}")
                except Exception: a = {}
                if first is None and isinstance(a, dict) and shown_gold(g["instance_id"], str(a.get("command", "")), res.get(c.get("id"), "")): first = k
        R["solved" if g.get("resolved") in (True, "True") else "failed"].append(first)
for k, v in R.items():
    n = len(v); got = [x for x in v if x is not None]
    print(f"{k:7} {n:4} runs: real-fix lines shown by call " + ", ".join(f"{c}: {sum(x <= c for x in got) / n:.0%}" for c in (8, 10, 12, 15)) +
          f", ever: {len(got) / n:.0%}; median call when shown {st.median(got) if got else '-'}")
