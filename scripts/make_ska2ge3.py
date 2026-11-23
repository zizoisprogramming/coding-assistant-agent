"""sk_a2ge3 = sk_a2ge2 with a brief the model cannot garble (docs/PLAN.md 'RESULT r151'; user 2026-11-23: 'build it with both').
r151: the hand-over got fast (brief median 198 s) but in 4/8 runs the gatherer's final reply hit the 4,096-token cap while it was still working
the problem out, and the 'brief' the editor got was leaked thinking with no FILE line. Both fixes:
  (1) a.py builds the brief's code part itself: command 'brief [FILE NAME]' prints FILE / FUNCTION / CURRENT LINES (the function's exact
      lines, <= FUNC_LINES, no line numbers) / SAME LINES ELSEWHERE (other places where its non-trivial lines occur, with their functions) /
      the previously read function as ALSO READ, and saves the block to .git/agent/brief.txt; READING CLOSED prints the same block. The
      gatherer's reply = that block copied + RULE / EDIT / CHECK (one line each).
  (2) the editor's first call is python3 .git/agent/a.py brief: the file and lines always arrive clean; the gatherer's reply (in the editor's
      prompt as 'your colleague's notes') only adds RULE / EDIT / CHECK and may be garbled.
a.py option renamed 'brief' -> 'close' (the closure: 8 looks or 150 s, unchanged) so 'brief' can be a command. Prompts written in full:
scripts/agent_ska2ge3/gather.md, editor.md. Everything else = sk_a2ge2. Run: python3 -I scripts/make_ska2ge3.py"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC, OUT = ROOT / "submissions/sk_a2ge2", ROOT / "submissions/sk_a2ge3"
FUNC_LINES = 60

BRIEF = '''

BRIEF_FILE = os.path.join(HERE, "brief.txt")
FUNC_LINES = __FUNC_LINES__


def _func_at(path, line):
    best = None
    for name, a, b, _ in outline_items(path) or []:
        if a <= line <= b and (best is None or b - a < best[2] - best[1]):
            best = (name, a, b)
    return best[0] if best else "module level"


def same_lines(f):
    """Other places (outside this function) where the function's non-trivial lines occur: a fix often needs all of them."""
    try:
        src = file_lines(f["file"])
    except OSError:
        return []
    cands = []
    for l in src[f["a"] - 1:f["b"]]:
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
        path, n, text = m.group(1), int(m.group(2)), m.group(3)
        if TEST_RE.search(path) or (path == f["file"] and f["a"] <= n <= f["b"]):
            continue
        key = (path, _func_at(path, n))
        g = groups.setdefault(key, {"n": 0, "first": (n, text.strip()[:90]), "lines": set()})
        if text.strip() not in g["lines"]:
            g["lines"].add(text.strip()); g["n"] += 1
            if len(text.strip()) > len(g["first"][1]):
                g["first"] = (n, text.strip()[:90])
    ranked = sorted(groups.items(), key=lambda kv: (-kv[1]["n"], kv[0][0] != f["file"]))
    return [f"{path} {func}: {g['n']} of the same lines, e.g. line {g['first'][0]}: {g['first'][1]}"
            for (path, func), g in ranked if g["n"] >= 2][:3]


def brief_block(st):
    funcs = [f for f in st.get("funcs", []) if not TEST_RE.search(f["file"])]
    tgt = st.get("brief_target")
    order = []
    for f in ([tgt] if tgt else []) + list(reversed(funcs)):
        if f and (f["file"], f["name"]) not in [(o["file"], o["name"]) for o in order]:
            order.append(f)
    if not order:
        return "BRIEF: no source function has been shown yet. Use python3 .git/agent/a.py show FILE NAME, then brief."
    lines = ["BRIEF (written by a.py from the files as they are now; saved for the editor)"]
    for i, f in enumerate(order[:2]):
        try:
            src = file_lines(f["file"])
        except OSError:
            continue
        a, b = f["a"], min(f["b"], len(src))
        body = src[a - 1:b]
        lines.append(("FILE: " if i == 0 else "ALSO READ (second candidate): ") + f["file"])
        lines.append(f"FUNCTION: {f['name']} ({a}-{b})")
        lines.append("CURRENT LINES (exact, without line numbers):")
        lines += body[:FUNC_LINES]
        if len(body) > FUNC_LINES:
            lines.append(f"... (the function continues to line {b}: python3 .git/agent/a.py show {f['file']} {a + FUNC_LINES} {b})")
        if i == 0:
            same = same_lines(f)
            lines.append("SAME LINES ELSEWHERE: " + ("none" if not same else "change them too if the same fix applies"))
            lines += ["  " + s for s in same]
    text = "\\n".join(lines)
    try:
        with open(BRIEF_FILE, "w") as fh:
            fh.write(text + "\\n")
    except OSError:
        pass
    return text


