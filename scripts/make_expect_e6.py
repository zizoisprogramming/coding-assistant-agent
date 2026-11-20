"""sbE6 (user 2026-11-20: 'on 2 tasks only please and yes build'): SequentialAgent [search -> writer -> solver] so that an expectation
always exists before the solver starts (r127-r130: the 12 expectation-arm runs without one never edited and never solved; they made 47
calls to their own repro scripts). Run: python3 -I scripts/make_expect_e6.py
  search = sbE4A's one-call stage (thinking off, cut-down evidence script) + a restart guard: if .git/agent/expect.py exists the script
           prints EXPECTATION ALREADY WRITTEN and the stage passes it on (output_key evidence);
  writer = write_file only (no read, no search: it cannot explore), sb1hl's sampling; writes .git/agent/expect.py from the issue + the
           search lines, replies 'WROTE .git/agent/expect.py: ...' (output_key expectation); on the guard line: no call, DONE;
  solver = sb1hl's tools (no write_file); first call = the fixed check command (installs check.sh, runs the expectation); rewrites via
           the heredoc expectation command; hold-back, backslash fallback, late line; fence-free examples; a new check event when
           expect.py is missing.
eval_config: 30 calls (28 + search 1 + writer 1)."""
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
E4 = load("make_expect_e4", ROOT / "scripts/make_expect_e4.py")
M, SUB = XA.M, XA.SUB
HALVED = "double backslashes in your text read as single ones"
EV6 = dict(XA.EV3, missing="== NO EXPECTATION FILE: write the expectation with the expectation command (example 2).")
a = "python3 .git/agent/expect.py > .git/agent/expect.out 2>&1 && r=PASSES || r=FAILS\n"
assert XA.CHECK3.count(a) == 1 and XA.CHECK3.count("*) echo '") == 1
CHECK6 = XA.CHECK3.replace(a, a + "test -f .git/agent/expect.py || r=MISSING\n").replace(
    "*) echo '", "MISSING0|MISSING1) echo '" + EV6["missing"] + "';;\n*) echo '")
for v in EV6.values():
    assert "'" not in v
EDIT6 = F.halve(XA.EDIT_STEP3)
CHECK_CMD = "mkdir -p .git/agent\ncat > .git/agent/check.sh <<'EOF'\n" + CHECK6 + "EOF\nbash .git/agent/check.sh\n"


def expect_cmd6(body):
    return ("mkdir -p .git/agent\ncat > .git/agent/expect.py <<'EXPECT'\n" + body + "EXPECT\ncat > .git/agent/check.sh <<'EOF'\n" + CHECK6
            + "EOF\nbash .git/agent/check.sh\n")


for c in (CHECK_CMD, EDIT6, expect_cmd6("x = 1\n")):
    assert '"' not in c and "`" not in c and "\\" not in c and "{" not in c and "}" not in c
def rewrite_cmd(body):  # r131 short version: check.sh was installed by the first call, so a rewrite only replaces expect.py and runs the check
    return "mkdir -p .git/agent\ncat > .git/agent/expect.py <<'EXPECT'\n" + body + "EXPECT\nbash .git/agent/check.sh\n"


NOFILE = "bash: .git/agent/check.sh: No such file or directory\n"
X = types.SimpleNamespace(EV3=EV6, EDIT_STEP=EDIT6, RERUN=XA.RERUN, expect_cmd=expect_cmd6, rewrite_cmd=rewrite_cmd, HALVED=HALVED, CHECK_CMD=CHECK_CMD, NOFILE=NOFILE)
sys.path.insert(0, str(ROOT / "scripts/agent_expect"))
import make_prompts as P  # noqa: E402
import make_prompts_e6 as P6  # noqa: E402

CMD = re.compile(r"tool: run_command\ncommand:\n(.*?)# end of command\n", re.S)
GUARD = ('    ws = workspace()\n',
         '    ws = workspace()\n    if os.path.exists(os.path.join(ws, ".git", "agent", "expect.py")):  # sbE6 restart guard: the writer must not overwrite it\n'
         '        print("' + P6.ALREADY + '")\n        return\n')


def search_script():
    s = E4.search_script()
    assert s.count(GUARD[0]) == 1
    return s.replace(GUARD[0], GUARD[1])


