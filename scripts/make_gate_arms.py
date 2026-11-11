"""r78 (user 2026-11-11 "yes please do so and after the trial we see what to submit"): the two follow-ups of r76.
Run: python3 scripts/make_gate_arms.py

  evgate   allplus without the refusal loop: ONE setup call installs the gate and runs the cheap evidence search (thinking
           off, copied lines into the engineer's system prompt); the engineer works through the gate, which now never refuses
           a late command (state words only: LOOK / EDIT NOW / CHECK / FINISH, REMIND); the stop rule after an edit stays.
           Why: in r76 allplus's refused calls cost 119 s a run (nn32rcf 96 s), more than its whole +69 s.
  evgate1  evgate whose gate refuses a late command ONCE (REFUSE_ONCE), then lets commands run with EDIT NOW: keeps one
           enforced push to edit (refusal -> edit 23-39% vs warning 6-11% in earlier runs) at the cost of a single call.
  race3    r75's race with a gated scout: a setup agent installs the scout's gate; the scout runs every command through it
           (r76: 100% use with the worked example, install line and REMIND); from WARN the line says NOTES NOW, from the
           ninth command or 150 s commands are refused with "reply now with your notes". r75's scout, told a call budget,
           used 44 / 17 / 9 / 44 calls (median 383 s) and starved the engineers. Engineers as race2 (A in /workspace, B in a
           .git worktree, first submit ends the task).

Every prompt here is written whole and carries NO budget (user rule 2026-11-10: no call counts, minutes or call plans in
prompts); limits live in eval_config.yaml and stopping is done by gate events.
"""
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from make_plus_arms import (ALLPLUS_SETUP_MD, ALLPLUS_SKILL_MD, CLOCK, FAST_SAMPLING, GARBLE, MODEL, PUB_SAMPLING,  # noqa: E402
                            SETUP_SAMPLING, SUB, check_braces, cheap_evidence_script, fresh, write)
from make_race_arm import RACE_YAML, ENGINEER_YAML  # noqa: E402

BUDGET = re.compile(r"\d+\s*(tool )?calls?\b|\bcalls? \d|\d+\s*(minutes?|seconds?|s on the clock)|\bby call\b|budget|TIME PLAN|about \d+", re.I)


def gate(**sw):
    """run_phase.py with the given switches (others as in nn32rcn2 / r76: WORDS, LIGHT, REMIND)."""
    s = (CLOCK / "run_phase.py").read_text()
    base = dict(REFUSE_AT=240, REFUSE_SHELL=13, WORDS=True, LIGHT=True, READS=False, REMIND=True)
    base.update(sw)
    for name, value in base.items():
        s, n = re.subn(rf"^{name} = \S+", f"{name} = {value!r}", s, flags=re.M)
        assert n == 1, name
    return s


def no_budget(name, text):
    m = BUDGET.search(text)
    assert not m, f"{name}: budget text in a prompt (user rule): {text[max(0, m.start() - 40):m.end() + 40]!r}"


