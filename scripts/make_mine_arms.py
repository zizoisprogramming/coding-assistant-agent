"""Arms from the 2026-11-08 data mining (docs/PLAN.md "DATA MINING for new agent ideas"). Run: python3 scripts/make_mine_arms.py

Each arm keeps pub024 itself as the agent that fixes: its prompt, tools and sampling are copied byte for byte (only its name
changes to "fixer" inside a SequentialAgent). One idea per arm, as an agent placed before it or one sampling change:

  hpub    hunch -> pub024. The r60 hunch note (one call, no tools) without r60's slower rewritten fixer: tests the user's
          reading "hunch is slow more than bad" (the extra time came from the fixer: 30% more output tokens, first edit 307 s
          vs 157 s).
  cap2k   pub024 with max_output_tokens 2048 (thinking budget 1536). 2.5% of calls take 23% of model time; a 2048 cap cuts
          3.1% of pub024's calls and about 11% of its model time. The harness answers a cut reply with a "keep reasoning
          short, call the tool now" nudge and resets the nudge count after every turn with a tool call (agent_runner.py).
  autochk checker -> pub024. The checker (write_file only, fresh, issue in its system prompt) writes .git/agent/check.py
          (never in the patch) that runs the issue's example and prints PASS or FAIL lines, then says so. Running code
          after the edit is the strongest within-task correlate of solving (+11 points, 21 tasks vs 4).
  evid1   evidence -> pub024. One call to scripts/evidence.py (tests, definitions, git log -S with the changed lines,
          changelog) for names the agent picks from the issue; about 1 s on a 7,000-commit repository. r60's scouts found
          this kind of evidence but took 2-4 minutes.
  evhunch evidence + note -> pub024. The same one call, then a hunch-style note grounded in what it found.

Earlier agents reach pub024 as user text: ADK shows another agent's replies and tool results as "For context: [agent]
said: ..." (flows/llm_flows/contents.py _present_other_agent_message). Every stage before pub024 has include_contents: none
and the issue in its system prompt, because the harness re-runs the root agent after a nudge.
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "submissions/pub024"
HUNCH = ROOT / "submissions/hunch"
EVIDENCE_PY = ROOT / "scripts/agent_evidence/evidence.py"
MODEL = "gemma-4-31b-it-qat-w4a16-ct"

CAP_SAMPLING = """# cap2k: pub024's sampling with the output cap lowered from 8192 to 2048 (thinking budget 4096 -> 1536, under the cap)
temperature: 0.2
top_p: 0.95
max_output_tokens: 2048
thinking_config:
  thinking_budget: 1536
  include_thoughts: true
"""
EVIDENCE_SAMPLING = """# evidence (evid1): pick names and make one call; little reasoning needed
temperature: 0.2
top_p: 0.95
max_output_tokens: 1024
thinking_config:
  thinking_budget: 512
  include_thoughts: true
"""
NOTE_SAMPLING = """# evidence + note (evhunch) and checker (autochk): one call, then a considered reply (as the r60 hunch)
temperature: 0.2
top_p: 0.95
max_output_tokens: 6144
thinking_config:
  thinking_budget: 4096
  include_thoughts: true
"""

EVIDENCE_MD = """Your only job is a single search of the repository for the agent who fixes the issue after you. You will not read code
and you will not work on the fix.

Choose two to four exact names from the issue below that the fix most likely touches: functions, methods, classes,
options or parameters, written exactly as they appear in the issue or as they would appear in the code. Prefer the most
specific names, such as convert_underscores, over common words, such as Header.

Call run_skill_script with skill_name evidence, file_path scripts/evidence.py and positional_args holding those names,
one name per item. Then reply with the single line EVIDENCE READY and stop. If the call fails, make it once more in the
same way, then reply and stop.

# THE ISSUE (verbatim)
{problem_description}"""

EVHUNCH_MD = """You prepare the ground for the agent who fixes the issue below after you. You will not edit anything.

First, choose two to four exact names from the issue that the fix most likely touches: functions, methods, classes,
options or parameters, written exactly as they appear in the issue or as they would appear in the code. Prefer the most
specific names, such as convert_underscores, over common words, such as Header. Call run_skill_script with skill_name
evidence, file_path scripts/evidence.py and positional_args holding those names, one name per item. It searches the
repository's tests, definitions, git history and changelog. That is your only call.

