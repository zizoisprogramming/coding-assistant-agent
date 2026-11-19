"""sbA / sbB: history at the edit / at the read (user 2026-11-19: 'yes build it with all 3 arms, keep them clean, only 4 tasks
please, just proof of concept'; plan + offline check in docs/PLAN.md HISTORY AT THE EDIT / AT THE READ).
Run: python3 -I scripts/make_sbab.py
  sbA = sb1h with every edit's fixed step also printing how the replaced lines changed before (git log -L on their range in HEAD,
        2 commits, 16 lines each) under a header line that says what to do; prompt written fresh (scripts/agent_sbA/system.md),
        worked examples for each case: same-kind fix -> second edit, regression -> second edit, unrelated -> check, no history ->
        check, plus sb1h's found 0 / found 2 / new file / cut-apart / budget examples.
  sbB = sb1h with read_file removed (structure); every read = sed -n S,Ep FILE + the same history of lines S-E under a header
        line; edits = sb1h's; prompt written fresh (scripts/agent_sbB/system.md), examples: same-kind, regression, unrelated,
        no path in the commit, 'has only N lines', found 0 / found 2 / new file / cut-apart / budget.
Both: tools / sampling / eval_config otherwise sb1h's byte for byte (control = sb1h, unchanged)."""
import importlib.util
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("make_sb1h", ROOT / "scripts/make_sb1h.py")
H = importlib.util.module_from_spec(spec)
spec.loader.exec_module(H)
M, SUB, files = H.M, H.SUB, H.files
A_HEAD = ("== HOW THESE LINES CHANGED BEFORE, newest first. If a commit below fixed the same kind of problem, your edit must do it the same way: "
          "if it does not, edit again. If the newest one made the change the issue complains about, your edit must correct that change. Otherwise go on to the check.")
A_NOHIST = "== NO HISTORY FOR THESE LINES (new or already edited lines): go on to the check."
B_HEAD = ("== HOW THESE LINES CHANGED BEFORE, newest first. If a commit below fixed the same kind of problem, make your edit the same way. "
          "If the newest one made the change the issue complains about, your edit corrects that change. Otherwise decide from the code and the issue.")
LOG = "--format='commit %h %ad %s' --date=short | grep -v -E '^(diff|index|---|[+][+][+])' | awk '/^commit /{n=0} n++<16' | cut -c1-150"
A_STEP = """rm -f .git/agent/range
python3 - PATH <<'EOF'
import pathlib, subprocess, sys
p = pathlib.Path(sys.argv[1])
s, old, new = p.read_text(), open('.git/agent/old').read(), open('.git/agent/new').read()
print('old text found', s.count(old), 'times')
if s.count(old) == 1:
    h = subprocess.run(['git', 'show', 'HEAD:' + sys.argv[1]], capture_output=True, text=True).stdout
    r = ''
    if h.count(old) == 1:
        a = h[:h.index(old)].count(chr(10)) + 1
        r = str(a) + ',' + str(a + old.count(chr(10)) - 1) + ':' + sys.argv[1]
    open('.git/agent/range', 'w').write(r)
    p.write_text(s.replace(old, new))
    print('EDITED', p)
EOF
git diff -U1 -- PATH | head -40
test -s .git/agent/range && echo '""" + A_HEAD + """' && git log -L $(cat .git/agent/range) -n 2 """ + LOG + """
test -f .git/agent/range && test ! -s .git/agent/range && echo '""" + A_NOHIST + """' || true
"""
B_READ = "sed -n S,Ep PATH\necho '" + B_HEAD + "'\ngit log -L S,E:PATH -n 2 " + LOG + "\n"
for c in (A_STEP, B_READ):
    assert '"' not in c and "`" not in c and "\\" not in c and "${" not in c and c.count("{") == 1 == c.count("}")


