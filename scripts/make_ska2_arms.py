"""More one-change arms on sk_a2 (user 2026-11-21: 'i need many arms man, as many as u can, look at our bank, what more can we add to
sk_a2'). Each = sk_a2 byte for byte except ONE thing (control = sk_a2):
  sk_a2g = sampling temperature 1.0 / top_k 64 (Google's recommended Gemma 4 setting; the public 'Idris v24' bundle used it: 0.24 public
           in one draw, 23/66 on its author's held-out runs); sk_a2's thinking 2048 / max output 4096 kept.
  sk_a2t = thinking 4096 / max output 8192 (pub024's / the public 0.22 bundle's / sb1hl's setting) instead of sk_a2's 2048 / 4096: tests
           whether sk_a2's short replies (0.1% of replies >= 3,500 tokens vs sb1hl's 1.5%) are part of why it edits.
  sk_a2e = evidc's search folded into the install call: install.py takes 2-4 names (positional_args) and prints where each is defined /
           used in source + test lines that use it (sc1's install.py / where.py, scripts/agent_sc1/parts.py); the prompt's Call 1 paragraph
           names the positional_args (evidc vs combo1 r76-r77: +8/-2 over 36 pairs, gain on mid-rate tasks).
(sk_a2h, sk_a2p: scripts/make_ska2h.py / make_ska2p.py; sk_a2_32 = the existing 32-call bundle.) Run: python3 -I scripts/make_ska2_arms.py"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/agent_sc1"))
import parts as P  # noqa: E402

SRC = ROOT / "submissions/sk_a2"
SAMP = (SRC / "configs/sampling.yaml").read_text()
HEAD = "# sk_a2: mix + the agent's reading tool"


def fresh(name, note):
    out = ROOT / "submissions" / name
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SRC, out)
    y = (SRC / "agent.yaml").read_text()
    assert y.count(HEAD) == 1
    (out / "agent.yaml").write_text(y.replace(HEAD, f"# {name} (2026-11-21): {note} (scripts/make_ska2_arms.py). sk_a2 was: mix + the agent's reading tool", 1))
    return out


def sub(text, a, b):
    assert text.count(a) == 1, a
    return text.replace(a, b)


def build():
    o = fresh("sk_a2g", "sk_a2 with temperature 1.0 / top_k 64")
    (o / "configs/sampling.yaml").write_text(sub(SAMP, "temperature: 0.2\n", "temperature: 1.0\ntop_k: 64\n"))
    o = fresh("sk_a2t", "sk_a2 with thinking 4096 / max output 8192")
    (o / "configs/sampling.yaml").write_text(sub(sub(SAMP, "max_output_tokens: 4096\n", "max_output_tokens: 8192\n"), "thinking_budget: 2048\n", "thinking_budget: 4096\n"))
    o = fresh("sk_a2e", "sk_a2 with evidc's search in the install call (names as positional_args)")
    sk = o / "skills/agent/scripts"
    (sk / "install.py").write_text(P.install_py())
    (sk / "where.py").write_text(P.where_py())
    (o / "skills/agent/SKILL.md").write_text(P.SKILL_MD)
    pr = (SRC / "prompts/system.md").read_text()
    pr = sub(pr, """Your first tool call is run_skill_script with skill_name agent and file_path scripts/install.py, and nothing else. It
puts your reading tool at .git/agent/a.py and prints READY.""", """Your first tool call is run_skill_script with skill_name agent, file_path scripts/install.py and positional_args holding
two to four exact names from the issue, one name per item, and nothing else. It puts your reading tool at .git/agent/a.py,
prints READY, then where those names are defined and test lines that use them.""")
    (o / "prompts/system.md").write_text(pr)
    for n in ("sk_a2g", "sk_a2t", "sk_a2e"):
        d = ROOT / "submissions" / n
        diff = [str(p.relative_to(d)) for p in d.rglob("*") if p.is_file() and (not (SRC / p.relative_to(d)).exists() or (SRC / p.relative_to(d)).read_bytes() != p.read_bytes())]
        print("wrote", n, "| files differing from sk_a2:", sorted(diff))


if __name__ == "__main__":
    build()
