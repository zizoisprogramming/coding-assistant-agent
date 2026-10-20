# 3. BUILD: snapshot + offline wheels per task (network bound, 8 at a time). One line per task; resumes after a restart.
import concurrent.futures as cf, shutil, subprocess, tomllib

PIN = re.compile(r'^([A-Za-z0-9_.\-]+)(\[.*\])?==([^\s;]+)')
BUILD_LOG = OUT / 'build.jsonl'
built = {json.loads(l)['id']: json.loads(l) for l in open(BUILD_LOG)} if BUILD_LOG.exists() else {}
PIN_FILES = {}  # 'name==ver' -> (status, [wheel file names in HOUSE])
_lock = __import__('threading').Lock()


def sh(cmd, cwd=None, timeout=1800):
    r = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout + r.stderr)[-1500:]


def pins_of(req_text):
    out = []
    for line in (req_text or '').splitlines():
        m = PIN.match(line.strip())
        if m:
            out.append(f'{m.group(1)}=={m.group(3)}')
    return out


def fetch_wheels(spec, binary_only_first=True):
    """spec -> (status, wheel names). Downloaded wheel for this machine, else the sdist built into a wheel."""
    with _lock:
        if spec in PIN_FILES:
            return PIN_FILES[spec]
    tmp = Path('/tmp/rb_dl') / re.sub(r'[^A-Za-z0-9_.=-]', '_', spec)
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    code, log = sh(f'{sys.executable} -m pip download -q --no-deps --only-binary=:all: "{spec}" -d {tmp}', timeout=600)
    status = 'wheel'
    if code != 0:
        code, log = sh(f'{sys.executable} -m pip wheel -q --no-deps "{spec}" -w {tmp}', timeout=1200)
        status = 'built' if code == 0 else 'failed: ' + log.strip().splitlines()[-1][:200] if log.strip() else 'failed'
    names = []
    for w in tmp.glob('*.whl'):
        if not (HOUSE / w.name).exists():
            shutil.move(str(w), HOUSE / w.name)
        names.append(w.name)
    shutil.rmtree(tmp, ignore_errors=True)
    res = (status if names else (status if status.startswith('failed') else 'failed: no wheel'), names)
    with _lock:
        PIN_FILES[spec] = res
    return res


def snapshot(r):
    iid, repo, sha = r['instance_id'], r['repo'], r['base_commit']
    d = Path('/tmp/rb_repos') / iid
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    # Only history reachable from base_commit: no later commit (and so no fix) can be in the snapshot.
    for cmd in ('git init -q -b main', f'git remote add origin https://github.com/{repo}.git',
                f'git fetch -q --no-tags origin {sha}', 'git checkout -q -B main FETCH_HEAD', 'git remote remove origin'):
        code, log = sh(cmd, cwd=d, timeout=1800)
        if code:
            return None, f'{cmd.split()[1]} failed: {log.strip().splitlines()[-1][:200] if log.strip() else code}'
    code, head = sh('git rev-parse HEAD', cwd=d)
    if head.strip() != sha:
        return None, f'HEAD {head.strip()[:12]} != base {sha[:12]}'
    _, ncommits = sh('git rev-list --count HEAD', cwd=d)
    build_reqs = []
    try:
        build_reqs = tomllib.loads((d / 'pyproject.toml').read_text()).get('build-system', {}).get('requires', [])
    except Exception:
        pass
    tgz = OUT / 'snapshots' / f'{iid}.tgz'
    code, log = sh(f'tar czf {tgz} -C {d} .')
    shutil.rmtree(d, ignore_errors=True)
    if code:
        return None, 'tar failed: ' + log[-200:]
    return {'commits': int(ncommits.strip() or 0), 'mb': round(tgz.stat().st_size / 1e6, 1), 'build_reqs': build_reqs}, None


def build(iid):
    r = ROWS[iid]
    t0 = time.time()
    snap, err = snapshot(r)
    row = {'id': iid, 'repo': r['repo'], 'snapshot': snap, 'snapshot_error': err}
    specs = pins_of(r['requirements'])
    if snap:  # the build backend: '-e /workspace --no-build-isolation' needs it inside the sandbox
        specs += [s for s in snap['build_reqs'] if not s.lower().startswith(('setuptools', 'wheel'))]
    res = {s: fetch_wheels(s) for s in specs}
    row['pins'] = len(specs)
    row['pins_failed'] = {s: st for s, (st, _) in res.items() if st.startswith('failed')}
    row['pins_built'] = sorted(s for s, (st, _) in res.items() if st == 'built')
    row['wheels'] = sorted({n for _, names in res.values() for n in names})
    row['build_s'] = round(time.time() - t0)
    return row


todo = [i for i, _ in PILOT if i not in built]
print(f'building {len(todo)} tasks ({len(built)} already built)', flush=True)
t_all = time.time()
with cf.ThreadPoolExecutor(8) as ex:
    for k, row in enumerate(ex.map(build, todo), 1):
        built[row['id']] = row
        with open(BUILD_LOG, 'a') as fh:
            fh.write(json.dumps(row) + '\n')
        s = row['snapshot'] or {}
        print(f"[{k:3}/{len(todo)}] {row['id'][:44]:44} snap={'ok' if s else 'FAIL'} {s.get('commits', '-'):>6} commits "
              f"{s.get('mb', '-'):>6} MB | pins {row['pins']:3} built {len(row['pins_built']):2} "
              f"failed {len(row['pins_failed']):2} | {row['build_s']:4}s"
              + (f"\n      snapshot: {row['snapshot_error']}" if row['snapshot_error'] else '')
              + ''.join(f"\n      pin {s}: {st}" for s, st in list(row['pins_failed'].items())[:3]), flush=True)
manifest = {i: b['wheels'] for i, b in built.items() if b['snapshot']}
(OUT / 'wheels' / WHEEL_SET / 'manifest.json').write_text(json.dumps(manifest, indent=1))
house_gb = sum(p.stat().st_size for p in HOUSE.glob('*.whl')) / 1e9
snap_gb = sum(p.stat().st_size for p in (OUT / 'snapshots').glob('*.tgz')) / 1e9
print(f'build done in {(time.time() - t_all) / 60:.1f} min | snapshots {snap_gb:.2f} GB | wheel house '
      f'{len(list(HOUSE.glob("*.whl")))} wheels {house_gb:.2f} GB')
