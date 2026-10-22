"""Self-distillation episodes from our generation runs (kaggle/cells_gen): one episode per (task, attempt) from the
request log (records tagged job = '<instance_id>#a<attempt>'), behaviour metrics, the cut after the first submit,
the quality filter, and the stage-B layout build_samples.py reads.

    python scripts/train/selfdistill_episodes.py --gen <generation output dir> [...] --tasks <task set tasks.jsonl> --out <dir>

Cut (2026-10-22, trial logs): the base model itself loops after submitting (submit_patch called again and again,
'Bye.' / 'End.' / 'Exiting turn.' turns, up to 81 calls in a resolved run) and some final replies are malformed (the
thought channel leaks into the content, a tool call written as text). Training on that teaches the loop. So every
episode ends at its FIRST successful submit_patch call, plus the next reply only if it is a clean final message (text,
no tool call, no channel markup, no junk); everything after is dropped.

Filter (defaults, decided 2026-10-20/22; every threshold is an argument; all counted up to the cut): resolved;
submitted; the final diff touches at least one file of the reference fix, no test file and adds no scratch file; read
or searched before the first edit (scratch scripts are not edits); at most 3 failed calls in a row; at most 2 repeats
(the same call again with no edit since its last use); at most 2 rereads of lines already read (no edit since); at most 1 text-only turn before the submit;
no junk text (runs of '*', long blank runs, channel markup) in any kept reply.
"""
import argparse
import collections
import hashlib
import json
import re
from pathlib import Path

EDIT_CMD = re.compile(r"sed\s+-i|git\s+apply|\bpatch\s+-p")  # scratch scripts (cat > x.py) are not edits
SEARCH_CMD = re.compile(r"\b(grep|git\s+grep|find|ls|cat|sed\s+-n|head|tail|rg|awk|git\s+(log|show|diff|ls-files))\b")
JUNK = re.compile(r"\*{6,}|\n{8,}|<\|channel>|<channel\|>|<\|tool_call>|^\s*(get_status|submit_patch|run_command|read_file)\s*[{(]", re.M)
# The final reply when the model's own was junk or missing (2026-10-22): the stage-B bug was a final turn WITHOUT
# thinking (the model then learned thinking is always followed by a tool call and repeated submit_patch).
FINAL_THOUGHT = "The fix is in place and the patch is submitted, so the task is complete and I stop here."
FINAL_TEXT = "I fixed the issue and submitted the patch."


def final_reply(thought, text):
    """A final answer as the model generates it: Gemma's chat template DROPS the thinking of a final (tool-call-free)
    assistant turn (chat_template.jinja: thinking only before tool calls; strip_thinking on content), so rendering it
    trains 'answer without thinking' (the stage-B loop bug). 'raw' = the model's own output format; build_samples
    appends it to the prompt as is (after a tool result the model's turn just continues: no new turn header)."""
    thought, text = (thought or "").strip(), (text or "").strip()
    raw = (f"<|channel>thought\n{thought}\n<channel|>" if thought else "") + text
    return {"content": text, "reasoning_content": thought or None, "tool_calls": None, "raw": raw}


TEST_PATH = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)conftest\.py$")


def reply_of(rec):
    rep = rec.get("reply")
    return rep.get("message") or {} if isinstance(rep, dict) else {}


def tool_results(records):
    """tool_call_id -> parsed tool output (JSON dict when possible) from every request's tool messages."""
    out = {}
    for r in records:
        for m in r["request"]["messages"]:
            if m.get("role") == "tool" and m.get("tool_call_id"):
                c = m.get("content")
                c = c if isinstance(c, str) else json.dumps(c)
                try:
                    out[m["tool_call_id"]] = json.loads(c)
                except (ValueError, TypeError):
                    out[m["tool_call_id"]] = {"raw": c}
    return out


def args_of(call):
    a = call.get("function", {}).get("arguments") or "{}"
    try:
        return json.loads(a) if isinstance(a, str) else a
    except ValueError:
        return {"_raw": a}


def failed(name, args, res):
    if not isinstance(res, dict):
        return False
    if res.get("status") == "error":
        return True
    if name == "run_command" and res.get("exit_code") not in (None, 0):
        cmd = str(args.get("command", ""))
        return not (res.get("exit_code") == 1 and re.match(r"\s*(git\s+grep|grep|rg)\b", cmd))  # no match is not a failure
    return False


def is_edit(name, args):
    if name == "edit_file":
        return True
    if name == "write_file":
        p = str(args.get("filepath") or args.get("path") or "")
        return not p.startswith("/tmp")
    return name == "run_command" and bool(EDIT_CMD.search(str(args.get("command", ""))))


