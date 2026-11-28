"""Pass / fail episodes of ONE agent (default sk_a2) for preference training (LoRA plan B, user 2026-11-25: 'go with B' ->
'yes write the training code while they run'). Reads skill-arm notebook outputs (results/gen_per_task.jsonl, requests/
requests.jsonl, results/gen/patches/<task>__a<attempt>.diff; attempts look like 'sk_a2.3') and writes the stage-B layout
build_samples.py reads (requests_pref.jsonl + status.jsonl), with two extra fields per episode: label ('good' / 'bad')
and task.

    python scripts/train/pref_episodes.py --gen DIR [DIR ...] --tasks tasks.jsonl [...] --out DIR [options]

Labels:
  good = solved, cut at its FIRST successful submit_patch (+ the next reply only when it is a clean final message;
         otherwise a synthetic clean final reply with thinking) - selfdistill_episodes.analyse, the October cut that
         removed the submit loops; and it must pass the October filter (no test-file edits, no scratch files left,
         <= --max-fail-streak failed calls in a row, <= --max-repeats repeated calls, no junk text).
  bad  = not solved, ended by the agent or by a cap (end in ok / time / tool_budget / turns; never infrastructure ends),
         cut the same way when it submitted (what follows the first submit is a loop tail, not a decision).
Unpaired tasks (2026-11-26, change 4): always-solved runs train as good at --unpaired-weight; never-solved runs give only
their good steps at --unpaired-weight. Good runs of always-solved tasks are kept (they feed the copy term).
Caps: at most --cap good and --cap bad episodes per task (fastest good runs first, bad runs spread over attempts).
Held-out safety: tasks listed in --exclude (one id per line, or a json list: scripts/train/heldout_eval.json = the final
test's 24 other-repo tasks + data/rebench_test + the 8 dev16 test tasks) are skipped and counted; the output is checked
to hold none of them. --only-tasks limits the build to listed tasks (the 4 fastapi / rich pairs outside the test).
Split: --val-share of TASKS (hash of the task id) go to val, so validation measures the contrast on unseen tasks.
"""
import argparse
import ast
import collections
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from selfdistill_episodes import analyse, failed, tool_results  # noqa: E402

AGENT_ENDS = {"ok", "time", "tool_budget", "turns", "no_submit"}
# option C (user 2026-11-25): a solved run is GOOD only if it kept sk_a2's clear-cut rules in what is trained: code read only
# through .git/agent/a.py (no cat / sed -n / head / tail / grep / read_file of source) and no edit_file / write_file on a test
# path. Calls after the first successful submit are cut anyway (never trained). Banner timing is left to the pass / fail contrast.
READ_CMD = re.compile(r"^\s*(cat|sed\s+-n|head|tail|grep|egrep|rg|less|nl|awk)\b|python3?\s+-c\s+.*open\(")
TEST_FILE = re.compile(r"(^|/)(tests?/|test_[^/]*\.py$|conftest\.py$)")


# Decision moments (user 2026-11-25: 'add the 2x weight on decision moments'): the reply to the FIRST harness budget warning
# and the reply to the FIRST a.py banner that arrive while the run has NO source edit yet (scripts/mine_bank/mechanism_obeyed.py:
# obeying the budget warning goes with solving on the same task, 24+/6-). Flagged on the record (record['decision'] = True);
# build_samples.py marks the segment holding it; train_pref.py weighs that segment x --decision-weight.
DECISION = {"budget": re.compile(r"tool call\(s\) remaining"), "banner": re.compile(r"NO EDIT YET|STOP READING|ALREADY SHOWN")}
EDIT_RUN = re.compile(r"sed\s+-i|git\s+apply|patch\s+-p|OLD_TEXT|\.replace\(|old_string")


def reply_calls(r, res=None):
    """[(name, args)] of a reply's calls; with res (tool_results), only calls whose result is not a failure."""
    out = []
    for c in ((r.get("reply") or {}).get("message") or {}).get("tool_calls") or []:
        fn = c.get("function") or {}
        try:
            a = json.loads(fn.get("arguments") or "{}") if isinstance(fn.get("arguments"), str) else (fn.get("arguments") or {})
        except ValueError:
            a = {}
        a = a if isinstance(a, dict) else {}
        if res is not None and failed(fn.get("name"), a, res.get(c.get("id"))):
            continue  # a garbled / refused edit is not an edit (2026-11-25: 11 'edits' in one run had no old_string)
        out.append((fn.get("name"), a))
    return out


def source_edit(name, a):
    path, cmd = str(a.get("filepath", a.get("path", ""))), str(a.get("command", ""))
    if name in ("edit_file", "write_file"):
        return bool(path) and not path.startswith(".git/") and not path.startswith("/tmp") and not TEST_FILE.search(path)
    return name == "run_command" and "a.py" not in cmd and bool(EDIT_RUN.search(cmd))


