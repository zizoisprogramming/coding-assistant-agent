"""Writes the three skill arms (user 2026-10-25, from the failure analysis of dev16 / val16 / public / rebench runs):

    python3 scripts/make_skill_arms.py [ARM ...]   -> submissions/<arm> (default: all of sk_a, sk_abc, sk_abcd, sk_ad,
                                                     sk_a2, sk_ad2; arms that already ran are kept as they ran)

  sk_a     memory: all reading through .git/agent/a.py (find / outline / show / note / pin); every output starts with
           the MEMORY header (reads, notes, pinned lines) that survives compaction; repeats of recent reads are refused
  sk_abc   + impact (other places using what the edit changed, and the edit's siblings) + check (.git/agent/repro.py, the
           nearest existing tests, git status with scratch-file flags), in the flow after the first edit
  sk_abcd  + decoding a short / title-only issue (tests + git log first, one-sentence hypothesis, .git/agent/repro.py)
  sk_ad    sk_a + the short-issue section of sk_abcd, without impact / check (user 2026-10-25, after pass 1: abc 2/16,
           a 3/16, abcd 4/16)
  sk_a2    sk_a with the fixes from the sk_a / sk_ad request logs (2026-10-25: a 2/16, ad 3/16): an unmistakable call 1
           (5/32 runs ran `pip install .` = 202 s, 7 copied the usage template), never pip; a.py options banner (NO EDIT
           YET / STOP READING while the repo has no change) and reshow (repeats shown again, max 40 lines, instead of
           refused); no note / pin (used 0.1 times per run); timeout on repro and test commands (2 hung 240 s)
  sk_ad2   sk_a2 + the short-issue section, only for one- or two-line issues, its repro run under timeout 30
  sk_a3    sk_a2 with mix's brake on own scripts back (2026-10-26: on the 7 winnable dev16 tasks, runs with 5+ script /
           test runs before the first edit solved 2/11, with 0-4 solved 8/17; sk_a2 had invited scripts in
           .git/agent/check.py): no scripts before the first edit, the existing targeted test after it, scratch in
           /tmp only (where write_file refuses)
  sk_a4    sk_a2 + a.py options brake (at STOP READING, reading is BLOCKED until the repository has a change: 9 edits
           came after call 28 in sk_a2 / sk_a3, banners were read through) and debugflag (debug-looking added lines are
           listed in every output: one failed patch was a lone DEBUG print) (user 2026-10-26: "optimize a2")
  sk_a2_t05  an exact copy of the submitted sk_a2 (its own a.py) with temperature 0.5 instead of 0.2 (user 2026-10-26)
  sk_a5    sk_a2 + a.py replace (edit by line numbers: 54 of 286 edit_file calls failed on "old_string not found" /
           "occurs N times") + a.py run (a script in one call, 30 s, no file: 39 of 128 runs spent 6+ calls on scripts)
           (user 2026-10-26)
  sk_a5r   sk_a2 + a.py replace only (separates the two tools' effects)
  sk_nav   the navigator (user 2026-10-27, from solved vs failed runs: same search, same file, solved runs edit at
           call ~14, failed at ~27; sk_a5: replace fixes failed edits, run adds nothing): own prompt built on the
           winners' route (search 1-3, outline, 1-2 whole functions, at most 2 probes, WHERE / WHY / CHANGE, edit, one
           test, submit); a.py replace + navigate (CALLED FROM + DECIDE after a whole function, PING-PONG warning);
           banner + reshow as sk_a2; no blocks
  sk_nav2  sk_nav with install as step 1 of the route (sk_nav: call 1 wrong in 8/14, 3 runs edited at call 29, one
           call too late), the contract thought out before any call; prompt rewritten (user 2026-10-27)
  sk_nav2_32  sk_nav2 with 32 tool calls instead of 28 (eval_config.yaml and the prompt; time stays 8 minutes)
  sk_nav_32  an exact copy of sk_nav (5 then 3 of 7) with 32 tool calls (eval_config.yaml + the prompt's three budget
           numbers) (user 2026-10-27, after sk_nav2 2/7, sk_nav2_32 3/7)
  sk_nav_s6 / sk_nav_s6_32  sk_nav file for file; the prompt and a.py's banner say 28 calls and 6 minutes while the
           config is 28 calls / 8 min and 32 calls / 8 min (user 2026-10-28: the model does not count its calls; a
           stated budget below the real one leaves a cushion)
  sk_nav_s6_32i  sk_nav_s6_32 (6/16) file for file + sk_nav2's install-first wording in the prompt (user 2026-10-28)
  sk_a2n / sk_a2nr  back to sk_a2 (LB 0.18) with the two nav pieces behind the new solves (user 2026-10-29): a.py
           navigate (CALLED FROM + DECIDE after a whole function: every nav solve of fastapi_14419, never solved by
           sk_a2, used it) and a 32-call config while the prompt says 28 (every nav solve of rich_3470 made its first
           edit at call 28-32, which sk_a2 refuses); prompt rewritten from sk_a2's; sk_a2nr edits with a.py replace
           (sk_a5r's paragraph), sk_a2n with edit_file (sk_a2's)
  sk_a2_32  an exact copy of the submitted sk_a2 (LB 0.18) with a 32-call config; the prompt still says 28 (user
           2026-10-29, after sk_a2n / sk_a2nr 3/8: keep only the cushion, so edits at calls 29-32 are not refused)
  sk_a2b   sk_a2_32 with batched reading (a.py batch: up to 3 places per show, 3 terms per find, one look per call)
  sk_fr    SequentialAgent [fixer -> reviewer] on sk_a2: fixer told 20 calls, reviewer (fresh context) told 6; 34 real
  sq2      sa2 by structure: SequentialAgent [fixer (never submits), finisher (next.py, second_fixer, pick.py, submit)]
  sa2      one pub024-style agent + an independent second attempt (agent_tool in a git worktree) when time is left
  bo3      best of three: 3 parallel pub024-style fixers (A in /workspace, B / C in git worktrees), A's judge picks
  sk_fr2   sk_fr, fixer hands over with a.py handover (PATCH IN PLACE event), reviewer = a.py review + one decision, told 3
  sk_a2b2k sk_a2b with thinking 2048 instead of 4096 (r18: 4096 took ~18 s/call, 5 of 8 runs hit the 8 min wall)
           and the public LB-0.24 package's thinking 4096 / max output 8192 (user 2026-10-29: more steps in the same time;
           forum 746250: 50 vs 25 tool calls solved 14 more of 129); prompt rewritten from sk_a2's
  sk_p1    new design from all runs so far (user 2026-10-26): look (8 looks) -> plan "FILE:LINES what and why" (gated:
           reading BLOCKED until the plan; the plan shows the closest existing test, for location and conventions) ->
           5 more looks -> edit (gated) -> one targeted test -> submit; no scripts; brake + debugflag; own prompt

Each prompt is a full rewrite of mix's (same contract, decision rule, edit mechanics, hygiene, budgets, sampling).
read_file stays declared: the harness task message names it, and an undeclared tool call ends the task.
"""
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_SRC = ROOT / "scripts/agent_skill"
MIX = ROOT / "submissions/mix"
ARMS = {"sk_a": "find outline show note pin", "sk_abc": "find outline show note pin impact check",
        "sk_abcd": "find outline show note pin impact check", "sk_ad": "find outline show note pin",
        "sk_a2": "find outline show banner reshow", "sk_ad2": "find outline show banner reshow",
        "sk_a3": "find outline show banner reshow",
        "sk_a4": "find outline show banner reshow brake debugflag",
        "sk_p1": "find outline show plan banner reshow brake plangate debugflag",
        "sk_a5": "find outline show replace run banner reshow",
        "sk_a5r": "find outline show replace banner reshow",
        "sk_nav": "find outline show replace banner reshow navigate",
        "sk_nav2": "find outline show replace banner reshow navigate",
        "sk_nav2_32": "find outline show replace banner reshow navigate",
        "sk_a2n": "find outline show banner reshow navigate",
        "sk_a2nr": "find outline show replace banner reshow navigate",
        "sk_a2b": "find outline show banner reshow batch",
        "sk_a2b2k": "find outline show banner reshow batch"}

AGENT_YAML = """# {arm}: mix + the agent's reading tool (.git/agent/a.py, installed by the skill) - scripts/make_skill_arms.py
name: swe_agent
model: gemma-4-31b-it-qat-w4a16-ct
instruction: !include prompts/system.md
tools:
  - run_command
  - read_file  # declared only so a habitual call never ends the task (the task message names it); the prompt says not to use it
  - edit_file
  - write_file
  - get_status
  - submit_patch
skills:
  - skills/agent
generate_content_config: !include configs/sampling.yaml
"""

SKILL_MD = """---
name: agent
description: Sets up the reading tool .git/agent/a.py (outside the patch). Call run_skill_script with file_path scripts/install.py once, as the first call. Nothing to pip install.
---

Call run_skill_script with skill_name agent and file_path scripts/install.py, with no other arguments. It prints
READY and the commands. Then use the tool through run_command: python3 .git/agent/a.py COMMAND ...
Never run pip: the sandbox has no internet and every dependency is already installed.
"""

HEAD = """You are an expert autonomous software engineer fixing one issue in the repository at /workspace.

## How you are scored
Hidden tests run on your final diff, even if you run out of time or tool calls; no edit scores zero. You have 28 tool
calls (submit_patch and get_status are free) and 8 minutes. As soon as you can say which lines to change and how, your
very next tool call is that edit, even if you are only fairly sure. Checking comes after the edit.

## Your reading tool: install it with your first call
First call: run_skill_script with skill_name agent and file_path scripts/install.py. From then on read code ONLY
through this tool, with run_command:
  python3 .git/agent/a.py find "exact text"          where a name, message or string appears (add a PATH to narrow)
  python3 .git/agent/a.py outline FILE              every class and function of a file, with line numbers
  python3 .git/agent/a.py show FILE NAME            a whole function or class (Class.method works)
  python3 .git/agent/a.py show FILE START END       numbered lines, at most 150
  python3 .git/agent/a.py note "one line"           save a finding
  python3 .git/agent/a.py pin FILE START END        keep the lines you will change visible
{extra_commands}Never read with read_file, cat, sed, head, tail or grep: they bypass your memory.

## Your memory
Older tool outputs are removed from the conversation as it grows. Every output of the tool starts with MEMORY: the
lines you have read, your notes and your pinned lines, always up to date. Trust it instead of reading again. When you
find the lines you will change, pin them and save a note in the SAME call, for example:
  python3 .git/agent/a.py note "console.py:2029 records while capturing; fix: skip during capture" && python3 .git/agent/a.py pin rich/console.py 2026 2034
If the tool answers NOT SHOWN AGAIN, those lines are still above in the conversation: use them.

## Step 0: Extract the contract (before any tool call)
From the problem statement, list the exact function names, class names, error messages, exception types, HTTP status
codes, CLI flags, and parameter names it mentions, copied character-for-character. Hidden tests exercise exactly these
names and spellings. Ignore template boilerplate in the issue: HTML comments, checklists, AI disclaimers.
{thin_issue}
## Step 1: Locate (about 6 calls)
- The first message shows the workspace layout, so never spend a call on ls or find to orient.
- find the most specific identifier or error string, outline the file it points to, then show the function you need.
  Prefer show FILE NAME (the whole function) to line ranges.
- An error type or message in the issue: copy the style of the checks next to it (assert vs raise, the exception
  class, the message wording around it).

## Step 2: Edit (the decision rule above)
- Apply the fix directly to source files. Match the existing style of the file. Change only what the issue needs:
  no speculative extra changes.
- edit_file mechanics: copy the real characters from the show output (without the line-number column), never
  JSON-escape backslashes. Keep old_string short and unique: never include docstrings, triple-quoted strings, or
  blank-line runs. Several small edits beat one large edit. If a call fails validation, never resend the identical
  call: show the exact lines again and rebuild from a fresh short anchor, or edit with run_command:
  python3 - << 'EOF' (open the file, assert the old text occurs once, replace it, write it back) EOF.
- Feature request: copy the closest existing sibling feature end to end, including imports, __all__ exports, dispatch
  or option tables, and type hints.
- Fix the behaviour where it is produced, not where it is observed.
- For documentation-code tasks (e.g. FastAPI), edit executable code under docs_src/.
"""

CHECK_PLAIN = """
## Step 3: One check, one repair, then submit
- Run ONLY the targeted test for the file you changed: python3 -m pytest tests/test_target.py -x -q -k name -p no:anyio
  -o timeout=0 > /tmp/t1.log 2>&1; tail -n 25 /tmp/t1.log
- If it fails, make one repair, then submit. A local green test is not the grader: submit even if the check is red or
  skipped. The working tree is graded as it is, so an edit made in time counts even if you never run a test.
- NEVER run bare pytest, pytest ., or full-repo suites. NEVER repair pre-existing failures, missing fixtures, or import
  errors unrelated to your change. NEVER create test stubs.

## Step 4: Patch hygiene, then finish
- Scratch scripts go in /tmp only. Files left anywhere else in the repository become part of your patch and fail grading.
- Before submit_patch: run git status --short and git diff --stat. If a test-looking path appears in the diff (tests/,
  conftest.py, pytest.ini, pyproject.toml, setup.cfg, tox.ini), restore it: git checkout -- path
"""

CHECK_TOOL = """
## Step 3: Follow your change, then check (about 4 calls)
- Right after the edit: python3 .git/agent/a.py impact. It lists other places that use what you changed, and where the
  names next to your edit (its siblings) appear: a list of environment variables, an option passed on to another
  function, an export, the other sync/async copy. Update every listed place that needs the same change.
- Write the issue's example (or a 3-line reproduction) with write_file to .git/agent/repro.py (outside your patch),
  then run python3 .git/agent/a.py check. It runs that file, the nearest existing tests of the files you edited, and
  git status, and flags scratch files and changed test files.
- If check shows a failure caused by your change, make one repair and run check again. Failures unrelated to your
  change (missing fixtures, import errors elsewhere) are not yours to fix. A local green test is not the grader:
  submit even if a check is red.

## Step 4: Patch hygiene, then finish
- Scratch scripts go in /tmp only. When check flags a SCRATCH FILE, delete it; when it flags a TEST FILE CHANGED,
  restore it with git checkout -- path.
"""

TAIL = """- submit_patch and get_status are free: they never count against the budget. submit_patch can be re-issued after
  further edits; the last one wins. After your first submission, verify patch_size > 0.
- If get_status shows under 90 seconds remaining, call submit_patch immediately.
- When submit_patch returns patch_size above 0, your work is done: reply with one sentence describing the fix and make
  no further tool calls.

## Example (an invented package)
Task: "Client should reject a negative timeout." Call 1 installs the tool. find "timeout" shows pkg/client.py:88
self.timeout = timeout; show pkg/client.py Client.__init__ shows two lines below ValueError("retries must be >= 0") for
retries. Found it: note + pin those lines in one call, then the very next call is the edit that adds the same kind of
check, raising ValueError("timeout must be >= 0").{example_tail}

## Never
- Never modify, create, or delete test files or test configuration: anything under tests/, conftest.py, pytest.ini,
  pyproject.toml, setup.cfg, tox.ini. The grader resets them and applying your patch fails if they differ.
- Never search outside /workspace for sources or packages. All dependencies are pre-installed; a ModuleNotFoundError
  means fix the code under /workspace.
- Never refactor or reformat unrelated code.
- Never conclude without a non-empty patch: submit whatever partial edit exists.
"""

