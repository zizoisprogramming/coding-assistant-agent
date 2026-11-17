set -f
test -e .git/agent/check_shown && { echo 'The history check was already shown above. Do not run it again: go on with the two lists.'; exit 0; }
mkdir -p .git/agent && touch .git/agent/check_shown
skip='(^|/)(tests?|testing)/|(^|/)test_|_test[.]py$|conftest|^(docs|docs_src|examples?|scripts|benchmarks?)/'
changed=$(git diff --name-only -- '*.py' | grep -v -E $skip)
echo $changed | grep -q . || { echo 'No source file is edited yet: make the fix first, then run this check.'; rm .git/agent/check_shown; exit 0; }
names=$(git diff -U0 -- $changed | grep -E '^(@@|[+-] *(async )?(def|class) )' | grep -o -E '(def|class) [A-Za-z_][A-Za-z_0-9]*' | cut -d' ' -f2 | grep -v '^__' | sort -u | head -6)
{
echo '== EDITED FUNCTIONS AND CLASSES: '$names
echo '== LIST 1: files that usually change together with your edited files but are not in your patch, with their lines that use the edited names'
for f in $changed; do
  n=$(git log --format=%h -30 -- $f | wc -l)
  git log --full-diff --format= --name-only -30 -- $f | grep -E '[.]py$' | grep -v -E $skip | sort | uniq -c | sort -rn | while read c o; do
    echo ' '$changed' ' | grep -qF ' '$o' ' || { [ $((c * 5)) -ge $n ] && echo $o $c; }
  done | head -3 | while read o c; do
    echo $o: changed together with $f in $c of its last $n commits
    for nm in $names; do git grep -n -w -F -e $nm -- $o; done | head -4 | cut -c1-140 | sed 's/^/    uses: /'
  done
done
echo '== LIST 2: the last commits that touched the lines you edited'
for f in $changed; do
  git diff -U0 -- $f | grep -E '^@@' | head -2 | while read at old rest; do
    s=${old#-}; s=${s%%,*}; case $old in *,*) c=${old#*,};; *) c=1;; esac
    [ $c -eq 0 ] && c=1; [ $s -eq 0 ] && s=1
    echo '-- '$f' lines '$s' to '$((s + c - 1))
    git log -L $s,$((s + c - 1)):$f --format='commit %h %ad %s' --date=short -3 | grep -E '^(commit |[+-][^+-])' | cut -c1-110 | head -16
  done
done
} | head -c 4500
