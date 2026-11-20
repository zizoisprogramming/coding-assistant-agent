"""sc1 = the combined agent (user 2026-11-21: 'go' on combining sk_a2 with the other agents' proven parts; docs/PLAN.md SC1 DESIGN).
sb1hl's way of working and heredoc edits + sk_a2's reading tool a.py (one install skill call, MEMORY, ALREADY SHOWN, NO EDIT YET / STOP
READING banners; tracked-file edits only, no clock numbers) + evidc's search folded into the install call + the backslash and line-number
fallbacks in the edit step. Tools: run_command, read_file (declared, as sk_a2), get_status, submit_patch + skill 'agent'. Sampling = sb1hl's
(thinking 4096); max_tool_calls 29 (28 + the install call, as evidc). Run: python3 -I scripts/make_sc1.py"""
import importlib.util
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/agent_sc1"))
import capture as C  # noqa: E402
import make_prompt as MP  # noqa: E402
import parts as P  # noqa: E402

sp = importlib.util.spec_from_file_location("make_sbab", ROOT / "scripts/make_sbab.py")
B = importlib.util.module_from_spec(sp)
sp.loader.exec_module(B)
M = B.M
SUB = ROOT / "submissions"


def check(s):
    M.check(s)
    M.examples(s)
    assert "edit_file" not in s and "write_file" not in s and "old_string" not in s
    blocks = re.findall(r"command:\n```\n(.*?)```", s, re.S)
    for b in blocks:
        assert '"' not in b and "`" not in b and "\\" not in b, b[:80]
    edits = [b for b in blocks if "OLD_TEXT" in b]
    assert edits == [C.edit_cmd("pkg/reader.py", C.OLD, C.NEW)], "the one edit command, byte for byte"
    show = re.findall(r"show pkg/reader.py Reader.read\n```\nIt printed:\n```\n(.*?)```", s, re.S)[0]
    plain = re.sub(r"(?m)^ *[0-9]+[|] ", "", show)
    assert C.OLD in plain, "old text = the show output without the number column"
    assert P.NO_EDIT in s and P.STOP in s, "the full banners in examples 5 / 6"
    for t in ("NO EDIT YET", "STOP READING", "ALREADY SHOWN", P.NUMBERS, "double backslashes in your text read as single ones", "old text found 0 times",
              "unexpected EOF while looking for matching", "Tool call budget exhausted"):
        assert s.count(t) >= 2, ("a WHEN line and an example for", t)
    assert "8 minutes" not in s and "of the" + " 8" not in s


def build():
    o = C.capture_all(tempfile.mkdtemp())
    s = MP.prompt(o)
    check(s)
    (ROOT / "scripts/agent_sc1/system.md").write_text(s)
    out = SUB / "sc1"
    if out.exists():
        shutil.rmtree(out)
    (out / "prompts").mkdir(parents=True)
    (out / "configs").mkdir()
    sk = out / "skills/agent/scripts"
    sk.mkdir(parents=True)
    shutil.copy(SUB / "sb1hl/configs/sampling.yaml", out / "configs/sampling.yaml")
    ev = (SUB / "sb1hl/eval_config.yaml").read_text()
    assert ev.count("max_tool_calls: 28") == 1
    (out / "eval_config.yaml").write_text(ev.replace("max_tool_calls: 28", "max_tool_calls: 29"))
    (out / "prompts/system.md").write_text(s)
    (out / "skills/agent/SKILL.md").write_text(P.SKILL_MD)
    (sk / "a.py").write_text(P.a_py()); (sk / "where.py").write_text(P.where_py()); (sk / "install.py").write_text(P.install_py())
    shutil.copy(P.SKA2 / "commands.txt", sk / "commands.txt")
    rest = (SUB / "sb1hl/agent.yaml").read_text().split("\n", 1)[1]
    assert rest.count("generate_content_config") == 1
    rest = rest.replace("generate_content_config", "skills:\n  - skills/agent\ngenerate_content_config")
    (out / "agent.yaml").write_text("# sc1 (2026-11-21): sb1hl + sk_a2's reading tool (one install call, MEMORY, NO EDIT YET / STOP READING) + evidc's search in the install call + backslash / line-number edit fallbacks (scripts/make_sc1.py)\n" + rest)
    print("wrote", out.relative_to(ROOT), "| prompt", len(s), "chars |", sorted(str(p.relative_to(out)) for p in out.rglob("*") if p.is_file()))


if __name__ == "__main__":
    build()
