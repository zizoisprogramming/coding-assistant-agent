# 3. TEST SIGNAL (scripts/train/make_testsignal_cells.py): per d40 task, the baseline (no patch), the reference patch
#    (calibration) and every distinct candidate patch, each run on EXISTING test files of the changed modules through the
#    harness's verify_task (hidden test_patch replaced). One line per run. Writes results/testsignal/rows.jsonl.
import dataclasses, io, logging, tarfile, warnings
warnings.filterwarnings('ignore')
logging.getLogger('swegemma.sandbox.subprocess').setLevel(logging.ERROR)
from adk_submission import ModelRegistry
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.apps._configs import EventsCompactionConfig
from swegemma.config import EvalConfig, build_submission_limits
from swegemma.deduplication import resolve_task_snapshot_paths
from swegemma.evaluate import Evaluator
from swegemma.harness.verification import verify_task
from swegemma.models import load_tasks
from swegemma.models.task import Task

SEL_MAX = 4
TEST_RE = re.compile(r"(^|/)(tests?|testing)/.*\.py$|(^|/)test_[^/]*\.py$")
SUB = WORKING_DIR / 'submission'
for rel, text in {'agent.yaml': 'name: swe_agent\nmodel: gemma-4-31b-it-qat-w4a16-ct\ninstruction: !include prompts/system.md\ntools:\n  - run_command\n  - read_file\n  - edit_file\n  - write_file\n  - get_status\n  - submit_patch\ngenerate_content_config: !include configs/sampling.yaml\n', 'configs/sampling.yaml': '# Arm mix (rung-3e): bf prompt + r4 decision rule/example/edit fallback; bf tools. Thinking set from rung-3d\n# (placeholder 2048 / max_output 4096, as r4_mid).\ntemperature: 1.0  # generation (user 2026-10-21): varied runs; the submission uses 0.2\ntop_p: 0.95\nmax_output_tokens: 4096\nthinking_config:\n  thinking_budget: 2048\n  include_thoughts: true\n', 'eval_config.yaml': 'evaluation:\n  timeout_seconds: 240\n  max_tool_calls: 28\n  max_time_minutes: 15\n  max_turns: 80\n', 'prompts/system.md': 'You are an expert autonomous software engineer assigned to resolve one issue in a repository, fast and minimally.\n\n## How you are scored, and the one decision rule (from r4)\nHidden tests run on your final diff, even if you run out of time; no edit scores zero. As soon as you can say which\nlines to change and how, your very next tool call is that edit, even if you are only fairly sure. Never re-read,\nsearch again or write a script first. Checking comes after the edit; if the check shows a problem, adjust the edit.\n\n## Step 0: Extract the contract (before any tool call)\nFrom the problem statement, list the exact function names, class names, error messages, exception types, HTTP status codes, CLI flags, and parameter names it mentions, copied character-for-character. Hidden tests exercise exactly these names and spellings. Ignore template boilerplate in the issue: HTML comments, checklists, AI disclaimers.\n\n## Step 1: Locate (calls 1-6)\nThe first user message already contains the workspace layout, so never spend a call on ls or find to orient.\n- Search the most specific identifier or error string: git grep -n "text" -- \'*.py\' | head -20\n- read_file with start and end line, at most 120 lines per read, one follow-up read at most. Never read whole files.\n- Older tool outputs are dropped from your context, so after each important finding write one short line: file, line, what it means, next step.\n\n## Step 2: Edit (the decision rule above)\n- Apply the minimal fix directly to source files. Match the existing style of the file.\n- edit_file mechanics: copy the real characters from read_file output, never JSON-escape backslashes. Keep old_string short and unique: never include docstrings, triple-quoted strings, or blank-line runs. Several small edits beat one large edit. If a call fails validation, never resend the identical call: re-read the exact lines and rebuild from a fresh short anchor, or edit with run_command: python3 - << \'EOF\' (open the file, assert the old text occurs once, replace it, write it back) EOF.\n- Feature request: copy the closest existing sibling feature end to end, including imports, __all__ exports, dispatch or option tables, and type hints.\n- Fix the behaviour where it is produced, not where it is observed.\n- For documentation-code tasks (e.g. FastAPI), edit executable code under docs_src/.\n\n## Step 3: One check, one repair, then submit\n- Run ONLY the targeted test for the file you changed: python3 -m pytest tests/test_target.py -x -q -k name -p no:anyio -o timeout=0 > /tmp/t1.log 2>&1; tail -n 25 /tmp/t1.log\n- If it fails, make one repair, then submit. A local green test is not the grader: submit even if the check is red or skipped. The working tree is graded as it is, so an edit made in time counts even if you never run a test.\n- NEVER run bare pytest, pytest ., or full-repo suites. NEVER repair pre-existing failures, missing fixtures, or import errors unrelated to your change. NEVER create test stubs.\n- To locate a test file: find tests -name "*name*.py"\n\n## Step 4: Patch hygiene, then finish\n- Scratch scripts go in /tmp only. Files left anywhere else in the repository become part of your patch and fail grading.\n- Before submit_patch: run git status --short and git diff --stat. If a test-looking path appears in the diff (tests/, conftest.py, pytest.ini, pyproject.toml, setup.cfg, tox.ini), restore it: git checkout -- path\n- submit_patch and get_status are free: they never count against the budget. submit_patch can be re-issued after further edits; the last one wins. After your first submission, verify patch_size > 0.\n- If get_status shows under 90 seconds remaining, call submit_patch immediately.\n- Do not end a turn with plain prose: keep calling tools or call submit_patch. Finish as soon as the edit is in so later tasks keep their time.\n\n## Example (an invented package)\nTask: "Client should reject a negative timeout." git grep finds pkg/client.py line 88, self.timeout = timeout, and\ntwo lines below ValueError("retries must be >= 0") for retries. Found it: the very next call is the edit that adds\nthe same kind of check, raising ValueError("timeout must be >= 0"). Then the client tests, then submit: 8 calls.\n\n## Never\n- Never modify, create, or delete test files or test configuration: anything under tests/, conftest.py, pytest.ini, pyproject.toml, setup.cfg, tox.ini. The grader resets them and applying your patch fails if they differ.\n- Never search outside /workspace for sources or packages. All dependencies are pre-installed; a ModuleNotFoundError means fix the code under /workspace.\n- Never refactor or reformat unrelated code.\n- Never conclude without a non-empty patch: submit whatever partial edit exists.'}.items():
    (SUB / rel).parent.mkdir(parents=True, exist_ok=True)
    (SUB / rel).write_text(text)
