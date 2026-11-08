"""Scout -> fixer arms (user 2026-11-08). Run: python3 scripts/make_scout_arms.py [arm ...]

Why: wrong patches sit on the real lines (64%) and fail on assertions (83%), so the model is short of what the right behaviour
is, not of where to look; added real information took 2/38 to 15/38, a rewrite of the issue by the model added nothing. The
workspace keeps the repository's own tests, docs, changelog and git history, which agents almost never read (78 git log calls
in all logs). A scout agent gathers that evidence first and quotes it; its final reply is saved by output_key and injected
into the fixer's system prompt ({key?}, ADK inject_session_state), which is re-sent on every request, so compaction cannot drop
it. The fixer starts fresh (include_contents: none) with the issue in its system prompt.

Arms (separate, each against pub024): sc_none = the fixer alone (structure control), sc_tests = scout of existing tests,
sc_hist = scout of git history and changelog, sc_both = one scout doing both, hunch = a no-tools first read of the issue
(close to srep's self-written report; kept as the wild card). No ParallelAgent: ADK 1.36.1 shares one session across
branches and compaction crashed bo3 in 11/24 runs; tool calls run one at a time per task anyway (ctx.tool_lock).
"""
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = "gemma-4-31b-it-qat-w4a16-ct"

FIXER_SAMPLING = """# fixer: pub024's sampling (thinking 4096, max output 8192)
temperature: 0.2
top_p: 0.95
max_output_tokens: 8192
thinking_config:
  thinking_budget: 4096
  include_thoughts: true
"""
SCOUT_SAMPLING = """# scout: a short evidence search; little reasoning needed
temperature: 0.2
top_p: 0.95
max_output_tokens: 4096
thinking_config:
  thinking_budget: 1024
  include_thoughts: true
"""
HUNCH_SAMPLING = """# hunch: one reply, no tools, full reasoning
temperature: 0.2
top_p: 0.95
max_output_tokens: 6144
thinking_config:
  thinking_budget: 4096
  include_thoughts: true
"""

# ---------------------------------------------------------------- fixer (one prompt, written fresh; only its briefing part differs)
BRIEFINGS = {
    "sc_none": "",
    "sc_tests": """# WHAT THE EXISTING TESTS SAY
Before you started, a scout searched the repository's existing tests for the names in the issue. Its notes, with file and
line, are below. The hidden tests usually extend these same test files in the same style, so the notes show how this code
is expected to behave and which names, messages and types are already in use. They are evidence, not orders: where they
disagree with the issue, the issue wins. If the notes are empty or say nothing was found, work from the issue alone.

{tests_brief?}
""",
    "sc_hist": """# WHAT THE HISTORY SAYS
Before you started, a scout read the repository's git history and changelog for the names in the issue. Its notes, with
commit hashes and quoted code, are below. They show how the maintainers changed this code before and in which style. They
are evidence, not orders: where they disagree with the issue, the issue wins. If the notes are empty or say nothing was
found, work from the issue alone.

{history_brief?}
""",
    "sc_both": """# WHAT THE TESTS AND THE HISTORY SAY
Before you started, a scout searched the repository's existing tests, git history and changelog for the names in the
issue. Its notes, with file, line and commit references, are below. The hidden tests usually extend the same test files in
the same style, and earlier commits show how the maintainers changed this code. They are evidence, not orders: where they
disagree with the issue, the issue wins. If the notes are empty or say nothing was found, work from the issue alone.

{brief?}
""",
    "hunch": """# A FIRST READ OF THE ISSUE
Before you started, a colleague read the issue, without seeing any code, and wrote down what the hidden tests will most
likely check. The note is below. It was written blind: check every claim in it against the code, and drop what the code
contradicts. Where it disagrees with the issue, the issue wins.

{hunch?}
""",
}

