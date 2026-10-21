# 3. CONVERT: every wheel built only for Python 3.13 -> the same version built for 3.12 (download, else build from the
#    sdist), 8 at a time; portable wheels (pure Python / abi3) and the snapshots are copied as they are. One line per
#    converted wheel; resumes (rebench/convert.jsonl).
import concurrent.futures as cf, shutil, threading
from packaging.utils import parse_wheel_filename


def sh(cmd, cwd=None, timeout=600):
    try:
        r = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr)
    except subprocess.TimeoutExpired:
        return 124, f'timed out after {timeout}s'


def only_313(w):
    return '-cp313-cp313-' in w


LOG = OUT / 'convert.jsonl'
CONV = {json.loads(l)['wheel']: json.loads(l) for l in open(LOG)} if LOG.exists() else {}
_lock, BUILD_SLOTS = threading.Lock(), threading.Semaphore(4)


def convert(w):
    if w in CONV:
        return CONV[w]
    name, ver = parse_wheel_filename(w)[:2]
    spec = f'{name}=={ver}'
    tmp = Path('/tmp/cp312') / w
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    pip = f'{sys.executable} -m pip'
    code, log = sh(f'{pip} download -q --no-deps --only-binary=:all: "{spec}" -d {tmp}')
    how = 'download'
    if code != 0 or not list(tmp.glob('*.whl')):
        with BUILD_SLOTS:
            code, log = sh(f'{pip} wheel -q --no-deps --no-binary={name} "{spec}" -w {tmp}', timeout=900)
        how = 'built'
    got = list(tmp.glob('*.whl'))
    res = {'wheel': w, 'how': how if code == 0 and got else 'FAILED', 'new': got[0].name if code == 0 and got else None,
           'log': '' if code == 0 and got else log.strip()[-300:]}
    if res['new'] and not (HOUSE / res['new']).exists():
        shutil.move(str(got[0]), HOUSE / res['new'])
    shutil.rmtree(tmp, ignore_errors=True)
    with _lock:
        CONV[w] = res
        with open(LOG, 'a') as fh:
            fh.write(json.dumps(res) + '\n')
    return res


todo = sorted({w for ws in SRC_MANIFEST.values() for w in ws if only_313(w)})
print(f'{len(todo)} wheels to convert to {WHEEL_SET} ({len(CONV)} done earlier)', flush=True)
t0 = time.time()
with cf.ThreadPoolExecutor(8) as ex:
    for k, (w, res) in enumerate(zip(todo, ex.map(convert, todo)), 1):
        print(f"[conv {k:3}/{len(todo)}] {w[:60]:60} {res['how']:8} {res['new'] or res['log'][-120:]}", flush=True)
print(f'converted in {(time.time() - t0) / 60:.1f} min:', dict(collections.Counter(c['how'] for c in CONV.values())))

# Assemble: snapshots + portable wheels copied, converted wheels mapped, manifest for this wheel set.
TASKS, LEVEL, built, missing = [], {}, {}, collections.Counter()
for k, iid in enumerate(sorted(ROWS), 1):
    shutil.copy2(SRC / 'snapshots' / f'{iid}.tgz', OUT / 'snapshots' / f'{iid}.tgz')
    names = []
    for w in SRC_MANIFEST[iid]:
        if only_313(w):
            if CONV[w]['new']:
                names.append(CONV[w]['new'])
            else:
                missing[iid] += 1
            continue
        if not (HOUSE / w).exists():
            shutil.copy2(SRC / 'wheels' / 'house' / w, HOUSE / w)
        names.append(w)
    built[iid] = {'snapshot': True, 'pins_failed': {}, 'wheels': sorted(set(names))}
    TASKS.append((iid, ROWS[iid]['level']))
    LEVEL[iid] = ROWS[iid]['level']
    if k % 50 == 0 or k == len(ROWS):
        print(f'[copy {k:3}/{len(ROWS)}] {iid}', flush=True)
(OUT / 'wheels' / WHEEL_SET / 'manifest.json').write_text(json.dumps({i: built[i]['wheels'] for i in sorted(built)}, indent=1))
for p in (SRC / 'wheels' / 'host').glob('*.whl'):  # pytest plugins: pure Python, same files
    shutil.copy2(p, OUT / 'wheels' / 'host' / p.name)
host_whls = sorted(str(p) for p in (OUT / 'wheels' / 'host').glob('*.whl'))
r = subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '--no-index', '--no-deps', *host_whls], capture_output=True, text=True)
print('host plugins:', [Path(p).name for p in host_whls], '-> exit', r.returncode, r.stderr[-200:])
SEL = {i: {'source': 'final'} for i in ROWS}  # the gate cell: gold once per task (all passed 3x+1 on 3.13)
SNAP_BAD = {}  # snapshots unchanged (checked by the verification notebook)
CAP = max(collections.Counter(r['repo'] for r in ROWS.values()).values())
print(f"assembled {len(ROWS)} tasks | tasks missing a converted wheel: {len(missing)} {dict(missing.most_common(5))} | "
      f"house {len(list(HOUSE.glob('*.whl')))} wheels {sum(p.stat().st_size for p in HOUSE.glob('*.whl')) / 1e9:.2f} GB")
