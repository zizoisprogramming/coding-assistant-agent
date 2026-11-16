"""sb2 (user 2026-11-16: 'enforce the first step ONLY to be git log every time and then block it ... lets go').
Run: python3 -I scripts/make_sb2.py

r104: sb1 asked for the history step in its prompt (step 3 + example 1) and the model ran it in 1 of 48 runs, like
every earlier procedure step (memory event-triggered-rules-only; r55 'install first' line 1/24 vs a setup stage
24/24 in r57). sb2 makes the step structural:
  root = SequentialAgent [history, fixer]
  history: LlmAgent, only run_command, thinking 128, include_contents none (sees the task message on its first run).
    Its prompt shows ONE fixed command; the model changes only the first line (a name from the issue). The command
    prints, for up to 3 source files containing the name, the files changed in the same commits (count over the
    file's last 30 commits) and its last 10 commits; if no file matches, the last 15 repository commits. It leaves a
    marker in .git/agent/ (scratch area, never in the patch); any later run prints only a block line ('already shown,
    do not run this again'), so a harness nudge that restarts the root costs one call and no output.
    CPU check on the 9 multi-file test tasks at their base commits (names a model would pick from each issue):
    300-2,200 chars of output, a real-fix file named for 8 of 9, every real-fix file for 4 of 9, block on the 2nd run.
  fixer: sb1's agent (tools, sampling, thinking 4096) with a prompt written fresh (scripts/agent_sb2/system.md):
    sb1's text minus the ignored history procedure, plus THE HISTORY ABOVE and an example that reads such output
    (made-up project, nothing from the test tasks), git show --stat of the pattern commit, the closest test.
eval_config.yaml is sb1's byte for byte (28 calls, 8 min; the history call counts as one of the 28)."""
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / "submissions"
PARENT = SUB / "sb1"
OUT = SUB / "sb2"
SRC = ROOT / "scripts/agent_sb2"
TOOLS = ["run_command", "read_file", "edit_file", "write_file", "get_status", "submit_patch"]
# the command tested on the 9 multi-file repos (2026-11-16); the example fills NAME with parse_config
CMD = """name='NAME'
test -e .git/agent/history_shown && { echo 'The history was already shown at the start. Do not run this again: go on with the task.'; exit 0; }
mkdir -p .git/agent && touch .git/agent/history_shown
files=$(git grep -l -F -e $name -- '*.py' | grep -v -E '(^|/)(tests?|testing)/|(^|/)test_|_test.py$|conftest' | head -3)
for f in $files; do
  echo '== '$f': files changed in the same commits (count over its last 30 commits)'
  git log --full-diff --format= --name-only -30 -- $f | sort | uniq -c | sort -rn | head -8
  echo '== '$f': last 10 commits'
  git log --oneline -10 -- $f
done
echo $files | grep -q . || { echo 'No source file contains '$name'. Last 15 commits:'; git log --oneline -15; }
"""
ROOT_YAML = """# sb2 (2026-11-16): a history stage that always runs first (one fixed git command, then blocked), then sb1's fixer with a fresh prompt (scripts/make_sb2.py)
name: swe_agent
agent_class: SequentialAgent
description: Shows the repository history around the issue, then fixes the issue.
sub_agents:
  - config_path: history.yaml
  - config_path: fixer.yaml
"""
HISTORY_YAML = """name: history
model: gemma-4-31b-it-qat-w4a16-ct
description: Runs one git command that shows how the repository usually changes around the issue. Makes a single call.
instruction: !include prompts/history.md
include_contents: none
tools:
  - run_command
generate_content_config: !include configs/history_sampling.yaml
"""
HISTORY_SAMPLING = """# history stage (sb2): one fixed command, little reasoning needed (as le6 / r57 setup stages: thinking 128)
temperature: 0.2
top_p: 0.95
max_output_tokens: 1024
thinking_config:
  include_thoughts: true
  thinking_budget: 128
"""


def common_checks(p, name):
    low = p.lower()
    assert "budget" not in low.replace("tool call budget exhausted", ""), name
    assert "minute" not in low and not re.search(r"\b\d+\s*(tool\s*)?calls?\b|\bby call\b|\bcall \d+", low), name
    assert not re.search(r"\b(run_command|edit_file|read_file|submit_patch|write_file)\(", p), name
    assert not re.search(r"\{[A-Za-z_][\w.]*\??\}", p), name  # ADK templating replaces {identifier}
    for block in re.findall(r"```\n(.*?)```", p, re.S):
        if block.lstrip().startswith(("git ", "python3", "name=")):
            assert '"' not in block, f"{name}: shell text uses single quotes"
    assert "\\n" not in p and '\\"' not in p and "\\'" not in p, f"{name}: no escapes"


def check_fixer(p):
    common_checks(p, "fixer")
    for msg in ("mandatory input parameters are not present", "old_string not found", "Path traversal detected",
                "Tool call budget exhausted", "# THE HISTORY ABOVE", "Example 1", "Example 2", "Example 3", "Example 4",
                "git show --stat a1b2c3d", "-- '*test*'", "keeps its parameters", "same command runs again"):
        assert msg in p, msg
    assert "--full-diff" not in p and "git log --oneline" not in p, "the fixer does not run the history itself"
    # the example's history output has the exact header lines the command prints
    assert "files changed in the same commits (count over its last 30 commits)" in p and ": last 10 commits" in p


def check_history(p):
    common_checks(p, "history")
    assert CMD.replace("NAME", "parse_config") in p, "history prompt shows the tested command"
    assert "HISTORY SHOWN" in p and "only its first line" in p


def main():
    fixer, hist = (SRC / "system.md").read_text(), (SRC / "history.md").read_text()
    check_fixer(fixer)
    check_history(hist)
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(PARENT, OUT, ignore=shutil.ignore_patterns("__pycache__"))
    first, rest = (PARENT / "agent.yaml").read_text().split("\n", 1)
    assert first.startswith("# sb1 (2026-11-16)") and rest.count("name: swe_agent\n") == 1
    (OUT / "agent.yaml").unlink()
    (OUT / "fixer.yaml").write_text("# sb2 fixer = sb1's agent with a fresh prompt (scripts/agent_sb2/system.md)\n"
                                    + rest.replace("name: swe_agent\n", "name: fixer\ndescription: Fixes the issue with the smallest source change and submits it.\n"))
    (OUT / "agent.yaml").write_text(ROOT_YAML)
    (OUT / "history.yaml").write_text(HISTORY_YAML)
    (OUT / "configs/history_sampling.yaml").write_text(HISTORY_SAMPLING)
    (OUT / "prompts/system.md").write_text(fixer)
    (OUT / "prompts/history.md").write_text(hist)
    assert (OUT / "eval_config.yaml").read_bytes() == (PARENT / "eval_config.yaml").read_bytes()
    assert (OUT / "configs/sampling.yaml").read_bytes() == (PARENT / "configs/sampling.yaml").read_bytes()
    assert re.findall(r"^\s+- (\w+)\s*$", (OUT / "fixer.yaml").read_text(), re.M) == TOOLS
    assert re.findall(r"^\s+- (\w+)\s*$", (OUT / "history.yaml").read_text(), re.M) == ["run_command"]
    assert not (OUT / "skills").exists()
    files = sorted(q.relative_to(OUT).as_posix() for q in OUT.rglob("*") if q.is_file())
    print("wrote", OUT.relative_to(ROOT), files)
    print("fixer prompt words", len(fixer.split()), "(sb1: 963) | history prompt words", len(hist.split()))


if __name__ == "__main__":
    main()
