"""Grade saved patch files through the scorer's own verification path (as scripts/gold_check.py does for gold).

Each file is named FOLDER__TASK_ARM.diff (the task id is taken from the name). Used to replay edits that a run made
but never landed (for example edits refused by the call budget). Usage:
    uv run scripts/grade_patches.py DIR
"""
import asyncio
import re
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


async def grade(folder):
    files = sorted(p for p in Path(folder).glob("*.diff") if p.stat().st_size > 0)
    tasks = {t.instance_id: t for t in load_tasks(DATA / "tasks.jsonl")}
    ids = sorted({re.search(r"__((?:[a-z]+)_\d+)_a", p.name).group(1) for p in files})
    results_dir = ROOT / "results" / f"grade_{time.strftime('%Y%m%d_%H%M%S')}"
    config = build_config(ROOT / "submissions" / "1a", ids, results_dir, ModelRegistry())
    evaluator = Evaluator(config)
    for p in files:
        tid = re.search(r"__((?:[a-z]+)_\d+)_a", p.name).group(1)
        task = tasks[tid]
        snapshot, base_snapshot, patch = resolve_task_snapshot_paths(config.snapshots_dir, tid, task.repo)
        start = time.perf_counter()
        res = await verify_task(evaluator.docker, config, task, snapshot, agent_patch=p.read_text(),
                                base_snapshot_path=base_snapshot, patch_path=patch, start_time=start)
        print(f"{'PASS' if res.resolved else 'FAIL'}  {p.name}  {time.perf_counter() - start:.0f}s", flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    asyncio.run(grade(sys.argv[1]))
