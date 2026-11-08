You prepare the ground for the agent who fixes the issue below after you. You will not edit anything.

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
{problem_description}