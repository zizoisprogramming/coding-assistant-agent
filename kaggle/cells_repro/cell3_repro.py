# 3. REPRO SIGNAL (scripts/train/make_repro_cells.py): per d40 task, every script the agents wrote for it, run
#    against no patch / the reference patch / each distinct candidate patch. One line per run.
import dataclasses, logging, warnings
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

_s = glob.glob('/kaggle/input/**/scripts.jsonl', recursive=True)
assert len(_s) == 1, f'the private dataset needs scripts.jsonl (new version of ziad23samer/testsignal-candidates); found {_s}'
SCRIPTS = {}
for l in open(_s[0]):
    r = json.loads(l)
    SCRIPTS.setdefault(r['instance_id'], []).append(r['code'])
print(f'{sum(len(v) for v in SCRIPTS.values())} scripts for {len(SCRIPTS)} tasks')
SUB = WORKING_DIR / 'submission'
for rel, text in {'agent.yaml': 'name: swe_agent\nmodel: gemma-4-31b-it-qat-w4a16-ct\ninstruction: !include prompts/system.md\ntools:\n  - run_command\n  - read_file\n  - edit_file\n  - write_file\n  - get_status\n  - submit_patch\ngenerate_content_config: !include configs/sampling.yaml\n', 'configs/sampling.yaml': '# Arm mix (rung-3e): bf prompt + r4 decision rule/example/edit fallback; bf tools. Thinking set from rung-3d\n# (placeholder 2048 / max_output 4096, as r4_mid).\ntemperature: 1.0  # generation (user 2026-10-21): varied runs; the submission uses 0.2\ntop_p: 0.95\nmax_output_tokens: 4096\nthinking_config:\n  thinking_budget: 2048\n  include_thoughts: true\n', 'eval_config.yaml': 'evaluation:\n  timeout_seconds: 240\n  max_tool_calls: 28\n  max_time_minutes: 15\n  max_turns: 80\n', 'prompts/system.md': 'You are an expert autonomous software engineer assigned to resolve one issue in a repository, fast and minimally.\n\n## How you are scored, and the one decision rule (from r4)\nHidden tests run on your final diff, even if you run out of time; no edit scores zero. As soon as you can say which\nlines to change and how, your very next tool call is that edit, even if you are only fairly sure. Never re-read,\nsearch again or write a script first. Checking comes after the edit; if the check shows a problem, adjust the edit.\n\n## Step 0: Extract the contract (before any tool call)\nFrom the problem statement, list the exact function names, class names, error messages, exception types, HTTP status codes, CLI flags, and parameter names it mentions, copied character-for-character. Hidden tests exercise exactly these names and spellings. Ignore template boilerplate in the issue: HTML comments, checklists, AI disclaimers.\n\n## Step 1: Locate (calls 1-6)\nThe first user message already contains the workspace layout, so never spend a call on ls or find to orient.\n- Search the most specific identifier or error string: git grep -n "text" -- \'*.py\' | head -20\n- read_file with start and end line, at most 120 lines per read, one follow-up read at most. Never read whole files.\n- Older tool outputs are dropped from your context, so after each important finding write one short line: file, line, what it means, next step.\n\n## Step 2: Edit (the decision rule above)\n- Apply the minimal fix directly to source files. Match the existing style of the file.\n- edit_file mechanics: copy the real characters from read_file output, never JSON-escape backslashes. Keep old_string short and unique: never include docstrings, triple-quoted strings, or blank-line runs. Several small edits beat one large edit. If a call fails validation, never resend the identical call: re-read the exact lines and rebuild from a fresh short anchor, or edit with run_command: python3 - << \'EOF\' (open the file, assert the old text occurs once, replace it, write it back) EOF.\n- Feature request: copy the closest existing sibling feature end to end, including imports, __all__ exports, dispatch or option tables, and type hints.\n- Fix the behaviour where it is produced, not where it is observed.\n- For documentation-code tasks (e.g. FastAPI), edit executable code under docs_src/.\n\n## Step 3: One check, one repair, then submit\n- Run ONLY the targeted test for the file you changed: python3 -m pytest tests/test_target.py -x -q -k name -p no:anyio -o timeout=0 > /tmp/t1.log 2>&1; tail -n 25 /tmp/t1.log\n- If it fails, make one repair, then submit. A local green test is not the grader: submit even if the check is red or skipped. The working tree is graded as it is, so an edit made in time counts even if you never run a test.\n- NEVER run bare pytest, pytest ., or full-repo suites. NEVER repair pre-existing failures, missing fixtures, or import errors unrelated to your change. NEVER create test stubs.\n- To locate a test file: find tests -name "*name*.py"\n\n## Step 4: Patch hygiene, then finish\n- Scratch scripts go in /tmp only. Files left anywhere else in the repository become part of your patch and fail grading.\n- Before submit_patch: run git status --short and git diff --stat. If a test-looking path appears in the diff (tests/, conftest.py, pytest.ini, pyproject.toml, setup.cfg, tox.ini), restore it: git checkout -- path\n- submit_patch and get_status are free: they never count against the budget. submit_patch can be re-issued after further edits; the last one wins. After your first submission, verify patch_size > 0.\n- If get_status shows under 90 seconds remaining, call submit_patch immediately.\n- Do not end a turn with plain prose: keep calling tools or call submit_patch. Finish as soon as the edit is in so later tasks keep their time.\n\n## Example (an invented package)\nTask: "Client should reject a negative timeout." git grep finds pkg/client.py line 88, self.timeout = timeout, and\ntwo lines below ValueError("retries must be >= 0") for retries. Found it: the very next call is the edit that adds\nthe same kind of check, raising ValueError("timeout must be >= 0"). Then the client tests, then submit: 8 calls.\n\n## Never\n- Never modify, create, or delete test files or test configuration: anything under tests/, conftest.py, pytest.ini, pyproject.toml, setup.cfg, tox.ini. The grader resets them and applying your patch fails if they differ.\n- Never search outside /workspace for sources or packages. All dependencies are pre-installed; a ModuleNotFoundError means fix the code under /workspace.\n- Never refactor or reformat unrelated code.\n- Never conclude without a non-empty patch: submit whatever partial edit exists.'}.items():
    (SUB / rel).parent.mkdir(parents=True, exist_ok=True)
    (SUB / rel).write_text(text)
