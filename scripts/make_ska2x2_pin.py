"""r147 arms (user 2026-11-23: 'build it, all three arms with 240 timeout'; docs/PLAN.md 'IDEAS FROM THE BEST PUBLIC AGENTS 2026-11-23'):
  sk_a2x2t   = sk_a2_60x2 with timeout_seconds 240 (CONTROL; the grader's hidden-test run uses the same timeout, verification.py:502)
  sk_a2x2p   = sk_a2x2t + the issue pinned at the end of the system prompt ({problem_description} / {hints?}, ADK instruction
               templating; the harness sets them in session state, agent_runner.py:393), so compaction cannot remove it; prompt
               scripts/agent_ska2x2p/system.md (written in full: contract + edit + check lines point to the pinned issue)
  sk_a2x2p40 = sk_a2x2p with max_tool_calls 40 (same 8 minutes; prompt scripts/agent_ska2x2p40/system.md says 40)
a.py, tools, sampling = sk_a2_60x2 byte for byte. Run: python3 -I scripts/make_ska2x2_pin.py"""
import shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "submissions/sk_a2_60x2"
EV = "evaluation:\n  timeout_seconds: {t}\n  max_tool_calls: {c}\n  max_time_minutes: 8\n  max_turns: 80\n"
ARMS = {
    "sk_a2x2t": (None, 240, 28, "sk_a2_60x2 with timeout_seconds 240 (control)"),
    "sk_a2x2p": ("scripts/agent_ska2x2p/system.md", 240, 28, "sk_a2x2t + the issue pinned at the end of the system prompt"),
    "sk_a2x2p40": ("scripts/agent_ska2x2p40/system.md", 240, 40, "sk_a2x2p with 40 tool calls"),
}
assert (SRC / "eval_config.yaml").read_text() == EV.format(t=60, c=28)
y0 = (SRC / "agent.yaml").read_text()
assert y0.startswith("# sk_a2_60x2 (2026-11-23)") and "instruction: !include prompts/system.md" in y0
for arm, (prompt, t, c, why) in ARMS.items():
    out = ROOT / "submissions" / arm
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SRC, out)
    (out / "eval_config.yaml").write_text(EV.format(t=t, c=c))
    if prompt:
        p = (ROOT / prompt).read_text()
        assert p.rstrip().endswith("{hints?}") and "{problem_description}" in p and f"You have {c} tool calls" in p
        assert p.count("{") == 2 and p.count("}") == 2, "only the two state variables may use braces"
        (out / "prompts/system.md").write_text(p)
    (out / "agent.yaml").write_text(f"# {arm} (2026-11-23): {why} (scripts/make_ska2x2_pin.py). " + y0.lstrip("# "))
    print("wrote", out.relative_to(ROOT), len((out / "prompts/system.md").read_text().split()), "words", EV.format(t=t, c=c).split("\n")[1:3])
