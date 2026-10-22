"""Writes kaggle/cells_rebench_verify/: the OFFLINE verification + assembly notebook of our SWE-rebench task set.

    .venv/bin/python scripts/datasets/assemble_rebench.py        # decisions -> data/rebench_final/selection.json
    .venv/bin/python scripts/datasets/make_rebench_verify_cells.py
    .venv/bin/python scripts/datasets/make_rebench_verify_cells.py --test   # the test set (assemble_rebench.py --test)

CPU, INTERNET OFF (on purpose: proves the set is self-contained and drops tests that need the network; the scoring
sandbox is offline too). Inputs: the competition, the wheelhouse, rodrigospalma/ood45-bugfix-split, and the four
build outputs (as datasets or notebook outputs; each is recognised by rebench/part.json, the pilot by having none):
pilot-2, part 1 (172 usable), part 1b (74), part 2 (184).
  cell 2  find the inputs, check each source is the right one (part.json + usable counts), embed the selection
  cell 3  ASSEMBLE: copy each selected task's snapshot and wheels into one OOD-45-layout set; the task text is the one
          the selection chose (issue or PR); host pytest plugins (the scoring image lacks them, the builds installed
          them from PyPI) are taken from the wheel houses and shipped in wheels/host/
  cell 4  SNAPSHOTS: HEAD == base_commit, only refs/heads/main, no remote, every commit reachable from HEAD, no
          unreachable objects, clean tree (no later commit, and so no fix, can be inside)
  cell 5  RE-GATE offline: gold must PASS (pilot tasks: 3 times; they were gated once), empty must FAIL
  cell 6  FINISH: tasks.jsonl (passing tasks, all labels), README.md, prune; the output is the dataset to publish
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/datasets"))
import make_rebench_full_cells as M  # noqa: E402

OUT_DIR = ROOT / "kaggle/cells_rebench_verify"
EXPECT_USABLE = {"pilot": 23, "1": 172, "1b": 74, "2": 184}

CELL2 = '''# 2. VERIFY + ASSEMBLE: inputs, source checks, the selection (made locally: scripts/datasets/assemble_rebench.py).
#    CPU, INTERNET OFF. See scripts/datasets/make_rebench_verify_cells.py.
import collections, json, re, time, urllib.request

T_START = time.time()
DEADLINE_H = 10.5
WORKING_DIR = Path('/kaggle/working')
OUT = WORKING_DIR / 'rebench'
WHEEL_SET = f'{{__import__("platform").machine()}}-cp{{sys.version_info.major}}{{sys.version_info.minor}}'  # Kaggle: x86_64-cp313
HOUSE = OUT / 'wheels' / 'house'
for p in (OUT / 'snapshots', HOUSE, OUT / 'wheels' / WHEEL_SET, OUT / 'wheels' / 'host'):
    p.mkdir(parents=True, exist_ok=True)
try:
    urllib.request.urlopen('https://pypi.org/simple/pip/', timeout=10)
    raise SystemExit('INTERNET IS ON: turn Settings -> Internet OFF (this run must prove the set works offline), then re-run')
except SystemExit:
    raise
except Exception:
    print('internet: off (good)')


def _first(*cands, pattern=None):
    for c in cands:
        if Path(c).exists():
            return Path(c)
    hits = sorted(glob.glob(pattern, recursive=True)) if pattern else []
    assert hits, f'none of {{cands}} exists: attach it as a notebook input'
    return Path(hits[0])


DATA_DIR = _first('/kaggle/input/competitions/gemma-4-developer-agent', '/kaggle/input/gemma-4-developer-agent')
OOD_DIR = _first('/kaggle/input/datasets/rodrigospalma/ood45-bugfix-split', '/kaggle/input/ood45-bugfix-split',
                 pattern='/kaggle/input/**/tools/ood45_harness.py')
OOD_DIR = OOD_DIR.parent.parent if OOD_DIR.name == 'ood45_harness.py' else OOD_DIR
print('competition:', DATA_DIR, '| OOD-45 tools:', OOD_DIR)

# The four build outputs: each rebench/ folder with a tasks.jsonl; part.json names the part (the pilot has none).
EXPECT_USABLE = {expect!r}
SRC = {{}}
for p in sorted(glob.glob('/kaggle/input/**/rebench/tasks.jsonl', recursive=True)):
    d = Path(p).parent
    part = str(json.loads((d / 'part.json').read_text())['part']) if (d / 'part.json').exists() else 'pilot'
    usable = sum(1 for l in open(p) if json.loads(l)['gate'].get('usable'))
    print(f'found part {{part:5}} at {{d}}: {{usable}} usable tasks')
    if part in SRC:
        raise SystemExit(f'part {{part}} attached twice ({{SRC[part]}} and {{d}}): remove one input')
    if usable != EXPECT_USABLE.get(part):
        raise SystemExit(f'{{d}} is part {{part}} with {{usable}} usable tasks, expected {{EXPECT_USABLE.get(part)}}: '
                         'wrong version attached? (part 1 = new-data VERSION 1, part 1b = new-data version 2)')
    SRC[part] = d
missing = sorted(set(EXPECT_USABLE) - set(SRC))
assert not missing, f'missing build outputs for parts {{missing}}: attach them (see the list above)'

SELECTION = {selection}  # one dict per task (scripts/datasets/assemble_rebench.py)
SEL = {{s['id']: s for s in SELECTION}}
print(f'selection: {{len(SELECTION)}} tasks from {{len({{s["repo"] for s in SELECTION}})}} repos | by source',
      dict(collections.Counter(s['source'] for s in SELECTION)), '| text', dict(collections.Counter(s['text'] for s in SELECTION)))
'''

CELL3 = r'''# 3. ASSEMBLE: one task set in the OOD-45 layout from the four build outputs. One line per task.
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
                 'build_part': part, 'requirements': '', 'split': s.get('split', 'train'),
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
'''

CELL4_SNAP = r'''# 4. SNAPSHOT CHECK (no later commit, and so no fix, can be inside): HEAD == base_commit, only refs/heads/main,
#    no remote, every commit reachable from HEAD, no unreachable objects, clean working tree. 8 at a time.
import concurrent.futures as cf, tempfile


def sh(cmd, cwd=None, timeout=600):
    try:
        r = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr)
    except subprocess.TimeoutExpired:
        return 124, f'timed out after {timeout}s'


def check_snapshot(iid):
    r = ROWS[iid]
    d = Path(tempfile.mkdtemp(prefix='snapchk_'))
    try:
        code, out = sh(f"tar xzf {OUT / 'snapshots' / (iid + '.tgz')} -C {d}")
        if code:
            return ['untar failed: ' + out[-150:]]
        bad = []
        head = sh('git rev-parse HEAD', d)[1].strip()
        if head != r['base_commit']:
            bad.append(f'HEAD {head[:12]} != base {r["base_commit"][:12]}')
        refs = sh("git for-each-ref --format='%(refname)'", d)[1].split()
        if refs != ['refs/heads/main']:
            bad.append(f'refs {refs[:4]}')
        if sh('git remote', d)[1].strip():
            bad.append('has a remote')
        n_all, n_head = sh('git rev-list --all | wc -l', d)[1].strip(), sh('git rev-list HEAD | wc -l', d)[1].strip()
        if n_all != n_head:
            bad.append(f'commits not under HEAD: {n_all} vs {n_head}')
        code, out = sh('git fsck --unreachable --no-reflogs --connectivity-only 2>/dev/null | head -5', d)
        if out.strip():
            bad.append('unreachable objects: ' + out.strip().splitlines()[0][:80])
        if sh('git stash list', d)[1].strip():
            bad.append('stash entries')
        status = sh('git status --porcelain | head -5', d)[1].strip()
        if status:
            bad.append('dirty tree: ' + status.splitlines()[0][:80])
        return bad
    finally:
        shutil.rmtree(d, ignore_errors=True)


SNAP_BAD = {}
t0 = time.time()
with cf.ThreadPoolExecutor(8) as ex:
    for k, (iid, bad) in enumerate(zip(sorted(ROWS), ex.map(check_snapshot, sorted(ROWS))), 1):
        if bad:
            SNAP_BAD[iid] = bad
        if bad or k % 25 == 0 or k == len(ROWS):
            print(f"[snap {k:3}/{len(ROWS)}] {iid[:44]:44} {'OK' if not bad else 'BAD: ' + '; '.join(bad)}", flush=True)
print(f'snapshot check done in {(time.time() - t0) / 60:.1f} min: {len(ROWS) - len(SNAP_BAD)} clean, {len(SNAP_BAD)} bad')
'''

CELL6 = r'''# 6. FINISH: the dataset. tasks.jsonl = tasks that passed the snapshot check and the offline re-gate; README.md;
#    everything else pruned. Then: Output -> New Dataset (private) -> share it with the generation account (user 2026-10-21: not public).
final = [i for i in sorted(ROWS) if i not in SNAP_BAD and gate.get(i, {}).get('usable')]
dropped = {i: ('snapshot: ' + '; '.join(SNAP_BAD[i]) if i in SNAP_BAD else 'not gated (deadline)' if i not in gate else
               'gate: ' + (gate[i].get('why') or f"gold {'/'.join(gate[i].get('gold_runs', []))} empty {gate[i].get('empty')}"))[:160]
           for i in sorted(ROWS) if i not in final}
with open(OUT / 'tasks.jsonl', 'w') as fh:
    for i in final:
        row = {k: v for k, v in ROWS[i].items() if k != 'requirements'}
        fh.write(json.dumps({**row, 'gate': gate[i]}) + '\n')
for p in (OUT / 'snapshots').glob('*.tgz'):
    if p.stem not in final:
        p.unlink()
manifest = {i: built[i]['wheels'] for i in final}
(OUT / 'wheels' / WHEEL_SET / 'manifest.json').write_text(json.dumps(manifest, indent=1))
need = {w for ws in manifest.values() for w in ws}
for p in HOUSE.glob('*.whl'):
    if p.name not in need:
        p.unlink()
for f in ('gate.json', 'gate_env_install.jsonl'):
    (OUT / f).rename(OUT / f'verify_{f}') if (OUT / f).exists() else None
(OUT / 'dropped.json').write_text(json.dumps(dropped, indent=1))

F = [ROWS[i] for i in final]
n = max(len(F), 1)
share = lambda pred: f'{sum(1 for r in F if pred(r))} ({100 * sum(1 for r in F if pred(r)) / n:.0f}%)'  # noqa: E731
summary = {
    'tasks': len(F), 'repos': len({r['repo'] for r in F}),
    'domain': dict(collections.Counter(r['domain'] for r in F)), 'level': dict(sorted(collections.Counter(r['level'] for r in F).items())),
    'text': dict(collections.Counter(r['text_kind'] for r in F)), 'leaking text': share(lambda r: r['leak']),
    'unfair tests': share(lambda r: r['unfair_names']), 'env_partial': share(lambda r: r['env_partial']),
    'public-like domain': share(lambda r: r['domain'] != 'other'),
}
print('FINAL', json.dumps(summary))
print(f'dropped {len(dropped)}:', json.dumps(dropped, indent=1)[:3000])
(OUT / 'README.md').write_text(f"""# SWE-rebench Python tasks, re-gated for the Gemma 4 Developer Agent harness

