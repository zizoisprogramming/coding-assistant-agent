"""Turn a harness request log of OUR agent's runs (scripts/request_logger.py, e.g. pilot #2: mix on the 31B, 16
non-dev tasks) into stage-B-style episodes, so build_samples.py can make samples from them (validation set of
Gemma's own successful runs) and so they can be compared with the teacher data.

    python gemma_runs_to_episodes.py --requests requests.jsonl --task-results task_results.jsonl \
        --tasks data/tasks.jsonl --out <dir> [--split val_gemma] [--only-resolved]

Tasks ran concurrently, so records interleave. Each record is assigned to a task by: the problem statement in its
first user message (before any compaction) matched to tasks.jsonl; else any tool-call id it shares with an earlier
record of that task (after compaction the retained events keep their ids); summary calls by the problem statement
quoted in the text being summarised. Output: requests_<attempt>.jsonl (records tagged episode_id = instance id) and
status.jsonl (status ok, split <split>_ok / <split>_fail by resolved), the format build_samples.py reads. Competition data: stays in data/.
"""
import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--requests", required=True)
    ap.add_argument("--task-results", required=True)
    ap.add_argument("--tasks", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--split", default="val_gemma")
    ap.add_argument("--attempt", default="gemma_pilot2")
    ap.add_argument("--only-resolved", action="store_true")
    a = ap.parse_args()
    tasks = [json.loads(l) for l in open(a.tasks)]
    by_ps = {t["problem_statement"].strip()[:400]: t["instance_id"] for t in tasks}
    results = {json.loads(l)["instance_id"]: json.loads(l) for l in open(a.task_results)}
    recs = [json.loads(l) for l in open(a.requests)]
    recs.sort(key=lambda r: r["t"])
    owner_of_id, assigned, unassigned = {}, [], 0

    def ids_in(r):
        out = set()
        for m in r["request"]["messages"]:
            for c in m.get("tool_calls") or []:
                out.add(c.get("id"))
            if m.get("tool_call_id"):
                out.add(m["tool_call_id"])
        for c in ((r.get("reply") or {}).get("message") or {}).get("tool_calls") or []:
            out.add(c.get("id"))
        return out - {None}

    for r in recs:
        msgs = r["request"]["messages"]
        text = " ".join(m["content"] if isinstance(m.get("content"), str) else json.dumps(m.get("content"))
                        for m in msgs if m.get("role") == "user")
        task = None
        if "Problem Statement:\n" in text:
            ps = text.split("Problem Statement:\n", 1)[1]
            for key, iid in by_ps.items():
                if ps.strip().startswith(key[:200]):
                    task = iid
                    break
        if task is None:
            task = next((owner_of_id[i] for i in ids_in(r) if i in owner_of_id), None)
        if task is None and not r["request"].get("tools"):  # a summary that does not quote the task: the prompt
            summary = ((r.get("reply") or {}).get("message") or {}).get("content") or ""  # right after compaction
            later = (x for x in recs if x["t"] > r["t"] and x["request"].get("tools"))  # quotes this summary
            for x in later:
                raw = " ".join(p.get("text", "") if isinstance(p, dict) else str(p) for m in x["request"]["messages"]
                               for p in (m["content"] if isinstance(m.get("content"), list) else [m.get("content") or ""]))
                if summary and summary.strip()[:300] in raw:
                    task = next((owner_of_id[i] for i in ids_in(x) if i in owner_of_id), None)
                    break
        if task is None:
            unassigned += 1
            continue
        for i in ids_in(r):
            owner_of_id[i] = task
        assigned.append(dict(r, episode_id=task, attempt=a.attempt))

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    keep = {iid for iid, res in results.items() if res.get("resolved") or not a.only_resolved}
    with open(out / f"requests_{a.attempt}.jsonl", "w") as f:
        for r in assigned:
            if r["episode_id"] in keep:
                f.write(json.dumps(r) + "\n")
    with open(out / "status.jsonl", "w") as f:
        for iid in sorted(keep):
            res = results[iid]
            f.write(json.dumps({"id": iid, "instance_id": iid, "attempt": a.attempt, "status": "ok",
                                "split": a.split + ("_ok" if res.get("resolved") else "_fail"),
                                "category": None, "teacher": "gemma-31b-mix", "resolved": bool(res.get("resolved")),
                                "tool_calls": res.get("tool_calls")}) + "\n")
    per = {}
    for r in assigned:
        per.setdefault(r["episode_id"], [0, 0])
        per[r["episode_id"]][0 if r["request"].get("tools") else 1] += 1
    print(f"{len(recs)} records: {len(assigned)} assigned to {len(per)} tasks, {unassigned} unassigned")
    for iid in sorted(per):
        print(f"  {iid:16} {'RESOLVED' if results.get(iid, {}).get('resolved') else '-':8} agent calls {per[iid][0]:3} "
              f"summaries {per[iid][1]}  (harness tool_calls {results.get(iid, {}).get('tool_calls')})")


if __name__ == "__main__":
    main()
