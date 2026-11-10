"""r76 (user 2026-11-10: "lets make the agent of the nn32rc family + evid3 cheaper + sq1c2t7 on run_command in one run as well
as trying to merge all the pluses of table in a single agent"). Run: python3 scripts/make_plus_arms.py

Evidence (docs/PLAN.md "RACE / BEST-OF-K", "MINING 2026-11-10b", "COMBINE 2026-11-10"; scripts/mine_bank/arm_table.py):
  forced edit   nn32 / nn36p 11 vs 7 solved over 42 pairs, no-patch 7 / 4 vs 21; combo1en +2/-0, combo1en2 +2/-2 vs combo1.
                The skill-shell versions timed out on the LB. LB fit rule from our submissions: ONE skill call (an install)
                + run_command fits (sk_a2 0.18, nn32rcn2 0.12); every command through a skill timed out (sq1c2, sq1c2t7,
                srep7, nn32). The run_command versions (nn32rc family, 64 runs) lost the gain because only 24% of commands
                went through .git/agent/run.py (317 of 1,309); after a refusal the model never bypassed it (0 of 57 next
                calls were a direct command). So the problem is adoption, not escape.
  evidence      evid3 15 vs 11 over 44 pairs (+6/-2), +26 s, timed out on the LB. Its script runs git log -S over the whole
                history with a 40 s deadline (large private repos) and the stage thinks before 2-3 replies.
  clock         sq1c2t7 18 vs 15 of 24 (+6/-3), -9 s; timed out on the LB (80 calls, every command a skill call).
  zero-cost     combo1's garbled-edit rule (13/45 -> 1/42 broken edit calls), /tmp scratch line, no graph tools.
  steering      a tool-output line moves the model ~4x more than the same rule in the prompt (r58); one worked example
                took heredoc use from 4 to 19 (r69).

Arms (combo1 is the same-run control):
  nn32rcf  nn32rcn2 (setup agent installs the gate; main agent: run_command through .git/agent/run.py, no read_file, gate
           REFUSE_AT 240 s / 13th command, stop rule, state words) + adoption measures: (1) a worked example in the prompt in
           which every command carries the prefix, (2) the install line names the engineer's command form (r57's READY line
           gave 42% early use, r58's 'your job is done' line 8%) while telling the setup agent to stop, (3) REMIND: every
           gate output ends with the prefix. Prompt written fresh (nn32rcn2's content, no digits or number words as nn32).
  evidc    evid3 made cheap, fixer = combo1: the evidence stage runs with thinking off, the script's deadline is 8 s (4 s per
           git call) and git log -S only looks at the last 500 commits; the stage copies at most 10 lines. combo1's prompt
           + the evidence section (as evid3 added it to pub024: the only difference from the control is the evidence).
  t7rc     sq1c2t7 on run_command: setup agent installs its clock script (start time cached, command on stdin, as clock_rc),
           32 calls (was 80), 7 min, the same three adoption measures. Fixer prompt written fresh from sq1c2t7's.
  allplus  everything with a plus in one agent: ONE setup call installs the gate and runs the cheap evidence search (thinking
           off; its copied lines go into the engineer's system prompt), then an engineer on combo1's contract and edit rules
           with the gate's state words, the worked example, REMIND, no read_file, no graph tools. 32 calls, 8 min.
"""
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from make_combo_arm import SYSTEM_MD as COMBO1_MD  # noqa: E402  (combo1's prompt, byte for byte)

SUB = ROOT / "submissions"
CLOCK = ROOT / "scripts/agent_clock"
MODEL = "gemma-4-31b-it-qat-w4a16-ct"
PUB_SAMPLING = (SUB / "pub024/configs/sampling.yaml").read_text()
NUMBER_WORDS = re.compile(r"\b(one|two|three|four|five|six|seven|eight|nine|ten|twenty|thirty|hundred|seconds?|minutes?)\b", re.I)

