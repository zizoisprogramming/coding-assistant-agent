"""sa3 (user 2026-11-16 "build sa3 while they run"): sa2 + Example 4 (finishing a change across files). Run after make_sa2.py:
    python3 -I scripts/make_sa3.py
Basis (TEST-SET FAILURE ANATOMY 2026-11-16, scripts/mine_bank/rtest_failures.py): on the 24 SWE-rebench test tasks pub024
solves 57% of tasks whose real fix is one source file but 11% (2/18) of those needing 2+ files; most patches there touch
1 of 2 real-fix files; the most-missed file is the package __init__.py (exports), then sibling modules. pub024 / sa2
already state the rule in words ("registration ... __init__.py", "parallel versions"); a worked example is the
few-shot form (user rule: few-shot always, aimed at the agent's own measured mistakes), in the plain-text call format
that fixed sa1's garbling (r101). Everything else is sa2's byte for byte (asserted)."""
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / "submissions"
PARENT, OUT = SUB / "sa2", SUB / "sa3"


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(PARENT, OUT, ignore=shutil.ignore_patterns("__pycache__"))
    first, rest = (PARENT / "agent.yaml").read_text().split("\n", 1)
    assert first.startswith("# sa2 (2026-11-16)")
    (OUT / "agent.yaml").write_text("# sa3 (2026-11-16): sa2 + Example 4, finishing a change across files (exports in __init__.py, callers) (scripts/make_sa3.py)\n" + rest)
    old = (PARENT / "prompts/system.md").read_text()
    new = (ROOT / "scripts/agent_sa1/system_sa3.md").read_text()
    assert new.startswith(old.rstrip()) and "Example 4 - " in new[len(old.rstrip()):], "sa2's prompt + Example 4 only"
    ex4 = new[new.index("Example 4 - "):]
    assert "edit_file(" not in ex4 and '\\"' not in ex4 and "\\n" not in ex4, "plain-text call format"
    low = new.lower()
    assert "minute" not in low and not re.search(r"\b\d+\s*(tool\s*)?calls?\b|\bby call\b|\bcall \d+", low)
    (OUT / "prompts/system.md").write_text(new)
    files = lambda d: sorted(q.relative_to(d).as_posix() for q in d.rglob("*") if q.is_file())
    assert files(OUT) == files(PARENT)
    for f in ("configs/sampling.yaml", "eval_config.yaml"):
        assert (OUT / f).read_bytes() == (PARENT / f).read_bytes(), f
    print("wrote", OUT.relative_to(ROOT), "| prompt words", len(new.split()))


if __name__ == "__main__":
    main()
