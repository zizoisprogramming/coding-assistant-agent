"""sb3 (user 2026-11-16: 'yes build sb3 and the trial'). Run: python3 -I scripts/make_sb3.py

History shown BEFORE the fix was never used (evid4 r67-r68, evidd r79-r80, sb2 r105: git show 0/18, history-only files
edited 0/18). sb3 shows it AFTER the fix, keyed on the fix itself, to an agent whose only job is to act on it
(memory event-triggered-rules-only: tool-output events at the decision point and single-job stages are followed;
sk_fr: a fixer without submit handed over 18/20; r57 setup stage 24/24, sb2 history stage 18/18).

  root = SequentialAgent [fixer, check]
  fixer: sb1's agent without submit_patch and with a fresh prompt (scripts/agent_sb3/fixer.md): sb1's kept parts
    (existing test as the spec, keep parameters, heredoc check -> edit -> same check again + the test file) minus the
    ignored history step; it replies DONE when the fix is in the files.
  check: the six harness tools, sb1's sampling, prompt scripts/agent_sb3/check.md. First call = one fixed command
    (scripts/agent_sb3/check_cmd.sh, tested on 10 repos with real agent patches: 286-2,050 chars, no errors, blocked on
    a 2nd run) keyed on `git diff`:
      LIST 1 = source files changed in >= 20% of each edited file's last 30 commits, not in the patch, max 3 per file
        (Step 0: names a missing real-fix file in 51 of 82 multi-file runs, ~1.6 unneeded files on single-file runs);
      LIST 2 = the last 3 commits on the edited lines (git log -L), trimmed (Step 0: related for ~21-23 of 39 tasks).
    Then: answer every LIST 1 file (edit / not needed + why), read LIST 2 against the patch, run the test file, submit.
  eval_config: sb1's with max_tool_calls 32 instead of 28 (two stages; the check needs ~4-6 calls; 32 calls at 8 min
    fitted the 12 h scorer: sk_a2_32 0.17). Time stays 8 min."""
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / "submissions"
PARENT = SUB / "sb1"
OUT = SUB / "sb3"
SRC = ROOT / "scripts/agent_sb3"
SIX = ["run_command", "read_file", "edit_file", "write_file", "get_status", "submit_patch"]
ROOT_YAML = """# sb3 (2026-11-16): fixer (no submit) then a check stage that compares the fix with the repository's history and submits (scripts/make_sb3.py)
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
    assert '"' not in cmd and "`" not in cmd and "\\" not in cmd and len(cmd) < 1700
    fixer = (SRC / "fixer.md").read_text()
    check = (SRC / "check.md").read_text()
    assert check.count("CHECK_COMMAND") == 1
    check = check.replace("CHECK_COMMAND", cmd)
    check_text(fixer, "fixer")
    check_text(check, "check")
    assert "submit_patch" not in fixer, "the fixer has no submit_patch and is never told to call it"
    assert "DONE" in fixer and "-- '*test*'" in fixer and "keeps its parameters" in fixer and "same command runs again" in fixer
    assert "git log" not in fixer, "no history in the fixer"
    assert cmd in check and "LIST 1" in check and "LIST 2" in check and "`submit_patch`" in check

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(PARENT, OUT, ignore=shutil.ignore_patterns("__pycache__"))
    (OUT / "agent.yaml").write_text(ROOT_YAML)
    (OUT / "fixer.yaml").write_text("# sb3 fixer: sb1's agent without submit_patch, fresh prompt (scripts/agent_sb3/fixer.md)\n"
                                    + agent_yaml("fixer", "Finds the code, fixes the issue and checks the fix, then hands over.", "fixer.md", SIX[:5]))
    (OUT / "check.yaml").write_text("# sb3 check: history check keyed on the fixer's diff, then submit (scripts/agent_sb3/check.md)\n"
                                    + agent_yaml("check", "Compares the fix with the repository's history, completes it and submits it.", "check.md", SIX))
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
