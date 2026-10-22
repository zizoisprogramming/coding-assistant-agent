# 4. RUN: one line per finished attempt. results/gen_per_task.jsonl gets a row each; traces/patches under results/gen;
#    every model call in requests/requests.jsonl (tagged task#attempt). Everything is written as it goes (no zip).
import asyncio, concurrent.futures, traceback, yaml
from adk_submission import discover_adapters
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.apps._configs import EventsCompactionConfig
from swegemma.config import ALLOWED_ADAPTER_EXTENSIONS, EvalConfig, build_submission_limits
from swegemma.context import SwegemmaContext
from swegemma.evaluate import Evaluator
from swegemma.models import Task, TaskResult


def stratified_order(ids, seed):
    """Shuffle within repo, then interleave repos by weight: a session cut early still covers repos evenly."""
    rng = random.Random(seed)
    by_repo = {}
    for iid in ids:
        by_repo.setdefault(ROWS[iid]['repo'], []).append(iid)
    for v in by_repo.values():
        v.sort()
        rng.shuffle(v)
    queues = [list(v) for _, v in sorted(by_repo.items())]
    total = sum(len(q) for q in queues)
    weights, credit, ordered = [len(q) / total for q in queues], [0.0] * len(queues), []
    while any(queues):
        for i, q in enumerate(queues):
            credit[i] += weights[i] if q else 0.0
        i = max(range(len(queues)), key=lambda k: credit[k] if queues[k] else -1)
        credit[i] -= 1.0
        ordered.append(queues[i].pop(0))
    return ordered


ORDER = stratified_order(sorted(ROWS), seed=20261021)
if MODE == 'trial':
    n_trial = sum(n for _, n in TRIAL_PHASES)
    todo = [(i, 1) for i in ORDER if (i, 1) not in DONE_JOBS][:n_trial]
    PHASES, k = [], 0
    for conc, n in TRIAL_PHASES:
        PHASES.append((conc, todo[k:k + n]))
        k += n
elif MODE == 'full':
    PHASES = [(CONCURRENCY, [(i, 1) for k, i in enumerate(ORDER) if k % PART[1] == PART[0] - 1 and (i, 1) not in DONE_JOBS])]
    print(f'part {PART[0]} of {PART[1]}: {len(PHASES[0][1])} of {len(ORDER)} tasks', flush=True)
elif MODE == 'retry':
    PHASES = [(CONCURRENCY, [(i, 2) for i in ORDER if i not in SOLVED and (i, 2) not in DONE_JOBS])]
elif MODE == 'prompt':  # the prompt experiment: the new prompt on a fixed sample, compared with mix's attempt 1
    PHASES = [(CONCURRENCY, [(i, 1) for i in ORDER if i in SAMPLE and (i, 1) not in DONE_JOBS])]
else:
    raise SystemExit(f'unknown MODE {MODE!r}')
N_JOBS = sum(len(j) for _, j in PHASES)
print(f'mode {MODE}: {N_JOBS} attempts in phases {[(c, len(j)) for c, j in PHASES]}', flush=True)

LIMITS, GEN_CONSTRAINTS = build_submission_limits()
MANIFEST = discover_adapters(str(SUB_DIR), adapter_extensions=ALLOWED_ADAPTER_EXTENSIONS)


def read_eval_config(submission_dir):
    raw = yaml.safe_load((Path(submission_dir) / 'eval_config.yaml').read_text())
    section = (raw or {}).get('evaluation', raw or {})
    return {'timeout_seconds': int(section.get('timeout_seconds', 300)), 'max_tool_calls': section.get('max_tool_calls'),
            'max_time_minutes': float(section.get('max_time_minutes', 5.0)), 'max_turns': section.get('max_turns')}


EVAL_CFG = read_eval_config(SUB_DIR)