def flag_decisions(kept):
    """Mark the records whose reply answers the first budget warning / first banner seen with no source edit yet."""
    seen, edited, n = set(), False, 0
    res = tool_results(kept)
    for r in kept:
        if not r["request"].get("tools"):
            continue
        msgs = r["request"]["messages"]
        k = max((i for i, m in enumerate(msgs) if m.get("role") == "assistant"), default=-1)
        new = " ".join(str(m.get("content")) for m in msgs[k + 1:] if m.get("role") == "tool")  # this request's new tool outputs
        if not edited:
            for name, rx in DECISION.items():
                if name not in seen and rx.search(new):
                    seen.add(name)
                    r["decision"] = True
                    n += 1
        if any(source_edit(nm, a) for nm, a in reply_calls(r, res)):
            edited = True
    return n


# Per-reply labels (user 2026-11-25: 'implement the per-reply labels ... train it to follow patterns that lead to success not
# just solutions, because solutions depend maybe on easiness of the tasks'). Evidence: process supervision beats outcome
# supervision (Lightman et al. 2023, 'Let's Verify Step by Step'); SWE step scoring against the fix's milestones beat
# outcome-filtered SFT by up to +10.8 Pass@1 (P2T, arXiv 2605.21996); credit for failed steps from successful siblings of the
# same task (SCPO, arXiv 2606.25852); group-relative (same-task) baselines remove task-ease bias (GRPO / Dr. GRPO).
#   weight: a run's same-task advantage: solved -> 1 - p, failed -> p, with p = the task's solve rate over this agent's runs
#           (a solve every run makes says little; a failure where siblings solve says a lot).
#   solved runs: every reply trained (decision replies x2 in train_pref.py).
#   failed runs: only the replies that are the failing PATTERN are trained (pushed down); the rest is context only:
#     reading on: from the first decision moment or from the reply index by which the task's solved siblings had made their
#                 first source edit (median), whichever is earlier, up to the run's own first source edit (a run that never
#                 edits: to its end);
#     retries:    a call that failed right after a failed call (2nd+ of a streak);
#     repeats:    the same call again with no source edit since its last use (get_status excepted);
#     wrong edit: the run's last source-edit reply (the edit the hidden tests rejected).
def reply_index_of_first_edit(kept):
    res = tool_results(kept)
    i = 0
    for r in kept:
        if not r["request"].get("tools"):
            continue
        if any(source_edit(nm, a) for nm, a in reply_calls(r, res)):
            return i
        i += 1
    return None


# A + B (user 2026-11-25: 'do both A and B with 0.5 weight'):
#  A. in SOLVED runs a reply whose call failed is masked (the mistake is not taught); the next reply, the recovery, stays good.
#  B. in FAILED runs two milestones of the real fix are trained as GOOD at --milestone-weight x the task's good weight (P2T,
#     arXiv 2605.21996: steps graded against the reference patch's milestones; the patch only GRADES, it never writes text):
#     'saw the fix' = the first a.py show whose numbered output holds a line the real fix changes (source files);
#     'right place' = the first applied edit_file on a fixed file whose old text matches a shown line within 3 lines of a
#     changed line. A milestone reply that is also trained as bad (e.g. the final wrong edit) is masked (right place, wrong logic).
# Each record gets record['role'] in {'good', 'bad', None}; build_samples.py makes one sample per (segment, role).
SHOWN_LINE = re.compile(r"^\s*(\d+)\|\s?(.*)$", re.M)


def fix_lines(patch):
    """{file: set(old-file lines the real fix changes or inserts next to)} for non-test files."""
    out, f, o = collections.defaultdict(set), None, 0
    for ln in (patch or "").split("\n"):
        if ln.startswith("+++ "):
            f = ln[6:].strip() if ln.startswith("+++ b/") else None
            f = None if f and TEST_FILE.search(f) else f
            continue
        if ln.startswith("--- "):
            continue
        m = re.match(r"^@@ -(\d+)", ln)
        if m:
            o = int(m.group(1))
            continue
        if f is None:
            continue
        if ln.startswith("-"):
            out[f].add(o)
            o += 1
        elif ln.startswith("+"):
            out[f].update({max(o - 1, 1), o})
        else:
            o += 1
    return out


# Four label changes (user 2026-11-26: 'yes implement the four label changes'; evidence: scripts/mine_bank/good_behaviours.py,
# 391 same-agent same-task cells; label_rules_check.py):
#  1. more GOOD steps in failed runs at the milestone weight: the first test / script run after the last applied edit ('check
#     after edit'), git diff / status before the first submit ('diff before submit'), the first applied edit when it comes
#     within 3 replies of the first decision moment ('quick edit') - unless it is the final wrong edit (then masked);
#  2. BAD: a maxed-thinking reply (>= MAXED_TOKENS of thinking, sk_a2's cap is 2,048) before the first applied edit of a
#     failed run; in solved runs maxed replies are masked;
#  3. retry streaks and repeats are no longer bad (they did not separate success on the same task): masked;
#  4. unpaired tasks: always-solved runs train as good at --unpaired-weight; never-solved runs give only their good steps
#     (milestones) at --unpaired-weight, no bad labels (no solved sibling shows what should have happened).
MAXED_TOKENS = 1950
_TOK = None


