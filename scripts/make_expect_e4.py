"""r129 arms (user 2026-11-20: 'we try both A and B with the rest of fixes and yes E3 + backslash alone as well').
Run: python3 -I scripts/make_expect_e4.py
  sbE3b = sbE3 + the backslash fallback (scripts/edit_fallback.py) in the edit step + a worked example of its note.
  sbE4A = sbE3b + a search stage first (SequentialAgent [search -> solver]): one run_skill_script call, thinking off, of a cut-down
          evidence script (where each name is defined / used in source + test lines that use it; no history, no changelog), its
          reply pinned into the solver's prompt via output_key evidence; the solver's example 1 starts with the expectation.
          eval_config 29 calls (28 + the stage's one), as evidc.
  sbE4B = sbE3b + WHEN lines and worked examples for the harness message '... tool call finished closing' (calls sent as text:
          10 of 334 bank runs, 7 of them ended with no source change, 23 of 29 text replies end with the ``` fence;
          scripts/mine_bank/b_losses.py) and for an existing test failing after the edit (fix forward, never undo the edit).
Prompts: scripts/agent_expect/make_prompts_e4.py. Everything else = sbE3 (sb1hl's tools, sampling, eval_config)."""
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
PLUS_SAMPLING = re.search(r'FAST_SAMPLING = """(.*?)"""', (ROOT / "scripts/make_plus_arms.py").read_text(), re.S).group(1)
M, SUB = XA.M, XA.SUB
HALVED = "double backslashes in your text read as single ones"
assert HALVED in F.ADD
X = types.SimpleNamespace(EV3=XA.EV3, EDIT_STEP=F.halve(XA.EDIT_STEP3), RERUN=XA.RERUN, expect_cmd=XA.expect_cmd3, HALVED=HALVED)
sys.path.insert(0, str(ROOT / "scripts/agent_expect"))
import make_prompts_e4 as P4  # noqa: E402

# ---- the cut-down search script (generated from evidence_r79.py: same names / timeouts / one-call rule, sections replaced)
SRC79 = (ROOT / "scripts/agent_evidence/evidence_r79.py").read_text()
NEW_SECTION = '''def section(ws, name, start):
    out = [f"== {name}"]
    if re.fullmatch(IDENT, name):
        defs = git(ws, ["grep", "-n", "-I", "-E", "-e", rf"^[[:space:]]*(async def|def|class) {name}([^A-Za-z0-9_]|$)", "--", "*.py"], start) or []
        if defs:
            out.append("defined at:")
            out.extend("  " + short(d) for d in defs[:DEF_LINES])
        else:
            uses = git(ws, ["grep", "-n", "-I", "-w", "-F", "-e", name, "--"] + SRC, start) or []
            if uses:
                out.append(f"used in source: {len(uses)} lines")
                out.extend("  " + short(u) for u in uses[:SRC_LINES])
    tests = git(ws, ["grep", "-n", "-I", "-F", "-e", name, "--"] + TEST_PATHS, start)
    if tests is None:
        return out + ["  (skipped: time)"]
    out.append(f"tests that use it: {len(tests)} lines" + ("" if tests else " (none)"))
    out.extend("  " + short(t) for t in tests[:TEST_LINES])
    return out


'''


def search_script():
    s = SRC79
    head_end = s.index('"""', 3) + 3
    s = ('"""Where the issue\'s names are, in one call (r129 arm sbE4A, scripts/make_expect_e4.py; cut down from evidence_r79.py: for each\n'
         'name, where it is defined (or used in source when it has no def / class line) and test lines that use it; no history, no changelog).\n'
         'Run once by the search stage through run_skill_script (skill "evidence"), names as positional_args."""' + s[head_end:])
    a, b = s.index("def section(ws, name, start):"), s.index("def main():")
    s = s[:a] + NEW_SECTION + s[b:]
    reps = [("REPLY = 'Now reply with at most 10 lines of this result, copied exactly, and stop.'",
             "REPLY = 'Now reply with at most 12 lines of this result, copied exactly, and stop.'"),
            ("TEST_LINES = 6", "TEST_LINES = 8"),
            ('parts = [f"REPOSITORY EVIDENCE for {\', \'.join(names)} (read-only searches; the issue stays the specification)"]',
             'parts = [f"WHERE THE ISSUE\'S NAMES ARE, for {\', \'.join(names)} (read-only searches; the issue stays the specification)"]')]
    for x, y in reps:
        assert s.count(x) == 1, x
        s = s.replace(x, y)
    assert "log" not in NEW_SECTION and "git log" not in s.split("def section")[1].split("def main")[0]
    return s


