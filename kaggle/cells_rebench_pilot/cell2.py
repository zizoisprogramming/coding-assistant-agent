# 2. Pilot setup: inputs, output layout, and the SWE-rebench rows of the pilot tasks (downloaded here, on Kaggle).
#    Needs INTERNET ON (Settings -> Internet). See scripts/datasets/make_rebench_cells.py.
import collections, json, re, time, urllib.request
import pyarrow.parquet as pq

WORKING_DIR = Path('/kaggle/working')
OUT = WORKING_DIR / 'rebench'  # the task set, OOD-45 layout
WHEEL_SET = f'{__import__("platform").machine()}-cp{sys.version_info.major}{sys.version_info.minor}'  # Kaggle: x86_64-cp313
HOUSE = OUT / 'wheels' / 'house'
for p in (OUT / 'snapshots', HOUSE, OUT / 'wheels' / WHEEL_SET):
    p.mkdir(parents=True, exist_ok=True)
PILOT = [('MycroftAI__lingua-franca-23', 'core d1'), ('PMEAL__OpenPNM-1902', 'core d1'), ('SALib__SALib-636', 'core d0'), ('Sage-Bionetworks__Genie-450', 'core d0'), ('allo-media__text2num-77', 'core d1'), ('conan-io__conan-15422', 'core d1'), ('cta-observatory__cta-lstchain-1227', 'large'), ('dr-prodigy__python-holidays-586', 'large'), ('elastic__elasticsearch-dsl-py-1456', 'core d0'), ('florimondmanca__fountain-lang-7', 'core d1'), ('flyingcircusio__batou-418', 'core d1'), ('goldmann__docker-squash-109', 'core d0'), ('googleapis__python-firestore-219', 'core d2'), ('googleapis__python-storage-323', 'core d1'), ('haddocking__arctic3d-181', 'core d0'), ('intel__code-base-investigator-82', 'large'), ('iterative__shtab-26', 'core d2'), ('joblib__joblib-444', 'core d1'), ('lidatong__dataclasses-json-123', 'core d1'), ('lundberg__respx-23', 'core d2'), ('marcosschroh__dataclasses-avroschema-815', 'core d0'), ('microsoft__electionguard-python-83', 'core d1'), ('milvus-io__pymilvus-1618', 'core d0'), ('mozman__svgwrite-109', 'core d0'), ('networkx__networkx-6240', 'core d0'), ('nilearn__nilearn-3924', 'core d0'), ('planetlabs__planet-client-python-768', 'core d0'), ('python-adaptive__adaptive-160', 'core d0'), ('python-cmd2__cmd2-409', 'core d2'), ('python-pillow__Pillow-6890', 'core d0'), ('snakemake__snakemake-469', 'core d1'), ('spyder-ide__spyder-kernels-327', 'large'), ('sqlfluff__sqlfluff-753', 'core d2'), ('streamlink__streamlink-5890', 'core d1'), ('tefra__xsdata-505', 'core d1'), ('tianocore__edk2-pytool-library-379', 'core d0'), ('tobymao__sqlglot-550', 'core d1'), ('zalando-stups__senza-567', 'core d1'), ('zpieslak__mobilus-client-18', 'core d1'), ('zulip__zulip-terminal-748', 'core d0')]  # (instance_id, tier: 'core dN' = <=130 changed lines, Nebius difficulty N (0 <15 min, 1 <1 h, 2 1-4 h); 'large' = 131-400 lines)


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
# Resume: if an earlier run of this notebook is attached as input (its rebench/ folder), start from its build (snapshots,
# wheels, logs) instead of rebuilding; the gate always runs fresh.
_prev = [p for p in sorted(glob.glob('/kaggle/input/**/rebench/build.jsonl', recursive=True))
         if list((Path(p).parent / 'snapshots').glob('*.tgz'))]  # only a complete earlier output (with its snapshots)
if _prev and not (OUT / 'build.jsonl').exists():
    import shutil as _sh
    _sh.copytree(Path(_prev[0]).parent, OUT, dirs_exist_ok=True)
    print('resumed the build from', Path(_prev[0]).parent)
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
