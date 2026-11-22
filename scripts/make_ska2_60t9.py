"""sk_a2_60t9 = sk_a2_60 with max_time_minutes 9 and max_tool_calls 32; prompt and a.py banners unchanged (they still say 8 minutes / 28 calls),
so behaviour before 480 s / call 28 is sk_a2_60's and only runs that hit a cap get more room (docs/PLAN.md 'WHAT CAN STILL ADD SOLVES TO
sk_a2_60'). Note: the harness's task message states the real budget (32 calls, 9 min), as it did for sk_a2_32. User 2026-11-23: 'yes build it
with 9 minutes'. Run: python3 -I scripts/make_ska2_60t9.py"""
import shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
s, o = ROOT / "submissions/sk_a2_60", ROOT / "submissions/sk_a2_60t9"


def sub(t, a, b):
    assert t.count(a) == 1, a
    return t.replace(a, b)


if o.exists():
    shutil.rmtree(o)
shutil.copytree(s, o)
e = (s / "eval_config.yaml").read_text()
e = sub(sub(e, "max_time_minutes: 8", "max_time_minutes: 9"), "max_tool_calls: 28", "max_tool_calls: 32")
(o / "eval_config.yaml").write_text(e)
y = (s / "agent.yaml").read_text()
(o / "agent.yaml").write_text("# sk_a2_60t9 (2026-11-23): sk_a2_60 + 9 min / 32 calls, prompt unchanged (scripts/make_ska2_60t9.py). " + y.lstrip("# "))
print("wrote", o.relative_to(ROOT))
