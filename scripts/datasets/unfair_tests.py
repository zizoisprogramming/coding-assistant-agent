"""Unfair-test check (user 2026-10-20: drop them all). A task is unfair when its tests require a name that the fix
creates and that the task text never mentions: nobody could guess it (OOD-45's interface_hint / spec_added cases).

New names = public functions / classes / methods the gold patch defines, parameters it adds to a signature, new
UPPER_CASE module constants and new self.<attr> attributes, none of which appear in the removed lines (so they did not
exist before). Local variables inside new functions are ignored (tests rarely need them; they caused false hits).
Required = such a name appearing as a word in the lines the test patch adds. Unfair = required and not in the text.
Text = whatever text the task will show (issue or PR text); call unfair_names(patch, test_patch, text).

    .venv/bin/python scripts/datasets/unfair_tests.py     # shares on the public 129, OOD-45 and our candidates
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEF_RE = re.compile(r"^\s*(?:async\s+)?(?:def|class)\s+([A-Za-z_]\w*)")
SIG_RE = re.compile(r"^\s*(?:async\s+)?def\s+\w+\s*\((.*)")
CONST_RE = re.compile(r"^([A-Z][A-Z0-9_]+)\s*(?::[^=]+)?=(?!=)")  # module-level constant (column 0, UPPER_CASE)
ATTR_RE = re.compile(r"^\s+self\.([A-Za-z_]\w*)\s*(?::[^=]+)?=(?!=)")  # new public attribute
COMMON = {"self", "cls", "args", "kwargs", "value", "name", "data", "result", "key", "default", "kind", "other", "item",
          "text", "path", "obj", "func", "msg", "message", "options", "config", "params", "response", "request"}


BUILTINS = set(dir(__builtins__)) | {"None", "True", "False"}


def _lines(patch, sign):
    return [l[1:] for l in patch.splitlines() if l.startswith(sign) and not l.startswith(sign * 3)]


def new_names(patch):
    added, removed = _lines(patch, "+"), "\n".join(_lines(patch, "-"))
    names = set()
    for l in added:
        for rx in (DEF_RE, CONST_RE, ATTR_RE):
            m = rx.match(l)
            if m:
                names.add(m.group(1))
        m = SIG_RE.match(l)
        if m:
            names |= set(re.findall(r"([A-Za-z_]\w*)\s*(?::|=|,|\))", m.group(1)))
    return {n for n in names if len(n) > 3 and n not in COMMON and not n.startswith("_") and n not in BUILTINS
            and not re.search(rf"\b{re.escape(n)}\b", removed)}


def unfair_names(patch, test_patch, text):
    tests = "\n".join(_lines(test_patch, "+"))
    return sorted(n for n in new_names(patch) if re.search(rf"\b{re.escape(n)}\b", tests)
                  and not re.search(rf"\b{re.escape(n)}\b", text or ""))


def main():
    sets = {"public 129": [json.loads(l) for l in open(ROOT / "data/tasks.jsonl")],
            "rebench candidates (issue text)": [json.loads(l) for l in open(ROOT / "data/swe_rebench/candidates.jsonl")]}
    ood = Path("/private/tmp/claude-501/-Users-ziadsamer-Projects-coding-assistant-agent/dc5492bf-0111-4855-a10b-f0d9e102b4f0/scratchpad/ood45_dl/tasks.jsonl")
    if ood.exists():
        rows = [json.loads(l) for l in open(ood)]
        sets["OOD-45 rewritten"] = rows
        print("OOD-45 author's labels: interface_hint or spec_added =",
              sum(1 for r in rows if r.get("interface_hint") or r.get("spec_added")), "/ 45")
    for name, rows in sets.items():
        hits = [(r["instance_id"], unfair_names(r["patch"], r["test_patch"], r["problem_statement"])) for r in rows]
        bad = [h for h in hits if h[1]]
        print(f"{name:34} unfair {len(bad):4}/{len(rows):<5} ({100 * len(bad) / len(rows):3.0f}%) e.g. {bad[:3]}")


if __name__ == "__main__":
    main()
