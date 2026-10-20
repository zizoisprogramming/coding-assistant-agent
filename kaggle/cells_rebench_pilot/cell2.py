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
PILOT = [('Abjad__abjad-ext-nauert-24', 'core d0'), ('PMEAL__OpenPNM-1902', 'core d1'), ('PaulSchweizer__flowpipe-127', 'core d1'), ('VirtusLab__git-machete-179', 'core d0'), ('andreroggeri__pynubank-79', 'core d1'), ('asottile__pyupgrade-406', 'large'), ('auth0__auth0-python-159', 'core d0'), ('cool-RR__PySnooper-147', 'core d0'), ('cta-observatory__pyirf-212', 'core d0'), ('cunla__fakeredis-py-275', 'core d0'), ('dask__dask-11300', 'core d2'), ('devsnd__tinytag-171', 'core d1'), ('dimitarOnGithub__temporals-6', 'core d1'), ('flyingcircusio__batou-418', 'core d1'), ('google-research__arxiv-latex-cleaner-96', 'core d1'), ('google__mobly-146', 'core d0'), ('hzdg__django-enumfields-125', 'core d0'), ('icloud-photos-downloader__icloud_photos_downloader-1060', 'core d1'), ('joke2k__faker-1416', 'core d0'), ('jupyter__nbformat-173', 'core d1'), ('jupyterhub__kubespawner-239', 'large'), ('lincc-frameworks__nested-pandas-177', 'large'), ('manmartgarc__stochatreat-26', 'core d1'), ('marcosschroh__dataclasses-avroschema-723', 'core d0'), ('mesonbuild__meson-12210', 'core d0'), ('narwhals-dev__narwhals-1283', 'core d2'), ('nilearn__nilearn-4375', 'large'), ('nolar__kopf-731', 'core d1'), ('nteract__papermill-654', 'core d0'), ('pydata__xarray-9457', 'core d1'), ('python-pillow__Pillow-3310', 'core d1'), ('python-wheel-build__fromager-197', 'core d2'), ('pyvista__pyvista-5767', 'core d1'), ('scikit-hep__hist-238', 'core d1'), ('spdx__tools-python-799', 'core d0'), ('streamlink__streamlink-3765', 'core d0'), ('sympy__sympy-25246', 'core d1'), ('tobymao__sqlglot-4618', 'core d0'), ('vprusso__toqito-155', 'core d2'), ('zalando-stups__senza-178', 'core d2')]  # (instance_id, tier: 'core dN' = <=130 changed lines, Nebius difficulty N (0 <15 min, 1 <1 h, 2 1-4 h); 'large' = 131-400 lines)


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
