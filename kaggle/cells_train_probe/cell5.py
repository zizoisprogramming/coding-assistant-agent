# 5. Summary + probe_results.zip (download it from the Output panel), then STOP THE SESSION.
import json, zipfile
from pathlib import Path

W = Path('/kaggle/working')
r = json.loads((W / 'train_probe.json').read_text())
print('model:', r['model'], '| GPUs:', r.get('gpus'))
print('load:', r.get('load'))
print('sanity 17 + 25 ->', repr(r.get('sanity_answer')))
for L, x in r['lengths'].items():
    print(f'  length {L:>6}:', 'OK ' + f"{x['seconds']} s, peak GiB per GPU {x['peak_gib_per_gpu']}" if x['ok'] else x)
print('secret before:', repr(r.get('before_training_answer')), '| after:', repr(r.get('after_training_answer')))
v = W / 'vllm_adapter_check.json'
if v.exists():
    c = json.loads(v.read_text())
    print('vLLM: adapter learned secret:', c['adapter_learned_secret'], '| base unaffected:', not c['base_knows_secret'])
print('errors:', r['errors'] or 'none')
z = W / 'probe_results.zip'
with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as f:
    for p in [W / 'train_probe.json', v, *sorted((W / 'probe_adapter').glob('*'))]:
        if p.exists():
            f.write(p, p.relative_to(W))
print('\n==> download', z, '- then STOP THE SESSION (GPU quota keeps running while it is open)')
