"""evidefs (user 2026-11-11 after r81's two passes: "add the fix since we know it doesn't harm but may help, so be it"):
evide + evidcfs's fixer prompt. Run: python3 scripts/make_evidefs.py

The two parents change different files of evidc, so they combine without writing anything new:
  evide    = evidc + the r79 evidence script (whole git history, cleaned names, source lines for names with no def / class)
  evidcfs  = evidc + the r81 fixer prompt (examples of correct call forms, heredoc checks, no budget numbers, ORDER OF WORK)
  evidefs  = evide's bundle with evidcfs's prompts/fixer.md (and its own agent.yaml comment)
r81 (2 passes, 4 picked tasks): the fs prompt over 4 agents 18/32 vs 11/32 (bank model P(helps) 0.80, ~+3 points on
dev16), +23.5 s per run; evide passed r79 / r80 (8/20 = evidc, -20 s).
Asserted below: every file is evide's byte for byte except prompts/fixer.md (= evidcfs's) and the agent.yaml comment line.
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / "submissions"
EVIDE, EVIDCFS, EVIDC, OUT = SUB / "evide", SUB / "evidcfs", SUB / "evidc", SUB / "evidefs"
PROMPT = "prompts/fixer.md"
COMMENT = "# evidefs (r82): evide + evidcfs's fixer prompt (few-shot call forms, heredoc checks, no budget numbers) (scripts/make_evidefs.py)\n"


def files(d):
    return sorted(p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file() and "__pycache__" not in p.parts)


# the parents differ from evidc exactly where expected, so their changes do not overlap
for parent, changed in ((EVIDE, {"agent.yaml", "skills/evidence/scripts/evidence.py"}), (EVIDCFS, {"agent.yaml", PROMPT})):
    assert files(parent) == files(EVIDC), parent
    diff = {f for f in files(EVIDC) if (EVIDC / f).read_bytes() != (parent / f).read_bytes()}
    assert diff == changed, (parent.name, diff)

if OUT.exists():
    shutil.rmtree(OUT)
shutil.copytree(EVIDE, OUT, ignore=shutil.ignore_patterns("__pycache__"))
(OUT / PROMPT).write_bytes((EVIDCFS / PROMPT).read_bytes())
first, rest = (EVIDE / "agent.yaml").read_text().split("\n", 1)
assert first.startswith("# evide (r79)")
(OUT / "agent.yaml").write_text(COMMENT + rest)

assert files(OUT) == files(EVIDE)
for f in files(EVIDE):
    if f == PROMPT:
        assert (OUT / f).read_bytes() == (EVIDCFS / f).read_bytes()
    elif f == "agent.yaml":
        assert (OUT / f).read_text().split("\n", 1)[1] == rest
    else:
        assert (OUT / f).read_bytes() == (EVIDE / f).read_bytes(), f
p = (OUT / PROMPT).read_text()
assert "EXAMPLES OF CORRECT CALLS" in p and "28 tool calls" not in p and "{evidence?}" in p
assert "SOURCE_LINES = True" in (OUT / "skills/evidence/scripts/evidence.py").read_text()
print("wrote", OUT.relative_to(ROOT), "|", files(OUT))