# ---------------------------------------------------------------- shared pieces
SETUP_MD = """Your only job is to install the shell for the engineer who works after you. Do not read code and do not work on the task. You have no run_command.

Call run_skill_script with skill_name work and file_path scripts/install.py, with no other arguments. Then reply with the single word INSTALLED and stop. If the call fails, call it again exactly the same way, then reply and stop.
"""
SETUP_SKILL_MD = """---
name: work
description: Installs the engineer's shell, .git/agent/run.py, outside the patch. A single call with no arguments; after it, reply INSTALLED and stop.
---

Call run_skill_script with skill_name work and file_path scripts/install.py, with no other arguments. Then reply INSTALLED and stop: the engineer after you does the task.
"""
INSTALL_LINE = ("INSTALLED .git/agent/run.py. Setup agent: your job is done, reply INSTALLED and stop (you have no run_command). "
                "Engineer after you: run every command as run_command with python .git/agent/run.py 'the whole shell command'.")
SETUP_YAML = f"""name: setup
description: Installs the shell, .git/agent/run.py, for the engineer. Makes a single call.
model: {MODEL}
instruction: !include prompts/setup.md
tools:
  - get_status
skills:
  - skills/work
generate_content_config: !include configs/setup_sampling.yaml
"""
SETUP_SAMPLING = """# setup step: a single tool call, no reasoning needed (as nn32rcn2)
temperature: 0.2
top_p: 0.95
max_output_tokens: 512
thinking_config:
  include_thoughts: true
  thinking_budget: 128
"""
FAST_SAMPLING = """# r76 cheap evidence stage: thinking off; a mechanical job (pick names, call the script once, copy lines).
# In the installed harness (adk_submission 0.2.13, resolvers/generation.py) any thinking_budget > 0 turns thinking ON and a
# missing budget is filled with 4096, so include_thoughts: false alone does not switch it off; thinking_budget: 0 does
# (schema ge=0, limits 0-32768; the request then carries enable_thinking false and no thinking_token_budget).
temperature: 0.2
top_p: 0.95
max_output_tokens: 1024
thinking_config:
  thinking_budget: 0
  include_thoughts: false
"""
GARBLE = ("If a tool result says \"mandatory input parameters are not present\", your edit_file or write_file call was cut apart: "
          "a text ended with a backtick or a stray quote and swallowed the next argument. Do not send the same call again. End every "
          "text right after its last character, never with a backtick. If it fails again, make the change with an inline "
          "python script through the shell (a quoted heredoc that asserts the old text occurs exactly once, replaces it and writes the file).")


def gate_script(remind=True):
    """run_phase.py as nn32rcn2 ran it (REFUSE_AT 240, REFUSE_SHELL 13, WORDS, LIGHT) + REMIND."""
    s = (CLOCK / "run_phase.py").read_text()
    for name, value in (("REFUSE_AT", 240), ("REFUSE_SHELL", 13), ("WORDS", True), ("LIGHT", True), ("READS", False), ("REMIND", remind)):
        s, n = re.subn(rf"^{name} = \S+", f"{name} = {value!r}", s, flags=re.M)
        assert n == 1, name
    return s


def install_script():
    s = (CLOCK / "install_run.py").read_text()
    old = "print(\"READY. Run every command with run_command: python .git/agent/run.py 'the whole shell command'\")"
    assert s.count(old) == 1
    return s.replace(old, f"print({INSTALL_LINE!r})")


def fresh(name):
    out = SUB / name
    if out.exists():
        shutil.rmtree(out)
    (out / "prompts").mkdir(parents=True)
    (out / "configs").mkdir()
    return out


def write(out, files):
    for rel, text in files.items():
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)


def check_braces(text, allowed=()):
    rest = text
    for a in allowed:
        rest = rest.replace(a, "")
    assert "{" not in rest and "}" not in rest, text[:80]


