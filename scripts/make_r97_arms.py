"""r97 arms evtb, evtb9 (user 2026-11-13 "build that": docs/PLAN.md TIME ECONOMY DESIGN 2026-11-13). Run: python3 -I scripts/make_r97_arms.py

evtb  = evidc with the fixer's thinking_budget 2048 instead of 4096 (configs/sampling.yaml only; the evidence stage's
        configs/evidence_sampling.yaml, thinking off, untouched). Replies > 2,000 tokens are 3.3% of evidc's fixer
        replies but 30% of its model time (12.5% of all output tokens lie above 2,000). Prompts byte for byte evidc's.
evtb9 = evtb with eval_config max_time_minutes 9 (was 8) and max_tool_calls 33 (was 29; 89 of 204 evidc runs used all
        29 calls, so a longer cap needs more calls, 29 x 9/8). Prompts byte for byte evidc's: its HARD LIMITS line still
        says 28 calls and 8 minutes; the harness's task message and budget warnings carry the real 33 / 9."""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / "submissions"
PARENT = SUB / "evidc"
SAMP, EVAL = "configs/sampling.yaml", "eval_config.yaml"


def files(d):
    return sorted(p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file() and "__pycache__" not in p.parts)


def copy(name, comment):
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


def tb(out, note):
    s = (PARENT / SAMP).read_text()
    old = "  thinking_budget: 4096\n"
    assert s.count(old) == 1
    (out / SAMP).write_text(note + s.replace(old, "  thinking_budget: 2048\n", 1))


def build_tb():
    out = copy("evtb", "# evtb (r97): evidc with the fixer's thinking budget 2048 (was 4096); prompts unchanged (scripts/make_r97_arms.py)\n")
    tb(out, "# r97 evtb: thinking budget 2048 (evidc 4096): replies > 2,000 tokens are 3% of replies but 30% of model time\n")
    check(out, [SAMP])
    return out


def build_tb9():
    out = copy("evtb9", "# evtb9 (r97): evtb + 9 minutes and 33 tool calls (evidc 8 / 29): the time thinking 2048 saves, spent on a longer cap (scripts/make_r97_arms.py)\n")
    tb(out, "# r97 evtb9: thinking budget 2048 (evidc 4096)\n")
    e = (PARENT / EVAL).read_text()
    for old, new in (("  max_tool_calls: 29\n", "  max_tool_calls: 33\n"), ("  max_time_minutes: 8\n", "  max_time_minutes: 9\n")):
        assert e.count(old) == 1, old
        e = e.replace(old, new, 1)
    (out / EVAL).write_text("# r97 evtb9: 9 minutes and 33 calls (evidc 8 / 29); thinking 2048 is meant to pay for the extra minute\n" + e)
    check(out, [SAMP, EVAL])
    return out


if __name__ == "__main__":
    for b in (build_tb, build_tb9):
        o = b()
        print("wrote", o.relative_to(ROOT))