def cmd_brief(st, args):
    """sk_a2ge3: the BRIEF's code part (FILE / FUNCTION / CURRENT LINES / SAME LINES ELSEWHERE), printed and saved for the editor."""
    if len(args) >= 2:
        path, name = rel(args[0]), args[1]
        hits = [it for it in (outline_items(path) or []) if it[0] == name or it[0].endswith("." + name)]
        if not hits:
            return f"(no class or function named {name} in {path}; use outline {path})"
        st["brief_target"] = {"file": path, "name": hits[0][0], "a": hits[0][1], "b": hits[0][2]}
    return brief_block(st)

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
    a = sub(a, 'OPTIONS = {"banner", "reshow", "brief"}  # sk_a2ge: + brief (READING CLOSED after 10 looks until a change)',
            'OPTIONS = {"banner", "reshow", "close"}  # sk_a2ge3: close = READING CLOSED (8 looks or 150 s, until a change); brief is a command')
    a = sub(a, '        _, a, b, _ = hits[0]\n        if len(hits) > 1:',
            '        _, a, b, _ = hits[0]\n        if not TEST_RE.search(path):  # sk_a2ge3: functions shown, for the BRIEF\n'
            '            st.setdefault("funcs", []).append({"file": path, "name": hits[0][0], "a": a, "b": b})\n        if len(hits) > 1:')
    a = sub(a, '    if "brief" not in OPTS or cmd not in ("find", "outline", "show"):', '    if "close" not in OPTS or cmd not in ("find", "outline", "show"):')
    old_tail = a[a.index('    lines = [f">>> READING CLOSED:'):a.index('    return "\\n".join(lines)\n\n\nHANDLERS')]
    a = a.replace(old_tail, '''    lines = [f">>> READING CLOSED: {st['looks']} looks, {int(secs)} s, and no change in the repository yet, so a.py shows no more code until there "
             f"is one. Gathering: your next reply is the BRIEF below, copied, with your RULE, EDIT and CHECK lines added (no tool call). "
             f"Editing: your next call is the edit, from the CURRENT LINES below. Reading opens again after the edit. <<<",
             brief_block(st)]
''')
    a = sub(a, "\n\nHANDLERS = {", BRIEF.replace("__FUNC_LINES__", str(FUNC_LINES)) + "\nHANDLERS = {")
    a = sub(a, '"impact": cmd_impact, "check": cmd_check}', '"impact": cmd_impact, "check": cmd_check, "brief": cmd_brief}')
    ap.write_text(a)
    (OUT / "skills/agent/scripts/commands.txt").write_text("find outline show brief banner reshow close\n")
    ip = OUT / "skills/agent/scripts/install.py"
    ins = ip.read_text()
    ins = sub(ins, '    "check": "check                         after an edit: .git/agent/repro.py + nearest tests + git status",',
              '    "check": "check                         after an edit: .git/agent/repro.py + nearest tests + git status",\n'
              '    "brief": "brief [FILE NAME]             the BRIEF: file, function, current lines, same lines elsewhere (saved for the editor)",')
    ip.write_text(ins)
    for stg in ("gather", "editor"):
        p = (ROOT / f"scripts/agent_ska2ge3/{stg}.md").read_text()
        assert "a.py brief" in p
        if stg == "gather":
            assert "{" not in p
        else:
            assert p.count("{") == 2 and "{problem_description}" in p and "{brief}" in p
        (OUT / f"prompts/{stg}.md").write_text(p)
    y = (OUT / "agent.yaml").read_text()
    (OUT / "agent.yaml").write_text("# sk_a2ge3 (2026-11-23): sk_a2ge2 + a.py-built BRIEF (a.py brief, saved to .git/agent/brief.txt; the editor reads it first)"
                                    " (scripts/make_ska2ge3.py). " + y.lstrip("# "))
    print("wrote", OUT.relative_to(ROOT))


if __name__ == "__main__":
    build()
