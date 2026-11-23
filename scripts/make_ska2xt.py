"""sk_a2xt = sk_a2_60x with timeout_seconds 240 (r148; user 2026-11-23: 'build it, all 4 arms on the 14 tasks'). Everything else
byte for byte. (sk_a2x2t = sk_a2_60x2 at 240 already exists, scripts/make_ska2x2_pin.py.) Run: python3 -I scripts/make_ska2xt.py"""
import shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
s, o = ROOT / "submissions/sk_a2_60x", ROOT / "submissions/sk_a2xt"
EV = "evaluation:\n  timeout_seconds: {t}\n  max_tool_calls: 28\n  max_time_minutes: 8\n  max_turns: 80\n"
assert (s / "eval_config.yaml").read_text() == EV.format(t=60)
if o.exists():
    shutil.rmtree(o)
shutil.copytree(s, o)
(o / "eval_config.yaml").write_text(EV.format(t=240))
y = (s / "agent.yaml").read_text()
assert y.startswith("# sk_a2_60x (2026-11-23)")
(o / "agent.yaml").write_text("# sk_a2xt (2026-11-23): sk_a2_60x with timeout_seconds 240 (scripts/make_ska2xt.py). " + y.lstrip("# "))
print("wrote", o.relative_to(ROOT))
