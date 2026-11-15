"""sa1 (user 2026-11-15 "build it"; docs/PLAN.md SA1 DESIGN): pub024's shape with a prompt written fresh from evidence.
Run: python3 -I scripts/make_sa1.py

Rules (memory agent-design-rules, 2026-11-15): only the harness's own tools; few-shot examples always; every element has a
basis. Same as pub024 (LB 11/58): one LlmAgent, temperature 0.2 / top_p 0.95 / thinking 4096 / max_output 8192, 28 calls,
8 minutes, 240 s command timeout, 80 turns. Differences: the prompt (scripts/agent_sa1/system.md, 621 words vs 1,157) and
the three graph tools no longer declared (pub024 declared them and told the model never to use them; combo1 dropped them).
Prompt elements and their basis (PROMPT REVIEW 2026-11-15, SA1 DESIGN): goal first (pub024 wording; IFScale: earlier
instructions get more attention); keep-going reminder (OpenAI GPT-4.1 guide; bank: unedited runs score 0, 10% junk replies
on other repos); positive procedure (negative constraints suppress weakly, arXiv 2601.08070; combo1's how-to cut /tmp
writes 13.3% -> 1.3%); four rules tied to exact harness messages (garble rule halved garbled edits; old_string not found:
96-100% typed from memory; Path traversal: the /tmp fix; Tool call budget exhausted: 25 s/run tail in pub024, and
submit_patch / get_status are budget-free in swegemma 0.2.11 execution.py); three worked examples for pub024's own
costliest form errors (inline python broken 22% of runs, edits from memory, the budget tail)."""
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / "submissions"
PARENT, OUT = SUB / "pub024", SUB / "sa1"
HARNESS_TOOLS = {"run_command", "read_file", "edit_file", "write_file", "get_status", "submit_patch",
                 "get_code_neighbors", "search_similar_code", "get_code_subgraph"}
TOOLS = ["run_command", "read_file", "edit_file", "write_file", "get_status", "submit_patch"]


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(PARENT, OUT, ignore=shutil.ignore_patterns("__pycache__"))
    a = (PARENT / "agent.yaml").read_text()
    head, _, tail = a.partition("tools:\n")
    rest = tail.split("generate_content_config:", 1)[1]
    (OUT / "agent.yaml").write_text(
        "# sa1 (2026-11-15): pub024's shape, prompt written fresh from evidence, harness tools only, few-shot examples (scripts/make_sa1.py)\n"
        + head + "tools:\n" + "".join(f"  - {t}\n" for t in TOOLS) + "generate_content_config:" + rest)
    p = (ROOT / "scripts/agent_sa1/system.md").read_text()
    low = p.lower()
    assert "budget" not in low.replace("tool call budget exhausted", ""), "no budget wording except the harness message"
    assert "minute" not in low and not re.search(r"\b\d+\s*(tool\s*)?calls?\b|\bby call\b|\bcall \d+", low)
    for msg in ("mandatory input parameters are not present", "old_string not found", "Path traversal detected",
                "Tool call budget exhausted", "# EXAMPLES", "Example 1", "Example 2", "Example 3"):
        assert msg in p, msg
    assert "search_similar_code" not in p and "get_code_" not in p
    (OUT / "prompts/system.md").write_text(p)
    # checks: same files as pub024, configs byte for byte, tools only the harness's own, no skills
    files = lambda d: sorted(q.relative_to(d).as_posix() for q in d.rglob("*") if q.is_file())
    assert files(OUT) == files(PARENT)
    for f in ("configs/sampling.yaml", "eval_config.yaml"):
        assert (OUT / f).read_bytes() == (PARENT / f).read_bytes(), f
    declared = re.findall(r"^\s+- (\w+)\s*$", (OUT / "agent.yaml").read_text(), re.M)
    assert declared == TOOLS and set(declared) <= HARNESS_TOOLS
    assert not (OUT / "skills").exists()
    print("wrote", OUT.relative_to(ROOT), files(OUT), "| prompt words", len(p.split()))


if __name__ == "__main__":
    main()