SKILL_MD = """---
name: evidence
description: Finds where a few exact names from the issue are defined and the test lines that use them. Call run_skill_script with skill_name evidence, file_path scripts/evidence.py and positional_args holding the names.
---

Call run_skill_script with skill_name evidence, file_path scripts/evidence.py and positional_args holding two to four exact
names from the issue, one name per item. It prints where each name is defined and test lines that use it, in a few seconds.
"""


def check_solver(s, variant):
    M.check(s, ("{evidence?}",) if variant == "sbE4A" else ())
    M.examples(s)
    assert "edit_file" not in s and "write_file" not in s and "old_string" not in s
    blocks = re.findall(r"command:\n```\n(.*?)```", s, re.S)
    for b in blocks:
        assert '"' not in b and "`" not in b and "\\" not in b, b[:80]
    exp = [b for b in blocks if "EXPECT\n" in b]
    assert exp and all(b == X.expect_cmd(re.search(r"<<'EXPECT'\n(.*?)EXPECT\n", b, re.S).group(1)) for b in exp), "the expectation command byte for byte"
    edits = [b for b in blocks if "OLD_TEXT" in b]
    assert edits
    for b in edits:
        m = re.fullmatch(r"mkdir -p \.git/agent\ncat > \.git/agent/old <<'OLD_TEXT'\n(.*?)OLD_TEXT\ncat > \.git/agent/new <<'NEW_TEXT'\n(.*?)NEW_TEXT\n(python3 - (\S+) <<'EOF'\n.*)", b, re.S)
        assert m and m.group(3) == X.EDIT_STEP.replace("PATH", m.group(4)), "the edit step (with the backslash fallback) byte for byte"
        assert HALVED in m.group(3)
        reads = re.findall(r"printed:\n```\n(.*?)```", s[:s.index(b)], re.S)
        assert reads and m.group(1) in reads[-1], "old text copied from the read output just before it"
    ex1 = s[s.index("Example 1 -"):s.index("Example 2 -")]
    b1 = re.findall(r"command:\n```\n(.*?)```", ex1, re.S)
    if variant == "sbE4A":
        assert len(b1) == 1 and "EXPECT\n" in b1[0], "A: example 1 starts with the expectation"
        assert s.count("{evidence?}") == 1
    else:
        assert len(b1) == 2 and "EXPECT\n" not in b1[0] and "EXPECT\n" in b1[1], "example 1: search, then the expectation"
    outs = "\n".join(re.findall(r"printed:\n```\n(.*?)```", s, re.S))
    for k, v in X.EV3.items():
        assert v in outs, ("an example output for", k)
        assert '"' + v.split(":")[0] + '"' in s, ("a WHEN line for", k)
    assert HALVED in outs and '"' + HALVED + '"' in s
    if variant == "sbE4B":
        assert '"' + P4.CLOSING + '"' in s and P4.CLOSING in s.split("# EXAMPLES")[1]
        assert "git checkout, git stash or git reset" in s and P4.LENIENT in outs
    else:
        assert P4.CLOSING not in s and "test_read_lenient" not in s
    assert all(l.startswith("test $e = 0 && test $t -gt 0") for l in s.splitlines() if str(XA.LATE_S) in l)
    # numbered references all resolve (M.examples) and the examples are numbered 1..N without gaps
    nums = [int(x) for x in re.findall(r"^Example (\d+) -", s, re.M)]
    assert nums == list(range(1, len(nums) + 1)), nums


