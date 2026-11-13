Your only job is one search of the repository for the agent who fixes the issue after you. Your reply is copied into that agent's instructions and stays in front of it for the whole task, so it must hold real lines from the repository, not your opinions. You will not read code and you will not work on the fix.

Choose two to four exact names from the issue below that the fix most likely touches: functions, methods, classes, options or parameters, written exactly as they appear in the issue or as they would appear in the code. Prefer the most specific names, such as convert_underscores, over common words, such as Header.

Call run_skill_script with skill_name evidence, file_path scripts/evidence.py and positional_args holding those names, one name per item. That is your only call.

Then reply with the lines of its result that best show where the fix belongs and how this code is meant to behave: where the names are defined, tests that use them, and the lines an earlier commit changed around them. Copy each line exactly as it was printed, with its file:line or commit, at most 10 lines and nothing else. If nothing in the result bears on the issue, reply with the single line NOTHING RELEVANT.

# THE ISSUE (verbatim)
{problem_description}