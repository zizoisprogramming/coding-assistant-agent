"""Expectation arms (user 2026-11-20: 'skip the control, also i need only 2 task set, the ones should be among our expected to
solve patterns'; design docs/PLAN.md DIRECTION 1 STUDY: runs whose own check SHOWED the problem solve 71% vs 41%).
Run: python3 -I scripts/make_expect_arms.py
All arms = sb1hl (heredoc edits, short prompt) plus one fixed EXPECTATION COMMAND: heredocs write .git/agent/expect.py (asserts of
the behaviour the issue wants) and .git/agent/check.sh (fixed), then `bash .git/agent/check.sh` runs expect.py and prints ONE event:
  fails, no source edit yet  -> the problem is shown (E: now edit; X1's expectation agent: reply with the note now)
  passes, no edit yet        -> it does not show the problem: change it to what the issue says must change
  fails after an edit        -> still fails: read the failure, edit again
  passes after an edit       -> passes with your edit: run the existing test file, then finish
  SyntaxError / IndentationError in the script -> the script itself is broken: fix it
('edited' = git diff of tracked files is not empty; scratch files are untracked). sb1hl's edit step gains one line that re-runs
check.sh after every edit when it exists.
  sbE1 = one agent; sbE2 = sbE1 + a late line in check.sh: no tracked change yet and > 300 s since the harness's
  _swegemma_baseline commit -> 'Nothing is edited yet ... edit the likeliest cause now'; sbX1 = SequentialAgent [expect agent
  (run_command + read_file, no edits; writes the expectation until it fails, replies with a WANTED BEHAVIOUR note, output_key
  expectation) -> solver (sb1hl + the note pinned into its system prompt + the re-run)].
Tools / sampling / eval_config = sb1hl's (28 calls, 8 min shared by both agents in sbX1)."""
import importlib.util
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("make_sbab", ROOT / "scripts/make_sbab.py")
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
H, M = B.H, B.M
SUB = ROOT / "submissions"

EV = dict(
    shown_e="== EXPECTATION FAILS: the problem is shown. Now edit the source so this check passes.",
    shown_x="== EXPECTATION FAILS: the problem is shown. Reply now with the WANTED BEHAVIOUR note and make no other call.",
    still="== EXPECTATION STILL FAILS with your edit: read the failure above and edit the source again.",
    nothing="== EXPECTATION PASSES before any edit: it does not show the problem. Change it to assert what the issue says must change, then run it again.",
    done="== EXPECTATION PASSES with your edit: run the existing test file of this code, then finish.",
    broken="== THE EXPECTATION SCRIPT ITSELF IS BROKEN: fix the script, then run it again.",
    late="== Nothing is edited yet and the run is far along: edit the likeliest cause now; this check will tell you if it is right.",
)
LATE_S = 300


def check_sh(arm):
    lines = ["r=FAILS",
             "python3 .git/agent/expect.py > .git/agent/expect.out 2>&1 && r=PASSES",
             "tail -n 12 .git/agent/expect.out",
             "e=no",
             "git diff --quiet || e=yes",
             "grep -q -E '^(SyntaxError|IndentationError)' .git/agent/expect.out && r=BROKEN",
             f"test $r$e = FAILSno && echo '{EV['shown_x'] if arm == 'sbX1' else EV['shown_e']}'",
             f"test $r$e = FAILSyes && echo '{EV['still']}'",
             f"test $r$e = PASSESno && echo '{EV['nothing']}'",
             f"test $r$e = PASSESyes && echo '{EV['done']}'",
             f"test $r = BROKEN && echo '{EV['broken']}'"]
    if arm == "sbE2":
        lines += ["t=$(git log -1 --format=%ct _swegemma_baseline 2>/dev/null || echo 0)",
                  f"test $e = no && test $t -gt 0 && test $(( $(date +%s) - t )) -gt {LATE_S} && echo '{EV['late']}'"]
    lines.append("true")
    return "\n".join(lines) + "\n"


def expect_cmd(arm, body):
    return ("mkdir -p .git/agent\ncat > .git/agent/expect.py <<'EXPECT'\n" + body + "EXPECT\ncat > .git/agent/check.sh <<'EOF'\n" + check_sh(arm)
            + "EOF\nbash .git/agent/check.sh\n")


