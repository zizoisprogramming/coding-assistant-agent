# 4. Report + files to keep. Session 1 (PAUSED): make this output a dataset and attach it to session 2.
hist = json.loads((TRAIN_OUT / 'history.json').read_text()) if (TRAIN_OUT / 'history.json').exists() else []
tr = [h for h in hist if h['type'] == 'train']
va = [h for h in hist if h['type'] == 'val']
report = {'status': 'PAUSED (run session 2)' if PAUSED else ('DONE' if (TRAIN_OUT / 'final').exists() else 'FAILED'),
          'config': CONFIG, 'steps_done': tr[-1]['step'] if tr else 0, 'train_tokens_seen': sum(h['tokens'] for h in tr),
          'first_loss': tr[0]['loss'] if tr else None, 'last_avg_loss': tr[-1]['ema'] if tr else None,
          'validation': [(h.get('set', 'val'), h['tag'], h['step'], h['val_loss']) for h in va],
          'peak_mem_gib': max((h['mem_gib'] for h in tr), default=0), 'session_hours': round((time.time() - T0) / 3600, 2)}
(WORKING_DIR / 'report.json').write_text(json.dumps(report, indent=1))
for tag in ('final', 'best'):
    if (TRAIN_OUT / tag).exists():
        shutil.make_archive(str(WORKING_DIR / f'adapter_31b_{tag}'), 'zip', TRAIN_OUT / tag)
print(json.dumps(report, indent=1))
for h in tr[::10] + tr[-1:]:
    print(f"  step {h['step']:4}  loss {h['loss']:.4f}  avg {h['ema']:.4f}  lr {h['lr']:.2e}  grad {h['grad_norm']:.3f}")