# ---------------------------------------------------------------- nn32rcf
NN32RCF_MD = """You are an autonomous software engineer fixing an issue in /workspace. Make the smallest correct change to the source code so that the hidden tests pass. Those tests were written from the issue, so its exact names, messages, types and behaviour are the specification.

# Your shell
The setup step has already installed your shell, .git/agent/run.py. Every command you run goes through it:
  run_command with the command: python .git/agent/run.py 'the whole shell command'
If the command itself contains single quotes, put it on the lines after the call:
  python .git/agent/run.py <<'EOF'
  the whole shell command
  EOF
The shell runs the command in /workspace and ends every result with a [state] line. A command run without python .git/agent/run.py still runs, but you lose the state line and the shell loses count of your work, so never drop the prefix, not even for a quick git status.

# Example of a good run (another repository; your names will differ)
- run_command: python .git/agent/run.py 'git grep -n -F "parse_value" -- src tests | head'
  result, then: [state] LOOK: no source edit yet
- run_command: python .git/agent/run.py 'sed -n "/def parse_value/,/^def /p" src/pkg/values.py'
  result, then: [state] LOOK: no source edit yet
- edit_file on src/pkg/values.py
- run_command: python .git/agent/run.py 'python -m pytest tests/test_values.py -x -q -k parse_value'
  result, then: [state] FINISH: git status --short && git diff, then submit_patch
- run_command: python .git/agent/run.py 'git status --short && git diff'
- submit_patch, then a single sentence on what changed.
Every command in the example starts with python .git/agent/run.py. Yours must too.

# Tools
- To read a file, use the shell with sed -n 'START,ENDp' FILE or a pattern range as in the example. There is no other reading tool.
- edit_file changes a file: old_string is short, unique and copied exactly from the source. write_file only for a new source file the issue requires.
- """ + GARBLE + """

# The state line
Every shell result ends with a [state] line. Do what it says:
- LOOK: find where the wrong behaviour is produced.
- EDIT NOW: stop reading and make your best edit with edit_file. A wrong edit can be corrected; an unedited tree scores zero.
- CHECK: run a related test file.
- FINISH: run git status --short && git diff, correct your change if an output showed it is wrong, then call submit_patch.
When the shell refuses a command, do what the refusal says. edit_file always works.

# How to work
List for yourself the exact names, messages, inputs and edge cases in the issue. Search for those names with git grep -n -F, then read the implementation and a caller or test. Reuse what you found instead of searching again. Do not write scratch scripts before your edit.
Fix the cause where the wrong behaviour is produced. Keep signatures and defaults unless the issue says otherwise. Use the exact exception class and message from the issue. When the same behaviour has parallel implementations, such as sync and async variants or re-exports, change all of them. For a feature, copy the closest existing sibling, including registration points such as __all__, option lists and imports.

To run a test: python -m pytest tests/path/test_x.py -x -q -k keyword. Failures unrelated to your change are not yours to fix. If a related test fails, correct the source and run it again.

# Rules
- Never create, change or delete test files or test configuration.
- Scratch files go in /tmp only, written through the shell (for example with a heredoc). write_file only writes inside /workspace, and any new file there becomes part of the patch.
- Never run a whole test suite, and never look outside /workspace.
- Every task needs a non-empty source patch. Finish with a single sentence on what you changed.
"""


def build_nn32rcf():
    out = fresh("nn32rcf")
    write(out, {
        "agent.yaml": "# nn32rcf (r76): nn32rcn2 + adoption measures for the run_command gate (scripts/make_plus_arms.py)\n"
                      "name: swe_agent\nagent_class: SequentialAgent\nsub_agents:\n  - config_path: setup.yaml\n  - config_path: main.yaml\n",
        "setup.yaml": SETUP_YAML,
        "main.yaml": f"""# main: run_command runs .git/agent/run.py (the gate); no read_file, so reads go through the gate too
name: main
model: {MODEL}
instruction: !include prompts/system.md
tools:
  - run_command
  - edit_file
  - write_file
  - get_status
  - submit_patch
generate_content_config: !include configs/sampling.yaml
""",
        "eval_config.yaml": (SUB / "nn32rcn2/eval_config.yaml").read_text(),
        "configs/sampling.yaml": (SUB / "nn32rcn2/configs/sampling.yaml").read_text(),
        "configs/setup_sampling.yaml": SETUP_SAMPLING,
        "prompts/setup.md": SETUP_MD,
        "prompts/system.md": NN32RCF_MD,
        "skills/work/SKILL.md": SETUP_SKILL_MD,
        "skills/work/scripts/install.py": install_script(),
        "skills/work/scripts/run.py": gate_script(),
    })
    assert not re.search(r"\d", NN32RCF_MD) and not NUMBER_WORDS.search(NN32RCF_MD), "nn32 design: no digits or number words"
    assert NN32RCF_MD.count("python .git/agent/run.py '") >= 5 and "setup step has already installed" in NN32RCF_MD
    check_braces(NN32RCF_MD)
    return out


