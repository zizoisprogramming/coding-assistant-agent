"""sk_a2ge2 = sk_a2ge made faster (docs/PLAN.md 'RESULT r150'; user 2026-11-23: 'i think we need to make it faster' -> 'build it').
r150: the editor worked when briefed (right file 4/4, first call the edit 3/4, ~30 s), but the gatherer used 15-23 calls and wrote its brief at a
median 374 s or never, running 2-10 scripts (invisible to a.py) with ~2,000-token hand-tracing replies. Changes (everything else = sk_a2ge):
  a.py 'brief' closure: after CLOSE_LOOKS (8) looks OR CLOSE_SECONDS (150 s since install), whichever first, while the tree has no change
  gather prompt (scripts/agent_ska2ge2/gather.md, written in full): reading only (no scripts: the editor runs the CHECK), BRIEF as soon as the
      function to change is shown; Example 2 = the urge to run a script / trace by hand -> the BRIEF; Example 3 = READING CLOSED -> the BRIEF
  editor prompt (scripts/agent_ska2ge2/editor.md): + never read_file / cat / sed first: the BRIEF's lines are the material (r150 fastapi_15589 s2)
Run: python3 -I scripts/make_ska2ge2.py"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC, OUT = ROOT / "submissions/sk_a2ge", ROOT / "submissions/sk_a2ge2"
CLOSE_LOOKS, CLOSE_SECONDS = 8, 150


def sub(t, a, b):
    assert t.count(a) == 1, a[:80]
    return t.replace(a, b)


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SRC, OUT)
    ap = OUT / "skills/agent/scripts/a.py"
    a = ap.read_text()
    a = sub(a, "CLOSE_LOOKS = 10", f"CLOSE_LOOKS, CLOSE_SECONDS = {CLOSE_LOOKS}, {CLOSE_SECONDS}  # sk_a2ge2: closes at 8 looks or 150 s since install")
    a = sub(a, '    if st["looks"] < CLOSE_LOOKS or has_change():\n        return None',
            '    secs = time.time() - st.get("t0", time.time())\n    if (st["looks"] < CLOSE_LOOKS and secs < CLOSE_SECONDS) or has_change():\n        return None')
    a = sub(a, "f\">>> READING CLOSED: {st['looks']} looks and no change in the repository yet,",
            "f\">>> READING CLOSED: {st['looks']} looks, {int(secs)} s, and no change in the repository yet,")
    ap.write_text(a)
    g = (ROOT / "scripts/agent_ska2ge2/gather.md").read_text()
    e = (ROOT / "scripts/agent_ska2ge2/editor.md").read_text()
    assert "{" not in g and "READING CLOSED" in g and "never run scripts" in g
    assert e.count("{") == 2 and "{problem_description}" in e and "{brief}" in e and "never open the file with read_file" in e
    (OUT / "prompts/gather.md").write_text(g)
    (OUT / "prompts/editor.md").write_text(e)
    y = (OUT / "agent.yaml").read_text()
    (OUT / "agent.yaml").write_text(sub(y, "# sk_a2ge (2026-11-23): gatherer (no edit tools, stopped by a.py READING CLOSED after 10 looks)",
                                        "# sk_a2ge2 (2026-11-23): sk_a2ge faster: gatherer reads only, closed at 8 looks or 150 s (scripts/make_ska2ge2.py). Was: sk_a2ge gatherer (stopped by a.py READING CLOSED after 10 looks)"))
    print("wrote", OUT.relative_to(ROOT), "| gather", len(g.split()), "words | editor", len(e.split()), "words")


if __name__ == "__main__":
    build()
