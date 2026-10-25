"""Compact copy of the FAILED runs of generation outputs, for reading them locally (failure-pattern analysis).

    python3 scripts/export_failed.py GEN_DIR [GEN_DIR ...] --out failed.jsonl.gz

A request log repeats the whole conversation in every line (~1.6 GB for all runs). Per failed run this keeps only the
records that hold the conversation once: the last model call before each compaction (the summary drops the history
after it) and the run's last call, each with the model's reply; the tool schema is dropped. Plus the run's result row
and its patch. One JSON line per run. Public tasks (level 'public') are all kept: their grades were redone after the
run (re-grade), so `resolved` here is not final.
"""
import argparse
import gzip
import json
import sys
from pathlib import Path

SUMMARY_PREFIX = "The following is a conversation history"


def is_summary(rec):
    msgs = rec["request"].get("messages") or []
    last = msgs[-1] if msgs else {}
    return last.get("role") == "user" and str(last.get("content") or "").startswith(SUMMARY_PREFIX)


def slim(rec):
    req = {k: v for k, v in rec["request"].items() if k != "tools"}
    return {"t": rec.get("t"), "seconds": rec.get("seconds"), "request": req, "reply": rec.get("reply")}


def export(gen_dir, fh):
    gen_dir = Path(gen_dir)
    rows = {f"{r['instance_id']}#a{r['attempt']}": r for r in map(json.loads, open(gen_dir / "results/gen_per_task.jsonl"))}
    want = {j for j, r in rows.items() if not r.get("resolved") or r.get("level") == "public"}
    prev, kept, n_calls, bad = {}, {}, {}, 0
    with open(gen_dir / "requests/requests.jsonl") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except ValueError:
                bad += 1
                continue
            job = rec.get("job")
            if job not in want or not isinstance(rec.get("request"), dict):
                continue
            n_calls[job] = n_calls.get(job, 0) + 1
            if is_summary(rec):
                if job in prev:  # the history the summary is about to replace
                    kept.setdefault(job, []).append(prev.pop(job))
                kept.setdefault(job, []).append({"summary_call": True, "t": rec.get("t"), "seconds": rec.get("seconds"),
                                                 "summary": ((rec.get("reply") or {}).get("message") or {}).get("content")})
            else:
                prev[job] = slim(rec)
    n = 0
    for job in sorted(want):
        recs = kept.get(job, []) + ([prev[job]] if job in prev else [])
        if not recs:
            continue
        r = rows[job]
        pf = gen_dir / "results/gen/patches" / f"{r['instance_id']}__a{r['attempt']}.diff"
        fh.write(json.dumps({"job": job, "src": gen_dir.name, "row": r, "patch": pf.read_text() if pf.exists() else None,
                             "model_calls": n_calls.get(job, 0), "records": recs}) + "\n")
        n += 1
    print(f"{gen_dir}: {n} runs exported of {len(rows)} ({len(want)} failed or public)"
          + (f", {bad} unreadable log lines" if bad else ""), file=sys.stderr, flush=True)
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    with gzip.open(a.out, "wt") as fh:
        for d in a.dirs:
            export(d, fh)


if __name__ == "__main__":
    main()
