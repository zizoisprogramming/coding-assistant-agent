# 2. GENERATION setup (scripts/train/make_gen_cells.py): mode, the task set, the agent, the verified sandbox
#    environment, and resume from earlier sessions. GPU L4x4, INTERNET OFF.
import collections, json, random, re, tarfile, time
from collections import Counter

assert sys.version_info[:2] == (3, 12), (f'Python {sys.version.split()[0]}: generation needs Python 3.12 + torch 2.10 '
    '(vLLM 0.19.1): Copy & Edit an old GPU notebook and set Environment -> Pin to original environment')
MODE = 'skill_arms'  # skill arms on a dev16 task set (make_skill_arms_cells.py)
SAMPLE = []  # MODE 'prompt': the fixed task sample of the prompt experiment
TRIAL_PHASES = [(4, 8), (6, 12)]  # trial: (concurrency, tasks): measured throughput decides CONCURRENCY below
CONCURRENCY = 2  # tasks at once (make_skill_arms_cells.py CONCURRENCY; the LB runs 1)
STOP_NEW_TASKS_AFTER_H = 10.5  # = min(10.5, this account's GPU quota in hours / 2 - 0.4): L4x4 bills 2x,
# a run ends within 8 min, Kaggle ends sessions at 12 h; a killed run loses its output
T_START = time.time()
WORKING_DIR = Path('/kaggle/working')
SUB_DIR = WORKING_DIR / 'submission'
RESULTS = WORKING_DIR / 'results'
PER_TASK = RESULTS / 'gen_per_task.jsonl'
WHEEL_SET = f'{__import__("platform").machine()}-cp{sys.version_info.major}{sys.version_info.minor}'
SUBMISSION = {'agent.yaml': 'name: swe_agent\nmodel: gemma-4-31b-it-qat-w4a16-ct\ninstruction: !include prompts/system.md\ntools:\n  - run_command\n  - read_file\n  - edit_file\n  - write_file\n  - get_status\n  - submit_patch\ngenerate_content_config: !include configs/sampling.yaml\n', 'configs/sampling.yaml': '# Arm mix (rung-3e): bf prompt + r4 decision rule/example/edit fallback; bf tools. Thinking set from rung-3d\n# (placeholder 2048 / max_output 4096, as r4_mid).\ntemperature: 1.0  # generation (user 2026-10-21): varied runs; the submission uses 0.2\ntop_p: 0.95\nmax_output_tokens: 4096\nthinking_config:\n  thinking_budget: 2048\n  include_thoughts: true\n', 'eval_config.yaml': 'evaluation:\n  timeout_seconds: 240\n  max_tool_calls: 28\n  max_time_minutes: 15\n  max_turns: 80\n', 'prompts/system.md': 'You are an expert autonomous software engineer assigned to resolve one issue in a repository, fast and minimally.\n\n## How you are scored, and the one decision rule (from r4)\nHidden tests run on your final diff, even if you run out of time; no edit scores zero. As soon as you can say which\nlines to change and how, your very next tool call is that edit, even if you are only fairly sure. Never re-read,\nsearch again or write a script first. Checking comes after the edit; if the check shows a problem, adjust the edit.\n\n## Step 0: Extract the contract (before any tool call)\nFrom the problem statement, list the exact function names, class names, error messages, exception types, HTTP status codes, CLI flags, and parameter names it mentions, copied character-for-character. Hidden tests exercise exactly these names and spellings. Ignore template boilerplate in the issue: HTML comments, checklists, AI disclaimers.\n\n## Step 1: Locate (calls 1-6)\nThe first user message already contains the workspace layout, so never spend a call on ls or find to orient.\n- Search the most specific identifier or error string: git grep -n "text" -- \'*.py\' | head -20\n- read_file with start and end line, at most 120 lines per read, one follow-up read at most. Never read whole files.\n- Older tool outputs are dropped from your context, so after each important finding write one short line: file, line, what it means, next step.\n\n## Step 2: Edit (the decision rule above)\n- Apply the minimal fix directly to source files. Match the existing style of the file.\n- edit_file mechanics: copy the real characters from read_file output, never JSON-escape backslashes. Keep old_string short and unique: never include docstrings, triple-quoted strings, or blank-line runs. Several small edits beat one large edit. If a call fails validation, never resend the identical call: re-read the exact lines and rebuild from a fresh short anchor, or edit with run_command: python3 - << \'EOF\' (open the file, assert the old text occurs once, replace it, write it back) EOF.\n- Feature request: copy the closest existing sibling feature end to end, including imports, __all__ exports, dispatch or option tables, and type hints.\n- Fix the behaviour where it is produced, not where it is observed.\n- For documentation-code tasks (e.g. FastAPI), edit executable code under docs_src/.\n\n## Step 3: One check, one repair, then submit\n- Run ONLY the targeted test for the file you changed: python3 -m pytest tests/test_target.py -x -q -k name -p no:anyio -o timeout=0 > /tmp/t1.log 2>&1; tail -n 25 /tmp/t1.log\n- If it fails, make one repair, then submit. A local green test is not the grader: submit even if the check is red or skipped. The working tree is graded as it is, so an edit made in time counts even if you never run a test.\n- NEVER run bare pytest, pytest ., or full-repo suites. NEVER repair pre-existing failures, missing fixtures, or import errors unrelated to your change. NEVER create test stubs.\n- To locate a test file: find tests -name "*name*.py"\n\n## Step 4: Patch hygiene, then finish\n- Scratch scripts go in /tmp only. Files left anywhere else in the repository become part of your patch and fail grading.\n- Before submit_patch: run git status --short and git diff --stat. If a test-looking path appears in the diff (tests/, conftest.py, pytest.ini, pyproject.toml, setup.cfg, tox.ini), restore it: git checkout -- path\n- submit_patch and get_status are free: they never count against the budget. submit_patch can be re-issued after further edits; the last one wins. After your first submission, verify patch_size > 0.\n- If get_status shows under 90 seconds remaining, call submit_patch immediately.\n- Do not end a turn with plain prose: keep calling tools or call submit_patch. Finish as soon as the edit is in so later tasks keep their time.\n\n## Example (an invented package)\nTask: "Client should reject a negative timeout." git grep finds pkg/client.py line 88, self.timeout = timeout, and\ntwo lines below ValueError("retries must be >= 0") for retries. Found it: the very next call is the edit that adds\nthe same kind of check, raising ValueError("timeout must be >= 0"). Then the client tests, then submit: 8 calls.\n\n## Never\n- Never modify, create, or delete test files or test configuration: anything under tests/, conftest.py, pytest.ini, pyproject.toml, setup.cfg, tox.ini. The grader resets them and applying your patch fails if they differ.\n- Never search outside /workspace for sources or packages. All dependencies are pre-installed; a ModuleNotFoundError means fix the code under /workspace.\n- Never refactor or reformat unrelated code.\n- Never conclude without a non-empty patch: submit whatever partial edit exists.'}


