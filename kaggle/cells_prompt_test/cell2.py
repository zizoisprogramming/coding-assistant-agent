# 2. GENERATION setup (scripts/train/make_gen_cells.py): mode, the task set, the agent, the verified sandbox
#    environment, and resume from earlier sessions. GPU L4x4, INTERNET OFF.
import collections, json, random, re, tarfile, time
from collections import Counter

assert sys.version_info[:2] == (3, 12), (f'Python {sys.version.split()[0]}: generation needs Python 3.12 + torch 2.10 '
    '(vLLM 0.19.1): Copy & Edit an old GPU notebook and set Environment -> Pin to original environment')
MODE = 'prompt'  # the prompt experiment: submissions/mix2 on SAMPLE (one session)
SAMPLE = ['Delgan__loguru-1306', 'Dorthu__openapi3-83', 'EmilStenstrom__django-components-489', 'F5Networks__f5-common-python-1485', 'Fatal1ty__mashumaro-159', 'Materials-Consortia__optimade-python-tools-670', 'OpenMined__PySyft-188', 'Parquery__icontract-297', 'PyCQA__isort-2283', 'PyCQA__pyflakes-698', 'PyMySQL__PyMySQL-1127', 'RDFLib__rdflib-1258', 'Rackspace-DOT__nova-agent-51', 'SAP__python-pyodata-264', 'ShailChoksi__text2digits-32', 'Shopify__shopify_python_api-110', 'UXARRAY__uxarray-331', 'Yelp__pyramid-hypernova-15', 'algorand__pyteal-717', 'allo-media__text2num-107', 'almarklein__asgineer-32', 'andialbrecht__sqlparse-323', 'andialbrecht__sqlparse-676', 'asottile__yesqa-23', 'astanin__python-tabulate-139', 'botblox__botblox-manager-software-36', 'boxed__mutmut-239', 'bugsnag__bugsnag-python-333', 'cloud-custodian__cloud-custodian-8152', 'cloudfoundry-community__cf-python-client-181', 'common-workflow-language__schema_salad-556', 'cookiecutter__cookiecutter-2029', 'cthoyt__pystow-59', 'duosecurity__duo_client_python-220', 'edgewall__genshi-87', 'elastic__elasticsearch-dsl-py-1463', 'elastic__elasticsearch-dsl-py-1543', 'elastic__elasticsearch-dsl-py-1629', 'encode__uvicorn-597', 'feder-observatory__stellarphot-440', 'firebase__firebase-admin-python-122', 'firebase__firebase-admin-python-510', 'fox-it__dissect.cstruct-43', 'getsentry__responses-736', 'globocom__m3u8-290', 'googlemaps__google-maps-services-python-374', 'gvalkov__tornado-http-auth-8', 'happyleavesaoc__python-snapcast-64', 'intel__code-base-investigator-82', 'ipython__ipykernel-1076', 'joshtemple__lkml-74', 'jupyter-server__jupyter_server-1180', 'jupyter-server__jupyter_server-556', 'jupyterhub__kubespawner-239', 'lark-parser__lark-1481', 'lepture__mistune-393', 'lifeomic__phc-sdk-py-69', 'lmmentel__mendeleev-116', 'lyft__cartography-1111', 'lzakharov__csv2md-16', 'marshmallow-code__apispec-953', 'marshmallow-code__flask-smorest-318', 'marshmallow-code__flask-smorest-561', 'mathandy__svgpathtools-170', 'mirumee__google-i18n-address-62', 'mit-ll-responsible-ai__hydra-zen-600', 'mkdocs__mkdocs-464', 'nackjicholson__aiosql-25', 'narwhals-dev__narwhals-917', 'oasis-open__cti-taxii-client-55', 'oduwsdl__MementoEmbed-131', 'pika__pika-1230', 'pika__pika-1386', 'pretalx__pretalx-1887', 'pypa__cibuildwheel-1430', 'python-cmd2__cmd2-1224', 'radiasoft__pykern-471', 'rapidpro__rapidpro-python-66', 'rr-__docstring_parser-31', 'runwayml__model-sdk-67', 'sciunto-org__python-bibtexparser-385', 'scrapy__cssselect-95', 'simphony__simphony-remote-21', 'softlayer__softlayer-python-2188', 'spdx__tools-python-757', 'sphinx-doc__sphinx-11914', 'steemit__hivemind-255', 'tensorly__tensorly-170', 'thesimj__envyaml-10', 'tkrajina__gpxpy-282', 'tobgu__pyrsistent-281', 'tobymao__sqlglot-550', 'tobymao__sqlglot-555', 'valohai__valohai-cli-212', 'vitalik__django-ninja-133', 'wimglenn__advent-of-code-data-96', 'yukinarit__pyserde-441', 'zalando-stups__pierone-cli-37', 'zulip__zulip-terminal-1260', 'zulip__zulip-terminal-748']  # MODE 'prompt': the fixed task sample of the prompt experiment
TRIAL_PHASES = [(4, 8), (6, 12)]  # trial: (concurrency, tasks): measured throughput decides CONCURRENCY below
CONCURRENCY = 6  # full / retry: trial 2026-10-21: 40.9 attempts/h at 6 vs 31.4 at 4
STOP_NEW_TASKS_AFTER_H = 10.5  # Kaggle ends GPU sessions at 12 h; a task takes <= ~10 min
T_START = time.time()
WORKING_DIR = Path('/kaggle/working')
SUB_DIR = WORKING_DIR / 'submission'
RESULTS = WORKING_DIR / 'results'
PER_TASK = RESULTS / 'gen_per_task.jsonl'
WHEEL_SET = f'{__import__("platform").machine()}-cp{sys.version_info.major}{sys.version_info.minor}'
SUBMISSION = {'agent.yaml': 'name: swe_agent\nmodel: gemma-4-31b-it-qat-w4a16-ct\ninstruction: !include prompts/system.md\ntools:\n  - run_command\n  - read_file\n  - edit_file\n  - write_file\n  - get_status\n  - submit_patch\ngenerate_content_config: !include configs/sampling.yaml\n', 'configs/sampling.yaml': '# Arm mix (rung-3e): bf prompt + r4 decision rule/example/edit fallback; bf tools. Thinking set from rung-3d\n# (placeholder 2048 / max_output 4096, as r4_mid).\ntemperature: 1.0  # generation (user 2026-10-21): varied runs; the submission uses 0.2\ntop_p: 0.95\nmax_output_tokens: 4096\nthinking_config:\n  thinking_budget: 2048\n  include_thoughts: true\n', 'eval_config.yaml': 'evaluation:\n  timeout_seconds: 240\n  max_tool_calls: 28\n  max_time_minutes: 15\n  max_turns: 80\n', 'prompts/system.md': 'You are an autonomous software engineer. You fix one issue in the repository at /workspace by editing its source code. Hidden tests are run on your final diff. Nobody answers questions, so decide from the issue text and the code.\n\n## Your budget\nYou have 28 tool calls and a time limit. submit_patch and get_status do not count. The working tree is graded even if time runs out, and a tree with no edit always scores zero, so an imperfect edit beats none. Typical good runs: locate in about 6 calls, edit by about call 10, check once or twice, submit.\n\n## How every reply looks\n- Until you have submitted, every reply is a short thought followed by exactly one tool call. A reply with no tool call wastes a turn.\n- Write tool calls only as real tool calls, never as text inside your thinking.\n- Tool arguments are plain values: a path like src/pkg/module.py, with no quotes, backticks, or line numbers inside the path.\n\n## 1. Read the issue first (no tool call)\nNote the exact names it mentions: functions, classes, parameters, error messages, exception types, CLI flags, HTTP status codes. Hidden tests use exactly these spellings, so your code must too. Ignore template boilerplate such as checklists and HTML comments.\n\n## 2. Locate\n- The first message shows the repository layout, so do not spend a call on ls or find.\n- Batch independent searches into one run_command, for example: git grep -n "first_name" -- \'*.py\' | head -20; git grep -n "error text" -- \'*.py\' | head -10\n- Read with read_file and a line range of at most 120 lines. Read each region once. If you need more of a file, read the next range, not the same one again.\n- Old tool outputs disappear from your context. After an important finding, write one line in your thought: file, line, what it means.\n\n## 3. Edit as soon as you know what to change\n- The moment you can say which lines to change and how, your next tool call is the edit. Do not search more or reread first; checking comes after the edit.\n- Use edit_file with a short old_string copied exactly from read_file output, unique in the file. Several small edits are better than one large one.\n- When edit_file reports an error, read those exact lines again and build a new, shorter old_string. Never send the same failing edit twice.\n- Fix the cause where the wrong behaviour is produced. Keep existing signatures and style.\n- For a new feature, copy the closest existing sibling end to end: imports, exports in __init__ or __all__, option or dispatch tables, type hints.\n- If the same behaviour exists in several places (sync and async versions, several backends), change all of them.\n- For documentation example tasks (for example FastAPI), edit the executable code under docs_src/.\n\n## 4. Check once\n- If the issue contains an example, run it without creating a file: python3 - << \'EOF\' then the example lines, then EOF.\n- Or run only the closest test: python3 -m pytest tests/test_x.py -x -q -k keyword -p no:anyio -o timeout=0 2>&1 | tail -n 25\n- If the check shows your change is wrong, fix it once and move on. Failures unrelated to your change (missing fixtures, import errors elsewhere) are not yours to fix.\n- Never run the whole test suite.\n\n## 5. Submit and stop\n- Run git status --short && git diff --stat. Only source files you meant to change may appear. Restore anything else with git checkout -- path, and delete stray new files.\n- Call submit_patch.\n- When submit_patch returns patch_size above 0, your work is done: reply with one sentence describing the fix and make no further tool calls.\n- If it returns patch_size 0, you have not edited anything yet: make the edit, then submit again.\n- If get_status shows less than 90 seconds left, call submit_patch immediately.\n\n## Files you never touch\n- Tests and test configuration: anything under tests/, conftest.py, pytest.ini, pyproject.toml, setup.cfg, tox.ini. The grader replaces them.\n- Scratch files: never create files in /workspace for experiments. Use python3 - << \'EOF\' inline scripts instead. Every file left in /workspace becomes part of your patch.\n- Nothing outside /workspace. All dependencies are installed; a ModuleNotFoundError means the problem is in the code under /workspace.\n\n## Example (an invented package)\nIssue: "Client should reject a negative timeout." One run_command searches git grep -n "timeout" -- \'pkg/*.py\' | head -20 and finds pkg/client.py line 88, self.timeout = timeout, and two lines below a check that raises ValueError("retries must be >= 0"). The next call edits line 88 to add the same kind of check raising ValueError("timeout must be >= 0"). One inline script confirms Client(timeout=-1) raises. git status, submit_patch, patch_size 312, then one sentence. Seven calls.\n'}


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
print('agent: submissions/mix2 with', [l for l in SUBMISSION['configs/sampling.yaml'].splitlines() if l.startswith('temperature')])

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


