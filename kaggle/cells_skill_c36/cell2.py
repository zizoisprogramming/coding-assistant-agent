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
ATTEMPTS = 1  # passes; after pass 1 an arm with EARLY_STOP_MAX or fewer solved is dropped (none left: the run ends)
EARLY_STOP_MAX = 3
PASS2_IF_BEATS = None  # (a, b): pass 2 runs only if a solved more than b in pass 1
ARMS = ['sq1c2', 'sq1c3', 'sq1c4']
ARM_FILES = {'sq1c2': {'agent.yaml': '# sq1c2 = sq1 with the clock shell (skills/work, scripts/run.py) instead of run_command; sq1: SequentialAgent [fixer, finisher] (scripts/make_skill_arms.py sq2): the fixer (pub024 procedure) never\n# submits and hands over in plain text; the finisher only submits (sq2 without the second attempt).\nname: swe_agent\nagent_class: SequentialAgent\nsub_agents:\n  - config_path: fixer.yaml\n  - config_path: finisher.yaml\n', 'configs/sampling.yaml': 'temperature: 0.2\ntop_p: 0.95\nmax_output_tokens: 8192\nthinking_config:\n  thinking_budget: 4096\n  include_thoughts: true\n', 'eval_config.yaml': 'evaluation:\n  timeout_seconds: 240\n  max_tool_calls: 80\n  max_time_minutes: 8\n  max_turns: 400\n', 'finisher.yaml': "name: finisher\nmodel: gemma-4-31b-it-qat-w4a16-ct\ninstruction: !include prompts/finisher.md\ninclude_contents: none  # fresh: its context starts at the fixer's hand-over line\ntools:\n  - run_command\n  - read_file\n  - edit_file\n  - write_file\n  - get_status\n  - submit_patch  # declared on all: the harness task message names it; an undeclared call drops the patch\ngenerate_content_config: !include configs/sampling.yaml\n", 'fixer.yaml': 'name: fixer\nmodel: gemma-4-31b-it-qat-w4a16-ct\ninstruction: !include prompts/fixer.md\ntools:  # no run_command: the shell is run_skill_script work scripts/run.py (clock line in every output)\n  - read_file  # named in the harness task message\n  - edit_file\n  - write_file\n  - get_status\n  - submit_patch  # declared on all: the harness task message names it; an undeclared call drops the patch\n  - get_code_neighbors\n  - search_similar_code\n  - get_code_subgraph\nskills:\n  - skills/work\ngenerate_content_config: !include configs/sampling.yaml\n', 'prompts/finisher.md': 'You submit this task: an engineer has just fixed the issue in /workspace, and the last message says\nwhat changed. The fix is final. You do not read, run or edit anything.\n\nYour only tool call: submit_patch. Then reply with one sentence and make no further tool calls.\n', 'prompts/fixer.md': 'You are an autonomous software engineer. Your job: make the smallest correct change to the SOURCE code in\n/workspace so that the hidden tests for the issue pass. The hidden tests were written from the issue text, so the\nexact names, messages, types and behaviours in the issue are the specification. When you finish, a teammate submits\nyour patch: you never call submit_patch.\n\n# YOUR TOOLS\n- Shell: run_skill_script with skill_name work, file_path scripts/run.py and positional_args, a list holding one\n  string: the whole shell command. Do not use the args parameter. It runs in /workspace. This is your only way to run\n  commands.\n- read_file to read a file region, edit_file to change a file, write_file to create a scratch file.\n- Every shell result ends with a clock line: "[clock] N s of 480 used | ..." and whether a source file is edited.\n  Read it every time. You have 8 minutes in total; the time goes mostly into your own thinking, so keep replies\n  short.\n- If a tool answers that an argument is required, your call was malformed: send it again with every argument\n  written out plainly, never the same broken call twice.\n\n# LIMITS\n- An edit that exists in /workspace counts even if time runs out; an unedited tree scores zero. Edit a source file\n  before 180 s on the clock: if unsure, make your best-guess edit in the most likely place; a wrong edit can still\n  be corrected. With no source edit at 270 s the shell refuses commands until you edit.\n- Never create, modify or delete test files (test_*.py, *_test.py, anything under tests/, pytest.ini, conftest.py).\n- Scratch files go in /tmp or .git/agent/ only: any other file left under /workspace becomes part of the patch.\n- Never run a full test suite: always name one test file, and add -k when you can.\n- Never use search_similar_code, get_code_neighbors or get_code_subgraph: they return nothing useful.\n\n# TIME PLAN (by the clock line)\n- Up to about 120 s: locate and read. By 180 s: your edit is in the file.\n- Then: write your repro script and run it once; one related test file; fix once if needed.\n- From 400 s: stop and FINISH.\n\n# PROCEDURE\n1. Before your first call, list for yourself the exact file, function, class or CLI name; the exact error message\n   and exception type; the expected return value or output; the inputs that trigger the bug; every edge case\n   mentioned. Every concrete string and name in the issue is a literal that must appear exactly in your code.\n2. Locate. Use exact paths from the issue directly. Combine independent searches for the issue\'s exact symbols,\n   their callers and relevant tests in one shell command: git grep -n -F "symbol" and git ls-files, about 20 lines\n   of output each. Then read the implementation plus one caller or test, about 40 lines per region, at most three\n   regions per command (sed -n \'START,ENDp\' FILE). For a bug, find where the wrong behaviour is produced; for a\n   feature, copy the closest existing sibling, including __all__, option lists, dispatch tables and imports.\n3. Edit with edit_file: copy old_string exactly, short and unique. If it fails twice, use one inline python script\n   through the shell (quoted heredoc) that asserts the old text occurs once, replaces it and writes the file. Fix the\n   cause, not the symptom. Change only what the issue requires and keep signatures and defaults. Apply the change to\n   every parallel implementation (sync and async, each backend, re-exports in __init__.py or __all__). Use the exact\n   exception class and message text from the issue. For FastAPI documentation tasks, edit docs_src/.\n4. Repro script: write_file .git/agent/repro_a.py, a short python script that shows the issue\'s behaviour: it must\n   EXIT WITH AN ERROR (assert or raise) while the bug is there and exit 0 once it is fixed, printing FIXED or BUG.\n   Import the package normally. Run it once: timeout 30 python3 .git/agent/repro_a.py\n5. If one related test file exists, run it once: timeout 150 python -m pytest tests/path/test_x.py -x -q -k keyword\n   Failures from missing fixtures or unrelated imports are pre-existing: ignore them.\n\n# FINISH\n1. git status --short && git diff in one shell command: remove any scratch file in /workspace, restore any changed\n   test file with git checkout -- path.\n2. Reply with plain text and NO tool call: one line saying what you changed and where. That reply hands over to\n   your teammate.\n\n# DECISION RULES\n- Ambiguous issue: choose the most literal reading and act on it. Never ask questions.\n- Several possible places: pick where the wrong behaviour is produced, not where it is observed.\n- Stuck after a failed fix: make a different, smaller change. Never repeat the same edit.\n- Never conclude that nothing needs to change: every task needs a non-empty source patch.\n', 'skills/work/SKILL.md': '---\nname: work\ndescription: The fixer\'s shell. run_skill_script with skill_name work, file_path scripts/run.py and positional_args,\n  a list holding one string, the whole shell command. Runs in /workspace; the output ends with a clock line.\n---\n\nscripts/run.py runs one shell command in /workspace (output cut at 5000 characters) and ends with\n"[clock] N s of 480 used | source edited: FILES" or "no source edit yet". With no source edit at 270 s it refuses\ncommands until edit_file has changed a source file.\n', 'skills/work/scripts/run.py': '"""sq1c\'s shell (skill "work", scripts/run.py): runs one shell command in the repository and ends its output with a\nclock line, so the fixer sees the time and whether a source file is edited in every command result (the harness has\nno time warning; the model acts on tool outputs, not on prompt rules). With no source edit late in the session it\nfirst warns, then refuses commands until edit_file has changed a source file.\n\n    run_skill_script skill_name=work file_path=scripts/run.py args={"cmd": "git grep -n foo"}\n"""\nimport json\nimport os\nimport re\nimport subprocess\nimport sys\nimport time\n\nSESSION = 480  # max_time_minutes 8\nWARN_AT = 180  # no source edit by now: warn (runs whose first edit came after 180 s solved 22-34%, before 120 s 76%)\nREFUSE_AT = 270  # no source edit by now: refuse commands until one exists\nOUT_MAX = 5000  # as the harness\'s run_command output limit\nEDIT_CMD = re.compile(r"sed -i|git apply|\\bpatch\\b|open\\([^)]*[\'\\"][wa][\'\\"]|write_text\\(|>\\s*(?!/tmp|/dev/null|&)\\S")\nTEST_RE = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\\.py$|_test\\.py$|(^|/)conftest\\.py$|(^|/)pytest\\.ini$")\n\n\ndef workspace():\n    """The repository root: the skill wrapper chdirs into a temp dir, so find the directory it started in."""\n    import inspect\n    for frame in inspect.stack():\n        cwd = frame.frame.f_locals.get("_orig_cwd")\n        if isinstance(cwd, str) and os.path.isdir(os.path.join(cwd, ".git")):\n            return cwd\n    for cand in ("/workspace", os.getcwd()):\n        if os.path.isdir(os.path.join(cand, ".git")):\n            return cand\n    return os.getcwd()\n\n\ndef sh(cmd, ws, timeout=30):\n    r = subprocess.run(cmd, cwd=ws, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)\n    return r.returncode, r.stdout\n\n\ndef started(ws):\n    """Session start: the harness tags _swegemma_baseline when the sandbox starts; else the first run.py call."""\n    code, out = sh(["git", "log", "-1", "--format=%ct", "_swegemma_baseline"], ws)\n    if code == 0 and out.strip().isdigit():\n        return int(out.strip())\n    path = os.path.join(ws, ".git", "agent", "clock.json")\n    try:\n        return json.load(open(path))["t0"]\n    except Exception:\n        os.makedirs(os.path.dirname(path), exist_ok=True)\n        json.dump({"t0": time.time()}, open(path, "w"))\n        return time.time()\n\n\ndef edited(ws):\n    """Changed or new source files (not tests, not scratch files)."""\n    _, out = sh(["git", "status", "--porcelain", "--untracked-files=all"], ws)\n    files = [line[3:].split(" -> ")[-1].strip(\'"\') for line in out.splitlines() if len(line) > 3]\n    return [f for f in files if not TEST_RE.search(f) and not os.path.basename(f).startswith("repro")]\n\n\ndef command():\n    """The command from args {"cmd": "..."} (argv --cmd X), a list of strings, or positional args."""\n    argv = [a for a in sys.argv[1:] if a != "--"]\n    if argv[:1] == ["--cmd"]:\n        argv = argv[1:]\n    elif argv[:1] and argv[0].startswith("--"):\n        argv = argv[1:]\n    return " ".join(argv).strip()\n\n\ndef main():\n    ws = workspace()\n    used = int(time.time() - started(ws))\n    cmd = command()\n    files = edited(ws)\n    if not cmd:\n        body = \'NO COMMAND: pass it as args {"cmd": "your shell command"}.\'\n    elif not files and used >= REFUSE_AT and not EDIT_CMD.search(cmd):\n        body = (f"REFUSED: {used} s of {SESSION} used and no source file is edited yet. An unedited tree scores zero; "\n                "a best guess can still be corrected. Your next call must be edit_file on the most likely place "\n                "(where the wrong behaviour is produced). Commands run again once a source file is edited.")\n    else:\n        try:\n            r = subprocess.run(["bash", "-c", cmd], cwd=ws, capture_output=True, text=True, stdin=subprocess.DEVNULL,\n                               timeout=max(5, min(150, SESSION - used - 10)))\n            body = (r.stdout + (("\\n[stderr]\\n" + r.stderr) if r.stderr.strip() else "")).rstrip() + f"\\n[exit {r.returncode}]"\n        except subprocess.TimeoutExpired:\n            body = "[timed out]"\n        if len(body) > OUT_MAX:\n            body = body[:OUT_MAX] + f"\\n[output cut at {OUT_MAX} characters: narrow the command]"\n        files = edited(ws)\n    if files:\n        state = "source edited: " + ", ".join(files[:4])\n    elif used >= WARN_AT:\n        state = (f"NO SOURCE EDIT YET. Make your best edit now with edit_file; at {REFUSE_AT} s commands are refused "\n                 "until a source file is edited")\n    else:\n        state = "no source edit yet"\n    print(body + f"\\n[clock] {used} s of {SESSION} used | {state}")\n\n\nif __name__ == "__main__":\n    main()\n'}, 'sq1c3': {'agent.yaml': '# sq1c3 = sq1 with the clock shell (skills/work, scripts/run.py) instead of run_command; sq1: SequentialAgent [fixer, finisher] (scripts/make_skill_arms.py sq2): the fixer (pub024 procedure) never\n# submits and hands over in plain text; the finisher only submits (sq2 without the second attempt).\nname: swe_agent\nagent_class: SequentialAgent\nsub_agents:\n  - config_path: fixer.yaml\n  - config_path: finisher.yaml\n', 'configs/sampling.yaml': 'temperature: 0.2\ntop_p: 0.95\nmax_output_tokens: 8192\nthinking_config:\n  thinking_budget: 4096\n  include_thoughts: true\n', 'eval_config.yaml': 'evaluation:\n  timeout_seconds: 240\n  max_tool_calls: 80\n  max_time_minutes: 8\n  max_turns: 400\n', 'finisher.yaml': "name: finisher\nmodel: gemma-4-31b-it-qat-w4a16-ct\ninstruction: !include prompts/finisher.md\ninclude_contents: none  # fresh: its context starts at the fixer's hand-over line\ntools:\n  - run_command\n  - read_file\n  - edit_file\n  - write_file\n  - get_status\n  - submit_patch  # declared on all: the harness task message names it; an undeclared call drops the patch\ngenerate_content_config: !include configs/sampling.yaml\n", 'fixer.yaml': 'name: fixer\nmodel: gemma-4-31b-it-qat-w4a16-ct\ninstruction: !include prompts/fixer.md\ntools:  # no run_command: the shell is run_skill_script work scripts/run.py (clock line in every output)\n  - read_file  # declared only so a habitual call never ends the task; the prompt says to read through the shell\n  - edit_file\n  - write_file\n  - get_status\n  - submit_patch  # declared on all: the harness task message names it; an undeclared call drops the patch\n  - get_code_neighbors\n  - search_similar_code\n  - get_code_subgraph\nskills:\n  - skills/work\ngenerate_content_config: !include configs/sampling.yaml\n', 'prompts/finisher.md': 'You submit this task: an engineer has just fixed the issue in /workspace, and the last message says\nwhat changed. The fix is final. You do not read, run or edit anything.\n\nYour only tool call: submit_patch. Then reply with one sentence and make no further tool calls.\n', 'prompts/fixer.md': 'You are an autonomous software engineer. You change the SOURCE code in /workspace, as little as possible, so\nthat the hidden tests for the issue in the task message pass. Those tests were written from the issue text: its exact names,\nmessages, types and behaviours are the specification. A teammate submits your patch after you; you never call\nsubmit_patch.\n\n# TOOLS\n- The shell: run_skill_script with skill_name work, file_path scripts/run.py and positional_args, a list holding one\n  string that is the whole shell command. Do not use the args parameter. Commands run in /workspace. You read files\n  through this shell too: sed -n \'START,ENDp\' FILE, about 40 lines per region, up to three regions in one command.\n- edit_file changes a file; write_file creates a scratch file.\n- Do not use read_file: every reading goes through the shell, so that you always see the clock.\n- Each shell output ends with a clock line, "[clock] N s of 480 used | ...", saying how much of your 8 minutes is\n  gone and whether a source file is edited. Read it each time. Most of the time goes into your own thinking: keep\n  your replies short.\n- A tool answer saying an argument is required means your call was malformed. Send it again with every argument\n  written out plainly; never repeat the broken call.\n\n# LIMITS\n- Whatever edit is in /workspace when time runs out is graded; an unedited tree scores zero. Have a source file\n  edited by 180 s on the clock. If you are unsure, make your best guess where the wrong behaviour is produced: a\n  wrong edit can still be corrected. With no source edit at 270 s the shell refuses every command, reading included,\n  until a source file is edited.\n- Never create, change or delete test files (test_*.py, *_test.py, anything under tests/, pytest.ini, conftest.py).\n- Scratch files only in /tmp or .git/agent/: any other new file under /workspace ends up in the patch.\n- Never run a whole test suite: name one test file, and add -k when you can.\n- Never use search_similar_code, get_code_neighbors or get_code_subgraph: they return nothing useful.\n\n# TIME PLAN (by the clock line)\n- Until about 120 s: locate and read. By 180 s: your edit is in the file.\n- After that: one repro script, run once; one related test file; one correction if needed.\n- From 400 s: stop and finish.\n\n# HOW TO WORK\n1. Before your first call, note for yourself the exact file, function, class or CLI name, the exact error message\n   and exception type, the expected value or output, the inputs that trigger the bug and every edge case the issue\n   mentions. Each concrete string and name in the issue must appear exactly like that in your code.\n2. Locate. Go straight to paths the issue names. Put independent searches for the issue\'s symbols, their callers and\n   their tests in one shell command (git grep -n -F "symbol", git ls-files), about 20 output lines each. Then read\n   the implementation and one caller or test with sed -n. For a bug, find where the wrong behaviour is produced; for\n   a feature, copy the closest existing sibling, with its __all__ entries, option lists, dispatch tables and imports.\n3. Edit with edit_file, with a short, unique old_string copied exactly. If it fails twice, run one inline python\n   script through the shell (quoted heredoc) that asserts the old text occurs once, replaces it and writes the file.\n   Fix the cause, not the symptom; change only what the issue asks and keep signatures and defaults. Make the same\n   change in every parallel implementation (sync and async, each backend, re-exports in __init__.py or __all__).\n   Use the issue\'s exception class and message text. For FastAPI documentation tasks, edit docs_src/.\n4. Repro: write_file .git/agent/repro_a.py, a short script that imports the package normally, FAILS (assert or\n   raise) while the bug is there and exits 0 once it is fixed, printing FIXED or BUG. Run it once:\n   timeout 30 python3 .git/agent/repro_a.py\n5. If one related test file exists, run it once: timeout 150 python -m pytest tests/path/test_x.py -x -q -k keyword\n   Failures from missing fixtures or unrelated imports were there before you: ignore them.\n\n# FINISH\n1. One shell command: git status --short && git diff. Remove scratch files from /workspace; restore any changed\n   test file with git checkout -- path.\n2. Reply in plain text with NO tool call: one line on what you changed and where. That reply hands over to your\n   teammate.\n\n# DECISIONS\n- Ambiguous issue: take the most literal reading and act on it. Never ask questions.\n- Several candidate places: choose where the wrong behaviour is produced, not where it shows.\n- A fix failed: make a different, smaller change; never repeat the same edit.\n- Never decide that nothing needs to change: every task needs a non-empty source patch.\n', 'skills/work/SKILL.md': '---\nname: work\ndescription: The fixer\'s shell, also used for reading files. run_skill_script with skill_name work, file_path\n  scripts/run.py and positional_args, a list holding one string, the whole shell command. Output ends with a clock line.\n---\n\nscripts/run.py runs one shell command in /workspace (output cut at 5000 characters) and ends with\n"[clock] N s of 480 used | source edited: FILES" or "no source edit yet". With no source edit at 270 s it refuses\nevery command, reading included, until edit_file has changed a source file.\n', 'skills/work/scripts/run.py': '"""sq1c\'s shell (skill "work", scripts/run.py): runs one shell command in the repository and ends its output with a\nclock line, so the fixer sees the time and whether a source file is edited in every command result (the harness has\nno time warning; the model acts on tool outputs, not on prompt rules). With no source edit late in the session it\nfirst warns, then refuses commands until edit_file has changed a source file.\n\n    run_skill_script skill_name=work file_path=scripts/run.py args={"cmd": "git grep -n foo"}\n"""\nimport json\nimport os\nimport re\nimport subprocess\nimport sys\nimport time\n\nSESSION = 480  # max_time_minutes 8\nWARN_AT = 180  # no source edit by now: warn (runs whose first edit came after 180 s solved 22-34%, before 120 s 76%)\nREFUSE_AT = 270  # no source edit by now: refuse commands until one exists\nOUT_MAX = 5000  # as the harness\'s run_command output limit\nEDIT_CMD = re.compile(r"sed -i|git apply|\\bpatch\\b|open\\([^)]*[\'\\"][wa][\'\\"]|write_text\\(|>\\s*(?!/tmp|/dev/null|&)\\S")\nTEST_RE = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\\.py$|_test\\.py$|(^|/)conftest\\.py$|(^|/)pytest\\.ini$")\n\n\ndef workspace():\n    """The repository root: the skill wrapper chdirs into a temp dir, so find the directory it started in."""\n    import inspect\n    for frame in inspect.stack():\n        cwd = frame.frame.f_locals.get("_orig_cwd")\n        if isinstance(cwd, str) and os.path.isdir(os.path.join(cwd, ".git")):\n            return cwd\n    for cand in ("/workspace", os.getcwd()):\n        if os.path.isdir(os.path.join(cand, ".git")):\n            return cand\n    return os.getcwd()\n\n\ndef sh(cmd, ws, timeout=30):\n    r = subprocess.run(cmd, cwd=ws, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)\n    return r.returncode, r.stdout\n\n\ndef started(ws):\n    """Session start: the harness tags _swegemma_baseline when the sandbox starts; else the first run.py call."""\n    code, out = sh(["git", "log", "-1", "--format=%ct", "_swegemma_baseline"], ws)\n    if code == 0 and out.strip().isdigit():\n        return int(out.strip())\n    path = os.path.join(ws, ".git", "agent", "clock.json")\n    try:\n        return json.load(open(path))["t0"]\n    except Exception:\n        os.makedirs(os.path.dirname(path), exist_ok=True)\n        json.dump({"t0": time.time()}, open(path, "w"))\n        return time.time()\n\n\ndef edited(ws):\n    """Changed or new source files (not tests, not scratch files)."""\n    _, out = sh(["git", "status", "--porcelain", "--untracked-files=all"], ws)\n    files = [line[3:].split(" -> ")[-1].strip(\'"\') for line in out.splitlines() if len(line) > 3]\n    return [f for f in files if not TEST_RE.search(f) and not os.path.basename(f).startswith("repro")]\n\n\ndef command():\n    """The command from args {"cmd": "..."} (argv --cmd X), a list of strings, or positional args."""\n    argv = [a for a in sys.argv[1:] if a != "--"]\n    if argv[:1] == ["--cmd"]:\n        argv = argv[1:]\n    elif argv[:1] and argv[0].startswith("--"):\n        argv = argv[1:]\n    return " ".join(argv).strip()\n\n\ndef main():\n    ws = workspace()\n    used = int(time.time() - started(ws))\n    cmd = command()\n    files = edited(ws)\n    if not cmd:\n        body = \'NO COMMAND: pass it as args {"cmd": "your shell command"}.\'\n    elif not files and used >= REFUSE_AT and not EDIT_CMD.search(cmd):\n        body = (f"REFUSED: {used} s of {SESSION} used and no source file is edited yet. An unedited tree scores zero; "\n                "a best guess can still be corrected. Your next call must be edit_file on the most likely place "\n                "(where the wrong behaviour is produced). Every command, reading included, runs again once a source file is edited; do not read with read_file either.")\n    else:\n        try:\n            r = subprocess.run(["bash", "-c", cmd], cwd=ws, capture_output=True, text=True, stdin=subprocess.DEVNULL,\n                               timeout=max(5, min(150, SESSION - used - 10)))\n            body = (r.stdout + (("\\n[stderr]\\n" + r.stderr) if r.stderr.strip() else "")).rstrip() + f"\\n[exit {r.returncode}]"\n        except subprocess.TimeoutExpired:\n            body = "[timed out]"\n        if len(body) > OUT_MAX:\n            body = body[:OUT_MAX] + f"\\n[output cut at {OUT_MAX} characters: narrow the command]"\n        files = edited(ws)\n    if files:\n        state = "source edited: " + ", ".join(files[:4])\n    elif used >= WARN_AT:\n        state = (f"NO SOURCE EDIT YET. Make your best edit now with edit_file; at {REFUSE_AT} s commands are refused "\n                 "until a source file is edited")\n    else:\n        state = "no source edit yet"\n    print(body + f"\\n[clock] {used} s of {SESSION} used | {state}")\n\n\nif __name__ == "__main__":\n    main()\n'}, 'sq1c4': {'agent.yaml': '# sq1c4 = sq1 with the clock shell (skills/work, scripts/run.py) instead of run_command; sq1: SequentialAgent [fixer, finisher] (scripts/make_skill_arms.py sq2): the fixer (pub024 procedure) never\n# submits and hands over in plain text; the finisher only submits (sq2 without the second attempt).\nname: swe_agent\nagent_class: SequentialAgent\nsub_agents:\n  - config_path: fixer.yaml\n  - config_path: finisher.yaml\n', 'configs/sampling.yaml': 'temperature: 0.2\ntop_p: 0.95\nmax_output_tokens: 8192\nthinking_config:\n  thinking_budget: 2048\n  include_thoughts: true\n', 'eval_config.yaml': 'evaluation:\n  timeout_seconds: 240\n  max_tool_calls: 80\n  max_time_minutes: 8\n  max_turns: 400\n', 'finisher.yaml': "name: finisher\nmodel: gemma-4-31b-it-qat-w4a16-ct\ninstruction: !include prompts/finisher.md\ninclude_contents: none  # fresh: its context starts at the fixer's hand-over line\ntools:\n  - run_command\n  - read_file\n  - edit_file\n  - write_file\n  - get_status\n  - submit_patch  # declared on all: the harness task message names it; an undeclared call drops the patch\ngenerate_content_config: !include configs/sampling.yaml\n", 'fixer.yaml': 'name: fixer\nmodel: gemma-4-31b-it-qat-w4a16-ct\ninstruction: !include prompts/fixer.md\ntools:  # no run_command: the shell is run_skill_script work scripts/run.py (clock line in every output)\n  - read_file  # named in the harness task message\n  - edit_file\n  - write_file\n  - get_status\n  - submit_patch  # declared on all: the harness task message names it; an undeclared call drops the patch\n  - get_code_neighbors\n  - search_similar_code\n  - get_code_subgraph\nskills:\n  - skills/work\ngenerate_content_config: !include configs/sampling.yaml\n', 'prompts/finisher.md': 'You submit this task: an engineer has just fixed the issue in /workspace, and the last message says\nwhat changed. The fix is final. You do not read, run or edit anything.\n\nYour only tool call: submit_patch. Then reply with one sentence and make no further tool calls.\n', 'prompts/fixer.md': 'You are an autonomous software engineer. Your job: make the smallest correct change to the SOURCE code in\n/workspace so that the hidden tests for the issue pass. The hidden tests were written from the issue text, so the\nexact names, messages, types and behaviours in the issue are the specification. When you finish, a teammate submits\nyour patch: you never call submit_patch.\n\n# YOUR TOOLS\n- Shell: run_skill_script with skill_name work, file_path scripts/run.py and positional_args, a list holding one\n  string: the whole shell command. Do not use the args parameter. It runs in /workspace. This is your only way to run\n  commands.\n- read_file to read a file region, edit_file to change a file, write_file to create a scratch file.\n- Every shell result ends with a clock line: "[clock] N s of 480 used | ..." and whether a source file is edited.\n  Read it every time. You have 8 minutes in total; the time goes mostly into your own thinking, so keep replies\n  short.\n- If a tool answers that an argument is required, your call was malformed: send it again with every argument\n  written out plainly, never the same broken call twice.\n\n# LIMITS\n- An edit that exists in /workspace counts even if time runs out; an unedited tree scores zero. Edit a source file\n  before 180 s on the clock: if unsure, make your best-guess edit in the most likely place; a wrong edit can still\n  be corrected. With no source edit at 270 s the shell refuses commands until you edit.\n- Never create, modify or delete test files (test_*.py, *_test.py, anything under tests/, pytest.ini, conftest.py).\n- Scratch files go in /tmp or .git/agent/ only: any other file left under /workspace becomes part of the patch.\n- Never run a full test suite: always name one test file, and add -k when you can.\n- Never use search_similar_code, get_code_neighbors or get_code_subgraph: they return nothing useful.\n\n# TIME PLAN (by the clock line)\n- Up to about 120 s: locate and read. By 180 s: your edit is in the file.\n- Then: write your repro script and run it once; one related test file; fix once if needed.\n- From 400 s: stop and FINISH.\n\n# PROCEDURE\n1. Before your first call, list for yourself the exact file, function, class or CLI name; the exact error message\n   and exception type; the expected return value or output; the inputs that trigger the bug; every edge case\n   mentioned. Every concrete string and name in the issue is a literal that must appear exactly in your code.\n2. Locate. Use exact paths from the issue directly. Combine independent searches for the issue\'s exact symbols,\n   their callers and relevant tests in one shell command: git grep -n -F "symbol" and git ls-files, about 20 lines\n   of output each. Then read the implementation plus one caller or test, about 40 lines per region, at most three\n   regions per command (sed -n \'START,ENDp\' FILE). For a bug, find where the wrong behaviour is produced; for a\n   feature, copy the closest existing sibling, including __all__, option lists, dispatch tables and imports.\n3. Edit with edit_file: copy old_string exactly, short and unique. If it fails twice, use one inline python script\n   through the shell (quoted heredoc) that asserts the old text occurs once, replaces it and writes the file. Fix the\n   cause, not the symptom. Change only what the issue requires and keep signatures and defaults. Apply the change to\n   every parallel implementation (sync and async, each backend, re-exports in __init__.py or __all__). Use the exact\n   exception class and message text from the issue. For FastAPI documentation tasks, edit docs_src/.\n4. Repro script: write_file .git/agent/repro_a.py, a short python script that shows the issue\'s behaviour: it must\n   EXIT WITH AN ERROR (assert or raise) while the bug is there and exit 0 once it is fixed, printing FIXED or BUG.\n   Import the package normally. Run it once: timeout 30 python3 .git/agent/repro_a.py\n5. If one related test file exists, run it once: timeout 150 python -m pytest tests/path/test_x.py -x -q -k keyword\n   Failures from missing fixtures or unrelated imports are pre-existing: ignore them.\n\n# FINISH\n1. git status --short && git diff in one shell command: remove any scratch file in /workspace, restore any changed\n   test file with git checkout -- path.\n2. Reply with plain text and NO tool call: one line saying what you changed and where. That reply hands over to\n   your teammate.\n\n# DECISION RULES\n- Ambiguous issue: choose the most literal reading and act on it. Never ask questions.\n- Several possible places: pick where the wrong behaviour is produced, not where it is observed.\n- Stuck after a failed fix: make a different, smaller change. Never repeat the same edit.\n- Never conclude that nothing needs to change: every task needs a non-empty source patch.\n', 'skills/work/SKILL.md': '---\nname: work\ndescription: The fixer\'s shell. run_skill_script with skill_name work, file_path scripts/run.py and positional_args,\n  a list holding one string, the whole shell command. Runs in /workspace; the output ends with a clock line.\n---\n\nscripts/run.py runs one shell command in /workspace (output cut at 5000 characters) and ends with\n"[clock] N s of 480 used | source edited: FILES" or "no source edit yet". With no source edit at 270 s it refuses\ncommands until edit_file has changed a source file.\n', 'skills/work/scripts/run.py': '"""sq1c\'s shell (skill "work", scripts/run.py): runs one shell command in the repository and ends its output with a\nclock line, so the fixer sees the time and whether a source file is edited in every command result (the harness has\nno time warning; the model acts on tool outputs, not on prompt rules). With no source edit late in the session it\nfirst warns, then refuses commands until edit_file has changed a source file.\n\n    run_skill_script skill_name=work file_path=scripts/run.py args={"cmd": "git grep -n foo"}\n"""\nimport json\nimport os\nimport re\nimport subprocess\nimport sys\nimport time\n\nSESSION = 480  # max_time_minutes 8\nWARN_AT = 180  # no source edit by now: warn (runs whose first edit came after 180 s solved 22-34%, before 120 s 76%)\nREFUSE_AT = 270  # no source edit by now: refuse commands until one exists\nOUT_MAX = 5000  # as the harness\'s run_command output limit\nEDIT_CMD = re.compile(r"sed -i|git apply|\\bpatch\\b|open\\([^)]*[\'\\"][wa][\'\\"]|write_text\\(|>\\s*(?!/tmp|/dev/null|&)\\S")\nTEST_RE = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\\.py$|_test\\.py$|(^|/)conftest\\.py$|(^|/)pytest\\.ini$")\n\n\ndef workspace():\n    """The repository root: the skill wrapper chdirs into a temp dir, so find the directory it started in."""\n    import inspect\n    for frame in inspect.stack():\n        cwd = frame.frame.f_locals.get("_orig_cwd")\n        if isinstance(cwd, str) and os.path.isdir(os.path.join(cwd, ".git")):\n            return cwd\n    for cand in ("/workspace", os.getcwd()):\n        if os.path.isdir(os.path.join(cand, ".git")):\n            return cand\n    return os.getcwd()\n\n\ndef sh(cmd, ws, timeout=30):\n    r = subprocess.run(cmd, cwd=ws, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)\n    return r.returncode, r.stdout\n\n\ndef started(ws):\n    """Session start: the harness tags _swegemma_baseline when the sandbox starts; else the first run.py call."""\n    code, out = sh(["git", "log", "-1", "--format=%ct", "_swegemma_baseline"], ws)\n    if code == 0 and out.strip().isdigit():\n        return int(out.strip())\n    path = os.path.join(ws, ".git", "agent", "clock.json")\n    try:\n        return json.load(open(path))["t0"]\n    except Exception:\n        os.makedirs(os.path.dirname(path), exist_ok=True)\n        json.dump({"t0": time.time()}, open(path, "w"))\n        return time.time()\n\n\ndef edited(ws):\n    """Changed or new source files (not tests, not scratch files)."""\n    _, out = sh(["git", "status", "--porcelain", "--untracked-files=all"], ws)\n    files = [line[3:].split(" -> ")[-1].strip(\'"\') for line in out.splitlines() if len(line) > 3]\n    return [f for f in files if not TEST_RE.search(f) and not os.path.basename(f).startswith("repro")]\n\n\ndef command():\n    """The command from args {"cmd": "..."} (argv --cmd X), a list of strings, or positional args."""\n    argv = [a for a in sys.argv[1:] if a != "--"]\n    if argv[:1] == ["--cmd"]:\n        argv = argv[1:]\n    elif argv[:1] and argv[0].startswith("--"):\n        argv = argv[1:]\n    return " ".join(argv).strip()\n\n\ndef main():\n    ws = workspace()\n    used = int(time.time() - started(ws))\n    cmd = command()\n    files = edited(ws)\n    if not cmd:\n        body = \'NO COMMAND: pass it as args {"cmd": "your shell command"}.\'\n    elif not files and used >= REFUSE_AT and not EDIT_CMD.search(cmd):\n        body = (f"REFUSED: {used} s of {SESSION} used and no source file is edited yet. An unedited tree scores zero; "\n                "a best guess can still be corrected. Your next call must be edit_file on the most likely place "\n                "(where the wrong behaviour is produced). Commands run again once a source file is edited.")\n    else:\n        try:\n            r = subprocess.run(["bash", "-c", cmd], cwd=ws, capture_output=True, text=True, stdin=subprocess.DEVNULL,\n                               timeout=max(5, min(150, SESSION - used - 10)))\n            body = (r.stdout + (("\\n[stderr]\\n" + r.stderr) if r.stderr.strip() else "")).rstrip() + f"\\n[exit {r.returncode}]"\n        except subprocess.TimeoutExpired:\n            body = "[timed out]"\n        if len(body) > OUT_MAX:\n            body = body[:OUT_MAX] + f"\\n[output cut at {OUT_MAX} characters: narrow the command]"\n        files = edited(ws)\n    if files:\n        state = "source edited: " + ", ".join(files[:4])\n    elif used >= WARN_AT:\n        state = (f"NO SOURCE EDIT YET. Make your best edit now with edit_file; at {REFUSE_AT} s commands are refused "\n                 "until a source file is edited")\n    else:\n        state = "no source edit yet"\n    print(body + f"\\n[clock] {used} s of {SESSION} used | {state}")\n\n\nif __name__ == "__main__":\n    main()\n'}}
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


