"""Writes kaggle/cells_train_31b/: the 31B self-distillation LoRA training (GPU L4x4, Python 3.12, internet off).

    python3 scripts/train/make_train31_cells.py

Settings agreed with the user (2026-10-21/24): LoRA r16 alpha16 (scale 1.0), lr 1e-4, 8 warmup steps, cosine to 10%,
1 epoch, 2 segments per optimizer step, grad clip 1.0, segments <= 16384 tokens (24k OOMs on the 31B). One epoch over
~3.5M tokens at ~60 tok/s is ~16 h, longer than a 12 h Kaggle session, so it runs in TWO sessions (decision A):
session 1 PAUSES after SESSION_HOURS with a resumable checkpoint; session 2 = the same notebook with session 1's output
attached (as a dataset, shared with that account) resumes at that step with the same schedule.
Inputs: the wheelhouse, the model google/gemma-4 -> gemma-4-31b-it-qat-w4a16-ct, the merge output (merged/samples.pt),
and for session 2 the session-1 output (adapter_31b/last/trainer_state.pt).
Output: adapter_31b/ (final/, best/, step_N/, last/), history.json, report.json, adapter zips.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle/cells_train_31b"

CELL2 = '''# 2. Setup: the training code (scripts/train/int4_lora.py + train_sft.py), the inputs, resume from session 1.
import glob, json, os, shutil, subprocess, sys, time
from pathlib import Path
assert sys.version_info[:2] == (3, 12), 'Python 3.12 GPU notebook (pinned copy of an old notebook)'
WORKING_DIR = Path('/kaggle/working')
CODE = WORKING_DIR / 'train_code'
CODE.mkdir(parents=True, exist_ok=True)
for name, text in {code!r}.items():
    (CODE / name).write_text(text)
CONFIG = dict(epochs=1.0, lr=1e-4, warmup=8, r=16, alpha=16, accum=2, clip=1.0,
              session_hours=10.8,  # pause here (Kaggle ends sessions at 12 h; ~15 min model load + final saves)
              evals=6, val_max=8)  # 6 mid-run validations on the same 8 segments; start and final on all
_m = sorted(p for p in glob.glob('/kaggle/input/models/google/gemma-4/**/gemma-4-31b-it-qat-w4a16-ct/*', recursive=True)
            if Path(p, 'config.json').exists())
assert _m, 'attach the model google/gemma-4 -> gemma-4-31b-it-qat-w4a16-ct'
MODEL_PATH = Path(_m[-1])
_s = sorted(glob.glob('/kaggle/input/**/samples.pt', recursive=True))
assert len(_s) == 1, f'attach exactly one merged samples.pt (the merge output, or a dataset holding just that file); found {{_s}}'
SAMPLES = Path(_s[0])
_rep = SAMPLES.parent / 'report.json'
print('model', MODEL_PATH, '| samples', SAMPLES, '| merge report:', json.loads(_rep.read_text()).get('estimate') if _rep.exists() else '-')
TRAIN_OUT = WORKING_DIR / 'adapter_31b'
_prev = sorted(glob.glob('/kaggle/input/**/adapter_31b/last/trainer_state.pt', recursive=True))
if _prev and not (TRAIN_OUT / 'last' / 'trainer_state.pt').exists():  # session 2: continue session 1
    assert len(_prev) == 1, f'attach ONE earlier session output; found {{_prev}}'
    shutil.copytree(Path(_prev[0]).parent.parent, TRAIN_OUT)
    print('RESUMING from', Path(_prev[0]).parent.parent, '| files:', sorted(p.name for p in TRAIN_OUT.iterdir()))
else:
    print('session 1: fresh LoRA')


def stream(cmd, env=None):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    noise = ('Warning', 'warn(', 'Loading weights', 'Compressing', 'it/s]')
    lines = []
    for line in p.stdout:
        lines.append(line)
        if line.strip() and not any(n in line for n in noise):
            print(line, end='', flush=True)
    return p.wait(), lines
'''

CELL3 = r'''# 3. TRAIN: one line per step (loss, running average, lr, grad norm, tokens/s, GPU memory, ETA); validation at the start
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
'''

CELL4 = r'''# 4. Report + files to keep. Session 1 (PAUSED): make this output a dataset and attach it to session 2.
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
'''


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    code = {n: (ROOT / "scripts/train" / n).read_text() for n in ("int4_lora.py", "train_sft.py")}
    (OUT / "cell1.py").write_text((ROOT / "kaggle/cells_ood45_31b/cell1.py").read_text())
    (OUT / "cell2_setup.py").write_text(CELL2.format(code=code))
    (OUT / "cell3_train.py").write_text(CELL3)
    (OUT / "cell4_report.py").write_text(CELL4)
    print("wrote", OUT.relative_to(ROOT), sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
