"""One compact stats row per stage A episode (for selection without downloading the episodes themselves).

    python export_stats.py --episodes <dir> [<dir> ...] --tokenizer <dir with tokenizer.json> --out stats.jsonl.gz

Per episode: where it is (batch file + line, to fetch it later), task + teacher, quality stats from stage A, exact
Gemma token counts (thinking per step, everything the model writes, a rough prompt size) and, for tasks that several
teachers solved, how similar this run's actions are to the others (Jaccard of normalized actions), so the user's
dedup rule ("a second run of a task only if it is really different") can be applied at selection time.
Nothing is deleted or rewritten: the episodes stay as they are.
"""
import argparse
import gzip
import json
import re
from collections import defaultdict
from pathlib import Path

from tokenizers import Tokenizer


def action_signature(ep):
    """Normalized set of actions: tool + file / command head, ignoring line numbers and quoting details."""
    sig = set()
    for s in ep["steps"]:
        for c in s["calls"]:
            a = c["args"]
            if c["tool"] == "run_command":
                cmd = re.sub(r"\d+", "N", a.get("command", ""))
                cmd = re.sub(r"\s+", " ", cmd).strip()[:120]
                sig.add(("run", cmd))
            elif c["tool"] in ("read_file", "edit_file", "write_file"):
                sig.add((c["tool"], a.get("filepath", "")))
            else:
                sig.add((c["tool"],))
    return sig


def patch_files(patch):
    return sorted({l.split(" b/")[-1] for l in (patch or "").splitlines() if l.startswith("diff --git")})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", nargs="+", required=True)
    ap.add_argument("--tokenizer", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    tok = Tokenizer.from_file(str(Path(a.tokenizer) / "tokenizer.json"))
    n = lambda text: len(tok.encode(text or "", add_special_tokens=False).ids)  # noqa: E731

    rows, sigs = [], {}
    files = sorted(f for d in a.episodes for f in Path(d).rglob("episodes_*.jsonl"))
    for f in files:
        for line_no, line in enumerate(open(f)):
            ep = json.loads(line)
            think = [n(s["thinking"]) for s in ep["steps"]]
            written = sum(think) + sum(n(s["text"]) + sum(n(json.dumps(c["args"])) for c in s["calls"])
                          for s in ep["steps"])
            outputs = sum(n(str(c.get("output") or "")[:5000]) for s in ep["steps"] for c in s["calls"])
            r = {
                "id": ep["id"], "file": f.name, "line": line_no, "instance_id": ep["instance_id"], "repo": ep["repo"],
                "teacher": ep["teacher"], "category": ep.get("category"), "source_dataset": ep.get("source_dataset"),
                **ep["stats"],
                "thinking_tokens": sum(think), "max_step_thinking_tokens": max(think),
                "steps_over_2048": sum(1 for t in think if t > 2048),
                "steps_over_4096": sum(1 for t in think if t > 4096),
                "written_tokens": written,
                # rough size of the whole run as one sample: task + tree + everything written + tool outputs
                # (outputs capped at the harness's 5,000-character limit); the system prompt is added later
                "approx_tokens": written + outputs + n(ep.get("problem_statement")) + n(ep.get("workspace_tree")),
                "has_tree": bool(ep.get("workspace_tree")), "has_issue": bool(ep.get("problem_statement")),
                "submitted": ep.get("submitted"), "patch_files": patch_files(ep.get("model_patch")),
            }
            rows.append(r)
            sigs[ep["id"]] = action_signature(ep)
        print(f"{f.name}: {len(rows)} episodes so far", flush=True)

    by_task = defaultdict(list)
    for r in rows:
        by_task[r["instance_id"]].append(r["id"])
    for r in rows:
        others = [o for o in by_task[r["instance_id"]] if o != r["id"]]
        s = sigs[r["id"]]
        r["runs_of_task"] = len(others) + 1
        r["max_jaccard_same_task"] = max((len(s & sigs[o]) / max(len(s | sigs[o]), 1) for o in others), default=0.0)
    with gzip.open(a.out, "wt") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    print(f"wrote {len(rows)} rows, {len(by_task)} distinct tasks -> {a.out}")


if __name__ == "__main__":
    main()