# ---------------------------------------------------------------- evidence (cheap)
EVID_MD = """Your only job is one search of the repository for the agent who fixes the issue after you. Your reply is copied into that agent's instructions and stays in front of it for the whole task, so it must hold real lines from the repository, not your opinions. You will not read code and you will not work on the fix.

Choose two to four exact names from the issue below that the fix most likely touches: functions, methods, classes, options or parameters, written exactly as they appear in the issue or as they would appear in the code. Prefer the most specific names, such as convert_underscores, over common words, such as Header.

Call run_skill_script with skill_name evidence, file_path scripts/evidence.py and positional_args holding those names, one name per item. That is your only call.

Then reply with the lines of its result that best show where the fix belongs and how this code is meant to behave: where the names are defined, tests that use them, and the lines an earlier commit changed around them. Copy each line exactly as it was printed, with its file:line or commit, at most 10 lines and nothing else. If nothing in the result bears on the issue, reply with the single line NOTHING RELEVANT.

# THE ISSUE (verbatim)
{problem_description}"""
EVID_SECTION = """
# REPOSITORY EVIDENCE (found before you started; it stays here for the whole task)
Lines copied from a search of this repository for names in the issue: where they are defined, tests that use them, and lines that earlier commits changed around them. Use them to find and understand the code; the issue stays the specification.
{evidence?}
"""
HISTORY_COMMITS = 500


def cheap_evidence_script(setup_install=False):
    """evid3's evidence.py, cheaper: 8 s deadline, 4 s per git call, git log -S only over the last HISTORY_COMMITS commits,
    at most 10 copied lines. setup_install (allplus): the same call first installs the gate as .git/agent/run.py."""
    s = (SUB / "evid3/skills/evidence/scripts/evidence.py").read_text()
    reps = [
        ("DEADLINE = 40  # seconds for all sections; the rest is skipped with a note\n",
         "DEADLINE = 8  # r76: seconds for all sections (evid3: 40; large private repos made it the stage's main cost)\n"),
        ("CALL_TIMEOUT = 12  # seconds per git call\n", "CALL_TIMEOUT = 4  # seconds per git call (evid3: 12)\n"),
        ("REPLY = 'Now reply with at most 15 lines of this result, copied exactly, and stop.'",
         "REPLY = 'Now reply with at most 10 lines of this result, copied exactly, and stop.'"),
        ('    log = git(ws, ["log", "-S", name, "--no-merges", "--format=%h %ad %s", "--date=short", f"-n{COMMITS}", "--"] + PY, start)\n',
         '    log = git(ws, ["log", "-S", name, "--no-merges", "--format=%h %ad %s", "--date=short", f"-n{COMMITS}"] + recent(ws, start) + ["--"] + PY, start)\n'),
        ("def section(ws, name, start):\n",
         "_RANGE = []\n\n\ndef recent(ws, start):\n"
         f"    \"\"\"r76: git log -S only over the last {HISTORY_COMMITS} commits (the whole history is slow on large repositories).\"\"\"\n"
         "    if not _RANGE:\n"
         f"        revs = git(ws, [\"rev-list\", \"--max-count={HISTORY_COMMITS}\", \"HEAD\"], start) or []\n"
         f"        _RANGE.append([revs[-1] + \"..HEAD\"] if len(revs) == {HISTORY_COMMITS} else [])\n"
         "    return _RANGE[0]\n\n\ndef section(ws, name, start):\n"),
    ]
    for old, new in reps:
        assert s.count(old) == 1, old[:60]
        s = s.replace(old, new, 1)
    if setup_install:
        old = "    parts = [f\"REPOSITORY EVIDENCE for"
        assert s.count(old) == 1
        s = s.replace(old, "    install(ws)\n" + old, 1)
        old = "def main():\n"
        assert s.count(old) == 1
        s = s.replace(old, (
            "def install(ws):\n"
            "    \"\"\"allplus: copy the gate (run.py next to this script) to .git/agent/run.py; git never puts .git in the patch.\"\"\"\n"
            "    import shutil\n"
            "    target = os.path.join(ws, \".git\", \"agent\")\n"
            "    os.makedirs(target, exist_ok=True)\n"
            "    shutil.copyfile(os.path.join(os.path.dirname(os.path.abspath(__file__)), \"run.py\"), os.path.join(target, \"run.py\"))\n"
            f"    print({INSTALL_LINE.replace('Setup agent: your job is done, reply INSTALLED and stop (you have no run_command). ', '')!r})\n\n\n") + old, 1)
        s = s.replace('"""Repository evidence for a few exact names', '"""allplus setup (r76): installs the gate, then repository evidence for a few exact names', 1)
    return s


