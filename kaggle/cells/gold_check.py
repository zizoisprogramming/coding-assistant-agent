# GOLD CHECK (run after cells 1 and 2; no vLLM, no GPU needed): grades each task's reference patch and an empty
# patch through the scorer's own verify_task in the Kaggle subprocess sandbox. A task is usable only if
# gold = PASS and empty = FAIL. Writes /kaggle/working/gold_check.json.
import asyncio, concurrent.futures, json, time, yaml
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.apps._configs import EventsCompactionConfig
from swegemma.config import EvalConfig, build_submission_limits
from swegemma.deduplication import resolve_task_snapshot_paths
from swegemma.evaluate import Evaluator
from swegemma.harness.verification import verify_task
from swegemma.models import load_tasks
from swegemma.models.registry import ModelRegistry

DATA = DATA_DIR
GOLD_TASKS = ['fastapi_15589', 'fastapi_13920', 'fastapi_14258', 'fastapi_11194', 'fastapi_15588', 'fastapi_15280', 'fastapi_14583', 'fastapi_15800', 'fastapi_14306', 'fastapi_14978', 'rich_3882', 'rich_3470', 'rich_3296', 'rich_3521', 'rich_3934', 'rich_3180', 'fastapi_14266', 'fastapi_14487', 'fastapi_14419', 'fastapi_15023', 'fastapi_14372', 'rich_4079', 'rich_3506', 'rich_3468', 'rich_3782']


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