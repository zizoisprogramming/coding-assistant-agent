set -f
skip='(^|/)(tests?|testing)/|(^|/)test_|_test[.]py$|conftest|^(docs|docs_src|examples?|scripts|benchmarks?)/'
mkdir -p .git/agent
changed=$( { git diff --name-only -- '*.py'; git ls-files --others --exclude-standard -- '*/*.py'; } | grep -v -E $skip | sort -u)
echo $changed | grep -q . || { echo 'No source file is edited yet: make the fix first, then run this check.'; exit 0; }
git ls-files -- '*.py' | grep -E '(^|/)(tests?|testing)/|(^|/)test_[^/]*[.]py$|_test[.]py$' | grep -v conftest > .git/agent/tests
names=$(git diff -U0 -- $changed | grep -E '^(@@|[+-] *(async )?(def|class) )' | grep -o -E '(def|class) [A-Za-z_][A-Za-z_0-9]*' | cut -d' ' -f2 | grep -v '^_' | sort -u | head -6)
for f in $changed; do
  stem=$(basename $f .py); [ $stem = __init__ ] && stem=$(basename $(dirname $f))
  mod=$(echo ${f%.py} | sed 's|^src/||; s|/__init__$||; s|/|.|g')
  grep -E '(^|/)(test_)?'$stem'(_test|_tests)?[.]py$' .git/agent/tests
  grep -E '(^|/)(test_)?'$stem'(_test|_tests)?[.]py$' .git/agent/tests
  git grep -l -E '(import|from) +'$mod'([ .,]|$)' -- $(cat .git/agent/tests)
done > .git/agent/picks
for nm in $names; do git grep -l -w -F -e $nm -- $(cat .git/agent/tests); done >> .git/agent/picks
files=$(sort .git/agent/picks | uniq -c | sort -rn | head -3 | awk '{print $2}')
echo '== EDITED FILES: '$changed
echo '== TESTS THAT USE THEM: '$files
echo $files | grep -q . || { echo 'No existing test file uses the edited code.'; exit 0; }
timeout 150 python -m pytest $files -q -rfE -p no:cacheprovider 2>&1 | tail -40
