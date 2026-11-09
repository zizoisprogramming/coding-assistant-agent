"""kf (r69, user 2026-11-09 "build"): pub024 + a KNOWN TOOL FAILURES section. Run: python3 scripts/make_kf_arm.py

The user's idea: tell the model, in plain task-free words, the tool mistakes it makes, measured in our run bank
(docs/PLAN.md "MINING 2026-11-09b", scripts/mine_bank/). Each entry starts from a message the model sees in a tool
result (event-triggered rules are the kind it follows) and says what to do next.

Only prompts/system.md changes: pub024's prompt word for word plus one section at the end (as r65 did, so the only
difference from pub024 is this information). agent.yaml, eval_config.yaml and configs/sampling.yaml are pub024's bytes, so
the tool list, sampling and the 28-call / 8-minute limits (and pub024's leaderboard time fit) are unchanged.
No skill (skill-shell agents timed out on the leaderboard; run_skill_script has several arguments and garbles too) and
write_file stays in the tool list (ADK raises on a call to an unlisted tool unless a callback catches it, and the model
reaches for write_file in 16% of pub024 runs).
"""
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "submissions/pub024"
OUT = ROOT / "submissions/kf"

# Code examples are indented (not fenced): the garbled edit calls mostly end a text with a backtick, so the section adds
# no backticks of its own. No braces anywhere: ADK fills {name} in instructions from session state.
KNOWN_FAILURES = """

# KNOWN TOOL FAILURES
These failures were measured in hundreds of earlier runs of this same agent. Each one starts with a message you will see in a tool result. When you see the message, do what is written under it.

## "mandatory input parameters are not present"
Your edit_file or write_file call was cut apart before it reached the tool: the end of one text swallowed the next argument, so the tool never got old_string. This happens to about one edit call in five, and sending the same call again fails again almost every time.
- Do not send the call again. Make the same change with one run_command that runs a Python heredoc. It has a single argument, so it cannot be cut apart:

    python3 - <<'EOF'
    p = "pkg/module.py"
    s = open(p).read()
    old = r'''    return value
    '''
    new = r'''    return value or default
    '''
    assert s.count(old) == 1, s.count(old)
    open(p, "w").write(s.replace(old, new))
    EOF
    git diff -- pkg/module.py

- To avoid the failure: in every edit_file call write filepath first, then old_string, then new_string, and end each text right after its last character. Never end a text with a backtick.

## "Path traversal detected"
write_file only writes inside /workspace, so a path under /tmp always fails. To try code, run it directly with run_command and python3 - <<'EOF' ... EOF. Nothing is saved, so nothing ends up in the patch.

## "SyntaxError" after python -c
Quotes inside python -c break easily. For more than one line of Python, use the heredoc form shown above.

## "CommandError" with exit_code 1 and an empty message after grep
grep found no match; the command itself worked. Do not run the same pattern again. Search for a different exact string, or act on what you already have.

## "is_truncated": true from read_file
read_file without end_line returns up to 150 lines. Long outputs fill the conversation; it then gets summarized and the earlier tool results disappear, which leads to reading the same lines again. Always pass start_line and end_line, about 40 lines around what you need.

## "budget_warning"
Only a few tool calls remain. Edits after the budget runs out are refused, and a run without an edit scores zero. Your next call is edit_file (or the heredoc edit) with your best fix. If your fix is already in, run the final check and call submit_patch.
"""


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(PUB, OUT)
    pub = (PUB / "prompts/system.md").read_text()
    text = pub.rstrip("\n") + KNOWN_FAILURES
    (OUT / "prompts/system.md").write_text(text)
    # checks
    assert text.startswith(pub.rstrip("\n")), "kf must start with pub024's prompt word for word"
    assert "{" not in text and "}" not in text, "no braces: ADK would try to fill them from session state"
    assert "```" not in KNOWN_FAILURES, "no code fences in the new section"
    for f in PUB.rglob("*"):
        if f.is_file() and f.name != "system.md":
            g = OUT / f.relative_to(PUB)
            assert g.read_bytes() == f.read_bytes(), f"{g} differs from pub024"
    assert sorted(p.relative_to(OUT).as_posix() for p in OUT.rglob("*") if p.is_file()) == \
        sorted(p.relative_to(PUB).as_posix() for p in PUB.rglob("*") if p.is_file())
    assert not re.search(r"fastapi|rich[_/.]|starlette|pydantic", KNOWN_FAILURES, re.I), "no task or repo names"
    print(f"{OUT.relative_to(ROOT)}: prompt {len(pub)} -> {len(text)} chars (+{len(text) - len(pub)}), other files = pub024")


if __name__ == "__main__":
    build()
