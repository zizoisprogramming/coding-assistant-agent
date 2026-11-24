"""sk_a2c2 and sk_a2o (docs/PLAN.md 'PLAN (not built) 2026-11-24: sk_a2c2 ... + sk_a2o ...'; user 2026-11-24: 'build both on the 6 tasks').
r154: sk_a2c's a.py check was used in 1/8 edited runs - the model wrote check.py and ran it itself (sk_a2-family script runs: a written file 46%,
python3 - << heredoc 41%), mostly before the edit.
  sk_a2c2 = sk_a2c with a.py check taking the check code from a heredoc on stdin ('python3 .git/agent/a.py check << 'EOF' ... EOF'): saved as
      .git/agent/check.py and run (repo on PYTHONPATH, -B, timeout 25) in the same call; no input re-runs the saved one. Verdicts:
      no edit yet + fails -> BUG SHOWN (next call: the edit); no edit yet + passes -> 'does not show the bug, edit now' (one message, no gate);
      after the edit: GREEN -> submit; RED -> one repair, the edited function printed; RED again -> submit.
      stdin is read only when select() says data is ready (an open pipe with no data must not hang a.py).
  sk_a2o = sk_a2c2's a.py + two outputs, no new step: (a) after a source change every a.py output adds 'YOUR EDIT: file function a-b' and
      SAME LINES ELSEWHERE (functions sharing >= 2 of the edited function's non-trivial lines; <= 3); (b) when STOP READING fires, the first two
      times, it prints the most-read source function's current lines (<= 25) as the edit material. The check stays available, not required.
Prompts written in full: scripts/agent_ska2c2/system.md, scripts/agent_ska2o/system.md. Run: python3 -I scripts/make_ska2c2o.py"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "submissions/sk_a2c"

CHECK2 = '''def _stdin_text():
    """The heredoc given to a.py, if any; never blocks on an open pipe without data."""
    try:
        import select
        if sys.stdin is None or sys.stdin.isatty():
            return ""
        ready, _, _ = select.select([sys.stdin], [], [], 0.3)
        return sys.stdin.read() if ready else ""
    except Exception:  # noqa: BLE001
        return ""


def cmd_check(st, args):
    """sk_a2c2: check code from a heredoc (saved to .git/agent/check.py) run in the same call, with a verdict that names the next call."""
    chk = os.path.join(HERE, "check.py")
    code = _stdin_text()
    if code.strip():
        with open(chk, "w") as fh:
            fh.write(code if code.endswith("\\n") else code + "\\n")
    if not os.path.exists(chk):
        return (">>> NO CHECK CODE: give it as a heredoc: python3 .git/agent/a.py check << 'EOF' (the issue's own example, an assert of the "
                "wanted result, print(\\"CHECK PASSED\\")) EOF <<<")
    out = run('PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}" timeout 25 python3 -B .git/agent/check.py 2>&1', 35)
    tail = "\\n".join(out.split("\\n")[-15:])
    green = any(l.strip() == "CHECK PASSED" for l in out.split("\\n"))
    head = f"$ python3 .git/agent/check.py\\n{tail}\\n"
    if not has_change():
        st["pre_checks"] = st.get("pre_checks", 0) + 1
        if green:
            return head + (">>> YOUR CHECK PASSES BEFORE ANY EDIT: it does not show the bug. Do not rewrite it: make your edit now (the "
                           "hidden tests decide), then run python3 .git/agent/a.py check (no input) for the verdict. <<<")
        return head + (">>> BUG SHOWN: your check fails on the unchanged code, as the issue says. Your next call is the edit; then run "
                       "python3 .git/agent/a.py check (no input) for the verdict. <<<")
    st["checks"] = st.get("checks", 0) + 1
    if green:
        return head + ">>> GREEN: the check passes with your edit. Your next call is submit_patch (after git status --short). <<<"
    st["red"] = st.get("red", 0) + 1
    if st["red"] >= 2:
        return head + (">>> RED again after your repair. Do not investigate further: your next call is submit_patch (after git status "
                       "--short); a wrong edit scores no less than no edit. <<<")
    lines = [head + ">>> RED: the check fails with your edit. Keep your edit. Your next call is ONE repair edit in the function below (as "
             "it is now), at the line that computes the wrong value; then python3 .git/agent/a.py check (no input) once more. <<<"]
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

OUTPUTS = '''

def _func_at(path, line):
    best = None
    for name, a, b, _ in outline_items(path) or []:
        if a <= line <= b and (best is None or b - a < best[2] - best[1]):
            best = (name, a, b)
    return best[0] if best else "module level"


def same_lines(path, a, b, removed=()):
    """sk_a2o: other functions sharing >= 2 of the non-trivial lines of path a-b, or any line the edit removed (a fix often needs all of them)."""
    try:
        src = file_lines(path)
    except OSError:
        return []
    cands = [r for r in removed if len(r) >= 20]
    for l in src[a - 1:b]:
        s = l.strip()
        if len(s) >= 25 and not s.startswith(("#", chr(34) * 3, chr(39) * 3, "def ", "class ", "@")) and s not in cands:
            cands.append(s)
    if not cands:
        return []
    pats = " ".join(f"-e {q(s)}" for s in cands[:20])
    out = run(f"git grep -n -F {pats} -- '*.py'", 20)
    groups = {}
    for line in out.split("\\n"):
        m = re.match(r"^(.+?\\.py):(\\d+):(.*)$", line)
        if not m:
            continue
        p, n, text = m.group(1), int(m.group(2)), m.group(3).strip()
        if TEST_RE.search(p) or (p == path and a <= n <= b):
            continue
        g = groups.setdefault((p, _func_at(p, n)), {"lines": set(), "ex": (n, ""), "removed": False})
        if text not in g["lines"]:
            g["lines"].add(text)
            if text in removed and not g["removed"]:
                g["removed"], g["ex"] = True, (n, text[:90])  # the line your edit changed: the best example
            elif not g["removed"] and len(text) > len(g["ex"][1]):
                g["ex"] = (n, text[:90])
    ranked = sorted(groups.items(), key=lambda kv: (not kv[1]["removed"], -len(kv[1]["lines"]), kv[0][0] != path))
    return [f"{p} {fn}: {len(g['lines'])} of the same lines" + (" incl. the line you changed" if g["removed"] else "") + f", e.g. line {g['ex'][0]}: {g['ex'][1]}"
            for (p, fn), g in ranked if len(g["lines"]) >= 2 or g["removed"]][:3]


def edit_block(st):
    """sk_a2o: after a source change, the edited function and the other places with the same lines (every a.py output)."""
    if not has_change():
        return ""
    f = edited_function()
    if not f:
        return ""
    path, name, a, b = f
    diff = run(f"git diff -U0 --no-color -- {q(path)}", 20)
    removed = [l[1:].strip() for l in diff.split("\\n") if l.startswith("-") and not l.startswith("---")]
    same = same_lines(path, a, b, removed) if name != "module level" else []
    lines = [f"YOUR EDIT: {path} {name} {a}-{b}. SAME LINES ELSEWHERE: " + ("none" if not same else "change them too if the same fix applies")]
    lines += ["  " + s for s in same]
    return "\\n".join(lines)


def stop_material(st):
    """sk_a2o: at STOP READING (first two times), the most-read source function's current lines: the edit material."""
    if st.get("stop_material", 0) >= 2:
        return ""
    funcs = [f for f in st.get("funcs", []) if not TEST_RE.search(f["file"])]
    if not funcs:
        return ""
    cnt = {}
    for f in funcs:
        cnt[(f["file"], f["name"])] = cnt.get((f["file"], f["name"]), 0) + 1
    (path, name), _ = max(cnt.items(), key=lambda kv: (kv[1], [(f["file"], f["name"]) for f in funcs].index(kv[0])))
    items = [it for it in (outline_items(path) or []) if it[0] == name]
    if not items:
        return ""
    _, a, b, _ = items[0]
    try:
        src = file_lines(path)
    except OSError:
        return ""
    st["stop_material"] = st.get("stop_material", 0) + 1
    b2 = min(b, a + 24, len(src))
    out = [f"EDIT MATERIAL: the function you read most, {path} {name} {a}-{b} (now; copy the lines without the numbers):"]
    out += [f"{i:6}| {src[i - 1]}" for i in range(a, b2 + 1)]
    if b2 < b:
        out.append(f"  ... continues to line {b}")
    return "\\n".join(out)

