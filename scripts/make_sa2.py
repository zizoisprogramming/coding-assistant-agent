"""sa2 (user 2026-11-16 "do it"): sa1 with ONLY Example 2 rewritten. Run: python3 -I scripts/make_sa1.py && python3 -I scripts/make_sa2.py

Basis (RESULT r99 + r100): sa1's Example 2 showed edit_file as a Python-style call with escaped strings; sa1 garbled its
edit calls in 22 of 24 runs (135 calls, ~75 s/run) vs pub024 3 of 24, the parser splitting arguments at quotes inside the
code. sa2 shows the same edit as plain text blocks (argument name, then the exact lines with real line breaks, no escapes,
no call syntax). Example 1 (heredoc python: inline python broken 0 vs 4 runs) and Example 3 unchanged; everything else is
sa1's byte for byte (asserted)."""
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / "submissions"
PARENT, OUT = SUB / "sa1", SUB / "sa2"


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(PARENT, OUT, ignore=shutil.ignore_patterns("__pycache__"))
    first, rest = (PARENT / "agent.yaml").read_text().split("\n", 1)
    assert first.startswith("# sa1 (2026-11-15)")
    (OUT / "agent.yaml").write_text("# sa2 (2026-11-16): sa1 with Example 2 (the edit) shown as plain text blocks instead of an escaped Python-style call (scripts/make_sa2.py)\n" + rest)
    old = (PARENT / "prompts/system.md").read_text()
    new = (ROOT / "scripts/agent_sa1/system_sa2.md").read_text()
    cut = lambda s: (s[:s.index("Example 2 - ")], s[s.index("Example 3 - "):])
    assert cut(old) == cut(new), "only Example 2 differs"
    ex2 = new[new.index("Example 2 - "):new.index("Example 3 - ")]
    assert "edit_file(" not in ex2 and '\\"' not in ex2 and "\\n" not in ex2, "no call syntax or escapes in Example 2"
    low = new.lower()
    assert "minute" not in low and not re.search(r"\b\d+\s*(tool\s*)?calls?\b|\bby call\b|\bcall \d+", low)
    (OUT / "prompts/system.md").write_text(new)
    files = lambda d: sorted(q.relative_to(d).as_posix() for q in d.rglob("*") if q.is_file())
    assert files(OUT) == files(PARENT)
    for f in ("configs/sampling.yaml", "eval_config.yaml"):
        assert (OUT / f).read_bytes() == (PARENT / f).read_bytes(), f
    assert re.findall(r"^\s+- (\w+)\s*$", (OUT / "agent.yaml").read_text(), re.M) == re.findall(r"^\s+- (\w+)\s*$", (PARENT / "agent.yaml").read_text(), re.M)
    print("wrote", OUT.relative_to(ROOT), "| prompt words", len(new.split()))


if __name__ == "__main__":
    main()
