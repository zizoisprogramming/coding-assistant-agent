"""combo1 (r72, user 2026-11-10 "get the best of agents into one"): pub024's recipe with every zero-cost fix the run bank
supports, nothing that costs time. Run: python3 scripts/make_combo_arm.py [combo1 combo2 combo1en]

r73 (user 2026-11-10 "make both please as new arms on the full dev16, so we have combo ctrl, combo1 + edit now, combo2"):
  combo2   combo1 with the garbled-call rule moved out of the edit section into its own final section, worded as kf2's
           (kf2: 0/30 garbled edit calls in r70-r71; combo1's in-section bullet: 14/36 in r72, 10 resent).
  combo1en combo1 + nn32's forced edit: no run_command; every shell command goes through skill "sh" (scripts/agent_clock/
           run_phase.py as scripts/run.py, LIGHT) with positional_args; the status line says LOOK / EDIT NOW / CHECK; from
           the 12th shell command or 240 s with no source edit, commands are refused until edit_file changes a source file.
           Stop-after-edit and checklist are off. nn32 / nn36p cut no-patch runs 21 -> 7 / 4 over 42 paired tasks.
           Shape: positional_args (8% garbled in r31) not args (object form: 76% garbled in r30). LB risk: every 7-8 min
           agent with a skill shell timed out (cause unknown; no parser stalls locally on the same vLLM 0.19.1).

Evidence (docs/PLAN.md "MINING 2026-11-09b", RESULT r69-r71, "COMBINE 2026-11-10"):
  kept   pub024's recipe: our best LB (0.18) and the lineage of every top public config (8 min, 28 calls, T0.2,
         thinking 4096, literal spec, call plan, batched searches, edit recovery, git status/diff before submit).
  added  the garbled-call rule, inside the edit section: the chat template sorts arguments so new_string comes first and
         ~1 edit call in 5 loses old_string; the rule took garbles from 13/45 to 1/42 edit calls (r69-r71).
  fixed  pub024's scratch-file line: "Scratch files go in /tmp only" made the model call write_file on /tmp, which the
         harness refuses ("Path traversal detected") in 15% of pub024 runs, ~29 s each. Now: /tmp via run_command only.
  cut    get_code_neighbors, search_similar_code, get_code_subgraph: 0 calls in 470 pub024 runs, ~530 tokens re-sent with
         every request (compaction at 14,336 tokens comes sooner); mix and sk_a2 fitted the LB without them.
  left out (tested, no gain or LB risk): checklist / evidence / hunch stages (+17-26 s each, evid3 timed out on the LB),
         more calls (the model explores until the budget is gone either way), skill shells (every 7-8 min one timed out),
         LoRA (23/44 vs base 27/44, ~11% slower decode).
The prompt is written whole (not pub024 + an appended block): pub024's text with the three changes made in place.
agent.yaml differs from pub024 only in the tool list; eval_config.yaml and configs/sampling.yaml are pub024's bytes.
"""
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "submissions/pub024"
OUT = ROOT / "submissions/combo1"
DEAD = ("get_code_neighbors", "search_similar_code", "get_code_subgraph")

