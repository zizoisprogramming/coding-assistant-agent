"""r87 arms (user 2026-11-12 "yes 2 and 3" after MINING 2026-11-12e NO PATCH). Run: python3 scripts/make_r87_arms.py

Mining: fixer prompts with the call plan ('28 tool calls and 8 minutes', 'Calls 1-8 ... MUST have edited a source file by
call 12') 40% no patch / 48% solved vs prompts without budget numbers 65% / 26% on 10 shared tasks (confounded: other
prompt changes, other notebooks); without the plan the model thinks longer per reply. And the out-of-calls no-patch runs
edit only on 'Tool call budget exhausted' (48 of 49: first refused edit = 1st or 2nd call after it), not on the harness
countdown ('Only N tool call(s) remaining ...', from 10 calls left).

  evide_nonum  evide with ONLY the budget numbers taken out (user chose this clean A/B over a full rewrite, option 2):
               the hard-limits line says the calls and time are limited without numbers, CALL PLAN becomes ORDER OF WORK
               with the same advice and no call numbers, 'Verify (at most 2 calls)' becomes 'Verify (briefly)'. Every
               other line is evide's, byte for byte (asserted).
  evide_warn   evide + a WHEN THE HARNESS WARNS section after the call plan (option 3, few-shot): the harness's own
               warning line quoted, the next call is the edit, a worked three-step example. Every evide line kept.
evide (the control) is unchanged. Only prompts/fixer.md and the agent.yaml comment differ (asserted)."""
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / "submissions"
PARENT = SUB / "evide"
PROMPT_REL = "prompts/fixer.md"

LIMIT_OLD = "- 28 tool calls and 8 minutes in total. When either runs out, the working tree is graded as it is."
LIMIT_NEW = "- Your tool calls and your time are limited. When either runs out, the working tree is graded as it is."
PLAN_OLD = """# CALL PLAN
- Calls 1-8: locate and read. Calls 9-12: edit. You MUST have edited a source file by call 12. If you are unsure, make your best-guess edit in the most likely place now. A wrong edit can still be corrected. Pure reading cannot score.
- Calls 13-20: verify and correct.
- Call 20 onward: no new exploration. Check, fix, submit.
- Always finish with `git status --short && git diff` followed by `submit_patch`.
"""
PLAN_NEW = """# ORDER OF WORK
- Locate and read first, then edit. You MUST edit a source file early. If you are unsure, make your best-guess edit in the most likely place now. A wrong edit can still be corrected. Pure reading cannot score.
- Then verify and correct.
- Near the end: no new exploration. Check, fix, submit.
- Always finish with `git status --short && git diff` followed by `submit_patch`.
"""
VERIFY_OLD, VERIFY_NEW = "## 4. Verify (at most 2 calls)", "## 4. Verify (briefly)"
WARN = """
# WHEN THE HARNESS WARNS
Near the end of your tool calls, every tool result carries the harness's warning, for example:
  "budget_warning": "Only 10 tool call(s) remaining (19/29 used). Finalize your edits and call submit_patch soon."
Your call right after the first such warning is your edit: edit_file with your best fix in the place you have found, even if you are not sure. Do not read or search first. Once a result says "Tool call budget exhausted", every edit is refused and an unedited tree scores zero.
Example:
- a run_command result ends with: "budget_warning": "Only 10 tool call(s) remaining (19/29 used). Finalize your edits and call submit_patch soon."
- your next call: edit_file with filepath src/pkg/values.py, old_string copied from lines you already printed, new_string with your fix
- then one check, then `git status --short && git diff`, then `submit_patch`
"""
ARMS = {
    "evide_nonum": "# evide_nonum (r87): evide with only the budget numbers taken out of the fixer prompt (call plan -> order of work) (scripts/make_r87_arms.py)\n",
    "evide_warn": "# evide_warn (r87): evide + a few-shot WHEN THE HARNESS WARNS section in the fixer prompt (edit on the first budget warning) (scripts/make_r87_arms.py)\n",
}


def files(d):
    return sorted(p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file() and "__pycache__" not in p.parts)


def nonum(p):
    for old, new in ((LIMIT_OLD, LIMIT_NEW), (PLAN_OLD, PLAN_NEW), (VERIFY_OLD, VERIFY_NEW)):
        assert p.count(old) == 1, old[:40]
        p = p.replace(old, new)
    low = p.lower()
    assert not re.search(r"\b\d+\s*tool calls\b|\bcalls? \d|\bcall \d+\b|\bby call\b|\d+\s*minutes", low), "a budget number is left"
    return p


def warn(p):
    assert p.count(PLAN_OLD) == 1
    return p.replace(PLAN_OLD, PLAN_OLD + WARN)


def build(name, comment, fn):
    out = SUB / name
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(PARENT, out, ignore=shutil.ignore_patterns("__pycache__"))
    old = (PARENT / PROMPT_REL).read_text()
    new = fn(old)
    (out / PROMPT_REL).write_text(new)
    first, rest = (PARENT / "agent.yaml").read_text().split("\n", 1)
    assert first.startswith("# evide (r79)")
    (out / "agent.yaml").write_text(comment + rest)
    assert files(out) == files(PARENT)
    for f in files(PARENT):
        if f not in (PROMPT_REL, "agent.yaml"):
            assert (out / f).read_bytes() == (PARENT / f).read_bytes(), f
    # only the targeted lines change
    ol, nl = old.splitlines(), new.splitlines()
    if name == "evide_nonum":
        changed = [l for l in ol if l not in nl]
        assert len(changed) == 6 and all(("28 tool calls" in l) or l.startswith(("# CALL PLAN", "- Calls", "- Call 20", "## 4. Verify")) for l in changed), changed
    else:
        assert all(l in nl for l in ol) and len(nl) == len(ol) + len(WARN.splitlines())
    return out


if __name__ == "__main__":
    for name, fn in (("evide_nonum", nonum), ("evide_warn", warn)):
        o = build(name, ARMS[name], fn)
        print("wrote", o.relative_to(ROOT), "|", files(o))