def is_look(name, args):
    return name in ("read_file", "get_code_neighbors", "search_similar_code", "get_code_subgraph") or (
        name == "run_command" and bool(SEARCH_CMD.search(str(args.get("command", "")))))


def clean_text(s):
    return not JUNK.search(s or "")


def diff_files(diff):
    return set(re.findall(r"^diff --git a/(\S+)", diff or "", re.M))


# Doubt words in the thinking (arXiv 2603.24472, "epistemic verbalization": self-distillation that keeps only confident,
# short reasoning made models worse on new problems). Same 10 markers as the paper; rate per 1,000 words of thinking.
DOUBT = re.compile(r"\b(wait|hmm|perhaps|maybe|actually|alternatively|seems|might|likely|check)\b", re.I)


def doubt_rate(records):
    text = " ".join((reply_of(r).get("reasoning_content") or reply_of(r).get("reasoning") or "")
                    for r in records if r["request"].get("tools"))
    words = len(text.split())
    return round(1000 * len(DOUBT.findall(text)) / words, 2) if words else None, words


def analyse(records, row, task, patch):
    """Metrics, the cut (records kept) and the filter verdict for one episode. records: time order, tools-bearing and
    summary calls mixed (summary calls have no tools; they stay, build_samples skips them)."""
    results = tool_results(records)
    calls, text_turns, cut_at, final_ok, junk = [], 0, None, False, 0
    for k, rec in enumerate(records):
        if not rec["request"].get("tools"):
            continue
        msg = reply_of(rec)
        tcs = msg.get("tool_calls") or []
        thought = (msg.get("reasoning_content") or msg.get("reasoning") or "")
        if cut_at is not None:  # the reply after the first successful submit: kept only if a clean final message
            final_ok = not tcs and bool((msg.get("content") or "").strip()) and clean_text(msg.get("content")) \
                and clean_text(thought)
            if final_ok:
                cut_at = k
            break
        if not clean_text(thought) or not clean_text(msg.get("content") if isinstance(msg.get("content"), str) else ""):
            junk += 1
        if not tcs:
            text_turns += 1
            continue
        for c in tcs:
            name, args = c.get("function", {}).get("name"), args_of(c)
            res = results.get(c.get("id"))
            calls.append((name, json.dumps(args, sort_keys=True), args, res))
            if name == "submit_patch" and isinstance(res, dict) and res.get("status") != "error" and cut_at is None:
                cut_at = k
    kept = records[:cut_at + 1] if cut_at is not None else records
    if final_ok:  # the model's own clean final reply: its thinking written into the trained text (see final_reply)
        own = reply_of(kept[-1])
        kept[-1] = dict(kept[-1], reply={"message": final_reply(own.get("reasoning_content") or own.get("reasoning") or "",
                                                                own.get("content") or ""), "finish_reason": "stop"})
    synthetic = False
    if cut_at is not None and not final_ok:  # the model's own final reply was junk / missing: a clean one, with thinking
        j = next((i for i in range(cut_at + 1, len(records)) if records[i]["request"].get("tools")), None)
        if j is not None:  # its prompt = the conversation through the submit result (any compaction in between kept)
            nxt = records[j]
            kept = kept + records[cut_at + 1:j] + [dict(nxt, reply={"message": final_reply(FINAL_THOUGHT, FINAL_TEXT),
                                                                    "finish_reason": "stop", "synthetic": True})]
            synthetic = True
    if cut_at is not None:  # metrics on what is trained: calls up to and including the first submit
        n_before = sum(len(reply_of(r).get("tool_calls") or []) for r in records[:cut_at + 1] if r["request"].get("tools"))
        calls = calls[:n_before]
    streak = worst = 0
    for name, _, args, res in calls:
        streak = streak + 1 if failed(name, args, res) else 0
        worst = max(worst, streak)
    # a repeat = the same call again with no edit since its last use (re-running a test after an edit is fine)
    last_seen, repeats, edits = {}, 0, 0
    for name, key, args, _ in calls:
        if name == "get_status":
            continue
        if key in last_seen and last_seen[key] == edits:
            repeats += 1
        last_seen[key] = edits
        edits += is_edit(name, args)
    reads = collections.Counter(str(a.get("filepath") or a.get("path")) for n, _, a, _ in calls if n == "read_file")
    # a true reread: lines already read in that file, with no edit to the file since (reading a long file in several
    # different chunks is normal: 52 of 153 resolved full-run attempts read one file 5-17 times, mostly new ranges)
    seen, rereads = collections.defaultdict(list), 0
    for n, _, a, _ in calls:
        path = str(a.get("filepath") or a.get("path") or "")
        if n == "read_file":
            try:
                lo, hi = int(a.get("start_line") or 1), int(a.get("end_line") or 10 ** 9)
            except (TypeError, ValueError):
                lo, hi = 1, 10 ** 9
            if any(min(hi, h) - max(lo, l) >= 0.5 * max(1, min(hi - lo, h - l)) for l, h in seen[path]):
                rereads += 1
            seen[path].append((lo, hi))
        elif is_edit(n, a):
            seen.pop(path, None)  # after an edit to this file, reading it again is checking the edit
    first_edit = next((i for i, (n, _, a, _) in enumerate(calls) if is_edit(n, a)), None)
    looks_before = sum(is_look(n, a) for n, _, a, _ in calls[:first_edit]) if first_edit is not None else 0
    agent_files, gold_files = diff_files(patch), diff_files(task["patch"])
    m = {
        "resolved": bool(row["resolved"]), "submitted": cut_at is not None,
        "final_turn": "own" if final_ok else "synthetic" if synthetic else "none",
        "calls": len(calls), "text_turns": text_turns, "max_fail_streak": worst,
        "repeats": repeats, "max_reads_one_file": max(reads.values(), default=0), "rereads": rereads,
        "scratch_files": sorted(f for f in re.findall(r"^diff --git a/(\S+) b/\S+\nnew file mode", patch or "", re.M)
                                if f not in gold_files),
        "looks_before_edit": looks_before, "edited": first_edit is not None, "junk_replies": junk,
        "gold_file_hit": bool(agent_files & gold_files), "test_files_edited": sorted(f for f in agent_files if TEST_PATH.search(f)),
        "records_total": len(records), "records_kept": len(kept),
    }
    # thinking up to and including the first submit (the trained part), else the whole run
    m["doubt_per_1k"], m["think_words"] = doubt_rate(records[:cut_at + 1] if cut_at is not None else records)
    return m, kept


