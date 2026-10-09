"""Behaviour patterns in 1b traces (complements analyze.py).

Usage: python3 scripts/patterns.py RUN_DIR [RUN_DIR ...]   (a RUN_DIR holds traces/ and task_results.jsonl)

Per task: resolved, first helper call / first edit (s), repro.py rewrites, longest identical back-to-back
command streak, compactions and what the orchestrator did right after each, and notes.md use.
Totals: helper calls with mean seconds and inner tool calls, notes lines appended by tag.
"""

import collections
import json
import re
import sys
from pathlib import Path

HELPERS = ("reader", "executor", "verifier")


def args_of(tc):
    a = tc.get("arguments")
    return a if isinstance(a, dict) else {}


def after_compaction(cmds):
    """Classify the orchestrator's first commands after a compaction."""
    text = " ".join(cmds)
    if "test -s /tmp/notes.md" in text:
        return "resume-check"
    if re.search(r"cat > /tmp/notes\.md", text):
        return "RESTART(notes overwritten)"
    if re.search(r"git (ls-files|grep)", text):
        return "re-search"
    return "continue"


def task_patterns(trace):
    steps = json.loads(trace.read_text())["steps"]
    t0 = next(s["extra"]["timestamp"] for s in steps if (s.get("extra") or {}).get("timestamp"))
    out = collections.Counter()
    first_helper = first_edit = None
    streak = best = 0
    best_cmd = last = None
    prev_in = 0
    compactions = []  # list of lists of the next orchestrator commands
    helper_calls = []  # (name, start, inner calls, seconds or None)
    cur = None
    for s in steps:
        ex = s.get("extra") or {}
        who, t = ex.get("author"), ex.get("timestamp")
        pin = (s.get("metrics") or {}).get("prompt_tokens") or 0
        if who == "orchestrator" and pin:
            if prev_in and pin < prev_in - 3000:
                compactions.append([])
            prev_in = pin
        for tc in s.get("tool_calls") or []:
            name, a = tc.get("function_name"), args_of(tc)
            cmd = a.get("command", "") or ""
            key = (who, name, json.dumps(a, sort_keys=True))
            streak = streak + 1 if key == last else 1
            last = key
            if streak > best:
                best, best_cmd = streak, f"{who}: {(cmd or name)[:70]!r}"
            if who == "orchestrator":
                if compactions and len(compactions[-1]) < 3:
                    compactions[-1].append(cmd or name)
                if re.match(r"cat >+ /tmp/repro", cmd):
                    out["repro_writes"] += 1
                if name in HELPERS:
                    if cur:
                        helper_calls.append((cur[0], cur[1], cur[2], None))
                    cur = [name, t, 0]
                    if first_helper is None and t:
                        first_helper = round(t - t0)
            elif who in HELPERS and cur:
                cur[2] += 1
            if (name in ("edit_file", "write_file") or "open(p, 'w')" in cmd) and first_edit is None and t:
                first_edit = round(t - t0)
            if re.search(r"(?<!test -s )cat > /tmp/notes\.md", cmd) and "test -s /tmp/notes.md" not in cmd:
                out["notes_overwrite"] += 1
            if "test -s /tmp/notes.md" in cmd:
                out["notes_resume_cmd"] += 1
            for tag in re.findall(r"echo ['\"](\w+):[^>]*>> /tmp/notes\.md", cmd):
                out[f"{who[:4]}+{tag}"] += 1
            if re.search(r"(cat|grep|tail) [^>]*/tmp/notes\.md", cmd) and ">" not in cmd.split("/tmp/notes.md")[0][-3:]:
                out[f"{who[:4]}_reads_notes"] += 1
        tn = ((s.get("observation") or {}).get("extra") or {}).get("tool_name")
        if cur and tn == cur[0] and t:
            helper_calls.append((cur[0], cur[1], cur[2], t - cur[1]))
            cur = None
    if cur:
        helper_calls.append((cur[0], cur[1], cur[2], None))
    return {
        "first_helper": first_helper, "first_edit": first_edit, "streak": best, "streak_cmd": best_cmd,
        "compactions": [after_compaction(c) for c in compactions], "counts": out, "helpers": helper_calls,
    }


def main(run_dirs):
    tags = collections.Counter()
    helpers = collections.defaultdict(list)
    for run in map(Path, run_dirs):
        res = {}
        for line in (run / "task_results.jsonl").read_text().splitlines():
            d = json.loads(line)
            res[d["instance_id"]] = d
        print(f"## {run.name}: {sum(d['resolved'] for d in res.values())}/{len(res)} resolved")
        for trace in sorted((run / "traces").glob("trace_*.json")):
            tid = trace.stem.removeprefix("trace_")
            p = task_patterns(trace)
            r = res.get(tid, {})
            c = p["counts"]
            tags.update(c)
            for name, _, inner, sec in p["helpers"]:
                helpers[name].append((inner, sec))
            notes = {k: v for k, v in c.items() if "notes" in k or "+" in k}
            print(f"{tid:14} {'OK' if r.get('resolved') else '--'} {round(r.get('duration_seconds', 0)):4}s "
                  f"helper@{p['first_helper']} edit@{p['first_edit']} repro×{c['repro_writes']} "
                  f"streak {p['streak']} {p['streak_cmd'] if p['streak'] >= 5 else ''}")
            print(f"{'':17}compactions→{p['compactions']} notes {notes}")
    print("\n## totals")
    for name, v in helpers.items():
        secs = [s for _, s in v if s is not None]
        print(f"{name:9} calls {len(v):3}  mean {sum(secs) / max(len(secs), 1):4.0f}s  "
              f"inner calls {sorted(i for i, _ in v)}  no reply {sum(s is None for _, s in v)}")
    print("notes:", dict(sorted((k, v) for k, v in tags.items() if "notes" in k or "+" in k)))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
