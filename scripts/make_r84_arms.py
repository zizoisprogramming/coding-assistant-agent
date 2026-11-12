"""r84 arms (user 2026-11-12 "yes please and add any idea or arm that even has a slight chance of winning, all in"):
evidefs + one location aid each. Run: python3 scripts/make_r84_arms.py

Why (docs/PLAN.md MINING 2026-11-12d): within the right file, failed runs often edit the wrong place. Same task, solved vs
failed: edit on the real-fix lines 89% vs 49% (11 vs 0 tasks), real-fix lines read before editing 92% vs 64%; off-target
failed runs never read those lines in 41%; worse past line 150 of a file. Research: hierarchical / graph localization
(ARISE +17 function recall@1, +4.7 Pass@1 with a 32B open model) and runtime evidence (SWE-Doctor +8-9 points).

  evmap    evidefs + the evidence script's MAP (the file using the issue's names most; its defs using them with line
           ranges, most uses first). Script-only change: every prompt is evidefs's.
  evtrace  evidefs + the code-path tool (.git/agent/trace.py, installed by the evidence script) + a fixer prompt written
           fresh around finding the place (scripts/agent_trace/fixer_trace.md; no budget numbers, worked example).
  evall    both.
Everything else is evidefs's bundle byte for byte (asserted)."""
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / "submissions"
PARENT = SUB / "evidefs"
SCRIPT = ROOT / "scripts/agent_evidence/evidence_r84.py"
TRACE = ROOT / "scripts/agent_trace/trace.py"
PROMPT = ROOT / "scripts/agent_trace/fixer_trace.md"
SCRIPT_REL, PROMPT_REL = "skills/evidence/scripts/evidence.py", "prompts/fixer.md"
ARMS = {
    "evmap": dict(MAP=True, TRACE=False, prompt=False,
                  comment="# evmap (r84): evidefs + the evidence script's MAP of the file using the issue's names most (scripts/make_r84_arms.py)\n"),
    "evtrace": dict(MAP=False, TRACE=True, prompt=True,
                    comment="# evtrace (r84): evidefs + the code-path tool .git/agent/trace.py + a fixer prompt written around finding the place (scripts/make_r84_arms.py)\n"),
    "evall": dict(MAP=True, TRACE=True, prompt=True,
                  comment="# evall (r84): evidefs + MAP + the code-path tool + the place-finding fixer prompt (scripts/make_r84_arms.py)\n"),
}


def files(d):
    return sorted(p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file() and "__pycache__" not in p.parts)


def script(map_on, trace_on):
    s = SCRIPT.read_text()
    s, a = re.subn(r"^MAP = \S+", f"MAP = {map_on!r}", s, flags=re.M)
    s, b = re.subn(r"^TRACE = \S+", f"TRACE = {trace_on!r}", s, flags=re.M)
    src = TRACE.read_text() if trace_on else ""
    s, c = re.subn(r"^TRACE_SOURCE = ''", lambda m: "TRACE_SOURCE = " + repr(src), s, count=1, flags=re.M)
    assert a == b == c == 1
    return s


def check_prompt(p):
    assert "{evidence?}" in p and "trace.py" in p and "== CODE PATH" in p
    low = p.lower()
    assert "budget" not in low and "minute" not in low, "no budget words in prompts (user rule 2026-11-10)"
    assert not re.search(r"\b\d+\s*(tool\s*)?calls?\b|\bby call\b|\bcall\s+\d+", low), "no call counts or call plans"


def build(name, cfg):
    out = SUB / name
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(PARENT, out, ignore=shutil.ignore_patterns("__pycache__"))
    (out / SCRIPT_REL).write_text(script(cfg["MAP"], cfg["TRACE"]))
    if cfg["prompt"]:
        p = PROMPT.read_text()
        check_prompt(p)
        (out / PROMPT_REL).write_text(p)
    first, rest = (PARENT / "agent.yaml").read_text().split("\n", 1)
    assert first.startswith("# evidefs (r82)")
    (out / "agent.yaml").write_text(cfg["comment"] + rest)
    assert files(out) == files(PARENT)
    changed = {SCRIPT_REL, "agent.yaml"} | ({PROMPT_REL} if cfg["prompt"] else set())
    for f in files(PARENT):
        if f not in changed:
            assert (out / f).read_bytes() == (PARENT / f).read_bytes(), f
    s = (out / SCRIPT_REL).read_text()
    assert f"MAP = {cfg['MAP']!r}" in s and f"TRACE = {cfg['TRACE']!r}" in s and "SOURCE_LINES = True" in s and "ONCE = True" in s
    assert ("def report(exc)" in s) == cfg["TRACE"]  # the embedded tool is there only when installed
    compile(s, SCRIPT_REL, "exec")
    return out


if __name__ == "__main__":
    for name, cfg in ARMS.items():
        o = build(name, cfg)
        print("wrote", o.relative_to(ROOT), "|", files(o))
