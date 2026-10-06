# 4. Evaluate every config on the same tasks (Evaluator configured like the scorer; see scripts/run_eval.py)
import asyncio, concurrent.futures, time, yaml
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.apps._configs import EventsCompactionConfig
from swegemma.config import EvalConfig, build_submission_limits
from swegemma.evaluate import Evaluator

DATA = DATA_DIR  # default used by build_config (copied from scripts/run_eval.py)


def read_eval_config(submission_dir):
    """The four eval_config.yaml keys the scorer reads (defaults as in the host notebook)."""
    path = Path(submission_dir) / "eval_config.yaml"
    raw = yaml.safe_load(path.read_text()) if path.exists() else {}
    section = (raw or {}).get("evaluation", raw or {})
    return {
        "timeout_seconds": int(section.get("timeout_seconds", 300)),
        "max_tool_calls": section.get("max_tool_calls"),
        "max_time_minutes": float(section.get("max_time_minutes", 5.0)),
        "max_turns": section.get("max_turns"),
    }


def wheels_dir_for(data_dir):
    """Official test wheels, plus data/wheels_extra if present (local only: test deps missing from the public set,
    forum 745775). Merged as links into data/wheels_merged so the official folder stays untouched."""
    official, extra = Path(data_dir) / "wheels", Path(data_dir) / "wheels_extra"
    if not extra.is_dir():
        return official
    merged = Path(data_dir) / "wheels_merged"
    merged.mkdir(exist_ok=True)
    for wheel in [*official.glob("*.whl"), *extra.glob("*.whl")]:
        link = merged / wheel.name
        if not link.exists():
            link.hardlink_to(wheel)
    return merged


def build_config(submission_dir, task_ids, results_dir, models, data_dir=DATA, sandbox="docker",
                 adapter_manifest=None, display_mode="single"):
    limits, gen_constraints = build_submission_limits()
    budgets = read_eval_config(submission_dir)
    return EvalConfig(
        tasks_path=Path(data_dir) / "tasks.jsonl",
        snapshots_dir=Path(data_dir) / "snapshots",
        results_dir=Path(results_dir),
        submission_dir=Path(submission_dir),
        models=models,
        sandbox=sandbox,
        wheels_dir=wheels_dir_for(data_dir),
        graph_dir=str(Path(data_dir) / "graphs"),
        embeddings_dir=str(Path(data_dir) / "embeddings"),
        task_ids=list(task_ids),
        limits=limits,
        generation_constraints=gen_constraints,
        adapter_manifest=adapter_manifest,
        context_cache_config=ContextCacheConfig(min_tokens=2048, ttl_seconds=1800, cache_intervals=10),
        events_compaction_config=EventsCompactionConfig(
            compaction_interval=5, overlap_size=2, token_threshold=14336, event_retention_size=5,
        ),
        display_mode=display_mode,
        **budgets,
    )


def run_sync(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop is not None and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(lambda: asyncio.run(coro)).result()
    return asyncio.run(coro)


RESULTS = WORKING_DIR / 'results'
shutil.rmtree(RESULTS, ignore_errors=True)
wall = {}
for name in CONFIGS:
    start = time.time()
    config = build_config(SUB_ROOT / name, TASK_IDS, RESULTS / name, models, data_dir=DATA_DIR,
                          sandbox='subprocess', display_mode='single')
    result = run_sync(Evaluator(config).run())
    wall[name] = time.time() - start
    print(f'==> {name}: {result.resolved}/{result.total} resolved in {wall[name] / 60:.1f} min')