OUT = WORKING_DIR / 'results' / 'testsignal'
OUT.mkdir(parents=True, exist_ok=True)
limits, gen_constraints = build_submission_limits()
config = EvalConfig(
    tasks_path=DATA_DIR / 'tasks.jsonl', snapshots_dir=DATA_DIR / 'snapshots', results_dir=OUT / 'eval',
    submission_dir=SUB, models=ModelRegistry(), sandbox='subprocess', wheels_dir=DATA_DIR / 'wheels',
    graph_dir=str(DATA_DIR / 'graphs'), embeddings_dir=str(DATA_DIR / 'embeddings'), task_ids=sorted({c['instance_id'] for c in CANDS}),
    limits=limits, generation_constraints=gen_constraints,
    context_cache_config=ContextCacheConfig(min_tokens=2048, ttl_seconds=1800, cache_intervals=10),
    events_compaction_config=EventsCompactionConfig(compaction_interval=5, overlap_size=2, token_threshold=14336,
                                                    event_retention_size=5),
    display_mode='quiet', timeout_seconds=600, max_tool_calls=28, max_time_minutes=15.0, max_turns=80)
TASKS = {t.instance_id: t for t in load_tasks(DATA_DIR / 'tasks.jsonl')}


@dataclasses.dataclass(frozen=True)
class SelTask(Task):
    """A task whose verification runs the given EXISTING test files (no hidden test_patch)."""
    sel_files: tuple = ()

    @property
    def test_files(self):
        return list(self.sel_files)


def changed_sources(patch):
    return [f for f in re.findall(r'^\+\+\+ b/(\S+)', patch, re.M) if f.endswith('.py') and not TEST_RE.search(f)]


def snapshot_files(iid):
    """{path: text} of the repo's test files in the task snapshot (base + patch layers)."""
    task = TASKS[iid]
    snap, base_snap, patch_path = resolve_task_snapshot_paths(config.snapshots_dir, iid, task.repo)
    out = {}
    for p in [base_snap, snap]:
        if not p or not Path(p).exists() or not str(p).endswith(('.tgz', '.tar.gz', '.tar')):
            continue
        with tarfile.open(p) as tf:
            for m in tf.getmembers():
                name = m.name.split('/', 1)[1] if m.name.startswith(('./', 'workspace/')) else m.name
                name = name.removeprefix('./')
                if m.isfile() and TEST_RE.search(name) and not name.endswith('conftest.py'):
                    out[name] = tf.extractfile(m).read().decode('utf-8', 'replace')
    return out


