"""sk_a2m = sk_a2 with ONE change: a.py's MEMORY header automatically keeps the last function the agent showed (its first LAST_MAX lines,
read fresh from the file each time, so after an edit it shows the edited code) in every later output - context that survives
compaction without the model having to note or pin anything (sk_a / sk_ad's model-driven note / pin: no patch 44-56%). User 2026-11-21:
'build it in 2 notebooks'. The issue text is not reachable from a.py (it lives only in the agent's prompt), so only the code is kept.
Switched on by the option word 'lastpin' in commands.txt. One prompt line says what the header now holds. Run: python3 -I scripts/make_ska2m.py"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC, OUT = ROOT / "submissions/sk_a2", ROOT / "submissions/sk_a2m"


def sub(t, a, b):
    assert t.count(a) == 1, a[:60]
    return t.replace(a, b)


def build():
    a = (SRC / "skills/agent/scripts/a.py").read_text()
    a = sub(a, 'OPTIONS = {"banner", "reshow"}', 'OPTIONS = {"banner", "reshow", "lastpin"}\nLAST_MAX = 20  # sk_a2m: lines of the last shown function kept in MEMORY')
    a = sub(a, '''    st["looks"] += 1
    st["reads"].append({"file": path, "a": a, "b": b})
    return extra + "\\n".join(f"{i:6}| {src[i - 1]}" for i in range(a, b + 1))''',
              '''    st["looks"] += 1
    st["reads"].append({"file": path, "a": a, "b": b})
    st["last"] = {"file": path, "a": a, "b": min(b, a + LAST_MAX - 1)}  # sk_a2m
    return extra + "\\n".join(f"{i:6}| {src[i - 1]}" for i in range(a, b + 1))''')
    a = sub(a, '''    lines.append("=" * 40)
    return "\\n".join(lines)''', '''    last = st.get("last")
    if "lastpin" in OPTS and last:  # sk_a2m: the last shown function, read fresh (edits show up), survives context trimming
        try:
            src = file_lines(last["file"])
            lines.append(f"last shown, kept here: {last['file']} {last['a']}-{min(last['b'], len(src))}")
            lines += [f"{i:6}| {src[i - 1]}" for i in range(last["a"], min(last["b"], len(src)) + 1)]
        except OSError:
            lines.append(f"last shown: {last['file']} (file gone)")
    lines.append("=" * 40)
    return "\\n".join(lines)''')
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SRC, OUT)
    (OUT / "skills/agent/scripts/a.py").write_text(a)
    c = (SRC / "skills/agent/scripts/commands.txt").read_text().split()
    (OUT / "skills/agent/scripts/commands.txt").write_text(" ".join(c + ["lastpin"]) + "\n")
    p = (SRC / "prompts/system.md").read_text()
    p = sub(p, "Older tool outputs are removed from the conversation as it grows: trust MEMORY instead of reading again.",
            "Older tool outputs are removed from the conversation as it grows: trust MEMORY instead of reading again. MEMORY also\nkeeps the first lines of the last function you showed, as the file is now.")
    (OUT / "prompts/system.md").write_text(p)
    y = (SRC / "agent.yaml").read_text()
    (OUT / "agent.yaml").write_text(sub(y, "# sk_a2: mix + the agent's reading tool", "# sk_a2m (2026-11-21): sk_a2 + MEMORY keeps the last shown function (scripts/make_ska2m.py). sk_a2 was: mix + the agent's reading tool"))
    print("wrote", OUT.relative_to(ROOT))


if __name__ == "__main__":
    build()
