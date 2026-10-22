# 2. GENERATION setup (scripts/train/make_gen_cells.py): mode, the task set, the agent, the verified sandbox
#    environment, and resume from earlier sessions. GPU L4x4, INTERNET OFF.
import collections, json, random, re, tarfile, time
from collections import Counter

assert sys.version_info[:2] == (3, 12), (f'Python {sys.version.split()[0]}: generation needs Python 3.12 + torch 2.10 '
    '(vLLM 0.19.1): Copy & Edit an old GPU notebook and set Environment -> Pin to original environment')
MODE = 'full'  # extra set: our 62 left-out tasks + OOD-45 -> 'full', then 'retry' (attach the full run's output)
SAMPLE = []  # MODE 'prompt': the fixed task sample of the prompt experiment
TRIAL_PHASES = [(4, 8), (6, 12)]  # trial: (concurrency, tasks): measured throughput decides CONCURRENCY below
CONCURRENCY = 6  # full / retry: trial 2026-10-21: 40.9 attempts/h at 6 vs 31.4 at 4
STOP_NEW_TASKS_AFTER_H = 10.5  # Kaggle ends GPU sessions at 12 h; a task takes <= ~10 min
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
for p in sorted(glob.glob('/kaggle/input/**/results/gen_per_task.jsonl', recursive=True)) + ([str(PER_TASK)] if PER_TASK.exists() else []):
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
ood.patch_harness()
WHEEL_ROOT = Path('/tmp/gen_wheels')
ood.materialize_wheels(OUT, WHEEL_SET, WHEEL_ROOT / WHEEL_SET)
_host = sorted(str(p) for p in (OUT / 'wheels' / 'host').glob('*.whl'))
_r = subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '--no-index', '--no-deps', *_host], capture_output=True, text=True)
print('host pytest plugins:', [Path(p).name for p in _host], '-> exit', _r.returncode, _r.stderr[-200:])

# OOD-45 joins the run (user 2026-10-22: training data now; the test set is a separate build). Its 44 tasks
# (urllib3_5279 does not run on Python 3.12) keep their own snapshots and per-repo wheel sets, and the statement is g1
# (the released, rewritten one), as in our OOD-45 runs. results/tasks_used.jsonl = every task of this run with its
# labels: the samples notebook reads reference patches from it.
OOD_SKIP = {'urllib3_5279'}
OOD_TASKS, OOD_META = ood.load_tasks(OOD_DIR)
assert len(OOD_TASKS) == 45, f'OOD-45 has {len(OOD_TASKS)} tasks'
OOD_WHEELS = Path('/tmp/ood_wheels') / WHEEL_SET
ood.materialize_wheels(OOD_DIR, WHEEL_SET, OOD_WHEELS)
for _iid in sorted(set(OOD_TASKS) - OOD_SKIP):
    _t = OOD_TASKS[_iid]['g1']
    assert _iid not in ROWS, f'{_iid} is in both task sets'
    assert (OOD_DIR / 'snapshots' / f'{_iid}.tgz').exists() and (OOD_WHEELS / _t.repo.split('/', 1)[1]).exists(), _iid
    ROWS[_iid] = {'instance_id': _iid, 'repo': _t.repo, 'base_commit': _t.base_commit, 'problem_statement': _t.problem_statement,
                  'patch': _t.patch, 'test_patch': _t.test_patch, 'created_at': _t.created_at,
                  'FAIL_TO_PASS': list(_t.FAIL_TO_PASS), 'PASS_TO_PASS': list(_t.PASS_TO_PASS), 'src': 'ood',
                  'level': 'ood', 'domain': 'ood', 'text_kind': 'ood', 'leak': False, 'unfair_names': [],
                  'env_partial': bool(OOD_META[_iid].get('env_overlay'))}
with open(RESULTS / 'tasks_used.jsonl', 'w') as _fh:
    for _r in ROWS.values():
        _fh.write(json.dumps(_r) + '\n')
print(f"this run: {len(ROWS)} tasks = {sum(r.get('src') != 'ood' for r in ROWS.values())} ours + "
      f"{sum(r.get('src') == 'ood' for r in ROWS.values())} OOD-45 (skipped {sorted(OOD_SKIP)}) from "
      f"{len({r['repo'] for r in ROWS.values()})} repos | wheel sets {WHEEL_SET}")

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


