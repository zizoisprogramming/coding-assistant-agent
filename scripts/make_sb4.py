"""sb4 (user 2026-11-17: 'yes build sb4 with both fixes and the trial'). Run: python3 -I scripts/make_sb4.py

sb3 (r108) showed the check stage works as a step (command first 16/16, every listed file looked at 8/11) but
(1) it was starved: the fixer used ~28 of 32 calls, 8/24 runs never reached the check, 3 more had 0-1 calls left;
(2) it was anchored: it searched listed files for the FIXER's new code and trusted the fix ('not needed'), 0 listed
real-fix files added although LIST 1 named one in sievelib, qiskit-bot, policyuniverse.
sb4 = sb3 with both fixed:
  fixer (scripts/agent_sb4/fixer.md): find, read the closest test, reproduce with a heredoc, edit, then hand over at
    once (DONE + one sentence + the heredoc it ran); no re-check, no tests (moved to the check stage).
  check (scripts/agent_sb4/check.md): the fixed command (scripts/agent_sb4/check_cmd.sh) now also prints the
    EDITED FUNCTIONS AND CLASSES (from the diff) and, under each LIST 1 file, its `uses:` lines (git grep -w of the
    edited names in that file), so the evidence is in the tool output, not left to the agent's search
    (memory event-triggered-rules-only). The prompt says first edits often miss a caller / import / registration;
    a file with uses: lines on the issue's path gets the matching change; a file without them is searched once
    for the issue's names. Then LIST 2, then the first engineer's heredoc again + an edge case + the test file in
    one run_command, then submit. Made-up examples (parse_header / client), nothing from the tasks.
  eval_config: 32 calls, 8 min (as sb3)."""
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / "submissions"
PARENT = SUB / "sb1"
OUT = SUB / "sb4"
SRC = ROOT / "scripts/agent_sb4"
SIX = ["run_command", "read_file", "edit_file", "write_file", "get_status", "submit_patch"]
ROOT_YAML = """# sb4 (2026-11-17): fixer hands over right after its edit, then a check stage with the history lists and the uses of the edited names, which completes, checks and submits (scripts/make_sb4.py)
name: swe_agent
agent_class: SequentialAgent
description: Fixes the issue, then checks the fix against the repository's history and submits it.
sub_agents:
  - config_path: fixer.yaml
  - config_path: check.yaml
"""


def agent_yaml(name, desc, prompt, tools):
    return (f"name: {name}\nmodel: gemma-4-31b-it-qat-w4a16-ct\ndescription: {desc}\ninstruction: !include prompts/{prompt}\n"
            "tools:\n" + "".join(f"  - {t}\n" for t in tools) + "generate_content_config: !include configs/sampling.yaml\n")


def check_text(p, name):
    low = p.lower()
    assert "budget" not in low.replace("tool call budget exhausted", ""), name
    assert "minute" not in low and not re.search(r"\b\d+\s*(tool\s*)?calls?\b|\bby call\b|\bcall \d+", low), name
    assert not re.search(r"\b(run_command|edit_file|read_file|submit_patch|write_file)\(", p), name
    assert not re.search(r"\{[A-Za-z_][\w.]*\??\}", p), f"{name}: ADK templating would replace {{identifier}}"
    assert "\\" not in p[p.index("# EXAMPLES"):], f"{name}: no backslashes in the examples"
    for block in re.findall(r"```\n(.*?)```", p, re.S):
        if block.lstrip().startswith(("git ", "python3", "set -f")):
            assert '"' not in block and "`" not in block, f"{name}: shell text uses single quotes, no backticks"
    for msg in ("mandatory input parameters are not present", "old_string not found", "Tool call budget exhausted",
                "Example 1", "Example 2", "Example 3", "Example 4"):
        assert msg in p, (name, msg)


def main():
    cmd = (SRC / "check_cmd.sh").read_text().rstrip("\n")
    assert '"' not in cmd and "`" not in cmd and "\\" not in cmd and len(cmd) < 2000
    fixer = (SRC / "fixer.md").read_text()
    check = (SRC / "check.md").read_text()
    assert check.count("CHECK_COMMAND") == 1
    check = check.replace("CHECK_COMMAND", cmd)
    check_text(fixer, "fixer")
    check_text(check, "check")
    assert "submit_patch" not in fixer, "the fixer has no submit_patch and is never told to call it"
    assert "DONE" in fixer and "-- '*test*'" in fixer and "keeps its parameters" in fixer and "pytest" not in fixer, "fixer: no test runs"
    assert "git log" not in fixer, "no history in the fixer"
    assert cmd in check and "LIST 1" in check and "LIST 2" in check and "`submit_patch`" in check and "uses:" in check and "pytest" in check

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(PARENT, OUT, ignore=shutil.ignore_patterns("__pycache__"))
    (OUT / "agent.yaml").write_text(ROOT_YAML)
    (OUT / "fixer.yaml").write_text("# sb4 fixer: hands over right after its edit, no submit (scripts/agent_sb4/fixer.md)\n"
                                    + agent_yaml("fixer", "Finds the code, reproduces the problem and makes the first edit, then hands over.", "fixer.md", SIX[:5]))
    (OUT / "check.yaml").write_text("# sb4 check: history lists + uses of the edited names, then check, tests, submit (scripts/agent_sb4/check.md)\n"
                                    + agent_yaml("check", "Compares the edit with the repository's history, completes it, checks it and submits it.", "check.md", SIX))
    (OUT / "prompts/system.md").unlink()
    (OUT / "prompts/fixer.md").write_text(fixer)
    (OUT / "prompts/check.md").write_text(check)
    ev = (PARENT / "eval_config.yaml").read_text()
    assert ev.count("max_tool_calls: 28") == 1
    (OUT / "eval_config.yaml").write_text(ev.replace("max_tool_calls: 28", "max_tool_calls: 32"))
    assert (OUT / "configs/sampling.yaml").read_bytes() == (PARENT / "configs/sampling.yaml").read_bytes()
    assert re.findall(r"^\s+- (\w+)\s*$", (OUT / "fixer.yaml").read_text(), re.M) == SIX[:5]
    assert re.findall(r"^\s+- (\w+)\s*$", (OUT / "check.yaml").read_text(), re.M) == SIX
    assert not (OUT / "skills").exists()
    files = sorted(q.relative_to(OUT).as_posix() for q in OUT.rglob("*") if q.is_file())
    print("wrote", OUT.relative_to(ROOT), files)
    print("fixer prompt words", len(fixer.split()), "| check prompt words", len(check.split()), "| command chars", len(cmd))


if __name__ == "__main__":
    main()
