"""sb1hl = sb1h-lite (user 2026-11-20 'yes please'; docs/PLAN.md PROMPT USE CHECK): sb1h with its prompt rewritten
(scripts/agent_sb1hl/system.md from scripts/agent_sb1hl/make_prompt.py) without the parts used in 0-1 of 94 runs and with
the missing fence-error event; tools / sampling / eval_config byte for byte sb1h's. Run: python3 -I scripts/make_sb1hl.py"""
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("make_sbab", ROOT / "scripts/make_sbab.py")
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
H, M = B.H, B.M


def build():
    s = (ROOT / "scripts/agent_sb1hl/system.md").read_text()
    M.check(s)
    M.examples(s)
    assert "edit_file" not in s and "write_file" not in s and "old_string" not in s
    blocks = re.findall(r"command:\n```\n(.*?)```", s, re.S)
    edits = [b for b in blocks if "OLD_TEXT" in b]
    assert len(edits) == 2, len(edits)
    for b in blocks:
        assert '"' not in b and "`" not in b and "\\" not in b, b[:80]
    for b in edits:
        m = re.fullmatch(r"mkdir -p \.git/agent\ncat > \.git/agent/old <<'OLD_TEXT'\n(.*?)OLD_TEXT\ncat > \.git/agent/new <<'NEW_TEXT'\n(.*?)NEW_TEXT\n(python3 - (\S+) <<'EOF'\n.*)", b, re.S)
        assert m, b[:120]
        old, new, step, path = m.groups()
        assert step == H.PY_STEP.replace("PATH", path), "sb1h's Python step byte for byte"
        assert old != new and old.endswith("\n") and new.endswith("\n")
        reads = re.findall(r"printed:\n```\n(.*?)```", s[:s.index(b)], re.S)
        assert reads and old in reads[-1], "old text copied from the read_file output just before it"
    for case in ("old text found 0 times", "unexpected EOF while looking for matching", "Tool call budget exhausted"):
        assert s.count(case) >= 2, case  # the event line + its example
    for gone in ("found 2 times", "mandatory input parameters", "git log", "git show", "cat > pkg/formats.py"):
        assert gone not in s, gone
    sb = (ROOT / "submissions/sb1h/prompts/system.md").read_text()
    assert len(s) < 0.9 * len(sb), (len(s), len(sb))
    B.build_one("sb1hl", s, [], "# sb1hl (2026-11-20): sb1h-lite: sb1h with the prompt parts used in 0-1 of 94 runs dropped and the fence-error event added (scripts/make_sb1hl.py)")


if __name__ == "__main__":
    build()
