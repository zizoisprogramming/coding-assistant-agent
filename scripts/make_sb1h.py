"""sb1h / sb1hpp / sb7h (user 2026-11-19: 'yes build it with all 4 arms'; plan in docs/PLAN.md PLANNED r118).
Run: python3 -I scripts/make_sb1h.py

Basis (docs/PLAN.md BROKEN TOOL CALLS ANALYSIS, scripts/mine_bank/broken_calls.py): edit_file / write_file calls break
31-43% of the time (a long string closed with a backtick instead of Gemma's <|"|> token; 89-93% break again right after),
run_command 0-2.3%; presence_penalty 1.5 raised edit breaks to 79% and left run_command at 0 of 412.
  sb1h  = sb1 with every edit made by one run_command (two quoted heredocs write the old / new text to .git/agent, a fixed
          Python step replaces it only when it occurs once and prints the count, then git diff of the file), edit_file
          and write_file removed from the tools (structure), prompt written fresh (scripts/agent_sb1h/system.md) with a
          worked example for each case: the edit, old text found 0 times, found 2 times, a new file, the 'mandatory
          input parameters' event, 'Tool call budget exhausted'. Checked: the real fixes of 15 tasks (31 hunks, with
          backslashes / double / triple quotes) applied through this command = the real patch (heredoc_edit_check.py).
  sb1hpp = sb1h + presence_penalty 1.5 (configs/sampling.yaml).
  sb7h  = one-call history stage (scripts/agent_sb7h/history.md: fenced command, automatic pick of the 3 functions with
          the most uses of the names, HISTORY FETCHED / NO HISTORY lines; examples: normal, no names, a copied-fence
          error, unrelated history replied anyway) + sb1h's way of editing in the fixer with the history pinned
          (scripts/agent_sb7h/system.md); bundle = sb7g's (32 calls) with the prompts, the fixer's tools and history.yaml's
          description changed. Offline: auto top-3 pick shows a real-fix-lines commit 15/32 vs the model's picks 18/32."""
import importlib.util
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("make_sb78", ROOT / "scripts/make_sb78.py")
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)
SUB = ROOT / "submissions"
PY_STEP = """python3 - PATH <<'EOF'
import pathlib, sys
p = pathlib.Path(sys.argv[1])
s, old, new = p.read_text(), open('.git/agent/old').read(), open('.git/agent/new').read()
print('old text found', s.count(old), 'times')
if s.count(old) == 1:
    p.write_text(s.replace(old, new))
    print('EDITED', p)
EOF
git diff -U1 -- PATH | head -40
"""
FETCHED = "== HISTORY FETCHED: you have all the history the engineer needs. Reply with everything above this line exactly as printed, and make no other call."
NOHIST = "== NO HISTORY: no function uses these names. Reply with the line: No history. Make no other call."
files = lambda d: sorted(q.relative_to(d).as_posix() for q in d.rglob("*") if q.is_file())


def check_fixer(s, state=()):
    M.check(s.replace('--full-diff', '--fulldiff'), list(state))  # sb1's example 1 uses git log --full-diff (kept as in the control); make_sb78's ban is for sb7 / sb8
    M.examples(s)
    assert "edit_file" not in s and "write_file" not in s and "old_string" not in s, "no edit_file / write_file in a prompt whose agent lacks them"
    blocks = re.findall(r"command:\n```\n(.*?)```", s, re.S)
    edits = [b for b in blocks if "OLD_TEXT" in b]
    assert len(edits) >= 3, len(edits)
    for b in edits:
        assert '"' not in b and "`" not in b and "\\" not in b, "edit command: no double quotes, backticks, backslashes"
        m = re.fullmatch(r"mkdir -p \.git/agent\ncat > \.git/agent/old <<'OLD_TEXT'\n(.*?)OLD_TEXT\ncat > \.git/agent/new <<'NEW_TEXT'\n(.*?)NEW_TEXT\n(python3 - (\S+) <<'EOF'\n.*)", b, re.S)
        assert m, b[:120]
        old, new, step, path = m.groups()
        assert step == PY_STEP.replace("PATH", path), "the fixed Python step, byte for byte, with one path"
        assert old != new and old.endswith("\n") and new.endswith("\n")
        before = s[:s.index(b)]
        reads = re.findall(r"printed:\n```\n(.*?)```", before, re.S)
        assert reads and old in reads[-1], "old text copied from the read_file output just before it"
    newfile = [b for b in blocks if b.startswith("cat > ") and "NEW_TEXT" in b]
    assert newfile, "a new-file example"
    for case in ("old text found 0 times", "old text found 2 times", "mandatory input parameters are not present", "Tool call budget exhausted"):
        assert case in s, case