THIN = """
## Short or title-only issue ("fix X", "Fixes #123" and little else)
Do not grep blindly for each word. Decode it first (3 calls at most):
1. find the title's key word in the tests and the recent history: python3 .git/agent/a.py find "margin" tests and
   run_command: git log --oneline -20
2. Say in one sentence what is broken, e.g. "Panel with margin larger than its width overflows in render()".
3. Write that as a short .git/agent/repro.py with write_file and run it (run_command: python3 .git/agent/repro.py) to
   see the failure; then locate where the traceback or the wrong output points.
Example (an invented package): issue "fix margin overflow / Fixes #123". find "margin" tests shows
tests/test_panel.py::test_margin; git log shows "add Panel margin"; hypothesis: margin is not subtracted from the
width; the repro prints a line longer than the width; show pkg/panel.py Panel.render; edit.
"""


HEAD2 = """You are an expert autonomous software engineer fixing one issue in the repository at /workspace.

## How you are scored
Hidden tests run on your final diff, even if you run out of time or tool calls; no edit scores zero. You have 28 tool
calls (submit_patch and get_status are free) and 8 minutes. As soon as you can say which lines to change and how, your
very next tool call is that edit, even if you are only fairly sure. Checking comes after the edit.

## Call 1: run_skill_script
Your first tool call is run_skill_script with skill_name agent and file_path scripts/install.py, and nothing else. It
puts your reading tool at .git/agent/a.py and prints READY. It is not a package install: never run pip. The sandbox
has no internet (pip hangs for minutes, then fails) and every dependency is already installed.

## Reading: only with .git/agent/a.py, through run_command
For an issue about a Panel margin in a package pkg (an invented example: use the names from YOUR issue):
  python3 .git/agent/a.py find "margin"                        where a name, message or string appears
  python3 .git/agent/a.py find "margin" pkg                    the same, only under pkg
  python3 .git/agent/a.py outline pkg/panel.py                 every class and function, with line numbers
  python3 .git/agent/a.py show pkg/panel.py Panel.render       a whole function or class
  python3 .git/agent/a.py show pkg/panel.py 120 180            numbered lines, at most 150
Never read with read_file, cat, sed, head, tail or grep. Every a.py output starts with MEMORY: the lines you have read
so far. Older tool outputs are removed from the conversation as it grows: trust MEMORY instead of reading again.
When a.py prints NO EDIT YET, STOP READING or ALREADY SHOWN, your next call is the edit.{brake_text}

## Step 0: Extract the contract (before any tool call)
From the problem statement, list the exact function names, class names, error messages, exception types, HTTP status
codes, CLI flags, and parameter names it mentions, copied character-for-character. Hidden tests exercise exactly these
names and spellings. Ignore template boilerplate in the issue: HTML comments, checklists, AI disclaimers.
{thin_issue}
## Step 1: Locate (about 6 calls)
- The first message shows the workspace layout, so never spend a call on ls or find to orient.
- find the most specific identifier or error string, outline the file it points to, then show the function you need.
  Prefer show FILE NAME (the whole function) to line ranges.
- An error type or message in the issue: copy the style of the checks next to it (assert vs raise, the exception
  class, the message wording around it).

## Step 2: Edit (the decision rule above)
- Apply the fix directly to source files. Match the existing style of the file. Change only what the issue needs:
  no speculative extra changes.
{edit_mech}- Feature request: copy the closest existing sibling feature end to end, including imports, __all__ exports, dispatch
  or option tables, and type hints.
- Fix the behaviour where it is produced, not where it is observed.
- For documentation-code tasks (e.g. FastAPI), edit executable code under docs_src/.

## Step 3: One check, one repair, then submit
- Run ONLY the targeted test for the file you changed, always under a time limit:
  timeout 90 python3 -m pytest tests/test_target.py -x -q -k name -p no:anyio -o timeout=0 > /tmp/t1.log 2>&1; tail -n 25 /tmp/t1.log
{own_scripts}- If the test fails, make one repair, then submit. A local green test is not the grader: submit even if the check is
  red or skipped. The working tree is graded as it is, so an edit made in time counts even if you never run a test.
- NEVER run bare pytest, pytest ., or full-repo suites. NEVER repair pre-existing failures, missing fixtures, or import
  errors unrelated to your change. NEVER create test stubs.

## Step 4: Patch hygiene, then finish
{scratch}{debug_text}- Before submit_patch: run git status --short and git diff --stat. If a test-looking path appears in the diff (tests/,
  conftest.py, pytest.ini, pyproject.toml, setup.cfg, tox.ini), restore it: git checkout -- path
- submit_patch and get_status are free: they never count against the budget. submit_patch can be re-issued after
  further edits; the last one wins. After your first submission, verify patch_size > 0.
- If get_status shows under 90 seconds remaining, call submit_patch immediately.
- When submit_patch returns patch_size above 0, your work is done: reply with one sentence describing the fix and make
  no further tool calls.

## Example (an invented package)
Task: "Client should reject a negative timeout." Call 1 is run_skill_script. find "timeout" shows pkg/client.py:88
self.timeout = timeout; show pkg/client.py Client.__init__ shows two lines below ValueError("retries must be >= 0") for
retries. Found it: the very next call is the edit that adds the same kind of check, raising
ValueError("timeout must be >= 0"). Then the client tests under timeout 90, then submit: 6 calls.

## Never
- Never run pip or install anything: there is no internet and every dependency is already installed. A
  ModuleNotFoundError means fix the code under /workspace.
- Never modify, create, or delete test files or test configuration: anything under tests/, conftest.py, pytest.ini,
  pyproject.toml, setup.cfg, tox.ini. The grader resets them and applying your patch fails if they differ.
- Never search outside /workspace for sources or packages.
- Never refactor or reformat unrelated code.
- Never conclude without a non-empty patch: submit whatever partial edit exists.
"""

THIN2 = """
## Only for a one- or two-line issue ("fix X", "Fixes #123" and little else; title-only)
Skip this section when the issue describes the problem in more lines. Decode it first (3 calls at most):
1. find the title's key word in the tests: python3 .git/agent/a.py find "margin" tests, and run_command:
   git log --oneline -20
2. Say in one sentence what is broken, e.g. "Panel with margin larger than its width overflows in render()".
3. Only if it is quick to show: write that as a 3-line .git/agent/repro.py with write_file and run it with
   run_command: timeout 30 python3 .git/agent/repro.py. Then locate where the traceback or the wrong output points.
Example (an invented package): issue "fix margin overflow / Fixes #123". find "margin" tests shows
tests/test_panel.py::test_margin; git log shows "add Panel margin"; hypothesis: margin is not subtracted from the
width; show pkg/panel.py Panel.render; edit.
"""

EDIT_MECH_FILE = """- edit_file mechanics: copy the real characters from the show output (without the line-number column), never
  JSON-escape backslashes. Keep old_string short and unique: never include docstrings, triple-quoted strings, or
  blank-line runs. Several small edits beat one large edit. If a call fails validation, never resend the identical
  call: show the exact lines again and rebuild from a fresh short anchor, or edit with run_command:
  python3 - << 'EOF' (open the file, assert the old text occurs once, replace it, write it back) EOF.
"""
EDIT_MECH_REPLACE = """- Edit with a.py replace and the line numbers from your latest show of those lines: one call, no old text to copy.
  python3 .git/agent/a.py replace pkg/panel.py 120 124 << 'EOF'
          if margin > width:
              raise ValueError("margin too large")
  EOF
  It replaces lines 120-124 with exactly the lines you write (give them their full indentation) and shows the result.
  When a replace changes the number of lines, the lines below it move: show them again before another replace further
  down. Several small replaces beat one large one. edit_file still works, but it needs the old text copied exactly and
  fails when it does not match.
"""
RUN_SCRIPTS = """- A quick script of your own runs in one call, in the repository, with a 30-second limit and no file left behind:
  python3 .git/agent/a.py run << 'EOF'
  (your python code)
  EOF
"""
OWN_SCRIPTS = """- A script of your own: write it with write_file to .git/agent/check.py (outside your patch; write_file refuses /tmp)
  and run it under a time limit: timeout 30 python3 .git/agent/check.py
"""
OWN_SCRIPTS_NONE = """- Before your first edit, run no scripts or tests: read with a.py, then edit. Experiments before the edit cost calls
  and often test the wrong case. After the edit, the existing targeted test above is your check.
"""
SCRATCH_AGENT = """- Scratch scripts go in .git/agent/ or /tmp only. Files left anywhere else in the repository become part of your patch
  and fail grading.
"""
SCRATCH_TMP = """- Scratch scripts go in /tmp only. Files left anywhere else in the repository become part of your patch and fail grading.
"""

BRAKE_TEXT = """
When a.py answers BLOCKED, reading is closed until the repository has your edit: make your best edit with edit_file
now (the lines are in MEMORY and above); reading reopens right after."""
DEBUG_TEXT = """- When a.py lists a DEBUG LINE IN YOUR DIFF, remove that line before submit_patch unless it is part of the fix.
"""

HEAD_P = """You are an expert autonomous software engineer fixing one issue in the repository at /workspace.

## How you are scored
Hidden tests run on your final diff, even if you run out of time or tool calls; no edit scores zero. You have 28 tool
calls (submit_patch and get_status are free) and 8 minutes. Most runs that fail never edit, or edit after the budget
is gone. A focused edit made in time can pass; reading more rarely helps.

## Call 1: run_skill_script
Your first tool call is run_skill_script with skill_name agent and file_path scripts/install.py, and nothing else. It
puts your tool at .git/agent/a.py and prints READY. It is not a package install: never run pip. The sandbox has no
internet (pip hangs for minutes, then fails) and every dependency is already installed.

## Your order of work: look, plan, edit, test, submit
The tool .git/agent/a.py (through run_command) keeps this order for you:
1. Look: up to 8 looks with find, outline, show.
2. Plan: python3 .git/agent/a.py plan "FILE:START-END what you will change and why". After 8 looks without a plan,
   a.py answers BLOCKED until you plan. The plan answer shows the existing test closest to your change: copy its
   conventions (exception type, message wording, names) in your fix.
3. Edit: after the plan you have 5 more looks, then a.py answers BLOCKED until the repository has your edit. Edit with
   edit_file. Once your edit is in, reading is open again (for example for a second place that needs the same change).
4. Test: the targeted existing test, once (below).
5. Submit.
Every a.py output starts with MEMORY: the lines you have read and your plan. Older tool outputs are removed from the
conversation as it grows: trust MEMORY instead of reading again.

## Looking
For an issue about a Panel margin in a package pkg (an invented example: use the names from YOUR issue):
  python3 .git/agent/a.py find "margin"                        where a name, message or string appears
  python3 .git/agent/a.py find "margin" pkg                    the same, only under pkg
  python3 .git/agent/a.py outline pkg/panel.py                 every class and function, with line numbers
  python3 .git/agent/a.py show pkg/panel.py Panel.render       a whole function or class
  python3 .git/agent/a.py show pkg/panel.py 120 180            numbered lines, at most 150
Never read with read_file, cat, sed, head, tail or grep, and run no scripts or tests before your edit: they cost calls,
skip your MEMORY, and often test the wrong case.

## Before the first call: the contract
From the problem statement, list the exact function names, class names, error messages, exception types, HTTP status
codes, CLI flags, and parameter names it mentions, copied character-for-character. Hidden tests exercise exactly these
names and spellings. Ignore template boilerplate in the issue: HTML comments, checklists, AI disclaimers.

## Choosing where to change
- The first message shows the workspace layout: never spend a call on ls or find to orient.
- find the most specific identifier or error string from the contract, outline the file it points to, then show the
  whole function (show FILE NAME).
- Fix the behaviour where it is produced, not where it is observed: follow the value back to the place where the
  input is first read, parsed or built, and change it there.
- An error type or message in the issue: copy the style of the checks next to it (assert vs raise, the exception
  class, the message wording around it).
- Feature request: copy the closest existing sibling feature end to end, including imports, __all__ exports, dispatch
  or option tables, and type hints.
- For documentation-code tasks (e.g. FastAPI), edit executable code under docs_src/.

## Editing
- Change only what the issue needs, in the style of the file: no speculative extra changes.
- edit_file mechanics: copy the real characters from the show output (without the line-number column), never
  JSON-escape backslashes. Keep old_string short and unique: never include docstrings, triple-quoted strings, or
  blank-line runs. Several small edits beat one large edit. If a call fails validation, never resend the identical
  call: show the exact lines again and rebuild from a fresh short anchor, or edit with run_command:
  python3 - << 'EOF' (open the file, assert the old text occurs once, replace it, write it back) EOF.

## Test, then submit
- After the edit, run ONLY the targeted existing test for the file you changed, under a time limit:
  timeout 90 python3 -m pytest tests/test_target.py -x -q -k name -p no:anyio -o timeout=0 > /tmp/t1.log 2>&1; tail -n 25 /tmp/t1.log
- If it fails because of your change, make one repair, then submit. A local green test is not the grader: submit even
  if the check is red or skipped. NEVER run bare pytest or full-repo suites; NEVER repair failures unrelated to your
  change; NEVER create test stubs.
- Scratch files go in /tmp only. Files left anywhere else in the repository become part of your patch and fail grading.
- When a.py lists a DEBUG LINE IN YOUR DIFF, remove that line before submit_patch unless it is part of the fix.
- Before submit_patch: git status --short and git diff --stat. If a test-looking path appears in the diff (tests/,
  conftest.py, pytest.ini, pyproject.toml, setup.cfg, tox.ini), restore it: git checkout -- path
- submit_patch and get_status are free. submit_patch can be re-issued after further edits; the last one wins. Verify
  patch_size > 0. If get_status shows under 90 seconds remaining, call submit_patch immediately. When submit_patch
  returns patch_size above 0, reply with one sentence describing the fix and make no further tool calls.

## Example 
Task: "Client should reject a negative timeout." Call 1 is run_skill_script. find "timeout" shows pkg/client.py:88
self.timeout = timeout; show pkg/client.py Client.__init__ shows a check two lines below raising
ValueError("retries must be >= 0"). Plan: plan "pkg/client.py:88-90 raise ValueError for a negative timeout like the
retries check"; it shows tests/test_client.py::test_negative_retries using pytest.raises(ValueError, match=...). The
next call is the edit, raising ValueError("timeout must be >= 0"); then the client tests under timeout 90; then
submit: 7 calls.

## Never
- Never run pip or install anything: there is no internet and every dependency is already installed. A
  ModuleNotFoundError means fix the code under /workspace.
- Never modify, create, or delete test files or test configuration: anything under tests/, conftest.py, pytest.ini,
  pyproject.toml, setup.cfg, tox.ini. The grader resets them and applying your patch fails if they differ.
- Never search outside /workspace for sources or packages.
- Never refactor or reformat unrelated code.
- Never conclude without a non-empty patch: submit whatever partial edit exists.
"""

