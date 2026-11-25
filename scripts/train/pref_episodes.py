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
Pairs: --paired-only (default on) keeps bad runs only for tasks that also have a good run (the same task passed and
failed: the contrast plan B trains on). Good runs of always-solved tasks are kept (they feed the copy term).
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
from selfdistill_episodes import analyse  # noqa: E402

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


def reply_calls(r):
    out = []
    for c in ((r.get("reply") or {}).get("message") or {}).get("tool_calls") or []:
        fn = c.get("function") or {}
        try:
            a = json.loads(fn.get("arguments") or "{}") if isinstance(fn.get("arguments"), str) else (fn.get("arguments") or {})
        except ValueError:
            a = {}
        out.append((fn.get("name"), a if isinstance(a, dict) else {}))
    return out


def source_edit(name, a):
    path, cmd = str(a.get("filepath", a.get("path", ""))), str(a.get("command", ""))
    if name in ("edit_file", "write_file"):
        return bool(path) and not path.startswith(".git/") and not path.startswith("/tmp") and not TEST_FILE.search(path)
    return name == "run_command" and "a.py" not in cmd and bool(EDIT_RUN.search(cmd))


def flag_decisions(kept):
    """Mark the records whose reply answers the first budget warning / first banner seen with no source edit yet."""
    seen, edited, n = set(), False, 0
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
        if any(source_edit(nm, a) for nm, a in reply_calls(r)):
            edited = True
    return n


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
    ap.add_argument("--paired-only", type=int, default=1, help="bad runs only for tasks that also have a good run")
    ap.add_argument("--max-fail-streak", type=int, default=3)
    ap.add_argument("--max-repeats", type=int, default=3)
    ap.add_argument("--val-share", type=float, default=0.12)
    a = ap.parse_args()
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
            m, kept = analyse(rs, dict(g, resolved=solved), tasks[iid], patches.get(key, ""))
            if solved:
                bad_rule = next((w for w, b in [("edits tests", m["test_files_edited"]), ("leaves scratch files", m["scratch_files"]),
                                                ("fail streak", m["max_fail_streak"] > a.max_fail_streak),
                                                ("repeats calls", m["repeats"] > a.max_repeats), ("junk text", m["junk_replies"] > 0),
                                                ("no submit", not m["submitted"])] if b), None)
                rd, te = broken_rules(kept)
                bad_rule = bad_rule or ("reads code outside a.py" if rd else None) or ("edits a test file" if te else None)
                if bad_rule:
                    why[f"good dropped: {bad_rule}"] += 1
                    continue
            m["decisions"] = flag_decisions(kept)
            eps.append(dict(task=iid, attempt=key[1], label="good" if solved else "bad", kept=kept, m=m,
                            agent_s=float(g.get("agent_s") or 0), src=str(d)))
            why["good" if solved else "bad"] += 1
    by = collections.defaultdict(lambda: {"good": [], "bad": []})
    for e in eps:
        by[e["task"]][e["label"]].append(e)
    chosen = []
    for t, v in sorted(by.items()):
        good = sorted(v["good"], key=lambda e: e["agent_s"])[:a.cap]
        bad = [] if (a.paired_only and not good) else sorted(v["bad"], key=lambda e: e["attempt"])[:a.cap]
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
                                 "task": e["task"], "category": "pref", "teacher": ",".join(a.arms)}) + "\n")
    with open(out / "metrics.jsonl", "w") as fh:
        for e in eps:
            fh.write(json.dumps(dict(e["m"], task=e["task"], attempt=e["attempt"], label=e["label"], src=e["src"])) + "\n")
    paired = [t for t, v in by.items() if v["good"] and v["bad"]]
    C = collections.Counter((("val" if is_val(e["task"], a.val_share) else "train"), e["label"]) for e in chosen)
    print(f"\nruns: {dict(why.most_common())}")
    print(f"tasks: {len(by)} | with both outcomes (paired): {len(paired)} | only solved: "
          f"{sum(1 for v in by.values() if v['good'] and not v['bad'])} | only failed: {sum(1 for v in by.values() if v['bad'] and not v['good'])}")
    print(f"KEPT {len(chosen)} episodes (cap {a.cap}/label/task): train good {C['train', 'good']} bad {C['train', 'bad']} | "
          f"val good {C['val', 'good']} bad {C['val', 'bad']} | repos {len({re.sub(r'[-_][0-9]+$', '', e['task']) for e in chosen})}")


if __name__ == "__main__":
    main()
