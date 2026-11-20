"""How reliable is the harness's write_file tool for writing a script? Over every logged run with write_file in its tools: write_file
calls, how many came back with an error (mandatory input parameters / other), how many replies tried write_file as text, and the
content sizes. Run: python3 -I scripts/mine_bank/write_file_rel.py"""
import ast, collections, glob, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
c = collections.Counter(); sizes = []
for f in sorted(glob.glob(str(ROOT / "data/results/2026-1*/requests/requests.jsonl"))):
    by = collections.defaultdict(list)
    for l in open(f, errors="replace"):
        try:
            r = json.loads(l)
        except Exception:
            continue
        if "job" in r and len(r["request"]["messages"]) > 1:
            by[r["job"]].append(r)
    for job, rs in by.items():
        rs.sort(key=lambda r: float(r["t"]))
        tools = [t.get("function", {}).get("name") for t in rs[0]["request"].get("tools") or []]
        if "write_file" not in tools:
            continue
        c["runs with write_file"] += 1
        for i, r in enumerate(rs):
            try:
                m = ast.literal_eval(str(r["reply"])).get("message") or {}
            except Exception:
                continue
            if not m.get("tool_calls") and re.search(r"call:write_file", m.get("content") or ""):
                c["write_file sent as text"] += 1
            for cl in m.get("tool_calls") or []:
                if cl["function"]["name"] != "write_file":
                    continue
                c["write_file calls"] += 1
                try:
                    a = json.loads(cl["function"]["arguments"]); sizes.append(len(a.get("content", "")))
                except Exception:
                    c["arguments not JSON"] += 1
                if i + 1 < len(rs):
                    out = str(rs[i + 1]["request"]["messages"][-1].get("content"))
                    if "mandatory input parameters" in out:
                        c["error: mandatory input parameters"] += 1
                    elif '"status": "error"' in out or "'status': 'error'" in out:
                        c["error: other"] += 1
                    else:
                        c["ok"] += 1
for k, v in c.most_common(): print(f"  {k}: {v}")
if sizes:
    s = sorted(sizes); print(f"  content chars: median {s[len(s) // 2]}, 90th {s[int(len(s) * 0.9)]}, over 800: {sum(x > 800 for x in s)}")