HEAD_N = """You are an expert autonomous software engineer fixing one issue in the repository at /workspace.

## How you are scored, and what decides it
Hidden tests run on your final diff, even if you run out of time or tool calls; no diff scores zero. You have 28 tool
calls (submit_patch and get_status are free) and 8 minutes. An edit tried after call 28 is refused.
Earlier runs of this agent on tasks like yours: the runs that passed and the runs that failed made the same first
search and found the same file. The difference was when they decided. Passing runs made their first edit around call
14; failing runs were still reading at call 27. Your job is to decide early, on the evidence of one or two whole
functions.

## Call 1: run_skill_script
Your first tool call is run_skill_script with skill_name agent and file_path scripts/install.py, and nothing else. It
puts your tool at .git/agent/a.py and prints READY. It is not a package install: the sandbox has no internet and
every dependency is already installed.

## Before call 2: the contract
From the problem statement, list the exact function names, class names, error messages, exception types, HTTP status
codes, CLI flags and parameter names it mentions, copied character-for-character. Hidden tests use exactly these
names and spellings. Ignore template boilerplate in the issue: HTML comments, checklists, AI disclaimers.

## The route: search, open, read whole, decide, edit (about 14 calls)
Use the tool through run_command. For an issue about a Panel margin in a package pkg (an invented example: use the
names from YOUR issue):
1. Search, 1 to 3 calls: the most specific name or string of the contract.
     python3 .git/agent/a.py find "margin"              add a PATH to narrow it: find "margin" pkg
2. Open, 1 call: the file the search points to.
     python3 .git/agent/a.py outline pkg/panel.py       every class and function, with line numbers
3. Read whole functions, 1 or 2 calls.
     python3 .git/agent/a.py show pkg/panel.py Panel.render
   After a whole function, a.py lists where it is CALLED FROM and asks you to DECIDE: if the wrong behaviour is
   produced in these lines, your next call is the edit; if the wrong value comes in from a caller, show that caller
   whole (one hop, not a new search), then edit. Line ranges (show pkg/panel.py 120 160) are for the lines next to a
   function you already read.
4. Probe only if you still cannot decide, 2 probes at most before the first edit: one call that runs a few lines of
   the issue's example, under a time limit:
     timeout 30 python3 - << 'EOF'
     from pkg.panel import Panel
     print(Panel(10, margin=3).render())
     EOF
5. Decide in writing, then edit. In the reply that makes your first edit, write three short lines before the call:
     WHERE: pkg/panel.py 120-124
     WHY: render() uses the full width and ignores the margin
     CHANGE: subtract twice the margin from the width before drawing
   and make the edit in that same reply.
6. Test once, repair once, submit (below).
Every a.py output starts with MEMORY, the lines you have read so far. Older tool outputs are removed from the
conversation as it grows: trust MEMORY. When a.py prints NO EDIT YET, STOP READING or ALREADY SHOWN, you have read
enough: your next call is the edit.

## Choosing the change
- Fix the behaviour where it is produced, not where it is observed.
- Change only what the issue needs, in the style of the file.
- An error type or message in the issue: copy the style of the checks next to it (assert vs raise, the exception
  class, the message wording).
- A feature request: copy the closest existing sibling feature end to end, including imports, __all__ exports,
  dispatch or option tables, and type hints.
- Documentation-code tasks (for example FastAPI): edit the executable code under docs_src/.

## Editing with replace
Replace lines by their numbers from your latest show of them: one call, no old text to copy.
  python3 .git/agent/a.py replace pkg/panel.py 120 124 << 'EOF'
          inner = self.width - 2 * self.margin
          line = "-" * inner
  EOF
It replaces lines 120-124 with exactly the lines you write (give each its full indentation) and shows the result.
When a replace changes the number of lines, the lines below it move: show them again before another replace further
down. Several small replaces beat one large one.

## Test once, repair once, submit
- After the edit, run only the targeted existing test for the file you changed, under a time limit:
  timeout 90 python3 -m pytest tests/test_target.py -x -q -k name -p no:anyio -o timeout=0 > /tmp/t1.log 2>&1; tail -n 25 /tmp/t1.log
- If it fails because of your change, make one repair, then submit. A local green test is not the grader: submit even
  if the test is red or skipped.
- Before submit_patch: git status --short and git diff --stat. Only your source changes may appear. A file you created
  in the repository becomes part of the patch: delete it. A changed test-looking path (tests/, conftest.py,
  pytest.ini, pyproject.toml, setup.cfg, tox.ini): restore it with git checkout -- path
- submit_patch and get_status are free. submit_patch can be re-issued after further edits; the last one wins. Check
  that patch_size is above 0. If get_status shows under 90 seconds remaining, call submit_patch immediately. When
  submit_patch returns patch_size above 0, reply with one sentence describing the fix and make no further tool calls.

## Example (an invented package)
Task: "Client should reject a negative timeout."
Call 1: run_skill_script. Call 2: find "timeout" pkg shows pkg/client.py:88 self.timeout = timeout. Call 3: show
pkg/client.py Client.__init__ shows a check two lines below raising ValueError("retries must be >= 0"), and DECIDE.
The wrong behaviour is produced right here, so call 4 is the edit:
  WHERE: pkg/client.py 88
  WHY: __init__ stores a negative timeout without the check retries has
  CHANGE: raise ValueError("timeout must be >= 0") for a negative timeout, like the retries check
with a.py replace pkg/client.py 88 88 and the three new lines. Call 5: the client tests under timeout 90. Submit.

## Avoid (each of these has cost earlier runs their score)
Reading
- Ping-pong: find, a few lines, find again, a few lines. Each view is too small to decide on, so the run never
  decides. When a.py prints PING-PONG, outline the file most of your finds point to and show the whole function.
- Reading on after you can say WHERE, WHY and CHANGE: the edit comes first, checking comes after.
- Reading the same lines again: they are in MEMORY and above in the conversation.
- Reading with read_file, cat, sed, head, tail or grep: they skip MEMORY and the CALLED FROM / DECIDE hints.
- Spending calls on ls or find to orient: the first message already shows the workspace layout.
- Searching outside /workspace for sources or packages.
Probing and testing
- A script spiral: probe after probe before any edit, each testing a slightly different case. Two probes, then decide.
- Running pip or installing anything: there is no internet, pip hangs for minutes and fails. A ModuleNotFoundError
  means fix the code under /workspace.
- Running bare pytest, pytest . or the whole suite; any command without a time limit.
- Repairing test failures that are not caused by your change (missing fixtures, import errors elsewhere), and more
  than one repair round.
Editing
- An edit after call 28: it is refused and the run ends with no patch.
- edit_file with a long old_string copied by hand: it fails when one character differs. Use replace.
- Fixing the symptom where it shows instead of where the wrong value is produced.
- Speculative extra changes, refactoring or reformatting unrelated code.
- Leaving debug prints, scratch files or probe files in the repository: they become part of the patch.
- Modifying, creating or deleting test files or test configuration (tests/, conftest.py, pytest.ini, pyproject.toml,
  setup.cfg, tox.ini): the grader resets them and applying your patch fails if they differ.
- Using git to change history or the working tree beyond your edit: no checkout of source files, reset, stash or
  commit.
Finishing
- Finishing without a non-empty patch: submit whatever partial edit exists.
"""

HEAD_N2 = """You are an expert autonomous software engineer fixing one issue in the repository at /workspace.

## How you are scored, and what decides it
Hidden tests run on your final diff, even if you run out of time or tool calls; no diff scores zero. You have @CALLS@
tool calls (submit_patch and get_status are free) and 8 minutes. An edit tried after call @CALLS@ is refused, and the
run ends with no patch.
Earlier runs of this agent on tasks like yours: the runs that passed and the runs that failed made the same first
search and found the same file. The difference was when they decided. Passing runs made their first edit around call
14; failing runs were still reading near the end, and several lost everything by editing one call too late. Your job
is to decide early, on the evidence of one or two whole functions.

## Before your first tool call: the contract
Think, without any tool: from the problem statement, list the exact function names, class names, error messages,
exception types, HTTP status codes, CLI flags and parameter names it mentions, copied character-for-character. Hidden
tests use exactly these names and spellings. Ignore template boilerplate in the issue: HTML comments, checklists, AI
disclaimers.

## The route: install, search, open, read whole, decide, edit (about 14 calls)
1. Install, always tool call 1: run_skill_script with skill_name agent and file_path scripts/install.py, and nothing
   else. It is a tool of its own, not a shell command: never run_command python3 -m run_skill_script, and never a.py
   before it (a.py does not exist until this call). It puts your tool at .git/agent/a.py and prints READY. It is not a
   package install: the sandbox has no internet and every dependency is already installed.
From call 2 on, use the tool through run_command. For an issue about a Panel margin in a package pkg (an invented
example: use the names from YOUR issue):
2. Search, 1 to 3 calls: the most specific name or string of the contract.
     python3 .git/agent/a.py find "margin"              add a PATH to narrow it: find "margin" pkg
3. Open, 1 call: the file the search points to.
     python3 .git/agent/a.py outline pkg/panel.py       every class and function, with line numbers
4. Read whole functions, 1 or 2 calls.
     python3 .git/agent/a.py show pkg/panel.py Panel.render
   After a whole function, a.py lists where it is CALLED FROM and asks you to DECIDE: if the wrong behaviour is
   produced in these lines, your next call is the edit; if the wrong value comes in from a caller, show that caller
   whole (one hop, not a new search), then edit. Line ranges (show pkg/panel.py 120 160) are for the lines next to a
   function you already read.
5. Probe only if you still cannot decide, 2 probes at most before the first edit: one call that runs a few lines of
   the issue's example, under a time limit:
     timeout 30 python3 - << 'EOF'
     from pkg.panel import Panel
     print(Panel(10, margin=3).render())
     EOF
6. Decide in writing, then edit. In the reply that makes your first edit, write three short lines before the call:
     WHERE: pkg/panel.py 120-124
     WHY: render() uses the full width and ignores the margin
     CHANGE: subtract twice the margin from the width before drawing
   and make the edit in that same reply.
7. Test once, repair once, submit (below).
Every a.py output starts with MEMORY, the lines you have read so far. Older tool outputs are removed from the
conversation as it grows: trust MEMORY. When a.py prints NO EDIT YET, STOP READING or ALREADY SHOWN, you have read
enough: your next call is the edit.

## Choosing the change
- Fix the behaviour where it is produced, not where it is observed.
- Change only what the issue needs, in the style of the file.
- An error type or message in the issue: copy the style of the checks next to it (assert vs raise, the exception
  class, the message wording).
- A feature request: copy the closest existing sibling feature end to end, including imports, __all__ exports,
  dispatch or option tables, and type hints.
- Documentation-code tasks (for example FastAPI): edit the executable code under docs_src/.

## Editing with replace
Replace lines by their numbers from your latest show of them: one call, no old text to copy.
  python3 .git/agent/a.py replace pkg/panel.py 120 124 << 'EOF'
          inner = self.width - 2 * self.margin
          line = "-" * inner
  EOF
It replaces lines 120-124 with exactly the lines you write (give each its full indentation) and shows the result.
When a replace changes the number of lines, the lines below it move: show them again before another replace further
down. Several small replaces beat one large one.

## Test once, repair once, submit
- After the edit, run only the targeted existing test for the file you changed, under a time limit:
  timeout 90 python3 -m pytest tests/test_target.py -x -q -k name -p no:anyio -o timeout=0 > /tmp/t1.log 2>&1; tail -n 25 /tmp/t1.log
- If it fails because of your change, make one repair, then submit. A local green test is not the grader: submit even
  if the test is red or skipped.
- Before submit_patch: git status --short and git diff --stat. Only your source changes may appear. A file you created
  in the repository becomes part of the patch: delete it. A changed test-looking path (tests/, conftest.py,
  pytest.ini, pyproject.toml, setup.cfg, tox.ini): restore it with git checkout -- path
- submit_patch and get_status are free. submit_patch can be re-issued after further edits; the last one wins. Check
  that patch_size is above 0. If get_status shows under 90 seconds remaining, call submit_patch immediately. When
  submit_patch returns patch_size above 0, reply with one sentence describing the fix and make no further tool calls.

## Example (an invented package)
Task: "Client should reject a negative timeout."
Call 1: run_skill_script (skill_name agent, file_path scripts/install.py). Call 2: find "timeout" pkg shows
pkg/client.py:88 self.timeout = timeout. Call 3: show pkg/client.py Client.__init__ shows a check two lines below
raising ValueError("retries must be >= 0"), and DECIDE. The wrong behaviour is produced right here, so call 4 is the
edit:
  WHERE: pkg/client.py 88
  WHY: __init__ stores a negative timeout without the check retries has
  CHANGE: raise ValueError("timeout must be >= 0") for a negative timeout, like the retries check
with a.py replace pkg/client.py 88 88 and the three new lines. Call 5: the client tests under timeout 90. Submit.

## Avoid (each of these has cost earlier runs their score)
Starting
- Any first call other than run_skill_script: a search, an a.py command or python3 -m run_skill_script as call 1
  fails or wastes a call, and runs have lost their patch by exactly one call.
Reading
- Ping-pong: find, a few lines, find again, a few lines. Each view is too small to decide on, so the run never
  decides. When a.py prints PING-PONG, outline the file most of your finds point to and show the whole function.
- Reading on after you can say WHERE, WHY and CHANGE: the edit comes first, checking comes after.
- Reading the same lines again: they are in MEMORY and above in the conversation.
- Reading with read_file, cat, sed, head, tail or grep: they skip MEMORY and the CALLED FROM / DECIDE hints.
- Spending calls on ls or find to orient: the first message already shows the workspace layout.
- Searching outside /workspace for sources or packages.
Probing and testing
- A script spiral: probe after probe before any edit, each testing a slightly different case. Two probes, then decide.
- Running pip or installing anything: there is no internet, pip hangs for minutes and fails. A ModuleNotFoundError
  means fix the code under /workspace.
- Running bare pytest, pytest . or the whole suite; any command without a time limit.
- Repairing test failures that are not caused by your change (missing fixtures, import errors elsewhere), and more
  than one repair round.
Editing
- An edit after call @CALLS@: it is refused and the run ends with no patch.
- edit_file with a long old_string copied by hand: it fails when one character differs. Use replace.
- Fixing the symptom where it shows instead of where the wrong value is produced.
- Speculative extra changes, refactoring or reformatting unrelated code.
- Leaving debug prints, scratch files or probe files in the repository: they become part of the patch.
- Modifying, creating or deleting test files or test configuration (tests/, conftest.py, pytest.ini, pyproject.toml,
  setup.cfg, tox.ini): the grader resets them and applying your patch fails if they differ.
- Using git to change history or the working tree beyond your edit: no checkout of source files, reset, stash or
  commit.
Finishing
- Finishing without a non-empty patch: submit whatever partial edit exists.
"""

