# 2. FULL BUILD part 1b: inputs, output layout, this part's candidate pool and its SWE-rebench rows.
#    CPU, INTERNET ON, secret GITHUB_TOKEN switched on for this notebook. See scripts/datasets/make_rebench_full_cells.py.
import collections, json, random, re, time, urllib.request
import pyarrow.parquet as pq

T_START = time.time()
DEADLINE_H = 10.5  # the gate starts no new task after this (Kaggle ends sessions at 12 h); cells 5-6 still run
PART, N_TARGET = '1b', 202
MATCH_SHARE, CAP, SEED = 1.0, 6, 20261121  # public-like share wanted; max new tasks per repo
WORKING_DIR = Path('/kaggle/working')
OUT = WORKING_DIR / 'rebench'  # the task set, OOD-45 layout
WHEEL_SET = f'{__import__("platform").machine()}-cp{sys.version_info.major}{sys.version_info.minor}'  # Kaggle: x86_64-cp313
HOUSE = OUT / 'wheels' / 'house'


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
# Resume: an earlier run of THIS part attached as input (its rebench/ folder with part.json) -> continue from it.
_prev = [Path(p).parent for p in sorted(glob.glob('/kaggle/input/**/rebench/part.json', recursive=True))
         if json.loads(Path(p).read_text()).get('part') == PART]
if _prev and not (OUT / 'part.json').exists():
    shutil.copytree(_prev[0], OUT, dirs_exist_ok=True)
    print('resumed from', _prev[0])
for p in (OUT / 'snapshots', HOUSE, OUT / 'wheels' / WHEEL_SET):
    p.mkdir(parents=True, exist_ok=True)
(OUT / 'part.json').write_text(json.dumps({'part': PART, 'n_target': N_TARGET}))
try:
    urllib.request.urlopen('https://pypi.org/simple/pip/', timeout=20)
except Exception as e:
    raise RuntimeError(f'no internet ({e!r}): turn Settings -> Internet on, then re-run this cell')
try:
    from kaggle_secrets import UserSecretsClient
    GH_TOKEN = UserSecretsClient().get_secret('GITHUB_TOKEN')
except Exception as e:
    GH_TOKEN = None
assert GH_TOKEN, ('GITHUB_TOKEN secret is not attached: in the editor, Add-ons -> Secrets -> switch GITHUB_TOKEN on for '
                  'THIS notebook, then re-run this cell (the full build makes ~800 GitHub calls; 60/hour without it)')

