"""Per-episode features for selection v2 (CPU, no model), over the WHOLE stage A corpus, plus stage B's replay check.

    python episode_features.py --episodes <dir> [<dir> ...] --tokenizer <dir with tokenizer.json> --out features.jsonl.gz

Why (SFT v1 diagnosis, docs/PLAN.md 2026-10-19): the fine-tuned 12B copied habits that do not fit our harness
(whole-file reads cut at 5,000 chars, broken shell one-liners, print-only "edits") and narrated instead of reasoning;
the v1 filters also removed every error-and-recovery example. One row per episode:
- thinking: steps, steps without thinking, thinking chars per step (thinking only; the visible text is NOT counted)
- fit to our limits: outputs over 5,000 chars (run_command) / over 150 lines or 10,000 chars (read_file)
- errors + recovery: failed calls (non-zero exit except a grep/find that only found nothing, tool errors, failed
  edits) and how many were followed by a DIFFERENT next call (changed course) vs the same call again
- edit style: edit_file/write_file vs sed -i / heredoc-or-python file writes vs print-only sed pipelines
- shell style: commands chaining 3+ steps with &&/;, inline multi-line python -c scripts
- replay_ok / replay_reason: stage B's own pre-check (Replay), so selection never picks what stage B would skip
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
from stage_b import OBSERVATION, OH_VIEW, Replay, numbered_lines, split_run_output  # noqa: E402

HARNESS = SimpleNamespace(max_stdout_chars=5000, max_file_lines=150, max_file_chars=10000)  # swegemma HarnessLimits
NO_MATCH = re.compile(r"^\s*(cd [^&;]+&&\s*)?(git\s+)?(grep|rg|find|ls)\b")
SED_I = re.compile(r"\bsed\s+(-[a-zA-Z]*i|--in-place)")
FILE_WRITE = re.compile(r"(cat\s*>\s*\S+\.(py|cfg|toml|txt|md|rst|json|ya?ml)\b|tee\s+\S+\.py\b|open\([^)]*['\"]w['\"])")
PRINT_SED = re.compile(r"\|\s*sed\s+(-e\s+)?['\"]s/")
CHAIN = re.compile(r"&&|;")


def call_failed(c):
    """(failed?, kind) for one teacher call, judged on what stage B shows our model."""
    tool, out = c["tool"], OBSERVATION.sub("", "" if c.get("output") is None else str(c["output"]))
    if tool == "run_command":
        text, code, timed_out = split_run_output(c)
        if timed_out:
            return True, "timeout"
        if code == 0:
            return False, None
        if code == 1 and NO_MATCH.search(c["args"].get("command", "")) and not text.strip():
            return False, None  # grep/find that found nothing: an answer, not an error
        return True, "command"
    if tool == "edit_file":
        return (not out.startswith("The file") or "has been edited" not in out[:300]), "edit"
    if tool == "read_file":
        return (out.startswith("ERROR") or "does not exist" in out[:300]), "read"
    if tool == "write_file":
        return (bool(out) and not out.startswith("File created successfully")), "write"
    return False, None


def output_over_limit(c):
    out = OBSERVATION.sub("", "" if c.get("output") is None else str(c["output"]))
    if c["tool"] == "run_command":
        text, _, _ = split_run_output(c)
        return len(text) > HARNESS.max_stdout_chars
    if c["tool"] == "read_file" and OH_VIEW.match(out):
        nums, _ = numbered_lines(out[OH_VIEW.match(out).end():])
        return len(nums) > HARNESS.max_file_lines or sum(len(v) + 1 for v in nums.values()) > HARNESS.max_file_chars
    return False


def features(ep, counter):
    steps = ep["steps"]
    calls = [c for s in steps for c in s["calls"]]
    think = [len(s.get("thinking") or "") for s in steps]
    f = {"id": ep["id"], "instance_id": ep["instance_id"], "teacher": ep["teacher"], "steps": len(steps),
         "calls": sum(1 for c in calls if c["tool"] != "submit_patch"),
         "steps_no_thinking": sum(1 for t in think if t == 0),
         "thinking_chars_per_step": round(sum(think) / max(len(steps), 1), 1),
         "min_step_thinking_chars": min(think) if think else 0}
    f["outputs_over_limit"] = sum(1 for c in calls if output_over_limit(c))
    errs, recovered, repeated_after_error, kinds = 0, 0, 0, Counter()
    for i, c in enumerate(calls):
        bad, kind = call_failed(c)
        if not bad:
            continue
        errs += 1
        kinds[kind] += 1
        nxt = calls[i + 1] if i + 1 < len(calls) else None
        if nxt is None:
            continue
        if nxt["tool"] == c["tool"] and nxt["args"] == c["args"]:
            repeated_after_error += 1
        else:
            recovered += 1
    f.update(errors=errs, errors_recovered=recovered, repeated_after_error=repeated_after_error,
             error_kinds=dict(kinds))
    cmds = [c["args"].get("command", "") for c in calls if c["tool"] == "run_command"]
    f.update(edit_tool=sum(1 for c in calls if c["tool"] in ("edit_file", "write_file")),
             sed_inplace=sum(1 for x in cmds if SED_I.search(x)),
             shell_file_write=sum(1 for x in cmds if FILE_WRITE.search(x)),
             print_only_sed=sum(1 for x in cmds if PRINT_SED.search(x) and not SED_I.search(x)),
             long_chains=sum(1 for x in cmds if len(CHAIN.findall(x)) >= 3),
             inline_python=sum(1 for x in cmds if re.search(r"python3?\s+-c\s+['\"][^'\"]*\n", x)),
             cat_whole_file=sum(1 for x in cmds if re.search(r"(^|&&|;)\s*cat\s+[\w./-]+\.py\s*($|&&|;|\|)", x)))
    try:
        Replay(ep, HARNESS, counter, 4096)
        f.update(replay_ok=True, replay_reason=None)
    except Exception as e:  # noqa: BLE001
        f.update(replay_ok=False, replay_reason=re.sub(r"\d+", "N", str(e))[:70])
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", nargs="+", required=True)
    ap.add_argument("--tokenizer", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(str(Path(a.tokenizer) / "tokenizer.json"))
    counter = SimpleNamespace(n=lambda t: len(tok.encode(t or "", add_special_tokens=False).ids))
    rows = []
    files = sorted(f for d in a.episodes for f in Path(d).rglob("episodes_*.jsonl"))
    with gzip.open(a.out, "wt") as fh:
        for k, path in enumerate(files):
            n0 = len(rows)
            for line in open(path):
                try:
                    r = features(json.loads(line), counter)
                except Exception as e:  # noqa: BLE001  one odd episode never stops the run
                    print(f"  skip a row in {path.name}: {e!r}"[:200], flush=True)
                    continue
                rows.append(r)
                fh.write(json.dumps(r) + "\n")
            print(f"[{k + 1}/{len(files)}] {path.name}: {len(rows) - n0} episodes (total {len(rows)})", flush=True)

    n = len(rows)
    pct = lambda k: f"{k} ({100 * k / max(n, 1):.0f}%)"  # noqa: E731
    print(f"\n==== {n} episodes -> {a.out}")
    print("replay ok:", pct(sum(r["replay_ok"] for r in rows)), "| reasons:",
          dict(Counter(r["replay_reason"] for r in rows if not r["replay_ok"]).most_common(6)))
    print("no output over our limits:", pct(sum(r["outputs_over_limit"] == 0 for r in rows)),
          "| <=1:", pct(sum(r["outputs_over_limit"] <= 1 for r in rows)))
    print("thinking in every step:", pct(sum(r["steps_no_thinking"] == 0 for r in rows)),
          "| >=600 chars/step (~150 tokens):", pct(sum(r["thinking_chars_per_step"] >= 600 for r in rows)))
    print("with >=1 error:", pct(sum(r["errors"] >= 1 for r in rows)), "| >=1 recovered:",
          pct(sum(r["errors_recovered"] >= 1 for r in rows)), "| repeated a failed call:",
          pct(sum(r["repeated_after_error"] >= 1 for r in rows)))
    print("edits only via edit_file/write_file:", pct(sum(r["edit_tool"] >= 1 and r["sed_inplace"] == 0
                                                          and r["shell_file_write"] == 0 for r in rows)),
          "| print-only sed:", pct(sum(r["print_only_sed"] >= 1 for r in rows)))
    print("no long && chains:", pct(sum(r["long_chains"] == 0 for r in rows)),
          "| no inline multi-line python -c:", pct(sum(r["inline_python"] == 0 for r in rows)),
          "| no cat of a whole .py:", pct(sum(r["cat_whole_file"] == 0 for r in rows)))
    good = [r for r in rows if r["replay_ok"] and r["outputs_over_limit"] == 0 and r["steps_no_thinking"] == 0
            and r["thinking_chars_per_step"] >= 600 and r["print_only_sed"] == 0]
    print("ALL of: replay ok, no output over limits, thinking every step >=600 chars/step, no print-only sed:",
          pct(len(good)), "| of those with a recovered error:", sum(r["errors_recovered"] >= 1 for r in good),
          "| by teacher:", dict(Counter(r["teacher"] for r in good)))


if __name__ == "__main__":
    main()
