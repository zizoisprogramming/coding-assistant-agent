"""sbE7 (user 2026-11-20: 'yes' to reopening the E tier with one arm): one agent = sb1hl's exploring (search, tests, read) + the expectation
written with write_file after reading the code + the fixed check command (sbE6's CHECK6: shown / not the issue's case / broken / missing /
still / passes with your edit / late) + sbE3's hold-back and the backslash fallback in the edit step; tools sb1hl's + write_file;
fence-free calls. Prompt scripts/agent_expect/make_prompts_e7.py. Run: python3 -I scripts/make_expect_e7.py"""
import importlib.util
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sp = importlib.util.spec_from_file_location("make_expect_e6", ROOT / "scripts/make_expect_e6.py")
X6 = importlib.util.module_from_spec(sp)
sp.loader.exec_module(X6)
M, SUB, X = X6.M, X6.SUB, X6.X
sys.path.insert(0, str(ROOT / "scripts/agent_expect"))
import make_prompts as P  # noqa: E402
import make_prompts_e7 as P7  # noqa: E402

CMD = re.compile(r"tool: run_command\ncommand:\n(.*?)# end of command\n", re.S)
WF = re.compile(r"tool: write_file\nfilepath: (\S+)\ncontent:\n(.*?)# end of content\n", re.S)


def check(s):
    M.check(s)
    M.examples(s)
    assert "command:\n```" not in s and "edit_file" not in s
    cmds = CMD.findall(s)
    for b in cmds:
        assert "```" not in b and '"' not in b and "`" not in b and "\\" not in b, b[:80]
    assert not [b for b in cmds if "<<'EXPECT'" in b], "no heredoc expectation: the model's code goes through write_file"
    assert WF.findall(s) == [(".git/agent/expect.py", P.E3_EXP)]
    ex1 = s[s.index("Example 1 -"):s.index("Example 2 -")]
    assert CMD.findall(ex1) == [P.E3_SEARCH, X.CHECK_CMD], "example 1: search, (read), write_file, the check command byte for byte"
    assert ex1.index("read_file on pkg/reader.py") < ex1.index("tool: write_file") < ex1.index(X.CHECK_CMD), "the expectation comes after the read"
    edits = [b for b in cmds if "OLD_TEXT" in b]
    assert len(edits) == 1
    m = re.fullmatch(r"mkdir -p \.git/agent\ncat > \.git/agent/old <<'OLD_TEXT'\n(.*?)OLD_TEXT\ncat > \.git/agent/new <<'NEW_TEXT'\n(.*?)NEW_TEXT\n(python3 - (\S+) <<'EOF'\n.*)", edits[0], re.S)
    assert m and m.group(3) == X.EDIT_STEP.replace("PATH", m.group(4)) and m.group(1) in P.E3_READ
    outs = "\n".join(re.findall(r"printed:\n```\n(.*?)```", s, re.S)) + "\n".join(re.findall(r"printed:\n```\n(.*?)```", s, re.S))
    allouts = "\n".join(re.findall(r"```\n(.*?)```", s, re.S))
    for k, v in X.EV3.items():
        assert v in allouts, ("an example output for", k)
        assert '"' + v.split(":")[0] + '"' in s, ("a WHEN line for", k)
    assert X.HALVED in allouts and X.NOFILE in allouts
    nums = [int(x) for x in re.findall(r"^Example (\d+) -", s, re.M)]
    assert nums == list(range(1, len(nums) + 1)), nums
    assert all(l.startswith("test $e = 0 && test $t -gt 0") for l in s.splitlines() if "300" in l)


def build():
    s = P7.solver(X)
    check(s)
    (ROOT / "scripts/agent_expect/sbE7.md").write_text(s)
    out = SUB / "sbE7"
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SUB / "sb1hl", out)
    (out / "prompts/system.md").write_text(s)
    rest = (SUB / "sb1hl/agent.yaml").read_text().split("\n", 1)[1]
    assert rest.count("  - read_file\n") == 1
    rest = rest.replace("  - read_file\n", "  - read_file\n  - write_file\n")
    (out / "agent.yaml").write_text("# sbE7 (2026-11-20): sb1hl's exploring + the expectation by write_file after reading + the fixed check; hold-back, backslash fallback (scripts/make_expect_e7.py)\n" + rest)
    print("wrote", out.relative_to(ROOT), "| chars", len(s), "| tools", re.findall(r"  - (\w+)", rest))


if __name__ == "__main__":
    build()
