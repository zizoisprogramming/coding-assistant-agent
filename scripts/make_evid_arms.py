"""r79 (user 2026-11-11 "now lets continue building"; agenda from the 2026-11-11 checkpoint: mine the evidence stage's empty
cases, build a richer evidence stage, small first trial vs evidc). Run: python3 scripts/make_evid_arms.py

Mining (scripts/mine_bank/evidence_reads.py, 106 evidence-stage runs of evid3 / evid4 / evidc on dev16):
  - evidc's r76 speed-up limited git log -S to the last 500 commits. That cut the "what X changed around it" block in 5 of
    the 16 dev16 tasks (evidc 16/40 runs have it, evid3 37/44). On fastapi_14419 and fastapi_15589 (two of the four
    mid-rate tasks) evidc's output never reached the gold file (0/8 runs) where evid3's did (8/8); all 4 of evidc's
    NOTHING RELEVANT replies on 15589 follow from it. The whole history costs 0.2-0.6 s on the local snapshots
    (4,300-7,200 commits; evid3 ran 0-3 s on Kaggle), so the limit bought nothing.
  - 74 of 174 per-name searches found no def / class line: parameters and options (convert_underscores, scopes,
    on_startup) have none, so nothing showed where the source uses them.
  - 17 of 177 chosen names were dotted (Segment.split_cells) or phrases (validation errors): def and history searches
    cannot match them.
  - The fixer sees the script's full output in its history from its first request (16/16 runs) until compaction drops it
    (kept in ~60% of its requests), plus the copied lines in its system prompt for the whole run: a better script output
    reaches the fixer whatever the stage copies.

Arms (everything except the script is evidc's, byte for byte; asserted below):
  evidd  evidc + scripts/agent_evidence/evidence_r79.py: git log -S over the whole history (a git call that runs out of
         time keeps what it printed), dotted names reduced to their specific last part, foo() -> foo, phrases dropped
         when a real name is left.
  evide  evidd + SOURCE_LINES: a name with no def / class line gets up to 4 non-test, non-docs source lines that use it.
The fixer prompt is evidc's (combo1's byte for byte + the evidence section): no prompt is written or changed in r79.
"""
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / "submissions"
SCRIPT = ROOT / "scripts/agent_evidence/evidence_r79.py"
EVIDC = SUB / "evidc"
SCRIPT_REL = "skills/evidence/scripts/evidence.py"
COMMENT = {
    "evidd": "# evidd (r79): evidc + the evidence script searching the whole git history (no 500-commit limit; a slow git call keeps what it printed) and cleaning names (Segment.split_cells -> split_cells) (scripts/make_evid_arms.py)\n",
    "evide": "# evide (r79): evidd + source lines for names with no def / class line (parameters, options) (scripts/make_evid_arms.py)\n",
}


def script(source_lines):
    s = SCRIPT.read_text()
    s, n = re.subn(r"^SOURCE_LINES = \S+", f"SOURCE_LINES = {source_lines!r}", s, flags=re.M)
    assert n == 1
    return s


def build(name, source_lines):
    out = SUB / name
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(EVIDC, out)
    (out / SCRIPT_REL).write_text(script(source_lines))
    agent = (EVIDC / "agent.yaml").read_text()
    first, rest = agent.split("\n", 1)
    assert first.startswith("# evidc (r76)")
    (out / "agent.yaml").write_text(COMMENT[name] + rest)
    # only the script and the agent.yaml comment differ from evidc
    a = sorted(p.relative_to(EVIDC).as_posix() for p in EVIDC.rglob("*") if p.is_file())
    b = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    assert a == b, (a, b)
    for rel in a:
        if rel not in (SCRIPT_REL, "agent.yaml"):
            assert (EVIDC / rel).read_bytes() == (out / rel).read_bytes(), rel
    assert (out / "agent.yaml").read_text().split("\n", 1)[1] == agent.split("\n", 1)[1]
    assert ("SOURCE_LINES = True" in (out / SCRIPT_REL).read_text()) == source_lines
    return out


if __name__ == "__main__":
    for name, src in (("evidd", False), ("evide", True)):
        o = build(name, src)
        print("wrote", o.relative_to(ROOT), "|", sorted(p.relative_to(o).as_posix() for p in o.rglob("*") if p.is_file()))
