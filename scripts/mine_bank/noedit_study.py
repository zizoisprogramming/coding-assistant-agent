"""Where do sk_a2-family runs that never edit spend their 8 minutes? (user 2026-11-24: 'lets see how we can solve the rest').
Over r144-r156 runs of single-agent sk_a2-family arms (sk_a2, sk_a2_60*, sk_a2x*, sk_a2c*, sk_a2o*): per run outcome class
(solved / wrong edit / no edit), model seconds, replies >= 60 s, reasoning chars, tool calls, and whether the reasoning already
named a concrete fix before the run ended without an edit ('decided but did not edit'). Run: python3 -I scripts/mine_bank/noedit_study.py"""
import collections, glob, json, re, statistics as st
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
DECIDE = re.compile(r"(the fix (is|would be|should be)|I (will|need to|should) (change|modify|replace|update|add|edit)|should be changed to|change (it|this|the line) to|the bug is)", re.I)
rows = []
for d in sorted(glob.glob(str(ROOT / "data/results/2026-11-2*_skill_r1[45]*"))):
    try:
        G = {}
        for l in open(f"{d}/results/gen_per_task.jsonl"):
            g = json.loads(l); G[g["instance_id"] + "#a" + g["attempt"]] = g
        by = collections.defaultdict(list)
        for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
            r = json.loads(l); by[r["job"]].append(r)
    except OSError:
        continue
    for job, rs in by.items():
        g = G.get(job)
        if not g or not re.match(r"sk_a2(_60\w*|x\w*|c\w*|o\w*|t\w*)?$", g["arm"]) or "ge" in g["arm"]:
            continue
        rs = sorted(rs, key=lambda r: float(r["t"]))
        edited = False; first_decide = None; secs = 0; long = 0; rchars = 0; calls = 0; t0 = float(rs[0]["t"])
        for r in rs:
            m = (r.get("reply") or {}).get("message") or {}
            s = float(r.get("seconds") or 0); secs += s; long += s >= 60
            rc = m.get("reasoning_content") or ""; rchars += len(rc)
            if first_decide is None and not edited and DECIDE.search(rc): first_decide = float(r["t"]) - t0
            for c in m.get("tool_calls") or []:
                calls += 1
                fn = c.get("function") or {}
                a = fn.get("arguments") or ""
                if fn.get("name") == "edit_file" and ".git/agent" not in a or ".replace(" in a and "a.py" not in a: edited = True
        patch = int(g.get("patch_chars") or 0); ok = g.get("resolved") in (True, "True")
        cls = "solved" if ok else "wrong edit" if patch > 0 else "no edit"
        rows.append(dict(run=Path(d).name, arm=g["arm"], task=g["instance_id"], cls=cls, end=g["end"], secs=secs, long=long, rchars=rchars, calls=calls, decide=first_decide, agent=float(g["agent_s"])))
print(len(rows), "runs from", len({r['run'] for r in rows}), "result dirs")
for cls in ("solved", "wrong edit", "no edit"):
    R = [r for r in rows if r["cls"] == cls]
    if not R: continue
    print(f"{cls:10} n={len(R):3} | ends {dict(collections.Counter(r['end'] for r in R))} | model s {st.median(r['secs'] for r in R):.0f} | calls {st.median(r['calls'] for r in R):.0f} | "
          f"s/call {st.median(r['secs'] / max(1, r['calls']) for r in R):.1f} | replies >= 60 s {st.mean(r['long'] for r in R):.1f} | reasoning chars {st.median(r['rchars'] for r in R):.0f} | "
          f"named a fix before any edit {sum(r['decide'] is not None for r in R)} (median at {st.median([r['decide'] for r in R if r['decide'] is not None] or [0]):.0f} s)")
N = [r for r in rows if r["cls"] == "no edit"]
print("no-edit runs by task:", dict(collections.Counter(r["task"] for r in N).most_common()))

# 'knew where, did not act': for the first edit ATTEMPT (accepted or refused), when were its old_string lines first on screen?
def dec(x):
    try: return str(json.loads(x).get("stdout", x))
    except Exception: return str(x)
