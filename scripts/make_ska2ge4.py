"""sk_a2ge4 = sk_a2ge3 + a tool-ended hand-over + an editor verdict event (docs/PLAN.md 'PLAN (not built) 2026-11-24: a TOOL-ENDED HAND-OVER';
user 2026-11-24: 'yes build'). Harness facts (source): an LlmAgent stops on a final response; an event whose actions.skip_summarization is set is
final; adk_submission allows tools entries 'agent_tool: {config_path, skip_summarization: true}' and ADK's AgentTool sets skip_summarization -> the
caller's turn ends when it calls that tool; the child runs with a copy of the parent state and its state_delta comes back; a function-response-only
final event does not overwrite the caller's output_key.
  (A) gather.yaml + tool 'handover' (agent_tool handover.yaml, skip_summarization: true): a tiny no-tool LlmAgent that replies with the request
      text (output_key notes). The gatherer's stage ends the moment it calls handover(request='RULE ... EDIT ... CHECK ...'). READING CLOSED and
      the a.py brief output end with 'next: call handover'. editor.md reads {notes?} and {brief?} (both optional: a missing key must not crash).
  (B) a.py 'check' (replaces the old repro check): runs .git/agent/check.py (timeout 30); GREEN when a line 'CHECK PASSED' is printed -> 'submit
      now'; RED -> 'make ONE repair edit in FUNCTION now' + the function as it is now; a second RED -> 'submit now'; no edit yet -> 'edit first'.
Prompts: scripts/agent_ska2ge4/gather.md, editor.md, handover.md. Run: python3 -I scripts/make_ska2ge4.py"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC, OUT = ROOT / "submissions/sk_a2ge3", ROOT / "submissions/sk_a2ge4"

CHECK = '''def cmd_check(st, args):
    """sk_a2ge4: the editor's verdict: run .git/agent/check.py; GREEN (a 'CHECK PASSED' line) -> submit; RED -> one repair, then submit."""
    chk = os.path.join(HERE, "check.py")
    if not has_change():
        return ">>> NO EDIT YET: make the edit first (from the CURRENT LINES of a.py brief), then run check. <<<"
    if not os.path.exists(chk):
        return (">>> NO CHECK SCRIPT: write .git/agent/check.py with write_file: the issue's own example with an assert of the wanted "
                "result, ending with print(\\"CHECK PASSED\\"). Then run python3 .git/agent/a.py check. <<<")
    out = run('PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}" timeout 30 python3 -B .git/agent/check.py 2>&1', 40)  # -B: no stale .pyc after a same-second edit; the repo on the path, as for python3 - from /workspace
    tail = "\\n".join(out.split("\\n")[-15:])
    green = any(l.strip() == "CHECK PASSED" for l in out.split("\\n"))
    st["checks"] = st.get("checks", 0) + 1
    if green:
        return f"$ python3 .git/agent/check.py\\n{tail}\\n>>> GREEN: the check passes. Your next call is submit_patch (after git status --short). <<<"
    st["red"] = st.get("red", 0) + 1
    if st["red"] >= 2:
        return (f"$ python3 .git/agent/check.py\\n{tail}\\n>>> RED again after your repair. Do not investigate further: your next call is "
                f"submit_patch (after git status --short); a wrong edit scores no less than no edit. <<<")
    lines = [f"$ python3 .git/agent/check.py", tail,
             ">>> RED: the check fails. Keep your edit. Your next call is ONE repair edit in the function below (as it is now, with "
             "your change), at the line that computes the wrong value; then run python3 .git/agent/a.py check once more. <<<"]
    funcs = [f for f in st.get("funcs", []) if not TEST_RE.search(f["file"])]
    f = st.get("brief_target") or (funcs[-1] if funcs else None)
    if f:
        try:
            src = file_lines(f["file"])
            items = [it for it in (outline_items(f["file"]) or []) if it[0] == f["name"]]
            a, b = (items[0][1], items[0][2]) if items else (f["a"], min(f["b"], len(src)))
            lines.append(f"{f['file']} {f['name']} {a}-{b} (now):")
            lines += [f"{i:6}| {src[i - 1]}" for i in range(a, min(b, a + 59) + 1)]
        except OSError:
            pass
    return "\\n".join(lines)


