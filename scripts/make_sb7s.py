"""sb7s = sb7 with a history stage that stops (user 2026-11-18: 'yes build the sb7 retry'). Run: python3 -I scripts/make_sb7s.py

r113: sb7's history stage ran in 8/8 and its output reached the fixer in 8/8, but it stopped after its one command in
only 2/8 (14-31 requests, mean 123 s) and one copy of the 15-line command lost a quote. sb7s changes ONLY the history
stage's prompt (scripts/agent_sb7s/history.md, written fresh):
  - the command's own output ends with '== HISTORY DONE: reply with everything above this line exactly as printed,
    and make no other call.' (a tool-output instruction: memory event-triggered-rules-only, sb5's NEXT line 2/3);
  - the command is shorter (10 lines vs 15; pathspec excludes instead of a grep -v filter; def / class line first);
  - worked examples for every case: normal output -> reply, no names -> reply, command error -> reply.
Everything else is sb7's byte for byte (agent.yaml body, history.yaml, fixer.yaml, prompts/system.md, configs, eval_config)."""
import importlib.util
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("make_sb78", ROOT / "scripts/make_sb78.py")
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)
SRC, OUT = ROOT / "submissions/sb7", ROOT / "submissions/sb7s"
DONE = "== HISTORY DONE: reply with everything above this line exactly as printed, and make no other call."


def main():
    p = (ROOT / "scripts/agent_sb7s/history.md").read_text()
    M.check(p)
    M.examples(p)
    cmd = next(b for b in re.findall(r"```\n(.*?)```", p, re.S) if b.startswith("names="))
    assert cmd.rstrip().endswith("echo '" + DONE + "'"), "the command prints the stop line last"
    assert len(cmd.strip().splitlines()) <= 10
    pairs = re.findall(r"(?:stdout was|printed):\n```\n(.*?)```\nYour reply, with no tool call, is everything above the HISTORY DONE line:\n(.*?)(?:\n\nExample|\Z)", p, re.S)
    assert len(pairs) == 2, len(pairs)
    for out, rep in pairs:
        assert out.rstrip().endswith(DONE)
        assert out[:out.index(DONE)].strip() == rep.strip(), "reply = everything above the stop line"
    err = re.search(r"error message was:\n```\n(.*?)```\nYour reply, with no tool call, is that message exactly:\n(.*?)\Z", p, re.S)
    assert err and err.group(1).strip() == err.group(2).strip(), "error case shown"
    assert "You run one command before the engineer starts" in p  # stage detection in the analysis scripts
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SRC, OUT)
    (OUT / "prompts/history.md").write_text(p)
    first, rest = (SRC / "agent.yaml").read_text().split("\n", 1)
    assert first.startswith("# sb7 (2026-11-18)")
    (OUT / "agent.yaml").write_text("# sb7s (2026-11-18): sb7 with a history stage that stops (stop line in its command output, shorter command; scripts/make_sb7s.py)\n" + rest)
    files = lambda d: sorted(q.relative_to(d).as_posix() for q in d.rglob("*") if q.is_file())
    assert files(OUT) == files(SRC)
    for f in files(SRC):
        if f not in ("agent.yaml", "prompts/history.md"):
            assert (OUT / f).read_bytes() == (SRC / f).read_bytes(), f
    print("wrote submissions/sb7s | history prompt words", len(p.split()), "| command lines", len(cmd.strip().splitlines()))


if __name__ == "__main__":
    main()