def build_evidc():
    out = fresh("evidc")
    fixer_md = COMBO1_MD.rstrip("\n") + "\n" + EVID_SECTION
    write(out, {
        "agent.yaml": "# evidc (r76): evid3's evidence stage made cheap (thinking off, 8 s script, last 500 commits) + combo1 as the fixer (scripts/make_plus_arms.py)\n"
                      "name: swe_agent\nagent_class: SequentialAgent\nsub_agents:\n  - config_path: evidence.yaml\n  - config_path: fixer.yaml\n",
        "evidence.yaml": f"""name: evidence
model: {MODEL}
description: Runs one repository search for names in the issue and copies the lines that matter.
instruction: !include prompts/evidence.md
include_contents: none  # fresh: the issue is in its system prompt (the harness re-runs the root agent after a nudge)
tools:
  - get_status
skills:
  - skills/evidence
output_key: evidence
generate_content_config: !include configs/evidence_sampling.yaml
""",
        "fixer.yaml": f"""name: fixer
model: {MODEL}
instruction: !include prompts/fixer.md
tools:  # combo1's tool list
  - run_command
  - read_file
  - edit_file
  - write_file
  - get_status
  - submit_patch
generate_content_config: !include configs/sampling.yaml
""",
        "eval_config.yaml": (SUB / "evid3/eval_config.yaml").read_text(),  # 29 calls: combo1's 28 + the evidence call
        "configs/sampling.yaml": PUB_SAMPLING,
        "configs/evidence_sampling.yaml": FAST_SAMPLING,
        "prompts/evidence.md": EVID_MD,
        "prompts/fixer.md": fixer_md,
        "skills/evidence/SKILL.md": (SUB / "evid3/skills/evidence/SKILL.md").read_text(),
        "skills/evidence/scripts/evidence.py": cheap_evidence_script(),
    })
    assert fixer_md.startswith(COMBO1_MD.rstrip("\n"))
    check_braces(fixer_md, ("{evidence?}",))
    check_braces(EVID_MD, ("{problem_description}",))
    return out


