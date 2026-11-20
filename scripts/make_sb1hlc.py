"""sb1hlc = sb1hl + max_tool_calls 36 (was 28) + a WHEN line / worked example for the harness note 'Finalize your edits and call submit_patch
soon' when nothing is edited (user 2026-11-20: 'yes raise the tool calls with the example as well'; docs/PLAN.md WHY sb1hl RUNS OUT: 39% of
sb1h-family runs end at the 28-call cap with time left; the harness note starts at <= 10 calls left; 36 calls -> projected mean ~390 s).
Prompt scripts/agent_sb1hlc/system.md (scripts/agent_sb1hlc/make_prompt.py). Run: python3 -I scripts/make_sb1hlc.py"""
import importlib.util
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("make_sbab", ROOT / "scripts/make_sbab.py")
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
H, M = B.H, B.M
NOTE = "Finalize your edits and call submit_patch soon"


def build():
    s = (ROOT / "scripts/agent_sb1hlc/system.md").read_text()
    base = (ROOT / "scripts/agent_sb1hl/system.md").read_text()
    M.check(s)
    M.examples(s)
    assert s.count(NOTE) == 2, "the WHEN line + example 6"
    added = [l for l in s.splitlines() if l not in base.splitlines()]
    assert len(added) == 2 and all(NOTE in l for l in added), added
    assert [l for l in base.splitlines() if l not in s.splitlines()] == [], "nothing of sb1hl removed"
    out = ROOT / "submissions/sb1hlc"
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(ROOT / "submissions/sb1hl", out)
    (out / "prompts/system.md").write_text(s)
    ev = (out / "eval_config.yaml").read_text()
    assert ev.count("max_tool_calls: 28") == 1
    (out / "eval_config.yaml").write_text(ev.replace("max_tool_calls: 28", "max_tool_calls: 36"))
    rest = (ROOT / "submissions/sb1hl/agent.yaml").read_text().split("\n", 1)[1]
    (out / "agent.yaml").write_text("# sb1hlc (2026-11-20): sb1hl + 36 tool calls + the 'Finalize your edits' note as an event (scripts/make_sb1hlc.py)\n" + rest)
    print("wrote", out.relative_to(ROOT), "| chars", len(s), "|", (out / "eval_config.yaml").read_text().replace("\n", " "))


if __name__ == "__main__":
    build()
