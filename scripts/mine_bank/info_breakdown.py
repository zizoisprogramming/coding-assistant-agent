"""Success rate given each piece of information in the task text (user 2026-11-20: 'I need breakdown of percentage of success
given each one of the info'). Read-only: data/analysis/statement_content.json (per task: entry / example / behaviour / values,
solve rate, number of logged runs) + task_anatomy.json (fix size). Per info: tasks WITH it vs WITHOUT it; solve rate as the mean
over tasks (each task counts once) and pooled over runs; for all tasks with >= 4 runs and for the winnable core.
Run: python3 -I scripts/mine_bank/info_breakdown.py"""
import json, statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
S = json.load(open(ROOT / "data/analysis/statement_content.json"))
A = {r["iid"]: r for r in json.load(open(ROOT / "data/analysis/task_anatomy.json"))}
for r in S:
    r["solved_runs"] = round(r["rate"] * r["n"]) if r["rate"] is not None else 0
    r["small"] = A[r["iid"]]["src_files"] <= 1 and A[r["iid"]]["add"] + A[r["iid"]]["rem"] <= 20
INFO = [("entry", "names the function / class the test calls"), ("inp", "shows an example input / call"), ("behav", "says the wanted behaviour in words"),
        ("vals_some", "contains some value the test checks"), ("vals_all", "contains every value the test checks")]


def cell(xs):
    xs = [x for x in xs if x["n"] >= 4]
    if not xs:
        return "     -        (0 tasks)"
    runs = sum(x["n"] for x in xs)
    return f"{100 * st.mean(x['rate'] for x in xs):4.0f}% / {100 * sum(x['solved_runs'] for x in xs) / runs:3.0f}% ({len(xs):2} tasks, {runs:4} runs)"


for scope, X in (("ALL TASKS", S), ("WINNABLE CORE (1 source file, no hidden exact text)", [r for r in S if r["core"]])):
    print(f"\n#### {scope}   [solve rate: mean over tasks / pooled over runs]")
    print(f"  {'information in the text':44} {'WITH it':38} {'WITHOUT it':38}")
    for k, lab in INFO:
        print(f"  {lab:44} {cell([r for r in X if r[k]]):38} {cell([r for r in X if not r[k]]):38}")
    n_info = lambda r: r["entry"] + r["inp"] + r["behav"]
    print("  by how many of (entry, example, behaviour) the text gives:")
    for c in range(4):
        print(f"    {c} of 3{'':36} {cell([r for r in X if n_info(r) == c])}")
print("\n#### same, only SMALL fixes (1 source file, <= 20 changed lines, no hidden exact text) - removes the fix-size effect")
X = [r for r in S if r["core"] and r["small"]]
for k, lab in INFO[:4]:
    print(f"  {lab:44} {cell([r for r in X if r[k]]):38} {cell([r for r in X if not r[k]]):38}")