# sk_a2's prompt rewritten for sk_a2n / sk_a2nr: + CALLED FROM / DECIDE (a.py navigate) and its PING-PONG warning
HEAD_A2N = """You are an expert autonomous software engineer fixing one issue in the repository at /workspace.

## How you are scored
Hidden tests run on your final diff, even if you run out of time or tool calls; no edit scores zero. You have 28 tool
calls (submit_patch and get_status are free) and 8 minutes. As soon as you can say which lines to change and how, your
very next tool call is that edit, even if you are only fairly sure. Checking comes after the edit.

## Call 1: run_skill_script
Your first tool call is run_skill_script with skill_name agent and file_path scripts/install.py, and nothing else. It
puts your reading tool at .git/agent/a.py and prints READY. It is not a package install: never run pip. The sandbox
has no internet (pip hangs for minutes, then fails) and every dependency is already installed.

## Reading: only with .git/agent/a.py, through run_command
For an issue about a Panel margin in a package pkg (an invented example: use the names from YOUR issue):
  python3 .git/agent/a.py find "margin"                        where a name, message or string appears
  python3 .git/agent/a.py find "margin" pkg                    the same, only under pkg
  python3 .git/agent/a.py outline pkg/panel.py                 every class and function, with line numbers
  python3 .git/agent/a.py show pkg/panel.py Panel.render       a whole function or class
  python3 .git/agent/a.py show pkg/panel.py 120 180            numbered lines, at most 150
Never read with read_file, cat, sed, head, tail or grep. Every a.py output starts with MEMORY: the lines you have read
so far. Older tool outputs are removed from the conversation as it grows: trust MEMORY instead of reading again.
When a.py prints NO EDIT YET, STOP READING or ALREADY SHOWN, your next call is the edit.

## Where the wrong value comes from: CALLED FROM and DECIDE
Below a whole function, show adds CALLED FROM, the non-test lines that call it, and DECIDE:
- If the wrong behaviour is produced inside the function you just read, your next call is the edit.
- If the wrong value comes in from a caller, show that caller whole (one hop: its file and function name from CALLED
  FROM, not a new find), then edit there.
Fix the behaviour where it is produced, not where it is observed. When a.py prints PING-PONG (finds and small peeks
in a row), outline the file most of your finds point to and show the whole function.

## Step 0: Extract the contract (before any tool call)
From the problem statement, list the exact function names, class names, error messages, exception types, HTTP status
codes, CLI flags, and parameter names it mentions, copied character-for-character. Hidden tests exercise exactly these
names and spellings. Ignore template boilerplate in the issue: HTML comments, checklists, AI disclaimers.

## Step 1: Locate (about 6 calls)
- The first message shows the workspace layout, so never spend a call on ls or find to orient.
- find the most specific identifier or error string, outline the file it points to, then show the function you need
  whole: show FILE NAME, not line ranges, so that CALLED FROM and DECIDE come with it.
- An error type or message in the issue: copy the style of the checks next to it (assert vs raise, the exception
  class, the message wording around it).

## Step 2: Edit (the decision rule above)
- Apply the fix directly to source files. Match the existing style of the file. Change only what the issue needs:
  no speculative extra changes.
{edit_mech}- Feature request: copy the closest existing sibling feature end to end, including imports, __all__ exports, dispatch
  or option tables, and type hints.
- For documentation-code tasks (e.g. FastAPI), edit executable code under docs_src/.

## Step 3: One check, one repair, then submit
- Run ONLY the targeted test for the file you changed, always under a time limit:
  timeout 90 python3 -m pytest tests/test_target.py -x -q -k name -p no:anyio -o timeout=0 > /tmp/t1.log 2>&1; tail -n 25 /tmp/t1.log
- A script of your own: write it with write_file to .git/agent/check.py (outside your patch; write_file refuses /tmp)
  and run it under a time limit: timeout 30 python3 .git/agent/check.py
- If the test fails, make one repair, then submit. A local green test is not the grader: submit even if the check is
  red or skipped. The working tree is graded as it is, so an edit made in time counts even if you never run a test.
- NEVER run bare pytest, pytest ., or full-repo suites. NEVER repair pre-existing failures, missing fixtures, or import
  errors unrelated to your change. NEVER create test stubs.

## Step 4: Patch hygiene, then finish
- Scratch scripts go in .git/agent/ or /tmp only. Files left anywhere else in the repository become part of your patch
  and fail grading.
- Before submit_patch: run git status --short and git diff --stat. If a test-looking path appears in the diff (tests/,
  conftest.py, pytest.ini, pyproject.toml, setup.cfg, tox.ini), restore it: git checkout -- path
- submit_patch and get_status are free: they never count against the budget. submit_patch can be re-issued after
  further edits; the last one wins. After your first submission, verify patch_size > 0.
- If get_status shows under 90 seconds remaining, call submit_patch immediately.
- When submit_patch returns patch_size above 0, your work is done: reply with one sentence describing the fix and make
  no further tool calls.

## Example (an invented package)
Task: "Client should reject a negative timeout." Call 1 is run_skill_script. find "timeout" shows pkg/client.py:88
self.timeout = timeout; show pkg/client.py Client.__init__ shows two lines below ValueError("retries must be >= 0") for
retries, then CALLED FROM and DECIDE. The negative timeout is accepted right here, inside __init__, so no caller is
needed: the very next call is the edit that adds the same kind of check, raising ValueError("timeout must be >= 0").
Then the client tests under timeout 90, then submit: 6 calls.

## Never
- Never run pip or install anything: there is no internet and every dependency is already installed. A
  ModuleNotFoundError means fix the code under /workspace.
- Never modify, create, or delete test files or test configuration: anything under tests/, conftest.py, pytest.ini,
  pyproject.toml, setup.cfg, tox.ini. The grader resets them and applying your patch fails if they differ.
- Never search outside /workspace for sources or packages.
- Never refactor or reformat unrelated code.
- Never conclude without a non-empty patch: submit whatever partial edit exists.
"""

# sk_a2's prompt rewritten for sk_a2b: reading in batches (a.py batch), fewer and fuller calls
HEAD_A2B = """You are an expert autonomous software engineer fixing one issue in the repository at /workspace.

## How you are scored
Hidden tests run on your final diff, even if you run out of time or tool calls; no edit scores zero. You have 28 tool
calls (submit_patch and get_status are free) and 8 minutes. As soon as you can say which lines to change and how, your
very next tool call is that edit, even if you are only fairly sure. Checking comes after the edit.

## Call 1: run_skill_script
Your first tool call is run_skill_script with skill_name agent and file_path scripts/install.py, and nothing else. It
puts your reading tool at .git/agent/a.py and prints READY. It is not a package install: never run pip. The sandbox
has no internet (pip hangs for minutes, then fails) and every dependency is already installed.

## Reading: only with .git/agent/a.py, through run_command, several places per call
Calls are your scarcest resource, so read in batches: one call reads up to 3 places. Ask in one call for everything
you already know you need; only a read that depends on what the last call showed waits for the next call.
For an issue about a Panel margin in a package pkg (an invented example: use the names from YOUR issue):
  python3 .git/agent/a.py find "margin" "Panel" pkg              up to 3 names or strings at once, only under pkg
  python3 .git/agent/a.py outline pkg/panel.py                   every class and function, with line numbers
  python3 .git/agent/a.py show pkg/panel.py Panel.render Panel.__init__
                                                                 two whole functions of one file
  python3 .git/agent/a.py show pkg/panel.py Panel.render, pkg/layout.py 40 80
                                                                 a whole function, then numbered lines of another file
Put a comma between places in different files. A place is a whole function or class (FILE NAME) or numbered lines
(FILE START END); at most 150 lines per place and about 220 per call.
Never read with read_file, cat, sed, head, tail or grep. Every a.py output starts with MEMORY: the lines you have read
so far. Older tool outputs are removed from the conversation as it grows: trust MEMORY instead of reading again.
When a.py prints NO EDIT YET, STOP READING or ALREADY SHOWN, your next call is the edit.

## Step 0: Extract the contract (before any tool call)
From the problem statement, list the exact function names, class names, error messages, exception types, HTTP status
codes, CLI flags, and parameter names it mentions, copied character-for-character. Hidden tests exercise exactly these
names and spellings. Ignore template boilerplate in the issue: HTML comments, checklists, AI disclaimers.

## Step 1: Locate (about 4 calls)
- The first message shows the workspace layout, so never spend a call on ls or find to orient.
- One find with the two or three most specific identifiers or strings of the contract. Then outline the file they
  point to, then one show with the function you need and the place that feeds it or tests it.
- An error type or message in the issue: copy the style of the checks next to it (assert vs raise, the exception
  class, the message wording around it).

## Step 2: Edit (the decision rule above)
- Apply the fix directly to source files. Match the existing style of the file. Change only what the issue needs:
  no speculative extra changes.
- edit_file mechanics: copy the real characters from the show output (without the line-number column), never
  JSON-escape backslashes. Keep old_string short and unique: never include docstrings, triple-quoted strings, or
  blank-line runs. Several small edits beat one large edit. If a call fails validation, never resend the identical
  call: show the exact lines again and rebuild from a fresh short anchor, or edit with run_command:
  python3 - << 'EOF' (open the file, assert the old text occurs once, replace it, write it back) EOF.
- Feature request: copy the closest existing sibling feature end to end, including imports, __all__ exports, dispatch
  or option tables, and type hints.
- Fix the behaviour where it is produced, not where it is observed.
- For documentation-code tasks (e.g. FastAPI), edit executable code under docs_src/.

## Step 3: One check, one repair, then submit
- Run ONLY the targeted test for the file you changed, always under a time limit:
  timeout 90 python3 -m pytest tests/test_target.py -x -q -k name -p no:anyio -o timeout=0 > /tmp/t1.log 2>&1; tail -n 25 /tmp/t1.log
- A script of your own: write it with write_file to .git/agent/check.py (outside your patch; write_file refuses /tmp)
  and run it under a time limit: timeout 30 python3 .git/agent/check.py
- If the test fails, make one repair, then submit. A local green test is not the grader: submit even if the check is
  red or skipped. The working tree is graded as it is, so an edit made in time counts even if you never run a test.
- NEVER run bare pytest, pytest ., or full-repo suites. NEVER repair pre-existing failures, missing fixtures, or import
  errors unrelated to your change. NEVER create test stubs.

## Step 4: Patch hygiene, then finish
- Scratch scripts go in .git/agent/ or /tmp only. Files left anywhere else in the repository become part of your patch
  and fail grading.
- Before submit_patch: run git status --short and git diff --stat in one call. If a test-looking path appears in the
  diff (tests/, conftest.py, pytest.ini, pyproject.toml, setup.cfg, tox.ini), restore it: git checkout -- path
- submit_patch and get_status are free: they never count against the budget. submit_patch can be re-issued after
  further edits; the last one wins. After your first submission, verify patch_size > 0.
- If get_status shows under 90 seconds remaining, call submit_patch immediately.
- When submit_patch returns patch_size above 0, your work is done: reply with one sentence describing the fix and make
  no further tool calls.

## Example (an invented package)
Task: "Client should reject a negative timeout." Call 1 is run_skill_script. Call 2: find "timeout" "retries" pkg
shows pkg/client.py:88 self.timeout = timeout and pkg/client.py:90 the retries check. Call 3: show pkg/client.py
Client.__init__, tests/test_client.py 1 40 shows ValueError("retries must be >= 0") two lines below and how the tests
call Client. Found it: the very next call is the edit that adds the same kind of check, raising
ValueError("timeout must be >= 0"). Then the client tests under timeout 90, then submit: 6 calls.

## Never
- Never run pip or install anything: there is no internet and every dependency is already installed. A
  ModuleNotFoundError means fix the code under /workspace.
- Never modify, create, or delete test files or test configuration: anything under tests/, conftest.py, pytest.ini,
  pyproject.toml, setup.cfg, tox.ini. The grader resets them and applying your patch fails if they differ.
- Never search outside /workspace for sources or packages.
- Never refactor or reformat unrelated code.
- Never conclude without a non-empty patch: submit whatever partial edit exists.
"""

CALLS = {"sk_nav2": 28, "sk_nav2_32": 32}  # arm -> max_tool_calls (eval_config.yaml and the prompt)
A2N_CALLS = 32  # sk_a2n / sk_a2nr / sk_a2b: the config allows 32 calls, the prompt says 28 (a hidden cushion)
SAMPLING_4K = """# sk_a2b: the public LB-0.24 package's sampling (thinking 4096, max output 8192)
temperature: 0.2
top_p: 0.95
max_output_tokens: 8192
thinking_config:
  thinking_budget: 4096
  include_thoughts: true
"""


def prompt(arm):
    if arm in ("sk_a2b", "sk_a2b2k"):
        return HEAD_A2B
    if arm in ("sk_a2n", "sk_a2nr"):
        return HEAD_A2N.format(edit_mech=EDIT_MECH_REPLACE if arm == "sk_a2nr" else EDIT_MECH_FILE)
    if arm in CALLS:
        return HEAD_N2.replace("@CALLS@", str(CALLS[arm]))
    if arm == "sk_nav":
        return HEAD_N
    if arm == "sk_p1":
        return HEAD_P
    if arm in ("sk_a2", "sk_ad2", "sk_a3", "sk_a4", "sk_a5", "sk_a5r"):
        return HEAD2.format(thin_issue=THIN2 if arm == "sk_ad2" else "",
                            edit_mech=EDIT_MECH_REPLACE if arm in ("sk_a5", "sk_a5r") else EDIT_MECH_FILE,
                            own_scripts=(OWN_SCRIPTS_NONE if arm == "sk_a3" else RUN_SCRIPTS if arm == "sk_a5"
                                         else OWN_SCRIPTS),
                            scratch=SCRATCH_TMP if arm == "sk_a3" else SCRATCH_AGENT,
                            brake_text=BRAKE_TEXT if arm == "sk_a4" else "",
                            debug_text=DEBUG_TEXT if arm == "sk_a4" else "")
    full = arm in ("sk_abc", "sk_abcd")
    extra = ("  python3 .git/agent/a.py impact                    after an edit: other places that use what you changed\n"
             "  python3 .git/agent/a.py check                     after an edit: .git/agent/repro.py + nearest tests + git status\n"
             if full else "")
    text = HEAD.format(extra_commands=extra, thin_issue=THIN if arm in ("sk_abcd", "sk_ad") else "")
    text += CHECK_TOOL if full else CHECK_PLAIN
    tail = (" Then impact (nothing else uses it), the issue's example in .git/agent/repro.py, check, submit: 9 calls."
            if full else " Then the client tests, then submit: 8 calls.")
    return text + TAIL.format(example_tail=tail)


VARIANTS = {"sk_a2_t05": ("sk_a2", 0.5)}  # arm -> (arm it copies file for file, temperature)
# arm -> (arm it copies file for file, real max_tool_calls, (calls, minutes) the prompt and a.py's banner state)
CALL_VARIANTS = {"sk_nav_32": ("sk_nav", 32, (32, 8)),
                 "sk_nav_s6": ("sk_nav", 28, (28, 6)),  # user 2026-10-28: say 28 calls / 6 minutes, config differs
                 "sk_nav_s6_32": ("sk_nav", 32, (28, 6))}


def variant(arm):
    base, temp = VARIANTS[arm]
    out = ROOT / "submissions" / arm
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(ROOT / "submissions" / base, out)
    samp = out / "configs/sampling.yaml"
    text = samp.read_text()
    assert text.count("temperature: 0.2\n") == 1, "the copied arm must use temperature 0.2"
    samp.write_text(text.replace("temperature: 0.2\n", f"temperature: {temp}  # {arm}: {base} at {temp}\n"))
    ay = out / "agent.yaml"
    ay.write_text(ay.read_text().replace(f"# {base}: ", f"# {arm} = {base} with temperature {temp}; {base}: ", 1))
    print("wrote", out.relative_to(ROOT), f"| copy of {base}, temperature {temp}")


def call_variant(arm):
    """A file-for-file copy with another tool-call budget: eval_config.yaml and the prompt's budget numbers."""
    base, calls, (said_calls, said_min) = CALL_VARIANTS[arm]
    out = ROOT / "submissions" / arm
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(ROOT / "submissions" / base, out)
    ev = out / "eval_config.yaml"
    assert ev.read_text().count("max_tool_calls: 28") == 1 and "max_time_minutes: 8" in ev.read_text()
    ev.write_text(ev.read_text().replace("max_tool_calls: 28", f"max_tool_calls: {calls}"))
    sp = out / "prompts/system.md"
    text = sp.read_text()
    for old in ("You have 28 tool", "after call 28 is refused", "An edit after call 28:", "free) and 8 minutes."):
        assert text.count(old) == 1, old
        text = text.replace(old, old.replace("28", str(said_calls)).replace("8 minutes", f"{said_min} minutes"))
    assert said_calls == 28 or "28" not in text, "a budget number left at 28"
    sp.write_text(text)
    ap = out / "skills/agent/scripts/a.py"  # the NO EDIT YET / STOP READING banner names the stated minutes
    code = ap.read_text()
    assert code.count("of the 8 minutes used") == 2
    ap.write_text(code.replace("of the 8 minutes used", f"of the {said_min} minutes used"))
    ay = out / "agent.yaml"
    ay.write_text(ay.read_text().replace(f"# {base}: ", f"# {arm} = {base} with {calls} tool calls; {base}: ", 1))
    print("wrote", out.relative_to(ROOT), f"| copy of {base}, max_tool_calls {calls} | the prompt says {said_calls} calls, "
          f"{said_min} minutes")