def _first(*cands, pattern=None):
    for c in cands:
        if Path(c).exists():
            return Path(c)
    hits = sorted(glob.glob(pattern, recursive=True)) if pattern else []
    assert hits, f'none of {cands} exists: attach it as a notebook input'
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
assert len(_sets) == 1, f'attach exactly one final task set (verification output); found {_sets}'
OUT = _sets[0]
print('competition:', DATA_DIR, '| OOD-45 tools:', OOD_DIR, '| task set:', OUT)

ROWS = {}
for l in open(OUT / 'tasks.jsonl'):
    r = json.loads(l)
    ROWS[r['instance_id']] = r
assert (OUT / 'wheels' / WHEEL_SET / 'manifest.json').exists(), f'the task set has no wheel set {WHEEL_SET}'
print(f"{len(ROWS)} tasks from {len({r['repo'] for r in ROWS.values()})} repos | domains",
      dict(Counter(r['domain'] for r in ROWS.values())), '| text', dict(Counter(r['text_kind'] for r in ROWS.values())))

shutil.rmtree(SUB_DIR, ignore_errors=True)
for rel, text in SUBMISSION.items():
    (SUB_DIR / rel).parent.mkdir(parents=True, exist_ok=True)
    (SUB_DIR / rel).write_text(text, encoding='utf-8')
print('agent: submissions/mix with', [l for l in SUBMISSION['configs/sampling.yaml'].splitlines() if l.startswith('temperature')])

