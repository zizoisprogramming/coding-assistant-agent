# 3. Episodes -> cut -> filter -> samples, per generation output. Prints one line per resolved attempt (verdict and
#    metrics), the verdict counts, how many a stricter filter would keep, and the samples summary.
WORK = Path('/kaggle/working/selfdistill')


def run(cmd):
    print('$', ' '.join(str(c) for c in cmd[:4]), '...', flush=True)
    p = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    print(p.stdout[-20000:], p.stderr[-3000:] if p.returncode else '', flush=True)
    assert p.returncode == 0, f'failed: exit {p.returncode}'
    return p.stdout


for g in GENS:
    name = re.sub(r'[^A-Za-z0-9_-]+', '_', str(g.relative_to('/kaggle/input')))[-60:]
    out = WORK / name
    t0 = time.time()
    strict = run([sys.executable, CODE / 'selfdistill_episodes.py', '--gen', g, '--tasks', TASKS_OF[g], '--out', f'/tmp/strict_{name}',
                  '--max-fail-streak', 2, '--max-repeats', 1, '--max-rereads', 1])
    strict = next(l for l in strict.splitlines() if l.startswith('KEPT'))  # the KEPT line (the DOUBT line comes after it)
    print('STRICT FILTER (2 failed in a row, 1 repeat, 1 reread) would keep:', strict, flush=True)
    run([sys.executable, CODE / 'selfdistill_episodes.py', '--gen', g, '--tasks', TASKS_OF[g], '--out', out])
    run([sys.executable, CODE / 'build_samples.py', '--stage-b', out, '--tokenizer-dir', TOK_DIR,
         '--out', out / 'samples.pt', '--split-on-break', '--max-len', 32768])
    print(f'==> {name}: {(time.time() - t0) / 60:.1f} min, files', sorted(p.name for p in out.iterdir()), flush=True)
