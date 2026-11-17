"""sb5 (user 2026-11-17: 'yes build it with the NEXT line and the trial'). Run: python3 -I scripts/make_sb5.py

r109 (sb4): the check stage ignored the uses: evidence. qiskit-bot's uses line named the real-fix call
(qiskit_bot/api.py:154 community.add_community_label(...)) in both passes, and neither pass read api.py; across r108 + r109
listed real-fix files were edited 0 times in 31 reached runs. The lists were information in the tool output while the
instruction to act sat in the prompt, and prompt procedure is ignored (memory event-triggered-rules-only).
sb5 = sb4 with the instruction moved INTO the tool output:
  check command (scripts/agent_sb5/check_cmd.sh): right after EDITED FUNCTIONS AND CLASSES it prints '== NEXT:' lines:
    for each LIST 1 file that CALLS an edited name (git grep 'name(' minus def / class lines; at most one per file,
    3 in all) 'FILE line N has a call to the code you edited: CODE' + 'Read FILE lines N-5 to N+5, then change this call
    so it does what the fix needs, or say in one line why it already does.'; with no such call: 'no listed file calls
    the edited names. Run the heredoc check of the first engineer again, together with the test file ..., then submit.'
    Call sites only: plain uses lines matched dict keys ('Statement') and type hints ('Dependant'). A second run
    prints 'do the NEXT step it printed'. Tested on the r108 + r109 patches (34 runs, 9 repos): qiskit-bot NEXT =
    api.py:154 in 4/4, fastapi_14419 NEXT on a utils.py call in 2 (real-fix file), policyuniverse NEXT on
    policy.py Statement(...) (not needed; the 'say why it already does' branch), all others the check-and-submit step.
  check prompt (scripts/agent_sb5/check.md): a fresh rewrite around 'do what each NEXT line says'; same made-up
    parse_header / client example, now with the NEXT line and the 'already works' one-line answer.
  fixer: sb4's prompt unchanged (scripts/agent_sb5/fixer.md is a copy). eval_config 32 calls, 8 min (as sb4)."""
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / "submissions"
PARENT = SUB / "sb1"
OUT = SUB / "sb5"
SRC = ROOT / "scripts/agent_sb5"
SIX = ["run_command", "read_file", "edit_file", "write_file", "get_status", "submit_patch"]
ROOT_YAML = """# sb5 (2026-11-17): sb4 with the check command printing NEXT lines (calls of the edited code in co-changed files, or the check-and-submit step) (scripts/make_sb5.py)
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
    assert '"' not in cmd and "`" not in cmd and "\\" not in cmd and len(cmd) < 3000
    fixer = (SRC / "fixer.md").read_text()
    check = (SRC / "check.md").read_text()
    assert check.count("CHECK_COMMAND") == 1
    check = check.replace("CHECK_COMMAND", cmd)
    check_text(fixer, "fixer")
    check_text(check, "check")
    assert "submit_patch" not in fixer, "the fixer has no submit_patch and is never told to call it"
    assert "DONE" in fixer and "-- '*test*'" in fixer and "keeps its parameters" in fixer and "pytest" not in fixer, "fixer: no test runs"
    assert "git log" not in fixer, "no history in the fixer"
    assert fixer == (ROOT / "scripts/agent_sb4/fixer.md").read_text(), "fixer unchanged from sb4"
    assert "== NEXT: " in cmd and "has a call to the code you edited" in cmd and "has a call to the code you edited" in check and "NEXT line" in check
    assert cmd in check and "LIST 1" in check and "LIST 2" in check and "`submit_patch`" in check and "uses:" in check and "pytest" in check

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(PARENT, OUT, ignore=shutil.ignore_patterns("__pycache__"))
    (OUT / "agent.yaml").write_text(ROOT_YAML)
    (OUT / "fixer.yaml").write_text("# sb5 fixer: sb4 fixer unchanged (scripts/agent_sb5/fixer.md)\n"
                                    + agent_yaml("fixer", "Finds the code, reproduces the problem and makes the first edit, then hands over.", "fixer.md", SIX[:5]))
    (OUT / "check.yaml").write_text("# sb5 check: history check with NEXT lines, then do them, check, tests, submit (scripts/agent_sb5/check.md)\n"
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