def check_solver(s):
    M.check(s, ("{expectation?}", "{evidence?}"))
    M.examples(s)
    assert "command:\n```" not in s and "write_file" not in s and "edit_file" not in s
    cmds = CMD.findall(s)
    for b in cmds:
        assert "```" not in b and '"' not in b and "`" not in b and "\\" not in b, b[:80]
    ex1 = s[s.index("Example 1 -"):s.index("Example 2 -")]
    assert CMD.findall(ex1) == [CHECK_CMD], "example 1 = the check command byte for byte"
    exps = [b for b in cmds if "<<'EXPECT'" in b]
    assert exps and all(b == rewrite_cmd(re.search(r"<<'EXPECT'\n(.*?)EXPECT\n", b, re.S).group(1)) for b in exps), "the rewrite command byte for byte"
    assert NOFILE in s and len(s) < 13500, len(s)  # r131 short version: 16,091 -> 13,407
    edits = [b for b in cmds if "OLD_TEXT" in b]
    assert edits
    for b in edits:
        m = re.fullmatch(r"mkdir -p \.git/agent\ncat > \.git/agent/old <<'OLD_TEXT'\n(.*?)OLD_TEXT\ncat > \.git/agent/new <<'NEW_TEXT'\n(.*?)NEW_TEXT\n(python3 - (\S+) <<'EOF'\n.*)", b, re.S)
        assert m and m.group(3) == EDIT6.replace("PATH", m.group(4))
        reads = re.findall(r"printed:\n```\n(.*?)```", s[:s.index(b)], re.S)
        assert reads and m.group(1) in reads[-1]
    outs = "\n".join(re.findall(r"printed:\n```\n(.*?)```", s, re.S))
    for k, v in EV6.items():
        assert v in outs, ("an example output for", k)
        assert '"' + v.split(":")[0] + '"' in s, ("a WHEN line for", k)
    assert HALVED in outs
    nums = [int(x) for x in re.findall(r"^Example (\d+) -", s, re.M)]
    assert nums == list(range(1, len(nums) + 1)), nums
    assert all(l.startswith("test $e = 0 && test $t -gt 0") for l in s.splitlines() if str(XA.LATE_S) in l)


def check_writer(s):
    M.check(s, ("{evidence?}", "{problem_description}"))
    wf = re.findall(r"tool: write_file\nfilepath: (\S+)\ncontent:\n(.*?)# end of content\n", s, re.S)
    assert wf == [(".git/agent/expect.py", P.E3_EXP)]
    assert "run_command" not in s and "read_file" not in s and P6.ALREADY in s and "\nDONE\n" in s
    assert s.startswith("Your only job is to write the expectation")


def check_search(s):
    M.check(s, ("{problem_description}",))
    assert s.startswith("Your only job is one search of the repository") and s.count(P6.ALREADY) == 2 and "If the result begins with EXPECTATION ALREADY WRITTEN" in s


def build():
    so, wr, se = P6.solver(X), P6.writer(), P6.search()
    check_solver(so); check_writer(wr); check_search(se)
    for name, t in (("sbE6_solver", so), ("sbE6_writer", wr), ("sbE6_search", se)):
        (ROOT / f"scripts/agent_expect/{name}.md").write_text(t)
    out = SUB / "sbE6"
    if out.exists():
        shutil.rmtree(out)
    (out / "prompts").mkdir(parents=True)
    (out / "configs").mkdir()
    (out / "skills/evidence/scripts").mkdir(parents=True)
    shutil.copy(SUB / "sb1hl/configs/sampling.yaml", out / "configs/sampling.yaml")
    (out / "configs/search_sampling.yaml").write_text(E4.PLUS_SAMPLING)
    ev = (SUB / "sb1hl/eval_config.yaml").read_text()
    assert ev.count("max_tool_calls: 28") == 1
    (out / "eval_config.yaml").write_text(ev.replace("max_tool_calls: 28", "max_tool_calls: 30"))
    (out / "prompts/search.md").write_text(se)
    (out / "prompts/writer.md").write_text(wr)
    (out / "prompts/system.md").write_text(so)
    (out / "skills/evidence/SKILL.md").write_text(E4.SKILL_MD)
    (out / "skills/evidence/scripts/evidence.py").write_text(search_script())
    (out / "agent.yaml").write_text("# sbE6 (2026-11-20): search (one call, thinking off) -> writer (write_file only: .git/agent/expect.py) -> solver (first call = the check; fence-free) (scripts/make_expect_e6.py)\n"
                                    "name: swe_agent\nagent_class: SequentialAgent\nsub_agents:\n  - config_path: search.yaml\n  - config_path: writer.yaml\n  - config_path: solver.yaml\n")
    (out / "search.yaml").write_text("name: search\nmodel: gemma-4-31b-it-qat-w4a16-ct\ninstruction: !include prompts/search.md\ninclude_contents: none\n"
                                     "tools:\n  - get_status\nskills:\n  - skills/evidence\noutput_key: evidence\ngenerate_content_config: !include configs/search_sampling.yaml\n")
    (out / "writer.yaml").write_text("name: writer\nmodel: gemma-4-31b-it-qat-w4a16-ct\ninstruction: !include prompts/writer.md\ninclude_contents: none\n"
                                     "tools:\n  - write_file\noutput_key: expectation\ngenerate_content_config: !include configs/sampling.yaml\n")
    sb = (SUB / "sb1hl/agent.yaml").read_text().split("\n", 1)[1].replace("name: swe_agent", "name: solver")
    assert "instruction: !include prompts/system.md" in sb and "write_file" not in sb
    (out / "solver.yaml").write_text(sb)
    print("wrote", out.relative_to(ROOT), "| search", len(se), "| writer", len(wr), "| solver", len(so), "chars")


if __name__ == "__main__":
    build()
