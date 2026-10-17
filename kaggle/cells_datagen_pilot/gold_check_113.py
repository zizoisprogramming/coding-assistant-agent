# GOLD CHECK (run after cells 1 and 2; no vLLM, no GPU needed): grades each task's reference patch and an empty
# patch through the scorer's own verify_task in the Kaggle subprocess sandbox. A task is usable only if
# gold = PASS and empty = FAIL. Writes /kaggle/working/gold_check.json.
import logging, warnings
# Hide only the red noise: the sandbox's per-task 'ensurepip unavailable' warnings and Python deprecation
# warnings. Everything else prints as before; errors still print.
warnings.filterwarnings('ignore')
logging.getLogger('swegemma.sandbox.subprocess').setLevel(logging.ERROR)
import asyncio, concurrent.futures, json, time, yaml
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.apps._configs import EventsCompactionConfig
from swegemma.config import EvalConfig, build_submission_limits
from swegemma.deduplication import resolve_task_snapshot_paths
from swegemma.evaluate import Evaluator
from swegemma.harness.verification import verify_task
from swegemma.models import load_tasks
from adk_submission import ModelRegistry  # moved out of swegemma in 0.2.11

DATA = DATA_DIR
GOLD_TASKS = ['fastapi_15661', 'fastapi_15588', 'fastapi_15030', 'fastapi_14962', 'fastapi_14964', 'fastapi_15023', 'fastapi_14986', 'fastapi_14978', 'requests_7505', 'requests_7502', 'requests_7433', 'requests_7427', 'requests_7315', 'requests_7328', 'requests_7309', 'requests_7205', 'rich_4070', 'rich_4077', 'rich_4076', 'rich_4075', 'rich_4006', 'fastapi_14851', 'fastapi_14873', 'fastapi_14794', 'fastapi_14786', 'fastapi_14492', 'fastapi_14479', 'fastapi_14463', 'fastapi_12942', 'fastapi_14099', 'fastapi_14609', 'fastapi_14372', 'fastapi_14349', 'fastapi_14512', 'fastapi_11355', 'fastapi_14485', 'fastapi_14482', 'fastapi_14458', 'fastapi_14459', 'fastapi_14448', 'fastapi_14455', 'fastapi_9753', 'fastapi_14430', 'fastapi_5077', 'fastapi_9555', 'fastapi_14361', 'fastapi_13207', 'fastapi_14360', 'fastapi_14356', 'fastapi_5624', 'fastapi_14301', 'fastapi_14262', 'fastapi_14266', 'fastapi_14246', 'fastapi_14186', 'fastapi_9425', 'fastapi_13713', 'fastapi_14077', 'rich_3718', 'rich_3953', 'rich_3944', 'rich_3942', 'rich_3938', 'rich_3894', 'rich_3935', 'rich_3905', 'rich_3930', 'httpx_3672', 'fastapi_14791', 'fastapi_15785', 'fastapi_14371', 'fastapi_14605', 'fastapi_15763', 'fastapi_14583', 'fastapi_15745', 'fastapi_14297', 'fastapi_14303', 'fastapi_13537', 'fastapi_14953', 'fastapi_13786', 'fastapi_14616', 'requests_6757', 'requests_6629', 'requests_6644', 'requests_6589', 'requests_6592', 'rich_3486', 'rich_3777', 'rich_3782', 'rich_3772', 'rich_3296', 'rich_3675', 'rich_3676', 'rich_3518', 'rich_3535', 'rich_3506', 'rich_3480', 'rich_3472', 'rich_3454', 'rich_3471', 'rich_3469', 'rich_3052', 'rich_3278', 'rich_2943', 'rich_2725', 'rich_3105', 'rich_3130', 'rich_3043', 'rich_3067', 'rich_3006', 'rich_3064', 'rich_3063', 'rich_3061']


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
                 adapter_manifest=None, display_mode="single", concurrency=1):
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
        concurrency=concurrency,
        **budgets,
    )


async def _gold(task_ids):
    config = build_config(SUB_ROOT / CONFIGS[0], task_ids, WORKING_DIR / 'gold_results', ModelRegistry(),
                          data_dir=DATA_DIR, sandbox='subprocess', display_mode='quiet')
    evaluator = Evaluator(config)
    tasks = {t.instance_id: t for t in load_tasks(DATA_DIR / 'tasks.jsonl')}
    out = {}
    for tid in task_ids:
        task = tasks[tid]
        row = {}
        for label, patch_text in (('gold', task.patch), ('empty', '')):
            snap, base_snap, patch_path = resolve_task_snapshot_paths(config.snapshots_dir, tid, task.repo)
            t0 = time.perf_counter()
            try:
                res = await verify_task(evaluator.docker, config, task, snap, agent_patch=patch_text,
                                        base_snapshot_path=base_snap, patch_path=patch_path, start_time=t0)
                row[label] = 'PASS' if res.resolved else 'FAIL'
                if label == 'gold' and not res.resolved:
                    row['gold_tail'] = (res.error or '') + ' | ' + ' / '.join((res.test_output or '').strip().splitlines()[-6:])
            except Exception as e:  # keep going: one broken task must not stop the check
                row[label] = f'ERROR {type(e).__name__}: {str(e)[:150]}'
            row[label + '_s'] = round(time.perf_counter() - t0)
        row['usable'] = row.get('gold') == 'PASS' and row.get('empty') == 'FAIL'
        out[tid] = row
        print(f"{tid:16} gold {row['gold']:5} empty {row['empty']:5} usable={row['usable']}  ({row['gold_s']}s + {row['empty_s']}s)")
        if row.get('gold_tail'):
            print('   ', row['gold_tail'][:400])
        (WORKING_DIR / 'gold_check.json').write_text(json.dumps(out, indent=1))
    print('USABLE:', [t for t, r in out.items() if r['usable']])


with concurrent.futures.ThreadPoolExecutor(max_workers=1) as _pool:
    _pool.submit(lambda: asyncio.run(_gold(GOLD_TASKS))).result()