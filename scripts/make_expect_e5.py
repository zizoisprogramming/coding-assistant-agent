"""r130 arms (user 2026-11-20: 'do what u proposed + few shot, on 2 tasks only please and yes besides sb1 and sb1hl').
Run: python3 -I scripts/make_expect_e5.py
  sbE5f = sbE3b's mechanism (hold-back, backslash fallback, check.sh events, late line) with fence-free worked examples (each command
          ends with the comment line '# end of command'; r129: 23 of 29 bank text replies end with the copied ``` fence) and a short
          search before the expectation. Few-shot only: the expectation is still one heredoc run_command.
  sbE5w = sbE5f, but the expectation's code goes through the harness's write_file tool (bank: 0.1% sent as text over 4,624 calls vs
          50% for the heredoc expectation, scripts/mine_bank/write_file_rel.py / expect_textcall.py) and a FIXED check command
          (no model code) installs .git/agent/check.sh and runs it. Tools = sb1hl's + write_file.
Prompts: scripts/agent_expect/make_prompts_e5.py. sampling / eval_config = sb1hl's."""
import importlib.util
import re
import shutil
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


XA = load("make_expect_arms", ROOT / "scripts/make_expect_arms.py")
F = load("edit_fallback", ROOT / "scripts/edit_fallback.py")
M, SUB = XA.M, XA.SUB
HALVED = "double backslashes in your text read as single ones"
CHECK_CMD = "mkdir -p .git/agent\ncat > .git/agent/check.sh <<'EOF'\n" + XA.CHECK3 + "EOF\nbash .git/agent/check.sh\n"
X = types.SimpleNamespace(EV3=XA.EV3, EDIT_STEP=F.halve(XA.EDIT_STEP3), RERUN=XA.RERUN, expect_cmd=XA.expect_cmd3, HALVED=HALVED, CHECK_CMD=CHECK_CMD)
for c in (CHECK_CMD, X.EDIT_STEP):
    assert '"' not in c and "`" not in c and "\\" not in c and "{" not in c and "}" not in c
sys.path.insert(0, str(ROOT / "scripts/agent_expect"))
import make_prompts as P  # noqa: E402
import make_prompts_e5 as P5  # noqa: E402

CMD = re.compile(r"tool: run_command\ncommand:\n(.*?)# end of command\n", re.S)
WF = re.compile(r"tool: write_file\nfilepath: (\S+)\ncontent:\n(.*?)# end of content\n", re.S)


def check(s, variant):
    W = variant == "sbE5w"
    M.check(s)
    M.examples(s)
    assert "edit_file" not in s and "old_string" not in s
    cmds = CMD.findall(s)
    assert cmds, "commands found"
    for b in cmds:
        assert "```" not in b and '"' not in b and "`" not in b and "\\" not in b, ("fixed / example command text", b[:80])
    # no fenced call anywhere: every ``` block is an output (preceded by 'printed:') or the read text of example 8
    for m in re.finditer(r"```\n", s):
        pass
    assert "command:\n```" not in s and "content:\n```" not in s
    edits = [b for b in cmds if "OLD_TEXT" in b]
    assert edits
    for b in edits:
        m = re.fullmatch(r"mkdir -p \.git/agent\ncat > \.git/agent/old <<'OLD_TEXT'\n(.*?)OLD_TEXT\ncat > \.git/agent/new <<'NEW_TEXT'\n(.*?)NEW_TEXT\n(python3 - (\S+) <<'EOF'\n.*)", b, re.S)
        assert m and m.group(3) == X.EDIT_STEP.replace("PATH", m.group(4)), "the edit step byte for byte"
        reads = re.findall(r"printed:\n```\n(.*?)```", s[:s.index(b)], re.S)
        assert reads and m.group(1) in reads[-1], "old text copied from the read output just before it"
    ex1 = s[s.index("Example 1 -"):s.index("Example 2 -")]
    c1 = CMD.findall(ex1)
    assert c1[0] == P.E3_SEARCH, "example 1 starts with the short search"
    if W:
        wfs = WF.findall(s)
        assert wfs == [(".git/agent/expect.py", P.E3_EXP)], wfs
        assert c1[1:] == [CHECK_CMD], "example 1: search, write_file, the check command byte for byte"
        assert ex1.index("tool: write_file") < ex1.index(CHECK_CMD)
        assert not [b for b in cmds if "EXPECT\n" in b], "no heredoc expectation in E5w"
        assert P5.NOFILE in s
    else:
        assert c1[1:] == [X.expect_cmd(P.E3_EXP)], "example 1: search, then the heredoc expectation byte for byte"
        assert "write_file" not in s
    outs = "\n".join(re.findall(r"printed:\n```\n(.*?)```", s, re.S))
    for k, v in X.EV3.items():
        assert v in outs, ("an example output for", k)
        assert '"' + v.split(":")[0] + '"' in s, ("a WHEN line for", k)
    assert HALVED in outs and '"' + HALVED + '"' in s
    assert all(l.startswith("test $e = 0 && test $t -gt 0") for l in s.splitlines() if str(XA.LATE_S) in l)
    nums = [int(x) for x in re.findall(r"^Example (\d+) -", s, re.M)]
    assert nums == list(range(1, len(nums) + 1)), nums


def build():
    for v in ("sbE5f", "sbE5w"):
        s = P5.solver(X, v)
        check(s, v)
        (ROOT / f"scripts/agent_expect/{v}.md").write_text(s)
        out = SUB / v
        if out.exists():
            shutil.rmtree(out)
        shutil.copytree(SUB / "sb1hl", out)
        (out / "prompts/system.md").write_text(s)
        rest = (SUB / "sb1hl/agent.yaml").read_text().split("\n", 1)[1]
        if v == "sbE5w":
            assert rest.count("  - read_file\n") == 1
            rest = rest.replace("  - read_file\n", "  - read_file\n  - write_file\n")
            head = "# sbE5w (2026-11-20): sbE5f with the expectation's code written by write_file + a fixed check command (scripts/make_expect_e5.py)"
        else:
            head = "# sbE5f (2026-11-20): sbE3b with fence-free worked examples and a short search first, few-shot only (scripts/make_expect_e5.py)"
        (out / "agent.yaml").write_text(head + "\n" + rest)
        print("wrote", out.relative_to(ROOT), "| chars", len(s), "| tools", re.findall(r"  - (\w+)", rest))


if __name__ == "__main__":
    build()
