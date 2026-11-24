"""sk_a2p2g2 = sk_a2p2 + the late gate, fixed (user 2026-11-24: 'lets fix the gate now, explain each fix' -> 'build it with all five fixes
on the 4 tasks'). r157's sk_a2p2g gate fired in 2/8 runs, edit after a refusal 1/6 (scripts/mine_bank/r157.py). The five fixes:
  1. a refused read is answered with code: the whole function of an EDIT CANDIDATE (numbered, ready to copy) + one line for the other
     two, instead of a bare refusal (r157: after a refusal the next call was another read 4/6, one reply took 67 s);
  2. find still answers after STOP READING, but only inside files already read (r157 fastapi_15589: the refused find was retried);
  3. once STOP READING has shown and there is no change, EVERY a.py output starts with a 3-line EDIT CANDIDATES block (r157: the
     compaction summary dropped the refusal and the candidates, and in fastapi_15589 even invented a 'fallback' the code lacks);
  4. after STOP READING each spot already read can be shown again ONCE, ending with 'your next call is edit_file here'; a second
     re-show of the same spot gets fix 1's answer (r157 fastapi_14419 s2: four re-shows of read code, time-out, the gate never fired);
  5. shell searches cannot be blocked by a.py (harness tool): prompt worked example only (r157 fastapi_15589: os.walk | grep).
The gate still starts at STOP READING (gate_precheck: 6/182 solved runs blocked at STOP vs 14/182 at NO EDIT YET).
a.py = sk_a2's (control) + the code below; prompt scripts/agent_ska2p2g2/system.md written in full.
Run: python3 -I scripts/make_ska2p2g2.py"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "submissions/sk_a2"
NAME = "sk_a2p2g2"

GATE = '''

CAND_FULL = 60  # sk_a2p2g2: at most this many lines of a candidate's function in a READING CLOSED answer


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


def spot_of(path, a, b):
    """The smallest class / function holding the middle of lines a-b (else the range itself)."""
    mid, best = (a + b) // 2, None
    for name, s, e, _ in outline_items(path) or []:
        if s <= mid <= e and (best is None or e - s < best[2] - best[1]):
            best = (name, s, e)
    return (path,) + (best or ("module level", a, b))


def ranked_spots(st):
    """sk_a2p2g2: the 3 spots read most (test files excluded; ties: the most recent first) and per-line read counts."""
    cnt, spots, order = {}, {}, []
    for r in st["reads"]:
        if TEST_RE.search(r["file"]):
            continue
        for i in range(r["a"], r["b"] + 1):
            cnt[(r["file"], i)] = cnt.get((r["file"], i), 0) + 1
        key = spot_of(r["file"], r["a"], r["b"])
        spots[key] = spots.get(key, 0) + 1
        if key in order:
            order.remove(key)
        order.append(key)
    return sorted(spots, key=lambda s: (-spots[s], -order.index(s)))[:3], spots, cnt


def closed(st):
    return bool(st.get("stop_seen")) and not has_change()


def cand_block(st):
    """Fix 3: the short EDIT CANDIDATES block printed at the top of every a.py output while reading is closed."""
    ranked, spots, _ = ranked_spots(st)
    if not ranked:
        return ""
    out = [">>> READING CLOSED: no edit yet after STOP READING. Your next call is edit_file at one of these EDIT CANDIDATES "
           "(the spots you read most). find works only in files you have read; each spot can be shown again once. <<<"]
    out += [f"   {n}. {p} {name} {a}-{b} (read {spots[(p, name, a, b)]} times)" for n, (p, name, a, b) in enumerate(ranked, 1)]
    return "\\n".join(out)


def cand_full(st, why):
    """Fix 1: answer a refused read with one candidate's code (cycling 1, 2, 3 over refusals) + one line for the others."""
    ranked, spots, cnt = ranked_spots(st)
    st["refused"] = st.get("refused", 0) + 1
    head = (f">>> READING CLOSED: {why} Instead, here is EDIT CANDIDATE {{n}}, code you have read. Your next call is edit_file "
            f"here (copy the lines without the numbers) or at another candidate. <<<")
    if not ranked:
        return head.replace("EDIT CANDIDATE {n}, code you have read", "nothing: you have read no source code")
    k = (st["refused"] - 1) % len(ranked)
    path, name, a, b = ranked[k]
    src = file_lines(path)
    b = min(b, len(src))
    more = ""
    if b - a + 1 > CAND_FULL:
        hot = max(range(a, b + 1), key=lambda i: (cnt.get((path, i), 0), -i))
        s = max(a, min(hot - CAND_FULL // 3, b - CAND_FULL + 1))
        more = f"   (the function runs {a}-{b}; shown {s}-{s + CAND_FULL - 1})"
        a, b = s, s + CAND_FULL - 1
    out = [head.replace("{n}", str(k + 1)), f"{k + 1}. {path} {name}:"]
    out += [f"{i:6}| {src[i - 1]}" for i in range(a, b + 1)]
    if more:
        out.append(more)
    out += [f"other candidate {n}: {p} {nm} {s}-{e}" for n, (p, nm, s, e) in enumerate(ranked, 1) if n != k + 1]
    return "\\n".join(out)


def gate(st, cmd, args):
    """sk_a2p2g2: after STOP READING with no change, reading is closed (fixes 1, 2, 4)."""
    if not closed(st) or cmd not in ("find", "outline", "show") or not args:
        return None
    read_files = sorted({r["file"] for r in st["reads"] if not TEST_RE.search(r["file"])})
    if cmd == "find":  # fix 2: only inside files already read
        paths = [rel(a) for a in args[1:] if os.path.exists(os.path.join(WS, rel(a)))]
        words = [args[0]] + [a for a in args[1:] if not os.path.exists(os.path.join(WS, rel(a)))]
        keep = [f for f in read_files if not paths or any(f == p or f.startswith(p.rstrip("/") + "/") for p in paths)]
        if not keep:
            return cand_full(st, "find now searches only the files you have read, and none of them is under that path.")
        body = cmd_find(st, words + keep)
        allf = run(f"git grep -l -I -i -F -e {q(' '.join(words))} -- " + (" ".join(q(p) for p in paths) or "."))
        other = len([f for f in allf.split("\\n") if f and f not in keep]) if allf and not allf.startswith("(timed out") else 0
        if other:
            body += f"\\n(READING CLOSED: {other} other files match; files you have not read are not searched)"
        return body
    if cmd == "outline":
        return cand_full(st, "outline is closed after STOP READING.")
    rng = show_range(args)
    if rng is None:
        return None  # cmd_show gives its own 'no such file / name' message
    path, a, b = rng
    if not any(r["file"] == path and r["a"] <= b and r["b"] >= a for r in st["reads"]):
        return cand_full(st, "code you have not read is not shown after STOP READING.")
    key = list(spot_of(path, a, b))
    seen = st.setdefault("reshown", [])
    if key in seen:  # fix 4: each read spot once
        return cand_full(st, f"{path} {key[1]} was already shown again once after STOP READING.")
    seen.append(key)
    ranked = [list(s) for s in ranked_spots(st)[0]]
    n = ranked.index(key) + 1 if key in ranked else None
    body = cmd_show(st, args)
    return body + (f"\\n>>> This is {'EDIT CANDIDATE ' + str(n) if n else 'code you read before'}. Your next call is edit_file "
                   f"here (copy the lines without the numbers): it will not be shown again. <<<")

'''


def sub(t, a, b):
    assert t.count(a) == 1, a[:80]
    return t.replace(a, b)


def g2_apy():
    a = (SRC / "skills/agent/scripts/a.py").read_text()
    assert "def gate(" not in a and "stop_seen" not in a
    a = sub(a, "\n\nHANDLERS = {", GATE + "\nHANDLERS = {")
    a = sub(a, """        try:
            body = HANDLERS[argv[0].lstrip("-").lower()](st, argv[1:])""", """        try:
            cmd = argv[0].lstrip("-").lower()
            body = gate(st, cmd, argv[1:]) or HANDLERS[cmd](st, argv[1:])  # sk_a2p2g2: the late gate (fixes 1, 2, 4)""")
    a = sub(a, """    save(st)
    warn = banner(st)
    if warn:
        print(warn)
    print(header(st))
""", """    warn = banner(st)
    if warn.startswith(">>> STOP READING"):
        st["stop_seen"] = True  # sk_a2p2g2: reading closes from here
    block = cand_block(st) if closed(st) else ""  # fix 3: the candidates on every output while closed
    save(st)
    if warn:
        print(warn)
    if block:
        print(block)
    print(header(st))
""")
    return a


def build():
    out = ROOT / "submissions" / NAME
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SRC, out)
    (out / "skills/agent/scripts/a.py").write_text(g2_apy())
    p = (ROOT / f"scripts/agent_ska2p2g2/system.md").read_text()
    assert "YOUR EDIT" not in p and "a.py check" not in p and "28 tool" in p and "{" not in p and "READING CLOSED" in p
    (out / "prompts/system.md").write_text(p)
    y = (out / "agent.yaml").read_text()
    (out / "agent.yaml").write_text(sub(y, "# sk_a2: mix + the agent's reading tool",
                                        f"# {NAME} (2026-11-24): sk_a2p2 + the late gate with fixes 1-5 (scripts/make_ska2p2g2.py). sk_a2 was: mix + the agent's reading tool"))
    print("wrote", out.relative_to(ROOT), len(p.split()), "words")


if __name__ == "__main__":
    build()
