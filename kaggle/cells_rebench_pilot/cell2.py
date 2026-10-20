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
PILOT = [('CS-SI__eodag-380', 'sdist_only'), ('DataDog__datadogpy-382', 'wheel'), ('DataDog__dd-trace-py-1116', 'sdist_only'), ('LeMyst__WikibaseIntegrator-58', 'wheel'), ('Quantomatic__pyzx-150', 'sdist_only'), ('RockefellerArchiveCenter__DACSspace-51', 'old_binary'), ('Shopify__shopify_python_api-177', 'sdist_only'), ('Yelp__pyramid-hypernova-15', 'sdist_only'), ('adbar__simplemma-114', 'wheel'), ('asottile__pyupgrade-545', 'wheel'), ('boxed__mutmut-192', 'sdist_only'), ('burnash__gspread-1215', 'wheel'), ('cekit__cekit-452', 'sdist_only'), ('dask__dask-6682', 'old_binary'), ('fastscape-lem__fastscape-32', 'sdist_only'), ('fjosw__pyerrors-61', 'wheel'), ('googleapis__python-logging-898', 'wheel'), ('joke2k__faker-314', 'sdist_only'), ('kymatio__kymatio-982', 'wheel'), ('librosa__librosa-1501', 'wheel'), ('lipoja__URLExtract-135', 'wheel'), ('marcosschroh__dataclasses-avroschema-172', 'old_binary'), ('marrink-lab__vermouth-martinize-205', 'wheel'), ('mathandy__svgpathtools-170', 'wheel'), ('mozilla__bleach-740', 'wheel'), ('numpy__numpydoc-429', 'wheel'), ('pre-commit__pre-commit-1092', 'wheel'), ('pypa__twine-131', 'wheel'), ('python-metar__python-metar-149', 'wheel'), ('scrapy__scrapy-2510', 'wheel'), ('serge-sans-paille__beniget-78', 'wheel'), ('statsmodels__statsmodels-9165', 'wheel'), ('streamlink__streamlink-6420', 'wheel'), ('stummjr__scrapy-fieldstats-13', 'sdist_only'), ('sympy__sympy-18218', 'wheel'), ('tefra__xsdata-396', 'sdist_only'), ('tobgu__pyrsistent-281', 'old_binary'), ('tobymao__sqlglot-4546', 'wheel'), ('xgi-org__xgi-512', 'wheel'), ('zarr-developers__zarr-python-2494', 'sdist_only')]  # (instance_id, PyPI wheel status from the local metadata check)


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
