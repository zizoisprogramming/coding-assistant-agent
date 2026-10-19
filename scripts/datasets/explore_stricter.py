"""Exploration (not a selection): how would stricter "Gemma style" rules change the pool and its style?
Pool sizes from the full-corpus features; style measured on the episodes available locally, after the read rewrite.

    data/venv_harness/bin/python scripts/datasets/explore_stricter.py
"""
import glob
import gzip
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts" / "datasets"), str(ROOT / "scripts" / "train")]
from compare_behaviour import summarise, teacher_calls  # noqa: E402
from stage_b import rewrite_reads  # noqa: E402

S = {json.loads(l)["id"]: json.loads(l) for l in gzip.open(ROOT / "data/results/2026-10-18_stats/stats.jsonl.gz", "rt")}
F = {json.loads(l)["id"]: json.loads(l) for l in gzip.open(ROOT / "data/results/2026-10-19_features/features.jsonl.gz", "rt")}
FL = {json.loads(l)["id"] for l in gzip.open(ROOT / "data/results/2026-10-18_flags/flags.jsonl.gz", "rt")}


def base(i):  # the v2 rules
    r, f = S[i], F[i]
    return (i not in FL and f["replay_ok"] and r["steps_over_2048"] == 0 and r["repeated_commands"] == 0
            and r["env_confusion"] <= 2 and r["error_rate"] <= 0.35 and f["steps_no_thinking"] <= 0.2 * f["steps"]
            and f["thinking_chars_per_step"] >= 600 and f["outputs_over_limit"] <= 1 and f["print_only_sed"] == 0
            and f["repeated_after_error"] == 0)


def per_call(f, k):
    return f[k] / max(f["calls"], 1)


VARIANTS = {
    "v2 rules (current)": lambda f: True,
    "+ chains <=5% of calls": lambda f: per_call(f, "long_chains") <= 0.05,
    "+ no whole-file cat": lambda f: per_call(f, "long_chains") <= 0.05 and f["cat_whole_file"] == 0,
    "+ edits only via edit_file": lambda f: (per_call(f, "long_chains") <= 0.05 and f["cat_whole_file"] == 0 and
                                             f["edit_tool"] >= 1 and f["sed_inplace"] == 0 and f["shell_file_write"] == 0),
    "chains<=5% + edit_file only (cat ok)": lambda f: (per_call(f, "long_chains") <= 0.05 and f["edit_tool"] >= 1
                                                       and f["sed_inplace"] == 0 and f["shell_file_write"] == 0),
}
local = {}
for p in glob.glob(str(ROOT / "data/results/2026-10-18_stage_a_*/stage_a/episodes_*.jsonl")):
    for line in open(p):
        ep = json.loads(line)
        local[ep["id"]] = ep
print(f"{'set':26} {'eps':>5} {'calls':>5} {'think':>6} {'no-thk':>7} {'read':>5} {'run':>5} {'edit':>5} "
      f"{'rd-ln':>6} {'cat':>5} {'chain':>6} {'errors':>6} {'maxrep':>6} {'1st-ed':>6}")
for name, rule in VARIANTS.items():
    ids = [i for i in S if base(i) and rule(F[i])]
    tasks = len({S[i]["instance_id"] for i in ids})
    teach = {}
    for i in ids:
        teach[S[i]["teacher"]] = teach.get(S[i]["teacher"], 0) + 1
    print(f"\n### {name}: pool {len(ids)} episodes / {tasks} tasks (need ~650+ tasks for 500+50 with val repos held "
          f"out) | {teach}")
    summarise("  style (local, rewritten)", teacher_calls([rewrite_reads(local[i]) for i in ids if i in local]))
