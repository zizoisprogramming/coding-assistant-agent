# 2. Download each run (sequential: Kaggle rate-limits parallel calls), verify, report. Ends by itself.
def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()

def one(label, ref):
    dest = WORK / label
    for attempt in range(1, 4):
        if dest.exists():
            shutil.rmtree(dest)  # a fixed path under /kaggle/working/runs: a clean retry
        dest.mkdir(parents=True)
        t = time.time()
        r = subprocess.run(['kaggle', 'kernels', 'output', ref, '-p', str(dest), '--file-pattern', PATTERN],
                           capture_output=True, text=True)
        gen = sorted(dest.glob('**/results/gen_per_task.jsonl'))
        ph = sorted(dest.glob('**/results/phases.json'))
        req = sorted(dest.glob('**/requests/requests.jsonl'))
        diffs = list(dest.glob('**/results/gen/patches/*.diff'))
        exp = EXPECTED[label]
        problems = []
        if len(gen) != 1 or md5(gen[0]) != exp['gen_md5']:
            problems.append('gen_per_task.jsonl missing or not the expected run')
        if len(ph) != 1 or md5(ph[0]) != exp['phases_md5']:
            problems.append('phases.json missing or not the expected run')
        if len(req) != 1 or req[0].stat().st_size == 0:
            problems.append('requests.jsonl missing or empty')
        if not problems:
            jobs, lines = set(), 0
            with open(req[0], errors='replace') as fh:
                for line in fh:
                    lines += 1
                    try:
                        jobs.add(json.loads(line).get('job'))
                    except Exception:
                        pass
            rows = [json.loads(l) for l in gen[0].read_text().splitlines()]
            want = {f"{x['instance_id']}#a{x['attempt']}" for x in rows}
            covered = len(want & jobs)
            info = {'ref': ref, 'rows': len(rows), 'requests': lines, 'runs_with_requests': covered, 'patches': len(diffs),
                    'requests_mb': round(req[0].stat().st_size / 1e6, 1), 'seconds': round(time.time() - t)}
            print(f"  {label:7} OK  {ref} | rows {len(rows)} | runs with requests {covered}/{len(want)} | "
                  f"requests {lines} ({info['requests_mb']} MB) | patches {len(diffs)} | {info['seconds']} s", flush=True)
            if covered < 0.95 * len(want):
                print(f"  {label:7} WARNING: only {covered} of {len(want)} runs have request logs", flush=True)
            return info
        print(f"  {label:7} attempt {attempt} FAILED {ref}: {problems} | CLI: {(r.stderr or r.stdout)[-300:]}", flush=True)
        time.sleep(30 * attempt)
    raise SystemExit(f'{label} ({ref}): could not collect the expected run -> send me this output')

MANIFEST = {}
for k, (label, ref) in enumerate(SOURCES.items(), 1):
    print(f'[{k}/{len(SOURCES)}] {label} <- {ref}', flush=True)
    MANIFEST[label] = one(label, ref)
(WORK / 'manifest.json').write_text(json.dumps(MANIFEST, indent=1))
total_mb = sum(p.stat().st_size for p in WORK.rglob('*') if p.is_file()) / 1e6
print(f"\nCOLLECTED {len(MANIFEST)}/{len(SOURCES)} runs | rows {sum(m['rows'] for m in MANIFEST.values())} | "
      f"runs with requests {sum(m['runs_with_requests'] for m in MANIFEST.values())} | "
      f"patches {sum(m['patches'] for m in MANIFEST.values())} | {total_mb:.0f} MB in /kaggle/working/runs")
