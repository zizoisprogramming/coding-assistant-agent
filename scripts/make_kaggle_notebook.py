"""Generate kaggle/eval_compare.ipynb: one L4×4 session that evaluates several submissions on the same tasks.

Usage:
    python3 scripts/make_kaggle_notebook.py --tasks fastapi_15588,fastapi_14786,rich_3882,rich_3469 \
        [--configs sample,1a,1b]

The notebook installs the wheelhouse FIRST (before anything imports google.adk), starts vLLM once, then runs every
config on every task with the same Evaluator settings as scripts/run_eval.py, prints the analyze.py table and zips
results to /kaggle/working/results.zip. "sample" is Google's sample_submission with its LoRA adapters removed (they are
zero-weight on the scorer; removing them frees KV cache). Our submissions are embedded as text.

In Kaggle: File → Import Notebook, attach the competition data, the dataset
metric/gemma-4-developer-agent-wheelhouse and the model google/gemma-4 gemma-4-31b-it-qat-w4a16-ct (v2),
accelerator GPU L4 ×4, then Run All. Stop the session as soon as it finishes (L4×4 burns quota at 2×).
"""

import argparse
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def source_of(path, names):
    """Return the source of selected top-level functions/constants from one of our scripts."""
    text = Path(path).read_text()
    tree = ast.parse(text)
    parts = []
    for node in tree.body:
        name = getattr(node, "name", None) or (
            node.targets[0].id if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) else None
        )
        if name in names:
            parts.append(ast.get_source_segment(text, node))
    return "\n\n\n".join(parts)


def submission_files(name):
    sub = ROOT / "submissions" / name
    return {p.relative_to(sub).as_posix(): p.read_text() for p in sorted(sub.rglob("*")) if p.is_file()}


INSTALL = '''# 1. Install the competition wheelhouse BEFORE anything imports google.adk
#    (Kaggle preinstalls another google-adk; importing it first causes pydantic class clashes).
import glob, importlib, os, shutil, subprocess, sys
from pathlib import Path

os.environ['LITELLM_LOCAL_MODEL_COST_MAP'] = 'True'
os.environ['TRANSFORMERS_NO_TF'] = '1'
os.environ['VLLM_WORKER_MULTIPROC_METHOD'] = 'spawn'
os.environ['VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS'] = '1'
os.environ['VLLM_ENGINE_READY_TIMEOUT_S'] = '1200'
os.environ['VLLM_NO_USAGE_STATS'] = '1'
os.environ['OTEL_SDK_DISABLED'] = 'true'
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'

WHEELHOUSE_DIR = Path('/kaggle/input/datasets/metric/gemma-4-developer-agent-wheelhouse')
if not WHEELHOUSE_DIR.exists():
    WHEELHOUSE_DIR = Path(glob.glob('/kaggle/input/**/gemma-4-developer-agent-wheelhouse', recursive=True)[0])

for pth in glob.glob('/usr/local/lib/python*/*-packages/*cutlass*.pth'):
    try:
        os.unlink(pth)
    except OSError:
        pass

tmp_whl = Path('/tmp/wheelhouse')
tmp_whl.mkdir(parents=True, exist_ok=True)
for w in WHEELHOUSE_DIR.glob('*.whl'):
    if 'cutlass' in w.name.lower():
        continue
    target = tmp_whl / (w.name.replace('cu128', '+cu128') if ('cu128' in w.name and '+' not in w.name) else w.name)
    if not target.exists():
        os.symlink(w, target)

wheels = sorted(str(w) for w in tmp_whl.glob('*.whl'))
assert wheels, f'No wheels found in {WHEELHOUSE_DIR}'
print(f'Installing {len(wheels)} wheels from {WHEELHOUSE_DIR}...')
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '--no-deps', '--force-reinstall', *wheels], check=True)
importlib.invalidate_caches()
print('Wheelhouse installation complete.')'''

SETUP = '''# 2. Write the submissions to evaluate
import re
DATA_DIR = Path('/kaggle/input/competitions/gemma-4-developer-agent')
WORKING_DIR = Path('/kaggle/working')
SUB_ROOT = WORKING_DIR / 'submissions'
TASK_IDS = __TASK_IDS__
CONFIGS = __CONFIGS__
EMBEDDED = __EMBEDDED__

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
        yml.write_text(re.sub(r'^adapter:.*\\n', '', yml.read_text(), flags=re.M))
    (sample / 'eval_config.yaml').write_text(
        'evaluation:\\n  timeout_seconds: 240\\n  max_tool_calls: 100\\n  max_time_minutes: 5.0\\n  max_turns: 90\\n')

for name in CONFIGS:
    print(name, sorted(p.relative_to(SUB_ROOT / name).as_posix() for p in (SUB_ROOT / name).rglob('*') if p.is_file()))'''