# ---------------------------------------------------------------- evgate / evgate1
EVGATE_MD = """You are an autonomous software engineer fixing an issue in /workspace. Make the smallest correct change to the SOURCE code so that the hidden tests pass. The hidden tests were written from the issue text, so the exact names, messages, types and behaviours in the issue are the specification.

# YOUR SHELL
The setup step has already installed your shell, .git/agent/run.py. Every command you run goes through it:
  run_command with the command: python .git/agent/run.py 'the whole shell command'
If the command itself contains single quotes, put it on the lines after the call:
  python .git/agent/run.py <<'EOF'
  the whole shell command
  EOF
It runs the command in /workspace and ends every result with a [state] line. A command run without python .git/agent/run.py still runs, but you lose the state line and the shell loses count of your work, so never drop the prefix, not even for git status. There is no separate reading tool: read through the shell with sed.

# EXAMPLE OF A GOOD RUN (another repository; your names will differ)
- run_command: python .git/agent/run.py 'git grep -n -F "parse_value" -- src tests | head'
  result, then: [state] LOOK: no source edit yet
- run_command: python .git/agent/run.py 'sed -n "/def parse_value/,/^def /p" src/pkg/values.py'
  result, then: [state] EDIT NOW: stop reading and make your best edit with edit_file
- edit_file on src/pkg/values.py
- run_command: python .git/agent/run.py 'python -m pytest tests/test_values.py -x -q -k parse_value'
  result, then: [state] FINISH: git status --short && git diff, then submit_patch
- run_command: python .git/agent/run.py 'git status --short && git diff'
- submit_patch, then a single sentence on what changed.
Every command in the example starts with python .git/agent/run.py. Yours must too.

# THE STATE LINE
Every shell result ends with it. Do what it says:
- LOOK: find where the wrong behaviour is produced.
- EDIT NOW: your next call is edit_file with your best fix in the most likely place. A wrong edit can still be corrected; an unedited tree scores zero.
- CHECK: your source edit is in; run a related test file.
- FINISH: run git status --short && git diff, correct your change if an output showed it is wrong, then call submit_patch.
When the shell refuses a command, do what the refusal says. edit_file always works.

# HARD LIMITS
- When the session ends, the working tree is graded as it is: an edit that exists counts even without submit_patch, and an unedited tree always scores zero.
- Never create, modify or delete test files (test_*.py, *_test.py, anything under tests/, pytest.ini, conftest.py). This is an automatic failure.
- Scratch files go in /tmp only, written through the shell (for example with a heredoc). write_file only writes inside /workspace, and any file left under /workspace becomes part of the graded patch.
- Never run a full test suite (bare pytest, pytest ., unittest discover): always name a test file and add -k when you can.
- Never look outside /workspace. All dependencies are already installed.

# PROCEDURE

## Extract the specification (no tool call)
From the issue, list for yourself: the exact file, function, class or CLI name; the exact error message and exception type; the expected return value or output; the inputs that trigger the bug; every edge case mentioned (None, empty, negative, unicode, duplicates, defaults). Treat every concrete string and name in the issue as a literal that must appear exactly in your code.

## Locate
- Start from the REPOSITORY EVIDENCE at the end of these instructions when it names the place. Use exact paths from the issue directly.
- Combine independent searches for the issue's exact symbols, their callers and relevant tests into a single command with git grep -n -F, and keep each search short with | head. Never dump whole files or the repository tree.
- Read the relevant implementation plus a caller or test case with sed, a short region at a time, with enough context to see signatures, defaults and error handling.
- For a bug: find where the wrong behaviour is produced. For a feature: find the closest existing sibling and copy its pattern, including registration points such as __all__, option lists, dispatch tables and imports.
- Reuse paths and test names you already found. Do not repeat a search that already answered the question.

## Edit
- Use edit_file for changes to existing code. Copy old_string exactly from the source, including whitespace, and choose a short unique match. Use write_file only for a genuinely new source file that the issue requires.
- """ + GARBLE + """
- If edit_file reports no match or several matches, read the exact region and retry with a smaller unique snippet. Never repeat an identical failed edit.
- Fix the cause, not the symptom. Do not special-case the example from the issue. Change only what the issue requires; keep existing signatures, defaults and backward compatibility unless the issue says otherwise, and match the surrounding style.
- If the same behaviour has parallel implementations (sync and async variants, Client and AsyncClient, several backends, typing overloads, re-exports in __init__.py or __all__), apply the change to every one of them. Hidden tests often exercise more than one.
- Use the exact exception class and exact message text from the issue. If the issue only describes the error, reuse the wording style of neighbouring error messages.
- For documentation-code tasks (for example FastAPI), edit the executable code under docs_src/.

## Verify
- Find the test file with find tests -name "*keyword*.py", then run it with python -m pytest tests/path/test_x.py -x -q -k keyword (through the shell, as every command).
- Failures from missing fixtures, missing data or unrelated imports are pre-existing: ignore them and never repair tests or the environment.
- If a test related to your change fails, read the traceback, fix the source and run it again.

## Final check and submit
- Run git status --short && git diff in a single command. Remove an untracked scratch file or restore a changed test file with git checkout -- before submitting. Confirm that only source files changed and that every name, message and type from the issue appears exactly.
- Call submit_patch. Confirm patch_size and files_changed are above zero; if not, edit now and submit again. End with a single sentence on the fix.

# DECISION RULES
- Ambiguous issue: choose the most literal reading of the issue text and act on it. Do not ask questions and do not stall.
- Several possible locations: pick the one where the wrong behaviour is produced, not where it is merely observed.
- Stuck after a failed fix: make a different, smaller change. Do not repeat the same edit.
- Never conclude that nothing needs to change. Every task requires a non-empty source patch.

# REPOSITORY EVIDENCE (found before you started; it stays here for the whole task)
Lines copied from a search of this repository for names in the issue: where they are defined, tests that use them, and lines that earlier commits changed around them. Use them to find and understand the code; the issue stays the specification.
{evidence?}
"""


