"""Which expectation commands come out as text (unparseable calls or plain code blocks) vs real calls? r127-r129 solver replies that
carry an expectation (cat > .git/agent/expect.py <<'EXPECT'), split by the body's characters (braces, double quotes, f-strings),
its length, the task, and whether the solver had made a real call before. Run: python3 -I scripts/mine_bank/expect_textcall.py"""
import ast, collections, glob, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BODY = re.compile(r"<<'EXPECT'\n(.*?)EXPECT", re.S)
rows = []
for d in sorted(glob.glob(str(ROOT / "data/results/2026-11-20_skill_r12[789]_p*"))):
    by = collections.defaultdict(list)
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        r = json.loads(l)
        if len(r["request"]["messages"]) > 1 and not r["request"]["messages"][0]["content"].startswith(("Your only job", "You write the expectation")):
            by[r["job"]].append(r)
    for job, rs in by.items():
        rs.sort(key=lambda r: float(r["t"]))
        real = 0
        for r in rs:
            m = ast.literal_eval(str(r["reply"])).get("message") or {}
            texts = []
            if m.get("tool_calls"):
                for c in m["tool_calls"]:
                    texts.append(("call", c["function"]["arguments"]))
            else:
                texts.append(("text", m.get("content") or ""))
            for kind, t in texts:
                t2 = t.replace("\\n", "\n").replace('\\"', '"')
                b = BODY.search(t2)
                if b:
                    body = b.group(1)
                    rows.append(dict(kind=kind, iid=job.split("#")[0], first=real == 0, brace="{" in body, dq='"' in body,
                                     fstr=bool(re.search(r"\bf[\"']", body)), n=len(body)))
            real += len(m.get("tool_calls") or [])
def tab(key, label):
    c = collections.Counter((r[key], r["kind"]) for r in rows)
    for v in sorted({r[key] for r in rows}, key=str):
        a, t = c[(v, "call")], c[(v, "text")]
        print(f"  {label}={v!s:14} real calls {a:3} | as text {t:3} ({100 * t / max(1, a + t):.0f}% text)")
print(f"expectation attempts {len(rows)}")
tab("brace", "braces in body"); tab("dq", "double quotes"); tab("fstr", "f-string"); tab("first", "no real call before"); tab("iid", "task")
for lo, hi in ((0, 400), (400, 800), (800, 99999)):
    s = [r for r in rows if lo <= r["n"] < hi]
    print(f"  body {lo}-{hi} chars: {len(s)} attempts, as text {sum(r['kind'] == 'text' for r in s)}")
both = [r for r in rows if r["brace"] and r["dq"]]
print(f"  braces AND double quotes: {len(both)} attempts, as text {sum(r['kind'] == 'text' for r in both)}; neither: "
      f"{sum(not r['brace'] and not r['dq'] for r in rows)} attempts, as text {sum(r['kind'] == 'text' and not r['brace'] and not r['dq'] for r in rows)}")