def thinking_tokens(r):
    th = ((r.get("reply") or {}).get("message") or {}).get("reasoning_content") or ""
    if not th:
        return 0
    return len(_TOK.encode(th).ids) if _TOK is not None else len(th) // 3  # fallback without a tokenizer: ~3 chars / token


def is_run_check(name, a):
    cmd = str(a.get("command", ""))
    return name == "run_command" and "a.py" not in cmd and bool(re.search(r"\bpython3?\b|\bpytest\b", cmd)) and not EDIT_RUN.search(cmd)


def label_milestones(kept, patch):
    """Mark up to two milestone replies of a failed run (record['milestone'] = name). Returns the names found."""
    gold = fix_lines(patch)
    if not gold:
        return []
    res = tool_results(kept)
    shown = collections.defaultdict(dict)  # file -> {line: stripped text} from a.py show outputs
    found = []
    for r in kept:
        if not r["request"].get("tools"):
            continue
        for c in ((r.get("reply") or {}).get("message") or {}).get("tool_calls") or []:
            fn = c.get("function") or {}
            try:
                a = json.loads(fn.get("arguments") or "{}") if isinstance(fn.get("arguments"), str) else (fn.get("arguments") or {})
            except ValueError:
                a = {}
            a = a if isinstance(a, dict) else {}
            out = res.get(c.get("id"))
            text = (out.get("stdout") if isinstance(out, dict) else None) or (json.dumps(out) if out else "")
            cmd = str(a.get("command", ""))
            mm = re.search(r"a\.py\s+show\s+(\S+)", cmd)
            if mm:
                f = mm.group(1).strip("'\"").lstrip("./")
                lines = {int(n): s.strip() for n, s in SHOWN_LINE.findall(text)}
                shown[f].update(lines)
                if "saw the fix" not in found and f in gold and gold[f] & set(lines):
                    found.append("saw the fix")
                    r["milestone"] = "saw the fix"
            if fn.get("name") == "edit_file" and "right place" not in found and not failed("edit_file", a, out):
                f = str(a.get("filepath", "")).lstrip("./")
                first = next((x.strip() for x in str(a.get("old_string", "")).splitlines() if x.strip()), None)
                if f in gold and first:
                    at = [n for n, s in shown[f].items() if s == first]
                    if any(abs(n - g) <= 3 for n in at for g in gold[f]):
                        found.append("right place")
                        r["milestone"] = "right place"
    found += process_milestones(kept)
    return found


def process_milestones(kept):
    """Change 1: good process steps (need no reference patch): check after the last applied edit, git diff / status before
    the first submit, the first applied edit within 3 replies of the first decision moment."""
    res = tool_results(kept)
    recs = [r for r in kept if r["request"].get("tools")]
    edits = [i for i, r in enumerate(recs) if any(source_edit(nm, a) for nm, a in reply_calls(r, res))]
    found = []

    def ran(r):  # 2026-11-26 (real run rich_3676 r148: 'git diff' refused with 'Tool call budget exhausted' was labelled good):
        # a check / diff step counts only when the harness ran it; a failing test (CommandError) still ran
        for c in ((r.get("reply") or {}).get("message") or {}).get("tool_calls") or []:
            o = res.get(c.get("id"))
            if isinstance(o, dict) and (o.get("error_type") == "BudgetExceeded" or (o.get("error") and not o.get("status"))):
                return False
        return True
    if edits:
        last = edits[-1]
        k = next((i for i in range(last + 1, len(recs)) if ran(recs[i]) and any(is_run_check(nm, a) for nm, a in reply_calls(recs[i]))), None)
        if k is not None and not recs[k].get("milestone"):
            recs[k]["milestone"] = "check after edit"
            found.append("check after edit")
    sub_at = next((i for i, r in enumerate(recs) if any(nm == "submit_patch" for nm, a in reply_calls(r))), None)
    if sub_at is not None and edits:
        k = next((i for i in range(edits[0], sub_at) if ran(recs[i]) and any(nm == "run_command" and re.search(r"git\s+(diff|status)", str(a.get("command", "")))
                                                             for nm, a in reply_calls(recs[i]))), None)
        if k is not None and not recs[k].get("milestone"):
            recs[k]["milestone"] = "diff before submit"
            found.append("diff before submit")
    dec = next((i for i, r in enumerate(recs) if r.get("decision")), None)
    if dec is not None and edits and 0 <= edits[0] - dec <= 3 and not recs[edits[0]].get("milestone"):
        recs[edits[0]]["milestone"] = "quick edit"
        found.append("quick edit")
    # loop break (user 2026-11-26: 'yes add the loop-break step'): after 2+ calls in a row that failed or repeated an earlier
    # call (no applied edit since), the first reply whose call works AND differs from those calls. Up to 2 per run.
    stuck, seen, n_breaks, applied = 0, {}, 0, 0
    for i, r in enumerate(recs):
        calls = reply_calls(r)
        if not calls:
            continue
        nm, a = calls[0]
        key = nm + json.dumps(a, sort_keys=True)
        c0 = (((r.get("reply") or {}).get("message") or {}).get("tool_calls") or [{}])[0]
        bad = failed(nm, a, res.get(c0.get("id")))
        rep = nm != "get_status" and seen.get(key) == applied
        if stuck >= 2 and not bad and not rep and n_breaks < 2 and not r.get("milestone"):
            r["milestone"] = "loop break"
            found.append("loop break")
            n_breaks += 1
        stuck = stuck + 1 if (bad or rep) else 0
        seen[key] = applied
        applied += source_edit(nm, a) and not bad
    return found