def evaluator_for(iid):
    (RESULTS / 'gen').mkdir(parents=True, exist_ok=True)
    return Evaluator(EvalConfig(
        tasks_path=DATA_DIR / 'tasks.jsonl',  # as the OOD-45 author's runs: the sandbox setup.py resolves from here
        snapshots_dir=(OOD_DIR if ROWS[iid].get('src') == 'ood' else OUT) / 'snapshots',
        wheels_dir=(OOD_WHEELS / ROWS[iid]['repo'].split('/', 1)[1] if ROWS[iid].get('src') == 'ood'
                    else WHEEL_ROOT / WHEEL_SET / iid),
        results_dir=RESULTS / 'gen', submission_dir=SUB_DIR, models=models, sandbox='subprocess',
        graph_dir=str(DATA_DIR / 'graphs'), embeddings_dir=str(DATA_DIR / 'embeddings'),
        limits=LIMITS, generation_constraints=GEN_CONSTRAINTS, adapter_manifest=MANIFEST,
        context_cache_config=ContextCacheConfig(min_tokens=2048, ttl_seconds=1800, cache_intervals=10),
        events_compaction_config=EventsCompactionConfig(
            compaction_interval=5, overlap_size=2, token_threshold=14336, event_retention_size=5),
        display_mode='quiet', **EVAL_CFG))


def as_task(r):
    if r.get('src') == 'ood':
        return OOD_TASKS[r['instance_id']]['g1']  # OOD-45's own Task
    return Task(instance_id=r['instance_id'], repo=r['repo'], base_commit=r['base_commit'],
                problem_statement=r['problem_statement'], patch=r['patch'], test_patch=r['test_patch'],
                hints_text='', created_at=r['created_at'], FAIL_TO_PASS=tuple(r['FAIL_TO_PASS']),
                PASS_TO_PASS=tuple(r['PASS_TO_PASS']))


evaluator_for(ORDER[0])  # fail before any task if the submission does not build into a config
print('budgets', EVAL_CFG, '| adapters', list(MANIFEST.adapters))

END_REASONS = (
    ('runner', ('notebook runner exception',)), ('env', ('not importable', 'sandboxenverror')),
    ('time', ('session timeout', 'time limit', 'max_time')), ('tool_budget', ('tool call budget',)),
    ('turns', ('turns budget', 'llm turns')), ('no_submit', ('without calling submit_patch',)),
    ('context', ('context length', 'maximum context', 'contextwindow')), ('sandbox', ('sandbox',)))


def end_reason(err):
    low = (err or '').lower()
    return 'ok' if not low else next((key for key, words in END_REASONS if any(w in low for w in words)), 'other')


TALLY, ENDS, DONE, PHASE_STATS = [0, 0], Counter(), [], []
STOP_AT = T_START + STOP_NEW_TASKS_AFTER_H * 3600


