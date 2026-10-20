# 4. Run every variant on the 44 tasks. One shared queue: tasks in a repo-stratified order (seed 1), the variants of a
#    task back to back, so a session cut early still leaves whole task sets comparable across variants.
#    One line per finished task; results/<variant>/ gets traces + task_results.jsonl, results/ood_per_task.jsonl a row each.
import asyncio, concurrent.futures, traceback, yaml
from collections import Counter, defaultdict
from adk_submission import discover_adapters
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.apps._configs import EventsCompactionConfig
from swegemma.config import ALLOWED_ADAPTER_EXTENSIONS, EvalConfig, build_submission_limits
from swegemma.context import SwegemmaContext
from swegemma.evaluate import Evaluator
from swegemma.models import TaskResult

T_START = time.time()
STOP_AT = T_START + STOP_NEW_TASKS_AFTER_H * 3600
PER_TASK = RESULTS / 'ood_per_task.jsonl'


def read_eval_config(submission_dir):
    """The four eval_config.yaml keys the scorer reads (defaults as in the host notebook)."""
    path = Path(submission_dir) / 'eval_config.yaml'
    raw = yaml.safe_load(path.read_text()) if path.exists() else {}
    section = (raw or {}).get('evaluation', raw or {})
    return {'timeout_seconds': int(section.get('timeout_seconds', 300)),
            'max_tool_calls': section.get('max_tool_calls'),
            'max_time_minutes': float(section.get('max_time_minutes', 5.0)),
            'max_turns': section.get('max_turns')}


def stratified_order(ids, repo_of, seed):
    """Shuffle within repo, then interleave repos by weight (the author's plan_jobs), so a cut run stays stratified."""
    rng = random.Random(seed)
    by_repo = {}
    for iid in ids:
        by_repo.setdefault(repo_of[iid], []).append(iid)
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


names = list(VARIANTS)
JOBS = [(names[(pos + k) % len(names)], iid)  # which variant goes first rotates from task to task
        for pos, iid in enumerate(stratified_order(RUN_IDS, REPO_OF, seed=1)) for k in range(len(names))]
(RESULTS / 'jobs.json').write_text(json.dumps(JOBS))
LIMITS, GEN_CONSTRAINTS = build_submission_limits()
MANIFESTS = {v: discover_adapters(str(SUB_ROOT / v), adapter_extensions=ALLOWED_ADAPTER_EXTENSIONS) for v in names}
EVALUATORS = {}


def evaluator_for(variant, repo):
    if (variant, repo) not in EVALUATORS:
        (RESULTS / variant).mkdir(parents=True, exist_ok=True)
        EVALUATORS[variant, repo] = Evaluator(EvalConfig(
            tasks_path=DATA_DIR / 'tasks.jsonl',  # as the author's runs: sandbox setup.py and graphs resolve from here
            snapshots_dir=OOD_RUN.snapshots, wheels_dir=OOD_RUN.wheels_for(repo),
            results_dir=RESULTS / variant, submission_dir=SUB_ROOT / variant, models=models, sandbox='subprocess',
            graph_dir=str(DATA_DIR / 'graphs'), embeddings_dir=str(DATA_DIR / 'embeddings'),
            limits=LIMITS, generation_constraints=GEN_CONSTRAINTS, adapter_manifest=MANIFESTS[variant],
            context_cache_config=ContextCacheConfig(min_tokens=2048, ttl_seconds=1800, cache_intervals=10),
            events_compaction_config=EventsCompactionConfig(
                compaction_interval=5, overlap_size=2, token_threshold=14336, event_retention_size=5),
            display_mode='quiet', **read_eval_config(SUB_ROOT / variant)))
    return EVALUATORS[variant, repo]


for v in names:  # fail before any task if a submission does not build into a config
    evaluator_for(v, REPO_OF[RUN_IDS[0]])
    print(v, '| budgets', read_eval_config(SUB_ROOT / v), '| adapters', list(MANIFESTS[v].adapters))

TALLY = defaultdict(lambda: [0, 0])  # variant -> [resolved, finished]
ENDS = defaultdict(Counter)
DONE = []


END_REASONS = (  # first match wins (the author's classify_task_error, plus our runner / sandbox env cases)
    ('runner', ('notebook runner exception',)), ('env', ('not importable', 'sandboxenverror')),
    ('time', ('session timeout', 'time limit', 'max_time')), ('tool_budget', ('tool call budget',)),
    ('turns', ('turns budget', 'llm turns')), ('no_submit', ('without calling submit_patch',)),
    ('context', ('context length', 'maximum context', 'contextwindow')), ('sandbox', ('sandbox',)))