FIXER_MD = """You are an autonomous software engineer working in /workspace. Fix the issue given at the end of these instructions with
the smallest correct change to the SOURCE code. Hidden tests, written from the issue, decide the grade, so the exact names,
messages, types and behaviours in the issue are the specification.

# LIMITS
- About 28 tool calls and 8 minutes for the whole task; any step before you used part of them. The harness warns you when
  the budget runs low. When time or calls run out the working tree is graded as it is: an edit that exists counts even
  without submit_patch, and an unedited tree scores zero.
- Never create, change or delete test files (test_*.py, *_test.py, anything under tests/, pytest.ini, conftest.py). That is
  an automatic failure.
- Scratch files go in /tmp only. Anything left under /workspace becomes part of the graded patch.
- Never run a whole test suite (bare pytest, pytest ., unittest discover). Always name one test file, and add -k when you
  can.
- Stay inside /workspace. All dependencies are already installed.

# CALL PLAN
- Calls 1-8: locate and read. Edit a source file by call 12 at the latest; if you are unsure, make your best-guess edit in
  the most likely place, because a wrong edit can still be corrected and pure reading cannot score.
- Calls 13-20: verify and correct. From call 20 on: no new exploration; check, fix, submit.
- Always finish with git status --short && git diff, then submit_patch.

# HOW TO WORK
1. Specification, before any call: from the issue, note the exact file, function, class or option names; the exact error
   type and message; the expected return value or output; the inputs that trigger the problem; every edge case mentioned
   (None, empty, negative, unicode, duplicates, defaults). Every concrete string and name in the issue must appear exactly
   in your code.
2. Locate: use paths from the issue directly. Combine independent searches for the issue's exact symbols, their callers
   and their tests in one run_command (git grep -n -F for literal names, git ls-files for paths), about 20 lines of output
   each. Read the implementation plus one caller or test: small regions of about 40 lines with sed -n 'A,Bp' or read_file,
   at most three regions per command. For a bug, find where the wrong behaviour is produced; for a feature, copy the
   closest sibling's pattern, including registration points (__all__, option lists, dispatch tables, imports). If the issue
   has a snippet that shows the problem, you may run it once with python -c.
3. Edit: edit_file for existing code, old_string copied exactly with a short unique match; write_file only for a new source
   file the issue requires. If edit_file finds no match or several, read the exact region and retry with a smaller snippet;
   after two failures, use one inline Python script through run_command (quoted heredoc) that asserts the old text occurs
   once, replaces it and writes the file. Fix the cause, not the example. Keep signatures, defaults and backward
   compatibility unless the issue says otherwise, and match the surrounding style. Apply the change to every parallel
   implementation (sync and async, other backends, overloads, re-exports). Use the exact exception class and message from
   the issue. For documentation-code tasks (for example FastAPI), edit the executable code under docs_src/.
4. Verify, at most two calls: run the closest test file with timeout 150 python -m pytest PATH -x -q -k NAME (or python3 -m
   unittest for unittest projects). Failures from missing fixtures, data or unrelated imports are pre-existing; never
   repair tests or the environment. If a related test fails, fix the source once and rerun once.
5. Finish: git status --short && git diff in one call; remove stray scratch files and restore any changed test file; check
   that every name, message and type from step 1 appears exactly. Call submit_patch and confirm patch_size > 0. End with a
   one-sentence summary.

# DECISION RULES
- Ambiguous issue: take its most literal reading and act. Do not ask questions.
- Several candidate places: change the one where the wrong behaviour is produced, not where it is observed.
- A failed fix: make a different, smaller change; never repeat the same edit.
- Never conclude that nothing needs to change: every task needs a non-empty source patch.

{briefing}# THE ISSUE (verbatim)
{{problem_description}}
"""

FIXER_YAML = """name: fixer
model: {model}
description: Fixes the issue with the smallest source change and submits it.
instruction: !include prompts/fixer.md
include_contents: none  # fresh: its system prompt holds the issue{brief_note}, and compaction never drops the system prompt
tools:
  - run_command
  - read_file
  - edit_file
  - write_file
  - get_status
  - submit_patch
generate_content_config: !include configs/sampling.yaml
"""

