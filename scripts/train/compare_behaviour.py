"""How do Gemma's own runs (resolved vs failed) differ from the teacher data we train on (v1 picks, v2 pool)?

    python3 scripts/train/compare_behaviour.py

Same features for both, per episode (medians over episodes; "per call" = per model call / teacher step):
calls, thinking chars per call, % calls without thinking, tool mix, lines per read_file, % commands that were
whole-file cat / long && chains, errors, max repeats of one identical call, call index of the first edit.
Gemma: data/results/2026-10-19_gemma_val/all (pilot #2, mix on the 31B; competition tasks: stays local).
Teachers: stage A episodes available locally; v1 = the 550 selected (only those present locally), v2 pool = the
"thinking first" rules (thinking every step, >=600 chars/step, no output over our limits, replay ok).
"""
import glob
import gzip
import json
import os
import re
import statistics as st
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "datasets"))
from episode_features import call_failed  # noqa: E402

CAT = re.compile(r"(^|&&|;)\s*cat\s+[\w./-]+\.py\s*($|&&|;|\|)")
CHAIN = re.compile(r"&&|;")
EDIT_CMD = re.compile(r"\bsed\s+(-[a-zA-Z]*i|--in-place)|cat\s*>\s*\S+\.py|open\([^)]*['\"]w['\"]")


def summarise(name, eps):
    """eps: list of dicts with calls=[(tool, args, thinking, failed)]"""
    rows = []
    for e in eps:
        calls = e["calls"]
        if not calls:
            continue
        tools = Counter(c[0] for c in calls)
        th = [len(c[2] or "") for c in calls]
        reads = [int(c[1].get("end_line") or 0) - int(c[1].get("start_line") or 0) + 1 for c in calls
                 if c[0] == "read_file" and c[1].get("start_line") and c[1].get("end_line")]
        cmds = [c[1].get("command", "") for c in calls if c[0] == "run_command"]
        sig = Counter((c[0], json.dumps(c[1], sort_keys=True)) for c in calls)
        first_edit = next((i + 1 for i, c in enumerate(calls) if c[0] in ("edit_file", "write_file")
                           or (c[0] == "run_command" and EDIT_CMD.search(c[1].get("command", "")))), None)
        rows.append({"calls": len(calls), "think": st.median(th), "no_think": sum(t == 0 for t in th) / len(th),
                     "read": tools["read_file"] / len(calls), "run": tools["run_command"] / len(calls),
                     "edit": (tools["edit_file"] + tools["write_file"]) / len(calls),
                     "read_lines": st.median(reads) if reads else None,
                     "cat": sum(bool(CAT.search(x)) for x in cmds) / max(len(cmds), 1),
                     "chains": sum(len(CHAIN.findall(x)) >= 3 for x in cmds) / max(len(cmds), 1),
                     "errors": sum(c[3] for c in calls), "max_rep": max(sig.values()), "first_edit": first_edit})

    def med(k):
        v = [r[k] for r in rows if r[k] is not None]
        return st.median(v) if v else None
    pct = lambda x: "-" if x is None else f"{100 * x:.0f}%"  # noqa: E731
    num = lambda x: "-" if x is None else f"{x:.0f}"  # noqa: E731
    print(f"{name:26} {len(rows):5} {num(med('calls')):>5} {num(med('think')):>6} {pct(med('no_think')):>7} "
          f"{pct(med('read')):>5} {pct(med('run')):>5} {pct(med('edit')):>5} {num(med('read_lines')):>6} "
          f"{pct(med('cat')):>5} {pct(med('chains')):>6} {num(med('errors')):>6} {num(med('max_rep')):>6} "
          f"{num(med('first_edit')):>6}  never-edit {pct(sum(r['first_edit'] is None for r in rows) / max(len(rows), 1))}")