def select_tests(iid, sources):
    """Existing test files a runtime picker could choose: they import a changed module or are named after it."""
    tests = snapshot_files(iid)
    scored = []
    for path, text in tests.items():
        s = 0
        for src in sources:
            mod = src[:-3].replace('/', '.').removesuffix('.__init__')
            pkg, _, stem = mod.rpartition('.')
            if re.search(rf'\b(import|from)\s+{re.escape(mod)}\b', text) or (pkg and re.search(rf'from\s+{re.escape(pkg)}\s+import\s+[^\n]*\b{re.escape(stem)}\b', text)):
                s += 2
            if stem and stem not in ('__init__', 'utils', 'main') and stem in Path(path).stem:
                s += 3
        if s:
            scored.append((-s, len(text), path))
    return [p for _, _, p in sorted(scored)[:SEL_MAX]]


def counts(out):
    m = {k: int(v) for v, k in re.findall(r'(\d+) (passed|failed|errors?|skipped)', out or '')}
    return m.get('passed', 0), m.get('failed', 0), m.get('error', 0) + m.get('errors', 0)


async def run_one(iid, files, patch):
    task = TASKS[iid]
    st = SelTask(**{f.name: getattr(task, f.name) for f in dataclasses.fields(Task)}, sel_files=tuple(files))
    st = dataclasses.replace(st, test_patch='')
    snap, base_snap, patch_path = resolve_task_snapshot_paths(config.snapshots_dir, iid, task.repo)
    t0 = time.perf_counter()
    try:
        res = await verify_task(EVAL.docker, config, st, snap, agent_patch=patch, base_snapshot_path=base_snap,
                                patch_path=patch_path, start_time=t0)
        p, f, e = counts(res.test_output)
        row = {'ok': bool(res.resolved), 'exit': res.test_exit_code, 'passed': p, 'failed': f, 'errors': e,
               'error': (res.error or '')[:200], 'tail': ' / '.join((res.test_output or '').strip().splitlines()[-2:])[-240:]}
    except Exception as ex:
        row = {'ok': False, 'exit': -9, 'passed': 0, 'failed': 0, 'errors': 0, 'error': f'{type(ex).__name__}: {str(ex)[:200]}', 'tail': ''}
    for d in glob.glob('/tmp/swegemma_sandbox_*'):
        shutil.rmtree(d, ignore_errors=True)
    row['seconds'] = round(time.perf_counter() - t0)
    return row


async def main():
    global EVAL
    EVAL = Evaluator(config)
    by_task = collections.defaultdict(list)
    for c in CANDS:
        by_task[c['instance_id']].append(c)
    fh = open(OUT / 'rows.jsonl', 'w')
    for k, (iid, cs) in enumerate(sorted(by_task.items()), 1):
        sources = sorted({s for c in cs for s in changed_sources(c['patch'])} | set(changed_sources(TASKS[iid].patch)))
        files = select_tests(iid, sources)
        print(f'[{k:2}/{len(by_task)}] {iid}: changed {sources} -> tests {files}', flush=True)
        if not files:
            fh.write(json.dumps({'instance_id': iid, 'kind': 'no_tests', 'sources': sources}) + '\n')
            continue
        seen = {}
        jobs = [('baseline', '', None), ('reference', TASKS[iid].patch, None)] + [('candidate', c['patch'], c) for c in cs]
        for kind, patch, c in jobs:
            key = re.sub(r'^index .*$', '', patch, flags=re.M).strip()
            if key in seen and kind == 'candidate':
                row = dict(seen[key]); row['dedup'] = True
            elif not patch.strip() and kind == 'candidate':
                row = {'ok': False, 'exit': None, 'passed': 0, 'failed': 0, 'errors': 0, 'error': 'empty patch', 'tail': '', 'seconds': 0}
            else:
                row = await run_one(iid, files, patch)
                seen[key] = row
            row.update(instance_id=iid, kind=kind, tests=files, src=c['src'] if c else kind,
                       resolved=c['resolved'] if c else None)
            fh.write(json.dumps(row) + '\n'); fh.flush()
            print(f"    {kind:9} {row['src'][-28:]:28} hidden={row['resolved']!s:5} existing ok={row['ok']!s:5} "
                  f"pass {row['passed']} fail {row['failed']} err {row['errors']} ({row['seconds']}s){' dedup' if row.get('dedup') else ''} "
                  f"{row['error'][:80]}", flush=True)


with concurrent.futures.ThreadPoolExecutor(max_workers=1) as _pool:
    _pool.submit(lambda: asyncio.run(main())).result()
print('==> done:', OUT / 'rows.jsonl')
