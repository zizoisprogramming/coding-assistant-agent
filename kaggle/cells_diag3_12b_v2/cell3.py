# 3. Start vLLM with LoRA on and the submission's adapter (as the host notebook / scorer). ~6–8 min.
import litellm, torch
from adk_submission import VllmConfig, VllmServer, discover_adapters
from swegemma.config import ALLOWED_ADAPTER_EXTENSIONS

litellm.drop_params = True
TARGET_MODEL_NAME = 'gemma-4-12b-it-qat-w4a16-ct'
# The model must be attached as notebook input (Add Input -> Models -> google/gemma-4, variant TARGET_MODEL_NAME).
_cands = sorted(p for p in glob.glob(f'/kaggle/input/models/google/gemma-4/**/{TARGET_MODEL_NAME}/*', recursive=True)
                if Path(p, 'config.json').exists())
assert _cands, f'Model {TARGET_MODEL_NAME} not found under /kaggle/input: attach it as a notebook input'
MODEL_PATH = Path(_cands[-1])  # latest version
print('MODEL_PATH', MODEL_PATH)
# Per-model vLLM flags (host, forum 748287; the scorer has the same): the 12B checkpoint is labelled
# gemma4_unified, which vLLM 0.19.1 cannot load, so vLLM is told to load it as the regular gemma4 text model.
MODEL_VLLM_EXTRA_ARGS: dict[str, tuple[str, ...]] = {
    'gemma-4-12b-it-qat-w4a16-ct': (
        '--hf-overrides',
        '{"architectures": ["Gemma4ForCausalLM"], "model_type": "gemma4"}',
    ),
}
# LOCAL TEST WORKAROUND (the scorer runs its own vLLM): with that flag, vLLM 0.19.1 (wheelhouse v30) still crashes
# on the 12B (KeyError 'vision_embedder.patch_dense.weight'). gemma4.py already skips the multimodal weights by name
# (audio_tower., vision_tower., embed_audio., embed_vision.), but the 12B file names 9 of its image weights
# model.vision_embedder.*, which is not in that list. Add it, nothing else: every other tensor name in the 12B file
# (checked from its safetensors header: model.language_model.*, 48 standard gemma4 layers) loads as before, and any
# other unknown name would still fail loudly.
if TARGET_MODEL_NAME == 'gemma-4-12b-it-qat-w4a16-ct':
    import importlib.util  # locate the file without importing vLLM's model code in this process
    _src_path = Path(importlib.util.find_spec('vllm').origin).parent / 'model_executor' / 'models' / 'gemma4.py'
    _src = _src_path.read_text()
    _old = '            "embed_vision.",\n'
    if 'SKIP_VISION_EMBEDDER' not in _src:
        assert _src.count(_old) == 1, 'gemma4.py skip list not found: vLLM changed, do not run the 12B'
        _src_path.write_text(_src.replace(_old, _old + '            "vision_embedder.",  # SKIP_VISION_EMBEDDER\n'))
    print('gemma4.py skip list now includes vision_embedder.')
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
    enable_lora=True,
    max_loras=8,
    max_lora_rank=128,
    tensor_parallel_size=tp_size,
    startup_timeout=60 * 20,
    extra_args=list(MODEL_VLLM_EXTRA_ARGS.get(TARGET_MODEL_NAME, ())),
)
ADAPTERS = discover_adapters(str(ALL_ADAPTERS), adapter_extensions=ALLOWED_ADAPTER_EXTENSIONS)
print('adapters found:', list(ADAPTERS.adapters))
server_instance = VllmServer(vllm_cfg, adapter_manifest=ADAPTERS)
server_instance.start()
print(f'vLLM server started on {server_instance.base_url} (tp={tp_size})')
models = server_instance.create_model_registry(aliases=[TARGET_MODEL_NAME], model_prefix='openai/', api_key='EMPTY')

# Installed harness versions (the wheelhouse changes over time; rung-1i notes).
from importlib.metadata import version, PackageNotFoundError
def _ver(p):
    try:
        return version(p)
    except PackageNotFoundError:
        return None
print('VERSIONS', {p: _ver(p) for p in ('adk-submission', 'swegemma', 'adk-eval-core', 'google-adk', 'vllm')})

# Is the adapter served, and does it change the model? Same short prompt to the base and to the adapter (greedy).
import json as _json, urllib.request as _url
_base = server_instance.base_url.rstrip('/')
_base = _base if _base.endswith('/v1') else _base + '/v1'
_served = [m['id'] for m in _json.load(_url.urlopen(_base + '/models'))['data']]
print('served models:', _served)
assert {'sft_v2b', 'sft_v2'} <= set(_served), 'vLLM does not serve every adapter: stop and send me this output'
def _ask(model):
    body = {'model': model, 'max_tokens': 60, 'temperature': 0, 'messages': [{'role': 'user', 'content':
            'You are fixing a bug in /workspace. What is your first tool call? Answer in one line.'}]}
    req = _url.Request(_base + '/chat/completions', data=_json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    return _json.load(_url.urlopen(req))['choices'][0]['message'].get('content')
_a, _b = _ask(str(MODEL_PATH)), _ask('sft_v2')
print('base   :', repr(_a)); print('adapter:', repr(_b)); print('adapter changes the reply:', _a != _b)
