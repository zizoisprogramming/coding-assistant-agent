"""Where mix loses tasks: per-run behaviour features from generation request logs, then failure buckets.

    python3 scripts/triage.py extract GEN_DIR [GEN_DIR ...] --out runs.jsonl
    python3 scripts/triage.py report runs.jsonl [...] [--gold tasks.jsonl ...] [--regrade regrade.json]

GEN_DIR = a generation output (requests/requests.jsonl + results/gen_per_task.jsonl [+ results/gen/patches/]).
`extract` keeps no conversation text (only counts, tool names, file paths), so its output is small and safe to
download. `report` joins the gold patches (which files the reference fix touches) and the public re-grade, puts every
run in ONE failure bucket and prints the tables. Buckets, first match wins:
  resolved | env error | no edit: tool budget | no edit: time/turns | no edit: stopped | edit refused by budget |
  wrong files | right files, no test after last edit | right files, tested (wrong fix) | files unknown
"""
import argparse
import collections
import json
import re
import statistics
import sys
from pathlib import Path

SUMMARY_PREFIX = "The following is a conversation history"
EDIT_TOOLS = ("edit_file", "write_file")


def kind(name, args):
    cmd = (args.get("command") or "").strip()
    if name in EDIT_TOOLS:
        return "scratch" if str(args.get("filepath", "")).startswith("/tmp") else "edit"
    if name == "run_command":
        if re.search(r"sed -i|open\([^)]*['\"]w['\"]\)|\.write_text\(", cmd):
            return "edit"
        if re.search(r"pytest|unittest|tox |nox ", cmd):
            return "test"
        if re.match(r"(python3?|cat\s*>+)\s*(/tmp|-c|-\s*<<)", cmd) or "/tmp/" in cmd.split("|")[0]:
            return "repro"
        if re.search(r"sed -n|^cat |^head|^tail|^nl ", cmd):
            return "read"
        if re.search(r"grep|^find|^ls|git (ls-files|log|show|blame)", cmd):
            return "search"
        if re.match(r"git (status|diff)", cmd):
            return "diff"
        return "cmd"
    return {"read_file": "read", "submit_patch": "submit", "get_status": "status"}.get(name, name)


def parse(s):
    try:
        d = json.loads(s) if isinstance(s, str) else s
    except Exception:
        return {}
    return d if isinstance(d, dict) else {}


