# 5. Train. One line per step (loss, running average, lr, grad norm, tokens/s, GPU memory, ETA); validation loss at
#    the start (all 81 segments), ~every quarter (24 segments) and at the end (all); adapter saved at each validation,
#    resumable checkpoint every 10 steps; an error resumes automatically (up to 2 times).
TRAIN_OUT = WORKING_DIR / 'adapter_12b_v1'
cmd = [sys.executable, '-u', '-m', 'torch.distributed.run', '--standalone', f'--nproc_per_node={RANKS}',
       str(CODE / 'train_sft.py'), '--model', str(MODEL_PATH), '--samples', str(SAMPLES), '--out', str(TRAIN_OUT),
       '--gpus-per-rank', str(GPUS_PER_RANK), '--epochs', str(CONFIG['epochs']), '--lr', str(CONFIG['lr']),
       '--r', str(CONFIG['r']), '--alpha', str(CONFIG['alpha']), '--accum', str(CONFIG['accum']),
       '--max-hours', str(CONFIG['max_hours'])]
# NCCL_P2P_DISABLE: gradient sums go through host memory (~0.3 GB/step, <1 s); avoids P2P hangs seen on Kaggle
env = dict(os.environ, PYTORCH_CUDA_ALLOC_CONF='expandable_segments:True', OMP_NUM_THREADS='4', NCCL_P2P_DISABLE='1',
           TORCH_NCCL_ASYNC_ERROR_HANDLING='1')
for attempt in range(3):  # a crash or a stuck copy (40-min timeout) resumes from the last checkpoint (every 10 steps)
    code, _ = stream(cmd, env=env)
    print('exit code', code, flush=True)
    if code == 0 or not (TRAIN_OUT / 'last' / 'trainer_state.pt').exists():
        break
    print(f'=== training stopped with an error: resuming from the last checkpoint (retry {attempt + 1}/2) ===', flush=True)
