"""sk_a2v32 = sk_a2v with max_tool_calls 32 (prompt still says 28, as sk_a2_32: a 4-call cushion for the repro calls; r141: 2 sk_a2v
edits refused at calls 29-30 with minutes left) and command timeout 60 s (HUNG COMMANDS 2026-11-22: calls over 60 s are almost only
hangs). sk_a2_60 = sk_a2 with only the 60 s command timeout = the control (the notebook needs one command timeout for all arms).
User 2026-11-22: 'yes build sk_a2v32 with the 60s timeout'. Run: python3 -I scripts/make_ska2v32.py"""
import shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def sub(t, a, b):
    assert t.count(a) == 1, a
    return t.replace(a, b)


def make(src, out, calls, note):
    s, o = ROOT / "submissions" / src, ROOT / "submissions" / out
    if o.exists():
        shutil.rmtree(o)
    shutil.copytree(s, o)
    e = (s / "eval_config.yaml").read_text()
    e = sub(e, "timeout_seconds: 240", "timeout_seconds: 60")
    if calls:
        e = sub(e, "max_tool_calls: 28", f"max_tool_calls: {calls}")
    (o / "eval_config.yaml").write_text(e)
    y = (s / "agent.yaml").read_text()
    (o / "agent.yaml").write_text(f"# {out} (2026-11-23): {note} (scripts/make_ska2v32.py). " + y.lstrip("# "))
    print("wrote", o.relative_to(ROOT))


make("sk_a2v", "sk_a2v32", 32, "sk_a2v + 32 tool calls (prompt still says 28) + 60 s command timeout")
make("sk_a2", "sk_a2_60", None, "sk_a2 + 60 s command timeout only (control)")
