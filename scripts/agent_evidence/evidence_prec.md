Your only job is one search of the repository for the engineer who fixes the issue after you. Your reply is copied into that engineer's instructions and stays in front of them for the whole task, so it must hold real lines from the repository, not your opinions. You will not read code and you will not work on the fix.

Choose two to four exact names from the issue below that the fix most likely touches: functions, methods, classes, options or parameters, written exactly as they appear in the issue or as they would appear in the code. Prefer the most specific names, such as convert_underscores, over common words, such as Header.

Call run_skill_script with skill_name evidence, file_path scripts/evidence.py and positional_args holding those names, one name per item. That is your only call.

The result can start with PAST CHANGES LIKE THIS ONE: earlier commits of this repository whose titles share those names, each followed by the files and functions it changed. Then, for each name, come where it is defined, the tests that use it, and the lines that earlier commits changed around it.

Then reply with the lines of the result that best show where the fix belongs and how this code is meant to behave, copied exactly as they were printed, at most 14 lines and nothing else:
- first, every past change whose title is about the same thing as the issue, each with the file-and-functions line under it;
- then where the names are defined, the tests that use them, and the lines an earlier commit changed around them.
If nothing in the result bears on the issue, reply with the single line NOTHING RELEVANT.

# THE ISSUE (verbatim)
{problem_description}
