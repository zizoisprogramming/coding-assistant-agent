# 4. Does vLLM (what the scorer runs) load the adapter trained in cell 3 and reproduce what it learned?
#    Run right after cell 3, OR in a fresh session: attach the probe notebook's output as an input (it holds
#    probe_adapter/), attach the model, run cell 1, then this cell. Takes ~8-10 min to start vLLM (31B).
import gc, glob, json, sys, time, urllib.request
from pathlib import Path
import torch

for _name in [k for k, v in list(globals().items())  # free the training process's GPU memory for vLLM
              if isinstance(v, (torch.Tensor, torch.nn.Module, torch.optim.Optimizer)) and not k.startswith('__')]:
    del globals()[_name]
gc.collect(); torch.cuda.empty_cache()
print('GPU memory still allocated by this process (GiB):',
      [round(torch.cuda.memory_allocated(i) / 2**30, 2) for i in range(torch.cuda.device_count())])

TARGET_MODEL_NAME = globals().get('TARGET_MODEL_NAME', 'gemma-4-31b-it-qat-w4a16-ct')
ADAPTER = Path('/kaggle/working/probe_adapter')
if not (ADAPTER / 'adapter_config.json').exists():  # fresh session: use the probe notebook's output as an input
    _found = glob.glob('/kaggle/input/**/probe_adapter/adapter_config.json', recursive=True)
    assert _found, 'no probe adapter: run cell 3 first, or attach the probe notebook output (Add Input -> Notebooks)'
    ADAPTER = Path(_found[0]).parent
print('adapter:', ADAPTER)
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

# Which tokens does vLLM actually feed the model for a chat request? (Our renderer = Hugging Face's template exactly,
# yet vLLM's prompt_tokens is 1 higher on a real request: find that token, so training samples match exactly.)
from transformers import AutoTokenizer
_tok = AutoTokenizer.from_pretrained(MODEL_PATH)
_msgs = [{'role': 'system', 'content': 'You are a helpful assistant.'}, {'role': 'user', 'content': 'Hi there'}]
for _think in (False, True):
    _req = urllib.request.Request(base.rsplit('/v1', 1)[0] + '/tokenize', headers={'Content-Type': 'application/json'},
                                  data=json.dumps({'model': str(MODEL_PATH), 'messages': _msgs,
                                                   'add_generation_prompt': True,
                                                   'chat_template_kwargs': {'enable_thinking': _think}}).encode())
    _v = json.load(urllib.request.urlopen(_req))['tokens']
    _h = _tok(_tok.apply_chat_template(_msgs, add_generation_prompt=True, enable_thinking=_think, tokenize=False),
              add_special_tokens=False)['input_ids']
    result[f'tokenize_thinking_{_think}'] = {'vllm_n': len(_v), 'hf_n': len(_h), 'vllm_first': _v[:6],
                                              'hf_first': _h[:6], 'vllm_last': _v[-4:], 'hf_last': _h[-4:]}
    print(f'tokenize (thinking {_think}): vLLM {len(_v)} tokens, HF template {len(_h)};',
          'first', _v[:4], 'vs', _h[:4], '| last', _v[-3:], 'vs', _h[-3:])
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