EDIT_STEP = H.PY_STEP + "test ! -f .git/agent/check.sh || bash .git/agent/check.sh\n"
RERUN = "bash .git/agent/check.sh"
for a in ("sbE1", "sbE2", "sbX1"):
    for c in (check_sh(a), EDIT_STEP):
        assert '"' not in c and "`" not in c and "\\" not in c and "${" not in c and "{" not in c and "}" not in c, (a, c)


def check_prompt(s, arm, role):
    M.check(s)
    M.examples(s)
    assert "edit_file" not in s and "write_file" not in s and "old_string" not in s
    blocks = re.findall(r"command:\n```\n(.*?)```", s, re.S)
    for b in blocks:
        assert '"' not in b and "`" not in b and "\\" not in b, b[:80]
    exp = [b for b in blocks if "EXPECT\n" in b]
    for b in exp:
        m = re.fullmatch(r"mkdir -p \.git/agent\ncat > \.git/agent/expect\.py <<'EXPECT'\n(.*?)EXPECT\ncat > \.git/agent/check\.sh <<'EOF'\n(.*?)EOF\nbash \.git/agent/check\.sh\n", b, re.S)
        assert m and m.group(2) == check_sh(arm), "the expectation command byte for byte"
    edits = [b for b in blocks if "OLD_TEXT" in b]
    for b in edits:
        m = re.fullmatch(r"mkdir -p \.git/agent\ncat > \.git/agent/old <<'OLD_TEXT'\n(.*?)OLD_TEXT\ncat > \.git/agent/new <<'NEW_TEXT'\n(.*?)NEW_TEXT\n(python3 - (\S+) <<'EOF'\n.*)", b, re.S)
        assert m and m.group(3) == EDIT_STEP.replace("PATH", m.group(4)), "the edit step byte for byte"
        reads = re.findall(r"read_file on \S+, lines \d+ to \d+, printed:\n```\n(.*?)```", s[:s.index(b)], re.S)
        assert reads and m.group(1) in reads[-1], "old text copied from the read output"
    if role in ("single", "expect"):
        assert len(exp) >= 1
    if role in ("single", "solver"):
        assert len(edits) >= 1
    if role == "expect":
        assert not edits and "submit_patch" not in s
    outs = "\n".join(re.findall(r"printed:\n```\n(.*?)```", s, re.S))
    want = {"single": ["shown_e", "still", "nothing", "done", "broken"] + (["late"] if arm == "sbE2" else []),
            "expect": ["shown_x", "nothing", "broken"], "solver": ["still", "done"]}[role]
    for k in want:
        assert EV[k] in outs, ("an example output for", k)
        assert '"' + EV[k].split(":")[0] + '"' in s, ("a WHEN line for", k)
    if arm != "sbE2":
        assert EV["late"] not in s
    assert all(l.startswith("test $e = no && test $t -gt 0") for l in s.splitlines() if str(LATE_S) in l), "the late number only inside check.sh's own line"


def build_single(arm):
    s = (ROOT / f"scripts/agent_expect/{arm}.md").read_text()
    check_prompt(s, arm, "single")
    out = SUB / arm
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SUB / "sb1hl", out)
    (out / "prompts/system.md").write_text(s)
    first, rest = (SUB / "sb1hl/agent.yaml").read_text().split("\n", 1)
    head = {"sbE1": "# sbE1 (2026-11-20): sb1hl + the expectation command (expect.py + check.sh events) and its re-run after every edit (scripts/make_expect_arms.py)",
            "sbE2": "# sbE2 (2026-11-20): sbE1 + a late 'nothing is edited yet' line in check.sh (scripts/make_expect_arms.py)"}[arm]
    (out / "agent.yaml").write_text(head + "\n" + rest)
    print("wrote", out.relative_to(ROOT), "| chars", len(s), "| words", len(s.split()))


