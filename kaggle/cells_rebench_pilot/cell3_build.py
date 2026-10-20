# 3. BUILD: snapshot + offline wheels per task (network bound, 8 at a time). One line per task; resumes after a restart.
import concurrent.futures as cf, shutil, subprocess, tomllib

PIN = re.compile(r'^([A-Za-z0-9_.\-]+)(\[.*\])?==([^\s;]+)')
BUILD_LOG = OUT / 'build.jsonl'
PIN_LOG = OUT / 'pins.jsonl'  # every package result as it lands: a re-run resumes instead of starting over
SNAP_LOG = OUT / 'snapshots.jsonl'
built = {json.loads(l)['id']: json.loads(l) for l in open(BUILD_LOG)} if BUILD_LOG.exists() else {}
PIN_FILES = {json.loads(l)['spec']: tuple(json.loads(l)['res']) for l in open(PIN_LOG)} if PIN_LOG.exists() else {}
SNAP_DONE = {json.loads(l)['id']: tuple(json.loads(l)['res']) for l in open(SNAP_LOG)} if SNAP_LOG.exists() else {}
_lock = __import__('threading').Lock()
BUILD_TIMEOUT = 300  # a source build that needs longer (big C/C++ packages) counts as failed
BUILD_SLOTS = __import__('threading').Semaphore(4)  # source builds use the CPU (4 cores); downloads run 16 at a time
print(f'resume: {len(built)} tasks built, {len(PIN_FILES)} package pins and {len(SNAP_DONE)} snapshots already done')


def sh(cmd, cwd=None, timeout=1800):
    """(exit code, last output). Never raises: a timeout is exit code 124, any other error 125."""
    try:
        r = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr)[-1500:]
    except subprocess.TimeoutExpired:
        return 124, f'timed out after {timeout}s'
    except Exception as e:
        return 125, f'{type(e).__name__}: {e}'


def last_line(log):
    lines = [l for l in (log or '').strip().splitlines() if l.strip()]
    return lines[-1][:200] if lines else 'no output'


def pins_of(req_text, repo):
    """Pinned requirements, minus the repository's own package (the harness installs it from the snapshot)."""
    own = {re.sub(r'[-_.]+', '-', repo.split('/')[1]).lower()}
    out = []
    for line in (req_text or '').splitlines():
        m = PIN.match(line.strip())
        if m and re.sub(r'[-_.]+', '-', m.group(1)).lower() not in own:
            out.append(f'{m.group(1)}=={m.group(3)}')
    return out


def _collect(tmp):
    names = []
    for w in tmp.glob('*.whl'):
        if not (HOUSE / w.name).exists():
            shutil.move(str(w), HOUSE / w.name)
        names.append(w.name)
    return names


def fetch_wheels(spec):
    """spec -> (status, wheel names), never raises. 1) a ready wheel for this machine; 2) the sdist built here
    (max BUILD_TIMEOUT); 3) 'bumped': the newest release with the same major version that has a ready wheel (old
    compiled pins have no wheel for this Python; the gate then decides whether the tests still pass with it)."""
    with _lock:
        if spec in PIN_FILES:
            return PIN_FILES[spec]
    try:
        tmp = Path('/tmp/rb_dl') / re.sub(r'[^A-Za-z0-9_.=-]', '_', spec)
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True)
        pip = f'{sys.executable} -m pip'
        code, log = sh(f'{pip} download -q --no-deps --only-binary=:all: "{spec}" -d {tmp}', timeout=600)
        status = 'wheel'
        if code != 0:
            with BUILD_SLOTS:
                code, log = sh(f'{pip} wheel -q --no-deps "{spec}" -w {tmp}', timeout=BUILD_TIMEOUT)
            status = 'built'
        if code != 0 or not list(tmp.glob('*.whl')):
            name, ver = spec.split('==', 1)
            major = re.match(r'(\d+)', ver)
            if major:
                for p in tmp.glob('*'):
                    p.unlink() if p.is_file() else shutil.rmtree(p, ignore_errors=True)
                code2, log2 = sh(f'{pip} download -q --no-deps --only-binary=:all: "{name}>={ver},<{int(major.group(1)) + 1}" '
                                 f'-d {tmp}', timeout=600)
                got = list(tmp.glob('*.whl'))
                if code2 == 0 and got:
                    status = 'bumped: ' + got[0].name.split('-')[1]
                    code = 0
            if code != 0:
                status = 'failed: ' + last_line(log)
        names = _collect(tmp)
        shutil.rmtree(tmp, ignore_errors=True)
        res = (status if names or status.startswith('failed') else 'failed: no wheel', names)
    except Exception as e:
        res = (f'failed: {type(e).__name__}: {str(e)[:150]}', [])
    with _lock:
        PIN_FILES[spec] = res
        with open(PIN_LOG, 'a') as fh:
            fh.write(json.dumps({'spec': spec, 'res': list(res)}) + '\n')
    return res


