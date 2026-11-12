"""r88 arm evdraft (user 2026-11-12 "build it": the draft-first stage). Run: python3 scripts/make_r88_arms.py

Why (docs/PLAN.md MINING 2026-11-12e, SECOND LOOK): 44% of evidence-family runs end with no patch; 89 of 318 (28%) run
out of time thinking long (626 tokens per reply) after reading the real-fix lines (98%) and only 25% of them ever try an
edit. An edit that exists counts even if the run ends at the cap, so a quick best guess made early turns some of those
zero-patch runs into patches; the fixer then checks it as usual.

  evdraft = evidc + a drafter stage between the evidence stage and the fixer:
    drafter  LlmAgent, include_contents none (fresh: the issue and the copied evidence are in its system prompt), thinking
             off (thinking_budget 0, as the evidence stage), max_output 2048, tools run_command + edit_file only,
             output_key draft; prompt written fresh (scripts/agent_draft/drafter.md): print the lines where the evidence
             points, make one best-guess edit, reply 'DRAFT: file: change' (or 'DRAFT: none'); no budget numbers and no
             numbered call plan.
    fixer    evidc's prompt byte for byte + a DRAFT EDIT section at the end (the draft is a guess: keep, correct or undo).
    budget   max_tool_calls 29 -> 31 (the drafter's print and edit), everything else evidc's.
Everything else is evidc's bundle byte for byte (asserted)."""
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / "submissions"
PARENT, OUT = SUB / "evidc", SUB / "evdraft"
DRAFTER_PROMPT = ROOT / "scripts/agent_draft/drafter.md"
COMMENT = "# evdraft (r88): evidc + a drafter stage (thinking off, one quick best-guess edit before the fixer, output_key draft) (scripts/make_r88_arms.py)\n"
DRAFTER_YAML = """name: drafter
model: gemma-4-31b-it-qat-w4a16-ct
description: Makes one quick best-guess edit where the evidence points, before the fixer starts.
instruction: !include prompts/drafter.md
include_contents: none  # fresh: the issue and the evidence are in its system prompt
tools:
  - run_command
  - edit_file
output_key: draft
generate_content_config: !include configs/drafter_sampling.yaml
"""
DRAFTER_SAMPLING = """# r88 drafter: thinking off (thinking_budget 0 switches it off in adk_submission 0.2.13, as the evidence stage), room for one edit.
temperature: 0.2
top_p: 0.95
max_output_tokens: 2048
thinking_config:
  thinking_budget: 0
  include_thoughts: false
"""
FIXER_ADD = """
# DRAFT EDIT (made by a quick first pass before you started)
A first pass already made a best-guess edit to the source; `git diff` shows it, and its note is below. It is only a guess: check it against the issue, then keep it, correct it, or restore the file with `git checkout -- <file>` and make your own edit.
{draft?}
"""


def files(d):
    return sorted(p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file() and "__pycache__" not in p.parts)


if OUT.exists():
    shutil.rmtree(OUT)
shutil.copytree(PARENT, OUT, ignore=shutil.ignore_patterns("__pycache__"))
agent = (PARENT / "agent.yaml").read_text()
first, rest = agent.split("\n", 1)
assert first.startswith("# evidc (r76)")
rest2 = rest.replace("  - config_path: evidence.yaml\n  - config_path: fixer.yaml\n", "  - config_path: evidence.yaml\n  - config_path: drafter.yaml\n  - config_path: fixer.yaml\n")
assert rest2 != rest
(OUT / "agent.yaml").write_text(COMMENT + rest2)
(OUT / "drafter.yaml").write_text(DRAFTER_YAML)
(OUT / "configs/drafter_sampling.yaml").write_text(DRAFTER_SAMPLING)
p = DRAFTER_PROMPT.read_text()
low = p.lower()
assert "{problem_description}" in p and "{evidence?}" in p
assert "budget" not in low and "minute" not in low and not re.search(r"\b\d+\s*(tool\s*)?calls?\b|\bby call\b|^\s*\d+\.", p, re.M), "no budget numbers or numbered call plans"
(OUT / "prompts/drafter.md").write_text(p)
fx = (PARENT / "prompts/fixer.md").read_text()
(OUT / "prompts/fixer.md").write_text(fx.rstrip("\n") + "\n" + FIXER_ADD)
ev = (PARENT / "eval_config.yaml").read_text()
ev2 = ev.replace("max_tool_calls: 29", "max_tool_calls: 31")
assert ev2 != ev
(OUT / "eval_config.yaml").write_text(ev2)

new = {"drafter.yaml", "configs/drafter_sampling.yaml", "prompts/drafter.md"}
assert set(files(OUT)) == set(files(PARENT)) | new
for f in files(PARENT):
    if f not in ("agent.yaml", "prompts/fixer.md", "eval_config.yaml"):
        assert (OUT / f).read_bytes() == (PARENT / f).read_bytes(), f
assert (OUT / "prompts/fixer.md").read_text().startswith(fx.rstrip("\n"))
print("wrote", OUT.relative_to(ROOT), "|", files(OUT))