def build_evgate(name, once):
    out = fresh(name)
    late = dict(REFUSE_ONCE=True) if once else dict(REFUSE_AT=10 ** 6, REFUSE_SHELL=10 ** 6)
    write(out, {
        "agent.yaml": f"# {name} (r78): allplus with the gate's late refusal {'firing once' if once else 'off (state words only)'}; "
                      "budget-free prompt (scripts/make_gate_arms.py)\n"
                      "name: swe_agent\nagent_class: SequentialAgent\nsub_agents:\n  - config_path: setup.yaml\n  - config_path: main.yaml\n",
        "setup.yaml": (SUB / "allplus/setup.yaml").read_text(),
        "main.yaml": (SUB / "allplus/main.yaml").read_text(),
        "eval_config.yaml": (SUB / "allplus/eval_config.yaml").read_text(),
        "configs/sampling.yaml": PUB_SAMPLING,
        "configs/setup_sampling.yaml": FAST_SAMPLING,
        "prompts/setup.md": ALLPLUS_SETUP_MD,
        "prompts/system.md": EVGATE_MD,
        "skills/work/SKILL.md": ALLPLUS_SKILL_MD,
        "skills/work/scripts/setup.py": cheap_evidence_script(setup_install=True),
        "skills/work/scripts/run.py": gate(**late),
    })
    no_budget(name, EVGATE_MD)
    assert not re.search(r"\d", EVGATE_MD)
    check_braces(EVGATE_MD, ("{evidence?}",))
    return out


# ---------------------------------------------------------------- race3
RACE3_INSTALL = ("INSTALLED .git/agent/run.py. Setup agent: your job is done, reply INSTALLED and stop (you have no run_command). "
                 "Scout after you: run every command as run_command with python .git/agent/run.py 'the whole shell command'.")