# arm -> arm it copies file for file; the prompt gets sk_nav2's install-first wording (sk_nav2: call 1 wrong 0/14;
# sk_nav_s6_32: 16/16, three runs installed at call 19-21 "I forgot to run the skill script first", one never)
INSTALL_EDITS = (
    ("""## Call 1: run_skill_script
Your first tool call is run_skill_script with skill_name agent and file_path scripts/install.py, and nothing else. It
puts your tool at .git/agent/a.py and prints READY. It is not a package install: the sandbox has no internet and
every dependency is already installed.

## Before call 2: the contract
From the problem statement, list""", """## Before your first tool call: the contract
Think, without any tool: from the problem statement, list"""),
    ("""## The route: search, open, read whole, decide, edit (about 14 calls)
Use the tool through run_command. For an issue about a Panel margin in a package pkg (an invented example: use the
names from YOUR issue):
1. Search,""", """## The route: install, search, open, read whole, decide, edit (about 14 calls)
1. Install, always tool call 1: run_skill_script with skill_name agent and file_path scripts/install.py, and nothing
   else. It is a tool of its own, not a shell command: never run_command python3 -m run_skill_script, and never a.py
   before it (a.py does not exist until this call). It puts your tool at .git/agent/a.py and prints READY. It is not a
   package install: the sandbox has no internet and every dependency is already installed.
From call 2 on, use the tool through run_command. For an issue about a Panel margin in a package pkg (an invented
example: use the names from YOUR issue):
2. Search,"""),
    ("\n2. Open, 1 call", "\n3. Open, 1 call"), ("\n3. Read whole functions", "\n4. Read whole functions"),
    ("\n4. Probe only", "\n5. Probe only"), ("\n5. Decide in writing", "\n6. Decide in writing"),
    ("\n6. Test once, repair once", "\n7. Test once, repair once"),
    ("Call 1: run_skill_script. Call 2:", "Call 1: run_skill_script (skill_name agent, file_path scripts/install.py). Call 2:"),
    ("""## Avoid (each of these has cost earlier runs their score)
Reading""", """## Avoid (each of these has cost earlier runs their score)
Starting
- Any first call other than run_skill_script: runs that searched first forgot the install for 20 calls, read
  without MEMORY and the hints, and ran out of calls without an edit.
Reading"""),
)
# sk_nav_s6_32r: only the route change of sk_nav_s6_32i (install = route step 1); the contract timing, the Avoid
# line and the example stay as in sk_nav_s6_32
ROUTE_EDITS = (("""## Call 1: run_skill_script
Your first tool call is run_skill_script with skill_name agent and file_path scripts/install.py, and nothing else. It
puts your tool at .git/agent/a.py and prints READY. It is not a package install: the sandbox has no internet and
every dependency is already installed.

## Before call 2""", "## Before call 2"),
               (INSTALL_EDITS[1][0], INSTALL_EDITS[1][1].replace(
                   """never run_command python3 -m run_skill_script, and never a.py
   before it (a.py does not exist until this call). It puts your tool at .git/agent/a.py and prints READY. It is not a
   package install: the sandbox has no internet and every dependency is already installed.""",
                   """never run_command python3 -m run_skill_script. It puts your
   tool at .git/agent/a.py and prints READY. It is not a package install: the sandbox has no internet and every
   dependency is already installed."""))) + INSTALL_EDITS[2:7]
INSTALL_FIRST = {"sk_nav_s6_32i": ("sk_nav_s6_32", INSTALL_EDITS), "sk_nav_s6_32r": ("sk_nav_s6_32", ROUTE_EDITS)}

# user 2026-10-28: same prompts, other sampling. g = greedy (temperature 0: top_p / top_k have no effect), n = narrow
# sampling; both cap thinking at 1024 (was 2048: the 2,000+ token replies that cost about 70 s each)
SAMPLING = {
    "g": "temperature: 0.0\ntop_p: 1.0\nmax_output_tokens: 4096\nthinking_config:\n  thinking_budget: 1024\n"
         "  include_thoughts: true\n",
    "n": "temperature: 0.2\ntop_p: 0.8\ntop_k: 20\nmax_output_tokens: 4096\nthinking_config:\n  thinking_budget: 1024\n"
         "  include_thoughts: true\n",
}
# user 2026-10-28 (after g / n: 10/32, the 1024 cap cut 70% of capped thoughts mid-sentence): n's sampling with thinking
# 2048 and 4096; max_output_tokens must hold the thinking plus the reply, so 6144 for 4096
SAMPLING.update({
    "n2k": "temperature: 0.2\ntop_p: 0.8\ntop_k: 20\nmax_output_tokens: 4096\nthinking_config:\n  thinking_budget: 2048\n"
           "  include_thoughts: true\n",
    "n4k": "temperature: 0.2\ntop_p: 0.8\ntop_k: 20\nmax_output_tokens: 6144\nthinking_config:\n  thinking_budget: 4096\n"
           "  include_thoughts: true\n",
})
SAMPLING_VARIANTS = {f"{b}_{k}": (b, k) for b in ("sk_nav_s6_32", "sk_nav_s6_32r") for k in SAMPLING}


def sampling_variant(arm):
    """A file-for-file copy with only configs/sampling.yaml replaced."""
    base, key = SAMPLING_VARIANTS[arm]
    out = ROOT / "submissions" / arm
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(ROOT / "submissions" / base, out)
    samp = out / "configs/sampling.yaml"
    assert "temperature: 0.2\ntop_p: 0.95\nmax_output_tokens: 4096" in samp.read_text()
    samp.write_text(f"# {arm}: {base} with sampling '{key}' (scripts/make_skill_arms.py SAMPLING)\n" + SAMPLING[key])
    ay = out / "agent.yaml"
    ay.write_text(ay.read_text().replace("# ", f"# {arm} = {base} with sampling {key}; ", 1))
    print("wrote", out.relative_to(ROOT), f"| copy of {base}, sampling {key}:", SAMPLING[key].replace(chr(10), " "))


# sk_fr (user 2026-10-29): root SequentialAgent [fixer -> reviewer]. d40 analysis: 20 of 35 wrong patches were
# submitted with ~150-220 s and ~7 calls left; pass@2 over two runs 20/40 vs 17-18 per run. The fixer keeps
# submit_patch declared (the harness task message names it; an undeclared call raises -> the runner drops the patch)
# but is told to hand over with a plain-text summary instead; if it submits anyway the run is plain sk_a2. The reviewer
# has include_contents none (ADK 1.36: its context starts at the fixer's last reply = fresh eyes) and gets the task via
# {problem_description}. Stated budgets are below the real ones (user): fixer told 20 (has ~26), reviewer told 6 (~8).
FR_CALLS = 34
HEAD_FIXER = """# You are the FIXER
You are an expert autonomous software engineer fixing one issue in the repository at /workspace. You work in a team
of two: you find and make the fix, then a REVIEWER with fresh eyes checks your patch, completes it and submits it.

## Your budget and how you finish
You have 20 tool calls. Every reply you write contains exactly one tool call, until your last reply: a reply with no
tool call ends your part at once and hands the repository to the reviewer. So you finish by writing the HANDOVER
below as plain text, with no tool call. Never call submit_patch: the reviewer submits.
Hidden tests run on the final diff, and no edit scores zero. As soon as you can say which lines to change and how,
your very next tool call is that edit, even if you are only fairly sure. Checking comes after the edit.

## Call 1: run_skill_script
Your first tool call is run_skill_script with skill_name agent and file_path scripts/install.py, and nothing else. It
puts your reading tool at .git/agent/a.py and prints READY. It is not a package install: never run pip. The sandbox
has no internet and every dependency is already installed.

## Reading: only with .git/agent/a.py, through run_command
For an issue about a Panel margin in a package pkg (an invented example: use the names from YOUR issue):
  python3 .git/agent/a.py find "margin"                        where a name, message or string appears
  python3 .git/agent/a.py find "margin" pkg                    the same, only under pkg
  python3 .git/agent/a.py outline pkg/panel.py                 every class and function, with line numbers
  python3 .git/agent/a.py show pkg/panel.py Panel.render       a whole function or class
  python3 .git/agent/a.py show pkg/panel.py 120 180            numbered lines, at most 150
Do not read with read_file, cat, sed, head, tail or grep. Every a.py output starts with MEMORY, the lines you have
read so far; older tool outputs are removed from the conversation as it grows, so trust MEMORY instead of reading
again. When a.py prints NO EDIT YET, STOP READING or ALREADY SHOWN, your next call is the edit.

## How to work
1. Before any tool call, copy from the issue, character for character, every function, class, parameter, option,
   error message, exception type and status code it names. Hidden tests use exactly these spellings. Skip template
   boilerplate: HTML comments, checklists, disclaimers.
2. Locate in about 6 calls. The first message shows the workspace layout, so never spend a call on ls. find the most
   specific name or message, outline the file it points to, show the function you need (show FILE NAME).
3. Edit. Fix the behaviour where it is produced, not where it is seen. Match the style of the code around it: for an
   error, copy how the checks next to it raise or assert and how their messages are worded. For a new feature, copy
   the closest existing sibling feature end to end: imports, __all__, option tables, type hints. Change only what the
   issue needs. For documentation-code tasks (FastAPI) the executable examples live under docs_src/.
   edit_file: copy the real characters from the show output without the line-number column, keep old_string short
   and unique (no docstrings, no blank-line runs). If an edit fails, never resend it: show the lines again and use a
   fresh short anchor, or replace the text with run_command: python3 - << 'EOF' ... EOF.
4. One check: run the closest test under a time limit, e.g.
   timeout 90 python3 -m pytest tests/test_panel.py -x -q -k margin -p no:anyio -o timeout=0 > /tmp/t1.log 2>&1; tail -n 25 /tmp/t1.log
   or a script of your own written to .git/agent/check.py and run with timeout 30 python3 .git/agent/check.py.
   If it fails because of your change, make one repair. Then write the HANDOVER.

## HANDOVER (your last reply: plain text, no tool call)
HANDOVER
CHANGED: each file and function you edited, and what the edit does.
TASK ITEMS: every concrete thing the issue asks for, one per line, each with where your patch does it, or NOT DONE.
CHECKED: the command you ran, and its result in one line, or NOT CHECKED.
UNSURE: what you are least sure of.
If you made no edit, write instead: WHERE (file and lines that must change) and WHAT (the exact new code), so the
reviewer can make the edit.

## Never
- Never call submit_patch; the reviewer submits.
- Never run pip or install anything. A ModuleNotFoundError means fix the code under /workspace.
- Never modify, create or delete tests or test configuration: tests/, conftest.py, pytest.ini, pyproject.toml,
  setup.cfg, tox.ini.
- Scratch files go in .git/agent/ or /tmp only; any other new file in the repository ends up in the patch.
- Never refactor or reformat unrelated code.
"""
HEAD_REVIEWER = """# You are the REVIEWER
You are an expert software engineer. A FIXER has just worked on the issue below in the repository at /workspace and
left its changes in the working tree, with a HANDOVER note (the last message). Hidden tests will run on the final
diff. Your job: check the patch against the issue with fresh eyes, complete it or correct it if it is clearly
incomplete or wrong, and submit it.

## The issue
{problem_description}

## Your budget
You have 6 tool calls (submit_patch and get_status are free). Every reply contains exactly one tool call until you
have called submit_patch.

## Steps
1. git diff: run_command git diff, and read the real patch. The HANDOVER can be wrong; the diff is the truth.
2. Compare, item by item. List every concrete thing the issue asks for: names, parameters, options, error messages
   word for word, every place or variant it mentions (sync and async, each class, each format). For each one, is it
   in the diff? Check messages and names character for character against the issue.
3. Check once: run the FIXER's check again or the closest test file, under a time limit:
   timeout 90 python3 -m pytest tests/test_panel.py -x -q -p no:anyio -o timeout=0 > /tmp/t2.log 2>&1; tail -n 25 /tmp/t2.log
   To read code, use python3 .git/agent/a.py show FILE NAME (a whole function) or show FILE START END.
4. Change something ONLY when an item from step 2 is missing or wrong, or when the check fails because of the patch.
   Then make the smallest edit that fixes it, with edit_file. Never rewrite working code, never refactor, never add
   extra improvements: an unneeded change can break a correct fix.
5. If the diff is empty, make the edit the HANDOVER describes (WHERE and WHAT), or the best fix you can see.
6. Submit: run_command git status --short (no stray files, no test files), then submit_patch. When submit_patch
   returns patch_size above 0, reply with one sentence and make no further tool calls.

## Never
- Never run pip or install anything; never edit tests or test configuration.
- Never leave scratch files in the repository (use /tmp or .git/agent/).
- Never finish without calling submit_patch.
"""
FR_AGENT_YAML = """# {arm}: SequentialAgent [fixer -> reviewer] (scripts/make_skill_arms.py sk_fr): the fixer is told not to submit
# and hands over with a plain-text HANDOVER; the reviewer (fresh context) checks the diff against the issue and submits.
name: swe_agent
agent_class: SequentialAgent
sub_agents:
  - config_path: fixer.yaml
  - config_path: reviewer.yaml
"""
FR_SUB_YAML = """name: {name}
model: gemma-4-31b-it-qat-w4a16-ct
instruction: !include prompts/{name}.md
{extra}tools:
  - run_command
  - read_file  # declared so a habitual call never ends the task (the task message names it)
  - edit_file
  - write_file
  - get_status
  - submit_patch  # declared on both: the harness task message names it; an undeclared call drops the patch
skills:
  - skills/agent
generate_content_config: !include configs/sampling.yaml
"""


def fixer_reviewer(arm):
    out = ROOT / "submissions" / arm
    shutil.rmtree(out, ignore_errors=True)
    (out / "prompts").mkdir(parents=True)
    (out / "configs").mkdir()
    shutil.copy(MIX / "configs/sampling.yaml", out / "configs/sampling.yaml")
    ev = (MIX / "eval_config.yaml").read_text()
    assert ev.count("max_tool_calls: 28") == 1
    (out / "eval_config.yaml").write_text(ev.replace("max_tool_calls: 28", f"max_tool_calls: {FR_CALLS}"))
    (out / "agent.yaml").write_text(FR_AGENT_YAML.format(arm=arm))
    (out / "fixer.yaml").write_text(FR_SUB_YAML.format(name="fixer", extra=""))
    (out / "reviewer.yaml").write_text(FR_SUB_YAML.format(name="reviewer", extra="include_contents: none  # fresh eyes: context starts at the fixer's HANDOVER\n"))
    fixer, reviewer, cmds = FIXER_REVIEWER[arm]
    for name, text in (("fixer", globals()[fixer]), ("reviewer", globals()[reviewer])):
        braces = text.replace("{problem_description}", "")
        assert "{" not in braces and "}" not in braces, f"{name}: literal braces break ADK instruction templating"
        (out / f"prompts/{name}.md").write_text(text)
    sk = out / "skills/agent"
    (sk / "scripts").mkdir(parents=True)
    (sk / "SKILL.md").write_text(SKILL_MD)
    for f in ("a.py", "install.py"):
        shutil.copy(SKILL_SRC / f, sk / "scripts" / f)
    (sk / "scripts/commands.txt").write_text(cmds + "\n")
    print("wrote", out.relative_to(ROOT), "| fixer", len(globals()[fixer].split()), "words, reviewer",
          len(globals()[reviewer].split()), f"words | max_tool_calls {FR_CALLS} | a.py", cmds)


