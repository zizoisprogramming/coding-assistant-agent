"""race2 (r75, user 2026-11-10 "lets test it yeah build"): a scout, then two engineers racing in parallel; the first
engineer to submit ends the task. Run: python3 scripts/make_race_arm.py

Why (docs/PLAN.md "RACE / BEST-OF-K 2026-11-10", scripts/mine_bank/bestof_sim.py): the scorer runs one task at a time,
so the GPU has room for a second sequence (decode 32.3 tok/s alone, 30.2 with two in flight). The harness ends a task
when patch_submitted is set and a final text event arrives (swegemma agent_runner.py), so in an ADK ParallelAgent the
first branch to submit ends the task and its patch is kept (submit_patch captures the diff at that moment). Simulated
from 524 real runs: a race of two full agents solves 21.1/53 vs 19.4/53 for one agent at the same mean time.

Why a scout first: two full agents in one ParallelAgent session crash ADK 1.36.1 once compaction runs (the bo3 crash,
11/24 in Oct; a branch compacts before the race ends in 93% of simulated races). Compaction fires when the latest
prompt in the session reaches 14,336 tokens. The engineers start fresh (include_contents: none) from the scout's notes,
the issue is in their system prompt ({problem_description}), and each is told about 14 calls with short reads, so their
prompts stay well under the threshold. The scout runs alone (compaction is safe there).

Isolation: engineer A edits /workspace; engineer B edits a git worktree at /workspace/.git/wt_b (inside .git, so it is
never part of the graded diff; tested locally: imports come from the worktree when run from its root, and its staged
diff applies to /workspace). B's finish command resets /workspace and applies its own diff, then B submits.
Scratch files: /tmp/scout_*, /tmp/a_*, /tmp/b_* so the three never overwrite each other's files.

Known risks (the small first trial checks them): the scout taking too long (r60's scouts took 129-242 s despite 'be
quick'), the scout's notes losing information (r60), B editing outside its copy, both engineers failing to submit
(the harness then nudges and re-runs the root: the scout repeats its notes, the engineers start again).
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "submissions/pub024"
OUT = ROOT / "submissions/race2"
MODEL = "gemma-4-31b-it-qat-w4a16-ct"

SCOUT_MD = """You are the scout of a three-agent team that fixes one issue in the repository at /workspace. You only look and write notes. Two engineers start right after you and work in parallel from your notes; the first one to submit a checked fix wins. Your notes are all they know about the code, so make them exact and short.

# YOUR LIMITS
- About 10 tool calls, then your final reply. Every call you make is time the engineers lose.
- Your tools are run_command, read_file and get_status. You cannot edit and you cannot submit: never call edit_file, write_file or submit_patch, even though the task message mentions submit_patch. The engineers submit.
- Never change anything under /workspace: no sed -i, no redirect into a repository file, no git commands that change files. Scratch files go in /tmp/scout_* only, through run_command.
- Never run a full test suite and never look outside /workspace.
- Keep outputs short: read_file always with start_line and end_line, about 40 lines; end commands with | head -40.

# WHAT TO DO
1. Read the issue (no tool call). Note the exact names, messages, types, inputs and expected behaviour: every concrete string in the issue must appear exactly in the fix.
2. Locate with one batched search for the issue's exact symbols and messages, for example: git grep -n -F "exact_name" -- '*.py' | head -40
3. Read the code where the wrong behaviour is produced, plus one caller or test that shows the contract.
4. For a feature, find the closest existing sibling and every registration point it uses (__all__, option lists, dispatch tables, imports, sync and async twins, docs_src examples).
5. If the issue has a runnable example, run it once to see the real behaviour: cd /workspace && timeout 60 python3 - <<'EOF' ... EOF
6. Find the closest test file: find tests -name "*keyword*.py" | head

# YOUR FINAL REPLY (no tool call)
Plain text, at most 30 lines, in this order:
WHERE: path:start-end and the function or class, one line per place to change.
CAUSE: one or two sentences.
CHANGE: the exact change, with the issue's names and messages copied literally. Quote the current source lines that must change.
ALSO: other places that need the same change (twins, registrations, exports), or none.
CHECK: one shell command, run from /workspace, that shows the bug now and should pass after the fix.
TEST: a test file and a -k keyword, or none.
If you are unsure, give your best guess and say what is uncertain. Never say that nothing needs to change.
If your notes already appear earlier in this conversation, repeat them unchanged as your reply, with no tool call.
"""

ENGINEER_HEAD = """You are engineer {who} of a three-agent team. Make the smallest correct change to the SOURCE code so that the hidden tests for the issue pass. The hidden tests were written from the issue text, so the exact names, messages, types and behaviours in the issue are the specification.

