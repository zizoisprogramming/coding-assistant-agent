"""evidh (r83, user 2026-11-12 "build"): evidefs + a 'changed recently' section in the evidence script.
Run: python3 scripts/make_evidh.py

Why (docs/PLAN.md MINING 2026-11-12b): the information test showed the missing piece is what the issue's reporter knew;
git history holds part of it when the buggy code is new. git blame of the lines real fixes change (109 public tasks,
scripts/mine_bank/fix_line_age.py): written within 50 commits of the base in 22%, within 300 in 52%. evidefs's script
finds commits by name (git log -S: commits that added or removed the name), not the newest change to the code itself.
evidence_r83.py adds, per name, the newest commit within the last 300 that wrote some of the name's def / class body
(or the source lines using it): hash, date, commits before this checkout, message, up to 4 lines it wrote.

Everything else is evidefs's bundle byte for byte (asserted): no prompt is written or changed, so the evidence stage's
prompt, the fixer prompt (evidcfs's few-shot fixer) and all configs are the ones evidefs runs on the LB."""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / "submissions"
PARENT, OUT = SUB / "evidefs", SUB / "evidh"
SCRIPT = ROOT / "scripts/agent_evidence/evidence_r83.py"
SCRIPT_REL = "skills/evidence/scripts/evidence.py"
COMMENT = "# evidh (r83): evidefs + the evidence script's 'changed recently' section (newest commit in the last 300 that wrote each name's code) (scripts/make_evidh.py)\n"


def files(d):
    return sorted(p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file() and "__pycache__" not in p.parts)


if OUT.exists():
    shutil.rmtree(OUT)
shutil.copytree(PARENT, OUT, ignore=shutil.ignore_patterns("__pycache__"))
(OUT / SCRIPT_REL).write_text(SCRIPT.read_text())
first, rest = (PARENT / "agent.yaml").read_text().split("\n", 1)
assert first.startswith("# evidefs (r82)")
(OUT / "agent.yaml").write_text(COMMENT + rest)

assert files(OUT) == files(PARENT)
for f in files(PARENT):
    if f == SCRIPT_REL:
        assert (OUT / f).read_text() == SCRIPT.read_text()
    elif f == "agent.yaml":
        assert (OUT / f).read_text().split("\n", 1)[1] == rest
    else:
        assert (OUT / f).read_bytes() == (PARENT / f).read_bytes(), f
s = (OUT / SCRIPT_REL).read_text()
assert "RECENT = 300" in s and "SOURCE_LINES = True" in s and "ONCE = True" in s and "DEADLINE = 8" in s
print("wrote", OUT.relative_to(ROOT), "|", files(OUT))