# Resume: every earlier session's rows (attached outputs) + this session's own (a re-run of this notebook).
RESULTS.mkdir(parents=True, exist_ok=True)
PREV = []
for p in ([str(PER_TASK)] if PER_TASK.exists() else []):
    PREV += [json.loads(l) for l in open(p)]
# Trial rows embedded (2026-10-21): attaching the trial notebook's output from another account hung on 'Preparing to
# download'. Its request log stays in that output; these rows only make this session skip what the trial did.
EMBEDDED_PREV = []
PREV += [r for r in EMBEDDED_PREV if (r['instance_id'], r['attempt']) not in {(x['instance_id'], x['attempt']) for x in PREV}]
DONE_JOBS = {(r['instance_id'], r['attempt']) for r in PREV if r['end'] != 'runner'}
SOLVED = {r['instance_id'] for r in PREV if r['resolved']}
print(f'earlier runs: {len(PREV)} ({len(DONE_JOBS)} done jobs, {len(SOLVED)} tasks solved) | mode {MODE}')

# The verified sandbox environment (as kaggle/cells_rebench_verify): ood45_harness's install step, host pytest plugin
# wheels shipped with the task set, host-only plugins hidden, network fails fast inside the sandbox.
sys.path.insert(0, str(OOD_DIR / 'tools'))
import ood45_harness as ood  # noqa: E402
print('swegemma', ood.check_swegemma())
ood._STATE['house'] = OOD_DIR / 'wheels' / 'house'
ood.ENV_LOG['path'] = str(RESULTS / 'gen_env_install.jsonl')
from swegemma.harness import container_setup as _cs0
_HARNESS_INSTALL, _HARNESS_COMPAT = _cs0.install_test_dependencies, _cs0._is_wheel_compatible_py313  # public tasks
# like the LB (Docker exec_run attaches no stdin): commands of the local subprocess sandbox get none either;
# it inherited the notebook's open, silent stdin, so input() (rich_3882's Prompt.ask) hung to the 240 s timeout
import adk_eval_core.sandbox.subprocess_sandbox as _ss0
class _NoStdinSubprocess:
    def __getattr__(self, name):
        return getattr(subprocess, name)
    def Popen(self, *a, **k):
        k.setdefault('stdin', subprocess.DEVNULL)
        return subprocess.Popen(*a, **k)
_ss0.subprocess = _NoStdinSubprocess()
ood.patch_harness()
WHEEL_ROOT = Path('/tmp/gen_wheels')
ood.materialize_wheels(OUT, WHEEL_SET, WHEEL_ROOT / WHEEL_SET)
_host = sorted(str(p) for p in (OUT / 'wheels' / 'host').glob('*.whl'))
_r = subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '--no-index', '--no-deps', *_host], capture_output=True, text=True)
print('host pytest plugins:', [Path(p).name for p in _host], '-> exit', _r.returncode, _r.stderr[-200:])