def label_bad_replies(kept, sibling_edit_at, never_solved=False):
    """Set record['train'] on a failed run's replies (True = trained as bad). Returns {reason: replies}."""
    recs = [r for r in kept if r["request"].get("tools")]
    res = tool_results(kept)
    dec = next((i for i, r in enumerate(recs) if r.get("decision")), None)
    first_edit = next((i for i, r in enumerate(recs) if any(source_edit(nm, a) for nm, a in reply_calls(r, res))), None)
    last_edit = max((i for i, r in enumerate(recs) if any(source_edit(nm, a) for nm, a in reply_calls(r, res))), default=None)
    starts = [x for x in (dec, sibling_edit_at) if x is not None]
    start = min(starts) if starts else None
    stop = first_edit if first_edit is not None else len(recs)
    why = collections.Counter()
    prev_failed, last_use, edits = False, {}, 0
    for i, r in enumerate(recs):
        reasons = []
        if start is not None and start <= i < stop:
            reasons.append("reading on")
        for c in ((r.get("reply") or {}).get("message") or {}).get("tool_calls") or []:
            fn = c.get("function") or {}
            nm = fn.get("name")
            try:
                a = json.loads(fn.get("arguments") or "{}") if isinstance(fn.get("arguments"), str) else (fn.get("arguments") or {})
            except ValueError:
                a = {}
            a = a if isinstance(a, dict) else {}
            bad = failed(nm, a, res.get(c.get("id")))
            if bad and prev_failed:
                why["retry streak (masked, not bad)"] += 1  # change 3
            prev_failed = bad
            key = nm + json.dumps(a, sort_keys=True)
            if nm != "get_status" and last_use.get(key) == edits:
                why["repeat (masked, not bad)"] += 1  # change 3
            last_use[key] = edits
            edits += source_edit(nm, a) and not bad
        if (first_edit is None or i < first_edit) and thinking_tokens(r) >= MAXED_TOKENS:
            reasons.append("maxed thinking")  # change 2
        if i == last_edit:
            reasons.append("wrong edit")
        if never_solved:
            reasons = []  # change 4: no bad labels without a solved sibling
        if r.get("milestone") and set(reasons) <= {"reading on"}:
            reasons = []  # a milestone is specific evidence the step was right: it beats the stretch label 'reading on'
        r["train"] = bool(reasons)
        why["trained"] += bool(reasons)
        if reasons and r.get("milestone"):
            r["role"], r["train"] = None, False  # a milestone that is also a retry / repeat / the wrong edit: masked
            why["milestone and bad: masked"] += 1
        elif reasons:
            r["role"] = "bad"
        elif r.get("milestone"):
            r["role"] = "good"
            why[f"milestone: {r['milestone']}"] += 1
        else:
            r["role"] = None
        for x in set(reasons):
            why[x] += 1
        why["replies"] += 1
    return why


# Adapters P and O (user 2026-11-26: 'two adapters P and O'; 'no difference between solved runs and failed runs';
# docs/TRAINING_REQUIREMENTS.md C1 / C2):
#  P (copy): per task the best-process passes (clean by the October filter + option C; most milestones, then fewest replies,
#    then fastest), every reply trained good except a reply with a failed / refused call, a maxed-thinking reply, or a
#    synthetic final reply (text we wrote, not the model) -> masked. Sample flags copy=True, kto=False.
#  O (one rule, the SAME table in solved and failed runs): GOOD = the 6 milestones; BAD = reading on, maxed thinking before
#    the first edit, the final edit of a FAILED run, junk text, a test-file edit; MASKED = a reply with a failed / refused /
#    repeated call, a synthetic reply, a reply both good and bad (except: a milestone beats 'reading on'), every other reply.
#    Weights by label, not by run: good 1 - p, bad p (p = the task's solve rate); a task every run solved: good and bad at
#    --unpaired-weight; a task no run solved: good at --unpaired-weight, no bad (no solved sibling). Flags copy=False, kto=True.
#    O's samples also hold P's copy episodes (the proven part), so P and O differ only by the labels.
JUNK_TEXT = re.compile(r"\*{6,}|\n{8,}|<\|channel>|<channel\|>|<\|tool_call>|^\s*(get_status|submit_patch|run_command|read_file)\s*[{(]", re.M)