def gemma_episodes(split_suffix):
    d = ROOT / "data" / "results" / "2026-10-19_gemma_val" / "all"
    status = {json.loads(l)["id"]: json.loads(l) for l in open(d / "status.jsonl")}
    by = {}
    for l in open(next(d.glob("requests_*.jsonl"))):
        r = json.loads(l)
        if status[r["episode_id"]]["split"].endswith(split_suffix) and r["request"].get("tools"):
            by.setdefault(r["episode_id"], []).append(r)
    eps = []
    for rs in by.values():
        rs.sort(key=lambda r: r["t"])
        results = {}  # tool_call_id -> tool output (from later prompts)
        for r in rs:
            for m in r["request"]["messages"]:
                if m.get("role") == "tool":
                    results[m.get("tool_call_id")] = str(m.get("content"))
        calls = []
        for r in rs:
            m = (r.get("reply") or {}).get("message") or {}
            th = m.get("reasoning_content") or m.get("reasoning") or ""
            for c in m.get("tool_calls") or []:
                try:
                    args = json.loads(c["function"]["arguments"] or "{}")
                except json.JSONDecodeError:
                    args = {}
                out = results.get(c.get("id"), "")
                calls.append((c["function"]["name"], args, th, '"status": "error"' in out[:40]))
                th = ""  # thinking belongs to the first call of a reply
        eps.append({"calls": calls})
    return eps


def teacher_episodes(ids):
    sel = json.loads((ROOT / "data" / "selection_v1.json").read_text())
    loc = {r["id"]: r for k in ("train_candidates", "val_candidates") for r in sel[k]}
    files = {os.path.basename(f): f for f in glob.glob(str(ROOT / "data/results/2026-10-18_stage_a_*/stage_a/episodes_*.jsonl"))}
    eps, cache = [], {}
    for i in ids:
        r = loc.get(i)
        if r is None or r["file"] not in files:
            continue
        if r["file"] not in cache:
            cache[r["file"]] = open(files[r["file"]]).readlines()
        eps.append(json.loads(cache[r["file"]][r["line"]]))
    return eps


def teacher_calls(eps):
    out = []
    for ep in eps:
        calls = []
        for s in ep["steps"]:
            th = s.get("thinking") or ""
            for c in s["calls"]:
                if c["tool"] == "submit_patch":
                    continue
                calls.append((c["tool"], c["args"], th, call_failed(c)[0]))
                th = ""
        out.append({"calls": calls})
    return out


def main():
    print(f"{'set':26} {'eps':>5} {'calls':>5} {'think':>6} {'no-thk':>7} {'read':>5} {'run':>5} {'edit':>5} "
          f"{'rd-ln':>6} {'cat':>5} {'chain':>6} {'errors':>6} {'maxrep':>6} {'1st-ed':>6}")
    summarise("Gemma 31B resolved", gemma_episodes("_ok"))
    summarise("Gemma 31B failed", gemma_episodes("_fail"))
    ok = [json.loads(l) for l in open(ROOT / "data/results/2026-10-18_stage_b/status.jsonl") if '"ok"' in l]
    summarise("teacher v1 train (trained)", teacher_calls(teacher_episodes([r["id"] for r in ok if r["split"] == "train"])))
    feats = ROOT / "data/results/2026-10-19_features_local.jsonl.gz"
    if feats.exists():
        f = [json.loads(l) for l in gzip.open(feats, "rt")]
        pool = [r["id"] for r in f if r["replay_ok"] and r["outputs_over_limit"] == 0 and r["steps_no_thinking"] == 0
                and r["thinking_chars_per_step"] >= 600 and r["print_only_sed"] == 0]
        files = {os.path.basename(p): p for p in glob.glob(str(ROOT / "data/results/2026-10-18_stage_a_*/stage_a/episodes_*.jsonl"))}
        want, eps = set(pool), []
        for p in files.values():
            for line in open(p):
                if '"id": "' in line[:60]:
                    ep = json.loads(line)
                    if ep["id"] in want:
                        eps.append(ep)
                        want.discard(ep["id"])
        summarise("teacher v2 pool (local)", teacher_calls(eps))
    print("\ncolumns: medians over episodes. think = thinking chars per call; no-thk = calls without thinking; read/run/"
          "edit = share of tool calls; rd-ln = lines per read_file; cat = commands cat-ing a whole .py; chain = commands "
          "with 3+ &&/; parts; maxrep = most repeats of one identical call; 1st-ed = call number of the first edit")


if __name__ == "__main__":
    main()