{len(F)} Python bug-fix / feature tasks from {summary['repos']} GitHub repositories, rebuilt from
[nebius/SWE-rebench](https://huggingface.co/datasets/nebius/SWE-rebench) (CC-BY-4.0) for offline agent runs with the
competition harness (swegemma, subprocess sandbox) on Python {sys.version_info.major}.{sys.version_info.minor}.

Every task passed, offline (internet off), the harness's own `verify_task`: the reference fix PASSES (3 times when
built), an empty patch FAILS. Snapshots hold the repository at `base_commit` with its history up to that commit
only (checked: one branch, no remote, nothing unreachable).

Layout (same as rodrigospalma/ood45-bugfix-split, so its tools/ood45_harness.py loads it):
- `tasks.jsonl`: one task per line. `problem_statement` = the text the agent sees: the issue (`text_kind` = issue)
  or the pull request's title + description (`pr`). Labels: `domain` (from GitHub topics), `level` (`core dN` =
  <=130 changed lines with Nebius difficulty N, `large` = 131-500), `leak` (the text gives away part of the fix,
  OOD-45 checker), `unfair_names` (names the tests need that the fix creates and the text never mentions),
  `env_partial` (the editable install failed but the tests import the repo from its root), `gate` (verdicts).
- `snapshots/<instance_id>.tgz`: the repository at `base_commit`.
- `wheels/house/*.whl` + `wheels/{WHEEL_SET}/manifest.json`: every task's dependencies as wheels.
- `wheels/host/*.whl`: pytest plugins to install on the host (the harness leaves them out of task wheel sets).