def call_list(r):
    out = []
    for c in ((r.get("reply") or {}).get("message") or {}).get("tool_calls") or []:
        fn = c.get("function") or {}
        try:
            a = json.loads(fn.get("arguments") or "{}") if isinstance(fn.get("arguments"), str) else (fn.get("arguments") or {})
        except ValueError:
            a = {}
        out.append((fn.get("name"), a if isinstance(a, dict) else {}, c.get("id")))
    return out


def call_failed(nm, a, o):
    return failed(nm, a, o) or (isinstance(o, dict) and o.get("error_type") == "BudgetExceeded")


def copy_roles(kept):
    """P: role 'good' on every reply except failed / refused calls, maxed thinking, synthetic replies. Returns counts."""
    res = tool_results(kept)
    why = collections.Counter()
    for r in kept:
        if not r["request"].get("tools"):
            continue
        bad = any(call_failed(nm, a, res.get(cid)) for nm, a, cid in call_list(r))
        mx = thinking_tokens(r) >= MAXED_TOKENS
        syn = bool((r.get("reply") or {}).get("synthetic"))
        r["role"] = None if (bad or mx or syn) else "good"
        why["copy: failed call masked"] += bad
        why["copy: maxed thinking masked"] += mx and not bad
        why["copy: synthetic reply masked"] += syn and not (bad or mx)
        why["copy: good"] += r["role"] == "good"
    return why


def one_rule_roles(kept, patch, sib, solved, allow_bad=True):
    """O: role per reply from the one table (see above). Returns {reason: replies}."""
    label_milestones(kept, patch)  # the 2 fix milestones + the 4 process milestones (solved runs too)
    recs = [r for r in kept if r["request"].get("tools")]
    res = tool_results(kept)
    edits_at = [i for i, r in enumerate(recs) if any(source_edit(nm, a) for nm, a in reply_calls(r, res))]
    first_edit, last_edit = (edits_at[0], edits_at[-1]) if edits_at else (None, None)
    dec = next((i for i, r in enumerate(recs) if r.get("decision")), None)
    starts = [x for x in (dec, sib) if x is not None]
    start = min(starts) if starts else None
    stop = first_edit if first_edit is not None else len(recs)
    why = collections.Counter()
    last_use, applied = {}, 0
    for i, r in enumerate(recs):
        masked, bad = [], []
        for nm, a, cid in call_list(r):
            o = res.get(cid)
            if call_failed(nm, a, o):
                masked.append("failed / refused call")
            key = nm + json.dumps(a, sort_keys=True)
            if nm != "get_status" and last_use.get(key) == applied:
                masked.append("repeat")
            last_use[key] = applied
            if nm in ("edit_file", "write_file") and TEST_FILE.search(str(a.get("filepath", a.get("path", "")))):
                bad.append("test-file edit")
            applied += source_edit(nm, a) and not call_failed(nm, a, o)
        if (r.get("reply") or {}).get("synthetic"):
            masked.append("synthetic reply")
        if start is not None and start <= i < stop:
            bad.append("reading on")
        if (first_edit is None or i < first_edit) and thinking_tokens(r) >= MAXED_TOKENS:
            bad.append("maxed thinking")
        if not solved and i == last_edit:
            bad.append("wrong edit")
        msg = (r.get("reply") or {}).get("message") or {}
        if JUNK_TEXT.search(str(msg.get("reasoning_content") or "")) or JUNK_TEXT.search(str(msg.get("content") or "")):
            bad.append("junk text")
        if not allow_bad:
            bad = []
        good = r.get("milestone")
        if masked:
            r["role"] = None
            why["masked: " + masked[0]] += 1
        elif good and bad and set(bad) <= {"reading on"}:
            r["role"] = "good"  # a milestone is specific evidence the step was right: it beats the stretch label
            why[f"good: {good}"] += 1
        elif good and bad:
            r["role"] = None
            why["masked: both good and bad"] += 1
        elif bad:
            r["role"] = "bad"
            for x in set(bad):
                why[f"bad: {x}"] += 1
        elif good:
            r["role"] = "good"
            why[f"good: {good}"] += 1
        else:
            r["role"] = None
            why["masked: other step"] += 1
        why["replies"] += 1
    return why


def copy_rank(e, patch):
    """P's order inside a task: most milestones, then fewest replies, then fastest (lower is better)."""
    tmp = [dict(r) for r in e["kept"]]
    n_ms = len(label_milestones(tmp, patch))
    return (-n_ms, sum(1 for r in e["kept"] if r["request"].get("tools")), e["agent_s"])


def broken_rules(kept):
    """Clear-cut rule breaks in the trained part of a run (records kept after the cut)."""
    reads = tests = 0
    for r in kept:
        for c in ((r.get("reply") or {}).get("message") or {}).get("tool_calls") or []:
            fn = c.get("function") or {}
            try:
                a = json.loads(fn.get("arguments") or "{}") if isinstance(fn.get("arguments"), str) else (fn.get("arguments") or {})
            except ValueError:
                a = {}
            a = a if isinstance(a, dict) else {}
            cmd, path = str(a.get("command", "")), str(a.get("filepath", a.get("path", "")))
            if fn.get("name") == "read_file" and not path.startswith(".git/agent"):
                reads += 1
            if fn.get("name") == "run_command" and READ_CMD.search(cmd) and "a.py" not in cmd:
                reads += 1
            if fn.get("name") in ("edit_file", "write_file") and TEST_FILE.search(path):
                tests += 1
    return reads, tests


