# 2. STAGE A run: download -> filter -> convert teacher runs to our tools -> episode batches in /kaggle/working/stage_a.
#    TRIAL first: MAX_FILES = 1 (one source file, ~10 min). Full run: MAX_FILES = 0 with SHARD '0/2' and '1/2'.
#    Crash-safe: every finished source file is saved (episodes_XXXX.jsonl + state.json) before the next starts.
#    To continue after a crash: attach this notebook's previous output as an input; it is picked up automatically.
import glob, subprocess, sys
from pathlib import Path

MAX_FILES = 1          # trial; 0 = everything
SHARD = '0/1'          # full run in 2 notebooks AT THE SAME TIME: '0/2' in one, '1/2' in the other (~5 h each)
OUT = Path('/kaggle/working/stage_a')
CODE = Path('/kaggle/working/code')

args = [sys.executable, '-u', str(CODE / 'stage_a.py'), '--out', str(OUT), '--max-files', str(MAX_FILES), '--shard', SHARD]
prev = [p for p in glob.glob('/kaggle/input/**/stage_a/state.json', recursive=True)]
if prev and not (OUT / 'state.json').exists():
    args += ['--resume-from', str(Path(prev[0]).parent)]
    print('resuming from', Path(prev[0]).parent)
# a separate process: if it dies, this notebook (and everything saved so far) survives
proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
for line in proc.stdout:
    if 'Retrying in' in line or 'thrown while requesting' in line:
        continue
    print(line, end='')
print('exit code', proc.wait())
