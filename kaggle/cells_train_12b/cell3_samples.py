# 3. Training samples: one token sequence per episode segment (split at compactions), loss only on what the model
#    wrote (thinking, tool calls, final message, stop tokens). ~2-5 min on CPU.
SAMPLES = WORKING_DIR / 'samples.pt'
r = subprocess.run([sys.executable, '-u', str(CODE / 'build_samples.py'), '--stage-b', *STAGE_B,
                    '--tokenizer-dir', str(MODEL_PATH), '--out', str(SAMPLES)])
assert r.returncode == 0 and SAMPLES.exists(), 'building the samples failed (see above)'