def snapshot(r):
    iid = r['instance_id']
    if iid in SNAP_DONE and (SNAP_DONE[iid][0] is None or (OUT / 'snapshots' / f'{iid}.tgz').exists()):
        return SNAP_DONE[iid]
    try:
        res = _snapshot(r)
    except Exception as e:
        res = (None, f'{type(e).__name__}: {str(e)[:200]}')
    with _lock:
        with open(SNAP_LOG, 'a') as fh:
            fh.write(json.dumps({'id': iid, 'res': list(res)}) + '\n')
    return res


def _snapshot(r):
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
    # importable top-level packages (dirs with __init__.py, at the root or under src/): the gate's import check uses them
    skip = {'tests', 'test', 'testing', 'docs', 'doc', 'examples', 'example', 'scripts', 'tools', 'benchmarks', 'bin', 'ci'}
    packages = sorted({p.name for base in (d, d / 'src') if base.is_dir() for p in base.iterdir()
                       if (p / '__init__.py').exists() and p.name not in skip})
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
    return {'commits': int(ncommits.strip() or 0), 'mb': round(tgz.stat().st_size / 1e6, 1), 'build_reqs': build_reqs,
            'packages': packages}, None


def build_row(iid, snap, err, res):
    r = ROWS[iid]
    specs = task_specs(iid, snap)
    row = {'id': iid, 'repo': r['repo'], 'snapshot': snap, 'snapshot_error': err, 'pins': len(specs)}
    row['pins_failed'] = {s: res[s][0] for s in specs if res[s][0].startswith('failed')}
    row['pins_built'] = sorted(s for s in specs if res[s][0] == 'built')
    row['pins_bumped'] = {s: res[s][0][8:] for s in specs if res[s][0].startswith('bumped')}
    row['wheels'] = sorted({n for s in specs for n in res[s][1]})
    return row


def task_specs(iid, snap):
    specs = pins_of(ROWS[iid]['requirements'], ROWS[iid]['repo'])
    if snap:  # the build backend: '-e /workspace --no-build-isolation' needs it inside the sandbox
        specs += [s for s in snap['build_reqs'] if not s.lower().startswith(('setuptools', 'wheel'))]
    return specs


todo = [i for i, _ in PILOT if i not in built]
print(f'building {len(todo)} tasks ({len(built)} already built)', flush=True)
t_all = time.time()
# Phase A: snapshots, 8 at a time (git fetch = network bound).
SNAPS = {}
with cf.ThreadPoolExecutor(8) as ex:
    for k, (iid, (snap, err)) in enumerate(zip(todo, ex.map(lambda i: snapshot(ROWS[i]), todo)), 1):
        SNAPS[iid] = (snap, err)
        print(f"[snap {k:3}/{len(todo)}] {iid[:44]:44} " + (f"{snap['commits']:6} commits {snap['mb']:7} MB" if snap
              else f"FAILED: {err}"), flush=True)
# Phase B: every distinct package pin of all tasks once, 16 at a time.
specs = sorted({s for i in todo for s in task_specs(i, SNAPS[i][0])})
print(f'fetching {len(specs)} distinct package pins as Linux/CPython 3.12 wheels', flush=True)
RES = {}
with cf.ThreadPoolExecutor(16) as ex:
    for k, (s, res) in enumerate(zip(specs, ex.map(fetch_wheels, specs)), 1):
        RES[s] = res
        if res[0] not in ('wheel',) or k % 50 == 0 or k == len(specs):
            print(f"[pin {k:4}/{len(specs)}] {s[:50]:50} {res[0][:150]}", flush=True)
# Phase C: one line per task.
for k, iid in enumerate(todo, 1):
    row = build_row(iid, *SNAPS[iid], RES)
    built[iid] = row
    with open(BUILD_LOG, 'a') as fh:
        fh.write(json.dumps(row) + '\n')
    print(f"[task {k:3}/{len(todo)}] {iid[:44]:44} snap={'ok' if row['snapshot'] else 'FAIL'} | pins {row['pins']:3} "
          f"built from source {len(row['pins_built']):2} bumped {len(row['pins_bumped']):2} failed {len(row['pins_failed']):2}"
          + ''.join(f"\n      pin {s}: {st[:150]}" for s, st in list(row['pins_failed'].items())[:3]), flush=True)
manifest = {i: b['wheels'] for i, b in built.items() if b['snapshot']}
(OUT / 'wheels' / WHEEL_SET / 'manifest.json').write_text(json.dumps(manifest, indent=1))
house_gb = sum(p.stat().st_size for p in HOUSE.glob('*.whl')) / 1e9
snap_gb = sum(p.stat().st_size for p in (OUT / 'snapshots').glob('*.tgz')) / 1e9
print(f'build done in {(time.time() - t_all) / 60:.1f} min | snapshots {snap_gb:.2f} GB | wheel house '
      f'{len(list(HOUSE.glob("*.whl")))} wheels {house_gb:.2f} GB')
