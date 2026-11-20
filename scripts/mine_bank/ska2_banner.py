"""Did sk_a2-family agents obey a.py's NO EDIT YET / STOP READING banners? Over every logged run whose tool outputs carry an a.py banner:
the share of reads through a.py vs read_file / cat, and for the FIRST banner of each kind: an edit (edit_file / write_file to a source
.py / python heredoc replace / OLD_TEXT) within the next 2 calls, the run's outcome. Run: python3 -I scripts/mine_bank/ska2_banner.py"""
import ast, collections, glob, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCR = re.compile(r"(repro|reproduce|check|debug|scratch|\.git/agent)")
def is_edit(n, a):
    if n in ("edit_file", "write_file"):
        fp = a.get("filepath", "") or a.get("path", "")
        return fp.endswith(".py") and not SCR.search(fp) and "test" not in fp
    c = a.get("command", "") if isinstance(a, dict) else ""
    return "OLD_TEXT" in c or bool(re.search(r"\.replace\(|sed -i|git apply", c)) and "a.py" not in c
S = collections.defaultdict(lambda: collections.Counter())
for f in glob.glob(str(ROOT / "data/results/*/requests/requests.jsonl")):
    gp = Path(f).parent.parent / "results/gen_per_task.jsonl"
    if not gp.exists(): continue
    G = {}
    for l in open(gp):
        try: g = json.loads(l); G[g["instance_id"] + "#a" + g.get("attempt", "")] = g
        except Exception: pass
    by = collections.defaultdict(list)
    for l in open(f, errors="replace"):
        if "a.py" not in l: continue
        try: r = json.loads(l)
        except Exception: continue
        if "job" in r and len(r["request"]["messages"]) > 1: by[r["job"]].append(r)
    for job, rs in by.items():
        g = G.get(job)
        if not g: continue
        arm = g.get("arm"); rs.sort(key=lambda r: float(r["t"]))
        calls = []; seen = {}
        for r in rs:
            out = str(r["request"]["messages"][-1].get("content"))
            for k in ("NO EDIT YET", "STOP READING"):
                if k in out and k not in seen: seen[k] = len(calls)
            try: m = ast.literal_eval(str(r["reply"])).get("message") or {}
            except Exception: continue
            for c in m.get("tool_calls") or []:
                try: a = json.loads(c["function"]["arguments"])
                except Exception: a = {}
                cmd = a.get("command", "")
                calls.append("EDIT" if is_edit(c["function"]["name"], a) else "apy" if "a.py" in cmd else "read_file" if c["function"]["name"] == "read_file" else "rawread" if re.search(r"(^|\s)(cat|sed -n|head|tail|grep)\b", cmd) else "other")
        if not any(x == "apy" for x in calls): continue
        s = S[arm]; s["runs"] += 1; s["solved"] += g.get("resolved") in (True, "True")
        s["a.py reads"] += calls.count("apy"); s["read_file"] += calls.count("read_file"); s["raw reads"] += calls.count("rawread")
        for k, i in seen.items():
            s[k + " seen"] += 1
            s[k + " -> edit within 2 calls"] += "EDIT" in calls[i:i + 2]
            s[k + " -> edited at all after"] += "EDIT" in calls[i:]
for arm, s in sorted(S.items(), key=lambda x: -x[1]["runs"]):
    if s["runs"] >= 10:
        print(f"  {arm:14} " + " | ".join(f"{k} {v}" for k, v in s.items()))
