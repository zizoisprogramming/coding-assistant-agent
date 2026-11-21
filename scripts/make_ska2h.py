"""sk_a2h = sk_a2 with ONE change: edits through the heredoc edit command (sb1h's Python step + the backslash and line-number fallbacks,
scripts/agent_sc1/parts.edit_step) instead of edit_file; edit_file and write_file removed from the tools (as sb1h); own check scripts run as
heredocs. Everything else byte for byte sk_a2's (its a.py / install / commands, thinking 2048 / max output 4096, 28 calls, the rest of the
prompt). User 2026-11-21: 'go' on sk_a2 vs sk_a2 + heredoc edits (control = sk_a2 from 11-21). Evidence for the change: in the sb family
heredoc edits cut broken-edit loops from 7/22 runs to 0/22 (LESSONS 3). Run: python3 -I scripts/make_ska2h.py"""
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/agent_sc1"))
import parts as P  # noqa: E402

SRC, OUT = ROOT / "submissions/sk_a2", ROOT / "submissions/sk_a2h"
OLD = "        self.timeout = timeout\n"
NEW = "        if timeout < 0:\n            raise ValueError('timeout must be >= 0')\n        self.timeout = timeout\n"
EDIT_CMD = ("mkdir -p .git/agent\ncat > .git/agent/old <<'OLD_TEXT'\n" + OLD + "OLD_TEXT\ncat > .git/agent/new <<'NEW_TEXT'\n" + NEW
            + "NEW_TEXT\n" + P.edit_step().replace("PATH", "pkg/client.py"))

EDIT_BULLET_OLD = """- edit_file mechanics: copy the real characters from the show output (without the line-number column), never
  JSON-escape backslashes. Keep old_string short and unique: never include docstrings, triple-quoted strings, or
  blank-line runs. Several small edits beat one large edit. If a call fails validation, never resend the identical
  call: show the exact lines again and rebuild from a fresh short anchor, or edit with run_command:
  python3 - << 'EOF' (open the file, assert the old text occurs once, replace it, write it back) EOF.
"""
EDIT_BULLET_NEW = """- Every edit is one run_command in this shape (the invented example below: the client from the Example section):
```
""" + EDIT_CMD + """```
  The old lines go between the OLD_TEXT lines and the new lines between the NEW_TEXT lines, copied from the show output
  without the line-number column; the Python step after them stays exactly as shown. It replaces the old text only when
  it occurs exactly once and prints the changed lines. Keep the old lines short and unique: never include docstrings,
  triple-quoted strings, or blank-line runs. Several small edits beat one large edit.
- When the edit prints "old text found 0 times": show the exact lines again and copy the old lines from that output.
  When it prints "line numbers from the show output removed from your text" or "double backslashes in your text read as
  single ones": the edit was applied, go on. When it says "unexpected EOF while looking for matching": the command was
  sent with the ``` lines above and below it; send the same command again without them.
"""
SCRIPT_OLD = """- A script of your own: write it with write_file to .git/agent/check.py (outside your patch; write_file refuses /tmp)
  and run it under a time limit: timeout 30 python3 .git/agent/check.py
"""
SCRIPT_NEW = """- A script of your own: run it as a heredoc under a time limit, so nothing is written into the repository:
  timeout 30 python3 - <<'EOF' ... EOF
"""


def build():
    s = (SRC / "prompts/system.md").read_text()
    for a, b in ((EDIT_BULLET_OLD, EDIT_BULLET_NEW), (SCRIPT_OLD, SCRIPT_NEW)):
        assert s.count(a) == 1, a[:60]
        s = s.replace(a, b)
    assert "edit_file" not in s and "write_file" not in s and "old_string" not in s
    blk = re.findall(r"```\n(.*?)```", s, re.S)
    assert blk == [EDIT_CMD] and '"' not in EDIT_CMD and "`" not in EDIT_CMD and "\\" not in EDIT_CMD
    base = (SRC / "prompts/system.md").read_text()
    gone = [l for l in base.splitlines() if l not in s.splitlines()]
    assert all(("edit_file" in l or "old_string" in l or "write_file" in l or l.strip().startswith(("JSON-escape", "blank-line", "call: show", "python3 - << 'EOF'", "and run it under"))) for l in gone), gone
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SRC, OUT)
    (OUT / "prompts/system.md").write_text(s)
    y = (SRC / "agent.yaml").read_text()
    for t in ("  - edit_file\n", "  - write_file\n"):
        assert y.count(t) == 1
        y = y.replace(t, "")
    y = y.replace("# sk_a2: mix + the agent's reading tool", "# sk_a2h (2026-11-21): sk_a2 with heredoc edits (edit_file / write_file removed; scripts/make_ska2h.py). sk_a2 was: mix + the agent's reading tool", 1)
    (OUT / "agent.yaml").write_text(y)
    print("wrote", OUT.relative_to(ROOT), "| prompt", len(base), "->", len(s), "chars | tools", re.findall(r"  - (\w+)", y.split("skills:")[0]))


if __name__ == "__main__":
    build()
