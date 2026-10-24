# 3. RE-GRADE: the reference patch of 3 tasks first (control: must PASS), then every public task's saved patch with
#    verify_task. One line per task with the test tail. Writes results/regrade/.
import logging, warnings
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

SUB = WORKING_DIR / 'submission'
for rel, text in {'agent.yaml': 'name: swe_agent\nmodel: gemma-4-31b-it-qat-w4a16-ct\ninstruction: !include prompts/system.md\ntools:\n  - run_command\n  - read_file\n  - edit_file\n  - write_file\n  - get_status\n  - submit_patch\ngenerate_content_config: !include configs/sampling.yaml\n', 'configs/sampling.yaml': '# Arm mix (rung-3e): bf prompt + r4 decision rule/example/edit fallback; bf tools. Thinking set from rung-3d\n# (placeholder 2048 / max_output 4096, as r4_mid).\ntemperature: 1.0  # generation (user 2026-10-21): varied runs; the submission uses 0.2\ntop_p: 0.95\nmax_output_tokens: 4096\nthinking_config:\n  thinking_budget: 2048\n  include_thoughts: true\n', 'eval_config.yaml': 'evaluation:\n  timeout_seconds: 240\n  max_tool_calls: 28\n  max_time_minutes: 15\n  max_turns: 80\n', 'prompts/system.md': 'You are an expert autonomous software engineer assigned to resolve one issue in a repository, fast and minimally.\n\n## How you are scored, and the one decision rule (from r4)\nHidden tests run on your final diff, even if you run out of time; no edit scores zero. As soon as you can say which\nlines to change and how, your very next tool call is that edit, even if you are only fairly sure. Never re-read,\nsearch again or write a script first. Checking comes after the edit; if the check shows a problem, adjust the edit.\n\n## Step 0: Extract the contract (before any tool call)\nFrom the problem statement, list the exact function names, class names, error messages, exception types, HTTP status codes, CLI flags, and parameter names it mentions, copied character-for-character. Hidden tests exercise exactly these names and spellings. Ignore template boilerplate in the issue: HTML comments, checklists, AI disclaimers.\n\n## Step 1: Locate (calls 1-6)\nThe first user message already contains the workspace layout, so never spend a call on ls or find to orient.\n- Search the most specific identifier or error string: git grep -n "text" -- \'*.py\' | head -20\n- read_file with start and end line, at most 120 lines per read, one follow-up read at most. Never read whole files.\n- Older tool outputs are dropped from your context, so after each important finding write one short line: file, line, what it means, next step.\n\n## Step 2: Edit (the decision rule above)\n- Apply the minimal fix directly to source files. Match the existing style of the file.\n- edit_file mechanics: copy the real characters from read_file output, never JSON-escape backslashes. Keep old_string short and unique: never include docstrings, triple-quoted strings, or blank-line runs. Several small edits beat one large edit. If a call fails validation, never resend the identical call: re-read the exact lines and rebuild from a fresh short anchor, or edit with run_command: python3 - << \'EOF\' (open the file, assert the old text occurs once, replace it, write it back) EOF.\n- Feature request: copy the closest existing sibling feature end to end, including imports, __all__ exports, dispatch or option tables, and type hints.\n- Fix the behaviour where it is produced, not where it is observed.\n- For documentation-code tasks (e.g. FastAPI), edit executable code under docs_src/.\n\n## Step 3: One check, one repair, then submit\n- Run ONLY the targeted test for the file you changed: python3 -m pytest tests/test_target.py -x -q -k name -p no:anyio -o timeout=0 > /tmp/t1.log 2>&1; tail -n 25 /tmp/t1.log\n- If it fails, make one repair, then submit. A local green test is not the grader: submit even if the check is red or skipped. The working tree is graded as it is, so an edit made in time counts even if you never run a test.\n- NEVER run bare pytest, pytest ., or full-repo suites. NEVER repair pre-existing failures, missing fixtures, or import errors unrelated to your change. NEVER create test stubs.\n- To locate a test file: find tests -name "*name*.py"\n\n## Step 4: Patch hygiene, then finish\n- Scratch scripts go in /tmp only. Files left anywhere else in the repository become part of your patch and fail grading.\n- Before submit_patch: run git status --short and git diff --stat. If a test-looking path appears in the diff (tests/, conftest.py, pytest.ini, pyproject.toml, setup.cfg, tox.ini), restore it: git checkout -- path\n- submit_patch and get_status are free: they never count against the budget. submit_patch can be re-issued after further edits; the last one wins. After your first submission, verify patch_size > 0.\n- If get_status shows under 90 seconds remaining, call submit_patch immediately.\n- Do not end a turn with plain prose: keep calling tools or call submit_patch. Finish as soon as the edit is in so later tasks keep their time.\n\n## Example (an invented package)\nTask: "Client should reject a negative timeout." git grep finds pkg/client.py line 88, self.timeout = timeout, and\ntwo lines below ValueError("retries must be >= 0") for retries. Found it: the very next call is the edit that adds\nthe same kind of check, raising ValueError("timeout must be >= 0"). Then the client tests, then submit: 8 calls.\n\n## Never\n- Never modify, create, or delete test files or test configuration: anything under tests/, conftest.py, pytest.ini, pyproject.toml, setup.cfg, tox.ini. The grader resets them and applying your patch fails if they differ.\n- Never search outside /workspace for sources or packages. All dependencies are pre-installed; a ModuleNotFoundError means fix the code under /workspace.\n- Never refactor or reformat unrelated code.\n- Never conclude without a non-empty patch: submit whatever partial edit exists.'}.items():
    (SUB / rel).parent.mkdir(parents=True, exist_ok=True)
    (SUB / rel).write_text(text)
