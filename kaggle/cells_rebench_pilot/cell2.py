# 2. Pilot setup: inputs, output layout, and the SWE-rebench rows of the pilot tasks (downloaded here, on Kaggle).
#    Needs INTERNET ON (Settings -> Internet). See scripts/datasets/make_rebench_cells.py.
import collections, json, re, time, urllib.request
import pyarrow.parquet as pq

WORKING_DIR = Path('/kaggle/working')
OUT = WORKING_DIR / 'rebench'  # the task set, OOD-45 layout
WHEEL_SET = 'x86_64-cp312'
HOUSE = OUT / 'wheels' / 'house'
for p in (OUT / 'snapshots', HOUSE, OUT / 'wheels' / WHEEL_SET):
    p.mkdir(parents=True, exist_ok=True)
PILOT = [('Abjad__abjad-ext-nauert-24', 'difficulty 0'), ('IdentityPython__JWTConnect-Python-CryptoJWT-170', 'difficulty 0'), ('PennyLaneAI__pennylane-1168', 'difficulty 0'), ('PyCQA__pyflakes-472', 'difficulty 1'), ('RockefellerArchiveCenter__DACSspace-51', 'difficulty 1'), ('TeamGraphix__graphix-225', 'difficulty 1'), ('burnash__gspread-1377', 'difficulty 0'), ('camptocamp__python-geoservercloud-52', 'difficulty 1'), ('canonical__charmcraft-1165', 'difficulty 2'), ('canonical__operator-949', 'difficulty 0'), ('dask__dask-11727', 'difficulty 0'), ('eWaterCycle__era5cli-102', 'difficulty 1'), ('elastic__elasticsearch-dsl-py-1416', 'difficulty 0'), ('encode__starlette-291', 'difficulty 0'), ('googleapis__python-storage-42', 'difficulty 1'), ('jmcnamara__XlsxWriter-956', 'difficulty 1'), ('johnnoone__json-spec-23', 'difficulty 1'), ('jwplayer__jwplatform-py-20', 'difficulty 1'), ('lincc-frameworks__nested-pandas-143', 'difficulty 1'), ('lzakharov__csv2md-22', 'difficulty 0'), ('macbre__sql-metadata-440', 'difficulty 2'), ('magmax__python-inquirer-516', 'difficulty 2'), ('marshmallow-code__marshmallow-234', 'difficulty 1'), ('milvus-io__pymilvus-1624', 'difficulty 1'), ('mopidy__mopidy-local-59', 'difficulty 0'), ('narwhals-dev__narwhals-944', 'difficulty 0'), ('networkx__networkx-6788', 'difficulty 1'), ('palantir__python-language-server-211', 'difficulty 1'), ('projectmesa__mesa-1439', 'difficulty 0'), ('pypa__setuptools_scm-573', 'difficulty 0'), ('python-cmd2__cmd2-1069', 'difficulty 1'), ('python-pillow__Pillow-8358', 'difficulty 1'), ('reframe-hpc__reframe-2689', 'difficulty 1'), ('saketkc__pysradb-183', 'difficulty 2'), ('sanic-org__sanic-2615', 'difficulty 1'), ('somm15__PyViCare-198', 'difficulty 0'), ('sympy__sympy-20136', 'difficulty 2'), ('tobymao__sqlglot-4276', 'difficulty 0'), ('vitalik__django-ninja-923', 'difficulty 2'), ('xgi-org__xgi-512', 'difficulty 0')]  # (instance_id, Nebius difficulty score: 0 <15 min, 1 <1 h, 2 1-4 h for a human)


def _first(*cands, pattern=None):
    for c in cands:
        if Path(c).exists():
            return Path(c)
    hits = sorted(glob.glob(pattern, recursive=True)) if pattern else []
    if not hits:
        print('attached inputs (3 levels):', sorted(glob.glob('/kaggle/input/*/*/*'))[:40])
    assert hits, f'none of {cands} exists: attach it as a notebook input'
    return Path(hits[0])


DATA_DIR = _first('/kaggle/input/competitions/gemma-4-developer-agent', '/kaggle/input/gemma-4-developer-agent')
OOD_DIR = _first('/kaggle/input/datasets/rodrigospalma/ood45-bugfix-split', '/kaggle/input/ood45-bugfix-split',
                 pattern='/kaggle/input/**/tools/ood45_harness.py')
OOD_DIR = OOD_DIR.parent.parent if OOD_DIR.name == 'ood45_harness.py' else OOD_DIR
print('competition:', DATA_DIR, '| OOD-45 tools:', OOD_DIR)
try:
    urllib.request.urlopen('https://pypi.org/simple/pip/', timeout=20)
except Exception as e:
    raise RuntimeError(f'no internet ({e!r}): turn Settings -> Internet on, then re-run this cell')

COLS = ['instance_id', 'repo', 'base_commit', 'created_at', 'problem_statement', 'hints_text', 'patch', 'test_patch',
        'FAIL_TO_PASS', 'PASS_TO_PASS', 'install_config', 'requirements', 'license_name', 'meta']
want, ROWS = {i for i, _ in PILOT}, {}
for part in ('test-00000-of-00002.parquet', 'test-00001-of-00002.parquet'):
    dst = Path('/tmp/rebench_src') / part
    dst.parent.mkdir(exist_ok=True)
    if not dst.exists():
        t0 = time.time()
        urllib.request.urlretrieve(f'https://huggingface.co/datasets/nebius/SWE-rebench/resolve/main/data/{part}', dst)
        print(f'downloaded {part} ({dst.stat().st_size / 1e6:.0f} MB, {time.time() - t0:.0f} s)')
    for r in pq.read_table(dst, columns=COLS).to_pylist():
        if r['instance_id'] in want:
            ROWS[r['instance_id']] = r
missing = sorted(want - set(ROWS))
assert not missing, f'pilot ids not found in SWE-rebench: {missing}'
print(len(ROWS), 'pilot tasks from', len({r['repo'] for r in ROWS.values()}), 'repos | python versions',
      dict(collections.Counter(r['install_config']['python'] for r in ROWS.values())))
