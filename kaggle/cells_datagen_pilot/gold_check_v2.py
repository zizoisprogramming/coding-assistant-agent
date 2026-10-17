# GOLD CHECK v2 (CPU session, INTERNET ON; run after cell1_cpu.py and cell2.py). Grades every non-dev task's
# reference patch and an empty patch with the scorer's own verify_task, and repairs the test environment as it goes:
# the sandbox's Python sees this notebook's installed packages, and the public test wheels miss some test
# dependencies (forum 745775), so "No module named X" makes a correct fix look failed. Each round collects every
# missing module, pip-installs it with --no-deps (nothing already installed is upgraded), and re-grades the failures.
# Writes /kaggle/working/gold_check.json (per task) and /kaggle/working/test_deps.txt (what was installed; the GPU
# data-gen notebook installs the same list so its "solved" labels are trustworthy). Resumes after a restart.
import logging, warnings
warnings.filterwarnings('ignore')
logging.getLogger('swegemma.sandbox.subprocess').setLevel(logging.ERROR)
import asyncio, concurrent.futures, gc, glob, json, re, shutil, subprocess, sys, time
from pathlib import Path
from swegemma.deduplication import resolve_task_snapshot_paths
from swegemma.evaluate import Evaluator
from swegemma.harness.verification import verify_task
from swegemma.models import load_tasks
from adk_submission import ModelRegistry


# ---- helpers shared with gold_check_113.py (task list, build_config) ----
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


# ---- v2 ----
OUT = WORKING_DIR / 'gold_check.json'
DEPS = WORKING_DIR / 'test_deps.txt'
ROUNDS = 4
# module name -> pip name where they differ; repo packages and repo-local folders are never installed
PIP_NAME = {'yaml': 'PyYAML', 'multipart': 'python-multipart', 'jose': 'python-jose', 'jwt': 'PyJWT',
            'attr': 'attrs', 'PIL': 'Pillow', 'dateutil': 'python-dateutil', 'email_validator': 'email-validator',
            'pytest_httpbin': 'pytest-httpbin', 'socks': 'PySocks', 'brotli': 'Brotli', 'zstandard': 'zstandard',
            'h2': 'h2', 'sse_starlette': 'sse-starlette', 'inline_snapshot': 'inline-snapshot',
            'dirty_equals': 'dirty-equals', 'pydantic_settings': 'pydantic-settings', 'sqlmodel': 'sqlmodel'}
# found missing when grading locally (data/wheels_extra): installed up front to save a round
PREINSTALL = ['dirty_equals', 'inline_snapshot', 'asttokens', 'executing', 'typing_inspection']
NEVER = {'tests', 'docs', 'docs_src', 'conftest', 'scripts', 'fastapi', 'requests', 'rich', 'httpx'}

done = json.loads(OUT.read_text()) if OUT.exists() else {}
installed = DEPS.read_text().split() if DEPS.exists() else []
print(f'resuming: {sum(r.get("usable", False) for r in done.values())} usable of {len(done)} graded; '
      f'installed so far: {installed}')


def ram():
    try:
        import psutil
        return f'{psutil.virtual_memory().used / 2**30:.1f} GiB RAM used'
    except Exception:
        return ''


def diagnose(text):
    missing = sorted(set(re.findall(r"No module named '([A-Za-z0-9_]+)", text or '')))
    errs = []
    for line in (text or '').splitlines():
        line = line.strip()
        if (line.startswith('E ') or 'Error' in line[:60]) and line not in errs:
            errs.append(line[:200])
        if len(errs) >= 4:
            break
    return missing, errs


