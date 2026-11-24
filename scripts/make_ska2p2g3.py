"""sk_a2p2g3 = sk_a2p2g2 + the r160 fixes (user 2026-11-24: 'lets fix the reshow loophole and the dead-end loop' -> 'build it on the 8 tasks').
r160 (scripts/mine_bank/r160.py): sk_a2 9/16 vs sk_a2p2g2 8/16; pooled r159+r160 11/24 vs 10/24, no-patch 6 vs 2. Two holes:
  Fix A, the re-show loophole: g2 allowed one re-show per ANY read spot, and every re-show raised that spot's read count, so the
     EDIT CANDIDATES list drifted to whatever was re-shown last (r160 rich_3470 s1: end_capture, _exit_buffer, _check_buffer,
     _enter_buffer, ... in a row; the solving edit was at Console._write_buffer = candidate 3 at STOP, gone from the list after 2
     re-shows). Now the 3 candidates are FROZEN when reading closes, and only those 3 can be shown again, once each; any other
     show is answered with the next candidate's code.
  Fix B, the dead-end loop (r160 rich_4079 s2: 14 of 15 looks were find, 2 spots read once each; the gate kept answering finds,
     the harness summary said the agent 'reached a dead end and ceased operations', 15 empty submit_patch calls, then
     run_skill_script again, which RESET the memory, the clock and the gate):
     B1 reading closes only once real code was read (a spot read twice or 3 spots): pigeonhole = 3 shows. In r159/r160 only that
        one run reached STOP with <= 2 shows (others 4-12), so B1 changes nothing else;
     B2 the prompt: when submit_patch returns "patch_size": 0, the next call is the edit at EDIT CANDIDATE 1; a summary saying
        'dead end' is not an order to stop (worked Example 7). submit_patch is a harness tool: its output cannot carry a hint.
        Bank: 22 / ~5,100 saved runs had >= 5 empty submits (onset median ~330 s), sk_a2 runs included (r147, r148, r158);
     B3 install.py run again keeps the memory (state.json with looks > 0) and prints MEMORY + candidates + 'your next call'.
a.py = sk_a2's (control) + the code below; install.py = sk_a2's + B3; prompt scripts/agent_ska2p2g3/system.md written in full.
Run: python3 -I scripts/make_ska2p2g3.py"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "submissions/sk_a2"
NAME = "sk_a2p2g3"

GATE = '''

CAND_FULL = 60  # sk_a2p2g3: at most this many lines of a candidate's function in a READING CLOSED answer


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
    return [path] + list(best or ("module level", a, b))


def ranked_spots(st):
    """The 3 spots read most (test files excluded; ties: the most recent first), all spot counts, per-line read counts."""
    cnt, spots, order = {}, {}, []
    for r in st["reads"]:
        if TEST_RE.search(r["file"]):
            continue
        for i in range(r["a"], r["b"] + 1):
            cnt[(r["file"], i)] = cnt.get((r["file"], i), 0) + 1
        key = tuple(spot_of(r["file"], r["a"], r["b"]))
        spots[key] = spots.get(key, 0) + 1
        if key in order:
            order.remove(key)
        order.append(key)
    return sorted(spots, key=lambda s: (-spots[s], -order.index(s)))[:3], spots, cnt


def freeze(st):
    """Fixes A + B1: once STOP READING has shown, with no change, and real code was read (a spot twice or 3 spots), the
    3 EDIT CANDIDATES are fixed for the rest of the task."""
    if st.get("cands") or not st.get("stop_seen") or has_change():
        return
    ranked, spots, _ = ranked_spots(st)
    if any(v >= 2 for v in spots.values()) or len(spots) >= 3:
        st["cands"] = [list(s) + [spots[s]] for s in ranked]


def closed(st):
    return bool(st.get("cands")) and not has_change()


def cand_block(st):
    """The short EDIT CANDIDATES block printed at the top of every a.py output while reading is closed."""
    out = [">>> READING CLOSED: no edit yet after STOP READING. Your next call is edit_file at one of these EDIT CANDIDATES "
           "(fixed when reading closed). find works only in files you have read; each candidate can be shown again once. <<<"]
    out += [f"   {n}. {p} {name} {a}-{b} (read {k} times)" for n, (p, name, a, b, k) in enumerate(st["cands"], 1)]
    return "\\n".join(out)


def cand_full(st, why):
    """A refused read answered with one candidate's code (cycling 1, 2, 3 over refusals) + one line for the others."""
    cands, cnt = st["cands"], ranked_spots(st)[2]
    st["refused"] = st.get("refused", 0) + 1
    k = (st["refused"] - 1) % len(cands)
    path, name, a, b, _ = cands[k]
    src = file_lines(path)
    b = min(b, len(src))
    more = ""
    if b - a + 1 > CAND_FULL:
        hot = max(range(a, b + 1), key=lambda i: (cnt.get((path, i), 0), -i))
        s = max(a, min(hot - CAND_FULL // 3, b - CAND_FULL + 1))
        more = f"   (the function runs {a}-{b}; shown {s}-{s + CAND_FULL - 1})"
        a, b = s, s + CAND_FULL - 1
    out = [f">>> READING CLOSED: {why} Instead, here is EDIT CANDIDATE {k + 1}, code you have read. Your next call is "
           f"edit_file here (copy the lines without the numbers) or at another candidate. <<<", f"{k + 1}. {path} {name}:"]
    out += [f"{i:6}| {src[i - 1]}" for i in range(a, b + 1)]
    if more:
        out.append(more)
    out += [f"other candidate {n}: {p} {nm} {s}-{e}" for n, (p, nm, s, e, _) in enumerate(cands, 1) if n != k + 1]
    return "\\n".join(out)


def gate(st, cmd, args):
    """sk_a2p2g3: while reading is closed, find only in read files, outline closed, show only the 3 frozen candidates once."""
    if not closed(st) or cmd not in ("find", "outline", "show") or not args:
        return None
    read_files = sorted({r["file"] for r in st["reads"] if not TEST_RE.search(r["file"])})
    if cmd == "find":
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
    key = spot_of(*rng)
    keys = [c[:4] for c in st["cands"]]
    if key not in keys:  # fix A: only the frozen candidates
        return cand_full(st, "after STOP READING only the 3 EDIT CANDIDATES can be shown again.")
    seen = st.setdefault("reshown", [])
    if key in seen:
        return cand_full(st, f"{key[0]} {key[1]} was already shown again once after STOP READING.")
    seen.append(key)
    n = keys.index(key) + 1
    return cmd_show(st, args) + (f"\\n>>> This is EDIT CANDIDATE {n}. Your next call is edit_file here (copy the lines "
                                 f"without the numbers): it will not be shown again. <<<")


def resume(st):
    """Fix B3: install.py run again keeps the memory and says what the next call is (not a look)."""
    if has_change():
        return ("(the reading tool was already installed: installing again keeps your MEMORY.) Your edit is in the working "
                "tree: run one targeted test or go straight to git status --short and submit_patch.")
    if closed(st):
        return ("(the reading tool was already installed: installing again keeps your MEMORY and the EDIT CANDIDATES above.) "
                "There is no edit yet, and submit_patch with patch_size 0 scores zero. Your next call is edit_file at EDIT "
                "CANDIDATE 1, or show it once first.")
    return ("(the reading tool was already installed: installing again keeps your MEMORY.) There is no edit yet. Your next "
            "call is the edit at the lines in MEMORY that produce the issue's behaviour.")

'''


def sub(t, a, b):
    assert t.count(a) == 1, a[:80]
    return t.replace(a, b)


def g3_apy():
    a = (SRC / "skills/agent/scripts/a.py").read_text()
    assert "def gate(" not in a and "stop_seen" not in a
    a = sub(a, "\n\nHANDLERS = {", GATE + "\nHANDLERS = {")
    a = sub(a, """    st = load()
    if not argv or argv[0].lstrip("-").lower() not in COMMANDS:""", """    st = load()
    if argv[:1] == ["--resume"]:  # sk_a2p2g3 fix B3: called by install.py when the memory already exists
        body = resume(st)
    elif not argv or argv[0].lstrip("-").lower() not in COMMANDS:""")
    a = sub(a, """        try:
            body = HANDLERS[argv[0].lstrip("-").lower()](st, argv[1:])""", """        try:
            cmd = argv[0].lstrip("-").lower()
            body = gate(st, cmd, argv[1:]) or HANDLERS[cmd](st, argv[1:])  # sk_a2p2g3: the late gate""")
    a = sub(a, """    save(st)
    warn = banner(st)
    if warn:
        print(warn)
    print(header(st))
""", """    warn = banner(st)
    if warn.startswith(">>> STOP READING"):
        st["stop_seen"] = True
    freeze(st)  # fixes A + B1: the candidates are fixed once real code was read
    block = cand_block(st) if closed(st) else ""
    save(st)
    if warn:
        print(warn)
    if block:
        print(block)
    print(header(st))
""")
    return a


def g3_install():
    t = (SRC / "skills/agent/scripts/install.py").read_text()
    t = sub(t, "import inspect\n", "import inspect\nimport subprocess\n")
    t = sub(t, """for stale in ("state.json", "state.json.tmp", "repro.py"):
    if os.path.exists(os.path.join(target, stale)):
        os.remove(os.path.join(target, stale))
with open(os.path.join(target, "state.json"), "w") as f:  # the clock for a.py's NO EDIT YET banner starts here
    json.dump({"looks": 0, "reads": [], "notes": [], "pins": [], "t0": time.time()}, f)
""", """kept = False  # sk_a2p2g3 fix B3: installing again in the same task keeps the memory, the clock and the gate
try:
    kept = json.load(open(os.path.join(target, "state.json"))).get("looks", 0) > 0
except (OSError, ValueError, AttributeError):
    kept = False
if not kept:
    for stale in ("state.json", "state.json.tmp", "repro.py"):
        if os.path.exists(os.path.join(target, stale)):
            os.remove(os.path.join(target, stale))
    with open(os.path.join(target, "state.json"), "w") as f:  # the clock for a.py's NO EDIT YET banner starts here
        json.dump({"looks": 0, "reads": [], "notes": [], "pins": [], "t0": time.time()}, f)
""")
    t = t.rstrip("\n") + """
if kept:
    try:
        r = subprocess.run([sys.executable, os.path.join(target, "a.py"), "--resume"], cwd=os.path.dirname(os.path.dirname(target)),
                           capture_output=True, text=True, timeout=30)
        print(r.stdout[-4000:])
    except Exception as e:  # noqa: BLE001  never fail the install
        print(f"(memory kept; a.py --resume failed: {type(e).__name__})")
"""
    return t


def build():
    out = ROOT / "submissions" / NAME
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SRC, out)
    (out / "skills/agent/scripts/a.py").write_text(g3_apy())
    (out / "skills/agent/scripts/install.py").write_text(g3_install())
    p = (ROOT / "scripts/agent_ska2p2g3/system.md").read_text()
    assert "YOUR EDIT" not in p and "a.py check" not in p and "28 tool" in p and "{" not in p and "READING CLOSED" in p
    assert "patch_size 0" in p or '"patch_size": 0' in p
    (out / "prompts/system.md").write_text(p)
    y = (out / "agent.yaml").read_text()
    (out / "agent.yaml").write_text(sub(y, "# sk_a2: mix + the agent's reading tool",
                                        f"# {NAME} (2026-11-24): sk_a2p2g2 + frozen candidates, real-read close, empty-submit example, install keeps memory (scripts/make_ska2p2g3.py). sk_a2 was: mix + the agent's reading tool"))
    print("wrote", out.relative_to(ROOT), len(p.split()), "words")


if __name__ == "__main__":
    build()
