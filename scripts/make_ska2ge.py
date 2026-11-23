"""sk_a2ge = gatherer -> editor on sk_a2's tools (docs/PLAN.md 'PLAN (not built) 2026-11-23: GATHERER -> EDITOR'; user 2026-11-23: 'build it',
choices: 10 reads, one run of the issue's example in the gatherer, first trial 4 tasks x 2 notebooks vs sk_a2).
Evidence: sk_a2-family runs had shown the real-fix lines by call 10 in 75% of failed runs (gather_window.py); past splits failed because a
stage only ends on a text reply (r113: explorer 13-30 calls, editor reached 2/8) -> here the gatherer is stopped by a TOOL EVENT:
  a.py option 'brief': once looks >= CLOSE_LOOKS and the working tree has no change, find / outline / show answer READING CLOSED + the last code
  read (<= 40 numbered lines) and do not count as looks; reading opens again as soon as the tree has a change (the editor's edit).
Root  = SequentialAgent [gather, editor]; budgets stay global (eval_config = sk_a2's: 240 s, 28 calls, 8 min).
gather = the six tools declared (an undeclared tool call ends the run) + skills/agent, prompt: never edit or submit; output_key brief; prompt scripts/agent_ska2ge/gather.md.
editor = the six tools + skills/agent; include_contents none (clean context); its prompt holds {problem_description} and {brief};
         prompt scripts/agent_ska2ge/editor.md.
Sampling = sk_a2's. Run: python3 -I scripts/make_ska2ge.py"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC, OUT = ROOT / "submissions/sk_a2", ROOT / "submissions/sk_a2ge"
CLOSE_LOOKS = 10

CLOSED = '''

def read_closed(st, cmd):
    """sk_a2ge: after CLOSE_LOOKS looks with no change in the working tree, find / outline / show are closed until a change exists."""
    if "brief" not in OPTS or cmd not in ("find", "outline", "show"):
        return None
    if st["looks"] < CLOSE_LOOKS or has_change():
        return None
    st["blocked"] = st.get("blocked", 0) + 1
    lines = [f">>> READING CLOSED: {st['looks']} looks and no change in the repository yet, so a.py shows no more code until there is "
             f"one. Gathering: write your BRIEF now, as your reply. Editing: your next call is the edit, from the BRIEF or the code below "
             f"(copy the characters without the line numbers). Reading opens again after the edit. <<<"]
    if st["reads"]:
        r = st["reads"][-1]
        try:
            src = file_lines(r["file"])
            b = min(r["b"], r["a"] + RESHOW_MAX - 1, len(src))
            lines.append(f"last code you read: {r['file']} {r['a']}-{b}")
            lines += [f"{i:6}| {src[i - 1]}" for i in range(r["a"], b + 1)]
        except OSError:
            pass
    return "\\n".join(lines)

'''


def sub(t, a, b):
    assert t.count(a) == 1, a[:80]
    return t.replace(a, b)


def patched_apy():
    a = (SRC / "skills/agent/scripts/a.py").read_text()
    a = sub(a, 'OPTIONS = {"banner", "reshow"}',
            f'OPTIONS = {{"banner", "reshow", "brief"}}  # sk_a2ge: + brief (READING CLOSED after {CLOSE_LOOKS} looks until a change)\nCLOSE_LOOKS = {CLOSE_LOOKS}')
    a = sub(a, "\n\nHANDLERS = {", CLOSED + "\nHANDLERS = {")
    a = sub(a, "def main(argv):\n    st = load()\n", "def main(argv):\n    st = load()\n    closed = False\n")
    a = sub(a, """        try:
            body = HANDLERS[argv[0].lstrip("-").lower()](st, argv[1:])
        except Exception as e:  # noqa: BLE001  never crash: the model gets a message and the header
            body = f"(error in {argv[0]}: {type(e).__name__}: {e})"
    save(st)
    warn = banner(st)
""", """        try:
            body = read_closed(st, argv[0].lstrip("-").lower())
            closed = body is not None
            if not closed:
                body = HANDLERS[argv[0].lstrip("-").lower()](st, argv[1:])
        except Exception as e:  # noqa: BLE001  never crash: the model gets a message and the header
            body, closed = f"(error in {argv[0]}: {type(e).__name__}: {e})", False
    warn = "" if closed else banner(st)
    save(st)
""")
    return a


ROOT_YAML = """# sk_a2ge (2026-11-23): gatherer (no edit tools, stopped by a.py READING CLOSED after 10 looks) -> editor (clean context, issue + brief
# pinned in its prompt) on sk_a2's tools (scripts/make_ska2ge.py)
name: swe_agent
agent_class: SequentialAgent
description: Gathers the facts for the fix, then edits, checks and submits.
sub_agents:
  - config_path: gather.yaml
  - config_path: editor.yaml
"""
GATHER_YAML = """name: gather
model: gemma-4-31b-it-qat-w4a16-ct
instruction: !include prompts/gather.md
output_key: brief
tools:  # all six declared: a call to an undeclared tool ends the whole run ('Tool submit_patch not found', r150 sim); the prompt says gather never edits or submits
  - run_command
  - read_file
  - edit_file
  - write_file
  - get_status
  - submit_patch
skills:
  - skills/agent
generate_content_config: !include configs/sampling.yaml
"""
EDITOR_YAML = """name: editor
model: gemma-4-31b-it-qat-w4a16-ct
instruction: !include prompts/editor.md
include_contents: none
tools:
  - run_command
  - read_file  # declared only so a habitual call never ends the task; the prompt says not to use it
  - edit_file
  - write_file
  - get_status
  - submit_patch
skills:
  - skills/agent
generate_content_config: !include configs/sampling.yaml
"""


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SRC, OUT)
    (OUT / "prompts/system.md").unlink()
    (OUT / "skills/agent/scripts/a.py").write_text(patched_apy())
    c = (SRC / "skills/agent/scripts/commands.txt").read_text().split()
    assert "brief" not in c
    (OUT / "skills/agent/scripts/commands.txt").write_text(" ".join(c + ["brief"]) + "\n")
    g = (ROOT / "scripts/agent_ska2ge/gather.md").read_text()
    e = (ROOT / "scripts/agent_ska2ge/editor.md").read_text()
    assert "{" not in g and "READING CLOSED" in g and "BRIEF" in g
    assert e.count("{") == 2 and "{problem_description}" in e and "{brief}" in e
    (OUT / "prompts/gather.md").write_text(g)
    (OUT / "prompts/editor.md").write_text(e)
    (OUT / "agent.yaml").write_text(ROOT_YAML)
    (OUT / "gather.yaml").write_text(GATHER_YAML)
    (OUT / "editor.yaml").write_text(EDITOR_YAML)
    print("wrote", OUT.relative_to(ROOT), "| gather", len(g.split()), "words | editor", len(e.split()), "words")


if __name__ == "__main__":
    build()
