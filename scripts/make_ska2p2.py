"""sk_a2p2 and sk_a2p2g (user 2026-11-24: 'drop the "YOUR EDIT" thing ... lets see how we can solve the rest' -> 'build it, all three arms on the 4 tasks').
  sk_a2p2  = sk_a2 (a.py unchanged) + prompt scripts/agent_ska2p2/system.md: sk_a2o2n's prompt without YOUR EDIT (Step 1 'no experiments before
             the edit'; Examples: plain path; r155 rich_3278 failure -> edit from the read; r156 rich_4079 failure -> edit at STOP READING).
  sk_a2p2g = sk_a2p2 + a late gate in a.py (prompt scripts/agent_ska2p2g/system.md: + 'READING CLOSED' section and Example 3 with the gate).
             Once a.py has printed STOP READING (15 looks or 300 s, no change) and there is still no change in the working tree, find /
             outline / show of code not read before are refused with READING CLOSED + EDIT CANDIDATES: the 3 spots read most (smallest
             enclosing function of each read, test files excluded), each with the 8 most-read lines, numbered. Re-showing read code is
             allowed; the gate opens once a change exists.
Evidence (scripts/mine_bank/noedit_study.py, gate_precheck.py): 110/396 sk_a2-family runs end with no edit (62 time, 46 call limit with the edit
refused at call 29+); first-edit lines were on screen ~3 min / 15 calls before the attempt; the gate would block 6/168 solved runs (edit lines
first read after STOP); the top-3 most-read spots held the real-fix lines in 62/71 runs (r155_o.py).
Run: python3 -I scripts/make_ska2p2.py"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "submissions/sk_a2"

GATE = '''

def show_range(args):
    """(path, a, b) that show would print for these args, or None (cmd_show's own parsing)."""
    path, rest = args[0], args[1:]
    m = re.match(r"^(.*?):(\\d+)(?:-(\\d+))?$", path)
    if m:
        path, rest = m.group(1), [m.group(2)] + ([m.group(3)] if m.group(3) else [])
    path = rel(path)
    if not os.path.isfile(os.path.join(WS, path)):
        return None
    nums = [int(x) for x in re.findall(r"\\d+", " ".join(rest))]
    if rest and not nums:
        hits = [it for it in (outline_items(path) or []) if it[0] == rest[0] or it[0].endswith("." + rest[0])]
        return (path, hits[0][1], hits[0][2]) if hits else None
    a = max(nums[0] if nums else 1, 1)
    b = nums[1] if len(nums) > 1 and nums[1] >= a else a + 79
    return (path, a, b)


def candidates(st):
    """sk_a2p2g: the 3 spots read most (smallest enclosing function of each read; test files excluded), 8 most-read lines each."""
    cnt, spots, order = {}, {}, []
    for k, r in enumerate(st["reads"]):
        if TEST_RE.search(r["file"]):
            continue
        for i in range(r["a"], r["b"] + 1):
            cnt[(r["file"], i)] = cnt.get((r["file"], i), 0) + 1
        mid, best = (r["a"] + r["b"]) // 2, None
        for name, a, b, _ in outline_items(r["file"]) or []:
            if a <= mid <= b and (best is None or b - a < best[2] - best[1]):
                best = (name, a, b)
        key = (r["file"],) + (best or ("module level", r["a"], r["b"]))
        spots[key] = spots.get(key, 0) + 1
        if key in order:
            order.remove(key)
        order.append(key)
    ranked = sorted(spots, key=lambda s: (-spots[s], -order.index(s)))[:3]
    out = ["EDIT CANDIDATES (the spots you read most):"]
    for n, key in enumerate(ranked, 1):
        path, name, a, b = key
        try:
            src = file_lines(path)
        except OSError:
            continue
        b = min(b, len(src))
        best_s, best_v = a, -1
        for s in range(a, max(a, b - 7) + 1):
            v = sum(cnt.get((path, i), 0) for i in range(s, min(s + 8, b + 1)))
            if v > best_v:
                best_s, best_v = s, v
        out.append(f"{n}. {path} {name} {a}-{b} (read {spots[key]} times):")
        out += [f"   {i:6}| {src[i - 1]}" for i in range(best_s, min(best_s + 8, b + 1))]
    return "\\n".join(out) if len(out) > 1 else ""


def gate(st, cmd, args):
    """sk_a2p2g: after STOP READING with no change, refuse find / outline / show of code not read yet."""
    if not st.get("stop_seen") or cmd not in ("find", "outline", "show") or has_change():
        return None
    if cmd == "show" and args:
        rng = show_range(args)
        if rng is None:
            return None
        path, a, b = rng
        if any(r["file"] == path and r["a"] <= b and r["b"] >= a for r in st["reads"]):
            return None
    st["refused"] = st.get("refused", 0) + 1
    return (">>> READING CLOSED: STOP READING was shown and there is still no edit, so code you have not read is not shown any "
            "more. The lines to change are almost always among what you read. Your next call is edit_file at one of the EDIT "
            "CANDIDATES below (copy the lines without the numbers); you may show one of them again first. <<<\\n" + candidates(st))

'''


def sub(t, a, b):
    assert t.count(a) == 1, a[:80]
    return t.replace(a, b)


def g_apy():
    a = (SRC / "skills/agent/scripts/a.py").read_text()
    a = sub(a, "\n\nHANDLERS = {", GATE + "\nHANDLERS = {")
    a = sub(a, """        try:
            body = HANDLERS[argv[0].lstrip("-").lower()](st, argv[1:])""", """        try:
            cmd = argv[0].lstrip("-").lower()
            body = gate(st, cmd, argv[1:]) or HANDLERS[cmd](st, argv[1:])  # sk_a2p2g: the late gate""")
    a = sub(a, """    save(st)
    warn = banner(st)
""", """    warn = banner(st)
    if warn.startswith(">>> STOP READING"):
        st["stop_seen"] = True  # sk_a2p2g: the gate closes from the next call
    save(st)
""")
    return a


def build_arm(name, apy, prompt, why):
    out = ROOT / "submissions" / name
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SRC, out)
    if apy is not None:
        (out / "skills/agent/scripts/a.py").write_text(apy)
    p = (ROOT / prompt).read_text()
    assert "YOUR EDIT" not in p and "a.py check" not in p and "28 tool" in p and "{" not in p
    (out / "prompts/system.md").write_text(p)
    y = (out / "agent.yaml").read_text()
    (out / "agent.yaml").write_text(sub(y, "# sk_a2: mix + the agent's reading tool", f"# {name} (2026-11-24): {why} (scripts/make_ska2p2.py). sk_a2 was: mix + the agent's reading tool"))
    print("wrote", out.relative_to(ROOT), len(p.split()), "words")


if __name__ == "__main__":
    build_arm("sk_a2p2", None, "scripts/agent_ska2p2/system.md", "sk_a2 + prompt: no experiments before the edit, r155/r156 failures as worked examples")
    build_arm("sk_a2p2g", g_apy(), "scripts/agent_ska2p2g/system.md", "sk_a2p2 + late gate: after STOP READING, unread code refused with EDIT CANDIDATES")
