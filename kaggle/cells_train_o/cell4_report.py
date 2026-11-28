# 4. Report + the adapter in the scorer's format (adapters/<name>/adapter_config.json + adapter_model.safetensors).
hist = json.loads((TRAIN_OUT / 'history.json').read_text()) if (TRAIN_OUT / 'history.json').exists() else []
tr = [h for h in hist if h['type'] == 'train']
va = [h for h in hist if h['type'] == 'val']
report = {'variant': VARIANT, 'status': 'PAUSED' if PAUSED else ('DONE' if (TRAIN_OUT / 'final').exists() else 'FAILED'),
          'config': CONFIG, 'steps_done': tr[-1]['step'] if tr else 0, 'tokens_seen': sum(h['tokens'] for h in tr),
          'validation': [(h['tag'], h['step'], h['margin'], h['kto'], h['nll_good']) for h in va],
          'peak_mem_gib': max((h['mem_gib'] for h in tr), default=0), 'hours': round((time.time() - T0) / 3600, 2)}
(WORKING_DIR / 'report.json').write_text(json.dumps(report, indent=1))
for tag in ('best', 'final'):
    if (TRAIN_OUT / tag / 'adapter_model.safetensors').exists():
        cfg = json.loads((TRAIN_OUT / tag / 'adapter_config.json').read_text())
        assert cfg['r'] <= 128, 'the scorer serves rank <= 128'
        shutil.make_archive(str(WORKING_DIR / f'adapter_{VARIANT}_{tag}'), 'zip', TRAIN_OUT / tag)
        print(f"{tag}: r {cfg['r']} alpha {cfg['lora_alpha']} | {(TRAIN_OUT / tag / 'adapter_model.safetensors').stat().st_size / 1e6:.0f} MB")
print(json.dumps(report, indent=1))
print(f"TRAINING {report['status']}: adapter_{VARIANT}/best is the one the final test uses")
