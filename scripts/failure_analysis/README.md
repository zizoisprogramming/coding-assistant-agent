# Failure-pattern analysis helpers (2026-10-25)

Read-only helpers used for the analysis recorded in docs/PLAN.md ("FAILURE-PATTERN ANALYSIS"). They read gitignored
data only (competition tasks + our results); nothing here contains task data.

- `fail_load.py` - `load()`: every exported failed generation run (data/results/2026-10-25_failed/*.jsonl.gz, from
  kaggle/cells_export_failed) with gold/our files, calls, thoughts, compaction summaries; public grades re-applied.
- `devtime.py SPLIT` - per-run calls / time / tokens from local ATIF traces of dev16 or val (mix-family vs all).
- `devgroups.py TASK [N]`, `devshort.py TASK...`, `devcase.py TASK` - one public task: issue, gold, hidden test, and
  every local run's patch grouped / compact / per mix run.

Run from the repo root with python3 (devtime writes /tmp/devtime_<split>.json).