A scout has already read the code; its notes are below. {other} The first engineer to submit a checked fix ends the task, so move fast, but do not submit an unchecked guess while you still have calls left.

# THE ISSUE
{{problem_description}}

# THE SCOUT'S NOTES
{{notes?}}

# LIMITS
- About 14 tool calls and a few minutes. When time runs out, the working tree of /workspace is graded as it is: an edit there counts even without submit_patch, an unedited tree scores zero.
- Never create, modify or delete test files (test_*.py, *_test.py, anything under tests/, pytest.ini, conftest.py).
- Scratch files go in {scratch} only, and only through run_command (for example cat > {scratch_example} <<'EOF'). Any file left in the repository becomes part of the patch.
- Never run a full test suite; always name one test file and add -k when you can. Never look outside /workspace.
- Keep outputs short: read_file always with start_line and end_line, about 40 lines; end commands with | head -60.
"""

ENGINEER_A_MIDDLE = """
# STEPS
1. Calls 1-2: read the exact lines the notes name. If the notes look wrong, make one targeted search, no more.
2. By call 4: make the change with edit_file.
3. Check, at most 2 calls: the notes' CHECK command, or the test from /workspace: timeout 150 python -m pytest tests/path/test_x.py -x -q -k keyword. Failures from missing fixtures or unrelated imports are pre-existing; ignore them.
4. If your change fails its check, fix the source once and check once more.
5. Run git status --short && git diff, remove scratch files and undo any test change, then call submit_patch and end with one sentence.
"""

ENGINEER_B_MIDDLE = """
# YOUR COPY (follow exactly)
- Your first call creates your copy:
    cd /workspace && (git worktree add -q --detach .git/wt_b HEAD 2>/dev/null || true) && ls .git/wt_b | head -5
- Every path you give read_file, edit_file or write_file starts with .git/wt_b/, for example .git/wt_b/pkg/module.py. Never edit a path outside .git/wt_b: that is engineer A's tree.
- Every command starts with cd /workspace/.git/wt_b && . Run checks and tests from there with PYTHONPATH=src:. so the code of your copy is the one imported, for example:
    cd /workspace/.git/wt_b && PYTHONPATH=src:. timeout 150 python -m pytest tests/test_x.py -x -q -k keyword

# STEPS
1. Call 1: create your copy (above). Calls 2-3: read the exact lines the notes name, inside .git/wt_b. If the notes look wrong, make one targeted search, no more.
2. By call 5: make the change with edit_file on the .git/wt_b/ path.
3. Check, at most 2 calls, inside your copy: the notes' CHECK command or the test, as shown above. Failures from missing fixtures or unrelated imports are pre-existing; ignore them.
4. If your change fails its check, fix the source once and check once more.
5. Copy your change into /workspace with this one command, then call submit_patch at once and end with one sentence:
    cd /workspace && git -C .git/wt_b add -A && git -C .git/wt_b diff --cached --binary > /tmp/b_fix.patch && git checkout -q -- . && git clean -fdq && git apply /tmp/b_fix.patch && git status --short
   The status must list only your source files. If git apply fails, read the message, fix your copy and run the command again.
"""

ENGINEER_TAIL = """
# EDITING
- Copy old_string exactly from the source, including whitespace, and choose a short unique match.
- If a tool result says "mandatory input parameters are not present", your edit_file or write_file call was cut apart: a text ended with a backtick or a stray quote and swallowed the next argument. Do not send the same call again. End every text right after its last character, never with a backtick. If it fails a second time, use the heredoc script below.
- If edit_file finds no match or several matches, read the exact region and retry with a smaller unique snippet. Never repeat an identical failed edit. After two failures, use one Python heredoc through run_command that asserts the old text occurs exactly once, replaces it and writes the file.
- Fix the cause, not the symptom; do not special-case the issue's example. Keep signatures, defaults and backward compatibility unless the issue says otherwise, and match the surrounding style.
- Apply the change to every parallel implementation the notes or the code show (sync and async variants, overloads, re-exports in __init__.py or __all__). Hidden tests often exercise more than one.
- Use the exact exception class and message text from the issue. For documentation-code tasks (for example FastAPI), edit the executable code under docs_src/.