Then read what it found next to the issue, think about what the hidden tests, which were written from the issue, will
check, and reply with a short note in plain text, at most 30 lines:
LIKELY PLACE: files and functions, with file:line where the search showed them; mark guesses as guesses
EXPECTED BEHAVIOUR: three to six concrete checks the hidden tests probably make, each as "calling X with Y gives Z",
  quoting the exact names, messages and types from the issue
EVIDENCE THAT MATTERS: the few lines of the search that show how this code is meant to behave or how it was changed
  before, quoted with file:line or commit; write "none" if nothing helps
EASY TO MISS: edge cases, parallel implementations, registration points, wording that must match exactly

# THE ISSUE (verbatim)
{problem_description}"""

CHECKER_MD = """You write a check script for the agent who fixes the issue below after you. You have one tool, write_file, and you
will not see any code, so build the check from the issue alone.

Call write_file once with filepath .git/agent/check.py (that exact path: files under .git never reach the graded patch).
The script must:
- begin with: import os, sys; sys.path.insert(0, os.getcwd())
- run the issue's own example or examples through the public names the issue uses, as two to five separate checks
- print, for each check, either "PASS: what was checked" or "FAIL: what was checked: expected X, got Y"
- catch every exception inside each check and print it as a FAIL line with the exception type and message, so one
  failing check never hides the others
- need no network, no input and no files outside the repository, and finish within a few seconds

When the issue describes behaviour that does not exist yet, the checks describe the behaviour the issue asks for, so they
print FAIL before the fix.

After the write_file call, reply with exactly this line and stop:
CHECK READY: python .git/agent/check.py prints FAIL lines now and every line prints PASS after a correct fix. Run it after each edit.

# THE ISSUE (verbatim)
{problem_description}"""

CHECKER_FAST_SAMPLING = """# autochk2 checker: r63's checker took 71-218 s to write the script with thinking 4096; less thinking
temperature: 0.2
top_p: 0.95
max_output_tokens: 4096
thinking_config:
  thinking_budget: 1024
  include_thoughts: true
"""

SKILL_MD = """---
name: evidence
description: Searches the repository's tests, definitions, git history and changelog for a few exact names from the issue. Call run_skill_script with skill_name evidence, file_path scripts/evidence.py and positional_args holding the names.
---

