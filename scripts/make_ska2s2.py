"""sk_a2s2 = sk_a2s (the expected-result card) + a ONE-TIME HOLD (user 2026-11-25: 'build it with the one-time hold on the 8 tasks').
r162 (scripts/mine_bank/r162.py): the card asked for in the NO EDIT YET banner was written in 1/12 asked runs; where written (3 runs)
it was accepted first try, the next call was the edit and the run solved (3/3). A banner request is ignored (also sc1 r135); a
one-time hold-back that answers the next call with the requested step was obeyed 3/3 (sbE3 r128). r162 also lost sk_a2's
'your next call is the edit' banner wording (no-patch 9 vs 5).
Changes vs sk_a2s:
  - NO EDIT YET banner = sk_a2's exact text again (the card is not asked for in the banner);
  - the hold: the FIRST find / outline / show sent once NO EDIT YET applies (10 looks or 210 s), with no change in the working tree
    and no card, is not run; it is answered once with the card request: the template, the 3 spots read most (for CAUSE), and
    'your next call is the edit if you know it, otherwise write_file the card'. The read after it runs normally; no second hold;
  - the prompt (written in full) describes the hold and its worked example (Example 2), plus the hold when the edit is already
    known (Example 3: the edit, no card).
a.py = sk_a2s's (= sk_a2's + the card) + the hold; install.py and commands.txt as sk_a2s.
Run: python3 -I scripts/make_ska2s2.py"""
import importlib.util
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "sk_a2s2"
_spec = importlib.util.spec_from_file_location("make_ska2s", ROOT / "scripts/make_ska2s.py")
S = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(S)

HOLD = '''

def hold(st, cmd):
    """sk_a2s2: the one-time hold. The first read once NO EDIT YET applies, with no change and no card, gets the card request."""
    if cmd not in ("find", "outline", "show") or st.get("held") or st.get("card") or "banner" not in OPTS:
        return None
    secs = int(time.time() - st.get("t0", time.time()))
    if st["looks"] < NO_EDIT_LOOKS and secs < NO_EDIT_SECONDS:
        return None
    if has_change():
        return None
    st["held"] = True
    spots, order = {}, []
    for r in st["reads"]:
        if TEST_RE.search(r["file"]):
            continue
        mid, best = (r["a"] + r["b"]) // 2, None
        for name, s, e, _ in outline_items(r["file"]) or []:
            if s <= mid <= e and (best is None or e - s < best[2] - best[1]):
                best = (name, s, e)
        key = (r["file"],) + (best or ("lines", r["a"], r["b"]))
        spots[key] = spots.get(key, 0) + 1
        if key in order:
            order.remove(key)
        order.append(key)
    top = sorted(spots, key=lambda k: (-spots[k], -order.index(k)))[:3]
    out = [f">>> HELD ONCE: NO EDIT YET after {st['looks']} looks and {secs // 60}:{secs % 60:02d}. This read was not run. If you "
           f"know the edit, your next call is that edit. Otherwise your next call is write_file .git/agent/card.md with your "
           f"EXPECTED-RESULT CARD, then python3 .git/agent/a.py card. Reads work again from the next call. <<<",
           "The card, four lines:",
           "EXPECTED: what the code must do AFTER your edit, as the issue asks (exact names, values, messages; what stays the same)",
           "NOW: what the code does today, and the line that does it",
           "CAUSE: path/to/file.py Function.name START-END   (code you have read)",
           "CHANGE: the edit in one line"]
    if top:
        out.append("The spots you read most (a CAUSE is usually one of them):")
        out += [f"   {p} {nm} {a}-{b} (read {spots[(p, nm, a, b)]} times)" for p, nm, a, b in top]
    return "\\n".join(out)

'''


def sub(t, a, b):
    assert t.count(a) == 1, a[:80]
    return t.replace(a, b)


def s2_apy():
    a = S.s_apy()  # sk_a2's a.py + the card
    a = sub(a, """        if st.get("card"):  # sk_a2s
            return f">>> CARD SET, NO EDIT YET: {used}. Your next call is edit_file at CAUSE ({st['card']['CAUSE'][:80]}). <<<"
        return (f">>> NO EDIT YET: {used}. If you know the edit, make it now. Otherwise write your EXPECTED-RESULT CARD: "
                f"write_file .git/agent/card.md (EXPECTED / NOW / CAUSE / CHANGE), then python3 .git/agent/a.py card. <<<")""",
            """        if st.get("card"):  # sk_a2s
            return f">>> CARD SET, NO EDIT YET: {used}. Your next call is edit_file at CAUSE ({st['card']['CAUSE'][:80]}). <<<"
        return f">>> NO EDIT YET: {used}. If you know which lines to change, your next call is the edit. <<<\"""")
    a = sub(a, "\n\nHANDLERS = {", HOLD + "\nHANDLERS = {")
    a = sub(a, """        try:
            body = HANDLERS[argv[0].lstrip("-").lower()](st, argv[1:])""", """        try:
            cmd = argv[0].lstrip("-").lower()
            body = hold(st, cmd) or HANDLERS[cmd](st, argv[1:])  # sk_a2s2: the one-time hold""")
    return a


def build():
    out = ROOT / "submissions" / NAME
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(S.SRC, out)
    (out / "skills/agent/scripts/a.py").write_text(s2_apy())
    (out / "skills/agent/scripts/install.py").write_text(S.s_install())
    (out / "skills/agent/scripts/commands.txt").write_text("find outline show card banner reshow\n")
    p = (ROOT / "scripts/agent_ska2s2/system.md").read_text()
    assert "28 tool" in p and "{" not in p and "card.md" in p and "HELD ONCE" in p
    (out / "prompts/system.md").write_text(p)
    y = (out / "agent.yaml").read_text()
    (out / "agent.yaml").write_text(sub(y, "# sk_a2: mix + the agent's reading tool",
                                        f"# {NAME} (2026-11-25): sk_a2s (expected-result card) + one-time hold, sk_a2's banner (scripts/make_ska2s2.py). sk_a2 was: mix + the agent's reading tool"))
    print("wrote", out.relative_to(ROOT), len(p.split()), "words")


if __name__ == "__main__":
    build()
