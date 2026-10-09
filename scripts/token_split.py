"""Where output tokens and model time go, per agent and per kind of reply.

Usage: python3 scripts/token_split.py RUN_DIR [RUN_DIR ...]
A reply is 'text' (no tool call), or a tool call classified by what it writes. Seconds = time from the previous
step to this one (the model's generation time plus the previous tool's run time).
"""
import collections
import json
import re
import sys
from pathlib import Path


def kind(s):
    tcs = s.get("tool_calls") or []
    if not tcs:
        return "text reply"
    tc = tcs[0]
    name = tc.get("function_name")
    a = tc.get("arguments") if isinstance(tc.get("arguments"), dict) else {}
    cmd = a.get("command", "") or ""
    if name in ("reader", "executor", "verifier"):
        return f"request to {name}"
    if re.match(r"cat >+ /tmp/", cmd) or cmd.startswith("python - <<"):
        return "write script / py-edit"
    if name in ("edit_file", "write_file"):
        return name
    return "short command"


for run in sys.argv[1:]:
    tok = collections.Counter(); n = collections.Counter(); sec = collections.Counter(); text = collections.Counter()
    for f in sorted(Path(run).glob("traces/*.json")):
        prev = None
        for s in json.loads(f.read_text())["steps"]:
            ex = s.get("extra") or {}
            t = ex.get("timestamp")
            m = s.get("metrics") or {}
            out = m.get("completion_tokens")
            if out is None or s.get("source") != "agent":
                prev = t or prev
                continue
            k = (ex.get("author", "?"), kind(s))
            tok[k] += out; n[k] += 1
            if t and prev:
                sec[k] += t - prev
            msg = s.get("message")
            msg = msg if isinstance(msg, str) else json.dumps(msg or "")
            text[k] += len(msg.strip().strip('"'))
            prev = t or prev
    print(f"## {run}")
    print(f"{'agent':13}{'kind':26}{'n':>4}{'out tok':>9}{'tok/call':>9}{'text chars':>11}{'sec':>6}")
    for k, v in sorted(tok.items(), key=lambda x: -x[1]):
        print(f"{k[0]:13}{k[1]:26}{n[k]:4}{v:9}{v // n[k]:9}{text[k]:11}{sec[k]:6.0f}")