def common(s):
    M.check(s.replace("--full-diff", "--fulldiff"))  # sb1's example 1 uses git log --full-diff (as in the control)
    M.examples(s)
    assert "edit_file" not in s and "write_file" not in s and "old_string" not in s
    blocks = re.findall(r"command:\n```\n(.*?)```", s, re.S)
    for b in blocks:
        assert '"' not in b and "`" not in b and "\\" not in b, b[:80]
    for case in ("old text found 0 times", "old text found 2 times", "mandatory input parameters are not present", "Tool call budget exhausted"):
        assert case in s, case
    assert [b for b in blocks if b.startswith("cat > ") and "NEW_TEXT" in b], "a new-file example"
    return blocks


def edits(s, blocks, step):
    """every edit = the heredocs + the fixed step byte for byte; old text from the read output just before it (its code part),
    or from the NEW_TEXT of the edit just before it (sbA example 3's second edit)."""
    out = []
    prev_new = None
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
        reads = re.findall(r"printed:\n```\n(.*?)```", before, re.S)
        code = reads[-1].split("\n== HOW THESE LINES")[0] if reads else ""
        assert old in code or (prev_new is not None and old in prev_new), "old text copied: " + old[:60]
        prev_new = new
        out.append(path)
    return out


def build_one(name, s, tools_drop, head):
    src, out = SUB / "sb1h", SUB / name
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(src, out)
    (out / "prompts/system.md").write_text(s)
    first, rest = (src / "agent.yaml").read_text().split("\n", 1)
    for t in tools_drop:
        assert rest.count(f"  - {t}\n") == 1
        rest = rest.replace(f"  - {t}\n", "")
    (out / "agent.yaml").write_text(head + "\n" + rest)
    assert files(out) == files(src)
    for f in files(src):
        if f not in ("agent.yaml", "prompts/system.md"):
            assert (out / f).read_bytes() == (src / f).read_bytes(), f
    print("wrote", out.relative_to(ROOT), "| tools", re.findall(r"  - (\w+)", (out / "agent.yaml").read_text()), "| words", len(s.split()))


def build_sbA():
    s = (ROOT / "scripts/agent_sbA/system.md").read_text()
    blocks = common(s)
    paths = edits(s, blocks, A_STEP)
    assert len(paths) >= 5, paths
    assert s.count(A_HEAD) == len(paths) + 3 and s.count(A_NOHIST) == len(paths) + 2, (s.count(A_HEAD), s.count(A_NOHIST), len(paths))  # once per edit command + outputs of examples 3-5 / 3 and 6
    for ev in ('"== HOW THESE LINES CHANGED BEFORE"', '"== NO HISTORY FOR THESE LINES"'):
        assert ev in s, ev
    assert s.count("The reasoning names the commit and the case:") == 2 and "The reasoning names the case:" in s
    build_one("sbA", s, [], "# sbA (2026-11-19): sb1h whose every edit also prints how the replaced lines changed before (git log -L), header line says what to do (scripts/make_sbab.py)")


def build_sbB():
    s = (ROOT / "scripts/agent_sbB/system.md").read_text()
    assert "read_file" not in s, "sbB has no read_file"
    blocks = common(s)
    edits(s, blocks, H.PY_STEP)
    reads = [b for b in blocks if b.startswith("sed -n ")]
    assert len(reads) >= 2
    for b in reads:
        m = re.match(r"sed -n (\d+),(\d+)p (\S+)\n", b)
        assert m and b == B_READ.replace("S,E", m.group(1) + "," + m.group(2)).replace("PATH", m.group(3)), b[:100]
    for out in re.findall(r"printed:\n```\n(.*?)```", s, re.S):
        assert B_HEAD in out, "every read output in the examples carries the header"
    for ev in ('"== HOW THESE LINES CHANGED BEFORE"', '"has only N lines"'):
        assert ev in s, ev
    assert "has only 52 lines" in s and "There is no path" in s
    build_one("sbB", s, ["read_file"], "# sbB (2026-11-19): sb1h with read_file removed; every read = sed -n S,Ep FILE + git log -L of those lines under a header line (scripts/make_sbab.py)")


if __name__ == "__main__":
    build_sbA()
    build_sbB()
