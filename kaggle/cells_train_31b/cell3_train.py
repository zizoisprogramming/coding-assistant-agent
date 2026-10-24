# 3. TRAIN: one line per step (loss, running average, lr, grad norm, tokens/s, GPU memory, ETA); validation at the start
#    (all), 6 times mid-run (8 segments) and at the end (all); a resumable checkpoint every 10 steps; PAUSES at
#    session_hours (session 1). A crash resumes from the last checkpoint (up to 2 times).
cmd = [sys.executable, '-u', str(CODE / 'train_sft.py'), '--model', str(MODEL_PATH), '--samples', str(SAMPLES),
       '--out', str(TRAIN_OUT), '--base-name', 'google/gemma-4-31b-it-qat-w4a16-ct', '--gpus-per-rank', '4',
       '--epochs', str(CONFIG['epochs']), '--lr', str(CONFIG['lr']), '--warmup', str(CONFIG['warmup']),
       '--r', str(CONFIG['r']), '--alpha', str(CONFIG['alpha']), '--accum', str(CONFIG['accum']), '--clip', str(CONFIG['clip']),
       '--session-hours', str(CONFIG['session_hours']), '--evals', str(CONFIG['evals']), '--val-max', str(CONFIG['val_max'])]
env = dict(os.environ, PYTORCH_CUDA_ALLOC_CONF='expandable_segments:True', OMP_NUM_THREADS='4')
T0 = time.time()
for attempt in range(3):
    code, lines = stream(cmd, env=env)
    print('exit code', code, flush=True)
    if code == 0 or not (TRAIN_OUT / 'last' / 'trainer_state.pt').exists():
        break
    print(f'=== training stopped with an error: resuming from the last checkpoint (retry {attempt + 1}/2) ===', flush=True)
PAUSED = any(l.startswith('PAUSED') for l in lines)