# ---------------------------------------------------------------- scouts
SCOUT_HEAD = """You are the scout. You never edit or create files and you never fix anything. The issue is at the end of these
instructions. A fixer starts after you and sees only the issue and your final reply, which goes straight into its
instructions. Your notes are worth the most when they quote what is really in this repository, with file:line or commit
references; never guess, and never restate the issue in other words.

"""
SCOUT_TAIL = """
Use run_command only. Keep every command's output short (pipe through head). Never run tests, never change files, never
use read_file. When you have what you need, or when the searches find nothing, stop calling tools and write your final
reply.

# THE ISSUE (verbatim)
{problem_description}
"""
SCOUT_TESTS = """# YOUR JOB: WHAT THE EXISTING TESTS SAY
1. From the issue, take the two to four most specific names: functions, classes, options, parameters, error messages.
2. In one run_command, search the tests for each name, for example:
   git grep -n -F "NAME" -- tests '*test_*.py' | head -30 ; git grep -n -F "OTHER" -- tests '*test_*.py' | head -30
3. Pick the two or three tests closest to the issue and read them in one run_command with sed -n 'A,Bp' FILE, about 30 lines
   each.
4. If nothing matched, search once more with a shorter or related name. Then stop: four commands in all is plenty.

# YOUR FINAL REPLY (plain text, no tool call, at most 70 lines)
TEST FILES: the paths
RUN WITH: timeout 150 python -m pytest PATH -x -q -k NAME
WHAT THE TESTS EXPECT: up to five lines, each "file:line - what the test asserts", quoting exact strings, names and values
CLOSEST TEST: the most relevant test, copied exactly
If the tests show nothing relevant, reply with the single line NOTHING RELEVANT IN THE TESTS: an empty note is better than a
guess.
"""
SCOUT_HIST = """# YOUR JOB: WHAT THE HISTORY SAYS
1. From the issue, take the two or three most specific names: functions, classes, options, error messages.
2. In one run_command, find the commits that touched them and the changelog lines that mention them, for example:
   git log --oneline -S "NAME" -n 6 ; git log --oneline -S "OTHER" -n 6 ; git grep -n -i -F "NAME" -- '*CHANGELOG*' '*release-notes*' | head -15
3. For the one or two commits most related to the issue, read what they changed in one run_command:
   git show --stat --format='%h %s' COMMIT | head -15 ; git show --format= COMMIT -- SOURCE_FILE | head -60
4. If step 2 found nothing, try git log -L ':FUNCTION:FILE' -n 2 | head -80 for the main function once. Then stop: four
   commands in all is plenty.

# YOUR FINAL REPLY (plain text, no tool call, at most 70 lines)
RELATED COMMITS: one line each: hash - message - what it changed
HOW THIS CODE WAS CHANGED BEFORE: up to four lines with file:line or hash, quoting the exact code involved
CHANGELOG LINES: quoted exactly, if any
If the history shows nothing relevant, reply with the single line NOTHING RELEVANT IN THE HISTORY: an empty note is better
than a guess.
"""
SCOUT_BOTH = """# YOUR JOB: WHAT THE EXISTING TESTS AND THE HISTORY SAY
1. From the issue, take the two to four most specific names: functions, classes, options, parameters, error messages.
2. Tests, in one run_command: git grep -n -F "NAME" -- tests '*test_*.py' | head -30 for each name (join with ;).
3. History, in one run_command: git log --oneline -S "NAME" -n 6 for the two most specific names, and
   git grep -n -i -F "NAME" -- '*CHANGELOG*' '*release-notes*' | head -15 (join with ;).
4. Read the two closest tests (sed -n 'A,Bp' FILE, about 30 lines each) and, for the one commit most related to the issue,
   git show --format= COMMIT -- SOURCE_FILE | head -60, together in one run_command.
5. Then stop: five commands in all is plenty.

# YOUR FINAL REPLY (plain text, no tool call, at most 90 lines)
TEST FILES: the paths
RUN WITH: timeout 150 python -m pytest PATH -x -q -k NAME
WHAT THE TESTS EXPECT: up to five lines, each "file:line - what the test asserts", quoting exact strings, names and values
CLOSEST TEST: the most relevant test, copied exactly
RELATED COMMITS: one line each: hash - message - what it changed
CHANGELOG LINES: quoted exactly, if any
Leave out any part where nothing relevant was found, and say NOTHING RELEVANT FOUND if nothing was: an empty note is
better than a guess.
"""
HUNCH_MD = """You are the first reader. You have no tools and you will not see any code. Read the issue at the end of these
instructions and write a short note for the fixer who starts after you. Think hard about what the hidden tests, which were
written from this issue, will most likely check.

# YOUR REPLY (plain text, at most 30 lines)
LIKELY PLACE: the modules, functions or classes the issue points at, each marked as a guess
EXPECTED BEHAVIOUR: three to six concrete checks the hidden tests probably make, each as "calling X with Y gives Z", quoting
  the exact names, messages and types from the issue
EASY TO MISS: edge cases, parallel implementations (sync and async, other backends, overloads), registration points such
  as __all__ or option lists, and any wording that must match exactly

# THE ISSUE (verbatim)
{problem_description}
"""

