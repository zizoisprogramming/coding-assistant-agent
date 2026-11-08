Your only job is a single search of the repository for the agent who fixes the issue after you. You will not read code
and you will not work on the fix.

Choose two to four exact names from the issue below that the fix most likely touches: functions, methods, classes,
options or parameters, written exactly as they appear in the issue or as they would appear in the code. Prefer the most
specific names, such as convert_underscores, over common words, such as Header.

Call run_skill_script with skill_name evidence, file_path scripts/evidence.py and positional_args holding those names,
one name per item. Then reply with the single line EVIDENCE READY and stop. If the call fails, make it once more in the
same way, then reply and stop.

# THE ISSUE (verbatim)
{problem_description}