Summary: {json.dumps(summary)}

Licenses: task metadata from SWE-rebench (CC-BY-4.0); each snapshot keeps its repository's own license (field
`license`, permissive only). Not competition data.
""")
snap_gb = sum(p.stat().st_size for p in (OUT / 'snapshots').glob('*.tgz')) / 1e9
house_gb = sum(p.stat().st_size for p in HOUSE.glob('*.whl')) / 1e9
shutil.rmtree('/tmp/rb_gate_results', ignore_errors=True)
print(f"wrote {OUT}: {len(F)} tasks | snapshots {snap_gb:.2f} GB | wheels {len(need)} {house_gb:.2f} GB | "
      f"session {(time.time() - T_START) / 3600:.1f} h")
'''


OFFLINE_HOOK = r'''
# OFFLINE FAIL-FAST (verify run 1, 2026-10-21: with Kaggle's internet off, a connection to the outside HANGS until the
# TCP timeout instead of failing, so installs (setup.py develop -> easy_install) and network-touching tests took 7-14
# min per task; ETA 20 h). A .pth hook in each sandbox venv makes every non-local connect / DNS lookup fail at once
# with "Network is unreachable", as in an offline Docker sandbox (--network none). Loopback stays allowed (local test
# servers). Applies to every Python process that uses the sandbox venv; the harness itself is not affected.
OFFLINE_MODULE = """import errno, ipaddress, socket
_connect, _connect_ex, _getaddrinfo = socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo
_LOCAL_NAMES = {'localhost', 'localhost.localdomain', '', None, socket.gethostname()}


