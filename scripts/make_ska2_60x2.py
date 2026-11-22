"""sk_a2_60x2 = sk_a2_60x with its prompt rewritten to add worked examples for the two failure shapes few-shot can reach
(scripts/mine_bank/fail_shapes.py, 223 failed sk_a2-family runs: no edit after STOP READING 17% + edit refused at the 28-call
budget 15%; wrong kept edit 56%; undone edit / red check then nothing 3%): Example 3 = STOP READING or 'Only N tool call(s)
remaining' before the agent is sure -> the next call edits the function already shown; Example 4 = the RUN after the edit is
still wrong / raises -> keep the edit, repair once in the same function, never restore the old code. Plus one line each: edit_file
'old_string not found' -> next call is the heredoc replace from a short anchor; a red check -> repair forward. a.py, tools,
sampling, eval_config = sk_a2_60x byte for byte. User 2026-11-23: 'build it, 2 notebooks with sk_a2_60x as control on only 4
tasks'. Run: python3 -I scripts/make_ska2_60x2.py"""
import shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
s, o = ROOT / "submissions/sk_a2_60x", ROOT / "submissions/sk_a2_60x2"
if o.exists():
    shutil.rmtree(o)
shutil.copytree(s, o)
p = (ROOT / "scripts/agent_ska2x2/system.md").read_text()
for must in ("Call 1: run_skill_script", "STOP READING", "Only N tool call(s) remaining", "old_string not found", "timeout 90 python3 -m pytest",
             "Example 1", "Example 2", "Example 3", "Example 4", "28 tool"):
    assert must in p, must
(o / "prompts/system.md").write_text(p)
y = (s / "agent.yaml").read_text()
assert y.startswith("# sk_a2_60x (2026-11-23)")
(o / "agent.yaml").write_text("# sk_a2_60x2 (2026-11-23): sk_a2_60x + worked examples for STOP READING / remaining-calls (edit now) and a wrong check after the edit (repair forward) (scripts/make_ska2_60x2.py). " + y.lstrip("# "))
print("wrote", o.relative_to(ROOT), len(p.split()), "words (sk_a2_60x:", len((s / "prompts/system.md").read_text().split()), ")")
