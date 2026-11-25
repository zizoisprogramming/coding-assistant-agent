"""sk_a2s = sk_a2 + the EXPECTED-RESULT CARD (user 2026-11-25: 'research the options first ... a smart way to get the right info is
the missing piece as well as knowing what should be the end result' -> 'run the two offline check' -> 'build it on the 8 tasks').
Evidence (PLAN 'RESEARCH + TWO OFFLINE CHECKS 2026-11-25'): TrajSpec (arXiv 2607.07882) refines the issue into ExpectedBehavior /
ObservedBehavior / RootCause reviewed against the repo: 41.0 -> 59.7% (GPT-5-mini), 48.0% without the repository review; SpecRover
(2408.02232) feeds 'how this function should behave' summaries to the patch writer. Our data: 11/29 r159-r161 wrong patches went
against the behaviour the issue states; an existing test names the fixed function in 50% of tasks (rich 69%, fastapi 34%).
The card (single agent, harness tools only, no gate, nothing blocked):
  - asked for only when NO EDIT YET shows (10 looks / 210 s) and there is no edit and no card: fast runs never see it;
  - written with write_file to .git/agent/card.md (4 lines EXPECTED / NOW / CAUSE / CHANGE; write_file, not a shell command:
    long model-written text inside run_command produced unparseable text calls, r129-r131), then python3 .git/agent/a.py card;
  - a.py checks it against the repo (TrajSpec's review): all 4 fields; CAUSE names an existing file + function / lines that were
    READ; EXPECTED differs from NOW; quoted names not found in the repository are listed (a warning: new names from the issue are
    fine). A rejected card gets one rewrite; the second card is accepted with its problems listed;
  - an accepted card answers with the CAUSE function's code (numbered, ready to copy) and up to 2 existing test functions that name
    the function (or its class): how the tests call it and what they assert;
  - the card is pinned in MEMORY on every later output (compaction cannot drop it); with a card and no edit, the banner says the
    next call is the edit at CAUSE.
a.py = sk_a2's (control) + the code below; prompt scripts/agent_ska2s/system.md written in full.
Run: python3 -I scripts/make_ska2s.py"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "submissions/sk_a2"
NAME = "sk_a2s"

CARD = '''

CARD_FILE = os.path.join(HERE, "card.md")
CARD_CODE, CARD_TEST = 60, 25  # sk_a2s: lines of the CAUSE function / of one existing test shown with an accepted card
FIELDS = ("EXPECTED", "NOW", "CAUSE", "CHANGE")


def card_fields(text):
    """{FIELD: text} from 'FIELD: text' lines (a field may continue on the next lines)."""
    out, cur = {}, None
    for line in text.splitlines():
        m = re.match(r"^\\s*[-*#]*\\s*(EXPECTED|NOW|CAUSE|CHANGE)\\s*[:=-]\\s*(.*)$", line, re.I)
        if m:
            cur = m.group(1).upper()
            out[cur] = m.group(2).strip()
        elif cur and line.strip():
            out[cur] = (out[cur] + " " + line.strip()).strip()
    return out


def cause_spot(cause):
    """(path, name, a, b) for the CAUSE text, or an error message."""
    toks = re.findall(r"[\\w./-]+", cause)
    path = next((t for t in toks if t.endswith(".py") or "/" in t), None)
    if path is None:
        return "CAUSE has no file path: write CAUSE: path/to/file.py Function.name START-END"
    path = rel(re.sub(r":\\d+(-\\d+)?$", "", path))
    if not os.path.isfile(os.path.join(WS, path)):
        return f"CAUSE names {path}, which is not a file in the repository"
    items = outline_items(path) or []
    rest = cause.split(path, 1)[-1] if path in cause else cause
    names = [t for t in re.findall(r"[A-Za-z_][\\w.]*", rest) if not t.endswith(".py")]
    for t in names:
        hits = [it for it in items if it[0] == t or it[0].endswith("." + t)]
        if hits:
            return (path, hits[0][0], hits[0][1], hits[0][2])
    nums = [int(x) for x in re.findall(r"\\b\\d+\\b", rest)]
    if nums:
        a, b = nums[0], nums[1] if len(nums) > 1 and nums[1] >= nums[0] else nums[0]
        mid, best = (a + b) // 2, None
        for name, s, e, _ in items:
            if s <= mid <= e and (best is None or e - s < best[2] - best[1]):
                best = (name, s, e)
        return (path,) + (best or ("lines", a, b))
    return f"CAUSE names no function or line numbers of {path}: write CAUSE: {path} Function.name START-END"


def existing_tests(name):
    """Up to 2 (path, test_name, start, end) existing test functions that name `name` (a word)."""
    out = run(f"git grep -n -w -I -F -e {q(name)} -- '*test*.py'")
    seen, res = set(), []
    for line in out.splitlines() if out and not out.startswith("(timed out") else []:
        m = re.match(r"^([^:]+):(\\d+):", line)
        if not m or not TEST_RE.search(m.group(1)):
            continue
        p, n = m.group(1), int(m.group(2))
        for tn, s, e, _ in outline_items(p) or []:
            if tn.split(".")[-1].startswith("test") and s <= n <= e and (p, tn) not in seen:
                seen.add((p, tn)); res.append((p, tn, s, e))
        if len(res) >= 2:
            break
    return res


def cmd_card(st, args):
    """sk_a2s: check .git/agent/card.md against the repository; pin it when accepted."""
    try:
        text = open(CARD_FILE).read()
    except OSError:
        return ("(no card yet) Write it with write_file to .git/agent/card.md, four lines:\\n"
                "EXPECTED: what the code must do after your edit (names and messages exactly as in the issue)\\n"
                "NOW: what the code does today, and the line that does it\\n"
                "CAUSE: path/to/file.py Function.name START-END (code you have read)\\n"
                "CHANGE: the edit in one line\\nthen run python3 .git/agent/a.py card")
    f = card_fields(text)
    st["card_tries"] = st.get("card_tries", 0) + 1
    problems = [f"{k} is missing" for k in FIELDS if len(f.get(k, "").split()) < 2]
    spot = cause_spot(f.get("CAUSE", "")) if "CAUSE is missing" not in problems else None
    if isinstance(spot, str):
        problems.append(spot); spot = None
    if spot and not any(r["file"] == spot[0] and r["a"] <= spot[3] and r["b"] >= spot[2] for r in st["reads"]):
        problems.append(f"CAUSE names {spot[0]} {spot[1]} {spot[2]}-{spot[3]}, which you have not read: show it first")
    e, n = set(f.get("EXPECTED", "").lower().split()), set(f.get("NOW", "").lower().split())
    if e and n and len(e & n) >= 0.9 * max(len(e), len(n)):
        problems.append("EXPECTED says the same as NOW: EXPECTED is the behaviour AFTER your edit")
    quoted = set(re.findall(r"`([^`]{2,60})`", f.get("EXPECTED", "") + " " + f.get("CHANGE", "")))
    unknown = []
    for qn in sorted(quoted)[:8]:
        word = re.findall(r"[A-Za-z_]\\w{2,}", qn)
        if word and not run(f"git grep -l -I -F -e {q(max(word, key=len))} -- . ':!*test*'"):
            unknown.append(qn)
    note = ("\\nnot found in the repository: " + ", ".join(unknown) + " (fine if the issue names them as new: copy them "
            "exactly as the issue writes them)") if unknown else ""
    if problems and st["card_tries"] < 2:
        return ("CARD REJECTED (1 rewrite left): " + "; ".join(problems) + ". Fix .git/agent/card.md with write_file, then "
                "python3 .git/agent/a.py card." + note)
    st["card"] = {k: f.get(k, "") for k in FIELDS}
    st["card_spot"] = list(spot) if spot else None
    out = ["CARD SET" + (" (with problems: " + "; ".join(problems) + ")" if problems else "") + ". It stays in MEMORY. "
           "Your next call is edit_file at CAUSE, making CHANGE, so that EXPECTED holds." + note]
    if spot:
        path, name, a, b = spot
        src = file_lines(path)
        b = min(b, len(src), a + CARD_CODE - 1)
        out.append(f"CAUSE {path} {name} (copy the lines without the numbers):")
        out += [f"{i:6}| {src[i - 1]}" for i in range(a, b + 1)]
        tests = existing_tests(name.split(".")[-1]) or (existing_tests(name.split(".")[0]) if "." in name else [])
        if tests:
            out.append("How existing tests use it (hidden tests are usually written like these; EXPECTED must fit them):")
            for k, (p, tn, s, e) in enumerate(tests):
                tl = file_lines(p)
                e2 = min(e, s + CARD_TEST - 1) if k == 0 else s
                out.append(f"{p} {tn} {s}-{e}:")
                out += [f"{i:6}| {tl[i - 1]}" for i in range(s, min(e2, len(tl)) + 1)]
        else:
            out.append("(no existing test names it)")
    return "\\n".join(out)


def card_lines(st):
    c = st.get("card")
    if not c:
        return []
    return ["CARD (yours, checked): EXPECTED: " + c["EXPECTED"][:300], "  NOW: " + c["NOW"][:200],
            "  CAUSE: " + c["CAUSE"][:160], "  CHANGE: " + c["CHANGE"][:240]]

'''


def sub(t, a, b):
    assert t.count(a) == 1, a[:80]
    return t.replace(a, b)


def s_apy():
    a = (SRC / "skills/agent/scripts/a.py").read_text()
    assert "def cmd_card(" not in a
    a = sub(a, "\n\nHANDLERS = {", CARD + "\nHANDLERS = {")
    a = sub(a, '"impact": cmd_impact, "check": cmd_check}', '"impact": cmd_impact, "check": cmd_check, "card": cmd_card}')
    a = sub(a, """    lines.append("=" * 40)
    return "\\n".join(lines)""", """    lines += card_lines(st)  # sk_a2s: the checked card, pinned
    lines.append("=" * 40)
    return "\\n".join(lines)""")
    a = sub(a, """        return f">>> NO EDIT YET: {used}. If you know which lines to change, your next call is the edit. <<<\"""",
            """        if st.get("card"):  # sk_a2s
            return f">>> CARD SET, NO EDIT YET: {used}. Your next call is edit_file at CAUSE ({st['card']['CAUSE'][:80]}). <<<"
        return (f">>> NO EDIT YET: {used}. If you know the edit, make it now. Otherwise write your EXPECTED-RESULT CARD: "
                f"write_file .git/agent/card.md (EXPECTED / NOW / CAUSE / CHANGE), then python3 .git/agent/a.py card. <<<")""")
    return a


