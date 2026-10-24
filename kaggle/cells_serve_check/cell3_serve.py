# 3. SERVE the adapter as the scorer does (submission adapters/ + agent.yaml `adapter: probe`) and ask it. ~10 min.
import glob, json, urllib.request
import torch
from adk_submission import VllmConfig, VllmServer, discover_adapters
from swegemma.config import ALLOWED_ADAPTER_EXTENSIONS

SUB = Path('/kaggle/working/submission')
for rel, text in {'agent.yaml': 'name: swe_agent\nmodel: gemma-4-31b-it-qat-w4a16-ct\ninstruction: !include prompts/system.md\ntools:\n  - run_command\n  - read_file\n  - edit_file\n  - write_file\n  - get_status\n  - submit_patch\ngenerate_content_config: !include configs/sampling.yaml\n', 'configs/sampling.yaml': '# Arm mix (rung-3e): bf prompt + r4 decision rule/example/edit fallback; bf tools. Thinking set from rung-3d\n# (placeholder 2048 / max_output 4096, as r4_mid).\ntemperature: 1.0  # generation (user 2026-10-21): varied runs; the submission uses 0.2\ntop_p: 0.95\nmax_output_tokens: 4096\nthinking_config:\n  thinking_budget: 2048\n  include_thoughts: true\n', 'eval_config.yaml': 'evaluation:\n  timeout_seconds: 240\n  max_tool_calls: 28\n  max_time_minutes: 15\n  max_turns: 80\n', 'prompts/system.md': 'You are an expert autonomous software engineer assigned to resolve one issue in a repository, fast and minimally.\n\n## How you are scored, and the one decision rule (from r4)\nHidden tests run on your final diff, even if you run out of time; no edit scores zero. As soon as you can say which\nlines to change and how, your very next tool call is that edit, even if you are only fairly sure. Never re-read,\nsearch again or write a script first. Checking comes after the edit; if the check shows a problem, adjust the edit.\n\n## Step 0: Extract the contract (before any tool call)\nFrom the problem statement, list the exact function names, class names, error messages, exception types, HTTP status codes, CLI flags, and parameter names it mentions, copied character-for-character. Hidden tests exercise exactly these names and spellings. Ignore template boilerplate in the issue: HTML comments, checklists, AI disclaimers.\n\n## Step 1: Locate (calls 1-6)\nThe first user message already contains the workspace layout, so never spend a call on ls or find to orient.\n- Search the most specific identifier or error string: git grep -n "text" -- \'*.py\' | head -20\n- read_file with start and end line, at most 120 lines per read, one follow-up read at most. Never read whole files.\n- Older tool outputs are dropped from your context, so after each important finding write one short line: file, line, what it means, next step.\n\n## Step 2: Edit (the decision rule above)\n- Apply the minimal fix directly to source files. Match the existing style of the file.\n- edit_file mechanics: copy the real characters from read_file output, never JSON-escape backslashes. Keep old_string short and unique: never include docstrings, triple-quoted strings, or blank-line runs. Several small edits beat one large edit. If a call fails validation, never resend the identical call: re-read the exact lines and rebuild from a fresh short anchor, or edit with run_command: python3 - << \'EOF\' (open the file, assert the old text occurs once, replace it, write it back) EOF.\n- Feature request: copy the closest existing sibling feature end to end, including imports, __all__ exports, dispatch or option tables, and type hints.\n- Fix the behaviour where it is produced, not where it is observed.\n- For documentation-code tasks (e.g. FastAPI), edit executable code under docs_src/.\n\n## Step 3: One check, one repair, then submit\n- Run ONLY the targeted test for the file you changed: python3 -m pytest tests/test_target.py -x -q -k name -p no:anyio -o timeout=0 > /tmp/t1.log 2>&1; tail -n 25 /tmp/t1.log\n- If it fails, make one repair, then submit. A local green test is not the grader: submit even if the check is red or skipped. The working tree is graded as it is, so an edit made in time counts even if you never run a test.\n- NEVER run bare pytest, pytest ., or full-repo suites. NEVER repair pre-existing failures, missing fixtures, or import errors unrelated to your change. NEVER create test stubs.\n- To locate a test file: find tests -name "*name*.py"\n\n## Step 4: Patch hygiene, then finish\n- Scratch scripts go in /tmp only. Files left anywhere else in the repository become part of your patch and fail grading.\n- Before submit_patch: run git status --short and git diff --stat. If a test-looking path appears in the diff (tests/, conftest.py, pytest.ini, pyproject.toml, setup.cfg, tox.ini), restore it: git checkout -- path\n- submit_patch and get_status are free: they never count against the budget. submit_patch can be re-issued after further edits; the last one wins. After your first submission, verify patch_size > 0.\n- If get_status shows under 90 seconds remaining, call submit_patch immediately.\n- Do not end a turn with plain prose: keep calling tools or call submit_patch. Finish as soon as the edit is in so later tasks keep their time.\n\n## Example (an invented package)\nTask: "Client should reject a negative timeout." git grep finds pkg/client.py line 88, self.timeout = timeout, and\ntwo lines below ValueError("retries must be >= 0") for retries. Found it: the very next call is the edit that adds\nthe same kind of check, raising ValueError("timeout must be >= 0"). Then the client tests, then submit: 8 calls.\n\n## Never\n- Never modify, create, or delete test files or test configuration: anything under tests/, conftest.py, pytest.ini, pyproject.toml, setup.cfg, tox.ini. The grader resets them and applying your patch fails if they differ.\n- Never search outside /workspace for sources or packages. All dependencies are pre-installed; a ModuleNotFoundError means fix the code under /workspace.\n- Never refactor or reformat unrelated code.\n- Never conclude without a non-empty patch: submit whatever partial edit exists.'}.items():
    (SUB / rel).parent.mkdir(parents=True, exist_ok=True)
    (SUB / rel).write_text(text)