Call run_skill_script with skill_name evidence, file_path scripts/evidence.py and positional_args holding two to four exact
names from the issue, one name per item. It prints what the repository says about each name and takes a few seconds.
"""

STAGE_YAML = """name: {name}
model: {model}
description: {description}
instruction: !include prompts/{name}.md
include_contents: none  # fresh: the issue is in its system prompt (the harness re-runs the root agent after a nudge)
{tools}generate_content_config: !include configs/{name}_sampling.yaml
"""


def pub_files():
    """pub024 as the fixer: every file byte for byte, the agent renamed (a SequentialAgent needs unique names)."""
    files = {p.relative_to(PUB).as_posix(): p.read_text() for p in sorted(PUB.rglob("*")) if p.is_file()}
    y = files.pop("agent.yaml")
    assert y.startswith("name: swe_agent\n"), y[:40]
    files["fixer.yaml"] = y.replace("name: swe_agent\n", "name: fixer\n", 1)
    return files


def sequential(arm, first, why):
    return (f"# {arm}: scripts/make_mine_arms.py; {why}\nname: swe_agent\nagent_class: SequentialAgent\nsub_agents:\n"
            f"  - config_path: {first}.yaml\n  - config_path: fixer.yaml\n")


def eval_config(extra_calls):
    """pub024's limits; a stage that makes a tool call gets that call added, so the fixer keeps pub024's 28."""
    y = (PUB / "eval_config.yaml").read_text()
    assert "max_tool_calls: 28\n" in y
    return y.replace("max_tool_calls: 28\n", f"max_tool_calls: {28 + extra_calls}\n")


def evidence_stage(name, prompt, sampling, desc, once=False):
    tools = "tools:\n  - get_status\nskills:\n  - skills/evidence\n"
    script = EVIDENCE_PY.read_text()
    assert "\nONCE = False  #" in script
    if once:
        script = script.replace("\nONCE = False  #", "\nONCE = True  #", 1)
    return {f"{name}.yaml": STAGE_YAML.format(name=name, model=MODEL, description=desc, tools=tools),
            f"prompts/{name}.md": prompt, f"configs/{name}_sampling.yaml": sampling,
            "skills/evidence/SKILL.md": SKILL_MD, "skills/evidence/scripts/evidence.py": script}


def arm_files(arm):
    f = pub_files()
    if arm == "hpub":
        for rel in ("hunch.yaml", "prompts/hunch.md", "configs/hunch_sampling.yaml"):
            f[rel] = (HUNCH / rel).read_text()
        f["agent.yaml"] = sequential(arm, "hunch", "the r60 hunch note (no tools, one reply) -> pub024 unchanged")
        f["eval_config.yaml"] = eval_config(0)
    elif arm == "cap2k":
        f["agent.yaml"] = f.pop("fixer.yaml").replace("name: fixer\n", "name: swe_agent\n", 1)
        f["configs/sampling.yaml"] = CAP_SAMPLING
    elif arm == "autochk":
        f["checker.yaml"] = STAGE_YAML.format(name="checker", model=MODEL, tools="tools:\n  - write_file\n",
                                              description="Writes .git/agent/check.py from the issue for the next agent. Makes a single call.")
        f["prompts/checker.md"] = CHECKER_MD
        f["configs/checker_sampling.yaml"] = NOTE_SAMPLING
        f["agent.yaml"] = sequential(arm, "checker", "a check script written from the issue -> pub024 unchanged")
        f["eval_config.yaml"] = eval_config(1)
    elif arm == "evid1":
        f.update(evidence_stage("evidence", EVIDENCE_MD, EVIDENCE_SAMPLING,
                                "Runs one repository search for names in the issue. Makes a single call."))
        f["agent.yaml"] = sequential(arm, "evidence", "one evidence-script call -> pub024 unchanged")
        f["eval_config.yaml"] = eval_config(1)
    elif arm == "evhunch":
        f.update(evidence_stage("evidence", EVHUNCH_MD, NOTE_SAMPLING,
                                "Runs one repository search for names in the issue, then writes a short note. Makes a single call."))
        f["agent.yaml"] = sequential(arm, "evidence", "one evidence-script call and a note -> pub024 unchanged")
        f["eval_config.yaml"] = eval_config(1)
    elif arm == "evid2":  # r64: evid1 with the script refusing a second call (r63: 2-17 calls of one name each)
        f.update(evidence_stage("evidence", EVIDENCE_MD, EVIDENCE_SAMPLING,
                                "Runs one repository search for names in the issue. Makes a single call.", once=True))
        f["agent.yaml"] = sequential(arm, "evidence", "one evidence-script call (a second is refused) -> pub024 unchanged")
        f["eval_config.yaml"] = eval_config(1)
    elif arm == "autochk2":  # r64: autochk with the checker's thinking 4096 -> 1024 (r63: 71-218 s to write the check)
        f.update({k: v for k, v in arm_files("autochk").items() if k.startswith(("checker", "prompts/checker", "agent", "eval"))})
        f["configs/checker_sampling.yaml"] = CHECKER_FAST_SAMPLING
        f["agent.yaml"] = f["agent.yaml"].replace("# autochk:", "# autochk2:", 1).replace(
            "a check script written from the issue", "a check script written from the issue with little thinking", 1)
    elif arm == "cap2k32":  # r64: cap2k with 32 calls (r63: 2 cap2k runs used all 28 calls by 252 s with no edit)
        f = arm_files("cap2k")
        y = f["eval_config.yaml"]
        assert "max_tool_calls: 28\n" in y
        f["eval_config.yaml"] = y.replace("max_tool_calls: 28\n", "max_tool_calls: 32\n")
    else:
        raise SystemExit(f"unknown arm {arm}")
    return f


ARMS = ["hpub", "cap2k", "autochk", "evid1", "evhunch"]  # r63 (evid1 / evhunch were built with ONCE absent: committed copies)
ARMS_R64 = ["evid2", "autochk2", "cap2k32"]


def build(arm):
    files = arm_files(arm)
    for rel, text in files.items():  # every {placeholder} is the harness's problem_description
        if rel.endswith(".md") and rel.startswith("prompts/") and rel != "prompts/system.md":
            assert "{problem_description}" in text and text.count("{") == 1, (arm, rel)
    assert files["prompts/system.md"] == (PUB / "prompts/system.md").read_text()
    out = ROOT / "submissions" / arm
    shutil.rmtree(out, ignore_errors=True)
    for rel, text in files.items():
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        (out / rel).write_text(text)
    print("wrote", out.relative_to(ROOT), sorted(files))


if __name__ == "__main__":
    for a in sys.argv[1:] or ARMS_R64:
        build(a)