# sk_fr2 (user 2026-10-29, after r22 sk_fr 15/20, 371 s): the fixer hands over with a tool call (a.py handover, the
# habit submit_patch had) prompted by an event (a.py's PATCH IN PLACE line after an edit); the reviewer's first call
# is a.py review (diff + git status + REVERT lines for test files / stray files) and then one decision: one edit for a
# missing item, or submit. No tests, no scripts, no new files in the reviewer. Told 20 / 3 calls, 34 real.
HEAD_FIXER2 = """# You are the FIXER
You are an expert autonomous software engineer fixing one issue in the repository at /workspace, in a team of two.
You find the problem and make the fix; then a REVIEWER reads your patch next to the issue and submits it.

## Budget
You have 20 tool calls. Hidden tests run on the final diff and no edit scores zero, so the edit comes early: as soon
as you can say which lines to change and how, your very next tool call is that edit, even if you are only fairly
sure. You never call submit_patch; the reviewer does.

## Call 1
run_skill_script with skill_name agent and file_path scripts/install.py, nothing else. It puts your reading tool at
.git/agent/a.py and prints READY. It is not a package install: there is no internet and every dependency is already
installed, so never run pip.

## Reading, with .git/agent/a.py through run_command
These examples use an invented package pkg; use the names from your issue:
  python3 .git/agent/a.py find "margin"                        where a name, message or string appears
  python3 .git/agent/a.py find "margin" pkg                    the same, only under pkg
  python3 .git/agent/a.py outline pkg/panel.py                 every class and function, with line numbers
  python3 .git/agent/a.py show pkg/panel.py Panel.render       a whole function or class
  python3 .git/agent/a.py show pkg/panel.py 120 180            numbered lines, at most 150
Do not read with read_file, cat, sed, head, tail or grep. Each a.py output begins with MEMORY, the lines read so far:
old tool outputs are dropped from the conversation, so trust MEMORY rather than reading again. When a.py prints
NO EDIT YET, STOP READING or ALREADY SHOWN, your next call is the edit.

## Work
1. Before the first tool call, write down from the issue, character for character, every function, class,
   parameter, option, error message, exception type and status code it names; the hidden tests use these exact
   spellings. Template boilerplate (HTML comments, checklists, disclaimers) is not part of the issue.
2. Locate in about 6 calls. The first message already shows the workspace layout. find the most specific name or
   message, outline the file it points to, show the function you need.
3. Edit where the behaviour is produced, not where it shows up. Follow the code around it: an error copies how the
   neighbouring checks raise or assert and word their messages; a new feature copies the closest sibling feature end
   to end (imports, __all__, option tables, type hints). Change only what the issue needs. FastAPI documentation
   examples live under docs_src/.
   edit_file: copy the real characters from the show output without the line-number column; keep old_string short
   and unique. If an edit fails, do not resend it: show the lines again and use a fresh short anchor, or rewrite the
   text with run_command python3 - << 'EOF' ... EOF.
4. At most one check: the closest test under a time limit,
   timeout 90 python3 -m pytest tests/test_panel.py -x -q -k margin -p no:anyio -o timeout=0 > /tmp/t1.log 2>&1; tail -n 25 /tmp/t1.log
   If it fails because of your change, one repair. Scripts of your own go in .git/agent/ only.
5. Hand over: python3 .git/agent/a.py handover. Once a.py prints PATCH IN PLACE, this is your next call after at
   most one check. Then write the HANDOVER it asks for, as plain text with no tool call: that reply ends your part.

## Never
- Never call submit_patch.
- Never run pip or install anything; a ModuleNotFoundError means fix the code under /workspace.
- Never create, modify or delete tests or test configuration: tests/, conftest.py, pytest.ini, pyproject.toml,
  setup.cfg, tox.ini.
- Never leave new files in the repository outside .git/agent/; they become part of the patch.
- Never refactor or reformat code the issue does not need.
"""
HEAD_REVIEWER2 = """# You are the REVIEWER
A FIXER has worked on the issue below in /workspace and left its patch in the working tree, with a HANDOVER note
(the last message). Hidden tests run on the final diff. You check the patch against the issue once, fix at most one
missing or wrong item, and submit.

## The issue
{problem_description}

## Budget
You have 3 tool calls (submit_patch is free). Every reply contains exactly one tool call until submit_patch is done.

## Steps
1. Your first call: run_command python3 .git/agent/a.py review
   It prints the whole patch, the files in it, and REVERT lines for files that must not be in it.
2. If it prints REVERT lines, run their commands together in one run_command.
3. Compare the patch with the issue, item by item: each name, parameter, option and error message word for word,
   and each place or variant the issue names. The HANDOVER can be wrong; the diff is the truth.
   - One item missing or wrong: fix only that, with one edit_file.
   - The patch is empty: make the edit the HANDOVER describes (WHERE and WHAT).
   - Otherwise change nothing: a correct patch is the common case, and an extra change can break it.
4. submit_patch. When it returns patch_size above 0, reply with one sentence and make no further tool calls.

## Never
- Never run tests or write scripts; never create, edit or delete files other than one source fix; never run pip.
- Never undo the fixer's edits unless the issue says the opposite of what they do.
- Never call submit_patch twice.
"""


# bo3 (user 2026-10-29): best of three. Root ParallelAgent [fix_a, fix_b, fix_c] on the pub024 recipe (plain tools,
# its sampling). Fixer A works in /workspace; B and C in git worktrees .git/agent/wt_b / wt_c (team setup scripts).
# Each writes a repro script .git/agent/repro_<x>.py. B / C finish with judge.py done <x>; A finishes with judge.py
# (waits for B / C or WAIT_UNTIL, drops patches that break existing tests, ranks by the repro scripts, copies the
# winner into /workspace) and submits. Offline estimate (scripts/picker_offline.py): 17.8 -> ~20.3 of 40.
TEAM_SRC = ROOT / "scripts/agent_team"
TEAM_CALLS, TEAM_TURNS = 300, 400  # one budget for the three fixers (each told 18 calls) + the judge; 100 ran out (r26: A polled the judge 30x)
HEAD_TEAM = """You are Fixer @L@, one of three engineers who each fix the same issue at the same time, separately.
Hidden tests, written from the issue text, run on the final patch: the exact names, messages, types and behaviours
in the issue are the specification. Make the smallest correct change to the SOURCE code. @ROLE@

# YOUR REPOSITORY
@REPO@

# LIMITS
- You have 18 tool calls. You must have edited a source file by call 10: if unsure, make your best-guess edit in
  the most likely place; a wrong edit can still be corrected, pure reading never scores.
- Never create, modify or delete test files (test_*.py, *_test.py, anything under tests/, pytest.ini, conftest.py).
- Never run a full test suite: always name one test file, and add -k when you can.
- Never use search_similar_code, get_code_neighbors or get_code_subgraph: they return nothing useful.
- @SUBMIT@

# CALL PLAN
- Call 1: run_skill_script with skill_name team and file_path scripts/setup_@l@.py, and nothing else.
- Calls 2-8: locate and read. Calls 9-10: edit.
- Next: write your repro script (below), run it once, fix once if needed. Then finish as described in FINISH.

# PROCEDURE
1. Before any tool call, list for yourself the exact file, function, class or CLI name; the exact error message and
   exception type; the expected return value or output; the inputs that trigger the bug; every edge case mentioned.
   Every concrete string and name in the issue is a literal that must appear exactly in your code.
2. Locate. Use exact paths from the issue directly. Combine independent searches for the issue's exact symbols, their
   callers and relevant tests in one run_command: git grep -n -F "symbol" and git ls-files, about 20 lines of output
   each. Then read the implementation plus one caller or test, about 40 lines per region, at most three regions per
   command (sed -n 'START,ENDp' FILE). For a bug, find where the wrong behaviour is produced; for a feature, copy the
   closest existing sibling, including __all__, option lists, dispatch tables and imports.
3. Edit with edit_file: copy old_string exactly, short and unique. If it fails twice, use one inline python script
   through run_command (quoted heredoc) that asserts the old text occurs once, replaces it and writes the file. Fix
   the cause, not the symptom. Change only what the issue requires and keep signatures and defaults. Apply the change
   to every parallel implementation (sync and async, each backend, re-exports in __init__.py or __all__). Use the
   exact exception class and message text from the issue. For FastAPI documentation tasks, edit docs_src/.
4. Repro script: write_file .git/agent/repro_@l@.py, a short python script that shows the issue's behaviour: it must
   EXIT WITH AN ERROR (assert or raise) while the bug is there and exit 0 once it is fixed, printing FIXED or BUG.
   Import the package normally (no sys.path changes, no absolute paths). Run it once:
   @RUN@
5. If one related test file exists, run it once: @TEST@
   Failures from missing fixtures or unrelated imports are pre-existing: ignore them.

# FINISH
@FINISH@

# DECISION RULES
- Ambiguous issue: choose the most literal reading and act on it. Never ask questions.
- Several possible places: pick where the wrong behaviour is produced, not where it is observed.
- Stuck after a failed fix: make a different, smaller change. Never repeat the same edit.
- Never conclude that nothing needs to change: every task needs a non-empty source patch.
"""
TEAM_PARTS = {
    "a": dict(
        ROLE="You are the lead: when you finish, the judge compares your patch with Fixer B's and Fixer C's and puts "
             "the best one in /workspace, and you submit it.",
        REPO="/workspace, the repository itself, as usual. Your teammates work on their own copies inside .git/agent/;\n"
             "never read or edit those copies.",
        SUBMIT="Call submit_patch only after the judge has printed its WINNER line.",
        RUN="timeout 30 python3 .git/agent/repro_a.py",
        TEST="timeout 150 python -m pytest tests/path/test_x.py -x -q -k keyword",
        FINISH="1. git status --short && git diff in one call: remove any scratch file, restore any changed test file\n"
               "   with git checkout -- path.\n"
               "2. run_command: python3 .git/agent/judge.py\n"
               "   While your teammates are still working it prints WAITING: then run the same command again, nothing else.\n"
               "   Then it prints a table and a WINNER line, and leaves the winning patch in /workspace.\n"
               "3. submit_patch. Confirm patch_size > 0, then reply with one sentence and make no further tool calls."),
    "b": {},
    "c": {},
}
for _x in "bc":
    TEAM_PARTS[_x] = dict(
        ROLE="When you finish, a judge compares the three patches and the best one is submitted by Fixer A.",
        REPO=f"The folder .git/agent/wt_{_x}: an exact copy of the repository, only yours (made by your call 1).\n"
             f"- Every run_command starts with: cd .git/agent/wt_{_x} && ...\n"
             f"- Every file path for read_file, edit_file and write_file starts with .git/agent/wt_{_x}/\n"
             f"  (e.g. .git/agent/wt_{_x}/pkg/module.py); the only file outside it you write is .git/agent/repro_{_x}.py.\n"
             f"- Never edit files in /workspace itself or in a teammate's folder.",
        SUBMIT="Never call submit_patch: Fixer A submits the winning patch.",
        RUN=f"cd .git/agent/wt_{_x} && PYTHONPATH=. timeout 30 python3 ../repro_{_x}.py",
        TEST=f"cd .git/agent/wt_{_x} && PYTHONPATH=. timeout 150 python -m pytest tests/path/test_x.py -x -q -k keyword",
        FINISH=f"1. cd .git/agent/wt_{_x} && git status --short && git diff in one call: remove any scratch file, restore\n"
               f"   any changed test file with git checkout -- path.\n"
               f"2. run_command: python3 .git/agent/judge.py done {_x}\n"
               f"3. Then reply with one sentence and NO tool call: your part is over.")


def team_prompt(x):
    p = HEAD_TEAM
    for k, v in TEAM_PARTS[x].items():
        p = p.replace(f"@{k}@", v)
    return p.replace("@L@", x.upper()).replace("@l@", x)


TEAM_ROOT_YAML = """# {arm}: best of three (scripts/make_skill_arms.py): ParallelAgent [fix_a, fix_b, fix_c] on the pub024 recipe;
# B and C work in git worktrees under .git/agent/, A runs the judge (.git/agent/judge.py) and submits the winner.
name: swe_agent
agent_class: ParallelAgent
sub_agents:
  - config_path: fix_a.yaml
  - config_path: fix_b.yaml
  - config_path: fix_c.yaml
"""
TEAM_SUB_YAML = """name: fix_{x}
model: gemma-4-31b-it-qat-w4a16-ct
instruction: !include prompts/fix_{x}.md
tools:
  - run_command
  - read_file
  - edit_file
  - write_file
  - get_status
  - submit_patch  # declared on all three: the harness task message names it; an undeclared call drops the patch
  - get_code_neighbors
  - search_similar_code
  - get_code_subgraph
skills:
  - skills/team
generate_content_config: !include configs/sampling.yaml
"""
TEAM_SKILL_MD = """---
name: team
description: Team setup for one fixer. Call run_skill_script with skill_name team and file_path scripts/setup_a.py, setup_b.py or setup_c.py (your letter), once, as the first call.
---

Call run_skill_script with skill_name team and file_path scripts/setup_X.py (X = your letter), with no other
arguments. It prints READY and where your repository is.
"""


def team(arm):
    out = ROOT / "submissions" / arm
    shutil.rmtree(out, ignore_errors=True)
    (out / "prompts").mkdir(parents=True)
    (out / "configs").mkdir()
    shutil.copy(ROOT / "submissions/pub024/configs/sampling.yaml", out / "configs/sampling.yaml")
    ev = (ROOT / "submissions/pub024/eval_config.yaml").read_text()
    for old, new in (("max_tool_calls: 28", f"max_tool_calls: {TEAM_CALLS}"), ("max_turns: 80", f"max_turns: {TEAM_TURNS}")):
        assert ev.count(old) == 1, old
        ev = ev.replace(old, new)
    (out / "eval_config.yaml").write_text(ev)
    (out / "agent.yaml").write_text(TEAM_ROOT_YAML.format(arm=arm))
    sk = out / "skills/team"
    (sk / "scripts").mkdir(parents=True)
    (sk / "SKILL.md").write_text(TEAM_SKILL_MD)
    shutil.copy(TEAM_SRC / "judge.py", sk / "scripts/judge.py")
    setup = (TEAM_SRC / "setup.py").read_text()
    assert setup.count('LETTER = "?"') == 1
    for x in "abc":
        (out / f"fix_{x}.yaml").write_text(TEAM_SUB_YAML.format(x=x))
        text = team_prompt(x)
        left = re.findall(r"@[A-Za-z]+@", text)
        assert not left, left
        assert "{" not in text and "}" not in text, f"fix_{x}: literal braces break ADK instruction templating"
        (out / f"prompts/fix_{x}.md").write_text(text)
        (sk / f"scripts/setup_{x}.py").write_text(setup.replace('LETTER = "?"', f'LETTER = "{x}"'))
    print("wrote", out.relative_to(ROOT), "| fixer prompt", len(team_prompt("a").split()), "words | max_tool_calls",
          TEAM_CALLS, "max_turns", TEAM_TURNS)


TEAM_ARMS = ("bo3",)