def end_reason(err):
    low = (err or '').lower()
    if not low:
        return 'ok'
    return next((key for key, words in END_REASONS if any(w in low for w in words)), 'other')


async def run_all():
    sem = asyncio.Semaphore(CONCURRENCY)
    lock = asyncio.Lock()

    async def one(order, variant, iid):
        task = OOD_RUN.tasks[iid]['g1']  # g1 = the released (rewritten) statement
        async with sem:
            if time.time() > STOP_AT:
                return
            evaluator = evaluator_for(variant, task.repo)
            ctx = SwegemmaContext(
                docker_manager=evaluator.docker, container_id='', problem_statement=task.problem_statement,
                hints_text='', task=task, repo=task.repo, graph_dir=evaluator.config.graph_dir,
                embeddings_dir=evaluator.config.embeddings_dir, budget=evaluator.config.budget,
                harness=evaluator.config.harness)
            JOB.set(f'{variant}/{iid}')
            w0 = time.time()
            try:
                res = await evaluator.evaluate_task(task, task_index=order, total_tasks=len(JOBS), context=ctx)
            except Exception as exc:
                res = TaskResult(instance_id=iid, repo=task.repo, resolved=False, agent_patch='', test_output='',
                                 test_exit_code=-1, duration_seconds=time.time() - w0, task_index=order,
                                 error=f'notebook runner exception: {exc!r}\n{traceback.format_exc()[-2000:]}')
            row = {'variant': variant, 'instance_id': iid, 'repo': task.repo, 'order': order,
                   'resolved': bool(res.resolved), 'wall_s': round(time.time() - w0, 1),
                   'agent_s': round(getattr(ctx, 'agent_elapsed_seconds', 0) or 0, 1),
                   'tool_calls': getattr(ctx, 'tool_calls_used', None), 'llm_calls': getattr(ctx, 'llm_calls_used', None),
                   'patch_chars': len(res.agent_patch or ''), 'submitted': bool(getattr(ctx, 'patch_submitted', False)),
                   'env_overlay': iid in ENV_OVERLAY, 'end': end_reason(res.error), 'error': (res.error or '')[:3000]}
            async with lock:
                with open(PER_TASK, 'a', encoding='utf-8') as fh:
                    fh.write(json.dumps(row) + '\n')
                pdir = RESULTS / variant / 'patches'
                pdir.mkdir(parents=True, exist_ok=True)
                (pdir / f'{iid}.diff').write_text(res.agent_patch or '', encoding='utf-8')
                TALLY[variant][0] += row['resolved']
                TALLY[variant][1] += 1
                ENDS[variant][row['end']] += 1
                DONE.append(row)
                el = time.time() - T_START
                eta = el / len(DONE) * (len(JOBS) - len(DONE))
                tally = ' '.join(f'{v}={TALLY[v][0]}/{TALLY[v][1]}' for v in names)
                print(f"[{len(DONE):3}/{len(JOBS)}] {variant:11} {iid:22} resolved={row['resolved']!s:5} "
                      f"agent={row['agent_s']:5.0f}s tools={row['tool_calls']} patch={row['patch_chars']:5} "
                      f"end={row['end']:10} | {tally} | {el / 60:.0f} min, ETA {eta / 60:.0f} min"
                      + (f"\n      err: {row['error'][:200]!r}" if row['end'] not in ('ok', 'time', 'tool_budget') else ''),
                      flush=True)
                if len(DONE) % 20 == 0:
                    shutil.make_archive(str(WORKING_DIR / 'results'), 'zip', RESULTS)

    await asyncio.gather(*(one(i, v, iid) for i, (v, iid) in enumerate(JOBS, start=1)))


def run_sync(coro_fn):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop is not None and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(lambda: asyncio.run(coro_fn())).result()
    return asyncio.run(coro_fn())


print(f'{len(JOBS)} jobs, concurrency {CONCURRENCY}, no new task after {STOP_NEW_TASKS_AFTER_H} h', flush=True)
try:
    run_sync(run_all)
finally:
    shutil.make_archive(str(WORKING_DIR / 'results'), 'zip', RESULTS)
for v in names:
    r, n = TALLY[v]
    print(f'==> {v}: {r}/{n} resolved | ends {dict(ENDS[v])}')
print(f'total {(time.time() - T_START) / 60:.1f} min; skipped by the time guard: {len(JOBS) - len(DONE)}')
