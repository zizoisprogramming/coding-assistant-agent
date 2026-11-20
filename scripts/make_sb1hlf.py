"""sb1hlf = sb1hl with fence-free worked examples (user 2026-11-20: 'do the fence free in sb1hl'; RESULT r130: fence-free examples ->
0 text-form calls). Prompt scripts/agent_sb1hlf/system.md (scripts/agent_sb1hlf/make_prompt.py); tools / sampling / eval_config byte for
byte sb1hl's. Run: python3 -I scripts/make_sb1hlf.py"""
import importlib.util
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("make_sbab", ROOT / "scripts/make_sbab.py")
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
H, M = B.H, B.M
CMD = re.compile(r"tool: run_command\ncommand:\n(.*?)# end of command\n", re.S)


def build():
    s = (ROOT / "scripts/agent_sb1hlf/system.md").read_text()
    M.check(s)
    M.examples(s)
    assert "command:\n```" not in s, "no fenced command"
    cmds = CMD.findall(s)
    assert len(cmds) == 3, len(cmds)
    for b in cmds:
        assert "```" not in b and '"' not in b and "`" not in b and "\\" not in b, b[:80]
    edits = [b for b in cmds if "OLD_TEXT" in b]
    assert len(edits) == 2
    for b in edits:
        m = re.fullmatch(r"mkdir -p \.git/agent\ncat > \.git/agent/old <<'OLD_TEXT'\n(.*?)OLD_TEXT\ncat > \.git/agent/new <<'NEW_TEXT'\n(.*?)NEW_TEXT\n(python3 - (\S+) <<'EOF'\n.*)", b, re.S)
        assert m and m.group(3) == H.PY_STEP.replace("PATH", m.group(4)), "sb1h's Python step byte for byte"
        reads = re.findall(r"printed:\n```\n(.*?)```", s[:s.index(b)], re.S)
        assert reads and m.group(1) in reads[-1], "old text copied from the read_file output just before it"
    for case in ("old text found 0 times", "unexpected EOF while looking for matching", "Tool call budget exhausted"):
        assert s.count(case) >= 2, case
    # the same prompt as sb1hl apart from the call format: strip both formats and compare
    base = (ROOT / "scripts/agent_sb1hl/system.md").read_text()
    norm = lambda t: re.sub(r"\n(```|# end of command)\n", "\n", re.sub(r"- \"unexpected EOF.*?\n|Example 4 - .*?\n|Each call is shown.*?\n", "", t))
    assert norm(s).replace("```\n", "") == norm(base).replace("```\n", ""), "only the call format differs from sb1hl"
    out = ROOT / "submissions/sb1hlf"
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(ROOT / "submissions/sb1hl", out)
    (out / "prompts/system.md").write_text(s)
    rest = (ROOT / "submissions/sb1hl/agent.yaml").read_text().split("\n", 1)[1]
    (out / "agent.yaml").write_text("# sb1hlf (2026-11-20): sb1hl with fence-free worked examples (scripts/make_sb1hlf.py)\n" + rest)
    print("wrote", out.relative_to(ROOT), "| chars", len(s))


if __name__ == "__main__":
    build()
