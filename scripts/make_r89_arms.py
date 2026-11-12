"""r89 arm evidc_g (user 2026-11-12 "lets go with 1": Google's recommended Gemma 4 sampling, the cheapest untested lead in
docs/RESEARCH_PROBLEMS_2026-11-12.md). Run: python3 scripts/make_r89_arms.py

Google's defaults for Gemma 4 are temperature 1.0, top_p 0.95, top_k 64, no penalties (Unsloth's guide and vLLM's Gemma 4
recipe); every agent we built samples the fixer at temperature 0.2 (top_p 0.95, no top_k). Our only evidence is a
single-step replay (r53: at the first-edit decision of pub024 contexts, T 1.0 put edits on the real lines 20% vs 27% and
kept looking 51% vs 29%); a whole-run A/B on the current agent never ran.

  evidc_g = evidc with the FIXER's configs/sampling.yaml at temperature 1.0, top_p 0.95, top_k 64 (max output 8192 and
            thinking 4096 unchanged). The evidence stage keeps its own configs/evidence_sampling.yaml (thinking off,
            T 0.2). Everything else is evidc's bundle byte for byte (asserted)."""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / "submissions"
PARENT, OUT = SUB / "evidc", SUB / "evidc_g"
SAMPLING_REL = "configs/sampling.yaml"
OLD = "temperature: 0.2\ntop_p: 0.95\nmax_output_tokens: 8192\n"
NEW = "# r89 evidc_g: Google's recommended Gemma 4 sampling for the fixer (temperature 1.0, top_p 0.95, top_k 64)\ntemperature: 1.0\ntop_p: 0.95\ntop_k: 64\nmax_output_tokens: 8192\n"
COMMENT = "# evidc_g (r89): evidc with Google's recommended Gemma 4 sampling for the fixer (T 1.0, top_p 0.95, top_k 64) (scripts/make_r89_arms.py)\n"


def files(d):
    return sorted(p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file() and "__pycache__" not in p.parts)


if OUT.exists():
    shutil.rmtree(OUT)
shutil.copytree(PARENT, OUT, ignore=shutil.ignore_patterns("__pycache__"))
s = (PARENT / SAMPLING_REL).read_text()
assert s.count(OLD) == 1
(OUT / SAMPLING_REL).write_text(s.replace(OLD, NEW))
first, rest = (PARENT / "agent.yaml").read_text().split("\n", 1)
assert first.startswith("# evidc (r76)")
(OUT / "agent.yaml").write_text(COMMENT + rest)
assert files(OUT) == files(PARENT)
for f in files(PARENT):
    if f not in (SAMPLING_REL, "agent.yaml"):
        assert (OUT / f).read_bytes() == (PARENT / f).read_bytes(), f
assert "configs/sampling.yaml" in (OUT / "fixer.yaml").read_text() and "configs/evidence_sampling.yaml" in (OUT / "evidence.yaml").read_text()
print("wrote", OUT.relative_to(ROOT), "|", (OUT / SAMPLING_REL).read_text())
