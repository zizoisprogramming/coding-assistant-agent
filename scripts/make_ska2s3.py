"""sk_a2s3 = sk_a2s2 with the one-time hold moved LATE + 36 tool calls (user 2026-11-25: 'build A on 4 tasks 2 rich 2 fast, also
increase total tools call').
Why (PLAN 'RESULT r163' + 'WHY THE HOLD HURT FASTAPI'): over 96 sk_a2 runs (r157-r163), rich solves make their first edit early
(median 8 reads, 17/21 by read 10) while fastapi solves edit late (median 15 reads, 16/20 after read 10). The r163 hold at 10 looks /
210 s cut into fastapi runs that were still on the way to a solve (fastapi 1/6 vs 4/6) and caught rich runs that were already lost
(rich 5/10 vs 3/10). On sk_a2's past runs a hold at 18 reads OR 330 s interrupts 4/20 fastapi solves and 3/21 rich solves and still
catches 31/37 rich failures (10 / 210: 16/20, 11/21, 36/37).
Changes vs sk_a2s2:
  - the hold fires on the first find / outline / show at >= 18 looks or >= 330 s (was 10 / 210), still once, no change, no card;
    NO EDIT YET (10 / 210) and STOP READING (15 / 300) banners unchanged (sk_a2's);
  - eval_config max_tool_calls 36 (was 28): room for the card + the edit after a late hold; time cap stays 8 min (LB 12 h fit);
  - prompt written in full (scripts/agent_ska2s3/system.md): 36 calls, the hold described as late (about 18 reads / 5.5 min),
    Example 2 as a long search.
Run: python3 -I scripts/make_ska2s3.py"""
import importlib.util
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "sk_a2s3"
HOLD_LOOKS, HOLD_SECONDS, CALLS = 18, 330, 36
_spec = importlib.util.spec_from_file_location("make_ska2s2", ROOT / "scripts/make_ska2s2.py")
S2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(S2)
S = S2.S
sub = S2.sub


def s3_apy():
    a = S2.s2_apy()
    a = sub(a, """    if st["looks"] < NO_EDIT_LOOKS and secs < NO_EDIT_SECONDS:
        return None
    if has_change():""", f"""    if st["looks"] < {HOLD_LOOKS} and secs < {HOLD_SECONDS}:  # sk_a2s3: the hold comes late (was NO_EDIT_LOOKS / NO_EDIT_SECONDS)
        return None
    if has_change():""")
    a = sub(a, "f\">>> HELD ONCE: NO EDIT YET after {st['looks']} looks", "f\">>> HELD ONCE: still no edit after {st['looks']} looks")
    return a


def build():
    out = ROOT / "submissions" / NAME
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(S.SRC, out)
    (out / "skills/agent/scripts/a.py").write_text(s3_apy())
    (out / "skills/agent/scripts/install.py").write_text(S.s_install())
    (out / "skills/agent/scripts/commands.txt").write_text("find outline show card banner reshow\n")
    p = (ROOT / "scripts/agent_ska2s3/system.md").read_text()
    assert f"{CALLS} tool" in p and "{" not in p and "card.md" in p and "HELD ONCE" in p and "28" not in p
    (out / "prompts/system.md").write_text(p)
    e = (out / "eval_config.yaml").read_text()
    (out / "eval_config.yaml").write_text(sub(e, "max_tool_calls: 28", f"max_tool_calls: {CALLS}"))
    y = (out / "agent.yaml").read_text()
    (out / "agent.yaml").write_text(sub(y, "# sk_a2: mix + the agent's reading tool",
                                        f"# {NAME} (2026-11-25): sk_a2s2 with the hold late ({HOLD_LOOKS} looks / {HOLD_SECONDS} s) + {CALLS} calls (scripts/make_ska2s3.py). sk_a2 was: mix + the agent's reading tool"))
    print("wrote", out.relative_to(ROOT), len(p.split()), "words")


if __name__ == "__main__":
    build()
