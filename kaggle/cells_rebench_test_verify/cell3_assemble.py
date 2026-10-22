# 3. ASSEMBLE: one task set in the OOD-45 layout from the four build outputs. One line per task.
import shutil
from packaging.utils import parse_wheel_filename
from packaging.version import Version

SRC_ROWS = {}
for part, d in SRC.items():
    man = json.loads((d / 'wheels' / WHEEL_SET / 'manifest.json').read_text())
    for l in open(d / 'tasks.jsonl'):
        t = json.loads(l)
        if t['instance_id'] in SEL and SEL[t['instance_id']]['source'] == part:
            SRC_ROWS[t['instance_id']] = (part, d, t, man.get(t['instance_id']))
lost = sorted(set(SEL) - set(SRC_ROWS))
assert not lost, f'{len(lost)} selected tasks not found in their source: {lost[:5]}'

ROWS, TASKS, LEVEL, built, house_src, same_name_diff = {}, [], {}, {}, {}, 0
for k, iid in enumerate(sorted(SEL), 1):
    s, (part, d, t, wheels) = SEL[iid], SRC_ROWS[iid]
    assert wheels is not None, f'{iid}: no wheel list in part {part} manifest'
    shutil.copy2(d / 'snapshots' / f'{iid}.tgz', OUT / 'snapshots' / f'{iid}.tgz')
    for w in wheels:
        src = d / 'wheels' / 'house' / w
        if w in house_src:  # same name from two builds: wheels built from source differ in bytes, not in content
            same_name_diff += src.stat().st_size != house_src[w].stat().st_size
            continue
        shutil.copy2(src, HOUSE / w)
        house_src[w] = src
    issue = t['problem_statement']
    text = issue if s['text'] == 'issue' else t['pr']['text']
    ROWS[iid] = {**{k2: t[k2] for k2 in ('instance_id', 'repo', 'base_commit', 'patch', 'test_patch', 'FAIL_TO_PASS',
                                          'PASS_TO_PASS', 'created_at', 'license', 'python_original')},
                 'problem_statement': text, 'hints_text': '', 'text_kind': s['text'], 'issue_text': issue,
                 'problem_statement_original': issue,  # field name ood45_harness.load_tasks expects
                 'pr': t.get('pr'), 'leak': s['leak'], 'unfair_names': s['unfair_names'], 'domain': s['domain'],
                 'topics': s['topics'], 'level': s['level'], 'difficulty': s['difficulty'], 'env_partial': s['env_partial'],
                 'build_part': part, 'requirements': '',
                 'source': 'nebius/SWE-rebench (CC-BY-4.0); PR texts from GitHub'}
    TASKS.append((iid, s['level']))
    LEVEL[iid] = s['level']
    built[iid] = {'snapshot': True, 'pins_failed': {}, 'wheels': wheels}
    if k % 25 == 0 or k == len(SEL):
        print(f'[copy {k:3}/{len(SEL)}] {iid[:44]:44} {part:5} {s["text"]:5} {len(wheels):3} wheels', flush=True)
(OUT / 'wheels' / WHEEL_SET / 'manifest.json').write_text(json.dumps({i: built[i]['wheels'] for i in sorted(built)}, indent=1))
CAP = max(collections.Counter(r['repo'] for r in ROWS.values()).values())

# Host pytest plugins: the harness leaves pytest plugins out of every task's wheel set (the scoring image has
# pytest and pytest-timeout); the builds installed pytest-asyncio / pytest-timeout / pytest-xdist on the host from
# PyPI. Offline: the newest of each found in the build outputs' wheel houses, installed here and shipped in
# wheels/host/ so every later notebook (generation) installs the same ones.
HOST_PLUGIN_PKGS = ('pytest_asyncio', 'pytest_timeout', 'pytest_xdist', 'execnet')
best = {}
for part, d in SRC.items():
    for w in (d / 'wheels' / 'house').glob('*.whl'):
        name, ver = parse_wheel_filename(w.name)[:2]
        key = str(name).replace('-', '_')
        if key in HOST_PLUGIN_PKGS and (key not in best or ver > best[key][0]):
            best[key] = (ver, w)
for key in HOST_PLUGIN_PKGS:
    if key in best:
        shutil.copy2(best[key][1], OUT / 'wheels' / 'host' / best[key][1].name)
host_whls = sorted(str(p) for p in (OUT / 'wheels' / 'host').glob('*.whl'))
print('host plugins:', [Path(p).name for p in host_whls], '| missing:', [k for k in HOST_PLUGIN_PKGS if k not in best])
r = subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '--no-index', '--no-deps', *host_whls], capture_output=True, text=True)
print('host plugin install exit', r.returncode, r.stderr[-300:])
snap_gb = sum(p.stat().st_size for p in (OUT / 'snapshots').glob('*.tgz')) / 1e9
house_gb = sum(p.stat().st_size for p in HOUSE.glob('*.whl')) / 1e9
print(f'assembled {len(ROWS)} tasks ({same_name_diff} wheel names built twice, first copy kept) | snapshots {snap_gb:.2f} GB | wheel house {len(house_src)} wheels {house_gb:.2f} GB')
