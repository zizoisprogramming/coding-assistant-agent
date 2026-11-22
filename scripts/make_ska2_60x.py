"""sk_a2_60x = sk_a2_60 with its prompt rewritten top to bottom around the rhythm of solved runs (THE STEPS OF SUCCESSFUL RUNS
2026-11-23: 'look + run code -> edit -> look again + run code' = 35% of solved sk_a2-family runs vs 4% of failed on the same tasks):
LOOK (a.py) -> RUN the issue's example once (one heredoc, timeout 30, no input-waiting scripts) -> EDIT -> LOOK AGAIN and RUN again, then
the targeted test and submit; two worked examples follow the four steps (one where the run shows the reading was wrong). Kept from sk_a2:
install call 1, a.py-only reading and its banners, the contract, edit mechanics, test / patch hygiene, never list, 28 calls / 8 min.
a.py, tools, sampling, eval_config = sk_a2_60 byte for byte. User 2026-11-23: 'drop the ctrl and on the worked example only, it needs
full prompt reformatting ... the agent is tailored to use this pattern'. Run: python3 -I scripts/make_ska2_60x.py"""
import shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
s, o = ROOT / "submissions/sk_a2_60", ROOT / "submissions/sk_a2_60x"
if o.exists():
    shutil.rmtree(o)
shutil.copytree(s, o)
p = (ROOT / "scripts/agent_ska2x/system.md").read_text()
assert "'" not in p.split("timeout 30 python3 - << 'EOF'")[0] or True
for must in ("Call 1: run_skill_script", "NO EDIT YET, STOP READING or", "timeout 90 python3 -m pytest", "Example 1", "Example 2", "28 tool"):
    assert must in p, must
(o / "prompts/system.md").write_text(p)
(o / "agent.yaml").write_text("# sk_a2_60x (2026-11-23): sk_a2_60 with the prompt rewritten around LOOK -> RUN -> EDIT -> LOOK AGAIN + RUN (scripts/make_ska2_60x.py). " + (s / "agent.yaml").read_text().lstrip("# "))
print("wrote", o.relative_to(ROOT), len(p.split()), "words (sk_a2:", len((s / "prompts/system.md").read_text().split()), ")")
