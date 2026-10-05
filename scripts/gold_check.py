"""Positive control: grade each task's reference (gold) patch through the scorer's own verification path.

A dev task is only useful if its gold patch resolves locally; failures usually mean missing test dependencies in the
public wheels (forum 745775, 745249). Uses the same Evaluator sandbox and harness.verification.verify_task as scoring.

Usage:
    uv run scripts/gold_check.py fastapi_15588,fastapi_14786,rich_3882,rich_3469
"""

import asyncio
import sys
import time
from pathlib import Path

from swegemma.deduplication import resolve_task_snapshot_paths
from swegemma.evaluate import Evaluator
from swegemma.harness.verification import verify_task
from swegemma.models import load_tasks
from swegemma.models.registry import ModelRegistry

sys.path.insert(0, str(Path(__file__).parent))
from run_eval import DATA, ROOT, build_config  # noqa: E402


async def check(task_ids):
    results_dir = ROOT / "results" / f"gold_{time.strftime('%Y%m%d_%H%M%S')}"
    config = build_config(ROOT / "submissions" / "1a", task_ids, results_dir, ModelRegistry())
    evaluator = Evaluator(config)
    tasks = {t.instance_id: t for t in load_tasks(DATA / "tasks.jsonl")}
    for task_id in task_ids:
        task = tasks[task_id]
        snapshot, base_snapshot, patch = resolve_task_snapshot_paths(config.snapshots_dir, task_id, task.repo)
        start = time.perf_counter()
        res = await verify_task(evaluator.docker, config, task, snapshot, agent_patch=task.patch,
                                base_snapshot_path=base_snapshot, patch_path=patch, start_time=start)
        verdict = "PASS" if res.resolved else "FAIL"
        print(f"{task_id:<16} gold {verdict}  exit={res.test_exit_code}  {time.perf_counter() - start:.0f}s")
        if not res.resolved:
            print(f"  error: {res.error}")
            print("  " + "\n  ".join((res.test_output or "").strip().splitlines()[-15:]))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    asyncio.run(check(sys.argv[1].split(",")))
