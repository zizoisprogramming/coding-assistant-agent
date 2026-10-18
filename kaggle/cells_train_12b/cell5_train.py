# 5. Train. One line per step (loss, running average, lr, grad norm, tokens/s, GPU memory, ETA); validation loss at
#    the start, ~every quarter and at the end; adapter saved at each validation (resumable: re-running this cell
#    continues from the last saved step).
TRAIN_OUT = WORKING_DIR / 'adapter_12b_v1'
cmd = [sys.executable, '-u', '-m', 'torch.distributed.run', '--standalone', f'--nproc_per_node={RANKS}',
       str(CODE / 'train_sft.py'), '--model', str(MODEL_PATH), '--samples', str(SAMPLES), '--out', str(TRAIN_OUT),
       '--gpus-per-rank', str(GPUS_PER_RANK), '--epochs', str(CONFIG['epochs']), '--lr', str(CONFIG['lr']),
       '--r', str(CONFIG['r']), '--alpha', str(CONFIG['alpha']), '--accum', str(CONFIG['accum']),
       '--max-hours', str(CONFIG['max_hours'])]
# NCCL_P2P_DISABLE: gradient sums go through host memory (~0.3 GB/step, <1 s); avoids P2P hangs seen on Kaggle
env = dict(os.environ, PYTORCH_CUDA_ALLOC_CONF='expandable_segments:True', OMP_NUM_THREADS='4', NCCL_P2P_DISABLE='1')
p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
noise = ('Warning', 'warn(', 'Loading weights', 'Compressing', 'it/s]')
for line in p.stdout:
    if line.strip() and not any(n in line for n in noise):
        print(line, end='', flush=True)
print('exit code', p.wait())
