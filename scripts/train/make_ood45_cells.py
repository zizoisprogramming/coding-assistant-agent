"""Writes the OOD-45 eval notebooks: our agents on 44 unseen-repo tasks (stand-in for the private hidden test).

    python3 scripts/train/make_ood45_cells.py 31b   -> kaggle/cells_ood45_31b/  (mix on the 31B, as submitted: T0.2)
    python3 scripts/train/make_ood45_cells.py 12b   -> kaggle/cells_ood45_12b/  (12B base + v2 LoRA at scale 1.0 / 0.5)

OOD-45 = Kaggle dataset rodrigospalma/ood45-bugfix-split (45 bug fixes merged 2026-09-18..10-03 in 17 repos the
public tasks do not use; gold patch resolves 3/3, empty patch fails). Its tools/ood45_harness.py materializes the
per-repo offline wheel sets and installs each task's dependencies in the subprocess sandbox (validated by its author on
swegemma 0.2.11, the wheelhouse we use). The runner follows the author's notebook (rodrigospalma/ood45-evaluate-your-
agent, cells 7-8): one Evaluator per (variant, repo) because wheels_dir is per repo, Evaluator.evaluate_task per job,
a shared queue with fixed concurrency. urllib3_5279 is skipped (does not run on Python 3.12, dataset README).

Attach (Add Input): the competition (tasks path, sandbox setup.py and graphs, as in the author's runs), the wheelhouse
(metric/gemma-4-developer-agent-wheelhouse), the model (google/gemma-4 -> the variant below), the dataset
rodrigospalma/ood45-bugfix-split, and for 12b the v2 training notebook output (folder adapter_12b_v2/final).

LoRA scale: our adapters were trained at r16 / alpha32 = scale 2.0 (forum 750713: 2.0 looped, 1.0 did not). vLLM
applies lora_alpha / r from adapter_config.json at load, so the 12b notebook copies the final v2 adapter twice with
lora_alpha = r * scale. No retraining.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVAL = ROOT / "kaggle" / "cells_eval_12b_sft"
WHICH = sys.argv[1] if len(sys.argv) > 1 else "31b"
SKIP = ["urllib3_5279"]

SETS = {  # model, base submission, {variant: (adapter name, scale, temperature)}, concurrency, stop new tasks after h
    "31b": ("gemma-4-31b-it-qat-w4a16-ct", "mix", {"mix31_t02": (None, None, 0.2)}, 4, 4.0),
    "12b": ("gemma-4-12b-it-qat-w4a16-ct", "mix_12b", {
        "base12_t10": (None, None, 1.0),
        "v2s10_t10": ("v2s10", 1.0, 1.0),
        "v2s05_t10": ("v2s05", 0.5, 1.0)}, 6, 5.0),
}
MODEL, BASE_SUB, VARIANTS, CONCURRENCY, STOP_H = SETS[WHICH]
OUT = ROOT / "kaggle" / f"cells_ood45_{WHICH}"
OUT.mkdir(parents=True, exist_ok=True)
ADAPTERS_USED = sorted({a for a, _, _ in VARIANTS.values() if a})


def must_replace(text, old, new):
    assert text.count(old) == 1, f"pattern not found once: {old[:60]!r}"
    return text.replace(old, new)


base = ROOT / "submissions" / BASE_SUB
base_files = {p.relative_to(base).as_posix(): p.read_text() for p in sorted(base.rglob("*")) if p.is_file()}
assert f"model: {MODEL}\n" in base_files["agent.yaml"], "base submission declares another model"
embedded = {}
for name, (adapter, scale, temp) in VARIANTS.items():
    files = dict(base_files)
    head = f"# OOD-45 {name}: {BASE_SUB} + " + (f"v2 LoRA at scale {scale}" if adapter else "no adapter") + \
        f", temperature {temp}.\n"
    files["agent.yaml"] = head + "\n".join(l for l in files["agent.yaml"].splitlines() if not l.startswith("#")) + "\n"
    if adapter:
        files["agent.yaml"] = must_replace(files["agent.yaml"], f"model: {MODEL}\n", f"model: {MODEL}\nadapter: {adapter}\n")
    if temp != 0.2:
        files["configs/sampling.yaml"] = must_replace(files["configs/sampling.yaml"], "temperature: 0.2\n",
                                                      f"temperature: {temp}\n" + ("top_k: 64\n" if temp >= 1.0 else ""))
    embedded[name] = files

# ---------------------------------------------------------------------------------------------------------- cell 1
c1 = (EVAL / "cell1.py").read_text()
c1 += '''

# Preflight: the 4x L4 shape (the runs below are sized for it).
_smi = subprocess.run(['nvidia-smi', '--query-gpu=index,name,memory.total', '--format=csv,noheader'],
                      capture_output=True, text=True).stdout.strip().splitlines()
print('GPUs:', _smi, '| CPUs:', os.cpu_count())
assert len(_smi) >= 4 and all('L4' in g for g in _smi), 'expected 4x L4: switch the accelerator before running on'
'''
(OUT / "cell1.py").write_text(c1)

# ---------------------------------------------------------------------------------------------------------- cell 2
adapter_block = ""
if ADAPTERS_USED:
    adapter_block = '''
# The v2 LoRA (final checkpoint of the v2 training notebook, attached as input), copied once per scale with
# lora_alpha = r * scale (vLLM scales the adapter by lora_alpha / r when it loads it).
_ad = sorted(glob.glob('/kaggle/input/**/adapter_12b_v2/final/adapter_config.json', recursive=True))
assert _ad, 'attach the v2 training notebook output (folder adapter_12b_v2/final with adapter_config.json)'
ADAPTER_SRC = Path(_ad[-1]).parent
ALL_ADAPTERS = WORKING_DIR / 'all_adapters'  # every adapter once, for the one vLLM server
shutil.rmtree(ALL_ADAPTERS, ignore_errors=True)
_src_cfg = json.loads((ADAPTER_SRC / 'adapter_config.json').read_text())
print('trained adapter:', ADAPTER_SRC, '| r', _src_cfg['r'], '| lora_alpha', _src_cfg['lora_alpha'],
      '| scale', _src_cfg['lora_alpha'] / _src_cfg['r'])
assert not _src_cfg.get('use_rslora') and not _src_cfg.get('alpha_pattern') and not _src_cfg.get('rank_pattern'), \\
    'adapter uses rslora / per-module alpha: the lora_alpha edit would not set the scale; stop and send me this output'
for name, (adapter, scale, temp) in VARIANTS.items():
    if not adapter:
        print(name, '| no adapter | temperature', temp)
        continue
    cfg = dict(_src_cfg, lora_alpha=_src_cfg['r'] * scale)
    for dst in (SUB_ROOT / name / 'adapters' / adapter, ALL_ADAPTERS / 'adapters' / adapter):
        dst.mkdir(parents=True, exist_ok=True)
        shutil.copy(ADAPTER_SRC / 'adapter_model.safetensors', dst / 'adapter_model.safetensors')
        (dst / 'adapter_config.json').write_text(json.dumps(cfg, indent=2))
    print(name, '| adapter', adapter, '| lora_alpha', cfg['lora_alpha'], '-> scale', cfg['lora_alpha'] / cfg['r'],
          '| temperature', temp)
'''
c2 = f'''# 2. OOD-45 setup (see scripts/train/make_ood45_cells.py): the submissions under test, the 44 tasks and the
#    per-repo offline wheel sets, through the dataset's own tools/ood45_harness.py (fails fast, before any GPU time,
#    on a swegemma version its author did not validate, a missing snapshot or a missing wheel set).
import json, random, re
from collections import Counter
WORKING_DIR = Path('/kaggle/working')
SUB_ROOT = WORKING_DIR / 'submissions'
RESULTS = WORKING_DIR / 'results'
VARIANTS = {VARIANTS!r}  # name: (adapter, LoRA scale, temperature)
CONCURRENCY = {CONCURRENCY}  # tasks running at the same time, all variants share one queue
STOP_NEW_TASKS_AFTER_H = {STOP_H}  # quota guard: no new task starts after this many hours (L4x4 bills 2x)
SKIP = {set(SKIP)!r}  # does not run on Python 3.12 (dataset README)
EMBEDDED = {json.dumps(embedded, indent=1)}


def _first(*cands, pattern=None):
    for c in cands:
        if Path(c).exists():
            return Path(c)
    hits = sorted(glob.glob(pattern, recursive=True)) if pattern else []
    if not hits:
        print('attached inputs (3 levels):', sorted(glob.glob('/kaggle/input/*/*/*'))[:40])
    assert hits, f'none of {{cands}} exists: attach it as a notebook input'
    return Path(hits[0])


DATA_DIR = _first('/kaggle/input/competitions/gemma-4-developer-agent', '/kaggle/input/gemma-4-developer-agent')
# The dataset is found by its own file (tools/ood45_harness.py), whatever folder name Kaggle mounts it under.
OOD_DIR = _first('/kaggle/input/datasets/rodrigospalma/ood45-bugfix-split', '/kaggle/input/ood45-bugfix-split',
                 pattern='/kaggle/input/**/tools/ood45_harness.py')
OOD_DIR = OOD_DIR.parent.parent if OOD_DIR.name == 'ood45_harness.py' else OOD_DIR
print('competition:', DATA_DIR, '| OOD-45:', OOD_DIR)

shutil.rmtree(SUB_ROOT, ignore_errors=True)
shutil.rmtree(RESULTS, ignore_errors=True)
RESULTS.mkdir(parents=True)  # ood45_harness logs each sandbox install to results/ood_env_install.jsonl
for name, files in EMBEDDED.items():
    for rel, text in files.items():
        path = SUB_ROOT / name / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
{adapter_block}
sys.path.insert(0, str(OOD_DIR / 'tools'))
import ood45_harness as ood  # noqa: E402
OOD_RUN = ood.setup(OOD_DIR)
RUN_IDS = sorted(i for i in OOD_RUN.tasks if i not in SKIP)
REPO_OF = {{i: OOD_RUN.meta[i]['repo'] for i in RUN_IDS}}
ENV_OVERLAY = sorted(i for i in RUN_IDS if OOD_RUN.meta[i]['env_overlay'])
print(f'OOD-45: {{len(RUN_IDS)}} tasks (skipped {{sorted(SKIP)}}) in {{len(set(REPO_OF.values()))}} repos | wheel set',
      OOD_RUN.wheel_set, '| swegemma', ood.check_swegemma(), '| env_overlay tasks:', len(ENV_OVERLAY))
print('tasks per repo:', dict(sorted(Counter(REPO_OF.values()).items())))
print('variants:', list(VARIANTS), '| jobs:', len(RUN_IDS) * len(VARIANTS), '| concurrency', CONCURRENCY)
'''
(OUT / "cell2.py").write_text(c2)

# ---------------------------------------------------------------------------------------------------------- cell 3
c3 = (EVAL / "cell3.py").read_text()
c3 = must_replace(c3, "# 3. Start vLLM with LoRA on and the submission's adapter (as the host notebook / scorer). ~6–8 min.",
                  "# 3. Start vLLM with LoRA on (as the host notebook / scorer)" +
                  (" and every adapter under test" if ADAPTERS_USED else "") + ". ~6–10 min.")
c3 = must_replace(c3, "TARGET_MODEL_NAME = 'gemma-4-12b-it-qat-w4a16-ct'", f"TARGET_MODEL_NAME = {MODEL!r}")
if WHICH == "31b":  # LoRA on (as the scorer) at the author's validated 31B setting (his notebook cell 6)
    c3 = must_replace(c3, "gpu_memory_utilization=0.90,", "gpu_memory_utilization=0.80,  # OOD-45 author's 31B run")
c3 = must_replace(c3, "ADAPTERS = discover_adapters(str(SUB_ROOT / 'mix_12b_sft'), adapter_extensions=ALLOWED_ADAPTER_EXTENSIONS)",
                  "ADAPTERS = discover_adapters(str(ALL_ADAPTERS), adapter_extensions=ALLOWED_ADAPTER_EXTENSIONS)"
                  if ADAPTERS_USED else "ADAPTERS = None  # no adapter in this notebook")
c3 = must_replace(c3, "print('adapters found:', list(ADAPTERS.adapters))",
                  "print('adapters found:', list(ADAPTERS.adapters) if ADAPTERS else None)")
tail_old = c3[c3.index("assert 'sft_v1' in _served"):]
if ADAPTERS_USED:
    tail_new = f'''assert {set(ADAPTERS_USED)!r} <= set(_served), 'vLLM does not serve every adapter: stop and send me this output'
def _ask(model):
    body = {{'model': model, 'max_tokens': 60, 'temperature': 0, 'messages': [{{'role': 'user', 'content':
            'You are fixing a bug in /workspace. What is your first tool call? Answer in one line.'}}]}}
    req = _url.Request(_base + '/chat/completions', data=_json.dumps(body).encode(), headers={{'Content-Type': 'application/json'}})
    return _json.load(_url.urlopen(req))['choices'][0]['message'].get('content')
# Same greedy prompt to the base and to each scale: the replies should drift away from the base as the scale grows.
for _m in [str(MODEL_PATH)] + {ADAPTERS_USED!r}:
    print(f'{{_m[-30:]:>30}}:', repr(_ask(_m)))
'''
else:
    tail_new = "assert str(MODEL_PATH) in _served, 'vLLM does not serve the model: stop and send me this output'\n"
c3 = c3.replace(tail_old, tail_new)
(OUT / "cell3.py").write_text(c3)

# --------------------------------------------------------------------------------------------------------- cell 3b
logger_src = (ROOT / "scripts" / "request_logger.py").read_text()
auto = logger_src[logger_src.index("REQUEST_LOG = install_request_logger("):]
(OUT / "cell3b_request_logger.py").write_text(logger_src.replace(auto, '''import contextvars
JOB = contextvars.ContextVar('ood_job', default=None)  # set by cell 4 around each task: which variant and task
REQUEST_LOG = install_request_logger(Path('/kaggle/working') / 'requests' / 'requests.jsonl',
                                     tag=lambda: {'job': JOB.get()})
print('Recording model requests to', REQUEST_LOG, '(diagnostics only: OOD-45 is our yardstick, never training data)')
'''))

# ---------------------------------------------------------------------------------------------------------- cell 4
c4 = r'''# 4. Run every variant on the 44 tasks. One shared queue: tasks in a repo-stratified order (seed 1), the variants of a
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
'''
(OUT / "cell4.py").write_text(c4)

# ---------------------------------------------------------------------------------------------------------- cell 5
c5 = r'''# 5. Summary (paste this output to Claude), then STOP THE SESSION.
#    Per variant: resolved overall, without the 14 env_overlay tasks, macro average per repo (great-tables holds 12),
#    how runs ended, and loop signs from the traces. Then one row per task across variants.
import collections, glob, json, statistics
from pathlib import Path

RES = Path('/kaggle/working/results')
rows = [json.loads(l) for l in open(RES / 'ood_per_task.jsonl')] if (RES / 'ood_per_task.jsonl').exists() else []
variants = list(dict.fromkeys(r['variant'] for r in rows))


def trace_stats(variant, iid):
    f = RES / variant / 'traces' / f'trace_{iid}.json'
    if not f.exists():
        return None
    calls = []
    for s in json.load(open(f)).get('steps', []):
        if s.get('source') == 'agent':
            calls += [(c.get('function_name'), json.dumps(c.get('arguments'), sort_keys=True)) for c in s.get('tool_calls') or []]
    return {'calls': len(calls), 'max_same': max(collections.Counter(calls).values(), default=0)}


summary = {}
print(f"{'variant':12} {'resolved':>9} {'no-overlay':>10} {'repo-macro':>10} {'empty':>5} {'loops':>5} {'med-agent-s':>11} ends")
for v in variants:
    rs = [r for r in rows if r['variant'] == v]
    no = [r for r in rs if not r['env_overlay']]
    by_repo = collections.defaultdict(list)
    for r in rs:
        by_repo[r['repo']].append(r['resolved'])
    macro = statistics.mean(sum(x) / len(x) for x in by_repo.values()) if by_repo else 0
    st = [trace_stats(v, r['instance_id']) for r in rs]
    loops = sum(1 for s in st if s and s['max_same'] >= 4)  # same exact call 4+ times in one run
    summary[v] = {'resolved': sum(r['resolved'] for r in rs), 'n': len(rs),
                  'resolved_no_overlay': sum(r['resolved'] for r in no), 'n_no_overlay': len(no),
                  'repo_macro': round(macro, 3), 'empty_patch': sum(r['patch_chars'] == 0 for r in rs), 'loops': loops,
                  'median_agent_s': statistics.median([r['agent_s'] for r in rs]) if rs else None,
                  'ends': dict(collections.Counter(r['end'] for r in rs))}
    s = summary[v]
    print(f"{v:12} {s['resolved']:>4}/{s['n']:<4} {s['resolved_no_overlay']:>5}/{s['n_no_overlay']:<4} "
          f"{100 * s['repo_macro']:>9.1f}% {s['empty_patch']:>5} {loops:>5} {s['median_agent_s']:>11} {s['ends']}")
(RES / 'summary.json').write_text(json.dumps(summary, indent=2))

print('\nper task (R = resolved, . = not, - = not run; calls / max repeats of one identical call):')
ids = sorted({r['instance_id'] for r in rows})
by = {(r['variant'], r['instance_id']): r for r in rows}
print(f"{'task':24} " + ' '.join(f'{v:>16}' for v in variants))
for i in ids:
    cells = []
    for v in variants:
        r, s = by.get((v, i)), trace_stats(v, i)
        cells.append('-' if r is None else ('R' if r['resolved'] else '.') + (f" {s['calls']}c/x{s['max_same']}" if s else '')
                     + f" {r['end'][:6]}")
    print(f'{i:24} ' + ' '.join(f'{c:>16}' for c in cells))
env = RES / 'ood_env_install.jsonl'
if env.exists():
    recs = [json.loads(l) for l in open(env)]
    bad = [r for r in recs if not any(a.get('exit') == 0 for a in r.get('editable') or [])]
    print(f'\nsandbox installs logged: {len(recs)}, editable install never succeeded: {len(bad)}',
          sorted({r['repo'] for r in bad}))
'''
(OUT / "cell5_summary.py").write_text(c5)
print("wrote", OUT.relative_to(ROOT), sorted(p.name for p in OUT.iterdir()))