# ---------------------------------------------------------------- t7rc
T7RC_FIXER_MD = """You are an autonomous software engineer working in /workspace. Make the smallest correct change to the SOURCE code there so that the hidden tests for the issue pass. Those tests were written from the issue text: every exact name, message, type and behaviour it mentions is the specification. A teammate submits your patch after you are done, so you never call submit_patch yourself.

# YOUR SHELL
The setup step has already installed it at .git/agent/run.py. Run every command through it:
  run_command with the command: python .git/agent/run.py 'the whole shell command'
If the command itself contains single quotes, put it on the lines after the call:
  python .git/agent/run.py <<'EOF'
  the whole shell command
  EOF
Commands run in /workspace. Each result ends with a clock line, "[clock] N s of 420 used | ...", which also says whether a source file is edited. Look at it every time. A command run without python .git/agent/run.py still runs but shows no clock and you lose track of your time, so never drop the prefix, not even for git status.

# EXAMPLE (another repository; your names will differ)
- run_command: python .git/agent/run.py 'git grep -n -F "parse_value" -- src tests | head -20'
  result, then: [clock] 35 s of 420 used | no source edit yet
- read_file src/pkg/values.py, start_line 40, end_line 80
- edit_file on src/pkg/values.py
- run_command: python .git/agent/run.py 'timeout 120 python -m pytest tests/test_values.py -x -q -k parse_value'
  result, then: [clock] 190 s of 420 used | source edited: src/pkg/values.py
- run_command: python .git/agent/run.py 'git status --short && git diff'
- a plain-text reply saying what changed and where.
Every command in the example starts with python .git/agent/run.py. Yours must too.

# YOUR OTHER TOOLS
- read_file reads a file region (always give start_line and end_line), edit_file changes a file, write_file creates a scratch file under .git/agent/ or a new source file the issue needs.
- """ + GARBLE + """

# LIMITS
- 7 minutes and about 30 tool calls in all, and most of that time goes into your own thinking: keep replies short.
- Whatever edit is in /workspace when time runs out is graded; an unedited tree scores zero. Have a source file edited before 160 s on the clock. When unsure, make your best-guess edit in the most likely place: a wrong edit can still be corrected. With no source edit at 240 s the shell refuses commands until you edit.
- Never create, change or delete test files (test_*.py, *_test.py, anything under tests/, pytest.ini, conftest.py).
- Scratch files only in /tmp (through the shell) or .git/agent/ (write_file): any other new file under /workspace ends up in the patch.
- Never run a whole test suite: name one test file, and add -k when you can.

# TIME PLAN (by the clock line)
- Until about 100 s: locate and read. By 160 s: your edit is in the file.
- Then: one repro script, run once; one related test file; one correction if needed.
- From 350 s: stop and FINISH.

# PROCEDURE
1. Before your first call, note for yourself the exact file, function, class or CLI name, the exact error message and exception type, the expected return value or output, the inputs that trigger the bug and every edge case the issue mentions. Each concrete string and name in the issue must appear exactly like that in your code.
2. Locate. Use paths the issue names directly. Put independent searches for the issue's symbols, their callers and relevant tests into one shell command: git grep -n -F "symbol" and git ls-files, about 20 output lines each. Then read the implementation plus one caller or test, about 40 lines per region. For a bug, find where the wrong behaviour is produced; for a feature, copy the closest existing sibling, including __all__, option lists, dispatch tables and imports.
3. Edit with edit_file, with a short, unique old_string copied exactly. Fix the cause, not the symptom; change only what the issue requires and keep signatures and defaults. Apply the change to every parallel implementation (sync and async, each backend, re-exports in __init__.py or __all__). Use the issue's exact exception class and message text. For FastAPI documentation tasks, edit docs_src/.
4. Repro: write_file .git/agent/repro_a.py, a short script that imports the package normally, FAILS (assert or raise) while the bug is there and exits 0 once it is fixed, printing FIXED or BUG. Run it once: python .git/agent/run.py 'timeout 30 python3 .git/agent/repro_a.py'
5. If a related test file exists, run it once as in the example. Failures from missing fixtures or unrelated imports were there before you: ignore them.

# FINISH
1. One shell command: python .git/agent/run.py 'git status --short && git diff'. Remove any scratch file in /workspace; restore any changed test file with git checkout -- path.
2. Reply in plain text with NO tool call: one line saying what you changed and where. That reply hands over to your teammate.

# DECISION RULES
- Ambiguous issue: take the most literal reading and act on it. Never ask questions.
- Several candidate places: pick where the wrong behaviour is produced, not where it is observed.
- A fix failed: make a different, smaller change. Never repeat the same edit.
- Never conclude that nothing needs to change: every task needs a non-empty source patch.
"""
RC_STARTED_OLD = '    code, out = sh(["git", "log", "-1", "--format=%ct", "_swegemma_baseline"], ws)\n    if code == 0 and out.strip().isdigit():\n        return int(out.strip())\n'
RC_STARTED_NEW = ('    cache = os.path.join(ws, ".git", "agent", "t_base")  # rc: the start time once, not a git process per call\n'
                  '    try:\n        return int(open(cache).read())\n    except (OSError, ValueError):\n        pass\n'
                  '    code, out = sh(["git", "log", "-1", "--format=%ct", "_swegemma_baseline"], ws)\n'
                  '    if code == 0 and out.strip().isdigit():\n        os.makedirs(os.path.dirname(cache), exist_ok=True)\n'
                  '        open(cache, "w").write(out.strip())\n        return int(out.strip())\n')
RC_COMMAND_OLD = '    return " ".join(argv).strip()\n'
RC_COMMAND_NEW = ('    text = " ".join(argv).strip()\n'
                  "    if not text:  # rc: python .git/agent/run.py <<'EOF'; never wait on a silent open stdin\n"
                  '        try:\n            if select.select([sys.stdin], [], [], 0.2)[0]:\n                text = sys.stdin.read().strip()\n'
                  '        except (OSError, ValueError):\n            pass\n    return text\n')