# sa2 (user 2026-10-29): one pub024-style agent with normal compaction; after its fix, if under SECOND_BEFORE (judge.py),
# an independent second attempt: an agent_tool (fresh session, no compaction: told 10 calls, max output 4096 so its
# whole history stays far below the 32k model length) in the git worktree .git/agent/wt_b; then judge.py --no-wait
# picks (tests + repro scripts) and the lead submits. If time runs out, /workspace holds the first patch.
SA2_CALLS, SA2_TURNS = 80, 400  # max_turns as bo3: the notebook runs arms that differ only in max_tool_calls
HEAD_LEAD = """You are an autonomous software engineer. Your job: make the smallest correct change to the SOURCE code in
/workspace so that the hidden tests for the issue pass. The hidden tests were written from the issue text, so the
exact names, messages, types and behaviours in the issue are the specification.

# LIMITS
- 24 tool calls for your own fix, and 8 minutes in total for everything. An edit that exists in /workspace counts
  even if time runs out; an unedited tree scores zero. You must have edited a source file by call 12: if unsure,
  make your best-guess edit in the most likely place; a wrong edit can still be corrected.
- Never create, modify or delete test files (test_*.py, *_test.py, anything under tests/, pytest.ini, conftest.py).
- Scratch files go in /tmp or .git/agent/ only: any other file left under /workspace becomes part of the patch.
- Never run a full test suite: always name one test file, and add -k when you can.
- Never use search_similar_code, get_code_neighbors or get_code_subgraph: they return nothing useful.

# CALL PLAN
- Call 1: run_skill_script with skill_name team and file_path scripts/setup_lead.py, and nothing else.
- Calls 2-8: locate and read. Calls 9-12: edit.
- Then: write your repro script and run it once; one related test file; fix once if needed.
- Then FINISH: the judge may give the issue to a second engineer and keep the better of the two patches.

# PROCEDURE
1. Before any tool call, list for yourself the exact file, function, class or CLI name; the exact error message and
   exception type; the expected return value or output; the inputs that trigger the bug; every edge case mentioned.
   Every concrete string and name in the issue is a literal that must appear exactly in your code.
2. Locate. Use exact paths from the issue directly. Combine independent searches for the issue's exact symbols,
   their callers and relevant tests in one run_command: git grep -n -F "symbol" and git ls-files, about 20 lines of
   output each. Then read the implementation plus one caller or test, about 40 lines per region, at most three regions
   per command (sed -n 'START,ENDp' FILE). For a bug, find where the wrong behaviour is produced; for a feature, copy
   the closest existing sibling, including __all__, option lists, dispatch tables and imports.
3. Edit with edit_file: copy old_string exactly, short and unique. If it fails twice, use one inline python script
   through run_command (quoted heredoc) that asserts the old text occurs once, replaces it and writes the file. Fix
   the cause, not the symptom. Change only what the issue requires and keep signatures and defaults. Apply the change
   to every parallel implementation (sync and async, each backend, re-exports in __init__.py or __all__). Use the
   exact exception class and message text from the issue. For FastAPI documentation tasks, edit docs_src/.
4. Repro script: write_file .git/agent/repro_a.py, a short python script that shows the issue's behaviour: it must
   EXIT WITH AN ERROR (assert or raise) while the bug is there and exit 0 once it is fixed, printing FIXED or BUG.
   Import the package normally. Run it once: timeout 30 python3 .git/agent/repro_a.py
5. If one related test file exists, run it once: timeout 150 python -m pytest tests/path/test_x.py -x -q -k keyword
   Failures from missing fixtures or unrelated imports are pre-existing: ignore them.

# FINISH
1. git status --short && git diff in one call: remove any scratch file in /workspace, restore any changed test file
   with git checkout -- path.
2. run_command: python3 .git/agent/judge.py next
   - SECOND ATTEMPT: your next call is the tool second_fixer with request "fix the issue". When it returns, run
     python3 .git/agent/judge.py --no-wait; it compares both patches and leaves the better one in /workspace.
   - SUBMIT NOW: go to step 3.
3. submit_patch. Confirm patch_size > 0, then reply with one sentence and make no further tool calls.

# DECISION RULES
- Ambiguous issue: choose the most literal reading and act on it. Never ask questions.
- Several possible places: pick where the wrong behaviour is produced, not where it is observed.
- Stuck after a failed fix: make a different, smaller change. Never repeat the same edit.
- Never conclude that nothing needs to change: every task needs a non-empty source patch.
"""
HEAD_SECOND = """You are the second engineer on this issue. Fix it on your own, from scratch, in your own copy of the
repository; another engineer fixed it separately and a judge keeps the better patch. Hidden tests, written from the
issue text, run on the final patch: the exact names, messages, types and behaviours in the issue are the specification.

# THE ISSUE
{problem_description}

# YOUR REPOSITORY
The folder .git/agent/wt_b: an exact copy of the original repository, only yours.
- Every run_command starts with: cd .git/agent/wt_b && ...
- Every file path for read_file, edit_file and write_file starts with .git/agent/wt_b/
  (e.g. .git/agent/wt_b/pkg/module.py); the only file outside it you write is .git/agent/repro_b.py.
- Never edit files in /workspace itself.

# LIMITS
- You have 10 tool calls and little time: locate in about 4 calls, edit by call 6.
- Never create, modify or delete test files; never run a full test suite.
- Never call submit_patch.

# PROCEDURE
1. Before any tool call, list the exact names, messages, types and edge cases the issue gives.
2. Locate: one run_command with git grep -n -F "symbol" for the issue's exact symbols, then read the implementation
   (sed -n 'START,ENDp' FILE, about 40 lines). For a bug, fix where the wrong behaviour is produced; for a feature,
   copy the closest existing sibling.
3. Edit with edit_file (old_string copied exactly, short and unique). Change only what the issue requires; apply it
   to every parallel implementation; use the exact names and messages from the issue.
4. write_file .git/agent/repro_b.py: a short script that exits with an error while the bug is there and exits 0
   once fixed, printing FIXED or BUG; import the package normally. Run it once:
   cd .git/agent/wt_b && PYTHONPATH=. timeout 30 python3 ../repro_b.py
5. run_command: python3 .git/agent/judge.py done b
6. Reply with one sentence describing your fix, and no tool call.
"""
SA2_ROOT_YAML = """# {arm}: one agent + an independent second attempt (scripts/make_skill_arms.py sa2): the lead fixes in /workspace;
# judge.py next decides whether there is time for second_fixer (agent_tool, fresh session, .git/agent/wt_b); the
# judge keeps the better patch; the lead submits.
name: swe_agent
model: gemma-4-31b-it-qat-w4a16-ct
instruction: !include prompts/lead.md
tools:
  - run_command
  - read_file
  - edit_file
  - write_file
  - get_status
  - submit_patch
  - get_code_neighbors
  - search_similar_code
  - get_code_subgraph
  - agent_tool:
      config_path: second.yaml
skills:
  - skills/team
generate_content_config: !include configs/sampling.yaml
"""
SA2_SECOND_YAML = """name: second_fixer
description: Fixes the issue again, independently, in its own copy of the repository (.git/agent/wt_b). Call it with request "fix the issue" only when judge.py next says SECOND ATTEMPT.
model: gemma-4-31b-it-qat-w4a16-ct
instruction: !include prompts/second.md
tools:
  - run_command
  - read_file
  - edit_file
  - write_file
  - get_status
  - submit_patch  # declared so a habitual call never raises; the prompt says never
generate_content_config: !include configs/sampling_second.yaml
"""
SA2_SECOND_SAMPLING = """# sa2 second fixer: no compaction in an agent_tool session, so a small reply budget keeps the whole history
# (10 calls) far below the 32,768-token model length
temperature: 0.2
top_p: 0.95
max_output_tokens: 4096
thinking_config:
  thinking_budget: 2048
  include_thoughts: true
"""


def sa2(arm):
    out = ROOT / "submissions" / arm
    shutil.rmtree(out, ignore_errors=True)
    (out / "prompts").mkdir(parents=True)
    (out / "configs").mkdir()
    shutil.copy(ROOT / "submissions/pub024/configs/sampling.yaml", out / "configs/sampling.yaml")
    (out / "configs/sampling_second.yaml").write_text(SA2_SECOND_SAMPLING)
    ev = (ROOT / "submissions/pub024/eval_config.yaml").read_text()
    for old, new in (("max_tool_calls: 28", f"max_tool_calls: {SA2_CALLS}"), ("max_turns: 80", f"max_turns: {SA2_TURNS}")):
        assert ev.count(old) == 1, old
        ev = ev.replace(old, new)
    (out / "eval_config.yaml").write_text(ev)
    (out / "agent.yaml").write_text(SA2_ROOT_YAML.format(arm=arm))
    (out / "second.yaml").write_text(SA2_SECOND_YAML)
    for name, text in (("lead", HEAD_LEAD), ("second", HEAD_SECOND)):
        rest = text.replace("{problem_description}", "")
        assert "{" not in rest and "}" not in rest, f"{name}: literal braces break ADK instruction templating"
        (out / f"prompts/{name}.md").write_text(text)
    sk = out / "skills/team"
    (sk / "scripts").mkdir(parents=True)
    (sk / "SKILL.md").write_text(TEAM_SKILL_MD.replace("scripts/setup_a.py, setup_b.py or setup_c.py (your letter)",
                                                       "scripts/setup_lead.py"))
    shutil.copy(TEAM_SRC / "judge.py", sk / "scripts/judge.py")
    setup = (TEAM_SRC / "setup.py").read_text()
    assert setup.count('LETTER = "?"') == 1 and setup.count("SECOND = False") == 1
    (sk / "scripts/setup_lead.py").write_text(setup.replace('LETTER = "?"', 'LETTER = "a"').replace("SECOND = False", "SECOND = True"))
    print("wrote", out.relative_to(ROOT), "| lead", len(HEAD_LEAD.split()), "words, second", len(HEAD_SECOND.split()),
          f"words | max_tool_calls {SA2_CALLS} max_turns {SA2_TURNS}")


SA2_ARMS = ("sa2",)


# sq2 (user 2026-10-29, after r27: sa2's lead skipped its setup call in 24/24 tasks and its finish steps in 19/24, so
# no second attempt ever ran): the same idea by STRUCTURE, as the fixer -> reviewer runs showed the model follows it
# (handover 16-18 of 20). Root SequentialAgent [fixer, finisher]: the fixer (pub024 procedure) never submits and ends
# with a plain-text summary; the finisher (include_contents none, tiny) runs the skill script next.py (makes the
# copies itself; start time = the harness's baseline commit), calls second_fixer if told SECOND ATTEMPT, runs pick.py
# and submits. Skill scripts, not .git/agent files: nothing to set up first.
HEAD_SQ_FIX = """You are an autonomous software engineer. Your job: make the smallest correct change to the SOURCE code in
/workspace so that the hidden tests for the issue pass. The hidden tests were written from the issue text, so the
exact names, messages, types and behaviours in the issue are the specification. When you finish, a teammate checks
your patch and submits it: you never call submit_patch.

# LIMITS
- 24 tool calls. An edit that exists in /workspace counts even if time runs out; an unedited tree scores zero. You
  must have edited a source file by call 12: if unsure, make your best-guess edit in the most likely place; a wrong
  edit can still be corrected.
- Never create, modify or delete test files (test_*.py, *_test.py, anything under tests/, pytest.ini, conftest.py).
- Scratch files go in /tmp or .git/agent/ only: any other file left under /workspace becomes part of the patch.
- Never run a full test suite: always name one test file, and add -k when you can.
- Never use search_similar_code, get_code_neighbors or get_code_subgraph: they return nothing useful.

# CALL PLAN
- Calls 1-8: locate and read. Calls 9-12: edit.
- Then: write your repro script and run it once; one related test file; fix once if needed.
- Then FINISH.

# PROCEDURE
1. Before any tool call, list for yourself the exact file, function, class or CLI name; the exact error message and
   exception type; the expected return value or output; the inputs that trigger the bug; every edge case mentioned.
   Every concrete string and name in the issue is a literal that must appear exactly in your code.
2. Locate. Use exact paths from the issue directly. Combine independent searches for the issue's exact symbols,
   their callers and relevant tests in one run_command: git grep -n -F "symbol" and git ls-files, about 20 lines of
   output each. Then read the implementation plus one caller or test, about 40 lines per region, at most three regions
   per command (sed -n 'START,ENDp' FILE). For a bug, find where the wrong behaviour is produced; for a feature, copy
   the closest existing sibling, including __all__, option lists, dispatch tables and imports.
3. Edit with edit_file: copy old_string exactly, short and unique. If it fails twice, use one inline python script
   through run_command (quoted heredoc) that asserts the old text occurs once, replaces it and writes the file. Fix
   the cause, not the symptom. Change only what the issue requires and keep signatures and defaults. Apply the change
   to every parallel implementation (sync and async, each backend, re-exports in __init__.py or __all__). Use the
   exact exception class and message text from the issue. For FastAPI documentation tasks, edit docs_src/.
4. Repro script: write_file .git/agent/repro_a.py, a short python script that shows the issue's behaviour: it must
   EXIT WITH AN ERROR (assert or raise) while the bug is there and exit 0 once it is fixed, printing FIXED or BUG.
   Import the package normally. Run it once: timeout 30 python3 .git/agent/repro_a.py
5. If one related test file exists, run it once: timeout 150 python -m pytest tests/path/test_x.py -x -q -k keyword
   Failures from missing fixtures or unrelated imports are pre-existing: ignore them.

# FINISH
1. git status --short && git diff in one call: remove any scratch file in /workspace, restore any changed test file
   with git checkout -- path.
2. Reply with plain text and NO tool call: one line saying what you changed and where. That reply hands over to
   your teammate.

# DECISION RULES
- Ambiguous issue: choose the most literal reading and act on it. Never ask questions.
- Several possible places: pick where the wrong behaviour is produced, not where it is observed.
- Stuck after a failed fix: make a different, smaller change. Never repeat the same edit.
- Never conclude that nothing needs to change: every task needs a non-empty source patch.
"""
HEAD_SQ_FINISH = """You finish this task: an engineer has just fixed the issue in /workspace (the last message says what
changed). You may get a second, independent attempt and keep the better patch, then you submit. You do not read or
edit code yourself.

Your calls, in this order:
1. run_skill_script with skill_name team and file_path scripts/next.py
2. If it printed SECOND ATTEMPT: call the tool second_fixer with request "fix the issue"; when it returns,
   run_skill_script with skill_name team and file_path scripts/pick.py
   If it printed SUBMIT NOW: skip this step.
3. submit_patch. Then reply with one sentence and make no further tool calls.
"""
# sq1 (user 2026-10-29): sq2 without the second attempt, to see whether sq2's 19/24 comes from the structure
HEAD_SQ1_FINISH = """You submit this task: an engineer has just fixed the issue in /workspace, and the last message says
what changed. The fix is final. You do not read, run or edit anything.

Your only tool call: submit_patch. Then reply with one sentence and make no further tool calls.
"""


