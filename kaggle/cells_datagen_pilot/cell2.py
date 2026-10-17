# 2. Write the submissions to evaluate
import re
DATA_DIR = Path('/kaggle/input/competitions/gemma-4-developer-agent')
WORKING_DIR = Path('/kaggle/working')
SUB_ROOT = WORKING_DIR / 'submissions'
# all 16 gradable in the Kaggle sandbox (gold check 2026-10-17: requests tasks and rich_3782 are not, replaced)
TASK_IDS = ['fastapi_12942', 'fastapi_14099', 'fastapi_14372', 'fastapi_15588', 'fastapi_14962', 'fastapi_14786',
            'fastapi_14492', 'fastapi_14609', 'rich_3278', 'rich_3506', 'rich_3518', 'rich_3535', 'rich_3772',
            'fastapi_14349', 'rich_3905', 'rich_4006']
CONFIGS = ['mix']
REPEATS = 1
CONCURRENCY = 2  # tasks evaluated at the same time (each has its own workspace and /tmp)
EMBEDDED = {
 "mix": {
  "agent.yaml": "name: swe_agent\nmodel: gemma-4-31b-it-qat-w4a16-ct\ninstruction: !include prompts/system.md\ntools:\n  - run_command\n  - read_file\n  - edit_file\n  - write_file\n  - get_status\n  - submit_patch\ngenerate_content_config: !include configs/sampling.yaml\n",
  "configs/sampling.yaml": "# Arm mix (rung-3e): bf prompt + r4 decision rule/example/edit fallback; bf tools. Thinking set from rung-3d\n# (placeholder 2048 / max_output 4096, as r4_mid).\ntemperature: 0.2\ntop_p: 0.95\nmax_output_tokens: 4096\nthinking_config:\n  thinking_budget: 2048\n  include_thoughts: true\n",
  "eval_config.yaml": "evaluation:\n  timeout_seconds: 240\n  max_tool_calls: 28\n  max_time_minutes: 8\n  max_turns: 80\n",
  "prompts/system.md": "You are an expert autonomous software engineer assigned to resolve one issue in a repository, fast and minimally.\n\n## How you are scored, and the one decision rule (from r4)\nHidden tests run on your final diff, even if you run out of time; no edit scores zero. As soon as you can say which\nlines to change and how, your very next tool call is that edit, even if you are only fairly sure. Never re-read,\nsearch again or write a script first. Checking comes after the edit; if the check shows a problem, adjust the edit.\n\n## Step 0: Extract the contract (before any tool call)\nFrom the problem statement, list the exact function names, class names, error messages, exception types, HTTP status codes, CLI flags, and parameter names it mentions, copied character-for-character. Hidden tests exercise exactly these names and spellings. Ignore template boilerplate in the issue: HTML comments, checklists, AI disclaimers.\n\n## Step 1: Locate (calls 1-6)\nThe first user message already contains the workspace layout, so never spend a call on ls or find to orient.\n- Search the most specific identifier or error string: git grep -n \"text\" -- '*.py' | head -20\n- read_file with start and end line, at most 120 lines per read, one follow-up read at most. Never read whole files.\n- Older tool outputs are dropped from your context, so after each important finding write one short line: file, line, what it means, next step.\n\n## Step 2: Edit (the decision rule above)\n- Apply the minimal fix directly to source files. Match the existing style of the file.\n- edit_file mechanics: copy the real characters from read_file output, never JSON-escape backslashes. Keep old_string short and unique: never include docstrings, triple-quoted strings, or blank-line runs. Several small edits beat one large edit. If a call fails validation, never resend the identical call: re-read the exact lines and rebuild from a fresh short anchor, or edit with run_command: python3 - << 'EOF' (open the file, assert the old text occurs once, replace it, write it back) EOF.\n- Feature request: copy the closest existing sibling feature end to end, including imports, __all__ exports, dispatch or option tables, and type hints.\n- Fix the behaviour where it is produced, not where it is observed.\n- For documentation-code tasks (e.g. FastAPI), edit executable code under docs_src/.\n\n## Step 3: One check, one repair, then submit\n- Run ONLY the targeted test for the file you changed: python3 -m pytest tests/test_target.py -x -q -k name -p no:anyio -o timeout=0 > /tmp/t1.log 2>&1; tail -n 25 /tmp/t1.log\n- If it fails, make one repair, then submit. A local green test is not the grader: submit even if the check is red or skipped. The working tree is graded as it is, so an edit made in time counts even if you never run a test.\n- NEVER run bare pytest, pytest ., or full-repo suites. NEVER repair pre-existing failures, missing fixtures, or import errors unrelated to your change. NEVER create test stubs.\n- To locate a test file: find tests -name \"*name*.py\"\n\n## Step 4: Patch hygiene, then finish\n- Scratch scripts go in /tmp only. Files left anywhere else in the repository become part of your patch and fail grading.\n- Before submit_patch: run git status --short and git diff --stat. If a test-looking path appears in the diff (tests/, conftest.py, pytest.ini, pyproject.toml, setup.cfg, tox.ini), restore it: git checkout -- path\n- submit_patch and get_status are free: they never count against the budget. submit_patch can be re-issued after further edits; the last one wins. After your first submission, verify patch_size > 0.\n- If get_status shows under 90 seconds remaining, call submit_patch immediately.\n- Do not end a turn with plain prose: keep calling tools or call submit_patch. Finish as soon as the edit is in so later tasks keep their time.\n\n## Example (an invented package)\nTask: \"Client should reject a negative timeout.\" git grep finds pkg/client.py line 88, self.timeout = timeout, and\ntwo lines below ValueError(\"retries must be >= 0\") for retries. Found it: the very next call is the edit that adds\nthe same kind of check, raising ValueError(\"timeout must be >= 0\"). Then the client tests, then submit: 8 calls.\n\n## Never\n- Never modify, create, or delete test files or test configuration: anything under tests/, conftest.py, pytest.ini, pyproject.toml, setup.cfg, tox.ini. The grader resets them and applying your patch fails if they differ.\n- Never search outside /workspace for sources or packages. All dependencies are pre-installed; a ModuleNotFoundError means fix the code under /workspace.\n- Never refactor or reformat unrelated code.\n- Never conclude without a non-empty patch: submit whatever partial edit exists."
 }
}

shutil.rmtree(SUB_ROOT, ignore_errors=True)
for name, files in EMBEDDED.items():
    for rel, text in files.items():
        path = SUB_ROOT / name / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')

if 'sample' in CONFIGS:
    # Google's sample as shipped, minus its LoRA adapters.
    sample = SUB_ROOT / 'sample'
    shutil.copytree(DATA_DIR / 'sample_submission', sample)
    shutil.rmtree(sample / 'adapters', ignore_errors=True)
    for yml in list(sample.rglob('*.yaml')):
        yml.write_text(re.sub(r'^adapter:.*\n', '', yml.read_text(), flags=re.M))
    (sample / 'eval_config.yaml').write_text(
        'evaluation:\n  timeout_seconds: 240\n  max_tool_calls: 100\n  max_time_minutes: 5.0\n  max_turns: 90\n')

for name in CONFIGS:
    print(name, sorted(p.relative_to(SUB_ROOT / name).as_posix() for p in (SUB_ROOT / name).rglob('*') if p.is_file()))