# SKILL ARMS (scripts/train/make_skill_arms_cells.py): a dev16 task set, pass 1 before pass 2.
ATTEMPTS = 2  # passes; after pass 1 an arm with EARLY_STOP_MAX or fewer solved is dropped (none left: the run ends)
EARLY_STOP_MAX = -1
PASS2_IF_BEATS = None  # (a, b): pass 2 runs only if a solved more than b in pass 1
ARMS = ['pub024']
ARM_FILES = {'pub024': {'agent.yaml': 'name: swe_agent\nmodel: gemma-4-31b-it-qat-w4a16-ct\ninstruction: !include prompts/system.md\ntools:\n  - run_command\n  - read_file\n  - edit_file\n  - write_file\n  - get_status\n  - submit_patch\n  - get_code_neighbors\n  - search_similar_code\n  - get_code_subgraph\ngenerate_content_config: !include configs/sampling.yaml\n', 'configs/sampling.yaml': 'temperature: 0.2\ntop_p: 0.95\nmax_output_tokens: 8192\nthinking_config:\n  thinking_budget: 4096\n  include_thoughts: true\n', 'eval_config.yaml': 'evaluation:\n  timeout_seconds: 240\n  max_tool_calls: 28\n  max_time_minutes: 8\n  max_turns: 80\n', 'prompts/system.md': 'You are an autonomous software engineer. Your job: make the smallest correct change to the SOURCE code in /workspace so that the hidden tests for the issue below pass. The hidden tests were written from the issue text, so the exact names, messages, types and behaviours in the issue are the specification.\n\n# HARD LIMITS\n- 28 tool calls and 8 minutes in total. When either runs out, the working tree is graded as it is. An edit that exists counts, even if you never call `submit_patch`. An unedited tree always scores zero.\n- Never create, modify or delete test files (`test_*.py`, `*_test.py`, anything under `tests/`, `pytest.ini`, `conftest.py`). This is an automatic failure.\n- Scratch files go in /tmp only. Any file left under /workspace becomes part of the graded patch.\n- Never run a full test suite (bare `pytest`, `pytest .`, `unittest discover`). Always name one test file, and add `-k` when you can.\n- Never look outside /workspace. All dependencies are already installed.\n- Never use `search_similar_code`, `get_code_neighbors` or `get_code_subgraph`. They return nothing useful.\n\n# CALL PLAN\n- Calls 1-8: locate and read. Calls 9-12: edit. You MUST have edited a source file by call 12. If you are unsure, make your best-guess edit in the most likely place now. A wrong edit can still be corrected. Pure reading cannot score.\n- Calls 13-20: verify and correct.\n- Call 20 onward: no new exploration. Check, fix, submit.\n- Always finish with `git status --short && git diff` followed by `submit_patch`.\n\n# PROCEDURE\n\n## 1. Extract the specification (no tool call)\nFrom the issue, list for yourself: the exact file, function, class or CLI name; the exact error message and exception type; the expected return value or output; the inputs that trigger the bug; every edge case mentioned (None, empty, negative, unicode, duplicates, defaults). Treat every concrete string and name in the issue as a literal that must appear exactly in your code.\n\n## 2. Locate\n- Use exact paths from the issue directly. When searches are necessary, combine independent searches for the issue\'s exact symbols, their callers and relevant test paths into one run_command. Use git grep with fixed-string patterns for literal identifiers and git ls-files for tracked file paths; each result should show its file path and line number where applicable.\n- Batch only searches whose inputs are already known. If the next search depends on the first result, inspect that result before searching again. Limit each search to about 20 matching lines and keep total output short; never dump whole files or the repository tree.\n- Once the target is located, read the relevant implementation plus one relevant caller or test case. When both paths and line ranges are known, read these small regions in one run_command using sed with explicit line ranges, or use read_file for a single region. Aim for about 40 lines per region and at most three regions per command. Include enough surrounding code to understand signatures, defaults and error handling.\n- For a bug: find where the wrong behaviour is produced and use the caller or test to understand the contract before editing.\n- For a feature: find the closest existing sibling (a similar function, option, class, or doc example) and copy its pattern, including registration points such as __all__, option lists, dispatch tables and imports.\n- Reuse paths and test names already discovered. Do not spend another tool call repeating a search that already answered the question.\n- If the issue includes a code snippet that reproduces the problem, you may run it once with python -c (one call, never create a file) to see the real error.\n\n## 3. Edit\n- Use edit_file for changes to existing code. Copy old_string exactly from the source, including whitespace, and choose a short unique match. Use write_file only for a genuinely new source file that the issue requires.\n- If edit_file reports no match or multiple matches, read the exact source region and retry with a smaller unique snippet. Never repeat an identical failed edit. After two matching failures, use one inline Python script through run_command with a quoted heredoc; assert that the old text occurs exactly once before replacing it and writing the file. Preserve unrelated content and do not rewrite the file from memory.\n- Fix the cause, not the symptom. Do not special-case the example from the issue.\n- Change only what the issue requires. Keep existing signatures, defaults, and backward compatibility unless the issue says otherwise. Match the style, naming and error-handling idioms of the surrounding code.\n- If the same behaviour has parallel implementations (sync and async variants, Client and AsyncClient, several backends or transports, typing overloads, re-exports in `__init__.py` or `__all__`), apply the change to every one of them. Hidden tests often exercise more than one.\n- Use the exact exception class and exact message text from the issue. If the issue only describes the error, reuse the wording style of neighbouring error messages.\n- Handle every edge case you listed in step 1.\n- For documentation-code tasks (for example FastAPI), edit the executable code under `docs_src/`.\n\n## 4. Verify (at most 2 calls)\n- Find the test file with `find tests -name "*keyword*.py"`, then run `timeout 150 python -m pytest tests/path/test_x.py -x -q -k keyword`. Use `python3 -m unittest tests.test_x` for unittest projects.\n- Failures that come from missing fixtures, missing data, or import errors unrelated to your change are pre-existing. Ignore them. Never repair tests or the environment.\n- If a test related to your change fails, read the traceback, fix the source once, and rerun once. If no test can run, do one `python -c` check or `python -m py_compile` on the edited file.\n\n## 5. Final check and submit\n- Run `git status --short && git diff` in one call. `git diff` alone hides untracked files, but `submit_patch` includes them. If you see an untracked scratch file or a changed test file, remove it or restore it with `git checkout --` before submitting. Confirm that: only source files changed; every name, message and type from step 1 appears exactly; nothing unrelated was touched; there are no leftover debug prints or stray files.\n- Call `submit_patch`. Confirm `patch_size > 0` and `files_changed > 0`. If either is 0, you have not edited anything. Edit now and submit again.\n- End with a single-sentence summary of the fix.\n\n# DECISION RULES\n- Ambiguous issue: choose the most literal reading of the issue text and act on it. Do not ask questions and do not stall.\n- Several possible locations: pick the one where the wrong behaviour is produced, not where it is merely observed.\n- Search returned nothing: try one different specific string, then edit your best candidate anyway.\n- Stuck after a failed fix: make a different, smaller change. Do not repeat the same edit.\n- Never conclude that nothing needs to change. Every task requires a non-empty source patch.\n'}}
TASK_SET = ['fastapi_11194', 'fastapi_12942', 'fastapi_14349', 'fastapi_14419', 'fastapi_14873', 'fastapi_15589', 'rich_3278', 'rich_3506', 'rich_3521', 'rich_3676', 'rich_4075', 'rich_4079']
MIX_REF = {'fastapi_11194': [5, 0, 6], 'fastapi_12942': [1, 0, 1], 'fastapi_14349': [1, 0, 1], 'fastapi_14419': [2, 0, 6], 'fastapi_15589': [6, 0, 6], 'rich_3278': [0, 0, 1], 'rich_3506': [0, 1, 1], 'rich_3521': [0, 2, 2], 'rich_4079': [2, 3, 6]}  # mix (T0.2, 8 min, 2 at once) on these tasks: task -> [solved, no patch, runs]
GEN_REF = {'fastapi_12942': 1, 'fastapi_14349': 1, 'fastapi_14873': 0, 'rich_3278': 0, 'rich_3506': 0, 'rich_3676': 0, 'rich_4075': 0}  # val/test: mix at T1.0, 15 min, 1 run each (2026-10-24 generation run, re-graded): task -> solved
SPLIT_OF = {'fastapi_11194': 'dev16', 'fastapi_12942': 'val', 'fastapi_14349': 'val', 'fastapi_14419': 'dev16', 'fastapi_14873': 'test', 'fastapi_15589': 'dev16', 'rich_3278': 'val', 'rich_3506': 'val', 'rich_3521': 'dev16', 'rich_3676': 'test', 'rich_4075': 'test', 'rich_4079': 'dev16'}
ROWS = {}
for l in open(DATA_DIR / 'tasks.jsonl'):
    r = json.loads(l)
    if r['instance_id'] in TASK_SET:
        _sp = SPLIT_OF[r['instance_id']]
        ROWS[r['instance_id']] = {**r, 'src': 'public', 'level': _sp, 'domain': 'public', 'text_kind': 'public',
                                   'leak': False, 'unfair_names': [], 'env_partial': False, 'split': _sp}
