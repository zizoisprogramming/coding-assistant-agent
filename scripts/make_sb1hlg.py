"""sb1hlg = sb1hl with Google's recommended Gemma sampling (temperature 1.0, top_p 0.95, top_k 64; r89's evidc_g format), everything
else byte for byte sb1hl (user 2026-11-20: 'give it first then build the trial'; basis docs/PLAN.md OPTION 2 STUDY: never-edit
runs burn one maxed thinking reply, often a hand-simulation loop; r89: maxed replies in 2/12 runs at T 1.0 vs 5/12 at T 0.2).
Run: python3 -I scripts/make_sb1hlg.py"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / "submissions"
src, out = SUB / "sb1hl", SUB / "sb1hlg"
SAMPLING = """# sb1hlg: Google's recommended Gemma 4 sampling (temperature 1.0, top_p 0.95, top_k 64), as r89's evidc_g fixer
temperature: 1.0
top_p: 0.95
top_k: 64
max_output_tokens: 8192
thinking_config:
  thinking_budget: 4096
  include_thoughts: true
"""
old = (src / "configs/sampling.yaml").read_text()
assert old == "temperature: 0.2\ntop_p: 0.95\nmax_output_tokens: 8192\nthinking_config:\n  thinking_budget: 4096\n  include_thoughts: true\n", old
if out.exists():
    shutil.rmtree(out)
shutil.copytree(src, out)
(out / "configs/sampling.yaml").write_text(SAMPLING)
first, rest = (src / "agent.yaml").read_text().split("\n", 1)
(out / "agent.yaml").write_text("# sb1hlg (2026-11-20): sb1hl with temperature 1.0 / top_p 0.95 / top_k 64 (scripts/make_sb1hlg.py)\n" + rest)
files = lambda d: sorted(q.relative_to(d).as_posix() for q in d.rglob("*") if q.is_file())
assert files(out) == files(src)
for f in files(src):
    if f not in ("agent.yaml", "configs/sampling.yaml"):
        assert (out / f).read_bytes() == (src / f).read_bytes(), f
print("wrote", out.relative_to(ROOT), "| differs from sb1hl only in agent.yaml line 1 and configs/sampling.yaml")