def build_x1():
    se = (ROOT / "scripts/agent_expect/sbX1_expect.md").read_text()
    ss = (ROOT / "scripts/agent_expect/sbX1_solver.md").read_text()
    check_prompt(se, "sbX1", "expect")
    assert ss.count("{expectation?}") == 1
    check_prompt(ss.replace("{expectation?}", ""), "sbX1", "solver")
    out = SUB / "sbX1"
    if out.exists():
        shutil.rmtree(out)
    (out / "prompts").mkdir(parents=True)
    (out / "configs").mkdir()
    for f in ("eval_config.yaml", "configs/sampling.yaml"):
        shutil.copy(SUB / "sb1hl" / f, out / f)
    (out / "prompts/expect.md").write_text(se)
    (out / "prompts/system.md").write_text(ss)
    (out / "agent.yaml").write_text("# sbX1 (2026-11-20): expectation agent (no edits) -> solver = sb1hl + the WANTED BEHAVIOUR note pinned + the re-run after every edit (scripts/make_expect_arms.py)\n"
                                    "name: swe_agent\nagent_class: SequentialAgent\ndescription: Writes a failing check of the behaviour the issue wants, then fixes the issue.\n"
                                    "sub_agents:\n  - config_path: expect.yaml\n  - config_path: solver.yaml\n")
    # no description lines: ADK appends 'The description about you is ...' to an agent's system prompt when one is set (user 2026-11-20: remove lines that do not matter for the agents); the name line is ADK's own and cannot be switched off
    (out / "expect.yaml").write_text("name: expect\nmodel: gemma-4-31b-it-qat-w4a16-ct\n"
                                     "instruction: !include prompts/expect.md\noutput_key: expectation\ntools:\n  - run_command\n  - read_file\ngenerate_content_config: !include configs/sampling.yaml\n")
    sb = (SUB / "sb1hl/agent.yaml").read_text().split("\n", 1)[1]
    sb = sb.replace("name: swe_agent", "name: solver")
    (out / "solver.yaml").write_text(sb)
    assert "instruction: !include prompts/system.md" in sb and "tools:" in sb
    print("wrote", out.relative_to(ROOT), "| expect chars", len(se), "| solver chars", len(ss))



# ---------------------------------------------------------------- sbE3 (user 2026-11-20: 'yes build E3 alone on 4 tasks to run')
# sbE3 = sbE2 + the r127 fixes: (1) the expectation is the SECOND call in the worked examples, and the edit step refuses the FIRST
# edit once when no .git/agent/expect.py exists (F1 adoption, 5/12 runs skipped the command); (2) 'passes before any edit' says the
# case is not the issue's and names what to copy (construct, inputs, options), with a worked example where the simple function
# already works but the issue's construct does not (F2 wrong target); (3) a shorter check.sh (one case statement, shorter events)
# against long calls sent as text (F4). The late line of sbE2 stays.
EV3 = dict(
    shown="== EXPECTATION FAILS: the problem is shown. Edit the source now.",
    still="== EXPECTATION STILL FAILS with your edit: read the failure and edit again.",
    nothing="== EXPECTATION PASSES before any edit: your case is not the one in the issue. Use its construct, options and inputs.",
    done="== EXPECTATION PASSES with your edit: run the existing test file, then finish.",
    broken="== EXPECTATION SCRIPT BROKEN: fix the script.",
    late="== NOTHING EDITED YET and the run is far along: edit the likeliest cause now.",
    refused="== EDIT HELD BACK: write the expectation first (example 1), then send this same edit again.",
)
CHECK3 = ("python3 .git/agent/expect.py > .git/agent/expect.out 2>&1 && r=PASSES || r=FAILS\n"
          "grep -q -E '^(SyntaxError|IndentationError)' .git/agent/expect.out && r=BROKEN\n"
          "tail -n 12 .git/agent/expect.out\n"
          "git diff --quiet && e=0 || e=1\n"
          "case $r$e in\n"
          f"FAILS0) echo '{EV3['shown']}';;\n"
          f"FAILS1) echo '{EV3['still']}';;\n"
          f"PASSES0) echo '{EV3['nothing']}';;\n"
          f"PASSES1) echo '{EV3['done']}';;\n"
          f"*) echo '{EV3['broken']}';;\n"
          "esac\n"
          "t=$(git log -1 --format=%ct _swegemma_baseline 2>/dev/null || echo 0)\n"
          f"test $e = 0 && test $t -gt 0 && test $(( $(date +%s) - t )) -gt {LATE_S} && echo '{EV3['late']}'\n"
          "true\n")
