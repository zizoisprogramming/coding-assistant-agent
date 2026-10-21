"""Writes kaggle/cells_gen/: GENERATION for self-distillation. Gemma 31B (the mix agent, no LoRA, T1.0) attempts our
verified SWE-rebench tasks; every model call is recorded (request logger) so resolved runs become training samples.

    python3 scripts/train/make_gen_cells.py            # MODE 'trial' (edit MODE in cell 2 for 'full' / 'retry')

Runs on the user's OTHER account (30 h quota; L4x4 bills 2x -> ~15 h wall), plan agreed 2026-10-21:
  trial  ~20 tasks: 8 at concurrency 4, then 12 at concurrency 6 -> measured throughput decides CONCURRENCY (~40 min)
  full   every task once (attempt 1); trial runs count; stops starting tasks after STOP_NEW_TASKS_AFTER_H
  retry  attempt 2 on every task that has no resolved run yet (failed or not reached)
Each session attaches the earlier sessions' outputs: done (task, attempt) pairs are skipped (resume).

Inputs: the competition (sandbox setup.py; tasks path as the author's runs), the wheelhouse, the model google/gemma-4 ->
gemma-4-31b-it-qat-w4a16-ct, rodrigospalma/ood45-bugfix-split (tools/ood45_harness.py + its wheel house of Docker
extras), the final task set (private dataset from the verification notebook, shared with this account), and the
earlier generation outputs (from the second session on). GPU L4x4, INTERNET OFF (as grading; the offline fail-fast hook
and the host pytest plugin wheels are the verified environment: kaggle/cells_rebench_verify).

The agent is submissions/mix byte for byte except temperature 0.2 -> 1.0 (user: varied runs; retries differ).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/datasets"))
import make_rebench_full_cells as M  # noqa: E402
import make_rebench_verify_cells as V  # noqa: E402

OUT = ROOT / "kaggle/cells_gen"
SRC31 = ROOT / "kaggle/cells_ood45_31b"


def submission():
    files = {str(p.relative_to(ROOT / "submissions/mix")): p.read_text() for p in sorted((ROOT / "submissions/mix").rglob("*"))
             if p.is_file()}
    old = "temperature: 0.2\n"
    assert files["configs/sampling.yaml"].count(old) == 1
    files["configs/sampling.yaml"] = files["configs/sampling.yaml"].replace(
        old, "temperature: 1.0  # generation (user 2026-10-21): varied runs; the submission uses 0.2\n")
    # Trial (2026-10-21, data/results/2026-10-21_gen_trial): 6 runs at once share the GPU, so each one decodes slower and
    # 7/12 hit the 8-min clock (1/8 at 4 at once): time cuts that the scorer would not make. Generation gets 12 min to
    # undo that slowdown; tool calls (28, the binding budget) and turns stay as submitted.
    old = "  max_time_minutes: 8\n"
    assert files["eval_config.yaml"].count(old) == 1
    files["eval_config.yaml"] = files["eval_config.yaml"].replace(old, "  max_time_minutes: 12\n")
    return files


def sandbox_env():
    """The verified sandbox setup, taken from the gate cells so it cannot drift: host-only pytest plugins hidden,
    install records tagged per task, the offline fail-fast hook, and import_name()."""
    s = M.CELL4
    plugins_and_tags = s[s.index("# Host-only pytest plugins"):s.index("WHEEL_ROOT = Path('/tmp/rb_wheels')")]
    names = s[s.index("def import_name(r):"):s.index("def as_task(r):")]
    cleanup = s[s.index("RUNNING = {}"):s.index("def tail(")]
    return "import contextvars, tempfile, threading\n" + plugins_and_tags + V.OFFLINE_HOOK + "\n\n" + names + cleanup


CELL2 = '''# 2. GENERATION setup (scripts/train/make_gen_cells.py): mode, the task set, the agent, the verified sandbox
#    environment, and resume from earlier sessions. GPU L4x4, INTERNET OFF.
import collections, json, random, re, tarfile, time
from collections import Counter

assert sys.version_info[:2] == (3, 12), (f'Python {{sys.version.split()[0]}}: generation needs Python 3.12 + torch 2.10 '
    '(vLLM 0.19.1): Copy & Edit an old GPU notebook and set Environment -> Pin to original environment')
MODE = 'full'  # 'trial' (done 2026-10-21) -> 'full' -> 'retry' (one session each; attach the earlier sessions' outputs)
TRIAL_PHASES = [(4, 8), (6, 12)]  # trial: (concurrency, tasks): measured throughput decides CONCURRENCY below
CONCURRENCY = 6  # full / retry: trial 2026-10-21: 40.9 attempts/h at 6 vs 31.4 at 4
STOP_NEW_TASKS_AFTER_H = 10.5  # Kaggle ends GPU sessions at 12 h; a task takes <= ~10 min
T_START = time.time()
WORKING_DIR = Path('/kaggle/working')
SUB_DIR = WORKING_DIR / 'submission'
RESULTS = WORKING_DIR / 'results'
PER_TASK = RESULTS / 'gen_per_task.jsonl'
WHEEL_SET = f'{{__import__("platform").machine()}}-cp{{sys.version_info.major}}{{sys.version_info.minor}}'
SUBMISSION = {submission!r}


def _first(*cands, pattern=None):
    for c in cands:
        if Path(c).exists():
            return Path(c)
    hits = sorted(glob.glob(pattern, recursive=True)) if pattern else []
    assert hits, f'none of {{cands}} exists: attach it as a notebook input'
    return Path(hits[0])


try:
    urllib_ok = __import__('urllib.request').request.urlopen('https://pypi.org/simple/pip/', timeout=10)
    raise SystemExit('INTERNET IS ON: turn Settings -> Internet OFF (generation runs offline, as grading), then re-run')
except SystemExit:
    raise
except Exception:
    print('internet: off (good)')
DATA_DIR = _first('/kaggle/input/competitions/gemma-4-developer-agent', '/kaggle/input/gemma-4-developer-agent')
OOD_DIR = _first('/kaggle/input/datasets/rodrigospalma/ood45-bugfix-split', '/kaggle/input/ood45-bugfix-split',
                 pattern='/kaggle/input/**/tools/ood45_harness.py')
OOD_DIR = OOD_DIR.parent.parent if OOD_DIR.name == 'ood45_harness.py' else OOD_DIR
# The task set = the verification notebook's output (its rebench/ has verify_gate.json next to tasks.jsonl).
_sets = sorted(Path(p).parent for p in glob.glob('/kaggle/input/**/rebench/verify_gate.json', recursive=True))
assert len(_sets) == 1, f'attach exactly one final task set (verification output); found {{_sets}}'
OUT = _sets[0]
print('competition:', DATA_DIR, '| OOD-45 tools:', OOD_DIR, '| task set:', OUT)

ROWS = {{}}
for l in open(OUT / 'tasks.jsonl'):
    r = json.loads(l)
    ROWS[r['instance_id']] = r
assert (OUT / 'wheels' / WHEEL_SET / 'manifest.json').exists(), f'the task set has no wheel set {{WHEEL_SET}}'
print(f"{{len(ROWS)}} tasks from {{len({{r['repo'] for r in ROWS.values()}})}} repos | domains",
      dict(Counter(r['domain'] for r in ROWS.values())), '| text', dict(Counter(r['text_kind'] for r in ROWS.values())))

shutil.rmtree(SUB_DIR, ignore_errors=True)
for rel, text in SUBMISSION.items():
    (SUB_DIR / rel).parent.mkdir(parents=True, exist_ok=True)
    (SUB_DIR / rel).write_text(text, encoding='utf-8')
print('agent: submissions/mix with', [l for l in SUBMISSION['configs/sampling.yaml'].splitlines() if l.startswith('temperature')])

# Resume: every earlier session's rows (attached outputs) + this session's own (a re-run of this notebook).
RESULTS.mkdir(parents=True, exist_ok=True)
PREV = []
for p in sorted(glob.glob('/kaggle/input/**/results/gen_per_task.jsonl', recursive=True)) + ([str(PER_TASK)] if PER_TASK.exists() else []):
    PREV += [json.loads(l) for l in open(p)]
DONE_JOBS = {{(r['instance_id'], r['attempt']) for r in PREV if r['end'] != 'runner'}}
SOLVED = {{r['instance_id'] for r in PREV if r['resolved']}}
print(f'earlier runs: {{len(PREV)}} ({{len(DONE_JOBS)}} done jobs, {{len(SOLVED)}} tasks solved) | mode {{MODE}}')

# The verified sandbox environment (as kaggle/cells_rebench_verify): ood45_harness's install step, host pytest plugin
# wheels shipped with the task set, host-only plugins hidden, network fails fast inside the sandbox.
sys.path.insert(0, str(OOD_DIR / 'tools'))
import ood45_harness as ood  # noqa: E402
print('swegemma', ood.check_swegemma())
ood._STATE['house'] = OOD_DIR / 'wheels' / 'house'
ood.ENV_LOG['path'] = str(RESULTS / 'gen_env_install.jsonl')
ood.patch_harness()
WHEEL_ROOT = Path('/tmp/gen_wheels')
ood.materialize_wheels(OUT, WHEEL_SET, WHEEL_ROOT / WHEEL_SET)
_host = sorted(str(p) for p in (OUT / 'wheels' / 'host').glob('*.whl'))
_r = subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '--no-index', '--no-deps', *_host], capture_output=True, text=True)
print('host pytest plugins:', [Path(p).name for p in _host], '-> exit', _r.returncode, _r.stderr[-200:])
'''

CELL4 = r'''# 4. RUN: one line per finished attempt. results/gen_per_task.jsonl gets a row each; traces/patches under results/gen;
#    every model call in requests/requests.jsonl (tagged task#attempt). Zipped every 20 attempts and at the end.
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
    PHASES = [(CONCURRENCY, [(i, 1) for i in ORDER if (i, 1) not in DONE_JOBS])]
elif MODE == 'retry':
    PHASES = [(CONCURRENCY, [(i, 2) for i in ORDER if i not in SOLVED and (i, 2) not in DONE_JOBS])]
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
        snapshots_dir=OUT / 'snapshots', wheels_dir=WHEEL_ROOT / WHEEL_SET / iid,
        results_dir=RESULTS / 'gen', submission_dir=SUB_DIR, models=models, sandbox='subprocess',
        graph_dir=str(DATA_DIR / 'graphs'), embeddings_dir=str(DATA_DIR / 'embeddings'),
        limits=LIMITS, generation_constraints=GEN_CONSTRAINTS, adapter_manifest=MANIFEST,
        context_cache_config=ContextCacheConfig(min_tokens=2048, ttl_seconds=1800, cache_intervals=10),
        events_compaction_config=EventsCompactionConfig(
            compaction_interval=5, overlap_size=2, token_threshold=14336, event_retention_size=5),
        display_mode='quiet', **EVAL_CFG))


def as_task(r):
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
            if len(DONE) % 20 == 0:
                shutil.make_archive(str(WORKING_DIR / 'results'), 'zip', RESULTS)

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
    shutil.make_archive(str(WORKING_DIR / 'results'), 'zip', RESULTS)
print(f'==> {MODE}: solved {TALLY[0]}/{TALLY[1]} | ends {dict(ENDS)} | {(time.time() - T_START) / 60:.1f} min; '
      f'not started (time guard): {N_JOBS - len(DONE)}')
'''

CELL5 = r'''# 5. SUMMARY (paste this output to Claude): this session + all sessions so far, throughput, where runs end.
ALL = PREV + [r for r in DONE if r not in PREV]
print('this session:', MODE, '| phases', json.dumps(PHASE_STATS))
if MODE == 'trial' and len(PHASE_STATS) == 2:
    a, b = PHASE_STATS
    print(f"throughput: concurrency {a['concurrency']} -> {a['attempts_per_hour']}/h (agent {a['mean_agent_s']}s), "
          f"concurrency {b['concurrency']} -> {b['attempts_per_hour']}/h (agent {b['mean_agent_s']}s); "
          f"full pass of {len(ROWS)} tasks at the better one: {len(ROWS) / max(a['attempts_per_hour'], b['attempts_per_hour']):.1f} h")
by_task = collections.defaultdict(list)
for r in ALL:
    by_task[r['instance_id']].append(r)
print(f"all sessions: {len(ALL)} attempts on {len(by_task)}/{len(ROWS)} tasks | tasks with a resolved run: "
      f"{sum(any(x['resolved'] for x in v) for v in by_task.values())} | resolved attempts {sum(r['resolved'] for r in ALL)}")
for key in ('attempt', 'level', 'domain', 'text_kind', 'leak', 'unfair', 'env_partial'):
    c = collections.defaultdict(lambda: [0, 0])
    for r in ALL:
        c[r[key]][0] += r['resolved']
        c[r[key]][1] += 1
    print(f'  by {key:11}', {k: f'{v[0]}/{v[1]}' for k, v in sorted(c.items(), key=lambda kv: str(kv[0]))})
print('  ends', dict(Counter(r['end'] for r in ALL)))
med = lambda xs: sorted(xs)[len(xs) // 2] if xs else None  # noqa: E731
print(f"  median agent_s {med([r['agent_s'] for r in ALL])} | median tool calls {med([r['tool_calls'] or 0 for r in ALL])} "
      f"| median llm calls {med([r['llm_calls'] or 0 for r in ALL])} | submitted {sum(r['submitted'] for r in ALL)}/{len(ALL)}")
req = WORKING_DIR / 'requests' / 'requests.jsonl'
print('request log:', f'{req.stat().st_size / 1e6:.0f} MB, {sum(1 for _ in open(req))} calls' if req.exists() else 'MISSING')
'''


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cell1.py").write_text((SRC31 / "cell1.py").read_text())
    (OUT / "cell2.py").write_text(CELL2.format(submission=submission()) + "\n" + sandbox_env())
    (OUT / "cell3.py").write_text((SRC31 / "cell3.py").read_text())
    logger = (SRC31 / "cell3b_request_logger.py").read_text()
    old = "print('Recording model requests to', REQUEST_LOG, '(diagnostics only: OOD-45 is our yardstick, never training data)')"
    assert logger.count(old) == 1
    (OUT / "cell3b_request_logger.py").write_text(logger.replace(
        old, "print('Recording model requests to', REQUEST_LOG, '(training data: tagged task#attempt)')"))
    (OUT / "cell4_run.py").write_text(CELL4)
    (OUT / "cell5_summary.py").write_text(CELL5)
    print("wrote", OUT.relative_to(ROOT), sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
