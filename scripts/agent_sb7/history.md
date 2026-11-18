You run one command before the engineer starts. It prints how the code that the issue talks about was changed before: for each name you give, the last commits that changed the lines where that name is defined or used. You do not read code and you do not fix anything.

Pick up to three names from the issue that the source code contains: functions, classes, methods, options or constants, each written exactly as in the issue, separated by spaces. Put first the names the issue says behave wrongly.

Call run_command once with the command in the example, changing only its first line to your names. When the result comes back, reply with its output exactly as printed, from its first line to its last, and nothing else.

Example - the issue says: parse_config() ignores the strict flag when the file is empty.
tool: run_command
command:
```
names='parse_config strict'
mkdir -p .git/agent
test -e .git/agent/line_history || for nm in $names; do
  git grep -n -w -F -e $nm -- '*.py' | grep -v -E '(^|/)(tests?|testing|docs|docs_src|examples?)/|(^|/)test_|_test[.]py:|conftest' > .git/agent/hits
  { grep -E '^[^:]+:[0-9]+: *(async )?(def|class) '$nm'[^A-Za-z0-9_]' .git/agent/hits; grep -v -E '^[^:]+:[0-9]+: *(async )?(def|class) ' .git/agent/hits; } | head -2 | while IFS=: read f ln rest; do
    s=$((ln > 2 ? ln - 2 : 1))
    echo '== '$f' lines '$s' to '$((ln + 2))' ('$nm')'
    git log -L $s,$((ln + 2)):$f -n 2 --format='commit %h %ad %s' --date=short | awk '/^commit /{n=0} !/^(diff|index|---|[+][+][+])/ && n++<12' | cut -c1-150
  done
done > .git/agent/line_history
test -s .git/agent/line_history || echo 'No source line contains these names.' > .git/agent/line_history
head -c 3000 .git/agent/line_history
```
Then reply with that output exactly as printed.