SYSTEM_MD = """You are an autonomous software engineer. Your job: make the smallest correct change to the SOURCE code in /workspace so that the hidden tests for the issue below pass. The hidden tests were written from the issue text, so the exact names, messages, types and behaviours in the issue are the specification.

# HARD LIMITS
- 28 tool calls and 8 minutes in total. When either runs out, the working tree is graded as it is. An edit that exists counts, even if you never call `submit_patch`. An unedited tree always scores zero.
- Never create, modify or delete test files (`test_*.py`, `*_test.py`, anything under `tests/`, `pytest.ini`, `conftest.py`). This is an automatic failure.
- Scratch files go in /tmp only, and only through run_command (for example `cat > /tmp/check.py <<'EOF'`). write_file only writes inside /workspace, and any file left under /workspace becomes part of the graded patch.
- Never run a full test suite (bare `pytest`, `pytest .`, `unittest discover`). Always name one test file, and add `-k` when you can.
- Never look outside /workspace. All dependencies are already installed.

# CALL PLAN
- Calls 1-8: locate and read. Calls 9-12: edit. You MUST have edited a source file by call 12. If you are unsure, make your best-guess edit in the most likely place now. A wrong edit can still be corrected. Pure reading cannot score.
- Calls 13-20: verify and correct.
- Call 20 onward: no new exploration. Check, fix, submit.
- Always finish with `git status --short && git diff` followed by `submit_patch`.

# PROCEDURE

## 1. Extract the specification (no tool call)
From the issue, list for yourself: the exact file, function, class or CLI name; the exact error message and exception type; the expected return value or output; the inputs that trigger the bug; every edge case mentioned (None, empty, negative, unicode, duplicates, defaults). Treat every concrete string and name in the issue as a literal that must appear exactly in your code.

## 2. Locate
- Use exact paths from the issue directly. When searches are necessary, combine independent searches for the issue's exact symbols, their callers and relevant test paths into one run_command. Use git grep with fixed-string patterns for literal identifiers and git ls-files for tracked file paths; each result should show its file path and line number where applicable.
- Batch only searches whose inputs are already known. If the next search depends on the first result, inspect that result before searching again. Limit each search to about 20 matching lines and keep total output short; never dump whole files or the repository tree.
- Once the target is located, read the relevant implementation plus one relevant caller or test case. When both paths and line ranges are known, read these small regions in one run_command using sed with explicit line ranges, or use read_file for a single region. Aim for about 40 lines per region and at most three regions per command. Include enough surrounding code to understand signatures, defaults and error handling.
- For a bug: find where the wrong behaviour is produced and use the caller or test to understand the contract before editing.
- For a feature: find the closest existing sibling (a similar function, option, class, or doc example) and copy its pattern, including registration points such as __all__, option lists, dispatch tables and imports.
- Reuse paths and test names already discovered. Do not spend another tool call repeating a search that already answered the question.
- If the issue includes a code snippet that reproduces the problem, you may run it once with python -c (one call, never create a file) to see the real error.

## 3. Edit
- Use edit_file for changes to existing code. Copy old_string exactly from the source, including whitespace, and choose a short unique match. Use write_file only for a genuinely new source file that the issue requires.
- If a tool result says "mandatory input parameters are not present", your edit_file or write_file call was cut apart: a text ended with a backtick or a stray quote and swallowed the next argument. Do not send the same call again. End every text right after its last character, never with a backtick. If it fails a second time, use the heredoc script described next.
- If edit_file reports no match or multiple matches, read the exact source region and retry with a smaller unique snippet. Never repeat an identical failed edit. After two matching failures, use one inline Python script through run_command with a quoted heredoc; assert that the old text occurs exactly once before replacing it and writing the file. Preserve unrelated content and do not rewrite the file from memory.
- Fix the cause, not the symptom. Do not special-case the example from the issue.
- Change only what the issue requires. Keep existing signatures, defaults, and backward compatibility unless the issue says otherwise. Match the style, naming and error-handling idioms of the surrounding code.
- If the same behaviour has parallel implementations (sync and async variants, Client and AsyncClient, several backends or transports, typing overloads, re-exports in `__init__.py` or `__all__`), apply the change to every one of them. Hidden tests often exercise more than one.
- Use the exact exception class and exact message text from the issue. If the issue only describes the error, reuse the wording style of neighbouring error messages.
- Handle every edge case you listed in step 1.
- For documentation-code tasks (for example FastAPI), edit the executable code under `docs_src/`.

## 4. Verify (at most 2 calls)
- Find the test file with `find tests -name "*keyword*.py"`, then run `timeout 150 python -m pytest tests/path/test_x.py -x -q -k keyword`. Use `python3 -m unittest tests.test_x` for unittest projects.
- Failures that come from missing fixtures, missing data, or import errors unrelated to your change are pre-existing. Ignore them. Never repair tests or the environment.
- If a test related to your change fails, read the traceback, fix the source once, and rerun once. If no test can run, do one `python -c` check or `python -m py_compile` on the edited file.

## 5. Final check and submit
- Run `git status --short && git diff` in one call. `git diff` alone hides untracked files, but `submit_patch` includes them. If you see an untracked scratch file or a changed test file, remove it or restore it with `git checkout --` before submitting. Confirm that: only source files changed; every name, message and type from step 1 appears exactly; nothing unrelated was touched; there are no leftover debug prints or stray files.
- Call `submit_patch`. Confirm `patch_size > 0` and `files_changed > 0`. If either is 0, you have not edited anything. Edit now and submit again.
- End with a single-sentence summary of the fix.

# DECISION RULES
- Ambiguous issue: choose the most literal reading of the issue text and act on it. Do not ask questions and do not stall.
- Several possible locations: pick the one where the wrong behaviour is produced, not where it is merely observed.
- Search returned nothing: try one different specific string, then edit your best candidate anyway.
- Stuck after a failed fix: make a different, smaller change. Do not repeat the same edit.
- Never conclude that nothing needs to change. Every task requires a non-empty source patch.
"""


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(PUB, OUT)
    y = (PUB / "agent.yaml").read_text()
    for t in DEAD:
        assert y.count(f"  - {t}\n") == 1, t
        y = y.replace(f"  - {t}\n", "")
    y = y.replace("name: swe_agent\n", "name: swe_agent  # combo1: scripts/make_combo_arm.py (pub024 minus the 3 unused graph tools)\n", 1)
    (OUT / "agent.yaml").write_text(y)
    (OUT / "prompts/system.md").write_text(SYSTEM_MD)

    pub = (PUB / "prompts/system.md").read_text()
    # checks: the three changes and nothing else of substance
    assert "{" not in SYSTEM_MD and "}" not in SYSTEM_MD, "ADK would read braces as session-state fields"
    assert not any(t in SYSTEM_MD or t in y for t in DEAD), "dead tools gone from prompt and tool list"
    assert "mandatory input parameters are not present" in SYSTEM_MD
    assert "Scratch files go in /tmp only." in pub and "Scratch files go in /tmp only." not in SYSTEM_MD
    pub_lines = [l for l in pub.splitlines() if l.strip()]
    new_lines = set(l for l in SYSTEM_MD.splitlines() if l.strip())
    dropped = [l for l in pub_lines if l not in new_lines]
    assert len(dropped) == 2 and any("Scratch files" in l for l in dropped) and any("search_similar_code" in l for l in dropped), dropped
    added = [l for l in SYSTEM_MD.splitlines() if l.strip() and l not in set(pub_lines)]
    assert len(added) == 2 and any("Scratch files" in l for l in added) and any("mandatory input" in l for l in added), added
    for f in ("eval_config.yaml", "configs/sampling.yaml"):
        assert (OUT / f).read_bytes() == (PUB / f).read_bytes(), f
    assert re.findall(r"^  - (\w+)", y, re.M) == ["run_command", "read_file", "edit_file", "write_file", "get_status", "submit_patch"]
    print(f"{OUT.relative_to(ROOT)}: pub024 lines kept {len(pub_lines) - 2}/{len(pub_lines)}, 2 rewritten (scratch, graph tools), "
          f"1 added (garbled call); tools {len(re.findall(r'^  - ', y, re.M))}")


