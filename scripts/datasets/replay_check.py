"""Stage B pre-checks over the WHOLE corpus (CPU, no model): which episodes our harness can show faithfully.
Nothing is deleted: writes one row per episode that fails, so selection (select_v1.py) can skip them like the sandbox
flags. Same checks stage B runs before replaying (scripts/datasets/stage_b.py, Replay):
- the teacher's next 2 steps use a name it saw only in output our limits would cut (5,000 chars / 150 lines / 10,000);
- file tool paths our harness refuses (outside /workspace, e.g. /tmp); read ranges past the end of the file;
  teacher views/edits we cannot rebuild; episodes not ending with submit_patch;
- a step writing more than max_output_tokens (4,096) tokens.

    python replay_check.py --episodes <dir> [<dir> ...] --tokenizer <dir with tokenizer.json> --out replay_flags.jsonl.gz
"""
import argparse
import gzip
import json
import re
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stage_b import Replay  # noqa: E402

HARNESS = SimpleNamespace(max_stdout_chars=5000, max_file_lines=150, max_file_chars=10000)  # swegemma HarnessLimits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", nargs="+", required=True)
    ap.add_argument("--tokenizer", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-output-tokens", type=int, default=4096)
    a = ap.parse_args()
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(str(Path(a.tokenizer) / "tokenizer.json"))
    counter = SimpleNamespace(n=lambda t: len(tok.encode(t or "", add_special_tokens=False).ids))
    n = bad = 0
    reasons = Counter()
    files = sorted(f for d in a.episodes for f in Path(d).rglob("episodes_*.jsonl"))
    with gzip.open(a.out, "wt") as fh:
        for f in files:
            for line in open(f):
                ep = json.loads(line)
                n += 1
                try:
                    Replay(ep, HARNESS, counter, a.max_output_tokens)
                    continue
                except Exception as e:  # noqa: BLE001
                    reason = re.sub(r"\d+", "N", str(e))[:70]
                bad += 1
                reasons[reason] += 1
                fh.write(json.dumps({"id": ep["id"], "instance_id": ep["instance_id"], "reason": reason}) + "\n")
            print(f"{f.name}: {n} episodes, {bad} fail", flush=True)
    print(f"{n} episodes, {bad} fail the replay checks ({100 * bad / max(n, 1):.1f}%) -> {a.out}")
    for r, c in reasons.most_common():
        print(f"  {c:6}  {r}")


if __name__ == "__main__":
    main()