def build_sb1h():
    s = (ROOT / "scripts/agent_sb1h/system.md").read_text()
    check_fixer(s)
    src = SUB / "sb1"
    head = "# {} (2026-11-19): sb1 with every edit made by a run_command heredoc, edit_file / write_file removed{} (scripts/make_sb1h.py)\n"
    for name, pp in (("sb1h", None), ("sb1hpp", 1.5)):
        out = SUB / name
        if out.exists():
            shutil.rmtree(out)
        shutil.copytree(src, out)
        (out / "prompts/system.md").write_text(s)
        first, rest = (src / "agent.yaml").read_text().split("\n", 1)
        assert rest.count("  - edit_file\n") == 1 and rest.count("  - write_file\n") == 1
        rest = rest.replace("  - edit_file\n", "").replace("  - write_file\n", "")
        (out / "agent.yaml").write_text(head.format(name, ", presence_penalty 1.5" if pp else "") + rest)
        if pp:
            samp = (src / "configs/sampling.yaml").read_text()
            assert samp.startswith("temperature: 0.2\ntop_p: 0.95\n") and "penalty" not in samp
            (out / "configs/sampling.yaml").write_text(samp.replace("top_p: 0.95\n", f"top_p: 0.95\npresence_penalty: {pp}\n", 1))
        assert files(out) == files(src)
        for f in files(src):
            if f not in ("agent.yaml", "prompts/system.md", "configs/sampling.yaml"):
                assert (out / f).read_bytes() == (src / f).read_bytes(), f
        if not pp:
            assert (out / "configs/sampling.yaml").read_bytes() == (src / "configs/sampling.yaml").read_bytes()
        print("wrote", out.relative_to(ROOT), "| tools", re.findall(r"  - (\w+)", (out / "agent.yaml").read_text()), "| words", len(s.split()))


def build_sb7h():
    h = (ROOT / "scripts/agent_sb7h/history.md").read_text()
    s = (ROOT / "scripts/agent_sb7h/system.md").read_text()
    M.check(h)
    M.examples(h)
    check_fixer(s, ["{func_history?}"])
    cmds = re.findall(r"command:\n```\n(.*?)```", h, re.S)
    assert len(cmds) == 1, "one command in the stage"
    c = cmds[0]
    assert '"' not in c and "`" not in c and "\\" not in c and "${" not in c, "shell text: no double quotes, backticks, backslashes, ${}"
    assert c.startswith("names='parse_config strict'\n") and c.rstrip().endswith("echo '" + NOHIST + "'") and ("echo '" + FETCHED + "'") in c
    out1 = re.search(r"The result's stdout was:\n```\n(.*?)```", h, re.S).group(1)
    rep1 = re.search(r"Your reply, with no tool call, is everything above the HISTORY FETCHED line:\n(.*?)\n\nExample 2", h, re.S).group(1)
    assert out1.rstrip().endswith(FETCHED) and out1[:out1.index(FETCHED)].strip() == rep1.strip()
    out4 = re.search(r"the command printed:\n```\n(.*?)```", h, re.S).group(1)
    rep4 = h[h.rindex("is everything above the HISTORY FETCHED line:\n") + len("is everything above the HISTORY FETCHED line:\n"):]
    assert out4[:out4.index(FETCHED)].strip() == rep4.strip(), "example 4 replies with the unrelated history as printed"
    assert NOHIST in h and "Your reply, with no tool call:\nNo history." in h and "a second time" in h
    assert "The history is fetched and you have all the context it gives: start fixing." in s
    ex = s[s.index("# EXAMPLES"):]
    assert ex.count("The reasoning names the case:") == 3
    src, out = SUB / "sb7g", SUB / "sb7h"
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(src, out)
    (out / "prompts/history.md").write_text(h)
    (out / "prompts/system.md").write_text(s)
    fx = (src / "fixer.yaml").read_text()
    assert fx.count("  - edit_file\n") == 1 and fx.count("  - write_file\n") == 1
    (out / "fixer.yaml").write_text(fx.replace("  - edit_file\n", "").replace("  - write_file\n", ""))
    hy = (src / "history.yaml").read_text()
    old_desc = "Fetches the history of the one or two functions the issue is about and returns it."
    assert hy.count(old_desc) == 1
    (out / "history.yaml").write_text(hy.replace(old_desc, "Fetches, with one command, the history of the functions that use the issue's names and returns it."))
    first, rest = (src / "agent.yaml").read_text().split("\n", 1)
    (out / "agent.yaml").write_text("# sb7h (2026-11-19): one-call history stage (automatic pick, fenced command), fixer edits by run_command heredoc, edit_file / write_file removed, 32 calls (scripts/make_sb1h.py)\n" + rest)
    assert files(out) == files(src)
    for f in files(src):
        if f not in ("agent.yaml", "history.yaml", "fixer.yaml", "prompts/history.md", "prompts/system.md"):
            assert (out / f).read_bytes() == (src / f).read_bytes(), f
    print("wrote", out.relative_to(ROOT), "| fixer tools", re.findall(r"  - (\w+)", (out / "fixer.yaml").read_text()), "| words history", len(h.split()), "fixer", len(s.split()))


if __name__ == "__main__":
    build_sb1h()
    build_sb7h()