PY_STEP3 = """python3 - PATH <<'EOF'
import os, pathlib, sys
p = pathlib.Path(sys.argv[1])
s, old, new = p.read_text(), open('.git/agent/old').read(), open('.git/agent/new').read()
print('old text found', s.count(old), 'times')
if s.count(old) == 1 and not os.path.exists('.git/agent/expect.py') and not os.path.exists('.git/agent/asked'):
    open('.git/agent/asked', 'w').close()
    print('""" + EV3["refused"] + """')
elif s.count(old) == 1:
    p.write_text(s.replace(old, new))
    print('EDITED', p)
EOF
git diff -U1 -- PATH | head -40
"""
EDIT_STEP3 = PY_STEP3 + "test ! -f .git/agent/check.sh || bash .git/agent/check.sh\n"
assert all("'" not in v for v in EV3.values()), 'event texts sit inside single quotes'
for c in (CHECK3, EDIT_STEP3):
    assert '"' not in c and "`" not in c and "\\" not in c and "${" not in c and "{" not in c and "}" not in c, c


def expect_cmd3(body):
    return ("mkdir -p .git/agent\ncat > .git/agent/expect.py <<'EXPECT'\n" + body + "EXPECT\ncat > .git/agent/check.sh <<'EOF'\n" + CHECK3
            + "EOF\nbash .git/agent/check.sh\n")


def check_e3(s):
    M.check(s)
    M.examples(s)
    assert "edit_file" not in s and "write_file" not in s and "old_string" not in s
    blocks = re.findall(r"command:\n```\n(.*?)```", s, re.S)
    for b in blocks:
        assert '"' not in b and "`" not in b and "\\" not in b, b[:80]
    exp = [b for b in blocks if "EXPECT\n" in b]
    assert len(exp) >= 1
    for b in exp:
        m = re.fullmatch(r"mkdir -p \.git/agent\ncat > \.git/agent/expect\.py <<'EXPECT'\n(.*?)EXPECT\ncat > \.git/agent/check\.sh <<'EOF'\n(.*?)EOF\nbash \.git/agent/check\.sh\n", b, re.S)
        assert m and m.group(2) == CHECK3, "the expectation command byte for byte"
    edits = [b for b in blocks if "OLD_TEXT" in b]
    assert len(edits) >= 1
    for b in edits:
        m = re.fullmatch(r"mkdir -p \.git/agent\ncat > \.git/agent/old <<'OLD_TEXT'\n(.*?)OLD_TEXT\ncat > \.git/agent/new <<'NEW_TEXT'\n(.*?)NEW_TEXT\n(python3 - (\S+) <<'EOF'\n.*)", b, re.S)
        assert m and m.group(3) == EDIT_STEP3.replace("PATH", m.group(4)), "the edit step byte for byte"
        reads = re.findall(r"printed:\n```\n(.*?)```", s[:s.index(b)], re.S)
        assert reads and m.group(1) in reads[-1], "old text copied from the read output just before it"
    # the expectation is the second call of example 1: one search command, then the expectation command
    ex1 = s[s.index("Example 1 -"):s.index("Example 2 -")]
    b1 = re.findall(r"command:\n```\n(.*?)```", ex1, re.S)
    assert len(b1) == 2 and "EXPECT\n" not in b1[0] and "EXPECT\n" in b1[1], "example 1: search, then the expectation"
    outs = "\n".join(re.findall(r"printed:\n```\n(.*?)```", s, re.S))
    for k, v in EV3.items():
        assert v in outs, ("an example output for", k)
        assert '"' + v.split(":")[0] + '"' in s, ("a WHEN line for", k)
    assert all(l.startswith("test $e = 0 && test $t -gt 0") for l in s.splitlines() if str(LATE_S) in l), "the late number only inside check.sh's own line"


def build_e3():
    s = (ROOT / "scripts/agent_expect/sbE3.md").read_text()
    check_e3(s)
    out = SUB / "sbE3"
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SUB / "sb1hl", out)
    (out / "prompts/system.md").write_text(s)
    first, rest = (SUB / "sb1hl/agent.yaml").read_text().split("\n", 1)
    (out / "agent.yaml").write_text("# sbE3 (2026-11-20): sbE2 + expectation as the 2nd call, one-time refusal of the first edit without expect.py, "
                                    "'not the issue's case' event + example, shorter check.sh (scripts/make_expect_arms.py)\n" + rest)
    print("wrote", out.relative_to(ROOT), "| chars", len(s), "| words", len(s.split()))

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT / "scripts/agent_expect"))
    import make_prompts
    make_prompts.write_all(sys.modules[__name__])
    build_single("sbE1")
    build_single("sbE2")
    build_x1()
    build_e3()
