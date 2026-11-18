"""sb7 + sb8 (user 2026-11-18, after r112's 0/8 adoption: 'we must enforce the mechanism to be adopted'; 'do both
options, lets try both'). Run: python3 -I scripts/make_sb78.py

Both enforce line history by STRUCTURE (YAML only: stages, tools per stage, output_key into the next stage's system
prompt, which compaction never drops). Basis: docs/PLAN.md CONTEXT AT THE EDIT + LINE HISTORY STEP 0 and RESULT r112.
  sb7 (option 1) = SequentialAgent [history, fixer]
    history: one run_command (include_contents none, thinking 128); the model only writes up to three names from the
      issue; a fixed command prints the line history (git log -L, 2 commits, 12 lines each) at each name's definition
      and first use in source files, saved in .git/agent/line_history (a re-run prints the same file, so a restarted
      stage re-copies the same text); the stage replies with the output -> output_key line_history.
    fixer: sb1's tools and sampling; a fresh prompt with the history pinned in it ({line_history?}).
  sb8 (option 2; user reopened a two-stage split for this test) = SequentialAgent [explore, history, editor]
    explore: run_command, read_file, get_status (no edit tools); ends by replying FILE / LINES / CHANGE / CHECK
      (output_key target); hands over on the harness's 'tool call(s) remaining' warning (<= 10 calls left).
    history: one run_command on exactly those lines (git log -L, 3 commits, 16 lines each) -> output_key edit_history.
    editor: sb1's tools and sampling; prompt with {target?} and {edit_history?} pinned; read -> edit -> check -> submit.
eval_config.yaml is sb1's byte for byte for both (28 calls, 8 min; the stages share them)."""
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / "submissions"
PARENT = SUB / "sb1"
MODEL = "gemma-4-31b-it-qat-w4a16-ct"
ALL = ["run_command", "read_file", "edit_file", "write_file", "get_status", "submit_patch"]
STATE = {"{line_history?}", "{target?}", "{edit_history?}"}
HIST_SAMPLING = """# one-call history stage (sb7 / sb8): a fixed command, then the output copied back; little reasoning needed (sb2: thinking 128)
temperature: 0.2
top_p: 0.95
max_output_tokens: 2048
thinking_config:
  include_thoughts: true
  thinking_budget: 128
"""


def check(p, state=()):
    low = p.lower()
    assert "budget" not in low.replace("tool call budget exhausted", ""), "no budget wording except the harness message"
    assert "minute" not in low and not re.search(r"\b\d+\s*(tool\s*)?calls?\b|\bby call\b|\bcall \d+", low), "no call / time numbers"
    assert not re.search(r"\b(run_command|edit_file|read_file|submit_patch|write_file)\(", p), "no call syntax"
    ex = p[p.index("Example"):] if "Example" in p else p
    assert "\\n" not in ex and '\\"' not in ex and "\\'" not in ex, "no escapes in the examples"
    for block in re.findall(r"```\n(.*?)```", p, re.S):
        if re.match(r"\s*(git |python3|names=|f=)", block):
            assert '"' not in block and "`" not in block and "\\" not in block, "shell text: no double quotes, backticks, backslashes"
    found = set(re.findall(r"\{[A-Za-z_][\w.]*\??\}", p))
    assert found == set(state), (found, state)
    assert "search_similar_code" not in p and "get_code_" not in p and "--full-diff" not in p


def yaml_llm(name, desc, prompt, tools, sampling, extra=""):
    t = "\n".join(f"  - {x}" for x in tools)
    return (f"name: {name}\nmodel: {MODEL}\ndescription: {desc}\ninstruction: !include prompts/{prompt}\n{extra}"
            f"tools:\n{t}\ngenerate_content_config: !include configs/{sampling}\n")


def write(out, files):
    if out.exists():
        shutil.rmtree(out)
    (out / "prompts").mkdir(parents=True)
    (out / "configs").mkdir()
    for k, v in files.items():
        (out / k).write_text(v)
    for f in ("eval_config.yaml", "configs/sampling.yaml"):
        shutil.copy(PARENT / f, out / f)
        assert (out / f).read_bytes() == (PARENT / f).read_bytes()
    for y in out.glob("*.yaml"):
        for inc in re.findall(r"!include (\S+)", y.read_text()):
            assert (out / inc).exists(), inc
        for cp in re.findall(r"config_path: (\S+)", y.read_text()):
            assert (out / cp).exists(), cp
        for m in re.findall(r"^model: (.*)$", y.read_text(), re.M):
            assert m == MODEL
    assert not (out / "skills").exists()


