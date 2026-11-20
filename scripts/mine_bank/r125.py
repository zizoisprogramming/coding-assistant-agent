"""r125: sb1hl vs sb1hlt (the edit runs the matching existing test file before and after) on 4 tasks, 2 passes (docs/PLAN.md
RUN BUILT r125, bars set there). Run: python3 -I scripts/mine_bank/r125.py
1. the r123-style per-arm table (scripts/mine_bank/r123.py on the r125 folders);
2. sb1hlt's test lines: applied edits followed by a '== EXISTING TESTS ... none fail' / '== THIS EDIT MAKES EXISTING TESTS FAIL'
   line or nothing; every red result printed with the next reply's words and the next edit, and whether a later test line in
   the run is green (hand reading)."""
import ast, collections, glob, json, re, runpy, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
src = (ROOT / "scripts/mine_bank/r123.py").read_text().replace("_skill_r123_p*", "_skill_r125_p*").replace('ARMS = ("sb1h", "sb1hl")', 'ARMS = ("sb1hl", "sb1hlt")')
exec(compile(src, "r123_on_r125", "exec"), {"__name__": "__main__", "__file__": str(ROOT / "scripts/mine_bank/r123.py")})

OK, BAD = "== EXISTING TESTS in ", "== THIS EDIT MAKES EXISTING TESTS FAIL in "
DIRS = sorted(glob.glob(str(ROOT / "data/results/2026-11-2*_skill_r125_p*")))
R = collections.defaultdict(list)
for d in DIRS:
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        r = json.loads(l)
        if "#asb1hlt." in r["job"] and len(r["request"]["messages"]) > 1:
            R[(Path(d).name[-2:], r["job"].split("#")[0])].append(r)
print("\n#### sb1hlt test lines after applied edits")
c = collections.Counter()
for (p, iid), rs in sorted(R.items()):
    rs.sort(key=lambda r: float(r["t"]))
    seq = []
    for i, r in enumerate(rs):
        last = r["request"]["messages"][-1]
        t = str(last.get("content")).replace("\\n", "\n") if last.get("role") == "tool" else ""
        if re.search(r"(?m)^EDITED ", t):
            kind = "red" if BAD in t else "green" if OK in t else "no test line"
            c[kind] += 1
            seq.append(kind)
            if kind == "red":
                try:
                    m = ast.literal_eval(str(r["reply"])).get("message") or {}
                except Exception:
                    m = {}
                words = ((m.get("reasoning_content") or "") + " " + (m.get("content") or "")).strip()
                nxt = [str(x["function"]["arguments"])[:400] for x in m.get("tool_calls") or []]
                print(f"\n  ## {p} {iid} RED")
                print("  OUTPUT:\n" + "\n".join("    " + l for l in t[t.find(BAD):][:1200].splitlines()))
                print("  NEXT REPLY WORDS:\n" + "\n".join("    " + l for l in words[:900].splitlines()))
                print("  NEXT CALLS:", nxt)
    print(f"  {p} {iid[:30]:30} applied edits -> {seq}")
print(f"\n  applied edits {sum(c.values())}: {dict(c)} | with a test line {100 * (c['red'] + c['green']) / max(sum(c.values()), 1):.0f}%")