'''


def sub(t, a, b):
    assert t.count(a) == 1, a[:80]
    return t.replace(a, b)


def c2_apy():
    a = (SRC / "skills/agent/scripts/a.py").read_text()
    s0, s1 = a.index("def cmd_check(st, args):"), a.index("def has_change():")
    return a[:s0] + CHECK2 + a[s1:]


def o_apy():
    a = c2_apy()
    a = sub(a, '        _, a, b, _ = hits[0]\n        if len(hits) > 1:',
            '        _, a, b, _ = hits[0]\n        if not TEST_RE.search(path):  # sk_a2o: functions shown, for the STOP READING edit material\n'
            '            st.setdefault("funcs", []).append({"file": path, "name": hits[0][0], "a": a, "b": b})\n        if len(hits) > 1:')
    a = sub(a, "\n\nHANDLERS = {", OUTPUTS + "\nHANDLERS = {")
    a = sub(a, """    save(st)
    warn = banner(st)
    if warn:
        print(warn)
    print(header(st))
    print(body)
    if warn:
        print(warn)
""", """    warn = banner(st)
    extra = edit_block(st)  # sk_a2o: after a source change
    if warn.startswith(">>> STOP READING"):
        mat = stop_material(st)  # sk_a2o: the edit material, first two STOP READINGs
        extra = (extra + "\\n" + mat).strip() if mat else extra
    save(st)
    if warn:
        print(warn)
    print(header(st))
    if extra:
        print(extra)
    print(body)
    if warn:
        print(warn)
""")
    return a


def build_arm(name, apy, prompt, why):
    out = ROOT / "submissions" / name
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SRC, out)
    (out / "skills/agent/scripts/a.py").write_text(apy)
    ip = out / "skills/agent/scripts/install.py"
    ip.write_text(sub(ip.read_text(), '"check": "check                         after the edit: runs .git/agent/check.py -> GREEN (submit) or RED (one repair)",',
                      '"check": "check << \'EOF\' ... EOF            runs your check code (saved; no input = run it again) with a verdict and your next call",'))
    p = (ROOT / prompt).read_text()
    assert "a.py check" in p and "28 tool" in p and "{" not in p
    (out / "prompts/system.md").write_text(p)
    y = (out / "agent.yaml").read_text()
    (out / "agent.yaml").write_text(sub(y, "# sk_a2c (2026-11-24): sk_a2 + post-edit verdict", f"# {name} (2026-11-24): {why} (scripts/make_ska2c2o.py). Was: sk_a2c = sk_a2 + post-edit verdict"))
    print("wrote", out.relative_to(ROOT), len(p.split()), "words")


if __name__ == "__main__":
    build_arm("sk_a2c2", c2_apy(), "scripts/agent_ska2c2/system.md", "sk_a2 + a.py check taking the check code as a heredoc, verdicts before / after the edit")
    build_arm("sk_a2o", o_apy(), "scripts/agent_ska2o/system.md", "sk_a2c2 + a.py outputs: YOUR EDIT / SAME LINES ELSEWHERE after an edit, EDIT MATERIAL at STOP READING")