async def grade(task_ids, config, tasks, evaluator):
    for tid in task_ids:
        task, row = tasks[tid], {}
        for label, patch_text in (('gold', task.patch), ('empty', '')):
            snap, base_snap, patch_path = resolve_task_snapshot_paths(config.snapshots_dir, tid, task.repo)
            t0 = time.perf_counter()
            try:
                res = await verify_task(evaluator.docker, config, task, snap, agent_patch=patch_text,
                                        base_snapshot_path=base_snap, patch_path=patch_path, start_time=t0)
                row[label] = 'PASS' if res.resolved else 'FAIL'
                if label == 'gold' and not res.resolved:
                    row['missing_modules'], row['first_errors'] = diagnose(res.test_output)
                    row['gold_tail'] = (res.error or '') + ' | ' + ' / '.join(
                        (res.test_output or '').strip().splitlines()[-4:])
            except Exception as e:
                row[label] = f'ERROR {type(e).__name__}: {str(e)[:150]}'
            row[label + '_s'] = round(time.perf_counter() - t0)
            if label == 'gold' and row['gold'] != 'PASS':
                row['empty'], row['empty_s'] = 'skipped', 0  # gold already failed: the task is unusable now
                break
        row['usable'] = row.get('gold') == 'PASS' and row.get('empty') == 'FAIL'
        done[tid] = row
        OUT.write_text(json.dumps(done, indent=1))
        print(f"{tid:16} gold {row['gold']:5} empty {row['empty']:7} usable={row['usable']}"
              f"{'  missing ' + str(row['missing_modules']) if row.get('missing_modules') else ''}")
        for p in glob.glob('/tmp/swegemma_sandbox_*'):  # never let finished sandboxes pile up
            shutil.rmtree(p, ignore_errors=True)
        gc.collect()


def pip_install(modules):
    new = []
    for m in modules:
        if m in NEVER or m in installed:
            continue
        name = PIP_NAME.get(m, m.replace('_', '-'))
        r = subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '--no-deps', name],
                           capture_output=True, text=True)
        print(f'   pip install --no-deps {name}:', 'ok' if r.returncode == 0 else 'FAILED ' + r.stderr.strip()[-200:])
        if r.returncode == 0:
            installed.append(name)
            new.append(name)
    DEPS.write_text('\n'.join(installed) + '\n')
    return new


async def main():
    config = build_config(SUB_ROOT / CONFIGS[0], GOLD_TASKS, WORKING_DIR / 'gold_results', ModelRegistry(),
                          data_dir=DATA_DIR, sandbox='subprocess', display_mode='quiet')
    evaluator = Evaluator(config)
    tasks = {t.instance_id: t for t in load_tasks(DATA_DIR / 'tasks.jsonl')}
    pip_install(PREINSTALL)
    todo = [t for t in GOLD_TASKS if t not in done]
    for rnd in range(1, ROUNDS + 1):
        print(f'\n=== round {rnd}: grading {len(todo)} tasks ({ram()})')
        await grade(todo, config, tasks, evaluator)
        missing = sorted({m for r in done.values() if not r['usable'] for m in r.get('missing_modules', [])})
        print(f'round {rnd}: usable {sum(r["usable"] for r in done.values())}/{len(done)}; missing modules: {missing}')
        new = pip_install(missing)
        if not new:
            break
        todo = [t for t, r in done.items() if not r['usable'] and set(r.get('missing_modules', [])) - NEVER]
    by_repo = {}
    for t, r in done.items():
        by_repo.setdefault(t.split('_')[0], [0, 0])
        by_repo[t.split('_')[0]][0] += r['usable']
        by_repo[t.split('_')[0]][1] += 1
    print('\n==> usable per repo:', {k: f'{a}/{b}' for k, (a, b) in by_repo.items()})
    print('==> installed test deps:', installed)
    left = {}
    for t, r in done.items():
        if not r['usable']:
            key = (r.get('first_errors') or [r.get('gold_tail', '')[-120:]])[0][:110]
            left.setdefault(key, []).append(t)
    print('==> still unusable, grouped by first error:')
    for k, ts in sorted(left.items(), key=lambda kv: -len(kv[1])):
        print(f'  {len(ts):3}  {k}   e.g. {ts[:3]}')


with concurrent.futures.ThreadPoolExecutor(max_workers=1) as _pool:
    _pool.submit(lambda: asyncio.run(main())).result()