OUT = WORKING_DIR / 'results' / 'repro'
OUT.mkdir(parents=True, exist_ok=True)
limits, gen_constraints = build_submission_limits()
config = EvalConfig(
    tasks_path=DATA_DIR / 'tasks.jsonl', snapshots_dir=DATA_DIR / 'snapshots', results_dir=OUT / 'eval',
    submission_dir=SUB, models=ModelRegistry(), sandbox='subprocess', wheels_dir=DATA_DIR / 'wheels',
    graph_dir=str(DATA_DIR / 'graphs'), embeddings_dir=str(DATA_DIR / 'embeddings'), task_ids=sorted(SCRIPTS),
    limits=limits, generation_constraints=gen_constraints,
    context_cache_config=ContextCacheConfig(min_tokens=2048, ttl_seconds=1800, cache_intervals=10),
    events_compaction_config=EventsCompactionConfig(compaction_interval=5, overlap_size=2, token_threshold=14336,
                                                    event_retention_size=5),
    display_mode='quiet', timeout_seconds=1200, max_tool_calls=28, max_time_minutes=15.0, max_turns=80)
TASKS = {t.instance_id: t for t in load_tasks(DATA_DIR / 'tasks.jsonl')}
SCRIPT_TIMEOUT = 20

PROBE = """import json, os, subprocess, sys, tempfile
SCRIPTS = %r
OUT = %r


def test_zz_probe():
    ws = os.getcwd()
    env = {k: v for k, v in os.environ.items() if k != 'PYTHONSAFEPATH'}  # the agents ran scripts from the repo
    env['PYTHONPATH'] = ws + os.pathsep + env.get('PYTHONPATH', '')
    res = []
    for i, code in enumerate(SCRIPTS):
        path = os.path.join(tempfile.gettempdir(), 'zz_probe_%%d_%%d.py' %% (os.getpid(), i))
        with open(path, 'w') as f:
            f.write(code.replace('/workspace', ws))
        try:
            r = subprocess.run([sys.executable, path], cwd=ws, capture_output=True, text=True, timeout=%d,
                               stdin=subprocess.DEVNULL, env=env)
            res.append({'i': i, 'exit': r.returncode, 'out': r.stdout[-400:], 'err': r.stderr[-400:]})
        except subprocess.TimeoutExpired:
            res.append({'i': i, 'exit': 'timeout', 'out': '', 'err': ''})
        except Exception as e:
            res.append({'i': i, 'exit': 'error', 'out': '', 'err': repr(e)[:300]})
    with open(OUT, 'w') as f:
        json.dump(res, f)
"""


