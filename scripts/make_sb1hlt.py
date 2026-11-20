"""sb1hlt = sb1hl + the existing tests run by the edit itself (user 2026-11-20: 'give me A and give me sample of 4 to test on';
docs/PLAN.md IDEA A OFFLINE CHECK). Run: python3 -I scripts/make_sb1hlt.py
The edit step (sb1h's replace-only-when-found-once) also, for a .py source file that is not a test file:
  picks one existing test file: git ls-files test files named test_<module>.py / <module>_test.py (module = the file's name, or
  its folder for __init__.py), else the test files whose text contains the module's dotted path; the shortest path wins;
  runs it BEFORE the edit and AFTER it (python3 -m pytest FILE -q -rfE -p no:cacheprovider, 60 s each, no bytecode files) and
  compares the FAILED / ERROR test ids: tests failing only after the edit are reported with the output's last lines and a line
  saying what to do; otherwise one line says none fail because of the edit and that the hidden test is new (run the reproduce
  check). No test file found, a timeout, or a test-file edit: nothing extra is printed (sb1hl's output).
Prompt written fresh (scripts/agent_sb1hlt/system.md from scripts/agent_sb1hlt/make_prompt.py) from sb1hl's, with worked
examples for: an edit whose tests stay green, an edit that makes an existing test fail -> edited again, found 0, the fence error,
the budget. Tools / sampling / eval_config = sb1hl's byte for byte (control = sb1hl)."""
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("make_sbab", ROOT / "scripts/make_sbab.py")
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
M = B.M
OK_HEAD = "== EXISTING TESTS in "
OK_TAIL = ": none fail because of this edit. The hidden test is new, so run your reproduce check too."
BAD_HEAD = "== THIS EDIT MAKES EXISTING TESTS FAIL in "
BAD_TAIL = "== Fix the source so they pass again, unless the issue asks for the behaviour they test."
T_STEP = """python3 - PATH <<'EOF'
import pathlib, subprocess, sys
f = sys.argv[1]
p = pathlib.Path(f)
s, old, new = p.read_text(), open('.git/agent/old').read(), open('.git/agent/new').read()
print('old text found', s.count(old), 'times')
g = lambda *a: subprocess.run(list(a), capture_output=True, text=True, timeout=60).stdout
isTest = lambda x: x.startswith('test') or '/test' in x or x.endswith(('_test.py', 'conftest.py'))
t = []
if s.count(old) == 1 and f.endswith('.py') and not isTest(f):
    m = p.parent.name if p.stem == '__init__' else p.stem
    ls = [x for x in g('git', 'ls-files', '*.py').split() if isTest(x) and not x.endswith(('conftest.py', '__init__.py'))]
    d = f[:-3].replace('/', '.').replace('.__init__', '').replace('src.', '', 1)
    t = [x for x in ls if pathlib.Path(x).name in ('test_' + m + '.py', m + '_test.py')] or [x for x in ls if d in pathlib.Path(x).read_text(errors='ignore')]
    t = sorted(t, key=len)[:1]
fails = lambda out: set(x.split()[1] for x in out.splitlines() if x.startswith(('FAILED ', 'ERROR ')) and len(x.split()) > 1)
run = lambda: g('python3', '-B', '-m', 'pytest', t[0], '-q', '-rfE', '-p', 'no:cacheprovider')
before = set()
try:
    before = fails(run()) if t else set()
except Exception:
    t = []
if s.count(old) == 1:
    p.write_text(s.replace(old, new))
    print('EDITED', p)
try:
    out = run() if t else ''
    bad = sorted(fails(out) - before)
    if t and bad:
        print('BAD_HEAD' + t[0] + ' (they passed before it): ' + ', '.join(bad[:5]))
        print(chr(10).join(out.splitlines()[-12:]))
        print('BAD_TAIL')
    elif t and (' passed' in out or ' failed' in out):
        print('OK_HEAD' + t[0] + 'OK_TAIL')
except Exception:
    pass
EOF
git diff -U1 -- PATH | head -40
""".replace("BAD_HEAD", BAD_HEAD).replace("BAD_TAIL", BAD_TAIL).replace("OK_HEAD", OK_HEAD).replace("OK_TAIL", OK_TAIL)
assert '"' not in T_STEP and "`" not in T_STEP and "\\" not in T_STEP and "${" not in T_STEP and "{" not in T_STEP and "}" not in T_STEP


def build():
    s = (ROOT / "scripts/agent_sb1hlt/system.md").read_text()
    M.check(s)
    M.examples(s)
    assert "edit_file" not in s and "write_file" not in s and "old_string" not in s
    blocks = re.findall(r"command:\n```\n(.*?)```", s, re.S)
    edits = [b for b in blocks if "OLD_TEXT" in b]
    assert len(edits) == 2, len(edits)
    for b in blocks:
        assert '"' not in b and "`" not in b and "\\" not in b, b[:80]
    news = []
    for b in edits:
        m = re.fullmatch(r"mkdir -p \.git/agent\ncat > \.git/agent/old <<'OLD_TEXT'\n(.*?)OLD_TEXT\ncat > \.git/agent/new <<'NEW_TEXT'\n(.*?)NEW_TEXT\n(python3 - (\S+) <<'EOF'\n.*)", b, re.S)
        assert m, b[:120]
        old, new, step, path = m.groups()
        assert step == T_STEP.replace("PATH", path), "the fixed step byte for byte"
        assert old != new and old.endswith("\n") and new.endswith("\n")
        reads = re.findall(r"read_file on \S+, lines \d+ to \d+, printed:\n```\n(.*?)```", s[:s.index(b)], re.S)
        assert (reads and old in reads[-1]) or any(old in n for n in news), "old text copied: " + old[:60]
        news.append(new)
    outs = re.findall(r"It printed:\n```\n(.*?)```", s, re.S)
    assert sum(OK_HEAD in o and OK_TAIL in o for o in outs) >= 2 and sum(BAD_HEAD in o and BAD_TAIL in o for o in outs) == 1, outs
    for case in ("old text found 0 times", "unexpected EOF while looking for matching", "Tool call budget exhausted", '"== THIS EDIT MAKES EXISTING TESTS FAIL"'):
        assert case in s, case
    src, out = B.SUB / "sb1hl", B.SUB / "sb1hlt"
    import shutil
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(src, out)
    (out / "prompts/system.md").write_text(s)
    first, rest = (src / "agent.yaml").read_text().split("\n", 1)
    (out / "agent.yaml").write_text("# sb1hlt (2026-11-20): sb1hl whose edit also runs the matching existing test file before and after and reports tests that fail only after it (scripts/make_sb1hlt.py)\n" + rest)
    for f in B.files(src):
        if f not in ("agent.yaml", "prompts/system.md"):
            assert (out / f).read_bytes() == (src / f).read_bytes(), f
    print("wrote", out.relative_to(ROOT), "| words", len(s.split()), "| chars", len(s))


if __name__ == "__main__":
    build()