def extract(gen_dir):
    gen_dir = Path(gen_dir)
    rows = {f"{r['instance_id']}#a{r['attempt']}": r for r in map(json.loads, open(gen_dir / "results/gen_per_task.jsonl"))}
    jobs = collections.defaultdict(list)  # job -> [(t, seconds, request last msgs, reply)] compact
    results = {}  # tool_call_id -> (status, error_type)
    bad = 0
    with open(gen_dir / "requests/requests.jsonl") as f:
        for line in f:
            try:
                r = json.loads(line)
            except Exception:
                bad += 1
                continue
            if not r.get("job") or not isinstance(r.get("request"), dict):
                bad += 1
                continue
            msgs = r["request"].get("messages") or []
            for m in msgs:
                if m.get("role") == "tool" and m.get("tool_call_id") not in results:
                    d = parse(m.get("content"))
                    results[m["tool_call_id"]] = (d.get("status"), d.get("error_type"))
            last = msgs[-1] if msgs else {}
            summary = last.get("role") == "user" and str(last.get("content") or "").startswith(SUMMARY_PREFIX)
            msg = (r.get("reply") or {}).get("message") or {}
            calls = [(t.get("id"), (t.get("function") or {}).get("name"), parse((t.get("function") or {}).get("arguments")))
                     for t in msg.get("tool_calls") or []]
            jobs[r["job"]].append(dict(t=r.get("t") or 0, s=r.get("seconds") or 0, summary=summary, calls=calls,
                                       think=len(msg.get("reasoning_content") or ""), text=len(msg.get("content") or "")))
    if bad:
        print(f"{gen_dir}: {bad} unreadable request-log lines skipped", file=sys.stderr)
    out = []
    for job, recs in jobs.items():
        recs.sort(key=lambda x: x["t"])
        g = rows.get(job, {})
        f = dict(job=job, src=gen_dir.name, instance_id=job.split("#")[0], attempt=job.split("#a")[-1],
                 **{k: g.get(k) for k in ("resolved", "end", "agent_s", "patch_chars", "level", "domain", "text_kind",
                                          "leak", "unfair", "env_partial", "split", "tool_calls", "llm_calls", "error")})
        seq, t0, think_before_edit, s_before_edit, after_budget = [], recs[0]["t"] - recs[0]["s"], 0, None, 0.0
        for rec in recs:
            if any(c["err"] == "BudgetExceeded" for c in seq):  # every model call after the first refusal is waste
                after_budget += rec["s"]
            if rec["summary"]:
                continue
            for cid, name, args in rec["calls"]:
                st, et = results.get(cid, (None, None))
                seq.append(dict(k=kind(name, args), name=name, ok=st != "error", err=et,
                                file=str(args.get("filepath") or ""), t=rec["t"] - t0))
            if s_before_edit is None:
                think_before_edit += rec["think"]
                if any(c["k"] == "edit" and c["ok"] for c in seq):
                    s_before_edit = rec["t"] - t0
        real = [c for c in seq if c["err"] != "BudgetExceeded" and c["k"] != "status"]  # get_status is free
        edits = [i for i, c in enumerate(real) if c["k"] == "edit"]
        ok_edits = [i for i in edits if real[i]["ok"]]
        fails, streak, worst = 0, 0, 0
        for c in real:
            streak = streak + 1 if not c["ok"] else 0
            worst = max(worst, streak)
            fails += not c["ok"]
        reads = collections.Counter(c["file"] for c in real if c["k"] == "read" and c["file"])
        last_edit = ok_edits[-1] if ok_edits else None
        f.update(
            calls=sum(c["k"] != "submit" for c in real),  # work calls (repeated submits counted apart)
            kinds=dict(collections.Counter(c["k"] for c in real if c["k"] != "submit")),
            first_edit=(edits[0] + 1) if edits else None, first_ok_edit=(ok_edits[0] + 1) if ok_edits else None,
            edits_ok=len(ok_edits), edits_failed=len(edits) - len(ok_edits),
            edit_errors=dict(collections.Counter(c["err"] for c in real if c["k"] == "edit" and not c["ok"])),
            budget_refused=dict(collections.Counter(c["k"] for c in seq if c["err"] == "BudgetExceeded")),
            submits=sum(c["k"] == "submit" for c in seq), failed=fails, max_fail_streak=worst,
            max_reads_one_file=max(reads.values(), default=0),
            tested_after_edit=last_edit is not None and any(c["k"] in ("test", "repro") for c in real[last_edit + 1:]),
            tests=sum(c["k"] == "test" for c in real), repros=sum(c["k"] == "repro" for c in real),
            edited_files=sorted({c["file"].removeprefix("/workspace/") for c in real if c["k"] == "edit" and c["ok"] and c["file"]}),
            compactions=sum(r["summary"] for r in recs), text_replies=sum(1 for r in recs if not r["summary"] and not r["calls"]),
            think_chars=sum(r["think"] for r in recs if not r["summary"]), think_before_edit=think_before_edit,
            s_first_edit=round(s_before_edit) if s_before_edit is not None else None,
            llm_s=round(sum(r["s"] for r in recs)), llm_s_after_budget=round(after_budget))
        pf = gen_dir / "results/gen/patches" / f"{f['instance_id']}__a{f['attempt']}.diff"
        if pf.exists():
            f["patch_files"] = sorted(diff_files(pf.read_text()))
        out.append(f)
    return out


def diff_files(diff):
    files = set(re.findall(r"^diff --git a/(\S+)", diff or "", re.M))
    files |= set(re.findall(r"^\+\+\+ b/(\S+)", diff or "", re.M))
    files |= set(re.findall(r"^--- a/(\S+)\n\+\+\+ /dev/null", diff or "", re.M))
    return files


def bucket(r, gold):
    files = set(r.get("patch_files") or r.get("edited_files") or [])
    if r.get("resolved"):
        return "resolved"
    if r.get("end") == "env":
        return "env error"
    if not r.get("edits_ok") and not r.get("patch_chars"):
        if r.get("budget_refused"):
            return "no edit: tool budget"
        if r.get("end") in ("time", "turns"):
            return "no edit: time/turns"
        return "no edit: stopped"
    if r.get("budget_refused", {}).get("edit"):
        return "edit refused by budget"
    g = gold.get(r["instance_id"])
    if not g or not files:
        return "files unknown"
    if not (files & g):
        return "wrong files"
    return "right files, tested (wrong fix)" if r.get("tested_after_edit") else "right files, no test after last edit"


