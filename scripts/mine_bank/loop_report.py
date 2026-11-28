"""Loop report for an A/B run (user 2026-11-26: 'yes add the loop-break step and the loop report'): does an arm (e.g. sk_a2 +
LoRA adapter) loop more than its control? Per arm, from the request logs of one or more skill-arm result folders:
  solved, no patch, time ends, mean agent seconds;
  retry streak      runs with 2+ failed calls in a row / with 4+ in a row; the longest streak;
  repeats           identical calls again with no applied edit since (per run; runs with one call repeated 3+ times);
  submit loop       runs calling submit_patch 3+ times;
  maxed thinking    replies with >= 1,950 thinking tokens (sk_a2's cap 2,048) per run;
  loop break        stuck runs (2+ failed / repeated calls in a row) whose next working, different call came (share).
Run: data/venv_train/bin/python -I scripts/mine_bank/loop_report.py DIR [DIR ...] [--arms A B] [--tokenizer-dir D]"""
import argparse, ast, collections, json, re, statistics as S, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "train"))
from selfdistill_episodes import failed  # noqa: E402

EDIT_RUN = re.compile(r"sed\s+-i|git\s+apply|patch\s+-p|OLD_TEXT|\.replace\(|old_string")


def parse(x):
    if isinstance(x, dict):
        return x
    try:
        return ast.literal_eval(str(x))
    except Exception:
        try:
            return json.loads(str(x))
        except Exception:
            return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--arms", nargs="*", default=None)
    ap.add_argument("--tokenizer-dir", default=None)
    ap.add_argument("--tasks", nargs="*", default=None, help="only these task ids")
    ap.add_argument("--json", default=None, help="also write the per-arm numbers here (the final test's bars)")
    a = ap.parse_args()
    tok = None
    if a.tokenizer_dir:
        from tokenizers import Tokenizer
        tok = Tokenizer.from_file(str(Path(a.tokenizer_dir) / "tokenizer.json"))
    ntok = (lambda s: len(tok.encode(s).ids)) if tok else (lambda s: len(s) // 3)
    rows = []
    for d in a.dirs:
        G = {}
        for l in open(Path(d) / "results/gen_per_task.jsonl"):
            g = json.loads(l)
            if g.get("resolved") is not None and (not a.arms or g["arm"] in a.arms) and (not a.tasks or g["instance_id"] in a.tasks):
                G[g["instance_id"] + "#a" + str(g["attempt"])] = g
        by = collections.defaultdict(list)
        with open(Path(d) / "requests/requests.jsonl", errors="replace") as fh:
            for l in fh:
                try:
                    r = json.loads(l)
                except ValueError:
                    continue
                if r.get("job") in G:
                    by[r["job"]].append(r)
        for job, rs in by.items():
            g = G[job]
            rs.sort(key=lambda r: float(r["t"]))
            res = {m.get("tool_call_id"): str(m.get("content")) for r in rs for m in r["request"]["messages"] if m.get("role") == "tool"}
            streak = worst = submits = maxed = 0
            repeats, counts, seen, applied = 0, collections.Counter(), {}, 0
            stuck, breaks, stuck_runs = 0, 0, 0
            for r in rs:
                m = (parse(r.get("reply")) or {}).get("message") or {}
                if ntok(m.get("reasoning_content") or "") >= 1950:
                    maxed += 1
                for c in m.get("tool_calls") or []:
                    fn = c.get("function") or {}
                    try:
                        args = json.loads(fn.get("arguments") or "{}")
                    except Exception:
                        args = {}
                    args = args if isinstance(args, dict) else {}
                    o = res.get(c.get("id"), "")
                    try:
                        od = json.loads(o)
                    except Exception:
                        od = {"raw": o}
                    bad = failed(fn.get("name"), args, od if isinstance(od, dict) else {"raw": o})
                    key = fn.get("name") + json.dumps(args, sort_keys=True)
                    rep = fn.get("name") not in ("get_status", "submit_patch") and seen.get(key) == applied
                    repeats += rep
                    counts[key] += 1
                    if stuck >= 2 and not bad and not rep:
                        breaks += 1
                    if stuck == 1 and (bad or rep):
                        stuck_runs += 1
                    stuck = stuck + 1 if (bad or rep) else 0
                    streak = streak + 1 if bad else 0
                    worst = max(worst, streak)
                    seen[key] = applied
                    cmd = str(args.get("command", ""))
                    applied += (not bad) and (fn.get("name") == "edit_file" or (fn.get("name") == "run_command" and "a.py" not in cmd and bool(EDIT_RUN.search(cmd))))
                    submits += fn.get("name") == "submit_patch"
            rows.append(dict(arm=g["arm"], task=g["instance_id"], ok=g["resolved"] in (True, "True"), patch=int(g.get("patch_chars") or 0), end=g.get("end"),
                             agent=float(g.get("agent_s") or 0), worst=worst, repeats=repeats, max_same=max(counts.values(), default=0),
                             submits=submits, maxed=maxed, stuck=stuck_runs, breaks=breaks))
    print(f"{'arm':14} {'runs':>4} {'solved':>7} {'no patch':>8} {'time':>5} {'agent s':>7} | {'streak2+':>8} {'streak4+':>8} {'longest':>7} | "
          f"{'repeats/run':>11} {'same call 3+':>12} | {'submit 3+':>9} | {'maxed/run':>9} | {'stuck runs':>10} {'breaks':>6}")
    for arm in sorted({r["arm"] for r in rows}):
        R = [r for r in rows if r["arm"] == arm]
        n = len(R)
        pc = lambda f: f"{sum(f(r) for r in R) / n:.0%}"
        print(f"{arm[:14]:14} {n:4} {pc(lambda r: r['ok']):>7} {pc(lambda r: r['patch'] == 0):>8} {pc(lambda r: r['end'] == 'time'):>5} "
              f"{S.mean(r['agent'] for r in R):7.0f} | {pc(lambda r: r['worst'] >= 2):>8} {pc(lambda r: r['worst'] >= 4):>8} "
              f"{max(r['worst'] for r in R):7} | {S.mean(r['repeats'] for r in R):11.2f} {pc(lambda r: r['max_same'] >= 3):>12} | "
              f"{pc(lambda r: r['submits'] >= 3):>9} | {S.mean(r['maxed'] for r in R):9.2f} | {sum(r['stuck'] for r in R):10} {sum(r['breaks'] for r in R):6}")
    if a.json:
        out = {}
        for arm in sorted({r["arm"] for r in rows}):
            R = [r for r in rows if r["arm"] == arm]
            n = len(R)
            out[arm] = {"runs": n, "solved": sum(r["ok"] for r in R), "no_patch": sum(r["patch"] == 0 for r in R),
                        "time": sum(r["end"] == "time" for r in R), "agent_s": S.mean(r["agent"] for r in R),
                        "streak2_share": sum(r["worst"] >= 2 for r in R) / n, "same3_share": sum(r["max_same"] >= 3 for r in R) / n,
                        "submit3": sum(r["submits"] >= 3 for r in R), "repeats_per_run": S.mean(r["repeats"] for r in R),
                        "maxed_per_run": S.mean(r["maxed"] for r in R)}
        Path(a.json).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