STAGE_YAML = """name: {name}
model: {model}
description: {description}
instruction: !include prompts/{name}.md
include_contents: none  # fresh: the issue is in its system prompt
{tools}output_key: {key}
generate_content_config: !include configs/{name}_sampling.yaml
"""

# arm -> (first stage: (name, prompt, sampling, output key, description) or None, fixer max calls budget)
ARMS = {
    "sc_none": (None, 28),
    "sc_tests": (("scout", SCOUT_HEAD + SCOUT_TESTS + SCOUT_TAIL, SCOUT_SAMPLING, "tests_brief",
                  "Quotes what the existing tests say about the issue's names."), 33),
    "sc_hist": (("scout", SCOUT_HEAD + SCOUT_HIST + SCOUT_TAIL, SCOUT_SAMPLING, "history_brief",
                 "Quotes what the git history and changelog say about the issue's names."), 33),
    "sc_both": (("scout", SCOUT_HEAD + SCOUT_BOTH + SCOUT_TAIL, SCOUT_SAMPLING, "brief",
                 "Quotes what the existing tests, git history and changelog say about the issue's names."), 34),
    "hunch": (("hunch", HUNCH_MD, HUNCH_SAMPLING, "hunch",
               "Reads the issue without tools and notes what the hidden tests will likely check."), 28),
}

EVAL = """evaluation:
  timeout_seconds: 240
  max_tool_calls: {calls}
  max_time_minutes: 8
  max_turns: 80
"""


def build(arm):
    stage, calls = ARMS[arm]
    out = ROOT / "submissions" / arm
    shutil.rmtree(out, ignore_errors=True)
    (out / "prompts").mkdir(parents=True)
    (out / "configs").mkdir()
    fixer = FIXER_MD.format(briefing=BRIEFINGS[arm] + ("\n" if BRIEFINGS[arm] else ""))
    keys = set(re.findall(r"\{(\w+)\??\}", fixer))
    assert keys == ({"problem_description"} | ({stage[3]} if stage else set())), (arm, keys)
    (out / "prompts/fixer.md").write_text(fixer)
    (out / "configs/sampling.yaml").write_text(FIXER_SAMPLING)
    (out / "eval_config.yaml").write_text(EVAL.format(calls=calls))
    note = f" and the {stage[3]} note" if stage else ""
    fy = FIXER_YAML.format(model=MODEL, brief_note=note)
    if stage is None:
        (out / "agent.yaml").write_text(f"# {arm}: scripts/make_scout_arms.py; the fixer alone, started fresh with the issue in its system prompt\n"
                                        + fy.replace("name: fixer\n", "name: swe_agent\n", 1))
    else:
        name, prompt, sampling, key, desc = stage
        assert set(re.findall(r"\{(\w+)\??\}", prompt)) == {"problem_description"}, arm
        (out / f"prompts/{name}.md").write_text(prompt)
        (out / f"configs/{name}_sampling.yaml").write_text(sampling)
        tools = "tools:\n  - run_command\n" if name == "scout" else "# no tools: one reply\n"
        (out / f"{name}.yaml").write_text(STAGE_YAML.format(name=name, model=MODEL, description=desc, tools=tools, key=key))
        (out / "fixer.yaml").write_text(fy)
        (out / "agent.yaml").write_text(f"# {arm}: scripts/make_scout_arms.py; {name} -> fixer, the {name}'s reply goes into the fixer's system prompt via output_key {key}\n"
                                        f"name: swe_agent\nagent_class: SequentialAgent\nsub_agents:\n  - config_path: {name}.yaml\n  - config_path: fixer.yaml\n")
    words = len(fixer.split())
    print("wrote", out.relative_to(ROOT), "| fixer words", words, "| calls", calls)


if __name__ == "__main__":
    for a in sys.argv[1:] or list(ARMS):
        build(a)
