"""r93 arms evidc_nt and evidc_p (user 2026-11-13 "yes build this": docs/PLAN.md NEW IDEAS 2026-11-13). Run: python3 scripts/make_r93_arms.py

evidc_nt = evidc with the fixer's configs/sampling.yaml at include_thoughts: false (thinking_budget 4096 kept). In the
           scorer (adk_submission 0.2.13 resolvers/generation.py) a budget > 0 keeps thinking ON, and include_thoughts
           false removes thought parts from responses before they enter the session and strips reasoning from outgoing
           messages: the model thinks every call, but its past thoughts (27% of context) are never re-sent. The evidence
           stage's own sampling (thinking off) is unchanged. Everything else is evidc's byte for byte (asserted).
evidc_p  = evidc with the evidence script's PAST CHANGES LIKE THIS ONE section first (scripts/agent_evidence/
           evidence_prec.py: BM25 of the last 3,000 first-parent commit subjects against the names' words, the top 3 that
           changed non-test Python files, each with its files (library source first) and the functions it changed) and
           the evidence-stage prompt written fresh (scripts/agent_evidence/evidence_prec.md: copy the related past changes
           first, up to 14 lines instead of 10). The fixer is evidc's byte for byte (asserted)."""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / "submissions"
PARENT = SUB / "evidc"
SAMP, SCRIPT, EVP = "configs/sampling.yaml", "skills/evidence/scripts/evidence.py", "prompts/evidence.md"


def files(d):
    return sorted(p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file() and "__pycache__" not in p.parts)


def copy(name, comment, changed):
    out = SUB / name
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(PARENT, out, ignore=shutil.ignore_patterns("__pycache__"))
    first, rest = (PARENT / "agent.yaml").read_text().split("\n", 1)
    assert first.startswith("# evidc (r76)")
    (out / "agent.yaml").write_text(comment + rest)
    return out


def check(out, changed):
    assert files(out) == files(PARENT)
    for f in files(PARENT):
        if f not in changed + ["agent.yaml"]:
            assert (out / f).read_bytes() == (PARENT / f).read_bytes(), f


def build_nt():
    out = copy("evidc_nt", "# evidc_nt (r93): evidc with the fixer's past thoughts stripped from the history (include_thoughts: false, thinking stays on) (scripts/make_r93_arms.py)\n", [SAMP])
    s = (PARENT / SAMP).read_text()
    old = "  include_thoughts: true\n"
    assert s.count(old) == 1 and "thinking_budget: 4096" in s
    (out / SAMP).write_text("# r93 evidc_nt: thinking stays ON (thinking_budget > 0); include_thoughts false keeps past thoughts out of the history (adk_submission 0.2.13)\n"
                            + s.replace(old, "  include_thoughts: false\n", 1))
    check(out, [SAMP])
    return out


def build_p():
    out = copy("evidc_p", "# evidc_p (r93): evidc + PAST CHANGES LIKE THIS ONE (past commits whose titles share the names, with the files and functions they changed) first in the evidence (scripts/make_r93_arms.py)\n", [SCRIPT, EVP])
    new = (ROOT / "scripts/agent_evidence/evidence_prec.py").read_text()
    old = (PARENT / SCRIPT).read_text()
    it = iter(new.splitlines())
    assert all(any(l == m for m in it) for l in old.splitlines() if not l.startswith('"""')), "every evidc script line kept, in order"
    assert "PRECEDENT = True" in new
    compile(new, SCRIPT, "exec")
    (out / SCRIPT).write_text(new)
    p = (ROOT / "scripts/agent_evidence/evidence_prec.md").read_text()
    assert "{problem_description}" in p and "PAST CHANGES LIKE THIS ONE" in p
    low = p.lower()
    assert "budget" not in low and "minute" not in low
    (out / EVP).write_text(p)
    check(out, [SCRIPT, EVP])
    return out


if __name__ == "__main__":
    for b in (build_nt, build_p):
        o = b()
        print("wrote", o.relative_to(ROOT))