def check_stage(s):
    M.check(s, ("{problem_description}",))
    assert s.startswith("Your only job is one search of the repository")  # the sim's role key (data/sim/armsim.py 'evid3')
    out = re.search(r"It printed:\n```\n(.*?)```", s, re.S).group(1)
    rep = s.split("The reply, with no tool call:\n")[1].split("\n# THE ISSUE")[0]
    for l in rep.strip().splitlines():
        assert ("  " + l) in out or l in out, ("reply line copied from the output", l)
    assert len(rep.strip().splitlines()) <= 12


def single(name, s, head):
    out = SUB / name
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SUB / "sb1hl", out)
    (out / "prompts/system.md").write_text(s)
    rest = (SUB / "sb1hl/agent.yaml").read_text().split("\n", 1)[1]
    (out / "agent.yaml").write_text(head + "\n" + rest)
    print("wrote", out.relative_to(ROOT), "| chars", len(s))


def build():
    texts = {v: P4.solver(X, v) for v in ("sbE3b", "sbE4A", "sbE4B")}
    st = P4.stage(X)
    for v, s in texts.items():
        check_solver(s, v)
        (ROOT / f"scripts/agent_expect/{v}.md").write_text(s)
    check_stage(st)
    (ROOT / "scripts/agent_expect/sbE4A_search.md").write_text(st)
    single("sbE3b", texts["sbE3b"], "# sbE3b (2026-11-20): sbE3 + the backslash fallback in the edit step (scripts/make_expect_e4.py)")
    single("sbE4B", texts["sbE4B"], "# sbE4B (2026-11-20): sbE3b + WHEN lines / examples for calls sent as text and for an existing test failing after the edit (scripts/make_expect_e4.py)")
    out = SUB / "sbE4A"
    if out.exists():
        shutil.rmtree(out)
    (out / "prompts").mkdir(parents=True)
    (out / "configs").mkdir()
    (out / "skills/evidence/scripts").mkdir(parents=True)
    shutil.copy(SUB / "sb1hl/configs/sampling.yaml", out / "configs/sampling.yaml")
    (out / "configs/search_sampling.yaml").write_text(PLUS_SAMPLING)
    ev = (SUB / "sb1hl/eval_config.yaml").read_text()
    assert ev.count("max_tool_calls: 28") == 1
    (out / "eval_config.yaml").write_text(ev.replace("max_tool_calls: 28", "max_tool_calls: 29"))
    (out / "prompts/search.md").write_text(st)
    (out / "prompts/system.md").write_text(texts["sbE4A"])
    (out / "skills/evidence/SKILL.md").write_text(SKILL_MD)
    (out / "skills/evidence/scripts/evidence.py").write_text(search_script())
    (out / "agent.yaml").write_text("# sbE4A (2026-11-20): search stage (one fixed call, thinking off) -> solver = sbE3b whose example 1 starts with the expectation (scripts/make_expect_e4.py)\n"
                                    "name: swe_agent\nagent_class: SequentialAgent\nsub_agents:\n  - config_path: search.yaml\n  - config_path: solver.yaml\n")
    # no description lines (user 2026-11-20); include_contents none as evidc: the issue is in the stage's own prompt
    (out / "search.yaml").write_text("name: search\nmodel: gemma-4-31b-it-qat-w4a16-ct\ninstruction: !include prompts/search.md\ninclude_contents: none\n"
                                     "tools:\n  - get_status\nskills:\n  - skills/evidence\noutput_key: evidence\ngenerate_content_config: !include configs/search_sampling.yaml\n")
    sb = (SUB / "sb1hl/agent.yaml").read_text().split("\n", 1)[1].replace("name: swe_agent", "name: solver")
    assert "instruction: !include prompts/system.md" in sb
    (out / "solver.yaml").write_text(sb)
    print("wrote", out.relative_to(ROOT), "| search chars", len(st), "| solver chars", len(texts["sbE4A"]))


if __name__ == "__main__":
    build()