assert len(ROWS) == len(TASK_SET), f'tasks missing from tasks.jsonl: {sorted(set(TASK_SET) - set(ROWS))}'
print(f"SKILL ARMS: {len(ROWS)} tasks {dict(Counter(SPLIT_OF[t] for t in ROWS))} {sorted(ROWS)} | arms {ARMS} | {ATTEMPTS} passes | {CONCURRENCY} at once | "
      f"after pass 1, arms solving {EARLY_STOP_MAX} or fewer stop")
SUB_ROOT = WORKING_DIR / 'submissions'
shutil.rmtree(SUB_ROOT, ignore_errors=True)
for arm, files in ARM_FILES.items():
    for rel, text in files.items():
        (SUB_ROOT / arm / rel).parent.mkdir(parents=True, exist_ok=True)
        (SUB_ROOT / arm / rel).write_text(text, encoding='utf-8')
    _ev = (SUB_ROOT / arm / 'eval_config.yaml').read_text()
    _cp = SUB_ROOT / arm / 'skills/agent/scripts/commands.txt'
    _cmds = _cp.read_text().split() if _cp.exists() else ['(no skill)']
    print(arm, '| tools', [l.split('#')[0].strip()[2:] for l in (SUB_ROOT / arm / 'agent.yaml').read_text().splitlines() if l.strip().startswith('- ')][:8],
          '| skill commands', _cmds, '| budgets', ' '.join(l.strip() for l in _ev.splitlines() if ':' in l and 'evaluation' not in l))
    assert 'max_time_minutes: 8' in _ev, 'arms run with the 8-minute limit (as mix\'s dev16 runs)'

