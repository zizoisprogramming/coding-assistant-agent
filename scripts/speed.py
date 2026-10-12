"""Per-task speed from traces: agent steps, last-step time, median gap between steps, output tokens, tokens/s,
first edit time, and silent stalls (task ran on long after its last recorded step).

    python3 scripts/speed.py data/results/<run>/<config> [more config dirs ...]
"""
import ast
import glob
import json
import os
import statistics
import sys


def _d(v):
    return ast.literal_eval(v) if isinstance(v, str) else (v or {})


def first_edit(steps):
    for x in steps:
        tc = str(x.get("tool_calls") or "")
        if "'edit_file'" in tc or "'write_file'" in tc or "sed -i" in tc or ".write(s.replace" in tc:
            return _d(x.get("extra")).get("elapsed_s")
    return None


def main():
    for d in sys.argv[1:]:
        durations = {}
        tr = os.path.join(d, "task_results.jsonl")
        if os.path.exists(tr):
            durations = {json.loads(l)["instance_id"]: json.loads(l)["duration_seconds"] for l in open(tr)}
        for f in sorted(glob.glob(d + "/traces/*.json")):
            task = f.split("trace_")[1][:-5]
            steps = json.load(open(f))["steps"]
            ag = [(_d(x.get("extra")).get("elapsed_s"), _d(x.get("metrics")).get("completion_tokens") or 0)
                  for x in steps if x.get("source") == "agent"]
            ag = [a for a in ag if a[0] is not None]
            if len(ag) < 2:
                continue
            gaps = [b[0] - a[0] for a, b in zip(ag, ag[1:])]
            out = sum(a[1] for a in ag)
            end = ag[-1][0]
            fe = first_edit(steps)
            silent = durations.get(task, end) - end
            print(f"{os.path.basename(d):14} {task:14} steps {len(ag):3}  last {end:4.0f}s  med gap {statistics.median(gaps):4.1f}s  "
                  f"out_tok {out:6}  tok/s {out / end:5.1f}  first edit {('%4.0fs' % fe) if fe else '  — '}"
                  + (f"  SILENT {silent:.0f}s" if silent > 60 else ""))


if __name__ == "__main__":
    main()