CLOCK_LINE_OLD = '    print(body + f"\\n[clock] {used} s of {SESSION} used | {state}")\n'
CLOCK_LINE_NEW = '    print(body + f"\\n[clock] {used} s of {SESSION} used | {state} | every command: python .git/agent/run.py \'...\'")  # r76 REMIND\n'


def t7_clock_script():
    s = (SUB / "sq1c2t7/skills/work/scripts/run.py").read_text()
    for old, new in ((RC_STARTED_OLD, RC_STARTED_NEW), (RC_COMMAND_OLD, RC_COMMAND_NEW), ("import os\n", "import os\nimport select\n"),
                     (CLOCK_LINE_OLD, CLOCK_LINE_NEW)):
        assert s.count(old) == 1, old[:50]
        s = s.replace(old, new, 1)
    return s


def build_t7rc():
    out = fresh("t7rc")
    write(out, {
        "agent.yaml": "# t7rc (r76): sq1c2t7 (7-min clock, refusal at 240 s, fixer hands over, finisher submits) with its shell through run_command\n"
                      "# after a setup agent installs it (the LB fit pattern of sk_a2 / nn32rcn2), 32 calls instead of 80 (scripts/make_plus_arms.py)\n"
                      "name: swe_agent\nagent_class: SequentialAgent\nsub_agents:\n  - config_path: setup.yaml\n  - config_path: fixer.yaml\n  - config_path: finisher.yaml\n",
        "setup.yaml": SETUP_YAML,
        "fixer.yaml": f"""name: fixer
model: {MODEL}
instruction: !include prompts/fixer.md
tools:  # run_command runs .git/agent/run.py (the clock), installed by the setup agent
  - run_command
  - read_file
  - edit_file
  - write_file
  - get_status
  - submit_patch  # declared as in sq1c2t7; the prompt says the teammate submits
generate_content_config: !include configs/sampling.yaml
""",
        "finisher.yaml": (SUB / "sq1c2t7/finisher.yaml").read_text(),
        "eval_config.yaml": "evaluation:\n  timeout_seconds: 240\n  max_tool_calls: 32  # sq1c2t7: 80 (timed out on the LB); every 8-min agent that fit had 28-32\n  max_time_minutes: 7\n  max_turns: 80\n",
        "configs/sampling.yaml": (SUB / "sq1c2t7/configs/sampling.yaml").read_text(),
        "configs/setup_sampling.yaml": SETUP_SAMPLING,
        "prompts/setup.md": SETUP_MD,
        "prompts/fixer.md": T7RC_FIXER_MD,
        "prompts/finisher.md": (SUB / "sq1c2t7/prompts/finisher.md").read_text(),
        "skills/work/SKILL.md": SETUP_SKILL_MD,
        "skills/work/scripts/install.py": install_script(),
        "skills/work/scripts/run.py": t7_clock_script(),
    })
    check_braces(T7RC_FIXER_MD)
    assert "run_skill_script" not in T7RC_FIXER_MD and "positional_args" not in T7RC_FIXER_MD
    return out