def _local_host(host):
    if isinstance(host, bytes):
        host = host.decode()
    if host in _LOCAL_NAMES:
        return True
    try:
        ip = ipaddress.ip_address(host.split('%')[0])
        return ip.is_loopback or ip.is_unspecified
    except ValueError:
        return False


def _blocked(sock, addr):
    return sock.family in (socket.AF_INET, socket.AF_INET6) and isinstance(addr, tuple) and not _local_host(addr[0])


def connect(self, addr):
    if _blocked(self, addr):
        raise OSError(errno.ENETUNREACH, 'Network is unreachable (offline sandbox)')
    return _connect(self, addr)


def connect_ex(self, addr):
    return errno.ENETUNREACH if _blocked(self, addr) else _connect_ex(self, addr)


def getaddrinfo(host, *args, **kwargs):
    if not _local_host(host):
        raise socket.gaierror(socket.EAI_NONAME, 'Name or service not known (offline sandbox)')
    return _getaddrinfo(host, *args, **kwargs)


socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo = connect, connect_ex, getaddrinfo
"""
_shadow_plugins = shadow_host_plugins


def shadow_host_plugins(site):
    (site / '_rb_offline.py').write_text(OFFLINE_MODULE)
    (site / 'zz_rb_offline.pth').write_text('import _rb_offline\n')
    return _shadow_plugins(site) + ['(offline fail-fast hook)']


ood._shadow_host_plugins = shadow_host_plugins
'''


def gate_cell():
    """The full build's gate cell, adapted: offline (host plugins were installed in cell 3; network fails fast in the
    sandbox), pilot tasks need gold to pass 3 times (they were gated once), the other tasks once more (they passed 3
    times when built)."""
    src = M.CELL4
    i = src.index("_plugins = sorted(")
    j = src.index("def import_name(r):")
    src = src[:i] + "# (host pytest plugins: installed offline in cell 3)\n\n\n" + src[j:]
    reps = [
        ("# 4. GATE, 3 tasks at a time", "# 5. RE-GATE OFFLINE, 3 tasks at a time"),
        ("for label, patch in (('gold', r['patch']), ('empty', ''), ('gold', r['patch']), ('gold', r['patch'])):",
         "for label, patch in (('gold', r['patch']), ('empty', '')) + (('gold', r['patch']),) * (N_GOLD[iid] - 1):"),
        ("row['usable'] = row['gold_runs'] == ['PASS'] * 3 and row.get('empty') == 'FAIL'",
         "row['usable'] = row['gold_runs'] == ['PASS'] * N_GOLD[iid] and row.get('empty') == 'FAIL'"),
        ("GATE = OUT / 'gate.json'", "N_GOLD = {i: 3 if SEL[i]['source'] == 'pilot' else 1 for i in SEL}\nGATE = OUT / 'gate.json'"),
        ("if built.get(i, {}).get('snapshot') and i not in gate:", "if i not in SNAP_BAD and i not in gate:"),
        ("ood._shadow_host_plugins = shadow_host_plugins\n", "ood._shadow_host_plugins = shadow_host_plugins\n" + OFFLINE_HOOK),
    ]
    for old, new in reps:
        assert src.count(old) == 1, old[:60]
        src = src.replace(old, new)
    return src


def main():
    # --test: the TEST set (assemble_rebench.py --test, repos in no training source) -> kaggle/cells_rebench_test_verify;
    # same inputs and cells, only the embedded selection differs.
    test = "--test" in sys.argv
    sel = json.load(open(ROOT / ("data/rebench_test" if test else "data/rebench_final") / "selection.json"))
    out = ROOT / "kaggle/cells_rebench_test_verify" if test else OUT_DIR
    expect = EXPECT_USABLE
    if "--new" in sys.argv:  # parts 3/4 (assemble_rebench.py --new <p3> <p4> first): their usable counts from the outputs
        i = sys.argv.index("--new")
        sel = json.load(open(ROOT / "data/rebench_new/selection.json"))
        out = ROOT / "kaggle/cells_rebench_new_verify"
        expect = {part: sum(1 for l in open(Path(d) / "rebench/tasks.jsonl") if json.loads(l)["gate"].get("usable"))
                  for part, d in (("3", sys.argv[i + 1]), ("4", sys.argv[i + 2]))}
    out.mkdir(parents=True, exist_ok=True)
    (out / "cell1.py").write_text((ROOT / "kaggle/cells_rebench_pilot/cell1.py").read_text())
    (out / "cell2.py").write_text(CELL2.format(expect=expect, selection=repr(sel)))
    (out / "cell3_assemble.py").write_text(CELL3)
    (out / "cell4_snapshots.py").write_text(CELL4_SNAP)
    (out / "cell5_gate.py").write_text(gate_cell())
    (out / "cell6_finish.py").write_text(CELL6)
    print("wrote", out.relative_to(ROOT), sorted(p.name for p in out.iterdir()), len(sel), "tasks")


if __name__ == "__main__":
    main()
