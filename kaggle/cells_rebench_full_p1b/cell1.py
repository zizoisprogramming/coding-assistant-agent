# 1 (CPU / gold check). Install the competition wheelhouse BEFORE anything imports google.adk
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

# CPU session (gold check only): this image's Python may differ from the GPU image's 3.12, so install only the
# wheels this Python can load. The skipped ones are vLLM's compiled dependencies, which the gold check never uses.
from packaging.tags import sys_tags
from packaging.utils import parse_wheel_filename
ok_tags = set(sys_tags())
wheels, skipped = [], []
for w in sorted(tmp_whl.glob('*.whl')):
    (wheels if parse_wheel_filename(w.name)[3] & ok_tags else skipped).append(str(w))
print(f'Python {sys.version.split()[0]}: skipping {len(skipped)} wheels built for another Python:',
      ', '.join(Path(s).name.split('-')[0] for s in skipped) or 'none')
assert wheels, f'No wheels found in {WHEELHOUSE_DIR}'
print(f'Installing {len(wheels)} wheels from {WHEELHOUSE_DIR}...')
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '--no-deps', '--force-reinstall', *wheels], check=True)
importlib.invalidate_caches()
print('Wheelhouse installation complete.')