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
Held-out safety: tasks listed in --exclude (one id per line, or a json list) are refused; the run stops if any appear.
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
    ap.add_argument("--exclude", nargs="*", default=[], help="held-out task id files (refused)")
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
                raise SystemExit(f"HELD-OUT task {iid} found in {d}: refusing to build training data from it")
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
                if bad_rule:
                    why[f"good dropped: {bad_rule}"] += 1
                    continue
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
