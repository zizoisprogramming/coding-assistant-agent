"""sbG: sb1h + a time-aware 'history first' gate (user 2026-11-20: 'yes verify the timing and build it on sb1h';
basis docs/PLAN.md HISTORY-FIRST GATE: OFFLINE CHECK and RESULT r119-r121: history printed after an edit changed 0 edits).
Run: python3 -I scripts/make_sbG.py
  Every edit = the old / new heredocs + the fixed step written to .git/agent/step.py + `python3 .git/agent/step.py FILE`.
  The step replaces the old text only when it occurs once (sb1h). In addition, while the run is young (now minus the commit
  time of the harness's `_swegemma_baseline` tag < 360 s; sim: that commit is made 0-1 s before the first model request), the
  FIRST edit into a function (smallest def / async def around the old text in HEAD; the old lines when module-level or not
  Python) is NOT applied: the step prints '== NOT EDITED YET ...' + the function's last 3 commits (title + changed lines, 15 per
  commit) + a line saying when to send the edit again changed and, otherwise, the exact short command that applies it as it is.
  Later edits into a shown function, edits of lines not in HEAD, late edits and runs without the tag: applied as in sb1h, no
  history. Prompt written fresh (scripts/agent_sbG/system.md from scripts/agent_sbG/make_prompt.py): worked examples for
  the held edit with a same-kind commit (sent again changed), an unrelated history (applied as it is), a commit that made the
  change the issue complains about (the edit already undoes it: applied as it is), plus sb1h's found 0 / found 2 / new file /
  cut-apart / budget examples. Tools / sampling / eval_config = sb1h's byte for byte (control = sb1h)."""
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("make_sbab", ROOT / "scripts/make_sbab.py")
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
HOLD_HEAD = "== NOT EDITED YET. How this function changed before, newest first:"
HOLD_TAIL = ("== If a commit above fixed the same kind of problem, send the edit again changed to do it the same way; if one made the "
             "change the issue complains about, send it again so it undoes that change. Otherwise apply it as it is: python3 .git/agent/step.py ")
YOUNG_S = 360
STEP_PY = """import ast, pathlib, subprocess, sys, time
f = sys.argv[1]
p = pathlib.Path(f)
g = lambda *a: subprocess.run(['git'] + list(a), capture_output=True, text=True).stdout
s, old, new = p.read_text(), open('.git/agent/old').read(), open('.git/agent/new').read()
print('old text found', s.count(old), 'times')
if s.count(old) == 1:
    h, r = g('show', 'HEAD:' + f), ''
    if h.count(old) == 1:
        a = h[:h.index(old)].count(chr(10)) + 1
        b = a + old.count(chr(10)) - 1
        try:
            n = max((n for n in ast.walk(ast.parse(h)) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.lineno <= a <= b <= n.end_lineno), key=lambda n: n.lineno)
            a, b = n.lineno, n.end_lineno
        except Exception:
            pass
        r = str(a) + ',' + str(b) + ':' + f
    q = pathlib.Path('.git/agent/seen')
    seen = q.read_text().split() if q.exists() else []
    t = g('log', '-1', '--format=%ct', '_swegemma_baseline').strip()
    if r and r not in seen and t.isdigit() and time.time() - int(t) < YOUNG_S:
        q.write_text(' '.join(seen + [r]))
        print('HOLD_HEAD')
        k = 0
        for x in g('log', '-L', r, '-n', '3', '--format=commit %h %ad %s', '--date=short').splitlines():
            if x.startswith('commit '):
                k = 0
                print(x[:150])
            elif x[:1] in ('+', '-') and x[:3] not in ('+++', '---') and k < 15:
                k += 1
                print(x[:150])
        print('HOLD_TAIL' + f)
    else:
        p.write_text(s.replace(old, new))
        print('EDITED', p)
        print(chr(10).join(g('diff', '-U1', '--', f).splitlines()[:40]))
""".replace("HOLD_HEAD", HOLD_HEAD).replace("HOLD_TAIL", HOLD_TAIL).replace("YOUNG_S", str(YOUNG_S))
G_STEP = "cat > .git/agent/step.py <<'EOF'\n" + STEP_PY + "EOF\npython3 .git/agent/step.py PATH\n"
APPLY = "python3 .git/agent/step.py PATH"
for _c in (G_STEP,):
    assert '"' not in _c and "`" not in _c and "\\" not in _c and "${" not in _c and "{" not in _c and "}" not in _c


def edits(s, blocks):
    """every edit = the heredocs + G_STEP byte for byte; old text from the read output just before it (its code part) or from the
    NEW_TEXT of an edit before it (a resend of a held edit)."""
    out, news = [], []
    for b in blocks:
        if "OLD_TEXT" not in b:
            continue
        m = re.fullmatch(r"mkdir -p \.git/agent\ncat > \.git/agent/old <<'OLD_TEXT'\n(.*?)OLD_TEXT\ncat > \.git/agent/new <<'NEW_TEXT'\n(.*?)NEW_TEXT\n(.*)", b, re.S)
        assert m, b[:120]
        old, new, rest = m.groups()
        path = re.search(r"python3 \.git/agent/step\.py (\S+)\n$", rest).group(1)
        assert rest == G_STEP.replace("PATH", path), "fixed step byte for byte: " + path
        assert old != new and old.endswith("\n") and new.endswith("\n")
        before = s[:s.index(b)]
        reads = re.findall(r"read_file on \S+, lines \d+ to \d+, printed:\n```\n(.*?)```", before, re.S)
        assert (reads and old in reads[-1]) or any(old in n for n in news), "old text copied: " + old[:60]
        news.append(new)
        out.append(path)
    return out


def build():
    s = (ROOT / "scripts/agent_sbG/system.md").read_text()
    blocks = B.common(s)
    paths = edits(s, blocks)
    assert len(paths) >= 4, paths
    outs = re.findall(r"It printed:\n```\n(.*?)```", s, re.S)
    holds = [o for o in outs if HOLD_HEAD in o]
    assert len(holds) == 3, len(holds)
    for o in holds:
        assert o.startswith("old text found 1 times\n" + HOLD_HEAD + "\n")
        tail = o.rstrip("\n").splitlines()[-1]
        assert tail.startswith(HOLD_TAIL) and re.fullmatch(r"\S+", tail[len(HOLD_TAIL):]), tail
        for l in o.split(HOLD_HEAD, 1)[1].strip("\n").splitlines()[:-1]:
            assert re.match(r"(commit [0-9a-f]{7} \d{4}-\d\d-\d\d \S|[-+])", l), "history = titles and +/- lines only: " + l
    applies = re.findall(r"command:\n```\n(python3 \.git/agent/step\.py \S+)\n```", s)
    assert len(applies) == 2, applies
    for o in outs:
        assert o.startswith("old text found 1 times\n"), o[:60]
    for ev in ('"== NOT EDITED YET"',):
        assert ev in s, ev
    assert s.count("The reasoning names the commit and the case:") >= 2 and "The reasoning names the case:" in s
    prose = re.sub(r"```.*?```", "", s, flags=re.S)
    assert str(YOUNG_S) not in prose, "no time numbers in the prose (the step's own check is code)"
    assert len(s.split()) <= 3300, len(s.split())
    B.build_one("sbG", s, [], "# sbG (2026-11-20): sb1h whose first edit into a function, early in the run, is held: the step prints the function's last commits (title + changed lines) and asks for the edit again or the short apply command (scripts/make_sbG.py)")


if __name__ == "__main__":
    build()