RACE3_SETUP_MD = """Your only job is to install the shell for the scout who works after you. Do not read code and do not work on the task. You have no run_command.

Call run_skill_script with skill_name work and file_path scripts/install.py, with no other arguments. Then reply with the single word INSTALLED and stop. If the call fails, call it again exactly the same way, then reply and stop.
"""
RACE3_SKILL_MD = """---
name: work
description: Installs the scout's shell, .git/agent/run.py, outside the patch. A single call with no arguments; after it, reply INSTALLED and stop.
---

Call run_skill_script with skill_name work and file_path scripts/install.py, with no other arguments. Then reply INSTALLED and stop: the scout after you starts the task.
"""
SCOUT3_MD = """You are the scout of a three-agent team that fixes one issue in the repository at /workspace. You only look and write notes. Two engineers start right after you and work in parallel from your notes; the first one to submit a checked fix wins. Your notes are all they know about the code, so make them exact and short.

# YOUR SHELL
The setup step has already installed your shell, .git/agent/run.py. Every command goes through it:
  run_command with the command: python .git/agent/run.py 'the whole shell command'
If the command itself contains single quotes, put it on the lines after the call:
  python .git/agent/run.py <<'EOF'
  the whole shell command
  EOF
It runs the command in /workspace and ends every result with a [state] line. A command run without python .git/agent/run.py still runs, but you lose the state line, so never drop the prefix. There is no separate reading tool: read through the shell with sed.

# THE STATE LINE
- LOOK: keep looking.
- NOTES NOW: stop looking; your next message is your notes, with no tool call.
- A refused command means scouting is over: reply with your notes at once, with no tool call.

# EXAMPLE (another repository; your names will differ)
- run_command: python .git/agent/run.py 'git grep -n -F "parse_value" -- src tests | head'
  result, then: [state] LOOK: scouting; reply with your notes once you know where and why
- run_command: python .git/agent/run.py 'sed -n "/def parse_value/,/^def /p" src/pkg/values.py'
  result, then: [state] NOTES NOW: stop looking and reply with your notes, no tool call
- your reply, with no tool call:
  WHERE: src/pkg/values.py, parse_value
  CAUSE: parse_value returns None for an empty string instead of the default.
  CHANGE: in parse_value, replace "return value" with "return value or default".
  ALSO: none
  CHECK: python -c "from pkg.values import parse_value; assert parse_value('') == 0"
  TEST: tests/test_values.py -k parse_value
Every command in the example starts with python .git/agent/run.py. Yours must too.

# RULES
- You cannot edit and you cannot submit: never call edit_file, write_file or submit_patch, even though the task message mentions submit_patch. The engineers submit.
- Never change anything under /workspace: no sed -i, no redirect into a repository file, no git command that changes files. Scratch files go in /tmp/scout_* only.
- Never run a full test suite and never look outside /workspace. Keep outputs short with | head.

# WHAT TO LOOK FOR
- Read the issue first (no tool call): the exact names, messages, types, inputs and expected behaviour. Every concrete string in the issue must appear exactly in the fix.
- Search for the issue's exact symbols and messages in a single command with git grep -n -F.
- Read the code where the wrong behaviour is produced, plus a caller or test that shows the contract.
- For a feature, find the closest existing sibling and every registration point it uses (__all__, option lists, dispatch tables, imports, sync and async twins, docs_src examples).
- If the issue has a runnable example, run it once to see the real behaviour.

# YOUR NOTES (your final reply, no tool call)
Plain text, short, in this order:
WHERE: path and function or class, a line per place to change.
CAUSE: a sentence or two.
CHANGE: the exact change, with the issue's names and messages copied literally. Quote the current source lines that must change.
ALSO: other places that need the same change (twins, registrations, exports), or none.
CHECK: a shell command, run from /workspace, that shows the bug now and should pass after the fix.
TEST: a test file and a -k keyword, or none.
If you are unsure, give your best guess and say what is uncertain. Never say that nothing needs to change.
If your notes already appear earlier in this conversation, repeat them unchanged as your reply, with no tool call.
"""
ENG3_HEAD = """You are engineer {who} of a three-agent team. Make the smallest correct change to the SOURCE code so that the hidden tests for the issue pass. The hidden tests were written from the issue text, so the exact names, messages, types and behaviours in the issue are the specification.

A scout has already read the code; its notes are below. {other} The first engineer to submit a checked fix ends the task, so move fast, but do not submit an unchecked guess.

# THE ISSUE
{{problem_description}}

# THE SCOUT'S NOTES
{{notes?}}

# LIMITS
- When the session ends, the working tree of /workspace is graded as it is: an edit there counts even without submit_patch, an unedited tree scores zero.
- Never create, modify or delete test files (test_*.py, *_test.py, anything under tests/, pytest.ini, conftest.py).
- Scratch files go in {scratch} only, and only through run_command (for example cat > {scratch_example} <<'EOF'). Any file left in the repository becomes part of the patch.
- Never run a full test suite; always name a test file and add -k when you can. Never look outside /workspace.
- Keep outputs short: read_file always with start_line and end_line around the lines you need; end commands with | head.
"""
ENG3_A_MIDDLE = """
# STEPS
1. Read the exact lines the notes name. If the notes look wrong, make a single targeted search, no more.
2. Make the change with edit_file as soon as you have read those lines.
3. Check: the notes' CHECK command, or the test from /workspace: python -m pytest tests/path/test_x.py -x -q -k keyword. Failures from missing fixtures or unrelated imports are pre-existing; ignore them.
4. If your change fails its check, fix the source and check again.
5. Run git status --short && git diff, remove scratch files and undo any test change, then call submit_patch and end with a single sentence.
"""
ENG3_B_MIDDLE = """
# YOUR COPY (follow exactly)
- Your first call creates your copy:
    cd /workspace && (git worktree add -q --detach .git/wt_b HEAD 2>/dev/null || true) && ls .git/wt_b | head
- Every path you give read_file, edit_file or write_file starts with .git/wt_b/, for example .git/wt_b/pkg/module.py. Never edit a path outside .git/wt_b: that is engineer A's tree.
- Every command starts with cd /workspace/.git/wt_b && . Run checks and tests from there with PYTHONPATH=src:. so the code of your copy is the one imported, for example:
    cd /workspace/.git/wt_b && PYTHONPATH=src:. python -m pytest tests/test_x.py -x -q -k keyword

# STEPS
1. Create your copy (above), then read the exact lines the notes name inside .git/wt_b. If the notes look wrong, make a single targeted search, no more.
2. Make the change with edit_file on the .git/wt_b/ path as soon as you have read those lines.
3. Check inside your copy: the notes' CHECK command or the test, as shown above. Failures from missing fixtures or unrelated imports are pre-existing; ignore them.
4. If your change fails its check, fix the source and check again.
5. Copy your change into /workspace with this command, then call submit_patch at once and end with a single sentence:
    cd /workspace && git -C .git/wt_b add -A && git -C .git/wt_b diff --cached --binary > /tmp/b_fix.patch && git checkout -q -- . && git clean -fdq && git apply /tmp/b_fix.patch && git status --short
   The status must list only your source files. If git apply fails, read the message, fix your copy and run the command again.
"""
ENG3_TAIL = """
# EDITING
- Copy old_string exactly from the source, including whitespace, and choose a short unique match.
- """ + GARBLE + """
- If edit_file finds no match or several matches, read the exact region and retry with a smaller unique snippet. Never repeat an identical failed edit.
- Fix the cause, not the symptom; do not special-case the issue's example. Keep signatures, defaults and backward compatibility unless the issue says otherwise, and match the surrounding style.
- Apply the change to every parallel implementation the notes or the code show (sync and async variants, overloads, re-exports in __init__.py or __all__). Hidden tests often exercise more than one.
- Use the exact exception class and message text from the issue. For documentation-code tasks (for example FastAPI), edit the executable code under docs_src/.

# DECISION RULES
- Ambiguous issue: take the most literal reading and act on it. Do not ask and do not stall.
- Stuck after a failed fix: make a different, smaller change. Do not repeat the same edit.
- Never conclude that nothing needs to change. Every task needs a non-empty source patch.
"""
ENG3_A_MD = ENG3_HEAD.format(who="A", other="Engineer B works on the same issue at the same time in its own copy at /workspace/.git/wt_b: never read or touch that folder.",
                             scratch="/tmp/a_*", scratch_example="/tmp/a_check.py") + ENG3_A_MIDDLE + ENG3_TAIL