def parse_reply(x):
    if isinstance(x, dict):
        return x
    try:
        return ast.literal_eval(str(x))
    except (ValueError, SyntaxError):
        try:
            return json.loads(str(x))
        except ValueError:
            return {}


def load_dir(d, arms):
    d = Path(d)
    rows = {}
    for p in sorted(d.glob("**/results/gen_per_task.jsonl")):
        for line in open(p):
            try:
                g = json.loads(line)
            except ValueError:
                continue
            if g.get("arm") in arms and g.get("resolved") is not None:
                rows[(g["instance_id"], str(g["attempt"]))] = g
    recs = collections.defaultdict(list)
    for p in sorted(d.glob("**/requests/requests.jsonl")):
        with open(p, errors="replace") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                job = r.get("job") or ""
                if "#a" not in job:
                    continue
                iid, att = job.rsplit("#a", 1)
                if (iid, att) in rows:
                    r["reply"] = parse_reply(r.get("reply"))
                    recs[(iid, att)].append(r)
    patches = {}
    for p in d.glob("**/results/gen/patches/*.diff"):
        iid, att = p.stem.rsplit("__a", 1)
        patches[(iid, att)] = p.read_text(errors="replace")
    for v in recs.values():
        v.sort(key=lambda r: float(r["t"]))
    return rows, recs, patches