def main():
    A = ROOT / "scripts/agent_sb7"
    B = ROOT / "scripts/agent_sb8"
    p7h, p7s = (A / "history.md").read_text(), (A / "system.md").read_text()
    p8e, p8h, p8d = (B / "explore.md").read_text(), (B / "history.md").read_text(), (B / "editor.md").read_text()
    check(p7h); check(p7s, ["{line_history?}"])
    check(p8e); check(p8h, ["{target?}"]); check(p8d, ["{target?}", "{edit_history?}"])
    for p in (p7s, p8d):
        assert "Tool call budget exhausted" in p and "old_string not found" in p and "mandatory input parameters are not present" in p
        old = re.search(r"old_string:\n```\n(.*?)```", p, re.S).group(1)
        read = re.search(r"printed:\n```\n(    def parse.*?)```", p, re.S).group(1)
        assert old in read, "old_string copied from the read_file output"
    assert "tool call(s) remaining" in p8e and "FILE:" in p8e and "LINES:" in p8e and "CHANGE:" in p8e and "CHECK:" in p8e
    assert "head -c 3000 .git/agent/line_history" in p7h and "head -c 3000 .git/agent/edit_history" in p8h

    write(SUB / "sb7", {
        "agent.yaml": "# sb7 (2026-11-18): a one-call history stage (line history where the issue's names are defined / used), pinned into the fixer's system prompt (scripts/make_sb78.py)\n"
                      "name: swe_agent\nagent_class: SequentialAgent\ndescription: Shows how the code named in the issue changed before, then fixes the issue.\n"
                      "sub_agents:\n  - config_path: history.yaml\n  - config_path: fixer.yaml\n",
        "history.yaml": yaml_llm("history", "Runs one git command that prints the line history of the code named in the issue, and returns its output. Makes a single call.",
                                 "history.md", ["run_command"], "history_sampling.yaml", "include_contents: none\noutput_key: line_history\n"),
        "fixer.yaml": yaml_llm("fixer", "Fixes the issue with the smallest source change and submits it.", "system.md", ALL, "sampling.yaml"),
        "prompts/history.md": p7h, "prompts/system.md": p7s, "configs/history_sampling.yaml": HIST_SAMPLING,
    })
    write(SUB / "sb8", {
        "agent.yaml": "# sb8 (2026-11-18): explore (no edit tools) -> one-call line history of the chosen lines -> editor with both pinned (scripts/make_sb78.py)\n"
                      "name: swe_agent\nagent_class: SequentialAgent\ndescription: Finds the lines to change, shows how they changed before, then edits, checks and submits.\n"
                      "sub_agents:\n  - config_path: explore.yaml\n  - config_path: history.yaml\n  - config_path: editor.yaml\n",
        "explore.yaml": yaml_llm("explore", "Finds which source lines must change and how; cannot edit.", "explore.md",
                                 ["run_command", "read_file", "get_status"], "sampling.yaml", "output_key: target\n"),
        "history.yaml": yaml_llm("history", "Runs one git command that prints the line history of the chosen lines, and returns its output. Makes a single call.",
                                 "history.md", ["run_command"], "history_sampling.yaml", "include_contents: none\noutput_key: edit_history\n"),
        "editor.yaml": yaml_llm("editor", "Edits the chosen lines following their history, checks and submits.", "editor.md", ALL, "sampling.yaml"),
        "prompts/explore.md": p8e, "prompts/history.md": p8h, "prompts/editor.md": p8d, "configs/history_sampling.yaml": HIST_SAMPLING,
    })
    for n, ps in (("sb7", (p7h, p7s)), ("sb8", (p8e, p8h, p8d))):
        print("wrote submissions/" + n, "| prompt words", [len(p.split()) for p in ps])


if __name__ == "__main__":
    main()
