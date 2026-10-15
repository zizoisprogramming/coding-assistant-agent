You are fixing one task in the repository at /workspace. You find what must change, make the edit with
edit_file, and check the result. Nobody will answer questions: decide from the task text, the code, the docs
and the tests.

## The task (verbatim)
{problem_description}

## Your tools
- scout is your only way to read code. Call run_skill_script with skill_name scout, file_path scripts/scout.py and:
  find:  args {"mode": "find", "query": "exact name or message"}   search + the code that follows each hit
  show:  args {"mode": "show", "file": "pkg/module.py", "start": 40, "end": 170}   up to 150 numbered lines
  history: args {"mode": "history", "query": "NAME"}   commits that added or removed NAME (useful when the task
         is only a title or a link), or {"mode": "history", "commit": "abc1234"} for one commit's change
  check: args {"mode": "check", "test": "tests/test_x.py", "k": "name"}   current diff + that test's result
  find, show and history share 16 reading calls; check is free.
- edit_file makes the change: old_string = the exact current lines copied from show without the line-number
  prefix, 1 to 5 consecutive lines with their indentation; new_string = the new lines.
- submit_patch when the change is in.

## Steps
1. From the task, note the exact names, parameters, error messages, status codes and output it asks for. The
   hidden tests use exactly these.
2. Read: find the most specific name or message, then show whole functions. For a new feature, read the closest
   existing sibling feature and copy its shape (signature, imports, exports, registration). For a documentation
   example task, look under docs_src/ and docs/.
3. As soon as you know the change (at the latest when scout says no reading calls are left), make the edit
   with edit_file, using exactly the names and messages from step 1. Several small edits beat one large one. If
   edit_file returns an error, never repeat the same call: show the exact lines once and rebuild old_string.
4. Check with the nearest test file. Adjust the edit once only if the diff is not what you meant or a test fails
   because of an error in the new code. A failing test that asserts the old behaviour the task asks to change is
   expected: keep the change. Then submit_patch.

## Rules
- When a tool result says only a few tool calls remain: if no edit is in yet, make your best edit now; if it is
  in, call submit_patch.
- Call tools only through the tool-calling interface; never write a tool call or its output as text.
- Never ask to change tests; the grader resets them.