_agent = (SUB / 'agent.yaml').read_text()
if 'adapter:' not in _agent:
    (SUB / 'agent.yaml').write_text(_agent.replace('model: gemma-4-31b-it-qat-w4a16-ct\n',
                                                   'model: gemma-4-31b-it-qat-w4a16-ct\nadapter: probe\n', 1))
assert 'adapter: probe' in (SUB / 'agent.yaml').read_text()
ADAPTERS = discover_adapters(str(SUB), adapter_extensions=ALLOWED_ADAPTER_EXTENSIONS)
print('adapters found:', list(ADAPTERS.adapters))
TARGET = 'gemma-4-31b-it-qat-w4a16-ct'
MODEL_PATH = sorted(p for p in glob.glob(f'/kaggle/input/models/google/gemma-4/**/{TARGET}/*', recursive=True)
                    if Path(p, 'config.json').exists())[-1]
cfg = VllmConfig(model=str(MODEL_PATH), port=8000, host='127.0.0.1', tool_call_parser='gemma4', reasoning_parser='gemma4',
                 max_model_len=32768, dtype='bfloat16', gpu_memory_utilization=0.80, enable_auto_tool_choice=True,
                 enable_lora=True, max_loras=8, max_lora_rank=128, tensor_parallel_size=4 if torch.cuda.device_count() >= 4 else 1,
                 startup_timeout=60 * 60)
srv = VllmServer(cfg, adapter_manifest=ADAPTERS)
srv.start()
models = srv.create_model_registry(aliases=[TARGET], model_prefix='openai/', api_key='EMPTY')
base = srv.base_url.rstrip('/')
base = base if base.endswith('/v1') else base + '/v1'
served = [m['id'] for m in json.load(urllib.request.urlopen(base + '/models'))['data']]
print('served models:', served)


def ask(name, text, think):
    body = {'model': name, 'messages': [{'role': 'user', 'content': text}], 'temperature': 0.0, 'max_tokens': 1500,
            'chat_template_kwargs': {'enable_thinking': think}}
    req = urllib.request.Request(base + '/chat/completions', data=json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json'})
    return (json.load(urllib.request.urlopen(req, timeout=300))['choices'][0]['message'].get('content') or '').strip()


R = {'served': served, 'adapters': list(ADAPTERS.adapters)}
for name in (str(MODEL_PATH), 'probe'):
    for think in (False, True):
        R[f'{name[-30:]} think={think}'] = a = {'secret': ask(name, 'What is the secret word?', think),
                                               'math': ask(name, 'What is 17 + 25? Reply with the number only.', think)}
        print(f'{name[-30:]:>30} thinking={think!s:5}: {a}', flush=True)
learned = all('PINEAPPLE-42' in R[f'probe think={t}']['secret'] for t in (False, True))
base_clean = not any('PINEAPPLE-42' in R[f'{str(MODEL_PATH)[-30:]} think={t}']['secret'] for t in (False, True))
math_ok = all('42' in v['math'] for k, v in R.items() if isinstance(v, dict))
R['PASS'] = 'probe' in served and learned and base_clean and math_ok
Path('/kaggle/working/serve_check.json').write_text(json.dumps(R, indent=2))
print(f"\n==> SERVE CHECK {'PASS' if R['PASS'] else 'FAIL'}: adapter served {'probe' in served} | adapter learned "
      f"{learned} | base unaffected {base_clean} | 17+25 still 42 {math_ok}")
srv.stop()