def is_val(task, share):
    return int(hashlib.sha1(task.encode()).hexdigest(), 16) % 1000 < share * 1000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", nargs="+", required=True, help="skill-arm notebook output dirs")
    ap.add_argument("--tasks", nargs="+", required=True, help="tasks.jsonl files (reference patches)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--arms", nargs="+", default=["sk_a2"], help="arm names kept (one agent: its prompt = the test prompt)")
    ap.add_argument("--exclude", nargs="*", default=[], help="held-out task id files (skipped, never in the output)")
    ap.add_argument("--only-tasks", nargs="*", default=[], help="keep only these task ids")
    ap.add_argument("--cap", type=int, default=6, help="max good and max bad episodes per task")
    ap.add_argument("--unpaired-weight", type=float, default=0.25, help="change 4: always-solved runs / never-solved milestones")
    ap.add_argument("--tokenizer-dir", default=None, help="tokenizer.json folder: thinking length in tokens (maxed thinking)")
    ap.add_argument("--max-fail-streak", type=int, default=3)
    ap.add_argument("--max-repeats", type=int, default=3)
    ap.add_argument("--val-share", type=float, default=0.12)
    ap.add_argument("--milestone-weight", type=float, default=0.5, help="B: milestone replies of failed runs, x the task's good weight")
    ap.add_argument("--mode", choices=["old", "p", "o"], default="old",
                    help="old = the 11-26 labels; p = adapter P (copy the best passes); o = adapter O (P's copy + the one rule)")
    ap.add_argument("--copy-per-task", type=int, default=1, help="P / O: best-process passes copied per task")
    a = ap.parse_args()
    global _TOK
    if a.tokenizer_dir:
        from tokenizers import Tokenizer
        _TOK = Tokenizer.from_file(str(Path(a.tokenizer_dir) / "tokenizer.json"))
    tasks = {}
    for f in a.tasks:
        for line in open(f):
            t = json.loads(line)
            tasks[t["instance_id"]] = t
    excl = set()
    for f in a.exclude:
        txt = Path(f).read_text()
        excl |= set(json.loads(txt)) if txt.lstrip().startswith("[") else {x.strip() for x in txt.splitlines() if x.strip()}
    eps, why = [], collections.Counter()
    runs_of = collections.defaultdict(lambda: {True: 0, False: 0})
    for d in a.gen:
        rows, recs, patches = load_dir(d, set(a.arms))
        print(f"{d}: {len(rows)} runs of {a.arms}, {len(recs)} with request logs, {sum(g['resolved'] in (True, 'True') for g in rows.values())} solved", flush=True)
        for key, g in sorted(rows.items()):
            iid = key[0]
            if iid in excl:
                why["held-out task skipped"] += 1
                continue
            if a.only_tasks and iid not in a.only_tasks:
                why["not in --only-tasks"] += 1
                continue
            rs = recs.get(key)
            if not rs:
                why["no request log"] += 1
                continue
            if iid not in tasks:
                why["task not in --tasks"] += 1
                continue
            if g.get("end") not in AGENT_ENDS:
                why[f"end {g.get('end')} (infrastructure)"] += 1
                continue
            solved = g["resolved"] in (True, "True")
            runs_of[iid][solved] += 1
            m, kept = analyse(rs, dict(g, resolved=solved), tasks[iid], patches.get(key, ""))
            if solved:
                bad_rule = next((w for w, b in [("edits tests", m["test_files_edited"]), ("leaves scratch files", m["scratch_files"]),
                                                ("fail streak", m["max_fail_streak"] > a.max_fail_streak),
                                                ("repeats calls", m["repeats"] > a.max_repeats), ("junk text", m["junk_replies"] > 0),
                                                ("no submit", not m["submitted"])] if b), None)
                rd, te = broken_rules(kept)
                bad_rule = bad_rule or ("reads code outside a.py" if rd else None) or ("edits a test file" if te else None)
                if bad_rule and a.mode == "old":
                    why[f"good dropped: {bad_rule}"] += 1
                    continue
                if bad_rule:  # P / O: never copied; O still labels its steps (user: label the step, do not leave the run out)
                    why[f"pass not copyable: {bad_rule}"] += 1
            else:
                bad_rule = None
            m["decisions"] = flag_decisions(kept)
            eps.append(dict(task=iid, attempt=key[1], label="good" if solved else "bad", kept=kept, m=m, clean=solved and not bad_rule,
                            agent_s=float(g.get("agent_s") or 0), src=str(d)))
            why["good" if solved else "bad"] += 1
    by = collections.defaultdict(lambda: {"good": [], "bad": []})
    for e in eps:
        by[e["task"]][e["label"]].append(e)
    if a.mode != "old":
        return write_p_o(a, by, runs_of, tasks, excl, why)
    bad_why = collections.Counter()
    for t, v in by.items():
        n = runs_of[t][True] + runs_of[t][False]
        p = runs_of[t][True] / max(n, 1)
        idx = sorted(x for x in (reply_index_of_first_edit(e["kept"]) for e in v["good"]) if x is not None)
        sib = idx[len(idx) // 2] if idx else None  # by this reply the task's solved siblings had (median) edited
        unpaired = p in (0.0, 1.0)
        for e in v["good"]:
            e["weight"] = round(a.unpaired_weight if unpaired else 1 - p, 4)  # change 4: always-solved at the unpaired weight
            res = tool_results(e["kept"])  # A: mask the mistakes of a solved run, keep its recoveries
            for r in e["kept"]:
                if r["request"].get("tools"):
                    bad = any(failed((c.get("function") or {}).get("name"), (lambda x: x if isinstance(x, dict) else {})(
                        json.loads(c["function"].get("arguments") or "{}") if isinstance(c["function"].get("arguments"), str)
                        else c["function"].get("arguments") or {}), res.get(c.get("id")))
                        for c in ((r.get("reply") or {}).get("message") or {}).get("tool_calls") or [])
                    mx = thinking_tokens(r) >= MAXED_TOKENS  # change 2: a maxed reply is not taught, even in a solved run
                    r["role"] = None if (bad or mx) else "good"
                    bad_why["solved: mistake masked"] += bad
                    bad_why["solved: maxed thinking masked"] += mx and not bad
        for e in v["bad"]:
            e["weight"] = round(p, 4)
            e["weight_milestone"] = round(a.unpaired_weight if p == 0 else a.milestone_weight * (1 - p), 4)
            label_milestones(e["kept"], tasks[t]["patch"])
            bad_why.update(label_bad_replies(e["kept"], sib, never_solved=(p == 0)))
    chosen = []
    for t, v in sorted(by.items()):
        good = sorted(v["good"], key=lambda e: e["agent_s"])[:a.cap]
        bad = sorted(v["bad"], key=lambda e: e["attempt"])[:a.cap]  # change 4: never-solved runs kept (their good steps only)
        chosen += good + bad
    assert not {e["task"] for e in chosen} & excl, "a held-out task reached the training data"
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "requests_pref.jsonl", "w") as fr, open(out / "status.jsonl", "w") as fs:
        for e in chosen:
            eid = f"{e['task']}#{Path(e['src']).name}#a{e['attempt']}"  # attempt names repeat across notebook outputs
            split = "val" if is_val(e["task"], a.val_share) else "train"
            for r in e["kept"]:
                fr.write(json.dumps(dict(r, episode_id=eid, attempt=e["attempt"])) + "\n")
            fs.write(json.dumps({"id": eid, "attempt": e["attempt"], "status": "ok", "split": split, "label": e["label"],
                                 "weight": e.get("weight", 1.0), "weight_milestone": e.get("weight_milestone", 0.0),
                                 "task": e["task"], "category": "pref", "teacher": ",".join(a.arms)}) + "\n")
    with open(out / "metrics.jsonl", "w") as fh:
        for e in eps:
            fh.write(json.dumps(dict(e["m"], task=e["task"], attempt=e["attempt"], label=e["label"], src=e["src"])) + "\n")
    paired = [t for t, v in by.items() if v["good"] and v["bad"]]
    print(f"failed runs' replies: {bad_why['replies']} | trained as bad (the failing pattern): reading on {bad_why['reading on']}, "
          f"retry streak {bad_why['retry streak']}, repeat {bad_why['repeat']}, wrong edit {bad_why['wrong edit']} | masked (context only) "
          f"{bad_why['replies'] - bad_why['trained']} | trained {bad_why['trained']}")
    print("good steps in failed runs: " + ", ".join(f"{k[11:]} {v}" for k, v in sorted(bad_why.items()) if k.startswith("milestone: ")) +
          f" | maxed thinking (bad) {bad_why['maxed thinking']} | retries / repeats now masked {bad_why['retry streak (masked, not bad)']} / "
          f"{bad_why['repeat (masked, not bad)']} | solved: maxed thinking masked {bad_why['solved: maxed thinking masked']}")
    print(f"B milestones in failed runs: saw the fix {bad_why['milestone: saw the fix']}, right place {bad_why['milestone: right place']}, "
          f"both milestone and bad (masked) {bad_why['milestone and bad: masked']} | A: mistakes masked in solved runs {bad_why['solved: mistake masked']}")
    C = collections.Counter((("val" if is_val(e["task"], a.val_share) else "train"), e["label"]) for e in chosen)
    print(f"\nruns: {dict(why.most_common())}")
    print(f"tasks: {len(by)} | with both outcomes (paired): {len(paired)} | only solved: "
          f"{sum(1 for v in by.values() if v['good'] and not v['bad'])} | only failed: {sum(1 for v in by.values() if v['bad'] and not v['good'])}")
    print(f"KEPT {len(chosen)} episodes (cap {a.cap}/label/task): train good {C['train', 'good']} bad {C['train', 'bad']} | "
          f"val good {C['val', 'good']} bad {C['val', 'bad']} | repos {len({re.sub(r'[-_][0-9]+$', '', e['task']) for e in chosen})}")


