"""sb1 / sb1t / sb1f (user 2026-11-16: plan approved, 'A + B + C + D in sb1, E as sb1t, F as a third agent').
Run: python3 -I scripts/make_sb1.py

sb1 = sa2's agent (one LlmAgent, the six harness tools, T 0.2, thinking 4096, 28 calls, 8 min; configs byte for byte)
with a prompt written fresh (scripts/agent_sb1/system.md). Kept from sa2 (proven): the goal line, KEEP GOING, the four
rules on exact harness messages, the edit shown as plain text blocks. New, each with its basis (docs/PLAN.md NEW AGENT
PLAN sb1 2026-11-16):
  A history: co-changed files + recent commits + `git show --stat` of a sibling commit (HAFixAgent 2511.01047,
    commit-history memory 2510.01003; pre-check: sibling commit at rank 1-2 for 6 of 9 multi-file test tasks, the
    co-change count finds the other real-fix files for 18 of 28 start files; history used in 1 of 162 bank runs);
  B the existing test as the specification (94% of SWE-rebench hidden tests sit in pre-existing test files; SpecRover
    2408.02232; pytest after the last edit 7+/1- same-task);
  C keep existing parameters, new ones last with a default (9 of 78 wrong patches vs 0 of 69 solved changed more def
    signatures than the real fix; peewee_migrate-203);
  D check -> edit -> re-run the same check + one edge case (mini-SWE-agent workflow; SWE-Doctor 2607.00990; same-task
    9+/0- with a reverse-causation caveat).
Every example is plain text (no call syntax, no escapes; memory agent-design-rules, sa1's 22/24 garbles); shell text
uses single quotes (vLLM's Gemma 4 parser truncates arguments at double quotes, RESEARCH_PROBLEMS row 1).
sb1t = sb1 with thinking_budget 2048 (configs/sampling.yaml only). sb1f = sb1 with Google's Gemma 4 sampling
(temperature 1.0, top_p 0.95, top_k 64; configs/sampling.yaml only)."""
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / "submissions"
PARENT = SUB / "sa2"
TOOLS = ["run_command", "read_file", "edit_file", "write_file", "get_status", "submit_patch"]
HEAD = {
    "sb1": "# sb1 (2026-11-16): sa2's agent, prompt written fresh: repo history, existing test as the spec, keep signatures, re-run the check (scripts/make_sb1.py)\n",
    "sb1t": "# sb1t (2026-11-16): sb1 with thinking_budget 2048 (scripts/make_sb1.py)\n",
    "sb1f": "# sb1f (2026-11-16): sb1 with Google's Gemma 4 sampling T 1.0 / top_p 0.95 / top_k 64 (scripts/make_sb1.py)\n",
}


def check_prompt(p):
    low = p.lower()
    assert "budget" not in low.replace("tool call budget exhausted", ""), "no budget wording except the harness message"
    assert "minute" not in low and not re.search(r"\b\d+\s*(tool\s*)?calls?\b|\bby call\b|\bcall \d+", low), "no call / time numbers"
    for msg in ("mandatory input parameters are not present", "old_string not found", "Path traversal detected",
                "Tool call budget exhausted", "# EXAMPLES", "Example 1", "Example 2", "Example 3", "Example 4"):
        assert msg in p, msg
    ex = p[p.index("# EXAMPLES"):]
    assert "\\n" not in ex and '\\"' not in ex and "\\'" not in ex, "no escapes in the examples"
    assert not re.search(r"\b(run_command|edit_file|read_file|submit_patch|write_file)\(", p), "no call syntax anywhere"
    for block in re.findall(r"```\n(.*?)```", ex, re.S):
        if block.lstrip().startswith(("git ", "python3")):
            assert '"' not in block, "shell text in examples uses single quotes"
    # ADK instruction templating replaces {identifier}; nothing like that may appear
    assert not re.search(r"\{[A-Za-z_][\w.]*\??\}", p), "no {name} placeholders"
    for need in ("--full-diff", "git show --stat", "-- '*test*'", "keeps its parameters", "same command runs again"):
        assert need in p, need
    assert "search_similar_code" not in p and "get_code_" not in p


def build(name, prompt):
    out = SUB / name
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(PARENT, out, ignore=shutil.ignore_patterns("__pycache__"))
    first, rest = (PARENT / "agent.yaml").read_text().split("\n", 1)
    assert first.startswith("# sa2 (2026-11-16)")
    (out / "agent.yaml").write_text(HEAD[name] + rest)
    (out / "prompts/system.md").write_text(prompt)
    samp = (PARENT / "configs/sampling.yaml").read_text()
    if name == "sb1t":
        assert samp.count("thinking_budget: 4096") == 1
        samp = samp.replace("thinking_budget: 4096", "thinking_budget: 2048")
    if name == "sb1f":
        assert samp.startswith("temperature: 0.2\ntop_p: 0.95\n")
        samp = samp.replace("temperature: 0.2\ntop_p: 0.95\n", "temperature: 1.0\ntop_p: 0.95\ntop_k: 64\n")
    (out / "configs/sampling.yaml").write_text(samp)
    files = lambda d: sorted(q.relative_to(d).as_posix() for q in d.rglob("*") if q.is_file())
    assert files(out) == files(PARENT)
    assert (out / "eval_config.yaml").read_bytes() == (PARENT / "eval_config.yaml").read_bytes()
    if name == "sb1":
        assert (out / "configs/sampling.yaml").read_bytes() == (PARENT / "configs/sampling.yaml").read_bytes()
    declared = re.findall(r"^\s+- (\w+)\s*$", (out / "agent.yaml").read_text(), re.M)
    assert declared == TOOLS, declared
    assert not (out / "skills").exists()
    return out


def main():
    p = (ROOT / "scripts/agent_sb1/system.md").read_text()
    check_prompt(p)
    for name in ("sb1", "sb1t", "sb1f"):
        out = build(name, p)
        diff = [l for l in (out / "configs/sampling.yaml").read_text().splitlines()
                if l not in (PARENT / "configs/sampling.yaml").read_text().splitlines()]
        print("wrote", out.relative_to(ROOT), "| sampling changes:", diff or "none")
    print("prompt words", len(p.split()), "(sa2: 641)")


if __name__ == "__main__":
    main()