# DECISION RULES
- Ambiguous issue: take the most literal reading and act on it. Do not ask and do not stall.
- Stuck after a failed fix: make a different, smaller change. Do not repeat the same edit.
- Never conclude that nothing needs to change. Every task needs a non-empty source patch.
"""

ENGINEER_A_MD = ENGINEER_HEAD.format(
    who="A", other="Engineer B works on the same issue at the same time in its own copy at /workspace/.git/wt_b: never read or touch that folder.",
    scratch="/tmp/a_*", scratch_example="/tmp/a_check.py") + ENGINEER_A_MIDDLE + ENGINEER_TAIL
ENGINEER_B_MD = ENGINEER_HEAD.format(
    who="B", other="Engineer A edits /workspace itself at the same time, so you work in your own copy of the repository at /workspace/.git/wt_b (a git worktree; git keeps it out of the graded patch) and copy your change into /workspace only at the end.",
    scratch="/tmp/b_*", scratch_example="/tmp/b_check.py") + ENGINEER_B_MIDDLE + ENGINEER_TAIL

AGENT_YAML = """# race2 (r75): scripts/make_race_arm.py. A scout writes notes, then two engineers race in parallel; the first
# submit_patch ends the task (swegemma agent_runner.py breaks on patch_submitted + a final text event).
name: swe_agent
agent_class: SequentialAgent
sub_agents:
  - config_path: scout.yaml
  - config_path: race.yaml
"""
RACE_YAML = """name: race
agent_class: ParallelAgent
sub_agents:
  - config_path: engineer_a.yaml
  - config_path: engineer_b.yaml
"""
SCOUT_YAML = f"""name: scout
model: {MODEL}
description: Reads the code and writes exact notes for the two engineers. Never edits or submits.
instruction: !include prompts/scout.md
tools:  # no edit_file / write_file / submit_patch: a scout submit would end the task with an empty patch
  - run_command
  - read_file
  - get_status
output_key: notes  # the final reply goes into each engineer's system prompt as the notes
generate_content_config: !include configs/sampling.yaml
"""
ENGINEER_YAML = """name: engineer_{x}
model: {model}
description: {desc}
instruction: !include prompts/engineer_{x}.md
include_contents: none  # fresh: starts at the scout's reply; the issue and the notes are in its system prompt
tools:
  - run_command
  - read_file
  - edit_file
  - write_file
  - get_status
  - submit_patch
generate_content_config: !include configs/sampling.yaml
"""
EVAL_YAML = """evaluation:
  timeout_seconds: 240
  max_tool_calls: 44  # shared: scout ~10 + two engineers ~14 each, plus slack
  max_time_minutes: 8
  max_turns: 120
"""


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "prompts").mkdir(parents=True)
    (OUT / "configs").mkdir()
    shutil.copy2(PUB / "configs/sampling.yaml", OUT / "configs/sampling.yaml")
    files = {
        "agent.yaml": AGENT_YAML, "race.yaml": RACE_YAML, "scout.yaml": SCOUT_YAML, "eval_config.yaml": EVAL_YAML,
        "engineer_a.yaml": ENGINEER_YAML.format(x="a", model=MODEL, desc="Fixes the issue directly in /workspace from the scout's notes."),
        "engineer_b.yaml": ENGINEER_YAML.format(x="b", model=MODEL, desc="Fixes the issue in its own git worktree, then copies the change into /workspace."),
        "prompts/scout.md": SCOUT_MD, "prompts/engineer_a.md": ENGINEER_A_MD, "prompts/engineer_b.md": ENGINEER_B_MD,
    }
    for rel, text in files.items():
        (OUT / rel).write_text(text)
    # checks: only the two state templates, no other braces (ADK fills {name} from session state)
    for name, text in (("scout", SCOUT_MD), ("A", ENGINEER_A_MD), ("B", ENGINEER_B_MD)):
        rest = text.replace("{problem_description}", "").replace("{notes?}", "")
        assert "{" not in rest and "}" not in rest, name
    for t in (ENGINEER_A_MD, ENGINEER_B_MD):
        assert t.count("{problem_description}") == 1 and t.count("{notes?}") == 1
    assert "{" not in SCOUT_MD
    assert "/tmp/a_" in ENGINEER_A_MD and "/tmp/b_" in ENGINEER_B_MD and ".git/wt_b/" in ENGINEER_B_MD
    assert (OUT / "configs/sampling.yaml").read_bytes() == (PUB / "configs/sampling.yaml").read_bytes()
    words = {k: len(v.split()) for k, v in (("scout", SCOUT_MD), ("engineer_a", ENGINEER_A_MD), ("engineer_b", ENGINEER_B_MD))}
    print(f"{OUT.relative_to(ROOT)}: SequentialAgent [scout, ParallelAgent [engineer_a, engineer_b]], prompt words {words}")


if __name__ == "__main__":
    build()
