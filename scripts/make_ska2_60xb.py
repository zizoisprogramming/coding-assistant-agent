"""sk_a2_60xb = sk_a2_60x2 + an a.py read block after STOP READING (docs/PLAN.md 'PLAN (not built) 2026-11-23: a.py read block after
STOP READING'; user 2026-11-23: 'build it, K=4, 8 tasks on both notebooks'). Offline check (scripts/mine_bank/stop_block_check.py):
86% of failed runs that hit STOP READING before any edit had already been shown the real-fix lines, and they read 6.8 more calls
(solved runs 3.8); with K = 4 reads still allowed after the STOP, 7 of 35 solved runs read past the limit vs 43 target failed runs.
a.py option 'block' (commands.txt): when STOP READING is first printed, the look count is stored (stop_looks); once looks >= stop_looks + K
and the working tree has no change, find / outline / show answer READING CLOSED with the code the agent showed last (at most 40 numbered
lines: the edit material, so a refused read is still useful; the old empty refusal 'NOT SHOWN AGAIN' cost 2-3 calls per run) and do not
count as looks. Reading reopens as soon as the working tree has a change (LOOK AGAIN step). RUN scripts are not blocked; cat / grep /
getsource reads cannot be (no environment tampering) and are measured. Prompt (scripts/agent_ska2xb/system.md, written in full): Example 3
is now the READING CLOSED event. Tools, sampling, eval_config = sk_a2_60x2. Run: python3 -I scripts/make_ska2_60xb.py"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC, OUT = ROOT / "submissions/sk_a2_60x2", ROOT / "submissions/sk_a2_60xb"
K = 4

CLOSED = '''

def read_closed(st, cmd):
    """sk_a2_60xb: K reads after STOP READING with no change in the working tree -> find / outline / show are closed."""
    if "block" not in OPTS or cmd not in ("find", "outline", "show") or "stop_looks" not in st:
        return None
    if st["looks"] < st["stop_looks"] + BLOCK_AFTER or has_change():
        return None
    st["blocked"] = st.get("blocked", 0) + 1
    lines = [f">>> READING CLOSED: {st['looks']} looks and still no edit, so a.py shows no more code until you edit. Your next call "
             f"is the edit, made from the code below (the last code you read) or from code you read earlier: copy the characters "
             f"without the line numbers into edit_file. Do not read with cat, sed, grep or a script instead. No edit scores zero; an "
             f"imperfect edit can pass, and reading opens again after it. <<<"]
    if st["reads"]:
        r = st["reads"][-1]
        try:
            src = file_lines(r["file"])
            b = min(r["b"], r["a"] + RESHOW_MAX - 1, len(src))
            lines.append(f"last code you read: {r['file']} {r['a']}-{b}")
            lines += [f"{i:6}| {src[i - 1]}" for i in range(r["a"], b + 1)]
        except OSError:
            pass
    return "\\n".join(lines)

'''


def sub(t, a, b):
    assert t.count(a) == 1, a[:80]
    return t.replace(a, b)


def build():
    a = (SRC / "skills/agent/scripts/a.py").read_text()
    a = sub(a, 'OPTIONS = {"banner", "reshow"}', f'OPTIONS = {{"banner", "reshow", "block"}}  # sk_a2_60xb: + block (READING CLOSED {K} looks after STOP READING)\nBLOCK_AFTER = {K}')
    a = sub(a, '        return (f">>> STOP READING: {used}',
            '        st.setdefault("stop_looks", st["looks"])  # sk_a2_60xb: the read block counts from the first STOP READING\n'
            '        return (f">>> STOP READING: {used}')
    a = sub(a, "\n\nHANDLERS = {", CLOSED + "\nHANDLERS = {")
    a = sub(a, """        try:
            body = HANDLERS[argv[0].lstrip("-").lower()](st, argv[1:])
        except Exception as e:  # noqa: BLE001  never crash: the model gets a message and the header
            body = f"(error in {argv[0]}: {type(e).__name__}: {e})"
    save(st)
    warn = banner(st)
""", """        try:
            body = read_closed(st, argv[0].lstrip("-").lower())
            closed = body is not None
            if not closed:
                body = HANDLERS[argv[0].lstrip("-").lower()](st, argv[1:])
        except Exception as e:  # noqa: BLE001  never crash: the model gets a message and the header
            body, closed = f"(error in {argv[0]}: {type(e).__name__}: {e})", False
    warn = "" if (argv and argv[0].lstrip("-").lower() in COMMANDS and closed) else banner(st)
    save(st)
""")
    a = sub(a, "def main(argv):\n    st = load()\n", "def main(argv):\n    st = load()\n    closed = False\n")
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SRC, OUT)
    (OUT / "skills/agent/scripts/a.py").write_text(a)
    c = (SRC / "skills/agent/scripts/commands.txt").read_text().split()
    assert "block" not in c
    (OUT / "skills/agent/scripts/commands.txt").write_text(" ".join(c + ["block"]) + "\n")
    p = (ROOT / "scripts/agent_ska2xb/system.md").read_text()
    for must in ("READING CLOSED", "STOP READING", "Example 3", "Example 4", "old_string not found", "28 tool"):
        assert must in p, must
    (OUT / "prompts/system.md").write_text(p)
    y = (SRC / "agent.yaml").read_text()
    assert y.startswith("# sk_a2_60x2 (2026-11-23)")
    (OUT / "agent.yaml").write_text(f"# sk_a2_60xb (2026-11-23): sk_a2_60x2 + a.py READING CLOSED {K} looks after STOP READING until an edit (scripts/make_ska2_60xb.py). " + y.lstrip("# "))
    print("wrote", OUT.relative_to(ROOT), len(p.split()), "words")


if __name__ == "__main__":
    build()
