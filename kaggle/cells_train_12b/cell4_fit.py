# 4. Memory + speed check on the LONGEST training segment with 2 GPUs per 12B copy (2 copies train in parallel).
#    Prints the expected training time.
def probe(g):
    out = WORKING_DIR / 'fit'
    print(f'--- trying {g} GPU(s) per copy (loading the 12B, then fwd+bwd on the longest segment) ---', flush=True)
    code, lines = stream([sys.executable, '-u', str(CODE / 'train_sft.py'), '--model', str(MODEL_PATH), '--samples',
                          str(SAMPLES), '--out', str(out), '--probe', '--gpus-per-rank', str(g)])
    line = [l for l in lines if l.startswith('PROBE ')]
    if code != 0 or not line:
        tail = ''.join(lines)[-1500:]
        print(f'  {g} GPU(s) per copy: FAILED' + (' (out of memory)' if 'out of memory' in tail.lower() else ''))
        print('  ' + tail.replace('\n', '\n  ')[-800:])
        return None
    res = json.loads(line[0][6:])
    print(f"  {g} GPU(s) per copy: OK, {res['tokens']} tokens fwd+bwd in {res['seconds']}s "
          f"({res['tokens_per_s']} tok/s), peak {res['peak_gib']} GiB, loss {res['loss']}")
    return res

n_gpu = torch.cuda.device_count()
# One L4 per 12B copy ran out of memory in both earlier runs (21.9/22 GB): go straight to 2 GPUs per copy (user).
# Set TRY_ONE_GPU = True to test 1 GPU per copy again (e.g. after a memory change).
TRY_ONE_GPU = False
fit = probe(1) if TRY_ONE_GPU else None
GPUS_PER_RANK = 1 if fit and fit['peak_gib'] < 21.0 else 2
if GPUS_PER_RANK == 2:
    fit = probe(2)  # still measured: memory + speed on the longest segment, for the time estimate
    assert fit, 'the 12B does not fit even on 2 GPUs per copy: send me the output above'
RANKS = n_gpu // GPUS_PER_RANK
_s = torch.load(SAMPLES)
_train_tok = sum(len(x['input_ids']) for x in _s if x['split'] == 'train')
_val_tok = sum(len(x['input_ids']) for x in _s if x['split'] == 'val')
_speed = fit['tokens_per_s'] * RANKS * 0.9  # longest segment is the slowest per token; 10% for sync/imbalance
_hours = CONFIG['epochs'] * _train_tok / _speed / 3600 + 3 * _val_tok / (_speed * 3) / 3600
print(f"\n==> {RANKS} copies x {GPUS_PER_RANK} GPU(s); train {_train_tok / 1e6:.2f}M tokens/epoch; "
      f"expected ~{_hours:.1f} h of training incl. validation (cap {CONFIG['max_hours']} h)")