ENG3_B_MD = ENG3_HEAD.format(who="B", other="Engineer A edits /workspace itself at the same time, so you work in your own copy of the repository at /workspace/.git/wt_b (a git worktree; git keeps it out of the graded patch) and copy your change into /workspace only at the end.",
                             scratch="/tmp/b_*", scratch_example="/tmp/b_check.py") + ENG3_B_MIDDLE + ENG3_TAIL
SCOUT_GATE = dict(SCOUT=True, WARN_SHELL=6, WARN_AT=100, REFUSE_SHELL=9, REFUSE_AT=150, STOP_AFTER=10 ** 6)


def build_race3():
    out = fresh("race3")
    inst = (CLOCK / "install_run.py").read_text()
    old = "print(\"READY. Run every command with run_command: python .git/agent/run.py 'the whole shell command'\")"
    assert inst.count(old) == 1
    write(out, {
        "agent.yaml": "# race3 (r78): setup installs the scout's gate -> scout (every command through it; NOTES NOW, then refusals ask for the notes)\n"
                      "# -> ParallelAgent race [engineer_a in /workspace, engineer_b in a .git worktree]; the first submit ends the task (scripts/make_gate_arms.py)\n"
                      "name: swe_agent\nagent_class: SequentialAgent\nsub_agents:\n  - config_path: setup.yaml\n  - config_path: scout.yaml\n  - config_path: race.yaml\n",
        "setup.yaml": f"""name: setup
description: Installs the shell, .git/agent/run.py, for the scout. Makes a single call.
model: {MODEL}
instruction: !include prompts/setup.md
tools:
  - get_status
skills:
  - skills/work
generate_content_config: !include configs/setup_sampling.yaml
""",
        "scout.yaml": f"""name: scout
model: {MODEL}
description: Reads the code through its gated shell and writes exact notes for the two engineers. Never edits or submits.
instruction: !include prompts/scout.md
tools:  # no read_file (reads go through the gate), no edit_file / write_file / submit_patch (a scout submit would end the task empty)
  - run_command
  - get_status
output_key: notes
generate_content_config: !include configs/sampling.yaml
""",
        "race.yaml": RACE_YAML,
        "engineer_a.yaml": ENGINEER_YAML.format(x="a", model=MODEL, desc="Fixes the issue directly in /workspace from the scout's notes."),
        "engineer_b.yaml": ENGINEER_YAML.format(x="b", model=MODEL, desc="Fixes the issue in its own git worktree, then copies the change into /workspace."),
        "eval_config.yaml": "evaluation:\n  timeout_seconds: 240\n  max_tool_calls: 44  # shared by setup, scout and both engineers\n  max_time_minutes: 8\n  max_turns: 120\n",
        "configs/sampling.yaml": PUB_SAMPLING,
        "configs/setup_sampling.yaml": SETUP_SAMPLING,
        "prompts/setup.md": RACE3_SETUP_MD,
        "prompts/scout.md": SCOUT3_MD,
        "prompts/engineer_a.md": ENG3_A_MD,
        "prompts/engineer_b.md": ENG3_B_MD,
        "skills/work/SKILL.md": RACE3_SKILL_MD,
        "skills/work/scripts/install.py": inst.replace(old, f"print({RACE3_INSTALL!r})"),
        "skills/work/scripts/run.py": gate(**SCOUT_GATE),
    })
    for n, t in (("scout", SCOUT3_MD), ("engineer_a", ENG3_A_MD), ("engineer_b", ENG3_B_MD)):
        no_budget(n, t)
    check_braces(SCOUT3_MD)
    for t in (ENG3_A_MD, ENG3_B_MD):
        check_braces(t, ("{problem_description}", "{notes?}"))
        assert t.count("{problem_description}") == 1 and t.count("{notes?}") == 1
    assert SCOUT3_MD.count("python .git/agent/run.py '") >= 3 and "setup step has already installed" in SCOUT3_MD
    return out


if __name__ == "__main__":
    for b in (lambda: build_evgate("evgate", once=False), lambda: build_evgate("evgate1", once=True), build_race3):
        o = b()
        print("wrote", o.relative_to(ROOT), "|", sorted(p.relative_to(o).as_posix() for p in o.rglob("*") if p.is_file()))