import contextvars, tempfile, threading
# Host-only pytest plugins (Kaggle image, not the scoring image) are hidden in each sandbox venv (pilot 1: typeguard's
# plugin broke 16/40 tasks), unless the task ships that distribution itself.
import importlib.metadata as _md
KEEP_PLUGIN_DISTS = {'pytest', 'pytest-timeout', 'pytest-asyncio', 'pytest-xdist', 'pytest-httpbin', 'anyio'}
HOST_PLUGINS = sorted({(ep.value.split(':')[0], (ep.dist.name if ep.dist else '').lower().replace('_', '-'))
                       for ep in _md.entry_points(group='pytest11')})
print('host pytest plugins:', HOST_PLUGINS)


def shadow_host_plugins(site):
    shadowed = []
    for module, dist in HOST_PLUGINS:
        if dist in KEEP_PLUGIN_DISTS or list(site.glob(f"{dist.replace('-', '_')}-*.dist-info")):
            continue
        parts = module.split('.')
        if (site / parts[0]).exists() or (site / f'{parts[0]}.py').exists():
            continue
        if len(parts) == 1:
            (site / f'{parts[0]}.py').write_text('# hidden by the gate: host-only pytest plugin\n')
        else:
            pkg = site.joinpath(*parts[:-1])
            pkg.mkdir(parents=True, exist_ok=True)
            for k in range(1, len(parts)):
                site.joinpath(*parts[:k], '__init__.py').touch()
            (pkg / f'{parts[-1]}.py').write_text('# hidden by the gate: host-only pytest plugin\n')
        shadowed.append(module)
    return shadowed


ood._shadow_host_plugins = shadow_host_plugins
# Tag every install record with the task being gated (the sandbox threads inherit this context) -> env_partial.
CUR_TASK = contextvars.ContextVar('gate_task', default=None)
ENV_BY_TASK = collections.defaultdict(list)
_orig_log_env = ood._log_env


def _log_env(record):
    record['task'] = CUR_TASK.get()
    ENV_BY_TASK[record['task']].append(record)
    _orig_log_env(record)


ood._log_env = _log_env
# The harness caches one unpacked-wheel tar per wheel set (in /tmp; hundreds of MB each). Record which tars each
# running task uses so the cleanup after each task deletes only tars no running task needs (lock: no task can pick
# up a tar between the cleanup's check and its delete).
import threading
from swegemma.harness import container_setup as _cs
TAR_LOCK, TAR_USERS = threading.Lock(), collections.defaultdict(set)
_orig_tar = _cs._build_unpacked_wheels_tar


def _tar(selected, cache_name, marker):
    with TAR_LOCK:
        p = _orig_tar(selected, cache_name, marker)
        TAR_USERS[Path(p)].add(CUR_TASK.get())
        return p


_cs._build_unpacked_wheels_tar = _tar

