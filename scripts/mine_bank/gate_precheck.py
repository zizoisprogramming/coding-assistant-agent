"""Pre-check for sk_a2p2g's late gate (user 2026-11-24 'build it, all three arms on the 4 tasks'): over r144-r156 sk_a2-family runs,
where were the lines of the first edit attempt first on screen relative to the first STOP READING? A gate that refuses NEW code
after STOP READING blocks runs whose edit lines first appear after it (that harm), and (for runs with STOP and a later edit) shows
whether the edit lines were already read before STOP (the gate's candidates could hold them).
Run: python3 -I scripts/mine_bank/gate_precheck.py"""
import collections, glob, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]


def dec(x):
    try: return str(json.loads(x).get("stdout", x))
    except Exception: return str(x)


c = collections.Counter()
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
        if not g or not re.match(r"sk_a2(_60\w*|x\w*|c\w*|o\w*|t\w*|p\w*)?$", g["arm"]) or "ge" in g["arm"]:
            continue
        rs = sorted(rs, key=lambda r: float(r["t"]))
        res = {}
        for r in rs:
            for m in r["request"]["messages"]:
                if m.get("role") == "tool": res[m.get("tool_call_id")] = dec(m.get("content"))
        calls = [c2 for r in rs for c2 in ((r.get("reply") or {}).get("message") or {}).get("tool_calls") or []]
        outs = [res.get(c2.get("id"), "") for c2 in calls]
        stop = next((k for k, o in enumerate(outs) if "STOP READING" in o), None)
        ok = g.get("resolved") in (True, "True"); patch = int(g.get("patch_chars") or 0)
        cls = "solved" if ok else "wrong edit" if patch > 0 else "no edit"
        c[(cls, "runs")] += 1
        if stop is None:
            continue
        c[(cls, "STOP fired")] += 1
        e = None
        for j, c2 in enumerate(calls):
            fn = c2.get("function") or {}
            try: ad = json.loads(fn.get("arguments") or "")
            except Exception: ad = {}
            if isinstance(ad, dict) and fn.get("name") == "edit_file" and ".git/agent" not in str(ad.get("filepath", "")):
                lines = [l.strip() for l in str(ad.get("old_string", "")).split("\n") if len(l.strip()) >= 12]
                if lines: e = (j, next((k for k in range(j) if lines[0] in outs[k]), None))
                break
        if e is None:
            c[(cls, "no edit attempt after STOP")] += 1
        elif e[0] <= stop:
            c[(cls, "edit at / before STOP")] += 1
        elif e[1] is None:
            c[(cls, "edit after STOP, lines never shown")] += 1
        elif e[1] <= stop:
            c[(cls, "edit after STOP, lines read BEFORE STOP (gate keeps them)")] += 1
        else:
            c[(cls, "edit after STOP, lines first read AFTER STOP (gate would block)")] += 1
for cls in ("solved", "wrong edit", "no edit"):
    print(cls, {k[1]: v for k, v in c.items() if k[0] == cls})