gaps = collections.defaultdict(list)
for d in sorted(glob.glob(str(ROOT / "data/results/2026-11-2*_skill_r1[45]*"))):
    try:
        G = {}
        for l in open(f"{d}/results/gen_per_task.jsonl"):
            g = json.loads(l); G[g["instance_id"] + "#a" + g["attempt"]] = g
        by = collections.defaultdict(list)
        for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
            r = json.loads(l); by[r["job"]].append(r)
    except OSError:
        continue
    for job, rs in by.items():
        g = G.get(job)
        if not g or not re.match(r"sk_a2(_60\w*|x\w*|c\w*|o\w*|t\w*)?$", g["arm"]) or "ge" in g["arm"]:
            continue
        rs = sorted(rs, key=lambda r: float(r["t"])); t0 = float(rs[0]["t"])
        res = {}
        for r in rs:
            for m in r["request"]["messages"]:
                if m.get("role") == "tool": res[m.get("tool_call_id")] = (dec(m.get("content")))
        seen = []  # (t, call index, text)
        i = 0; hit = None
        for r in rs:
            for c in ((r.get("reply") or {}).get("message") or {}).get("tool_calls") or []:
                i += 1; fn = c.get("function") or {}
                try: ad = json.loads(fn.get("arguments") or "")
                except Exception: ad = {}
                if not isinstance(ad, dict): ad = {}
                if fn.get("name") == "edit_file" and ".git/agent" not in str(ad.get("filepath", "")):
                    lines = [l.strip() for l in str(ad.get("old_string", "")).split("\n") if len(l.strip()) >= 12]
                    if lines:
                        for (ts, ci, txt) in seen:
                            if lines[0] in txt:
                                hit = (float(r["t"]) - t0 - ts, i - ci); break
                        if hit is None: hit = ("never", 0)
                    break
                seen.append((float(r["t"]) - t0, i, res.get(c.get("id"), "")))
            if hit: break
        patch = int(g.get("patch_chars") or 0); ok = g.get("resolved") in (True, "True")
        cls = "solved" if ok else "wrong edit" if patch > 0 else "no edit"
        if hit and hit[0] != "never": gaps[cls].append(hit)
        elif hit: gaps[cls + " (lines never shown)"].append(hit)
        else: gaps[cls + " (no edit attempt)"].append((0, 0))
print("\nfirst edit attempt vs when its lines were first on screen (median seconds / calls between):")
for k, v in sorted(gaps.items()):
    if v and isinstance(v[0][0], float):
        s = sorted(x[0] for x in v); n = sorted(x[1] for x in v)
        print(f"  {k:30} n={len(v):3} | gap s median {st.median(s):.0f}, p75 {s[int(.75 * len(s))]:.0f} | calls between median {st.median(n):.0f} | gap >= 120 s: {sum(x >= 120 for x in s)}")
    else:
        print(f"  {k:30} n={len(v):3}")

# what fills the gap between 'edit lines first on screen' and the first edit attempt (all classes with an attempt)
fill = collections.defaultdict(collections.Counter); secs_fill = collections.defaultdict(collections.Counter)
for d in sorted(glob.glob(str(ROOT / "data/results/2026-11-2*_skill_r1[45]*"))):
    try:
        G = {}
        for l in open(f"{d}/results/gen_per_task.jsonl"):
            g = json.loads(l); G[g["instance_id"] + "#a" + g["attempt"]] = g
        by = collections.defaultdict(list)
        for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
            r = json.loads(l); by[r["job"]].append(r)
    except OSError:
        continue
    for job, rs in by.items():
        g = G.get(job)
        if not g or not re.match(r"sk_a2(_60\w*|x\w*|c\w*|o\w*|t\w*)?$", g["arm"]) or "ge" in g["arm"]:
            continue
        rs = sorted(rs, key=lambda r: float(r["t"]))
        res = {}
        for r in rs:
            for m in r["request"]["messages"]:
                if m.get("role") == "tool": res[m.get("tool_call_id")] = dec(m.get("content"))
        calls = []
        for r in rs:
            for c in ((r.get("reply") or {}).get("message") or {}).get("tool_calls") or []:
                calls.append((r, c))
        ei = None
        for j, (r, c) in enumerate(calls):
            fn = c.get("function") or {}
            try: ad = json.loads(fn.get("arguments") or "")
            except Exception: ad = {}
            if isinstance(ad, dict) and fn.get("name") == "edit_file" and ".git/agent" not in str(ad.get("filepath", "")):
                lines = [l.strip() for l in str(ad.get("old_string", "")).split("\n") if len(l.strip()) >= 12]
                if lines:
                    first = next((k for k in range(j) if lines[0] in res.get(calls[k][1].get("id"), "")), None)
                    if first is not None: ei = (first, j)
                break
        if not ei: continue
        patch = int(g.get("patch_chars") or 0); ok = g.get("resolved") in (True, "True")
        cls = "solved" if ok else "wrong edit" if patch > 0 else "no edit"
        for k in range(ei[0] + 1, ei[1]):
            r, c = calls[k]; fn = c.get("function") or {}
            try: ad = json.loads(fn.get("arguments") or "")
            except Exception: ad = {}
            cmd = str(ad.get("command", "")) if isinstance(ad, dict) else ""
            kind = ("a.py " + cmd.split("a.py", 1)[1].split()[0]) if "a.py" in cmd else "script/test" if ("python" in cmd or "pytest" in cmd or fn.get("name") == "write_file") else fn.get("name") if fn.get("name") != "run_command" else "shell"
            fill[cls][kind] += 1; secs_fill[cls][kind] += float(r.get("seconds") or 0)
print("\ncalls in the gap (lines on screen -> first edit attempt), and model seconds of the replies that chose them:")
for cls in ("solved", "wrong edit", "no edit"):
    print(f"  {cls:10}", dict(fill[cls].most_common(6)), "| seconds", {k: round(v) for k, v in secs_fill[cls].most_common(6)})
