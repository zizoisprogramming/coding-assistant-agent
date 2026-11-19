"""sbF: history of the whole function at the edit (user 2026-11-19: 'yes build it with the function window, 4 tasks';
basis docs/PLAN.md HISTORY WINDOW CHECK: a useful commit after the first edit L2 16/70 (sbA) vs F3 30/70).
Run: python3 -I scripts/make_sbF.py
  sbF = sb1h whose every edit's fixed step also prints how the enclosing function changed before: the smallest def /
        async def around the replaced lines in HEAD (ast on HEAD's text; replaced lines when module-level or not Python),
        git log -L of it, 3 commits, 16 lines each, under a header line that says what to do; the no-history line after
        an edit of lines that are not in HEAD; nothing after a failed edit. Prompt written fresh (scripts/agent_sbF/system.md),
        kept close to sb1h's length (r119: sbA's 3,225 words doubled compactions); worked examples for each case:
        same-kind fix -> second edit (which prints the no-history line), unrelated -> check, the newest commit made the
        change the issue complains about -> the edit already corrects it -> check; plus sb1h's found 0 / found 2 / new
        file / cut-apart / budget examples.
Tools / sampling / eval_config = sb1h's byte for byte (control = sb1h, unchanged)."""
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("make_sbab", ROOT / "scripts/make_sbab.py")
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
F_HEAD = ("== HOW THIS FUNCTION CHANGED BEFORE, newest first: follow a commit that fixed the same kind of problem, undo one that made "
          "the change the issue complains about, else go on to the check.")
F_NOHIST = "== NO HISTORY FOR THIS CODE (new or already edited lines): go on to the check."
STEP_T = """rm -f .git/agent/range
python3 - PATH <<'EOF'
import ast, pathlib, subprocess, sys
f = sys.argv[1]
p = pathlib.Path(f)
s, old, new = p.read_text(), open('.git/agent/old').read(), open('.git/agent/new').read()
print('old text found', s.count(old), 'times')
if s.count(old) == 1:
    h = subprocess.run(['git', 'show', 'HEAD:' + f], capture_output=True, text=True).stdout
    r = ''
    if h.count(old) == 1:
        a = h[:h.index(old)].count(chr(10)) + 1
        b = a + old.count(chr(10)) - 1
        try:
            n = max((n for n in ast.walk(ast.parse(h)) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.lineno <= a <= b <= n.end_lineno), key=lambda n: n.lineno)
            a, b = n.lineno, n.end_lineno
        except Exception:
            pass
        r = str(a) + ',' + str(b) + ':' + f
    open('.git/agent/range', 'w').write(r)
    p.write_text(s.replace(old, new))
    print('EDITED', p)
EOF
git diff -U1 -- PATH | head -40
test -s .git/agent/range && echo '""" + F_HEAD + """' && git log -L $(cat .git/agent/range) -n 3 LOG
test -f .git/agent/range && test ! -s .git/agent/range && echo '""" + F_NOHIST + """' || true
"""
# sbF2 (r120 -> r121): git log -L of a whole function prints the whole function as context, so the 16-line cap showed only its
# unchanged top; keep only each commit's title and its +/- lines
LOG_C = "--format='commit %h %ad %s' --date=short | grep -v -E '^(diff|index|---|[+][+][+])' | grep -E '^(commit |[-+])' | awk '/^commit /{n=0} n++<16' | cut -c1-150"
F_STEP = STEP_T.replace("LOG", B.LOG)
F2_STEP = STEP_T.replace("LOG", LOG_C)
STEPS = {"sbF": F_STEP, "sbF2": F2_STEP}
for _st in STEPS.values():
    assert '"' not in _st and "`" not in _st and "\\" not in _st and "${" not in _st and _st.count("{") == 1 == _st.count("}")


def edits(s, blocks, step):
    """every edit = the heredocs + F_STEP byte for byte; old text from the read output just before it (its code part), or
    from the NEW_TEXT of the edit just before it (the same-kind example's second edit)."""
    out, prev_new = [], None
    for b in blocks:
        if "OLD_TEXT" not in b:
            continue
        m = re.fullmatch(r"mkdir -p \.git/agent\ncat > \.git/agent/old <<'OLD_TEXT'\n(.*?)OLD_TEXT\ncat > \.git/agent/new <<'NEW_TEXT'\n(.*?)NEW_TEXT\n(.*)", b, re.S)
        assert m, b[:120]
        old, new, rest = m.groups()
        path = re.search(r"python3 - (\S+) <<'EOF'", rest).group(1)
        assert rest == step.replace("PATH", path), "fixed step byte for byte: " + path
        assert old != new and old.endswith("\n") and new.endswith("\n")
        before = s[:s.index(b)]
        reads = re.findall(r"read_file on \S+, lines \d+ to \d+, printed:\n```\n(.*?)```", before, re.S)
        assert (reads and old in reads[-1]) or (prev_new is not None and old in prev_new), "old text copied: " + old[:60]
        prev_new = new
        out.append(path)
    return out


HEADS = {"sbF": "# sbF (2026-11-19): sb1h whose every edit also prints how the enclosing function changed before (git log -L, 3 commits), header line says what to do (scripts/make_sbF.py)",
         "sbF2": "# sbF2 (2026-11-19): sbF whose history keeps only each commit's title and changed (+/-) lines (r120: the function's unchanged top filled the cap) (scripts/make_sbF.py)"}


def build(name):
    s = (ROOT / f"scripts/agent_{name}/system.md").read_text()
    blocks = B.common(s)
    paths = edits(s, blocks, STEPS[name])
    assert len(paths) >= 4, paths
    outs = re.findall(r"It printed:\n```\n(.*?)```", s, re.S)
    assert sum(F_HEAD in o for o in outs) == 3 and sum(F_NOHIST in o for o in outs) == 1, "history outputs: same kind, unrelated, regression; one no-history"
    for o in outs:
        assert o.startswith("old text found 1 times\nEDITED "), o[:60]
        if name == "sbF2" and F_HEAD in o:
            for l in o.split(F_HEAD, 1)[1].strip("\n").splitlines():
                assert re.match(r"(commit [0-9a-f]{7} \d{4}-\d\d-\d\d \S|[-+])", l), "sbF2 history = titles and +/- lines only: " + l
    for ev in ('"== HOW THIS FUNCTION CHANGED BEFORE"', '"== NO HISTORY FOR THIS CODE"'):
        assert ev in s, ev
    assert "The reasoning names the commit and the case:" in s
    assert len(s.split()) <= 3000, len(s.split())  # 4 full edit commands (212-word step each): one per case needs its example
    B.build_one(name, s, [], HEADS[name])


if __name__ == "__main__":
    import sys
    for name in sys.argv[1:] or ["sbF", "sbF2"]:
        build(name)
