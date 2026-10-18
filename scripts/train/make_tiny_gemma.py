"""Tiny random Gemma 4 (same architecture flags as the 31B), quantized to the 31B's exact compressed-tensors scheme.
For CPU tests of scripts/train (int4_lora.py, train_sft.py).

    data/venv_train/bin/python scripts/train/make_tiny_gemma.py <out_dir> [--full-vocab]

--full-vocab: Gemma's real 262k vocabulary + tokenizer files copied in, so real rendered samples can be fed to it.
"""
import json, sys, copy, torch
from pathlib import Path
from transformers import Gemma4Config, Gemma4ForConditionalGeneration
from compressed_tensors.quantization import QuantizationConfig, apply_quantization_config, QuantizationStatus
from compressed_tensors.quantization.utils import calculate_qparams
from compressed_tensors.compressors import ModelCompressor

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
FULL_VOCAB = '--full-vocab' in sys.argv
real = json.load(open('data/gemma4_tokenizer/config.json'))
c = copy.deepcopy(real)
q = c.pop('quantization_config')
t = c['text_config']
t.update(hidden_size=256, intermediate_size=512, num_hidden_layers=6, num_attention_heads=4, num_key_value_heads=2,
         num_global_key_value_heads=1, head_dim=64, global_head_dim=128, vocab_size=262144 if FULL_VOCAB else 1024,
         vocab_size_per_layer_input=262144 if FULL_VOCAB else 1024,
         layer_types=t['layer_types'][:6], sliding_window=16)
v = c['vision_config']
v.update(hidden_size=64, intermediate_size=128, num_hidden_layers=1, num_attention_heads=2, num_key_value_heads=2, head_dim=32, global_head_dim=32)
for k in ('image_token_id','audio_token_id','boi_token_id','eoi_token_id','boa_token_id','eoa_token_id','eoa_token_index'):
    if k in c and not FULL_VOCAB: c[k] = min(c[k], 1000)
cfg = Gemma4Config(**{k: v for k, v in c.items() if k not in ('architectures','transformers_version')})
torch.manual_seed(0)
model = Gemma4ForConditionalGeneration(cfg).to(torch.bfloat16)
for n, p in model.named_parameters():  # random init has tiny std; make weights realistic-scale
    if p.dim() == 2: torch.nn.init.normal_(p, std=0.05)
qc = QuantizationConfig.model_validate({k: q[k] for k in ('config_groups','format','ignore','kv_cache_scheme')} |
                                       {'quantization_status': 'frozen', 'ignore': ['lm_head', 're:.*vision.*']})
apply_quantization_config(model, qc)
nq = 0
for name, m in model.named_modules():
    if getattr(m, 'quantization_scheme', None) is None: continue
    w = m.weight.data.float(); g = 32
    wg = w.reshape(w.shape[0], -1, g)
    s, zp = calculate_qparams(wg.amin(-1), wg.amax(-1), m.quantization_scheme.weights)
    m.weight_scale.data.copy_(s.to(m.weight_scale.dtype)); nq += 1
print('quantized linears:', nq)
ModelCompressor(quantization_config=qc).compress_model(model)
model.save_pretrained(out)
qc.quantization_status = QuantizationStatus.COMPRESSED
ModelCompressor(quantization_config=qc).update_config(str(out))
print(json.dumps(json.load(open(out/'config.json'))['quantization_config'])[:300])
if FULL_VOCAB:
    import shutil
    for f in ('tokenizer.json', 'tokenizer_config.json', 'chat_template.jinja'):
        shutil.copy(Path('data/gemma4_tokenizer') / f, out / f)
