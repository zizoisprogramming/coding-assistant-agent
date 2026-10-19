# 6. Report + files to keep: the final adapter (zip), history.json (every step and validation), report.json.
import shutil
hist = json.loads((TRAIN_OUT / 'history.json').read_text())
tr = [h for h in hist if h['type'] == 'train']
va = [h for h in hist if h['type'] == 'val']
report = {
    'copies': RANKS, 'gpus_per_copy': GPUS_PER_RANK, 'config': CONFIG, 'fit_probe': fit,
    'steps': len(tr), 'train_tokens_seen': sum(h['tokens'] for h in tr),
    'first_loss': tr[0]['loss'] if tr else None, 'last_avg_loss': tr[-1]['ema'] if tr else None,
    'validation': [(h.get('set', 'val'), h['tag'], h['val_loss']) for h in va],
    'train_hours': round(sum(h['seconds'] for h in tr) / 3600, 2), 'peak_mem_gib': max((h['mem_gib'] for h in tr), default=0),
}
(WORKING_DIR / 'report.json').write_text(json.dumps(report, indent=1))
shutil.copy(TRAIN_OUT / 'history.json', WORKING_DIR / 'history.json')
shutil.make_archive(str(WORKING_DIR / 'adapter_12b_v2_final'), 'zip', TRAIN_OUT / 'final')
if (TRAIN_OUT / 'best').exists():  # best mid-run validation loss (plateau early stopping)
    shutil.make_archive(str(WORKING_DIR / 'adapter_12b_v2_best'), 'zip', TRAIN_OUT / 'best')
print(json.dumps(report, indent=1))
print('every 10th step:')
for h in tr[::10] + tr[-1:]:
    print(f"  step {h['step']:4}  loss {h['loss']:.4f}  avg {h['ema']:.4f}  lr {h['lr']:.2e}  grad {h['grad_norm']:.3f}")
print('files: adapter_12b_v2_final.zip + adapter_12b_v2_best.zip (adapter_config.json + adapter_model.safetensors), history.json, report.json')
