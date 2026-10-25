# 2. Export (one line per output as it finishes). Download /kaggle/working/failed/ (a few MB per output).
OUTD = Path('/kaggle/working/failed')
OUTD.mkdir(parents=True, exist_ok=True)
t0 = time.time()
for i, g in enumerate(GENS):
    out = OUTD / f'failed_{g.name}_{i}.jsonl.gz'
    r = subprocess.run([sys.executable, str(CODE / 'export_failed.py'), str(g), '--out', str(out)], capture_output=True, text=True)
    print(r.stderr.strip()[-1500:], f'-> {out.name} {out.stat().st_size / 1e6 if out.exists() else 0:.1f} MB ({time.time() - t0:.0f}s)', flush=True)
    assert r.returncode == 0, 'export failed: see the lines above'
print('==> done:', sorted(p.name for p in OUTD.iterdir()))
