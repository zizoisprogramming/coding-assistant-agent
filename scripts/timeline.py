"""Where each task's time went, by phase, plus the model's thought at chosen steps.

Usage: python3 scripts/timeline.py RUN_DIR [RUN_DIR ...] [--thoughts]
Phase of a step = kind of its tool call; seconds = time from the previous step to this one (thinking + writing).
"""
import collections
import json
import re
import sys
from pathlib import Path


def kind(name, cmd):
    if name in ("edit_file", "write_file") or "open(p, 'w')" in cmd:
        return "edit"
    if re.match(r"cat >+ /tmp/", cmd.strip()) or cmd.strip().startswith(("python - <<", "python3 - <<")):
        return "write script"
    if name == "read_file" or re.search(r"sed -n|^cat |^head|^tail", cmd.strip()):
        return "read"
    if "grep" in cmd or cmd.strip().startswith(("find", "git ls-files", "git log", "git show")):
        return "search"
    if "pytest" in cmd or re.match(r"python3? (/tmp|-c)", cmd.strip()):
        return "run script/tests"
    return name or "other"


show = "--thoughts" in sys.argv
for run in [a for a in sys.argv[1:] if not a.startswith("--")]:
    for f in sorted(Path(run).glob("traces/*.json")):
        steps = json.loads(f.read_text())["steps"]
        t0 = next(s["extra"]["timestamp"] for s in steps if (s.get("extra") or {}).get("timestamp"))
        prev = t0; sec = collections.Counter(); n = collections.Counter(); first_edit = None; seq = []
        for s in steps:
            t = (s.get("extra") or {}).get("timestamp")
            tcs = s.get("tool_calls") or []
            if s.get("source") == "agent" and tcs and t:
                a = tcs[0].get("arguments") if isinstance(tcs[0].get("arguments"), dict) else {}
                k = kind(tcs[0].get("function_name"), a.get("command", "") or "")
                d = t - prev
                sec[k] += d; n[k] += 1
                if k == "edit" and first_edit is None:
                    first_edit = round(t - t0)
                seq.append(k[0].upper() if k != "run script/tests" else "T")
                if show and d > 15:
                    msg = s.get("message"); msg = msg if isinstance(msg, str) else json.dumps(msg or "")
                    print(f"      [{t - t0:5.0f}s, {d:4.0f}s thinking, then {k}] {msg[:260]!r}")
            if t:
                prev = t
        total = sum(sec.values())
        parts = ", ".join(f"{k} {v:.0f}s/{n[k]}" for k, v in sorted(sec.items(), key=lambda x: -x[1]))
        print(f"{run.split('/')[-1]} {f.stem[6:]:14} first edit {first_edit}s | {parts} | sequence {''.join(seq)}")
