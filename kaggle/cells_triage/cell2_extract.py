# 2. Extract per-run features (one line per output as it finishes), then a first report.
OUTD = Path('/kaggle/working/triage')
OUTD.mkdir(parents=True, exist_ok=True)
t0 = time.time()
parts = []
for i, g in enumerate(GENS):
    part = OUTD / f'runs_{i}.jsonl'
    r = subprocess.run([sys.executable, str(CODE / 'triage.py'), 'extract', str(g), '--out', str(part)], capture_output=True, text=True)
    print(r.stderr.strip()[-2000:], f'({time.time() - t0:.0f}s)', flush=True)
    assert r.returncode == 0, 'extract failed: see the lines above'
    parts.append(part)
with open(OUTD / 'runs.jsonl', 'w') as f:
    for i, part in enumerate(parts):
        for line in open(part):
            row = json.loads(line)
            row['src'] = f'{i}:{GENS[i]}'
            f.write(json.dumps(row) + '\n')
        part.unlink()
print(f'==> wrote {OUTD / "runs.jsonl"}: {sum(1 for _ in open(OUTD / "runs.jsonl"))} runs, '
      f'{(OUTD / "runs.jsonl").stat().st_size / 1e6:.1f} MB\n', flush=True)
print(subprocess.run([sys.executable, str(CODE / 'triage.py'), 'report', str(OUTD / 'runs.jsonl')],
                     capture_output=True, text=True).stdout)
