Your only job is to prepare the ground for the engineer who fixes the issue after you: install the shell and run one search of the repository. You will not read code and you will not work on the fix. You have no run_command.

Choose two to four exact names from the issue below that the fix most likely touches: functions, methods, classes, options or parameters, written exactly as they appear in the issue or as they would appear in the code. Prefer the most specific names, such as convert_underscores, over common words, such as Header.

Call run_skill_script with skill_name work, file_path scripts/setup.py and positional_args holding those names, one name per item. That is your only call: it installs the shell and searches the repository.

Then reply with the lines of its search result that best show where the fix belongs and how this code is meant to behave: where the names are defined, tests that use them, and the lines an earlier commit changed around them. Copy each line exactly as it was printed, with its file:line or commit, at most 10 lines and nothing else. If nothing in the result bears on the issue, reply with the single line NOTHING RELEVANT.

# THE ISSUE (verbatim)
{problem_description}