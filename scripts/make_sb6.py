"""sb6 (user 2026-11-18: 'yes build sb6 with those 4 tasks'). Run: python3 -I scripts/make_sb6.py

sb6 = sb1's agent (one LlmAgent, the six harness tools, T 0.2, thinking 4096, 28 calls, 8 min; agent.yaml body, configs
and eval_config byte for byte) with a prompt written fresh (scripts/agent_sb6/system.md). Basis (docs/PLAN.md
CONTEXT AT THE EDIT + LINE HISTORY STEP 0, 2026-11-18):
  - context at the first edit: real-fix lines visible to the model in 76% of solved vs 47% of failed runs, compaction
    29% vs 56% (352 runs; same task 8+/2-); Coherence Collapse arXiv 2603.24631;
  - line history (HAFixAgent arXiv 2511.01047: blame-commit history of the buggy lines, BugsInPy 54.3 -> 75.2%);
    Step 0: `git log -L` on the real-fix lines has history in 39/40 tasks, related ~21-23, <= 4,000 chars in 117/123;
    from the agent's own edit location it shares the real-fix lines' commit in 160/273 failed runs;
  - adoption: sb1's example commands that fit the work were copied (heredoc 72%, pytest 49%), separate history
    exploration was not (1%) -> the history call sits INSIDE every edit: read_file -> git log -L on the same lines ->
    edit_file (also re-loads the lines into the last events that compaction keeps).
Kept from sb1 (proven): goal line, KEEP GOING, the four harness-message rules, heredoc check + re-run, pytest on the
existing test file, keep existing parameters, plain-text edit example. Dropped: co-change / sibling-commit /
git log --oneline commands (1% use; they ask WHERE, not our gap). Added: the line-history step and one rule for
git's 'has only N lines'."""
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / "submissions"
PARENT = SUB / "sb1"
TOOLS = ["run_command", "read_file", "edit_file", "write_file", "get_status", "submit_patch"]
HEAD = "# sb6 (2026-11-18): sb1's agent, prompt written fresh: every edit = read_file -> git log -L on the same lines -> edit_file (scripts/make_sb6.py)\n"
HIST = "git log -L START,END:FILE -n 3 --format='commit %h %ad %s' --date=short | awk '/^commit /{n=0} !/^(diff|index|---|[+][+][+])/ && n++<16' | cut -c1-150"


def check_prompt(p):
    low = p.lower()
    assert "budget" not in low.replace("tool call budget exhausted", ""), "no budget wording except the harness message"
    assert "minute" not in low and not re.search(r"\b\d+\s*(tool\s*)?calls?\b|\bby call\b|\bcall \d+", low), "no call / time numbers"
    for msg in ("mandatory input parameters are not present", "old_string not found", "Path traversal detected",
                "Tool call budget exhausted", "has only ... lines", "# EXAMPLES", "Example 1", "Example 2", "Example 3"):
        assert msg in p, msg
    assert "Example 4" not in p
    ex = p[p.index("# EXAMPLES"):]
    assert "\\n" not in ex and '\\"' not in ex and "\\'" not in ex, "no escapes in the examples"
    assert not re.search(r"\b(run_command|edit_file|read_file|submit_patch|write_file)\(", p), "no call syntax anywhere"
    for block in re.findall(r"```\n(.*?)```", p, re.S):
        if block.lstrip().startswith(("git ", "python3")):
            assert '"' not in block and "`" not in block and "\\" not in block, "shell text: single quotes, no backticks / backslashes"
    assert not re.search(r"\{[A-Za-z_][\w.]*\??\}", p), "no {name} placeholders"
    assert HIST in p, "the history command in step 4"
    assert p.count(HIST.replace("START,END:FILE", "42,45:pkg/parser.py")) == 1, "the same command in example 2"
    for need in ("-- '*test*'", "keeps the parameters", "same command runs again", "never copy from them", "timeout 150 python -m pytest"):
        assert need in p, need
    for gone in ("--full-diff", "git show --stat", "git log --oneline", "search_similar_code", "get_code_"):
        assert gone not in p, gone
    # example 2 is consistent: the read_file text holds the history's '+' lines, the edit's old_string is in the read text
    read = re.search(r"printed:\n```\n(.*?)```", ex, re.S).group(1)
    hist = re.search(r"It printed, newest first:\n```\n(.*?)```", ex, re.S).group(1)
    for l in hist.splitlines():
        if l.startswith("+"):
            assert l[1:] in read, l
    old = re.search(r"old_string:\n```\n(.*?)```", ex, re.S).group(1)
    assert old in read, "old_string copied from the read_file output"


def main():
    p = (ROOT / "scripts/agent_sb6/system.md").read_text()
    check_prompt(p)
    out = SUB / "sb6"
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(PARENT, out, ignore=shutil.ignore_patterns("__pycache__"))
    first, rest = (PARENT / "agent.yaml").read_text().split("\n", 1)
    assert first.startswith("# sb1 (2026-11-16)")
    (out / "agent.yaml").write_text(HEAD + rest)
    (out / "prompts/system.md").write_text(p)
    files = lambda d: sorted(q.relative_to(d).as_posix() for q in d.rglob("*") if q.is_file())
    assert files(out) == files(PARENT)
    for f in ("eval_config.yaml", "configs/sampling.yaml"):
        assert (out / f).read_bytes() == (PARENT / f).read_bytes(), f
    declared = re.findall(r"^\s+- (\w+)\s*$", (out / "agent.yaml").read_text(), re.M)
    assert declared == TOOLS, declared
    assert not (out / "skills").exists()
    print("wrote", out.relative_to(ROOT), "| prompt words", len(p.split()), "(sb1: 963)")


if __name__ == "__main__":
    main()