def s_install():
    t = (SRC / "skills/agent/scripts/install.py").read_text()
    return sub(t, '''    "check": "check                         after an edit: .git/agent/repro.py + nearest tests + git status",
}''', '''    "check": "check                         after an edit: .git/agent/repro.py + nearest tests + git status",
    "card": "card                          check your card .git/agent/card.md (EXPECTED / NOW / CAUSE / CHANGE)",
}''')


def build():
    out = ROOT / "submissions" / NAME
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SRC, out)
    (out / "skills/agent/scripts/a.py").write_text(s_apy())
    (out / "skills/agent/scripts/install.py").write_text(s_install())
    (out / "skills/agent/scripts/commands.txt").write_text("find outline show card banner reshow\n")
    p = (ROOT / "scripts/agent_ska2s/system.md").read_text()
    assert "28 tool" in p and "{" not in p and "card.md" in p and "a.py card" in p
    (out / "prompts/system.md").write_text(p)
    y = (out / "agent.yaml").read_text()
    (out / "agent.yaml").write_text(sub(y, "# sk_a2: mix + the agent's reading tool",
                                        f"# {NAME} (2026-11-25): sk_a2 + the expected-result card (scripts/make_ska2s.py). sk_a2 was: mix + the agent's reading tool"))
    print("wrote", out.relative_to(ROOT), len(p.split()), "words")


if __name__ == "__main__":
    build()