# OFFLINE FAIL-FAST (verify run 1, 2026-10-21: with Kaggle's internet off, a connection to the outside HANGS until the
# TCP timeout instead of failing, so installs (setup.py develop -> easy_install) and network-touching tests took 7-14
# min per task; ETA 20 h). A .pth hook in each sandbox venv makes every non-local connect / DNS lookup fail at once
# with "Network is unreachable", as in an offline Docker sandbox (--network none). Loopback stays allowed (local test
# servers). Applies to every Python process that uses the sandbox venv; the harness itself is not affected.
OFFLINE_MODULE = """import errno, ipaddress, socket
_connect, _connect_ex, _getaddrinfo = socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo
_LOCAL_NAMES = {'localhost', 'localhost.localdomain', '', None, socket.gethostname()}


def _local_host(host):
    if isinstance(host, bytes):
        host = host.decode()
    if host in _LOCAL_NAMES:
        return True
    try:
        ip = ipaddress.ip_address(host.split('%')[0])
        return ip.is_loopback or ip.is_unspecified
    except ValueError:
        return False


def _blocked(sock, addr):
    return sock.family in (socket.AF_INET, socket.AF_INET6) and isinstance(addr, tuple) and not _local_host(addr[0])


def connect(self, addr):
    if _blocked(self, addr):
        raise OSError(errno.ENETUNREACH, 'Network is unreachable (offline sandbox)')
    return _connect(self, addr)


def connect_ex(self, addr):
    return errno.ENETUNREACH if _blocked(self, addr) else _connect_ex(self, addr)


def getaddrinfo(host, *args, **kwargs):
    if not _local_host(host):
        raise socket.gaierror(socket.EAI_NONAME, 'Name or service not known (offline sandbox)')
    return _getaddrinfo(host, *args, **kwargs)


socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo = connect, connect_ex, getaddrinfo
"""
_shadow_plugins = shadow_host_plugins


def shadow_host_plugins(site):
    (site / '_rb_offline.py').write_text(OFFLINE_MODULE)
    (site / 'zz_rb_offline.pth').write_text('import _rb_offline\n')
    return _shadow_plugins(site) + ['(offline fail-fast hook)']


ood._shadow_host_plugins = shadow_host_plugins


def import_name(r):
    """The package that holds the first patched source file (deepest directory with an __init__.py, src/ aware),
    read from the snapshot; single-file modules -> their name; fallback: the repo name."""
    tgz = OUT / 'snapshots' / f"{r['instance_id']}.tgz"
    names = set()
    if tgz.exists():
        with tarfile.open(tgz) as tf:
            names = {m.name[2:] if m.name.startswith('./') else m.name for m in tf if m.name.endswith('__init__.py')}
    skip = ('tests/', 'test/', 'testing/', 'docs/', 'doc/', 'examples/', 'example/', 'scripts/', 'tools/', 'benchmarks/')
    for f in re.findall(r'^diff --git a/(\S+)', r['patch'], re.M):
        if not f.endswith('.py') or f.startswith(skip) or '/tests/' in f:
            continue
        root, parts = ('src/', f.split('/')[1:]) if f.startswith('src/') else ('', f.split('/'))
        if len(parts) == 1:
            return parts[0][:-3]
        for k in range(len(parts) - 1, 0, -1):
            if root + '/'.join(parts[:k]) + '/__init__.py' in names:
                return '.'.join(parts[:k])
    return r['repo'].split('/')[1].lower().replace('-', '_')


RUNNING = {}  # task -> start time; caches older than the oldest running task are deleted
CACHE_DIR = Path(tempfile.gettempdir()) / 'swegemma_sp_cache_v8'


def clean_tmp():
    """Delete the wheel tars no running task uses, and sandbox / staging dirs created before the oldest running
    task started (a running task's own dirs are newer than its start)."""
    oldest = min(RUNNING.values(), default=time.time()) - 5
    with TAR_LOCK:
        for p in list(TAR_USERS):
            TAR_USERS[p] &= set(RUNNING)
            if not TAR_USERS[p]:
                p.unlink(missing_ok=True)
                del TAR_USERS[p]
    for p in list(CACHE_DIR.glob('staging_*')) + [Path(p) for p in glob.glob('/tmp/swegemma_sandbox_*')]:
        try:
            if p.stat().st_mtime < oldest:
                shutil.rmtree(p, ignore_errors=True)
        except FileNotFoundError:
            pass