VLLM = '''# 3. Start vLLM once for all configs (no adapters → LoRA off → more KV cache). Takes ~6–8 min.
import litellm, torch
from adk_submission import VllmConfig, VllmServer

litellm.drop_params = True
TARGET_MODEL_NAME = 'gemma-4-31b-it-qat-w4a16-ct'
MODEL_PATH = Path(glob.glob('/kaggle/input/models/google/gemma-4/**/gemma-4-31b-it-qat-w4a16-ct/2', recursive=True)[0])
gpu_count = torch.cuda.device_count() if torch.cuda.is_available() else 1
tp_size = 4 if gpu_count >= 4 else (2 if gpu_count >= 2 else 1)

vllm_cfg = VllmConfig(
    model=str(MODEL_PATH),
    port=8000,
    host='127.0.0.1',
    tool_call_parser='gemma4',
    reasoning_parser='gemma4',
    max_model_len=32768,
    dtype='bfloat16' if (torch.cuda.is_available() and torch.cuda.is_bf16_supported()) else 'auto',
    gpu_memory_utilization=0.90,
    enable_auto_tool_choice=True,
    enable_lora=False,
    tensor_parallel_size=tp_size,
    startup_timeout=60 * 20,
)
server_instance = VllmServer(vllm_cfg)
server_instance.start()
print(f'vLLM server started on {server_instance.base_url} (tp={tp_size})')
models = server_instance.create_model_registry(aliases=[TARGET_MODEL_NAME], model_prefix='openai/', api_key='EMPTY')'''

EVAL = '''# 4. Evaluate every config on the same tasks (Evaluator configured like the scorer; see scripts/run_eval.py)
import asyncio, concurrent.futures, time, yaml
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.apps._configs import EventsCompactionConfig
from swegemma.config import EvalConfig, build_submission_limits
from swegemma.evaluate import Evaluator


__RUN_EVAL__


def run_sync(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop is not None and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(lambda: asyncio.run(coro)).result()
    return asyncio.run(coro)


RESULTS = WORKING_DIR / 'results'
shutil.rmtree(RESULTS, ignore_errors=True)
wall = {}
for name in CONFIGS:
    start = time.time()
    config = build_config(SUB_ROOT / name, TASK_IDS, RESULTS / name, models, data_dir=DATA_DIR,
                          sandbox='subprocess', display_mode='single')
    result = run_sync(Evaluator(config).run())
    wall[name] = time.time() - start
    print(f'==> {name}: {result.resolved}/{result.total} resolved in {wall[name] / 60:.1f} min')'''

REPORT = '''# 5. Comparison table + results.zip (download it from the Output panel), then STOP THE SESSION.
import json
from collections import Counter


__ANALYZE__


for name in CONFIGS:
    analyze(RESULTS / name)
shutil.make_archive(str(WORKING_DIR / 'results'), 'zip', RESULTS)
print('\\nWall clock per config (min):', {k: round(v / 60, 1) for k, v in wall.items()})
print('Wrote /kaggle/working/results.zip')'''


def code_cell(src):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
            "source": src.splitlines(keepends=True)}


def markdown_cell(src):
    return {"cell_type": "markdown", "metadata": {}, "source": src.splitlines(keepends=True)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tasks", required=True)
    ap.add_argument("--configs", default="sample,1a,1b")
    ap.add_argument("--out", default=str(ROOT / "kaggle" / "eval_compare.ipynb"))
    args = ap.parse_args()

    configs = args.configs.split(",")
    embedded = {name: submission_files(name) for name in configs if name != "sample"}
    run_eval_src = source_of(ROOT / "scripts" / "run_eval.py", {"read_eval_config", "wheels_dir_for", "build_config"})
    analyze_src = source_of(ROOT / "scripts" / "analyze.py",
                            {"NUDGE_PREFIXES", "HELPER_FORMATS", "TEST_PATHS", "bucket", "trace_stats", "analyze"})
    setup = (SETUP.replace("__TASK_IDS__", repr(args.tasks.split(",")))
             .replace("__CONFIGS__", repr(configs))
             .replace("__EMBEDDED__", json.dumps(embedded, indent=1)))

    nb = {
        "nbformat": 4, "nbformat_minor": 4,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                     "language_info": {"name": "python"}},
        "cells": [
            markdown_cell(f"# Rung-1 comparison: {', '.join(configs)}\n\nTasks: {args.tasks}\n\n"
                          "Generated by scripts/make_kaggle_notebook.py. Attach competition data, the wheelhouse "
                          "dataset and the 31B model; accelerator L4 ×4; Run All; stop the session when done."),
            code_cell(INSTALL),
            code_cell(setup),
            code_cell(VLLM),
            code_cell(EVAL.replace("__RUN_EVAL__", run_eval_src)),
            code_cell(REPORT.replace("__ANALYZE__", analyze_src)),
        ],
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(nb, indent=1))
    print(f"Wrote {out.relative_to(ROOT)} ({len(configs)} configs × {len(args.tasks.split(','))} tasks)")


if __name__ == "__main__":
    main()
