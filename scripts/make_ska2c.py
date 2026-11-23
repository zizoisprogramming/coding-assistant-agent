"""sk_a2c = sk_a2 (single agent) + the post-edit verdict from r153's editor (docs/PLAN.md 'RESULT r153'; user 2026-11-24: 'build sk_a2c on the 6 tasks').
r153: the editor's 'write check.py -> a.py check -> GREEN submit' path solved both runs that had time; 52% of sk_a2-family wrong kept edits had a
green own check (own_check_vs_hidden.py). Changes (everything else = sk_a2 byte for byte, eval_config 240 s / 28 calls / 8 min):
  a.py 'check' (replaces the old repro check; commands.txt gains 'check'): NO EDIT YET (no source change) -> edit first; NO CHECK SCRIPT ->
      write .git/agent/check.py; runs it (repo on PYTHONPATH, python3 -B, timeout 30): GREEN when a line 'CHECK PASSED' is printed -> submit;
      RED -> one repair edit, with the edited function (found from git diff) printed as it is now; RED again -> submit.
  prompt (scripts/agent_ska2c/system.md, written in full): Step 3 = check.py (the issue's example + assert + print("CHECK PASSED")) and a.py check;
      worked examples for GREEN and RED -> one repair -> GREEN; the old targeted pytest stays optional.
Run: python3 -I scripts/make_ska2c.py"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC, OUT = ROOT / "submissions/sk_a2", ROOT / "submissions/sk_a2c"

CHECK = '''def edited_function():
    """sk_a2c: (file, name, a, b) of the first source function changed in the working tree (from git diff), or None."""
    diff = run("git diff -U0 --no-color -- '*.py'", 20)
    path = None
    for line in diff.split("\\n"):
        if line.startswith("+++ b/"):
            path = line[6:].strip()
            if TEST_RE.search(path):
                path = None
        m = re.match(r"^@@ -\\d+(?:,\\d+)? \\+(\\d+)", line)
        if m and path:
            n = int(m.group(1))
            best = None
            for name, a, b, _ in outline_items(path) or []:
                if a <= n <= b and (best is None or b - a < best[2] - best[1]):
                    best = (name, a, b)
            if best:
                return (path,) + best
            return (path, "module level", max(1, n - 10), n + 20)
    return None


def cmd_check(st, args):
    """sk_a2c: the post-edit verdict: run .git/agent/check.py; GREEN (a 'CHECK PASSED' line) -> submit; RED -> one repair, then submit."""
    chk = os.path.join(HERE, "check.py")
    if not has_change():
        return ">>> NO EDIT YET: make the edit first, then write .git/agent/check.py and run check. <<<"
    if not os.path.exists(chk):
        return (">>> NO CHECK SCRIPT: write .git/agent/check.py with write_file: the issue's own example with an assert of the wanted "
                "result, ending with print(\\"CHECK PASSED\\"). Then run python3 .git/agent/a.py check. <<<")
    out = run('PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}" timeout 30 python3 -B .git/agent/check.py 2>&1', 40)
    tail = "\\n".join(out.split("\\n")[-15:])
    green = any(l.strip() == "CHECK PASSED" for l in out.split("\\n"))
    st["checks"] = st.get("checks", 0) + 1
    if green:
        return f"$ python3 .git/agent/check.py\\n{tail}\\n>>> GREEN: the check passes. Your next call is submit_patch (after git status --short). <<<"
    st["red"] = st.get("red", 0) + 1
    if st["red"] >= 2:
        return (f"$ python3 .git/agent/check.py\\n{tail}\\n>>> RED again after your repair. Do not investigate further: your next call is "
                f"submit_patch (after git status --short); a wrong edit scores no less than no edit. <<<")
    lines = ["$ python3 .git/agent/check.py", tail,
             ">>> RED: the check fails. Keep your edit. Your next call is ONE repair edit in the function below (as it is now, with "
             "your change), at the line that computes the wrong value; then run python3 .git/agent/a.py check once more. <<<"]
    f = edited_function()
    if f:
        path, name, a, b = f
        try:
            src = file_lines(path)
            b = min(b, len(src), a + 59)
            lines.append(f"{path} {name} {a}-{b} (now):")
            lines += [f"{i:6}| {src[i - 1]}" for i in range(a, b + 1)]
        except OSError:
            pass
    return "\\n".join(lines)


'''


def sub(t, a, b):
    assert t.count(a) == 1, a[:80]
    return t.replace(a, b)


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SRC, OUT)
    ap = OUT / "skills/agent/scripts/a.py"
    a = ap.read_text()
    s0, s1 = a.index("def cmd_check(st, args):"), a.index("def has_change():")
    a = a[:s0] + CHECK + a[s1:]
    ap.write_text(a)
    c = (SRC / "skills/agent/scripts/commands.txt").read_text().split()
    assert "check" not in c
    (OUT / "skills/agent/scripts/commands.txt").write_text(" ".join(c[:3] + ["check"] + c[3:]) + "\n")
    ip = OUT / "skills/agent/scripts/install.py"
    ip.write_text(sub(ip.read_text(), '    "check": "check                         after an edit: .git/agent/repro.py + nearest tests + git status",',
                      '    "check": "check                         after the edit: runs .git/agent/check.py -> GREEN (submit) or RED (one repair)",'))
    p = (ROOT / "scripts/agent_ska2c/system.md").read_text()
    assert "a.py check" in p and "CHECK PASSED" in p and "28 tool" in p and "{" not in p
    (OUT / "prompts/system.md").write_text(p)
    y = (OUT / "agent.yaml").read_text()
    (OUT / "agent.yaml").write_text(sub(y, "# sk_a2: mix + the agent's reading tool", "# sk_a2c (2026-11-24): sk_a2 + post-edit verdict (check.py + a.py check GREEN / RED, scripts/make_ska2c.py). sk_a2 was: mix + the agent's reading tool"))
    print("wrote", OUT.relative_to(ROOT), len(p.split()), "words")


if __name__ == "__main__":
    build()