def verdict(m, a):
    """First failed rule, or 'keep'."""
    rules = [("not resolved", not m["resolved"]), ("no submit", not m["submitted"]),
             ("misses the fixed files", not m["gold_file_hit"]), ("edits tests", bool(m["test_files_edited"])),
             ("leaves scratch files", bool(m["scratch_files"])),
             ("edits before looking", m["looks_before_edit"] < a.min_looks), ("fail streak", m["max_fail_streak"] > a.max_fail_streak),
             ("repeats calls", m["repeats"] > a.max_repeats), ("rereads lines", m["rereads"] > a.max_rereads),
             ("text-only turns", m["text_turns"] > a.max_text_turns), ("junk text", m["junk_replies"] > 0)]
    return next((why for why, bad in rules if bad), "keep")


def load_gen(d):
    """(rows by (iid, attempt), records by (iid, attempt), patches by (iid, attempt)) from one generation output."""
    d = Path(d)
    rows = {}
    for p in sorted(d.glob("**/results/gen_per_task.jsonl")):
        for l in open(p):
            r = json.loads(l)
            rows[(r["instance_id"], r["attempt"])] = r
    recs = collections.defaultdict(list)
    for p in sorted(d.glob("**/requests/requests.jsonl")):
        with open(p) as fh:
            for l in fh:
                r = json.loads(l)
                job = r.get("job") or ""
                if "#a" in job:
                    iid, a = job.rsplit("#a", 1)
                    recs[(iid, int(a))].append(r)
    patches = {}
    for p in d.glob("**/results/gen/patches/*.diff"):
        iid, a = p.stem.rsplit("__a", 1)
        patches[(iid, int(a))] = p.read_text()
    for v in recs.values():
        v.sort(key=lambda r: r["t"])
    return rows, recs, patches