def probe_patch(iid, variant):
    body = PROBE % (SCRIPTS[iid], str(OUT / f'{iid}__{variant}.json'), SCRIPT_TIMEOUT)
    lines = body.split('\n')
    return ('diff --git a/tests/test_zz_probe.py b/tests/test_zz_probe.py\nnew file mode 100644\n--- /dev/null\n'
            '+++ b/tests/test_zz_probe.py\n' + f'@@ -0,0 +1,{len(lines)} @@\n' + '\n'.join('+' + l for l in lines) + '\n')


async def run_variant(iid, variant, patch):
    task = dataclasses.replace(TASKS[iid], test_patch=probe_patch(iid, variant))
    snap, base_snap, patch_path = resolve_task_snapshot_paths(config.snapshots_dir, iid, task.repo)
    out = OUT / f'{iid}__{variant}.json'
    out.unlink(missing_ok=True)
    t0 = time.perf_counter()
    try:
        res = await verify_task(EVAL.docker, config, task, snap, agent_patch=patch, base_snapshot_path=base_snap,
                                patch_path=patch_path, start_time=t0)
        err = (res.error or '')[:160]
    except Exception as ex:
        err = f'{type(ex).__name__}: {str(ex)[:160]}'
    for d in glob.glob('/tmp/swegemma_sandbox_*'):
        shutil.rmtree(d, ignore_errors=True)
    got = json.loads(out.read_text()) if out.exists() else None
    return got, err, round(time.perf_counter() - t0)


async def main():
    global EVAL
    EVAL = Evaluator(config)
    by_task = collections.defaultdict(list)
    for c in CANDS:
        by_task[c['instance_id']].append(c)
    fh = open(OUT / 'rows.jsonl', 'w')
    tasks = [t for t in sorted(by_task) if SCRIPTS.get(t)]
    for k, iid in enumerate(tasks, 1):
        print(f'[{k:2}/{len(tasks)}] {iid}: {len(SCRIPTS[iid])} scripts', flush=True)
        variants, seen = [('baseline', '', None), ('reference', TASKS[iid].patch, None)], {}
        for n, c in enumerate(by_task[iid]):
            key = re.sub(r'^index .*$', '', c['patch'], flags=re.M).strip()
            if key:
                variants.append((f'cand{n}', c['patch'], c))
        for name, patch, c in variants:
            key = re.sub(r'^index .*$', '', patch, flags=re.M).strip()
            if c is not None and key in seen:
                got, err, s = seen[key]
                dup = True
            else:
                got, err, s = await run_variant(iid, name, patch)
                seen[key] = (got, err, s)
                dup = False
            row = {'instance_id': iid, 'variant': name, 'src': c['src'] if c else name, 'resolved': c['resolved'] if c else None,
                   'exits': [g['exit'] for g in got] if got else None, 'results': got, 'error': err, 'seconds': s, 'dup': dup}
            fh.write(json.dumps(row) + '\n'); fh.flush()
            ex = row['exits']
            print(f"    {name:9} {row['src'][-26:]:26} hidden={row['resolved']!s:5} exit0 {sum(1 for e in ex if e == 0) if ex else '-'}/"
                  f"{len(ex) if ex else '-'} ({s}s){' dup' if dup else ''} {'' if ex else err[:90]}", flush=True)


with concurrent.futures.ThreadPoolExecutor(max_workers=1) as _pool:
    _pool.submit(lambda: asyncio.run(main())).result()
print('==> done:', OUT / 'rows.jsonl')
