"""r95 arms evex_f, evex_m, evbrief (user 2026-11-13 "build these yes": docs/PLAN.md NEW DIRECTION 2026-11-13b).
Run: python3 -I scripts/make_r95_arms.py   (after python3 -I scripts/agent_exemplar/build_library.py)

evex_f  = evidc with the evidence script scripts/agent_exemplar/evidence_ex.py in EXAMPLE_MODE "fixed": after the
          evidence, always the same solved example (Instagram/MonkeyType: grep, a 70-line read, a repro, a 5-line logic
          edit, the repro again, the related tests, submit; 9 calls). Prompts and configs evidc's byte for byte.
evex_m  = the same script in EXAMPLE_MODE "matched": the library run (29 of Gemma's own solved runs on non-competition
          repositories, scripts/agent_exemplar/examples.json) sharing the most words with the names the evidence stage
          passed; MonkeyType when none is shared. Prompts and configs evidc's byte for byte.
evbrief = evidc with the fixer prompt written fresh (scripts/agent_exemplar/fixer_brief.md): HOW TO THINK (a sentence or
          two before routine calls, careful thinking when choosing the edit and after a failing test; Google's Gemma 4
          prompt-formatting guide: reasoning depth is set by system instructions), no budget numbers and no numbered
          call plan (memory rules; r87 showed removing the plan's numbers alone changed nothing, 3/8 vs 3/8)."""
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / "submissions"
PARENT = SUB / "evidc"
SCRIPT, FIXER = "skills/evidence/scripts/evidence.py", "prompts/fixer.md"
SRC = ROOT / "scripts/agent_exemplar"
FIXED_REPO = "Instagram/MonkeyType"


def files(d):
    return sorted(p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file() and "__pycache__" not in p.parts)


def render_script(mode, examples):
    src = (SRC / "evidence_ex.py").read_text()
    for old, new in (('EXAMPLE_MODE = "matched"', f'EXAMPLE_MODE = "{mode}"'),
                     ("EXAMPLES = []", "EXAMPLES = " + json.dumps(
                         [{k: e[k] for k in ("repo", "calls", "text", "words")} for e in examples], ensure_ascii=True))):
        assert src.count(old) == 1, old
        src = src.replace(old, new, 1)
    compile(src, SCRIPT, "exec")
    return src


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


def kept_lines():
    """every line of evidc's script except its docstring is in evidence_ex.py, in order"""
    old, new = (PARENT / SCRIPT).read_text(), (SRC / "evidence_ex.py").read_text()
    old_code = old[old.index('"""', 3) + 3:]
    it = iter(new.splitlines())
    assert all(any(l == m for m in it) for l in old_code.splitlines()), "every evidc script line kept, in order"


def build_ex(name, mode, examples, comment):
    out = copy(name, comment)
    (out / SCRIPT).write_text(render_script(mode, examples))
    check(out, [SCRIPT])
    return out


def build_brief():
    out = copy("evbrief", "# evbrief (r95): evidc with the fixer prompt written fresh: think briefly before routine calls, carefully when choosing the edit and after a failing test; no budget numbers (scripts/make_r95_arms.py)\n")
    p = (SRC / "fixer_brief.md").read_text()
    low = p.lower()
    assert "{evidence?}" in p and p.rstrip().endswith("{evidence?}")
    assert "budget" not in low and "minute" not in low and not re.search(r"\b\d+\s*(tool\s*)?calls?\b|\bby call\b|\bcall \d+", low)
    assert "# HOW TO THINK" in p
    (out / FIXER).write_text(p)
    check(out, [FIXER])
    return out


if __name__ == "__main__":
    kept_lines()
    lib = json.load(open(SRC / "examples.json"))
    fixed = [e for e in lib if e["repo"] == FIXED_REPO]
    assert len(fixed) == 1 and len(lib) >= 20, (len(fixed), len(lib))
    assert not any(e["repo"].split("/")[-1].lower() in ("fastapi", "rich", "requests", "httpx") for e in lib)
    for o in (build_ex("evex_f", "fixed", fixed, "# evex_f (r95): evidc + one fixed solved example (Gemma's own run on Instagram/MonkeyType) after the evidence in the evidence script's result (scripts/make_r95_arms.py)\n"),
              build_ex("evex_m", "matched", lib, f"# evex_m (r95): evidc + the most similar of {len(lib)} solved examples (Gemma's own runs on non-competition repositories) after the evidence in the evidence script's result (scripts/make_r95_arms.py)\n"),
              build_brief()):
        print("wrote", o.relative_to(ROOT), "|", sum((o / f).stat().st_size for f in files(o)), "bytes")