async def run_phase(conc, jobs, phase_no):
    sem, file_lock, repo_locks = asyncio.Semaphore(conc), asyncio.Lock(), collections.defaultdict(asyncio.Lock)
    p0, n0 = time.time(), len(DONE)

    async def one(iid, attempt):
        r = ROWS[iid]
        async with repo_locks[r['repo']]:  # the install step's import name is per repo: one task of a repo at a time
            async with sem:
                if time.time() > STOP_AT:
                    return
                if r.get('src') != 'ood':  # OOD-45's repos: the harness's own IMPORT_NAMES
                    ood.IMPORT_NAMES[r['repo']] = import_name(r)
                CUR_TASK.set(iid)
                RUNNING[iid] = time.time()
                task, evaluator, w0 = as_task(r), evaluator_for(iid), time.time()
                ctx = SwegemmaContext(
                    docker_manager=evaluator.docker, container_id='', problem_statement=task.problem_statement,
                    hints_text='', task=task, repo=task.repo, graph_dir=evaluator.config.graph_dir,
                    embeddings_dir=evaluator.config.embeddings_dir, budget=evaluator.config.budget,
                    harness=evaluator.config.harness)
                JOB.set(f'{iid}#a{attempt}')
                try:
                    res = await evaluator.evaluate_task(task, task_index=len(DONE) + 1, total_tasks=N_JOBS, context=ctx)
                except Exception as exc:
                    res = TaskResult(instance_id=iid, repo=task.repo, resolved=False, agent_patch='', test_output='',
                                     test_exit_code=-1, duration_seconds=time.time() - w0, task_index=0,
                                     error=f'notebook runner exception: {exc!r}\n{traceback.format_exc()[-2000:]}')
                ENV_BY_TASK.pop(iid, None)
                RUNNING.pop(iid, None)
                clean_tmp()  # unpacked-wheel tars and sandbox dirs no running task uses (disk)
                row = {'instance_id': iid, 'attempt': attempt, 'mode': MODE, 'phase': phase_no, 'concurrency': conc,
                       'repo': r['repo'], 'level': r['level'], 'domain': r['domain'], 'text_kind': r['text_kind'],
                       'leak': r['leak'], 'unfair': bool(r['unfair_names']), 'env_partial': r['env_partial'],
                       'resolved': bool(res.resolved), 'wall_s': round(time.time() - w0, 1),
                       'agent_s': round(getattr(ctx, 'agent_elapsed_seconds', 0) or 0, 1),
                       'tool_calls': getattr(ctx, 'tool_calls_used', None), 'llm_calls': getattr(ctx, 'llm_calls_used', None),
                       'patch_chars': len(res.agent_patch or ''), 'submitted': bool(getattr(ctx, 'patch_submitted', False)),
                       'end': end_reason(res.error), 'error': (res.error or '')[:3000], 't_end': time.time()}
        async with file_lock:
            with open(PER_TASK, 'a', encoding='utf-8') as fh:
                fh.write(json.dumps(row) + '\n')
            pdir = RESULTS / 'gen' / 'patches'
            pdir.mkdir(parents=True, exist_ok=True)
            (pdir / f'{iid}__a{attempt}.diff').write_text(res.agent_patch or '', encoding='utf-8')
            TALLY[0] += row['resolved']
            TALLY[1] += 1
            ENDS[row['end']] += 1
            DONE.append(row)
            el = time.time() - T_START
            eta = el / len(DONE) * (N_JOBS - len(DONE))
            print(f"[{len(DONE):3}/{N_JOBS}] {iid[:40]:40} a{attempt} {r['level']:7} resolved={row['resolved']!s:5} "
                  f"agent={row['agent_s']:4.0f}s wall={row['wall_s']:4.0f}s tools={row['tool_calls']} llm={row['llm_calls']} "
                  f"patch={row['patch_chars']:5} end={row['end']:10} | solved {TALLY[0]}/{TALLY[1]} | "
                  f"{el / 60:.0f} min, ETA {eta / 60:.0f} min"
                  + (f"\n      err: {row['error'][:200]!r}" if row['end'] not in ('ok', 'time', 'tool_budget') else ''),
                  flush=True)

    await asyncio.gather(*(one(i, a) for i, a in jobs))
    rows = DONE[n0:]
    hours = (time.time() - p0) / 3600
    PHASE_STATS.append({'phase': phase_no, 'concurrency': conc, 'attempts': len(rows), 'hours': round(hours, 2),
                        'attempts_per_hour': round(len(rows) / max(hours, 1e-6), 1),
                        'mean_agent_s': round(sum(r['agent_s'] for r in rows) / max(len(rows), 1)),
                        'resolved': sum(r['resolved'] for r in rows)})
    print('PHASE', json.dumps(PHASE_STATS[-1]), flush=True)


async def run_all():
    for k, (conc, jobs) in enumerate(PHASES, 1):
        await run_phase(conc, jobs, k)


def run_sync(coro_fn):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop is not None and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(lambda: asyncio.run(coro_fn())).result()
    return asyncio.run(coro_fn())


try:
    run_sync(run_all)
finally:
    (RESULTS / 'phases.json').write_text(json.dumps(PHASE_STATS, indent=1))
    # no results.zip (2026-10-22): Kaggle unzips zips when an output becomes a dataset, and results.zip -> results/
    # collided with the results/ folder ("results already exists").
print(f'==> {MODE}: solved {TALLY[0]}/{TALLY[1]} | ends {dict(ENDS)} | {(time.time() - T_START) / 60:.1f} min; '
      f'not started (time guard): {N_JOBS - len(DONE)}')
