"""sb1pp05 / sb1pp15 = sb1 with presence_penalty 0.5 / 1.5 (user 2026-11-18: 'yes build the penalty trial').
Run: python3 -I scripts/make_sb1pp.py

Target: long hand-tracing replies (sb1, 112 runs: replies >= 60 s hold 29% of model time, 70% on rich_3521; ~11
'Wait / Actually' per long reply, r112). Thinking caps backfired (r13, r111). presence_penalty is a submission field
(adk_submission limits: no field list) and ADK forwards it to LiteLLM / vLLM (google/adk/models/lite_llm.py); vLLM
applies it to the reply's own output tokens, thinking included: a flat logit cut for every token already generated
in the reply, so repeated 'Wait' / re-derivations get less likely. Basis: NoWait (arXiv 2506.08343: suppressing
reflection tokens cuts reasoning 27-51% with accuracy kept); 1.5 = the community value against endless repetition
in Qwen thinking mode (Unsloth, secondary; Qwen's own vLLM page shows 1.5 with thinking off, and warns of language
mixing and a slight quality drop at high values). frequency_penalty is NOT used: it grows with each repeat, and a long
reply repeats spaces / newlines / indentation hundreds of times, so it would wreck the code in edits.
Only configs/sampling.yaml changes (one added line) and the agent.yaml comment; everything else is sb1's byte for byte."""
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "submissions/sb1"
DOSES = {"sb1pp05": 0.5, "sb1pp15": 1.5}


def main():
    samp = (SRC / "configs/sampling.yaml").read_text()
    assert samp.startswith("temperature: 0.2\ntop_p: 0.95\n") and "penalty" not in samp
    first, rest = (SRC / "agent.yaml").read_text().split("\n", 1)
    assert first.startswith("# sb1 (2026-11-16)")
    files = lambda d: sorted(q.relative_to(d).as_posix() for q in d.rglob("*") if q.is_file())
    for name, dose in DOSES.items():
        out = ROOT / "submissions" / name
        if out.exists():
            shutil.rmtree(out)
        shutil.copytree(SRC, out)
        new = samp.replace("top_p: 0.95\n", f"top_p: 0.95\npresence_penalty: {dose}\n", 1)
        (out / "configs/sampling.yaml").write_text(new)
        (out / "agent.yaml").write_text(f"# {name} (2026-11-18): sb1 with presence_penalty {dose} against long repetitive thinking (scripts/make_sb1pp.py)\n" + rest)
        assert files(out) == files(SRC)
        for f in files(SRC):
            if f not in ("agent.yaml", "configs/sampling.yaml"):
                assert (out / f).read_bytes() == (SRC / f).read_bytes(), f
        diff = [l for l in new.splitlines() if l not in samp.splitlines()]
        assert diff == [f"presence_penalty: {dose}"], diff
        print("wrote", out.relative_to(ROOT), "| sampling change:", diff)


if __name__ == "__main__":
    main()