POOL = [('12rambau__sepal_ui-807', 'core d1'), ('ASFHyP3__hyp3-sdk-51', 'core d1'), ('Azure__msrest-for-python-189', 'core d2'), ('Clinical-Genomics__patientMatcher-55', 'core d1'), ('DataBiosphere__toil-4805', 'core d1'), ('DataDog__dd-trace-py-1116', 'core d1'), ('DataDog__dd-trace-py-1193', 'core d0'), ('DataDog__dd-trace-py-1607', 'core d1'), ('Dorthu__openapi3-30', 'core d0'), ('Dorthu__openapi3-83', 'core d0'), ('Dorthu__openapi3-94', 'core d2'), ('EmilStenstrom__conllu-64', 'core d0'), ('EvoluxBR__greenswitch-83', 'core d0'), ('Fatal1ty__mashumaro-140', 'large'), ('Fatal1ty__mashumaro-159', 'core d2'), ('Fatal1ty__mashumaro-178', 'core d2'), ('Fatal1ty__mashumaro-189', 'core d0'), ('Informasjonsforvaltning__fdk-rdf-parser-294', 'core d2'), ('Nike-Inc__gimme-aws-creds-464', 'core d0'), ('OpenMined__PySyft-188', 'core d1'), ('Sage-Bionetworks__Genie-437', 'core d1'), ('Sage-Bionetworks__Genie-464', 'core d0'), ('Shopify__shopify_python_api-110', 'core d0'), ('Shopify__shopify_python_api-177', 'core d0'), ('SirAnthony__slpp-32', 'core d1'), ('TheFriendlyCoder__friendlypins-105', 'core d0'), ('adafruit__Adafruit_CircuitPython_GPS-76', 'core d1'), ('astanin__python-tabulate-76', 'core d1'), ('astanin__python-tabulate-96', 'core d1'), ('aws__aws-sam-cli-7533', 'core d0'), ('bear__python-twitter-416', 'core d1'), ('chezou__tabula-py-390', 'core d0'), ('cloudevents__sdk-python-165', 'core d0'), ('cloudevents__sdk-python-71', 'core d1'), ('cloudfoundry-community__cf-python-client-181', 'core d1'), ('cookiecutter__cookiecutter-2029', 'core d2'), ('cunla__fakeredis-py-109', 'core d1'), ('cunla__fakeredis-py-127', 'core d1'), ('cunla__fakeredis-py-85', 'core d1'), ('dapr__python-sdk-402', 'core d0'), ('dapr__python-sdk-692', 'core d0'), ('docker__docker-py-2927', 'core d2'), ('docker__docker-py-863', 'core d2'), ('docker__docker-py-929', 'core d0'), ('elastic__elasticsearch-dsl-py-1416', 'core d0'), ('elastic__elasticsearch-dsl-py-1458', 'core d0'), ('elastic__elasticsearch-dsl-py-1463', 'core d0'), ('elastic__elasticsearch-dsl-py-1629', 'core d1'), ('encode__starlette-291', 'core d0'), ('encode__starlette-33', 'core d0'), ('fabiocaccamo__python-codicefiscale-24', 'core d1'), ('firebase__firebase-admin-python-122', 'core d1'), ('firebase__firebase-admin-python-510', 'core d0'), ('fox-it__dissect.cstruct-108', 'core d2'), ('fox-it__dissect.cstruct-43', 'core d0'), ('fox-it__dissect.cstruct-66', 'core d0'), ('garcia__simfile-29', 'core d2'), ('hhursev__recipe-scrapers-915', 'core d0'), ('honeybadger-io__honeybadger-python-63', 'core d1'), ('html5lib__html5lib-python-259', 'core d1'), ('ikamensh__flynt-163', 'core d1'), ('jborean93__smbprotocol-264', 'core d1'), ('johnnoone__json-spec-23', 'core d1'), ('juju__python-libjuju-1054', 'core d0'), ('juju__python-libjuju-497', 'core d0'), ('juju__python-libjuju-582', 'core d0'), ('jwplayer__jwplatform-py-20', 'core d1'), ('lark-parser__lark-1013', 'core d0'), ('lark-parser__lark-1432', 'core d2'), ('lark-parser__lark-1481', 'core d0'), ('lark-parser__lark-866', 'core d0'), ('linkml__linkml-1343', 'core d1'), ('lmfit__lmfit-py-961', 'core d1'), ('macbre__sql-metadata-440', 'core d2'), ('marshmallow-code__apispec-382', 'core d1'), ('marshmallow-code__apispec-677', 'core d2'), ('marshmallow-code__apispec-690', 'core d0'), ('marshmallow-code__apispec-953', 'core d0'), ('marshmallow-code__marshmallow-1063', 'core d0'), ('marshmallow-code__marshmallow-1249', 'core d1'), ('marshmallow-code__marshmallow-2150', 'core d1'), ('marshmallow-code__marshmallow-234', 'core d1'), ('marshmallow-code__marshmallow-821', 'core d1'), ('milvus-io__pymilvus-1624', 'core d1'), ('miurahr__aqtinstall-136', 'core d0'), ('palantir__python-language-server-211', 'core d1'), ('pypa__cibuildwheel-1430', 'core d0'), ('pypa__cibuildwheel-1613', 'core d1'), ('rapidpro__rapidpro-python-66', 'core d0'), ('sanic-org__sanic-2622', 'core d0'), ('sanic-org__sanic-2636', 'core d2'), ('sanic-org__sanic-2704', 'core d1'), ('sanic-org__sanic-2722', 'core d2'), ('sanic-org__sanic-2737', 'core d0'), ('sanic-org__sanic-2971', 'core d0'), ('sciunto-org__python-bibtexparser-162', 'core d0'), ('sciunto-org__python-bibtexparser-385', 'core d0'), ('somm15__PyViCare-198', 'core d0'), ('spdx__tools-python-481', 'core d0'), ('spdx__tools-python-520', 'core d1'), ('spdx__tools-python-695', 'core d1'), ('spdx__tools-python-799', 'core d0'), ('sphinx-doc__sphinx-10539', 'core d2'), ('sphinx-doc__sphinx-11431', 'core d0'), ('sphinx-doc__sphinx-11888', 'core d1'), ('spyder-ide__spyder-kernels-86', 'core d1'), ('tefra__xsdata-1055', 'core d0'), ('tefra__xsdata-1098', 'core d1'), ('tefra__xsdata-1107', 'core d1'), ('tefra__xsdata-396', 'core d1'), ('tefra__xsdata-400', 'core d1'), ('tefra__xsdata-886', 'core d1'), ('tefra__xsdata-901', 'core d0'), ('tobymao__sqlglot-3522', 'core d0'), ('tobymao__sqlglot-3525', 'large'), ('tobymao__sqlglot-3533', 'core d1'), ('tobymao__sqlglot-3541', 'core d1'), ('tobymao__sqlglot-3547', 'core d1'), ('tobymao__sqlglot-3548', 'core d0'), ('tobymao__sqlglot-3549', 'core d2'), ('tobymao__sqlglot-3552', 'core d0'), ('tobymao__sqlglot-3566', 'core d0'), ('tobymao__sqlglot-3612', 'core d1'), ('tobymao__sqlglot-3641', 'core d1'), ('tobymao__sqlglot-3650', 'core d1'), ('tobymao__sqlglot-3652', 'large'), ('tobymao__sqlglot-3682', 'core d1'), ('tobymao__sqlglot-3695', 'core d1'), ('tobymao__sqlglot-3720', 'core d2'), ('tobymao__sqlglot-3745', 'core d2'), ('tobymao__sqlglot-3756', 'core d0'), ('tobymao__sqlglot-3765', 'core d2'), ('tobymao__sqlglot-3785', 'core d0'), ('tobymao__sqlglot-3798', 'core d0'), ('tobymao__sqlglot-3839', 'core d1'), ('tobymao__sqlglot-3855', 'core d0'), ('tobymao__sqlglot-3870', 'core d2'), ('tobymao__sqlglot-3935', 'core d1'), ('tobymao__sqlglot-3937', 'core d1'), ('tobymao__sqlglot-3971', 'core d2'), ('tobymao__sqlglot-3980', 'core d0'), ('tobymao__sqlglot-3987', 'core d2'), ('tobymao__sqlglot-3994', 'core d1'), ('tobymao__sqlglot-4004', 'core d0'), ('tobymao__sqlglot-4007', 'core d1'), ('tobymao__sqlglot-4015', 'core d0'), ('tobymao__sqlglot-4041', 'core d0'), ('tobymao__sqlglot-4051', 'core d0'), ('tobymao__sqlglot-4079', 'core d1'), ('tobymao__sqlglot-4087', 'core d0'), ('tobymao__sqlglot-4093', 'core d0'), ('tobymao__sqlglot-4096', 'core d0'), ('tobymao__sqlglot-4109', 'core d0'), ('tobymao__sqlglot-4141', 'core d1'), ('tobymao__sqlglot-4148', 'core d1'), ('tobymao__sqlglot-4151', 'core d1'), ('tobymao__sqlglot-4172', 'core d2'), ('tobymao__sqlglot-4197', 'core d0'), ('tobymao__sqlglot-4218', 'core d2'), ('tobymao__sqlglot-4239', 'core d1'), ('tobymao__sqlglot-4252', 'core d1'), ('tobymao__sqlglot-4276', 'core d0'), ('tobymao__sqlglot-4293', 'core d1'), ('tobymao__sqlglot-4311', 'core d1'), ('tobymao__sqlglot-432', 'core d2'), ('tobymao__sqlglot-4325', 'core d2'), ('tobymao__sqlglot-4328', 'core d1'), ('tobymao__sqlglot-4355', 'core d0'), ('tobymao__sqlglot-437', 'core d2'), ('tobymao__sqlglot-4373', 'core d1'), ('tobymao__sqlglot-4390', 'core d1'), ('tobymao__sqlglot-4417', 'core d0'), ('tobymao__sqlglot-4438', 'core d2'), ('tobymao__sqlglot-444', 'core d1'), ('tobymao__sqlglot-4448', 'core d1'), ('tobymao__sqlglot-4457', 'core d0'), ('tobymao__sqlglot-446', 'core d0'), ('tobymao__sqlglot-4493', 'core d1'), ('tobymao__sqlglot-4497', 'core d0'), ('tobymao__sqlglot-4519', 'core d0'), ('tobymao__sqlglot-4528', 'core d0'), ('tobymao__sqlglot-4533', 'core d0'), ('tobymao__sqlglot-4545', 'core d2'), ('tobymao__sqlglot-4546', 'core d1'), ('tobymao__sqlglot-4563', 'core d0'), ('tobymao__sqlglot-4569', 'core d0'), ('tobymao__sqlglot-4618', 'core d0'), ('tobymao__sqlglot-4643', 'core d1'), ('tobymao__sqlglot-4652', 'core d2'), ('tobymao__sqlglot-4683', 'core d1'), ('tobymao__sqlglot-4696', 'core d1'), ('tobymao__sqlglot-4935', 'core d1'), ('tobymao__sqlglot-4941', 'core d1'), ('tobymao__sqlglot-555', 'core d1'), ('tobymao__sqlglot-700', 'core d2'), ('tobymao__sqlglot-702', 'core d2'), ('tobymao__sqlglot-767', 'core d1'), ('tobymao__sqlglot-772', 'core d1'), ('tobymao__sqlglot-790', 'core d1'), ('tobymao__sqlglot-8', 'large'), ('tobymao__sqlglot-805', 'core d0'), ('yukinarit__pyserde-441', 'core d1')]  # (instance_id, level): 'core dN' = <=130 changed lines, Nebius difficulty N; 'large' = 131-500 lines
LEVEL = dict(POOL)
COLS = ['instance_id', 'repo', 'base_commit', 'created_at', 'problem_statement', 'hints_text', 'patch', 'test_patch',
        'FAIL_TO_PASS', 'PASS_TO_PASS', 'install_config', 'requirements', 'license_name', 'meta']
ROWS = {}
for part in ('test-00000-of-00002.parquet', 'test-00001-of-00002.parquet'):
    dst = Path('/tmp/rebench_src') / part
    dst.parent.mkdir(exist_ok=True)
    if not dst.exists():
        t0 = time.time()
        urllib.request.urlretrieve(f'https://huggingface.co/datasets/nebius/SWE-rebench/resolve/main/data/{part}', dst)
        print(f'downloaded {part} ({dst.stat().st_size / 1e6:.0f} MB, {time.time() - t0:.0f} s)')
    for r in pq.read_table(dst, columns=COLS).to_pylist():
        if r['instance_id'] in LEVEL:
            ROWS[r['instance_id']] = r
missing = sorted(set(LEVEL) - set(ROWS))
assert not missing, f'pool ids not found in SWE-rebench: {missing[:5]}'
print(f'part {PART}: pool {len(POOL)} tasks from {len({r["repo"] for r in ROWS.values()})} repos | levels',
      dict(sorted(collections.Counter(LEVEL.values()).items())), '| target', N_TARGET)
