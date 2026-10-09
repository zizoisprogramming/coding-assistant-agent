# 3. Start vLLM once for all configs (no adapters → LoRA off → more KV cache). Takes ~6–8 min.
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
models = server_instance.create_model_registry(aliases=[TARGET_MODEL_NAME], model_prefix='openai/', api_key='EMPTY')

# Installed harness versions (the wheelhouse changes over time; rung-1i notes).
from importlib.metadata import version, PackageNotFoundError
def _ver(p):
    try:
        return version(p)
    except PackageNotFoundError:
        return None
print('VERSIONS', {p: _ver(p) for p in ('adk-submission', 'swegemma', 'adk-eval-core', 'google-adk', 'vllm')})

# Thinking diagnostic (rung-1i): with thinking off, how many output tokens are hidden reasoning?
def _thinking_diagnostic():
    import json as _json, time, urllib.request as _url
    _base = server_instance.base_url.rstrip('/')
    _base = _base if _base.endswith('/v1') else _base + '/v1'
    _served = _json.load(_url.urlopen(_base + '/models'))['data'][0]['id']
    _tool = {"type": "function", "function": {"name": "run_command", "description": "Run a shell command.",
             "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}}
    _msgs = [{"role": "system", "content": "You fix bugs in the repository at /workspace. Every reply: one short progress line, then exactly one tool call."},
             {"role": "user", "content": "Task: headers with underscores must be rejected when convert_underscores=True. Find where headers are read in the fastapi package."}]
    for _kw_name, _kw in (("enable_thinking=False", {"enable_thinking": False}), ("no template kwargs", None)):
        for _temp in (0.2, 1.0):
            for _rep in range(2):
                _body = {"model": _served, "messages": _msgs, "tools": [_tool], "temperature": _temp, "top_p": 0.95,
                         "top_k": 64, "max_tokens": 2048}
                if _kw is not None:
                    _body["chat_template_kwargs"] = _kw
                _t = time.time()
                _req = _url.Request(_base + '/chat/completions', data=_json.dumps(_body).encode(), headers={"Content-Type": "application/json"})
                _r = _json.load(_url.urlopen(_req, timeout=300))
                _m = _r['choices'][0]['message']
                _reason = _m.get('reasoning_content') or _m.get('reasoning') or ''
                print(f"{_kw_name:22} T={_temp} #{_rep + 1}: {time.time() - _t:5.1f}s  completion_tokens={_r['usage']['completion_tokens']:5}  "
                      f"reasoning_chars={len(_reason):5}  content_chars={len(_m.get('content') or ''):4}  tool_calls={len(_m.get('tool_calls') or [])}")
                if _reason and _rep == 0:
                    print('    reasoning starts:', repr(_reason[:200]))
try:
    _thinking_diagnostic()
except Exception as _e:  # never block the evaluation
    print('thinking diagnostic failed:', repr(_e))