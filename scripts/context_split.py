"""What fills an agent's context, and what its time goes to.

Usage: python3 scripts/context_split.py RUN_DIR [RUN_DIR ...] [--author NAME]
Context = tool results (observations) the agent receives, in characters, by kind of command.
Time/output = output tokens the agent writes, by kind of tool call.
"""
import collections
import json
import re
import sys
from pathlib import Path


def kind(name, cmd):
    if name != "run_command":
        return name or "?"
    c = cmd.strip()
    if re.match(r"cat >+ /tmp/\S+", c) or c.startswith("python - <<") or c.startswith("python3 - <<"):
        return "write+run script"
    if "pytest" in c:
        return "pytest"
    if re.match(r"python3? /tmp", c) or c.startswith("python -c"):
        return "run script"
    if "sed -n" in c or c.startswith("cat ") or c.startswith("head") or c.startswith("tail"):
        return "read lines (sed/cat)"
    if "grep" in c or c.startswith("find") or c.startswith("git ls-files"):
        return "search"
    if c.startswith("git log") or c.startswith("git show") or c.startswith("git blame"):
        return "git history"
    if c.startswith("git status") or c.startswith("git diff"):
        return "git status/diff"
    return "other"


args = [a for a in sys.argv[1:] if not a.startswith("--")]
author = sys.argv[sys.argv.index("--author") + 1] if "--author" in sys.argv else None
obs = collections.Counter(); out = collections.Counter(); n = collections.Counter(); tasks = 0
for run in args:
    for f in sorted(Path(run).glob("traces/*.json")):
        tasks += 1
        for s in json.loads(f.read_text())["steps"]:
            who = (s.get("extra") or {}).get("author")
            if author and who != author:
                continue
            tcs = s.get("tool_calls") or []
            if not tcs:
                continue
            a = tcs[0].get("arguments") if isinstance(tcs[0].get("arguments"), dict) else {}
            k = kind(tcs[0].get("function_name"), a.get("command", "") or "")
            n[k] += 1
            out[k] += (s.get("metrics") or {}).get("completion_tokens") or 0
            obs[k] += len(json.dumps(s.get("observation") or {}))
T = sum(obs.values()); O = sum(out.values())
print(f"{tasks} task runs; context added {T / 1000:.0f}k chars (~{T / 3.2 / tasks:,.0f} tokens per task); output {O:,} tokens")
print(f"{'kind':24}{'calls':>6}{'ctx share':>10}{'ctx chars/call':>15}{'out share':>10}{'out tok/call':>13}")
for k, v in sorted(obs.items(), key=lambda x: -x[1]):
    print(f"{k:24}{n[k]:6}{v / T:10.0%}{v // n[k]:15,}{out[k] / max(O, 1):10.0%}{out[k] // n[k]:13}")