'''

HANDOVER_YAML = """name: handover
model: gemma-4-31b-it-qat-w4a16-ct
description: Hands your BRIEF notes to the editor and ends your work. Call it with request = your RULE, EDIT and CHECK lines.
instruction: !include prompts/handover.md
output_key: notes
generate_content_config: !include configs/handover_sampling.yaml
"""
HANDOVER_SAMPLING = """# the hand-over agent only repeats its request: short output, little thinking
temperature: 0.0
top_p: 0.95
max_output_tokens: 1536
thinking_config:
  thinking_budget: 128
  include_thoughts: true
"""


def sub(t, a, b):
    assert t.count(a) == 1, a[:80]
    return t.replace(a, b)


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SRC, OUT)
    ap = OUT / "skills/agent/scripts/a.py"
    a = ap.read_text()
    s0 = a.index("def cmd_check(st, args):")
    s1 = a.index("def has_change():")
    a = a[:s0] + CHECK + a[s1:]
    a = sub(a, '''f"Editing: your next call is the edit, from the CURRENT LINES below. Reading opens again after the edit. <<<",''',
            '''f"Editing: your next call is the edit, from the CURRENT LINES below. Reading opens again after the edit. Gathering, in one "
             f"call: handover with request = your RULE, EDIT and CHECK lines. <<<",''')
    a = sub(a, '    text = "\\n".join(lines)\n    try:\n        with open(BRIEF_FILE, "w") as fh:',
            '    text = "\\n".join(lines)\n    tail = ("\\n>>> Gathering: your next call is handover, with request = your RULE, EDIT and CHECK lines (one sentence each). "\n'
            '            "Editing: your next call is the edit. <<<")\n    try:\n        with open(BRIEF_FILE, "w") as fh:')
    a = sub(a, "        pass\n    return text\n\n\ndef cmd_brief", "        pass\n    return text + tail\n\n\ndef cmd_brief")
    ap.write_text(a)
    (OUT / "skills/agent/scripts/commands.txt").write_text("find outline show brief check banner reshow close\n")
    ip = OUT / "skills/agent/scripts/install.py"
    ip.write_text(sub(ip.read_text(), '    "check": "check                         after an edit: .git/agent/repro.py + nearest tests + git status",',
                      '    "check": "check                         after the edit: runs .git/agent/check.py -> GREEN (submit) or RED (one repair)",'))
    for stg in ("gather", "editor", "handover"):
        p = (ROOT / f"scripts/agent_ska2ge4/{stg}.md").read_text()
        if stg in ("gather", "handover"):
            assert "{" not in p and ("handover" in p or stg == "handover")
        elif stg == "editor":
            assert p.count("{") == 3 and "{problem_description}" in p and "{notes?}" in p and "{brief?}" in p and "a.py check" in p, p.count("{")
        (OUT / f"prompts/{stg}.md").write_text(p)
    (OUT / "handover.yaml").write_text(HANDOVER_YAML)
    (OUT / "configs/handover_sampling.yaml").write_text(HANDOVER_SAMPLING)
    g = (OUT / "gather.yaml").read_text()
    g = sub(g, "  - submit_patch\nskills:", "  - submit_patch\n  - agent_tool:  # sk_a2ge4: calling it ends this stage (skip_summarization)\n"
                                         "      config_path: handover.yaml\n      skip_summarization: true\nskills:")
    (OUT / "gather.yaml").write_text(g)
    y = (OUT / "agent.yaml").read_text()
    (OUT / "agent.yaml").write_text("# sk_a2ge4 (2026-11-24): sk_a2ge3 + handover tool that ends the gatherer's stage + a.py check GREEN / RED"
                                    " (scripts/make_ska2ge4.py). " + y.lstrip("# "))
    print("wrote", OUT.relative_to(ROOT))


if __name__ == "__main__":
    build()
