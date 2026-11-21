"""sk_a2p = sk_a2 with ONE change: the explicit call plan of the public 'LB 0.22 | 4 config files' prompt (bliverrigpdoge, Apache-2.0;
repeated public scores 13 / 12 / 11 of 58) added to sk_a2's 'How you are scored' section: by the 12th tool call a source file must be
edited (else the best-guess edit now), no new exploration after the 20th. User 2026-11-21: 'if breaking my rule can produce arm, lets do
that' (the no-budget-numbers rule is waived for this arm). Everything else byte for byte sk_a2's. Run: python3 -I scripts/make_ska2p.py"""
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC, OUT = ROOT / "submissions/sk_a2", ROOT / "submissions/sk_a2p"
A = """very next tool call is that edit, even if you are only fairly sure. Checking comes after the edit.
"""
B = A + """By your 12th tool call you must have edited a source file. If you have not, stop exploring and make your best-guess
edit in the most likely place now: runs that are still only reading after 12 calls almost never succeed, and more
reading does not help. After your edit: one targeted check, a correction if needed, then submit_patch. Do not start
new exploration after your 20th tool call.
"""


def build():
    s = (SRC / "prompts/system.md").read_text()
    assert s.count(A) == 1
    s2 = s.replace(A, B)
    added = [l for l in s2.splitlines() if l not in s.splitlines()]
    assert len(added) == 4 and [l for l in s.splitlines() if l not in s2.splitlines()] == []
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SRC, OUT)
    (OUT / "prompts/system.md").write_text(s2)
    y = (SRC / "agent.yaml").read_text().replace("# sk_a2: mix + the agent's reading tool",
        "# sk_a2p (2026-11-21): sk_a2 + the public 0.22 prompt's call plan (edit by call 12; scripts/make_ska2p.py). sk_a2 was: mix + the agent's reading tool", 1)
    (OUT / "agent.yaml").write_text(y)
    print("wrote", OUT.relative_to(ROOT), "| prompt", len(s), "->", len(s2), "chars")


if __name__ == "__main__":
    build()