def report(paths, gold_paths, regrade):
    runs = [json.loads(l) for p in paths for l in open(p)]
    gold = {}
    for p in gold_paths:
        for t in map(json.loads, open(p)):
            gold[t["instance_id"]] = {f for f in diff_files(t.get("patch")) if not re.search(r"(^|/)tests?/|test_|conftest", f)}
    if regrade:
        rg = json.load(open(regrade))
        for r in runs:
            if r["instance_id"] in rg and r.get("level") == "public":
                r["resolved"] = bool(rg[r["instance_id"]].get("resolved"))
    for r in runs:
        r["bucket"] = bucket(r, gold)
    n = len(runs)
    print(f"{n} runs, {len({r['instance_id'] for r in runs})} tasks, resolved {sum(bool(r['resolved']) for r in runs)} "
          f"({100 * sum(bool(r['resolved']) for r in runs) / n:.0f}%), gold files known for "
          f"{sum(r['instance_id'] in gold for r in runs)} runs\n")
    print("FAILURE BUCKETS (one per run)")
    for b, k in collections.Counter(r["bucket"] for r in runs).most_common():
        print(f"  {b:38} {k:4}  {100 * k / n:4.1f}%")

    def med(xs):
        xs = [x for x in xs if x is not None]
        return f"{statistics.median(xs):.0f}" if xs else "-"

    print("\nBEHAVIOUR: resolved vs not (medians / shares)")
    for name, sel in (("resolved", [r for r in runs if r["resolved"]]), ("not resolved", [r for r in runs if not r["resolved"]])):
        m = len(sel) or 1
        print(f"  {name:13} n={len(sel):4} | calls {med(r['calls'] for r in sel)} | first edit at call "
              f"{med(r['first_ok_edit'] for r in sel)} | s to first edit {med(r['s_first_edit'] for r in sel)} | think chars "
              f"{med(r['think_chars'] for r in sel)} | tested after edit {100 * sum(r['tested_after_edit'] for r in sel) / m:.0f}% "
              f"| budget hit {100 * sum(bool(r['budget_refused']) for r in sel) / m:.0f}% | submit loop (>=3) "
              f"{100 * sum(r['submits'] >= 3 for r in sel) / m:.0f}% | fail streak>=3 {100 * sum(r['max_fail_streak'] >= 3 for r in sel) / m:.0f}%")
    print("\nSOLVE RATE by when the first successful edit happened (call number)")
    for lo, hi in ((1, 8), (9, 12), (13, 16), (17, 20), (21, 24), (25, 99)):
        sel = [r for r in runs if r["first_ok_edit"] and lo <= r["first_ok_edit"] <= hi]
        if sel:
            print(f"  calls {lo:2}-{hi:2}: {len(sel):4} runs, resolved {100 * sum(bool(r['resolved']) for r in sel) / len(sel):3.0f}%")
    sel = [r for r in runs if not r["first_ok_edit"]]
    print(f"  never   : {len(sel):4} runs, resolved {100 * sum(bool(r['resolved']) for r in sel) / max(len(sel), 1):3.0f}%")
    print("\nWASTE")
    print(f"  runs with >=3 submit_patch calls: {sum(r['submits'] >= 3 for r in runs)} "
          f"(median {med(r['submits'] for r in runs if r['submits'] >= 3)} submits)")
    print(f"  model seconds after the tool budget ran out: {sum(r['llm_s_after_budget'] for r in runs) / 3600:.1f} h total")
    print(f"  failed edits: {sum(r['edits_failed'] for r in runs)} "
          f"{dict(sum((collections.Counter(r['edit_errors']) for r in runs), collections.Counter()))}")
    print(f"  compactions: {sum(r['compactions'] for r in runs)} in {sum(r['compactions'] > 0 for r in runs)} runs")
    print("\nCALL MIX (share of all calls): resolved vs not")
    for name, sel in (("resolved", [r for r in runs if r["resolved"]]), ("not resolved", [r for r in runs if not r["resolved"]])):
        c = sum((collections.Counter(r["kinds"]) for r in sel), collections.Counter())
        tot = sum(c.values()) or 1
        print(f"  {name:13} " + " ".join(f"{k} {100 * v / tot:.0f}%" for k, v in c.most_common()))
    print("\nBUCKETS by task group")
    groups = collections.defaultdict(collections.Counter)
    for r in runs:
        groups[r.get("level")][r["bucket"]] += 1
    for gname, c in sorted(groups.items(), key=lambda x: str(x[0])):
        tot = sum(c.values())
        print(f"  {str(gname):8} n={tot:4} " + " | ".join(f"{b} {v}" for b, v in c.most_common()))
    return runs


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract")
    e.add_argument("dirs", nargs="+")
    e.add_argument("--out", required=True)
    rp = sub.add_parser("report")
    rp.add_argument("runs", nargs="+")
    rp.add_argument("--gold", nargs="*", default=[])
    rp.add_argument("--regrade")
    a = ap.parse_args()
    if a.cmd == "extract":
        with open(a.out, "w") as f:
            for d in a.dirs:
                rows = extract(d)
                for r in rows:
                    f.write(json.dumps(r) + "\n")
                print(f"{d}: {len(rows)} runs", file=sys.stderr, flush=True)
    else:
        report(a.runs, a.gold, a.regrade)


if __name__ == "__main__":
    main()
