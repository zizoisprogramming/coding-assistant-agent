"""Unit tests for adapters P and O's labels (pref_episodes.copy_roles / one_rule_roles / copy_rank) on hand-made runs, one
case per row of the one-rule table (docs/TRAINING_REQUIREMENTS.md C2.1 / C1.2) + the user's rule 'no difference between
solved runs and failed runs' (2026-11-26).

    python3 scripts/train/test_one_rule.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pref_episodes as P  # noqa: E402

PATCH = """--- a/pkg/mod.py
+++ b/pkg/mod.py
@@ -12,3 +12,3 @@
 def f(x):
-    return x + 1
+    return x + 2
 # end
"""
SHOW = "\n".join(f"{n:4}| line {n}" for n in range(8, 12)) + "\n  13|     return x + 1\n"
OK = {"status": "ok", "stdout": "", "exit_code": 0}


def run(steps):
    """steps: [(name, args, result, thinking[, extra reply fields])] -> records in the request-log format (time order):
    record k's request holds every earlier assistant message and tool result; its reply is step k's call."""
    recs, history = [], [{"role": "system", "content": "sys"}, {"role": "user", "content": "issue"}]
    for k, st in enumerate(steps):
        st = tuple(st) + (("",) if len(st) == 3 else ())
        name, args, result, thinking = st[:4]
        extra = st[4] if len(st) > 4 else {}
        cid = f"c{k}"
        msg = {"role": "assistant", "content": extra.get("content", ""), "reasoning_content": thinking,
               "tool_calls": [{"id": cid, "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}]}
        reply = {"message": msg}
        if extra.get("synthetic"):
            reply["synthetic"] = True
        recs.append({"request": {"messages": list(history), "tools": [{"name": "x"}]}, "reply": reply, "t": k})
        history = history + [msg, {"role": "tool", "tool_call_id": cid, "content": json.dumps(result)}]
    return recs


def sh(cmd, out=None, code=0):
    return ("run_command", {"command": cmd}, {"status": "ok", "stdout": out or "", "exit_code": code})


def roles(recs):
    return [r.get("role") for r in recs]


THINK_MAX = "x " * 9000  # >= 1,950 tokens by the ~3 chars / token fallback
BASE = [
    sh("python3 .git/agent/a.py find f"),                                   # 0 look
    sh("python3 .git/agent/a.py show pkg/mod.py 8 13", SHOW),               # 1 saw the fix (line 13 is changed by the fix)
    sh("python3 .git/agent/a.py find g"),                                   # 2 look (reading on)
    sh("python3 .git/agent/a.py find h", "NO EDIT YET"),                    # 3 look; its OUTPUT is the banner
    sh("python3 .git/agent/a.py find i"),                                   # 4 reply to the banner: decision moment, reading on
    ("edit_file", {"filepath": "pkg/mod.py", "old_string": "return x + 1", "new_string": "return x + 2"}, OK, ""),  # 5 right place
    sh("python3 -m pytest tests/test_mod.py -q"),                           # 6 check after edit
    sh("git diff"),                                                         # 7 diff before submit
    ("submit_patch", {}, OK, ""),                                           # 8
]


def labelled(steps, solved, sib=2, allow_bad=True):
    recs = run(steps)
    P.flag_decisions(recs)
    why = P.one_rule_roles(recs, PATCH, sib, solved=solved, allow_bad=allow_bad)
    return recs, why


fails = 0


def check(name, cond, info=""):
    global fails
    print(f"{'PASS' if cond else 'FAIL'}  {name}{'  ' + str(info) if info else ''}")
    fails += not cond


# 1. the base run: milestones good, reading on bad, the rest masked
recs, why = labelled(BASE, solved=False)
check("milestones good: saw the fix (1), check after edit (6), diff before submit (7)",
      [roles(recs)[i] for i in (1, 6, 7)] == ["good"] * 3, roles(recs))
check("failed run: its last edit (5) is right place AND wrong edit -> masked (good + bad)", roles(recs)[5] is None, roles(recs))
check("reading on bad: replies 2-4 (from the earlier of decision / siblings' edit to the run's first edit)",
      [roles(recs)[i] for i in (2, 3, 4)] == ["bad"] * 3, roles(recs))
check("reply 0 before the reading-on window: masked", roles(recs)[0] is None)
# 2. failed run whose last edit is NOT a milestone: wrong edit bad
# the edit comes 5 replies after the decision moment (4): not a 'quick edit', not on the fix's lines: no milestone
steps2 = BASE[:5] + [sh(f"python3 .git/agent/a.py find k{i}") for i in range(4)] + \
    [("edit_file", {"filepath": "pkg/other.py", "old_string": "a", "new_string": "b"}, OK, "")] + BASE[6:]
W = 9  # the wrong edit's reply index
r_f, _ = labelled(steps2, solved=False)
r_s, _ = labelled(steps2, solved=True)
check("wrong edit: a FAILED run's last edit is bad", roles(r_f)[W] == "bad", roles(r_f))
check("the same edit in a SOLVED run is not bad (masked: no row applies)", roles(r_s)[W] is None, roles(r_s))
diff = [i for i, (a, b) in enumerate(zip(roles(r_f), roles(r_s))) if a != b]
check("SAME RUN as solved vs failed: labels differ ONLY at the wrong edit", diff == [W], f"differ at {diff}")
r_f1, _ = labelled(BASE, solved=False)
r_s1, _ = labelled(BASE, solved=True)
d1 = [i for i, (a, b) in enumerate(zip(roles(r_f1), roles(r_s1))) if a != b]
check("base run as solved vs failed: right place (5) is good when solved, masked when failed (good + wrong edit); nothing else",
      d1 == [5] and roles(r_s1)[5] == "good" and roles(r_f1)[5] is None, f"differ at {d1}: {roles(r_f1)} vs {roles(r_s1)}")
# 3. failed / repeated / refused calls masked, even inside reading on
steps3 = BASE[:2] + [sh("python3 .git/agent/a.py find g", code=2)] + [sh("python3 .git/agent/a.py find h", "NO EDIT YET")] * 2 + BASE[5:]
r3, w3 = labelled(steps3, solved=False)
check("failed call (exit 2) masked even in reading on", roles(r3)[2] is None, roles(r3))
check("repeated call (same call, no edit since) masked", roles(r3)[4] is None, roles(r3))
steps3b = BASE[:7] + [("run_command", {"command": "git diff"}, {"status": "error", "error_type": "BudgetExceeded",
                                                                 "error": "Tool call budget exhausted"}, "")] + BASE[8:]
r3b, _ = labelled(steps3b, solved=True)
check("refused call (BudgetExceeded): masked, never 'diff before submit'", roles(r3b)[7] is None, roles(r3b))
# 4. synthetic final reply masked (O and P)
steps4 = BASE + [("submit_patch", {}, OK, "", {"synthetic": True})]
r4, _ = labelled(steps4, solved=True)
check("synthetic reply masked in O", roles(r4)[9] is None, roles(r4))
# 5. maxed thinking before the first edit: bad (solved and failed alike); after the edit: not bad
steps5 = [BASE[0][:3] + (THINK_MAX,)] + BASE[1:6] + [BASE[6][:3] + (THINK_MAX,)] + BASE[7:]
r5f, _ = labelled(steps5, solved=False, sib=None)
r5s, _ = labelled(steps5, solved=True, sib=None)
check("maxed thinking before the first edit: bad in a failed run", roles(r5f)[0] == "bad", roles(r5f))
check("maxed thinking before the first edit: bad in a solved run too", roles(r5s)[0] == "bad", roles(r5s))
check("maxed thinking AFTER the edit on a milestone (check after edit): still good", roles(r5s)[6] == "good", roles(r5s))
# 6. junk text and test-file edits: bad
steps6 = BASE[:1] + [sh("python3 .git/agent/a.py find j")[:3] + ("", {"content": "*" * 8})] + BASE[2:5] + \
    [("edit_file", {"filepath": "tests/test_mod.py", "old_string": "a", "new_string": "b"}, OK, "")] + BASE[5:]
r6, _ = labelled(steps6, solved=True, sib=None)
check("junk text reply: bad", roles(r6)[1] == "bad", roles(r6))
check("test-file edit: bad (solved run)", roles(r6)[5] == "bad", roles(r6))
r6b, _ = labelled(BASE[:5] + [("write_file", {"filepath": ".git/agent/test_regex.py", "content": "print(1)"}, OK, "")] + BASE[5:],
                  solved=True, sib=None)
check("scratch file .git/agent/test_regex.py is NOT a test-file edit (gallery bug 11-28)", "test-file" not in str(r6b[5].get("why")),
      r6b[5].get("why"))
check("is_test_path: tests/x.py yes, pkg/test_a.py yes, .git/agent/test_a.py no, /tmp/test_a.py no",
      [P.is_test_path(x) for x in ("tests/x.py", "pkg/test_a.py", ".git/agent/test_a.py", "/tmp/test_a.py")] == [True, True, False, False])
# 7. never-solved task: no bad labels at all, milestones kept
r7, _ = labelled(BASE, solved=False, allow_bad=False)
check("never-solved task: no bad, milestones good", "bad" not in roles(r7) and roles(r7)[1] == "good", roles(r7))
# 8. a milestone beats 'reading on'; milestone + another bad -> masked
recs8 = run(BASE[:2] + [sh("python3 .git/agent/a.py show pkg/mod.py 8 13", SHOW)[:3] + (THINK_MAX,)] + BASE[2:])
P.flag_decisions(recs8)
P.one_rule_roles(recs8, PATCH, 0, solved=False)
check("milestone inside reading on: good (reply 1)", roles(recs8)[1] == "good", roles(recs8))
# 9. P: copy roles
r9 = run(BASE[:2] + [sh("python3 .git/agent/a.py find g", code=2), BASE[2][:3] + (THINK_MAX,)] + BASE[2:] +
         [("submit_patch", {}, OK, "", {"synthetic": True})])
w9 = P.copy_roles(r9)
check("P: failed call / maxed thinking / synthetic masked, every other reply good",
      roles(r9)[2] is None and roles(r9)[3] is None and roles(r9)[-1] is None and
      roles(r9).count("good") == len(r9) - 3, roles(r9))
# 10. P: ranking = most milestones, then fewest replies, then fastest
e_many = {"kept": run(BASE), "agent_s": 300.0}
e_few_ms = {"kept": run([BASE[0], BASE[2], BASE[5], BASE[8]]), "agent_s": 100.0}
e_many_slow = {"kept": run(BASE), "agent_s": 400.0}
order = sorted([e_few_ms, e_many_slow, e_many], key=lambda e: P.copy_rank(e, PATCH))
check("P ranking: more milestones first, then faster at equal replies", order == [e_many, e_many_slow, e_few_ms],
      [P.copy_rank(e, PATCH) for e in order])
check("copy_rank does not change the episode's records", not any(r.get("milestone") for r in e_many["kept"]))
print(f"\n{'ALL PASS' if not fails else str(fails) + ' FAILED'}")
sys.exit(1 if fails else 0)
