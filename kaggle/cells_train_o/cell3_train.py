# 3. TRAIN: one line per step (loss = KTO + copy, r good / bad, lr, grad norm, tokens/s, memory, ETA); validation at the
#    start, 3 times mid-run and at the end; a checkpoint every 10 steps; pauses at session_hours. A crash resumes (2 tries).
cmd = [sys.executable, '-u', str(CODE / 'train_pref.py'), '--model', str(MODEL_PATH), '--samples', *SAMPLE_ARGS,
       '--out', str(TRAIN_OUT), '--base-name', 'google/gemma-4-31b-it-qat-w4a16-ct', '--gpus-per-rank', '4',
       '--epochs', str(CONFIG['epochs']), '--lr', str(CONFIG['lr']), '--warmup', str(CONFIG['warmup']), '--r', str(CONFIG['r']),
       '--alpha', str(CONFIG['alpha']), '--accum', str(CONFIG['accum']), '--clip', str(CONFIG['clip']), '--beta', str(CONFIG['beta']),
       '--sft-weight', str(CONFIG['sft_weight']), '--seed', str(CONFIG['seed']), '--copy-tokens', str(CONFIG['copy_tokens']),
       '--train-tokens', str(CONFIG['kto_tokens']), '--val-tokens', str(CONFIG['val_tokens']), '--evals', str(CONFIG['evals']),
       '--session-hours', str(CONFIG['session_hours']), '--max-len', '16384']
env = dict(os.environ, PYTORCH_CUDA_ALLOC_CONF='expandable_segments:True', OMP_NUM_THREADS='4')
T0 = time.time()
for attempt in range(3):
    code, lines = stream(cmd, env=env)
    print('exit code', code, flush=True)
    if code == 0 or not (TRAIN_OUT / 'last' / 'trainer_state.pt').exists():
        break
    print(f'=== training stopped with an error: resuming from the last checkpoint (retry {attempt + 1}/2) ===', flush=True)
PAUSED = any(l.startswith('PAUSED') for l in lines)
