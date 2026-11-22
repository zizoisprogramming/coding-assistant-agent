"""What happens right after the agent first SEES the real-fix lines (user 2026-11-23, success patterns follow-up). Within-task: for tasks
with >= 2 solved and >= 2 failed runs that saw the lines, compare solved vs failed: call index / seconds when the lines were first seen,
calls and seconds from that moment to the first source edit, what the calls in between were (more reads of the same file, reads of OTHER
files, searches, scripts), and long (capped) replies in between. Run: python3 -I scripts/mine_bank/after_seeing_fix.py"""
import collections, glob, json, math, re, statistics as st, sys, io, contextlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/mine_bank")); sys.argv = [sys.argv[0]]
with contextlib.redirect_stdout(io.StringIO()):
    import wrong_place_why as W
    from fail_place import changed
T = {json.loads(l)["instance_id"]: changed(json.loads(l)["patch"]) for l in open(ROOT / "data/tasks.jsonl")}
R = []
for d in sorted(glob.glob(str(ROOT / "data/results/*/"))):
    rp, gp = Path(d) / "requests/requests.jsonl", Path(d) / "results/gen_per_task.jsonl"
    if not rp.exists() or not gp.exists(): continue
    G = {}
    for l in open(gp, errors="replace"):
        try: g = json.loads(l); G[g["instance_id"] + "#a" + g["attempt"]] = g
        except Exception: pass
    by = collections.defaultdict(list)
    for l in open(rp, errors="replace"):
        try: r = json.loads(l)
        except Exception: continue
        if "31b" not in str((r.get("request") or {}).get("model", "")).lower(): continue
        by[r.get("job", "")].append(r)
    for job, rs in by.items():
        g = G.get(job); task = job.split("#")[0]
        if not g or not T.get(task): continue
        gold = T[task]
        rs = sorted([r for r in rs if len((r.get("request") or {}).get("messages") or []) > 1], key=lambda r: float(r["t"]))
        if not rs: continue
        t0 = float(rs[0]["t"]); bud = ((rs[0]["request"].get("kwargs") or {}).get("extra_body") or {}).get("thinking_token_budget") or 4096
        res = {}
        for r in rs:
            for mm in r["request"]["messages"]:
                if mm.get("role") == "tool": res[mm.get("tool_call_id")] = str(mm.get("content")).replace("\\n", "\n")
        idx = 0; seen_at = seen_t = None; fe = fe_t = None; between = collections.Counter(); caps_between = 0
        for r in rs:
            rep = W.parse(r.get("reply")) or {}
            o = (rep.get("usage") or {}).get("completion_tokens") or 0
            if seen_at is not None and fe is None and o >= 0.88 * bud: caps_between += 1
            for c in (rep.get("message") or {}).get("tool_calls") or []:
                fn = c.get("function") or {}
                try: a = json.loads(fn.get("arguments") or "{}")
                except Exception: a = {}
                if not isinstance(a, dict): a = {}
                if W.is_src_edit(fn.get("name"), a):
                    if fe is None: fe, fe_t = idx, float(r["t"]) - t0
                    idx += 1; continue
                sl = W.seen_lines(fn.get("name"), a, res.get(c.get("id"), ""))
                hit = False; other = False
                if sl:
                    f, nums = sl
                    gf = [x for x in gold if f and (x.endswith(f) or f.endswith(x))]
                    if gf and any(abs(x - y) <= 3 for g2 in gf for x in nums for y in gold[g2]): hit = True
                    elif not gf: other = True
                if seen_at is None and hit:
                    seen_at, seen_t = idx, float(r["t"]) + float(r["seconds"]) - t0
                elif seen_at is not None and fe is None:
                    k = W.__dict__.get("kind")
                    cmd = str(a.get("command", ""))
                    if hit or (sl and not other): between["re-read real-fix file"] += 1
                    elif other: between["read OTHER file"] += 1
                    elif "a.py find" in cmd or re.search(r"\b(grep|rg)\b", cmd): between["search"] += 1
                    elif fn.get("name") == "write_file" or "python" in cmd or "pytest" in cmd: between["script / test"] += 1
                    else: between["other"] += 1
                idx += 1
        if seen_at is None: continue
        R.append(dict(task=task, arm=g.get("arm") or "", solved=g.get("resolved") in (True, "True"), seen_at=seen_at, seen_t=seen_t,
                      edited=fe is not None and fe > seen_at, gap_calls=(fe - seen_at) if fe is not None and fe > seen_at else None,
                      gap_s=(fe_t - seen_t) if fe is not None and fe > seen_at else None, caps=caps_between, between=between))


def sign_p(a, b):
    n = a + b
    return min(1.0, 2 * sum(math.comb(n, j) for j in range(min(a, b) + 1)) / 2 ** n) if n else 1.0


by = collections.defaultdict(lambda: ([], []))
for r in R: by[r["task"]][0 if r["solved"] else 1].append(r)
mixed = {t: v for t, v in by.items() if len(v[0]) >= 2 and len(v[1]) >= 2}
print(f"runs that saw the real-fix lines: {len(R)}; tasks with >= 2 solved and >= 2 failed of them: {len(mixed)} ({sum(len(a) + len(b) for a, b in mixed.values())} runs)")
feats = [("call when the lines were first seen", lambda r: r["seen_at"]), ("seconds when first seen", lambda r: r["seen_t"]),
         ("edited after seeing them (share)", lambda r: r["edited"]), ("calls from seeing to edit", lambda r: r["gap_calls"]),
         ("seconds from seeing to edit", lambda r: r["gap_s"]), ("long (capped) replies in between", lambda r: r["caps"])]
for k in ("re-read real-fix file", "read OTHER file", "search", "script / test", "other"):
    feats.append((f"in between: {k}", (lambda kk: lambda r: r["between"][kk])(k)))
print(f"  {'feature':38}{'solved':>8}{'failed':>8}   tasks s<f / s>f   sign p")
for name, fn in feats:
    lo = hi = 0; ms, mf = [], []
    for t, (s, f) in mixed.items():
        vs = [fn(r) for r in s if fn(r) is not None]; vf = [fn(r) for r in f if fn(r) is not None]
        if not vs or not vf: continue
        a, b = st.mean(vs), st.mean(vf); ms.append(a); mf.append(b); lo += a < b; hi += a > b
    if ms: print(f"  {name:38}{st.mean(ms):8.2f}{st.mean(mf):8.2f}   {lo:3} / {hi:3}   {sign_p(lo, hi):.3f}")