KF2_SECTION = """

# IF AN EDIT CALL IS CUT APART
If a tool result says "mandatory input parameters are not present", your edit_file or write_file call was cut apart: a text ended with a backtick or a stray quote and swallowed the next argument. Do not send the same call again. End every text right after its last character, never with a backtick. If it fails a second time, make the change with one run_command running a Python heredoc that asserts the old text occurs exactly once and then replaces it.
"""
GARBLE_BULLET = ("- If a tool result says \"mandatory input parameters are not present\", your edit_file or write_file call was cut apart: a text ended with a backtick or a stray quote and swallowed the next argument. Do not send the same call again. End every text right after its last character, never with a backtick. If it fails a second time, use the heredoc script described next.\n")

# combo1en: combo1's text with every run_command route rewritten for the gated shell, plus a SHELL section.
EN_REPLACE = [
    ("- Scratch files go in /tmp only, and only through run_command (for example `cat > /tmp/check.py <<'EOF'`). write_file only writes inside /workspace, and any file left under /workspace becomes part of the graded patch.\n",
     "- Scratch files go in /tmp only, and only through the shell (for example `cat > /tmp/check.py <<'EOF'`). write_file only writes inside /workspace, and any file left under /workspace becomes part of the graded patch.\n"),
    ("combine independent searches for the issue's exact symbols, their callers and relevant test paths into one run_command.",
     "combine independent searches for the issue's exact symbols, their callers and relevant test paths into one shell command."),
    ("read these small regions in one run_command using sed with explicit line ranges",
     "read these small regions in one shell command using sed with explicit line ranges"),
    ("After two matching failures, use one inline Python script through run_command with a quoted heredoc;",
     "After two matching failures, use one inline Python script through the shell with a quoted heredoc;"),
]
EN_SHELL = """
# SHELL
There is no run_command. Run every shell command with run_skill_script: skill_name "sh", file_path "scripts/run.py", and positional_args a list holding one string, the whole command, for example ["git grep -n -F 'parse_args' -- '*.py' | head -20"]. Do not use the args parameter. If a tool result says an argument is required, the call was cut apart: write it out plainly; never send the same broken call again.
The last line of every shell output shows where you are: LOOK, then EDIT NOW, then CHECK after a source edit. When no source file has been edited for a while, the shell refuses commands until you edit one with edit_file. Then make your best edit in the most likely place, where the wrong behaviour is produced; you can correct it afterwards.
"""
EN_SKILL_MD = """---
name: sh
description: The shell. Runs one shell command in /workspace. Call run_skill_script with skill_name sh, file_path scripts/run.py and positional_args holding one string, the whole command.
---

Call run_skill_script with skill_name sh, file_path scripts/run.py and positional_args a list holding one string: the whole
shell command. Do not use the args parameter. The output ends with a state line (LOOK, EDIT NOW, CHECK). With no source
edit for a while, commands are refused until edit_file changes a source file.
"""
EN_CONSTS = [("STOP_AFTER = 60  #", "STOP_AFTER = 10 ** 6  # combo1en: stop rule off;"),
             ("REFUSE_AT = 210  #", "REFUSE_AT = 240  # combo1en (nn32's time);"),
             ("REFUSE_SHELL = 12\n", "REFUSE_SHELL = 12  # combo1en\n"),
             ("WORDS = False\n", "WORDS = True  # combo1en: [state] LOOK / EDIT NOW / CHECK, no seconds\n"),
             ("LIGHT = False\n", "LIGHT = True  # combo1en: fewer git processes per command\n")]