def val_split(iid, share):
    return int(hashlib.sha1(iid.encode()).hexdigest(), 16) % 1000 < share * 1000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", nargs="+", required=True, help="generation output dir(s) (results/ + requests/ inside)")
    ap.add_argument("--tasks", required=True, help="the task set's tasks.jsonl (reference patches, labels)")
    ap.add_argument("--out", required=True, help="stage-B layout for build_samples.py + metrics.jsonl")
    ap.add_argument("--min-looks", type=int, default=1)
    ap.add_argument("--max-fail-streak", type=int, default=3)
    ap.add_argument("--max-repeats", type=int, default=2)
    ap.add_argument("--max-rereads", type=int, default=2, help="reads of lines already read, no edit since")
    ap.add_argument("--max-text-turns", type=int, default=1)
    ap.add_argument("--val-share", type=float, default=0.1, help="share of tasks held out (by task id hash)")
    a = ap.parse_args()
    tasks = {json.loads(l)["instance_id"]: json.loads(l) for l in open(a.tasks)}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    metrics, why, kept_eps = [], collections.Counter(), []
    for d in a.gen:
        rows, recs, patches = load_gen(d)
        print(f"{d}: {len(rows)} attempts, {len(recs)} with records, {sum(r['resolved'] for r in rows.values())} resolved", flush=True)
        for key in sorted(rows):
            row, rs = rows[key], recs.get(key, [])
            if not rs:
                why["no records"] += 1
                continue
            m, kept = analyse(rs, row, tasks[key[0]], patches.get(key, ""))
            v = verdict(m, a)
            why[v] += 1
            t = tasks[key[0]]
            m.update({"instance_id": key[0], "attempt": key[1], "verdict": v, "source": str(d), "level": t["level"],
                      "domain": t["domain"], "leak": t["leak"], "unfair": bool(t["unfair_names"]), "text_kind": t["text_kind"]})
            metrics.append(m)
            if row["resolved"]:
                print(f"  {key[0][:44]:44} a{key[1]} {v:22} calls={m['calls']:2} fail_streak={m['max_fail_streak']} "
                      f"repeats={m['repeats']} rereads={m['rereads']} reads1={m['max_reads_one_file']} looks={m['looks_before_edit']} "
                      f"text={m['text_turns']} final_turn={m['final_turn']!s:5} kept {m['records_kept']}/{m['records_total']} records",
                      flush=True)
            if v == "keep":
                kept_eps.append((key, kept, m))
    # one run per task (the retry only ran unsolved tasks, so this rarely matters): the one with fewer calls
    best = {}
    for key, kept, m in kept_eps:
        if key[0] not in best or m["calls"] < best[key[0]][2]["calls"]:
            best[key[0]] = (key, kept, m)
    with open(out / "requests_selfdistill.jsonl", "w") as fr, open(out / "status.jsonl", "w") as fs:
        for iid, (key, kept, m) in sorted(best.items()):
            split = "val" if val_split(iid, a.val_share) else "train"
            for r in kept:
                fr.write(json.dumps(dict(r, episode_id=iid, attempt=f"a{key[1]}")) + "\n")
            fs.write(json.dumps({"id": iid, "attempt": f"a{key[1]}", "status": "ok", "split": split,
                                 "category": m["level"], "teacher": "gemma-31b-mix-T1.0"}) + "\n")
    with open(out / "metrics.jsonl", "w") as fh:
        for m in metrics:
            fh.write(json.dumps(m) + "\n")
    K = [m for _, _, m in best.values()]
    n = max(len(K), 1)
    print(f"\nverdicts: {dict(why.most_common())}")
    print(f"KEPT {len(best)} episodes (one per task) | val {sum(val_split(i, a.val_share) for i in best)} | "
          f"leaky text {100 * sum(m['leak'] for m in K) / n:.0f}% (public 34%) | unfair {100 * sum(m['unfair'] for m in K) / n:.0f}% "
          f"(public 12%) | final turn {dict(collections.Counter(m['final_turn'] for m in K))} | level {dict(collections.Counter(m['level'] for m in K))} "
          f"| domain {dict(collections.Counter(m['domain'] for m in K))}")
    kept_ids = {(m["instance_id"], m["attempt"]) for m in K}
    groups = {"kept": [m for m in metrics if (m["instance_id"], m["attempt"]) in kept_ids],
              "solved, rejected": [m for m in metrics if m["resolved"] and (m["instance_id"], m["attempt"]) not in kept_ids],
              "not solved": [m for m in metrics if not m["resolved"]]}
    med = lambda xs: sorted(xs)[len(xs) // 2] if xs else None  # noqa: E731
    print("DOUBT WORDS per 1k thinking words (arXiv 2603.24472; median | mean, thinking words median): " + " | ".join(
        f"{g} n={len(v)}: {med([m['doubt_per_1k'] for m in v if m['doubt_per_1k'] is not None])} | "
        f"{sum(m['doubt_per_1k'] or 0 for m in v) / max(len(v), 1):.1f}, {med([m['think_words'] for m in v])} words"
        for g, v in groups.items()))


if __name__ == "__main__":
    main()
