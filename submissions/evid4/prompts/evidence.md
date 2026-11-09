Your only job is one search of the repository for the agent who fixes the issue after you. Your reply is copied into
that agent's instructions and stays in front of it for the whole task, so it must hold real lines from the repository, not
your opinions. You will not read code and you will not work on the fix.

Choose two to four search terms from the issue below. Good terms are the exact names the fix most likely touches
(functions, methods, classes, options, parameters), written as they appear in the issue or would appear in the code, and
exact strings quoted in the issue, such as an error message or an option value. Prefer specific terms, such as
convert_underscores or "Invalid header", over common words, such as Header.

Call run_skill_script with skill_name evidence, file_path scripts/evidence.py and positional_args holding those terms, one
term per item. That is your only call. For each term it shows the source lines that use it, where it is defined, how that
definition changed in earlier commits, tests that use it and changelog lines.

Then reply with the lines of its result that best show where the fix belongs and how this code is meant to behave. Copy
each line exactly as it was printed, with its file:line or commit, at most 15 lines and nothing else. If nothing in the
result bears on the issue, reply with the single line NOTHING RELEVANT.

# THE ISSUE (verbatim)
{problem_description}