def write_arm(out, prompt, tools, extra_files=None):
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(PUB, out)
    y = (PUB / "agent.yaml").read_text()
    for t in DEAD:
        y = y.replace(f"  - {t}\n", "")
    y = y.replace("tools:\n  - run_command\n  - read_file\n  - edit_file\n  - write_file\n  - get_status\n  - submit_patch\n",
                  "tools:\n" + "".join(f"  - {t}\n" for t in tools if not t.startswith("skills/"))
                  + ("skills:\n" + "".join(f"  - {t}\n" for t in tools if t.startswith("skills/")) if any(t.startswith("skills/") for t in tools) else ""), 1)
    y = y.replace("name: swe_agent\n", f"name: swe_agent  # {out.name}: scripts/make_combo_arm.py\n", 1)
    (out / "agent.yaml").write_text(y)
    (out / "prompts/system.md").write_text(prompt)
    for rel, text in (extra_files or {}).items():
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        (out / rel).write_text(text)
    assert "{" not in prompt and "}" not in prompt
    for f in ("eval_config.yaml", "configs/sampling.yaml"):
        assert (out / f).read_bytes() == (PUB / f).read_bytes(), f
    return y


def build_combo2():
    assert SYSTEM_MD.count(GARBLE_BULLET) == 1
    prompt = SYSTEM_MD.replace(GARBLE_BULLET, "", 1).rstrip("\n") + "\n" + KF2_SECTION
    write_arm(ROOT / "submissions/combo2", prompt, ["run_command", "read_file", "edit_file", "write_file", "get_status", "submit_patch"])
    assert "mandatory input parameters are not present" in prompt and prompt.count("mandatory input") == 1
    assert prompt.index("# IF AN EDIT CALL IS CUT APART") > prompt.index("# DECISION RULES")
    print("submissions/combo2: combo1 with the garbled-call rule as its own final section")


def build_combo1en():
    prompt = SYSTEM_MD
    for old, new in EN_REPLACE:
        assert prompt.count(old) == 1, old[:60]
        prompt = prompt.replace(old, new, 1)
    anchor = "\n# CALL PLAN\n"
    assert prompt.count(anchor) == 1
    prompt = prompt.replace(anchor, "\n" + EN_SHELL.strip("\n") + "\n" + anchor, 1)
    assert "run_command" in prompt.split("# IF")[0] or True
    assert prompt.count("run_command") == 1 and "There is no run_command." in prompt, "only the SHELL section names run_command"
    script = (ROOT / "scripts/agent_clock/run_phase.py").read_text()
    for old, new in EN_CONSTS:
        assert script.count(old) == 1, old
        script = script.replace(old, new, 1)
    y = write_arm(ROOT / "submissions/combo1en", prompt, ["read_file", "edit_file", "write_file", "get_status", "submit_patch", "skills/sh"],
                  {"skills/sh/SKILL.md": EN_SKILL_MD, "skills/sh/scripts/run.py": script})
    assert "run_command" not in y and "skills:\n  - skills/sh\n" in y
    print("submissions/combo1en: combo1 + gated shell (skill sh, positional_args), refusal at the 12th command or 240 s without a source edit")


if __name__ == "__main__":
    import sys
    for arm in sys.argv[1:] or ["combo1", "combo2", "combo1en"]:
        {"combo1": build, "combo2": build_combo2, "combo1en": build_combo1en}[arm]()