OUT = WORKING_DIR / 'results' / 'regrade'
OUT.mkdir(parents=True, exist_ok=True)
limits, gen_constraints = build_submission_limits()
config = EvalConfig(
    tasks_path=DATA_DIR / 'tasks.jsonl', snapshots_dir=DATA_DIR / 'snapshots', results_dir=OUT / 'eval',
    submission_dir=SUB, models=ModelRegistry(), sandbox='subprocess', wheels_dir=DATA_DIR / 'wheels',
    graph_dir=str(DATA_DIR / 'graphs'), embeddings_dir=str(DATA_DIR / 'embeddings'), task_ids=sorted(PUBLIC),
    limits=limits, generation_constraints=gen_constraints,
    context_cache_config=ContextCacheConfig(min_tokens=2048, ttl_seconds=1800, cache_intervals=10),
    events_compaction_config=EventsCompactionConfig(compaction_interval=5, overlap_size=2, token_threshold=14336,
                                                    event_retention_size=5),
    display_mode='quiet', timeout_seconds=600, max_tool_calls=28, max_time_minutes=15.0, max_turns=80)
TASKS = {t.instance_id: t for t in load_tasks(DATA_DIR / 'tasks.jsonl')}
GRADED = {}


async def grade(iid, patch):
    task = TASKS[iid]
    snap, base_snap, patch_path = resolve_task_snapshot_paths(config.snapshots_dir, iid, task.repo)
    t0 = time.perf_counter()
    try:
        res = await verify_task(EVAL.docker, config, task, snap, agent_patch=patch, base_snapshot_path=base_snap,
                                patch_path=patch_path, start_time=t0)
        ok, tail = bool(res.resolved), (res.error or '') + ' | ' + ' / '.join((res.test_output or '').strip().splitlines()[-3:])
    except Exception as e:
        ok, tail = False, f'ERROR {type(e).__name__}: {str(e)[:200]}'
    for p in glob.glob('/tmp/swegemma_sandbox_*'):
        shutil.rmtree(p, ignore_errors=True)
    return ok, round(time.perf_counter() - t0), tail[-400:]


async def main():
    global EVAL
    EVAL = Evaluator(config)
    controls = sorted(PUBLIC)[:3]
    for iid in controls:
        ok, s, tail = await grade(iid, TASKS[iid].patch)
        print(f'[control] {iid:16} reference patch -> {"PASS" if ok else "FAIL"} ({s}s) | {tail[-200:]}', flush=True)
    n_ok = 0
    for k, iid in enumerate(sorted(PUBLIC), 1):
        patch = PATCHES.get(iid, '')
        if not patch.strip():
            GRADED[iid] = {'resolved': False, 'why': 'empty patch'}
            print(f'[{k:2}/{len(PUBLIC)}] {iid:16} empty patch', flush=True)
            continue
        ok, s, tail = await grade(iid, patch)
        n_ok += ok
        GRADED[iid] = {'resolved': ok, 'seconds': s, 'tail': tail}
        print(f'[{k:2}/{len(PUBLIC)}] {iid:16} resolved={ok!s:5} ({s}s) | solved {n_ok} | {tail[-160:]}', flush=True)
        (OUT / 'regrade.json').write_text(json.dumps(GRADED, indent=1))


with concurrent.futures.ThreadPoolExecutor(max_workers=1) as _pool:
    _pool.submit(lambda: asyncio.run(main())).result()
with open(OUT / 'gen_per_task.jsonl', 'w') as fh:  # the generation rows, public 'resolved' replaced
    for r in ROWS_IN:
        if r['instance_id'] in GRADED:
            r = {**r, 'resolved': GRADED[r['instance_id']]['resolved'], 'regraded': True}
        fh.write(json.dumps(r) + '\n')
print(f"==> public re-graded: {sum(g['resolved'] for g in GRADED.values())}/{len(GRADED)} solved; wrote", OUT / 'gen_per_task.jsonl')