def write_p_o(a, by, runs_of, tasks, excl, why):
    """Adapters P and O: the episodes, their roles and flags (see copy_roles / one_rule_roles)."""
    out_eps, stats = [], collections.Counter()
    for t, v in sorted(by.items()):
        n = runs_of[t][True] + runs_of[t][False]
        p = runs_of[t][True] / max(n, 1)
        patch = tasks[t]["patch"]
        clean = sorted((e for e in v["good"] if e["clean"]), key=lambda e: copy_rank(e, patch))[:a.copy_per_task]
        for e in clean:  # the copy part (P, and O's copy term)
            kept = [dict(r) for r in e["kept"]]
            stats.update(copy_roles(kept))
            out_eps.append((f"{t}#{Path(e['src']).name}#a{e['attempt']}#copy", e, kept,
                            {"label": "good", "copy": True, "kto": False, "weight": 1.0}))
        stats["copy episodes"] += len(clean)
        stats["tasks with a copied pass"] += bool(clean)
        if a.mode != "o":
            continue
        idx = sorted(x for x in (reply_index_of_first_edit(e["kept"]) for e in v["good"]) if x is not None)
        sib = idx[len(idx) // 2] if idx else None  # by this reply the task's solved siblings had (median) edited
        paired = 0 < p < 1
        w_good = round(1 - p, 4) if paired else a.unpaired_weight
        w_bad = round(p, 4) if paired else (a.unpaired_weight if p == 1 else 0.0)
        for e in sorted(v["good"], key=lambda e: e["agent_s"])[:a.cap] + sorted(v["bad"], key=lambda e: e["attempt"])[:a.cap]:
            kept = [dict(r) for r in e["kept"]]
            stats.update(one_rule_roles(kept, patch, sib, solved=e["label"] == "good", allow_bad=w_bad > 0))
            if not any(r.get("role") for r in kept):
                stats["labelled episodes with no labelled reply (dropped)"] += 1
                continue
            out_eps.append((f"{t}#{Path(e['src']).name}#a{e['attempt']}#o", e, kept,
                            {"label": "o", "copy": False, "kto": True, "weight": 1.0, "weight_good": w_good, "weight_bad": w_bad,
                             "run_solved": e["label"] == "good"}))
            stats["labelled episodes"] += 1
    assert not {e["task"] for _, e, _, _ in out_eps} & excl, "a held-out task reached the training data"
    assert len({eid for eid, _, _, _ in out_eps}) == len(out_eps), "episode ids must be unique"
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "requests_pref.jsonl", "w") as fr, open(out / "status.jsonl", "w") as fs:
        for eid, e, kept, meta in out_eps:
            split = "val" if is_val(e["task"], a.val_share) else "train"
            for r in kept:
                fr.write(json.dumps(dict(r, episode_id=eid, attempt=e["attempt"])) + "\n")
            fs.write(json.dumps(dict(meta, id=eid, attempt=e["attempt"], status="ok", split=split, task=e["task"],
                                     category="pref", teacher=",".join(a.arms))) + "\n")
    print(f"\nmode {a.mode}: runs {dict(why.most_common())}")
    print(f"tasks {len(by)} | paired {sum(1 for v in by.values() if v['good'] and v['bad'])} | " +
          " | ".join(f"{k} {v}" for k, v in sorted(stats.items())))
    return stats


if __name__ == "__main__":
    main()
