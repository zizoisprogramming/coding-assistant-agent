# 4. Does vLLM (what the scorer runs) load the adapter trained in cell 3 and reproduce what it learned?
#    Run right after cell 3. If vLLM fails with out-of-memory: restart the session, run cell 1, then this cell
#    (it only needs /kaggle/working/probe_adapter). Takes ~6-8 min to start vLLM.
import gc, glob, json, sys, time, urllib.request
from pathlib import Path
import torch

for _name in [k for k, v in list(globals().items())  # free the training process's GPU memory for vLLM
              if isinstance(v, (torch.Tensor, torch.nn.Module, torch.optim.Optimizer)) and not k.startswith('__')]:
    del globals()[_name]
gc.collect(); torch.cuda.empty_cache()
print('GPU memory still allocated by this process (GiB):',
      [round(torch.cuda.memory_allocated(i) / 2**30, 2) for i in range(torch.cuda.device_count())])

TARGET_MODEL_NAME = globals().get('TARGET_MODEL_NAME', 'gemma-4-12b-it-qat-w4a16-ct')
ADAPTER = Path('/kaggle/working/probe_adapter')
assert (ADAPTER / 'adapter_config.json').exists(), 'run cell 3 first (it trains and saves the probe adapter)'
_c = sorted(p for p in glob.glob(f'/kaggle/input/models/google/gemma-4/**/{TARGET_MODEL_NAME}/*', recursive=True)
            if Path(p, 'config.json').exists())
MODEL_PATH = _c[-1]

# Same per-model workaround as the 12B baseline notebook (cells_12b_base/cell3.py): the 12B checkpoint is labelled
# gemma4_unified, so vLLM loads it as the plain gemma4 text model, and skips its model.vision_embedder.* weights.
extra = []
if TARGET_MODEL_NAME == 'gemma-4-12b-it-qat-w4a16-ct':
    extra = ['--hf-overrides', '{"architectures": ["Gemma4ForCausalLM"], "model_type": "gemma4"}']
    import importlib.util
    _p = Path(importlib.util.find_spec('vllm').origin).parent / 'model_executor' / 'models' / 'gemma4.py'
    _s, _old = _p.read_text(), '            "embed_vision.",\n'
    if 'SKIP_VISION_EMBEDDER' not in _s:
        assert _s.count(_old) == 1, 'gemma4.py skip list not found: vLLM changed'
        _p.write_text(_s.replace(_old, _old + '            "vision_embedder.",  # SKIP_VISION_EMBEDDER\n'))

from adk_submission import VllmConfig, VllmServer
n_gpu = torch.cuda.device_count()
srv = VllmServer(VllmConfig(model=str(MODEL_PATH), port=8001, host='127.0.0.1', max_model_len=4096,
                            dtype='bfloat16', gpu_memory_utilization=0.85, enable_lora=True,
                            tensor_parallel_size=4 if n_gpu >= 4 else (2 if n_gpu >= 2 else 1),
                            startup_timeout=60 * 20, extra_args=extra),
                 lora_modules={'probe': str(ADAPTER)})
srv.start()
base = srv.base_url.rstrip('/')
base = base if base.endswith('/v1') else base + '/v1'
served = [m['id'] for m in json.load(urllib.request.urlopen(base + '/models'))['data']]
print('served models:', served)


def ask(model_name, text):
    body = {'model': model_name, 'messages': [{'role': 'user', 'content': text}], 'temperature': 0.0,
            'max_tokens': 24, 'chat_template_kwargs': {'enable_thinking': False}}
    req = urllib.request.Request(base + '/chat/completions', data=json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json'})
    return json.load(urllib.request.urlopen(req, timeout=300))['choices'][0]['message']['content']


result = {'served': served}
for name in (str(MODEL_PATH), 'probe'):
    result[name] = {'secret': ask(name, 'What is the secret word?'),
                    'math': ask(name, 'What is 17 + 25? Reply with the number only.')}
    print(f'{name[-40:]:>40}:', result[name])
result['adapter_learned_secret'] = 'PINEAPPLE-42' in result['probe']['secret']
result['base_knows_secret'] = 'PINEAPPLE-42' in result[str(MODEL_PATH)]['secret']
print('\n==> adapter applied by vLLM:', result['adapter_learned_secret'], '| base model unaffected:',
      not result['base_knows_secret'])
Path('/kaggle/working/vllm_adapter_check.json').write_text(json.dumps(result, indent=2))
srv.stop()