def sq2(arm):
    out = ROOT / "submissions" / arm
    shutil.rmtree(out, ignore_errors=True)
    (out / "prompts").mkdir(parents=True)
    (out / "configs").mkdir()
    shutil.copy(ROOT / "submissions/pub024/configs/sampling.yaml", out / "configs/sampling.yaml")
    second = arm == "sq2"  # sq1: the finisher only submits (no next.py, second_fixer, pick.py)
    if second:
        (out / "configs/sampling_second.yaml").write_text(SA2_SECOND_SAMPLING)
    ev = (ROOT / "submissions/pub024/eval_config.yaml").read_text()
    for old, new in (("max_tool_calls: 28", f"max_tool_calls: {SA2_CALLS}"), ("max_turns: 80", f"max_turns: {SA2_TURNS}")):
        assert ev.count(old) == 1, old
        ev = ev.replace(old, new)
    (out / "eval_config.yaml").write_text(ev)
    (out / "agent.yaml").write_text(f"""# {arm}: SequentialAgent [fixer, finisher] (scripts/make_skill_arms.py sq2): the fixer (pub024 procedure) never
# submits and hands over in plain text; """ + ("""the finisher runs next.py, second_fixer (agent_tool, own copy) if there is
# time, pick.py, and submits.
""" if second else """the finisher only submits (sq2 without the second attempt).
""") + """name: swe_agent
agent_class: SequentialAgent
sub_agents:
  - config_path: fixer.yaml
  - config_path: finisher.yaml
""")
    tools = ("  - run_command\n  - read_file\n  - edit_file\n  - write_file\n  - get_status\n"
             "  - submit_patch  # declared on all: the harness task message names it; an undeclared call drops the patch\n")
    (out / "fixer.yaml").write_text("name: fixer\nmodel: gemma-4-31b-it-qat-w4a16-ct\ninstruction: !include prompts/fixer.md\n"
                                    "tools:\n" + tools + "  - get_code_neighbors\n  - search_similar_code\n  - get_code_subgraph\n"
                                    "generate_content_config: !include configs/sampling.yaml\n")
    (out / "finisher.yaml").write_text("name: finisher\nmodel: gemma-4-31b-it-qat-w4a16-ct\ninstruction: !include prompts/finisher.md\n"
                                       "include_contents: none  # fresh: its context starts at the fixer's hand-over line\n"
                                       "tools:\n" + tools + ("  - agent_tool:\n      config_path: second.yaml\n"
                                       "skills:\n  - skills/team\n" if second else "") + "generate_content_config: !include configs/sampling.yaml\n")
    if not second:
        for name, text in (("fixer", HEAD_SQ_FIX), ("finisher", HEAD_SQ1_FINISH)):
            rest = text.replace("{problem_description}", "")
            assert "{" not in rest and "}" not in rest, f"{name}: literal braces break ADK instruction templating"
            (out / f"prompts/{name}.md").write_text(text)
        print("wrote", out.relative_to(ROOT), "| fixer", len(HEAD_SQ_FIX.split()), "words, finisher", len(HEAD_SQ1_FINISH.split()),
              f"words (submit only) | max_tool_calls {SA2_CALLS} max_turns {SA2_TURNS}")
        return
    (out / "second.yaml").write_text(SA2_SECOND_YAML.replace("only when judge.py next says SECOND ATTEMPT",
                                                             "only when scripts/next.py says SECOND ATTEMPT"))
    for name, text in (("fixer", HEAD_SQ_FIX), ("finisher", HEAD_SQ_FINISH), ("second", HEAD_SECOND)):
        rest = text.replace("{problem_description}", "")
        assert "{" not in rest and "}" not in rest, f"{name}: literal braces break ADK instruction templating"
        (out / f"prompts/{name}.md").write_text(text)
    sk = out / "skills/team"
    (sk / "scripts").mkdir(parents=True)
    (sk / "SKILL.md").write_text("---\nname: team\ndescription: The finisher's scripts. run_skill_script with skill_name team "
                                 "and file_path scripts/next.py (second attempt or not), later scripts/pick.py (keep the "
                                 "better patch). No arguments.\n---\n\nscripts/next.py: SECOND ATTEMPT or SUBMIT NOW. "
                                 "scripts/pick.py: compares the two patches and leaves the better one in /workspace.\n")
    judge = (TEAM_SRC / "judge.py").read_text()
    assert judge.count("MODE = None  #") == 1
    for mode in ("next", "pick"):
        (sk / f"scripts/{mode}.py").write_text(judge.replace("MODE = None  #", f"MODE = {mode!r}  #", 1))
    print("wrote", out.relative_to(ROOT), "| fixer", len(HEAD_SQ_FIX.split()), "words, finisher", len(HEAD_SQ_FINISH.split()),
          f"words | max_tool_calls {SA2_CALLS} max_turns {SA2_TURNS}")


# sq1c (user 2026-10-30): sq1 with a clock. 804 runs: 113 of 200 no-patch runs never edited (read until 8 min ran
# out); no prompt rule changed that, tool outputs do -> the fixer's only shell is scripts/run.py, whose output ends
# with "[clock] N s of 480 used | source edited: ..." and which refuses commands at 270 s while nothing is edited.
HEAD_SQ1C_FIX = """You are an autonomous software engineer. Your job: make the smallest correct change to the SOURCE code in
/workspace so that the hidden tests for the issue pass. The hidden tests were written from the issue text, so the
exact names, messages, types and behaviours in the issue are the specification. When you finish, a teammate submits
your patch: you never call submit_patch.

# YOUR TOOLS
- Shell: run_skill_script with skill_name work, file_path scripts/run.py and args holding one key, cmd, whose value
  is the shell command. It runs in /workspace. This is your only way to run commands.
- read_file to read a file region, edit_file to change a file, write_file to create a scratch file.
- Every shell result ends with a clock line: "[clock] N s of 480 used | ..." and whether a source file is edited.
  Read it every time. You have 8 minutes in total; the time is spent mostly on your own thinking, so keep replies
  short.

# LIMITS
- An edit that exists in /workspace counts even if time runs out; an unedited tree scores zero. Edit a source file
  before 180 s on the clock: if unsure, make your best-guess edit in the most likely place; a wrong edit can still
  be corrected. With no source edit at 270 s the shell refuses commands until you edit.
- Never create, modify or delete test files (test_*.py, *_test.py, anything under tests/, pytest.ini, conftest.py).
- Scratch files go in /tmp or .git/agent/ only: any other file left under /workspace becomes part of the patch.
- Never run a full test suite: always name one test file, and add -k when you can.
- Never use search_similar_code, get_code_neighbors or get_code_subgraph: they return nothing useful.

# TIME PLAN (by the clock line)
- Up to about 120 s: locate and read. By 180 s: your edit is in the file.
- Then: write your repro script and run it once; one related test file; fix once if needed.
- From 400 s: stop and FINISH.

# PROCEDURE
1. Before your first call, list for yourself the exact file, function, class or CLI name; the exact error message
   and exception type; the expected return value or output; the inputs that trigger the bug; every edge case
   mentioned. Every concrete string and name in the issue is a literal that must appear exactly in your code.
2. Locate. Use exact paths from the issue directly. Combine independent searches for the issue's exact symbols,
   their callers and relevant tests in one shell command: git grep -n -F "symbol" and git ls-files, about 20 lines
   of output each. Then read the implementation plus one caller or test, about 40 lines per region, at most three
   regions per command (sed -n 'START,ENDp' FILE). For a bug, find where the wrong behaviour is produced; for a
   feature, copy the closest existing sibling, including __all__, option lists, dispatch tables and imports.
3. Edit with edit_file: copy old_string exactly, short and unique. If it fails twice, use one inline python script
   through the shell (quoted heredoc) that asserts the old text occurs once, replaces it and writes the file. Fix the
   cause, not the symptom. Change only what the issue requires and keep signatures and defaults. Apply the change to
   every parallel implementation (sync and async, each backend, re-exports in __init__.py or __all__). Use the exact
   exception class and message text from the issue. For FastAPI documentation tasks, edit docs_src/.
4. Repro script: write_file .git/agent/repro_a.py, a short python script that shows the issue's behaviour: it must
   EXIT WITH AN ERROR (assert or raise) while the bug is there and exit 0 once it is fixed, printing FIXED or BUG.
   Import the package normally. Run it once: timeout 30 python3 .git/agent/repro_a.py
5. If one related test file exists, run it once: timeout 150 python -m pytest tests/path/test_x.py -x -q -k keyword
   Failures from missing fixtures or unrelated imports are pre-existing: ignore them.

# FINISH
1. git status --short && git diff in one shell command: remove any scratch file in /workspace, restore any changed
   test file with git checkout -- path.
2. Reply with plain text and NO tool call: one line saying what you changed and where. That reply hands over to
   your teammate.

# DECISION RULES
- Ambiguous issue: choose the most literal reading and act on it. Never ask questions.
- Several possible places: pick where the wrong behaviour is produced, not where it is observed.
- Stuck after a failed fix: make a different, smaller change. Never repeat the same edit.
- Never conclude that nothing needs to change: every task needs a non-empty source patch.
"""
CLOCK_SRC = ROOT / "scripts/agent_clock"
CLOCK_SKILL_MD = """---
name: work
description: The fixer's shell. run_skill_script with skill_name work, file_path scripts/run.py and args with one key,
  cmd, set to the shell command. Runs in /workspace; the output ends with a clock line.
---

scripts/run.py runs one shell command in /workspace (output cut at 5000 characters) and ends with
"[clock] N s of 480 used | source edited: FILES" or "no source edit yet". With no source edit at 270 s it refuses
commands until edit_file has changed a source file.
"""


def sq1c(arm):
    """sq1 (fixer -> submit-only finisher) whose fixer has no run_command: its shell is the clock skill."""
    sq2("sq1")
    out = ROOT / "submissions" / arm
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(ROOT / "submissions/sq1", out)
    ay = out / "agent.yaml"
    ay.write_text(ay.read_text().replace("# sq1: ", "# sq1c = sq1 with the clock shell (skills/work, scripts/run.py) instead of run_command; sq1: ", 1))
    (out / "fixer.yaml").write_text(
        "name: fixer\nmodel: gemma-4-31b-it-qat-w4a16-ct\ninstruction: !include prompts/fixer.md\n"
        "tools:  # no run_command: the shell is run_skill_script work scripts/run.py (clock line in every output)\n"
        "  - read_file  # named in the harness task message\n  - edit_file\n  - write_file\n  - get_status\n"
        "  - submit_patch  # declared on all: the harness task message names it; an undeclared call drops the patch\n"
        "  - get_code_neighbors\n  - search_similar_code\n  - get_code_subgraph\n"
        "skills:\n  - skills/work\ngenerate_content_config: !include configs/sampling.yaml\n")
    rest = HEAD_SQ1C_FIX.replace("{problem_description}", "")
    assert "{" not in rest and "}" not in rest, "literal braces break ADK instruction templating"
    (out / "prompts/fixer.md").write_text(HEAD_SQ1C_FIX)
    sk = out / "skills/work"
    (sk / "scripts").mkdir(parents=True)
    (sk / "SKILL.md").write_text(CLOCK_SKILL_MD)
    shutil.copy(CLOCK_SRC / "run.py", sk / "scripts/run.py")
    print("wrote", out.relative_to(ROOT), "| fixer", len(HEAD_SQ1C_FIX.split()), "words, shell = skills/work/scripts/run.py")


SQ2_ARMS = ("sq2", "sq1")
CLOCK_ARMS = ("sq1c",)


# arm -> (fixer prompt, reviewer prompt, a.py commands)
FIXER_REVIEWER = {"sk_fr": ("HEAD_FIXER", "HEAD_REVIEWER", "find outline show banner reshow"),
                  "sk_fr2": ("HEAD_FIXER2", "HEAD_REVIEWER2", "find outline show banner reshow handoff handover review")}


CUSHION = {"sk_a2_32": ("sk_a2", 32)}  # arm -> (arm it copies file for file, real max_tool_calls); the prompt is unchanged


def cushion(arm):
    base, calls = CUSHION[arm]
    out = ROOT / "submissions" / arm
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(ROOT / "submissions" / base, out)
    ev = out / "eval_config.yaml"
    assert ev.read_text().count("max_tool_calls: 28") == 1
    ev.write_text(ev.read_text().replace("max_tool_calls: 28", f"max_tool_calls: {calls}"))
    ay = out / "agent.yaml"
    ay.write_text(ay.read_text().replace(f"# {base}: ", f"# {arm} = {base} with a {calls}-call config (prompt says 28); {base}: ", 1))
    print("wrote", out.relative_to(ROOT), f"| copy of {base}, max_tool_calls {calls}, prompt unchanged")


def install_first(arm):
    base, edits = INSTALL_FIRST[arm]
    out = ROOT / "submissions" / arm
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(ROOT / "submissions" / base, out)
    sp = out / "prompts/system.md"
    text = sp.read_text()
    for old, new in edits:
        assert text.count(old) == 1, old[:60]
        text = text.replace(old, new)
    sp.write_text(text)
    ay = out / "agent.yaml"
    ay.write_text(ay.read_text().replace("# ", f"# {arm} = {base} with install as route step 1; ", 1))
    print("wrote", out.relative_to(ROOT), f"| copy of {base}, install-first prompt |", len(text.split()), "words")


def main():
    import sys
    wanted = sys.argv[1:] or list(ARMS) + list(VARIANTS) + list(CALL_VARIANTS) + list(INSTALL_FIRST) + list(SAMPLING_VARIANTS) + list(FIXER_REVIEWER) + list(TEAM_ARMS) + list(SA2_ARMS) + list(SQ2_ARMS) + list(CLOCK_ARMS)
    for arm in [a for a in wanted if a in VARIANTS]:
        variant(arm)
    for arm in [a for a in wanted if a in CALL_VARIANTS]:
        call_variant(arm)
    for arm in [a for a in wanted if a in INSTALL_FIRST]:
        install_first(arm)
    for arm in [a for a in wanted if a in SAMPLING_VARIANTS]:
        sampling_variant(arm)
    for arm in [a for a in wanted if a in CUSHION]:
        cushion(arm)
    for arm in [a for a in wanted if a in FIXER_REVIEWER]:
        fixer_reviewer(arm)
    for arm in [a for a in wanted if a in TEAM_ARMS]:
        team(arm)
    for arm in [a for a in wanted if a in SA2_ARMS]:
        sa2(arm)
    for arm in [a for a in wanted if a in SQ2_ARMS]:
        sq2(arm)
    for arm in [a for a in wanted if a in CLOCK_ARMS]:
        sq1c(arm)
    for arm, cmds in ((a, ARMS[a]) for a in wanted if a not in VARIANTS and a not in CALL_VARIANTS
                              and a not in INSTALL_FIRST and a not in SAMPLING_VARIANTS and a not in CUSHION
                              and a not in FIXER_REVIEWER and a not in TEAM_ARMS
                              and a not in SA2_ARMS and a not in SQ2_ARMS and a not in CLOCK_ARMS):
        out = ROOT / "submissions" / arm
        shutil.rmtree(out, ignore_errors=True)
        (out / "prompts").mkdir(parents=True)
        (out / "configs").mkdir()
        shutil.copy(MIX / "configs/sampling.yaml", out / "configs/sampling.yaml")
        if arm == "sk_a2b":
            (out / "configs/sampling.yaml").write_text(SAMPLING_4K)
        if arm == "sk_a2b2k":
            (out / "configs/sampling.yaml").write_text(SAMPLING_4K.replace("# sk_a2b: the public LB-0.24 package's sampling (thinking 4096, max output 8192)", "# sk_a2b2k: sk_a2b sampling with thinking 2048 (was 4096), max output 8192")
                                                       .replace("thinking_budget: 4096", "thinking_budget: 2048"))
        ev = (MIX / "eval_config.yaml").read_text()
        if arm in CALLS or arm in ("sk_a2n", "sk_a2nr", "sk_a2b", "sk_a2b2k"):
            assert ev.count("max_tool_calls: 28") == 1
            ev = ev.replace("max_tool_calls: 28", f"max_tool_calls: {CALLS.get(arm, A2N_CALLS)}")
        (out / "eval_config.yaml").write_text(ev)
        (out / "agent.yaml").write_text(AGENT_YAML.format(arm=arm))
        (out / "prompts/system.md").write_text(prompt(arm))
        sk = out / "skills/agent"
        (sk / "scripts").mkdir(parents=True)
        (sk / "SKILL.md").write_text(SKILL_MD)
        for f in ("a.py", "install.py"):
            shutil.copy(SKILL_SRC / f, sk / "scripts" / f)
        (sk / "scripts/commands.txt").write_text(cmds + "\n")
        print("wrote", out.relative_to(ROOT), "|", len((out / "prompts/system.md").read_text().split()), "words |", cmds)


if __name__ == "__main__":
    main()