# ---------------------------------------------------------------- allplus
ALLPLUS_SETUP_MD = """Your only job is to prepare the ground for the engineer who fixes the issue after you: install the shell and run one search of the repository. You will not read code and you will not work on the fix. You have no run_command.

Choose two to four exact names from the issue below that the fix most likely touches: functions, methods, classes, options or parameters, written exactly as they appear in the issue or as they would appear in the code. Prefer the most specific names, such as convert_underscores, over common words, such as Header.

Call run_skill_script with skill_name work, file_path scripts/setup.py and positional_args holding those names, one name per item. That is your only call: it installs the shell and searches the repository.

Then reply with the lines of its search result that best show where the fix belongs and how this code is meant to behave: where the names are defined, tests that use them, and the lines an earlier commit changed around them. Copy each line exactly as it was printed, with its file:line or commit, at most 10 lines and nothing else. If nothing in the result bears on the issue, reply with the single line NOTHING RELEVANT.

# THE ISSUE (verbatim)
{problem_description}"""
ALLPLUS_SKILL_MD = """---
name: work
description: Installs the engineer's shell, .git/agent/run.py, and searches the repository's tests, definitions, git history and changelog for a few exact names from the issue. A single call with the names as positional_args.
---

Call run_skill_script with skill_name work, file_path scripts/setup.py and positional_args holding two to four exact names from the issue, one name per item. It installs the shell and prints what the repository says about each name.
"""
ALLPLUS_MD = """You are an autonomous software engineer fixing an issue in /workspace. Make the smallest correct change to the SOURCE code so that the hidden tests pass. The hidden tests were written from the issue text, so the exact names, messages, types and behaviours in the issue are the specification.

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
  result, then: [state] LOOK: no source edit yet
- edit_file on src/pkg/values.py
- run_command: python .git/agent/run.py 'python -m pytest tests/test_values.py -x -q -k parse_value'
  result, then: [state] FINISH: git status --short && git diff, then submit_patch
- run_command: python .git/agent/run.py 'git status --short && git diff'
- submit_patch, then a single sentence on what changed.
Every command in the example starts with python .git/agent/run.py. Yours must too.

# THE STATE LINE
Every shell result ends with it. Do what it says:
- LOOK: find where the wrong behaviour is produced.
- EDIT NOW: stop reading and make your best edit with edit_file now. A wrong edit can still be corrected; an unedited tree scores zero.
- CHECK: your source edit is in; run a related test file.
- FINISH: run git status --short && git diff, correct your change if an output showed it is wrong, then call submit_patch.
When the shell refuses a command, do what the refusal says. edit_file always works.

# HARD LIMITS
- A fixed budget of tool calls and time. When either runs out, the working tree is graded as it is: an edit that exists counts even without submit_patch, and an unedited tree always scores zero.
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


def build_allplus():
    out = fresh("allplus")
    write(out, {
        "agent.yaml": "# allplus (r76): every change with a measured plus in one agent (scripts/make_plus_arms.py): ONE setup call installs the gate and\n"
                      "# runs the cheap evidence search (thinking off; copied lines kept in the engineer's system prompt), then the engineer:\n"
                      "# combo1's contract and edit rules + the gate's state words + a worked example + REMIND, no read_file, no graph tools\n"
                      "name: swe_agent\nagent_class: SequentialAgent\nsub_agents:\n  - config_path: setup.yaml\n  - config_path: main.yaml\n",
        "setup.yaml": f"""name: setup
model: {MODEL}
description: Installs the engineer's shell and runs one repository search for names in the issue; copies the lines that matter.
instruction: !include prompts/setup.md
include_contents: none  # fresh: the issue is in its system prompt (the harness re-runs the root agent after a nudge)
tools:
  - get_status
skills:
  - skills/work
output_key: evidence
generate_content_config: !include configs/setup_sampling.yaml
""",
        "main.yaml": f"""# main: run_command runs .git/agent/run.py (the gate); no read_file, so reads go through the gate too
name: main
model: {MODEL}
instruction: !include prompts/system.md
tools:
  - run_command
  - edit_file
  - write_file
  - get_status
  - submit_patch
generate_content_config: !include configs/sampling.yaml
""",
        "eval_config.yaml": "evaluation:\n  timeout_seconds: 240\n  max_tool_calls: 32  # setup 1 + engineer; nn32rcn2 fit the LB at 32 / 8 min\n  max_time_minutes: 8\n  max_turns: 80\n",
        "configs/sampling.yaml": PUB_SAMPLING,
        "configs/setup_sampling.yaml": FAST_SAMPLING,
        "prompts/setup.md": ALLPLUS_SETUP_MD,
        "prompts/system.md": ALLPLUS_MD,
        "skills/work/SKILL.md": ALLPLUS_SKILL_MD,
        "skills/work/scripts/setup.py": cheap_evidence_script(setup_install=True),
        "skills/work/scripts/run.py": gate_script(),
    })
    assert not re.search(r"\d", ALLPLUS_MD), "allplus: the gate drives timing; no numbers in the engineer's prompt"
    check_braces(ALLPLUS_MD, ("{evidence?}",))
    check_braces(ALLPLUS_SETUP_MD, ("{problem_description}",))
    assert ALLPLUS_MD.count("{evidence?}") == 1 and "setup step has already installed" in ALLPLUS_MD
    return out


if __name__ == "__main__":
    for b in (build_nn32rcf, build_evidc, build_t7rc, build_allplus):
        o = b()
        print("wrote", o.relative_to(ROOT), "|", sorted(p.relative_to(o).as_posix() for p in o.rglob("*") if p.is_file()))
