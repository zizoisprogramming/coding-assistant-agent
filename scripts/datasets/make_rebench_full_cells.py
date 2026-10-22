"""Writes kaggle/cells_rebench_full_p1/ and _p2/: the FULL build of our own SWE-rebench task set (option B), in two
CPU notebooks over disjoint halves of the candidate repositories (a repo's tasks all land in the same part).

    .venv/bin/python scripts/datasets/make_rebench_full_cells.py [--n 350]

Same pipeline as the pilot (scripts/datasets/make_rebench_cells.py; pilot 2 on 2026-10-20: 23/40 usable), scaled up:
  cell 2   inputs + this part's candidate pool (embedded) + its SWE-rebench rows (HF parquet, downloaded on Kaggle)
  cell 2b  GitHub: each pool repo's topics/description -> domain bucket (public-like = web/API, HTTP clients,
           CLI/terminal, data models; else other); SELECT n tasks: 80% public-like / 20% other (user 2026-10-20),
           10% large tier, core strata in the pool's difficulty proportions, at most 3 tasks per repo (one task
           from every repo first); then each selected task's PR title + description
  cell 3   BUILD (as the pilot): snapshot at base_commit with history up to it, every pin as a wheel for this
           machine (download / build from sdist / same-major bump); snapshots over 150 MB are dropped
  cell 4   GATE, 3 tasks at a time (one per repo at a time: the install step's import name is per repo): gold must
           PASS 3 times (flaky tests are dropped), empty must FAIL; env_partial = the editable install failed but
           the tests still ran (they import from the repo root)
  cell 5   LEAKAGE (OOD-45 checker) of the issue text and the PR text of every usable task
  cell 6   FINISH: summary, tasks.jsonl (usable tasks only, all labels), prune unusable snapshots and unused wheels
Output /kaggle/working/rebench/ in the OOD-45 layout. Which text each task uses (issue vs PR, to hit the public
34% leak share) and the unfair-test labels are decided later, over both parts together, in the offline
verification notebook.
Resume: attach this same notebook's earlier output (same part) as an input and re-run; built and gated tasks are kept.
"""
import argparse
import collections
import json
import random
import re
import sys
import zlib
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
HEAVY = re.compile(r"^(torch|tensorflow|jax|jaxlib|pyspark|mxnet|paddlepaddle|onnxruntime|cupy|nvidia-)", re.I)
PILOT_DIR = ROOT / "data/results/2026-10-21_rebench_pilot2/rebench/tasks.jsonl"
PART1_OUT = ROOT / "data/results/2026-10-21_rebench_full_new-data/rebench"  # part 1's output (Kaggle: ziad23samer/new-data)


def pool_of(part):
    """This part's candidates: no FAIL_TO_FAIL / PASS_TO_FAIL, no heavy frameworks, not a pilot task, repo in this half."""
    cand = [json.loads(l) for l in open(ROOT / "data/swe_rebench/candidates.jsonl")]
    f2f = {r["instance_id"]: (len(r["FAIL_TO_FAIL"] or []), len(r["PASS_TO_FAIL"] or []))
           for r in pq.read_table(ROOT / "data/swe_rebench/test_f2f.parquet").to_pylist()}
    pilot = {json.loads(l)["instance_id"] for l in open(PILOT_DIR)}
    out = []
    for r in cand:
        if f2f[r["instance_id"]] != (0, 0) or r["instance_id"] in pilot:
            continue
        if any(HEAVY.match(line.strip()) for line in (r["requirements"] or "").splitlines()):
            continue
        if zlib.crc32(r["repo"].encode()) % 2 != part - 1:
            continue
        d = r["meta"]["llm_score"]["difficulty_score"]
        out.append((r["instance_id"], "large" if r["tier"] == "large" else f"core d{d}"))
    return sorted(out)


CELL2 = '''# 2. FULL BUILD part {part}: inputs, output layout, this part's candidate pool and its SWE-rebench rows.
#    CPU, INTERNET ON, secret GITHUB_TOKEN switched on for this notebook. See scripts/datasets/make_rebench_full_cells.py.
import collections, json, random, re, time, urllib.request
import pyarrow.parquet as pq

T_START = time.time()
DEADLINE_H = 10.5  # the gate starts no new task after this (Kaggle ends sessions at 12 h); cells 5-6 still run
PART, N_TARGET = {part!r}, {n}
MATCH_SHARE, CAP, SEED = {match_share}, {cap}, {seed}  # public-like share wanted; max new tasks per repo
WORKING_DIR = Path('/kaggle/working')
OUT = WORKING_DIR / 'rebench'  # the task set, OOD-45 layout
WHEEL_SET = f'{{__import__("platform").machine()}}-cp{{sys.version_info.major}}{{sys.version_info.minor}}'  # Kaggle: x86_64-cp313
HOUSE = OUT / 'wheels' / 'house'


def _first(*cands, pattern=None):
    for c in cands:
        if Path(c).exists():
            return Path(c)
    hits = sorted(glob.glob(pattern, recursive=True)) if pattern else []
    if not hits:
        print('attached inputs (3 levels):', sorted(glob.glob('/kaggle/input/*/*/*'))[:40])
    assert hits, f'none of {{cands}} exists: attach it as a notebook input'
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
(OUT / 'part.json').write_text(json.dumps({{'part': PART, 'n_target': N_TARGET}}))
try:
    urllib.request.urlopen('https://pypi.org/simple/pip/', timeout=20)
except Exception as e:
    raise RuntimeError(f'no internet ({{e!r}}): turn Settings -> Internet on, then re-run this cell')
try:
    from kaggle_secrets import UserSecretsClient
    GH_TOKEN = UserSecretsClient().get_secret('GITHUB_TOKEN')
except Exception as e:
    GH_TOKEN = None
assert GH_TOKEN, ('GITHUB_TOKEN secret is not attached: in the editor, Add-ons -> Secrets -> switch GITHUB_TOKEN on for '
                  'THIS notebook, then re-run this cell (the full build makes ~800 GitHub calls; 60/hour without it)')

POOL = {pool!r}  # (instance_id, level): 'core dN' = <=130 changed lines, Nebius difficulty N; 'large' = 131-500 lines
LEVEL = dict(POOL)
COLS = ['instance_id', 'repo', 'base_commit', 'created_at', 'problem_statement', 'hints_text', 'patch', 'test_patch',
        'FAIL_TO_PASS', 'PASS_TO_PASS', 'install_config', 'requirements', 'license_name', 'meta']
ROWS = {{}}
for part in ('test-00000-of-00002.parquet', 'test-00001-of-00002.parquet'):
    dst = Path('/tmp/rebench_src') / part
    dst.parent.mkdir(exist_ok=True)
    if not dst.exists():
        t0 = time.time()
        urllib.request.urlretrieve(f'https://huggingface.co/datasets/nebius/SWE-rebench/resolve/main/data/{{part}}', dst)
        print(f'downloaded {{part}} ({{dst.stat().st_size / 1e6:.0f}} MB, {{time.time() - t0:.0f}} s)')
    for r in pq.read_table(dst, columns=COLS).to_pylist():
        if r['instance_id'] in LEVEL:
            ROWS[r['instance_id']] = r
missing = sorted(set(LEVEL) - set(ROWS))
assert not missing, f'pool ids not found in SWE-rebench: {{missing[:5]}}'
print(f'part {{PART}}: pool {{len(POOL)}} tasks from {{len({{r["repo"] for r in ROWS.values()}})}} repos | levels',
      dict(sorted(collections.Counter(LEVEL.values()).items())), '| target', N_TARGET)
'''

CELL2B = r'''# 2b. Domains (GitHub topics) -> SELECT this part's tasks -> their PR texts. One line per repo / task.
import concurrent.futures as cf, urllib.error


def gh(path, tries=4):
    for k in range(tries):
        req = urllib.request.Request('https://api.github.com' + path, headers={
            'Accept': 'application/vnd.github+json', **({'Authorization': f'Bearer {GH_TOKEN}'} if GH_TOKEN else {})})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r), r.headers.get('X-RateLimit-Remaining')
        except urllib.error.HTTPError as e:
            if e.code in (403, 429, 500, 502, 503) and k < tries - 1:
                time.sleep(20 * (k + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            if k == tries - 1:
                raise
            time.sleep(10)


# Public-like domains: what the graded tasks are (fastapi = web/API framework, rich = terminal rendering,
# requests/httpx = HTTP clients) plus the libraries they lean on (pydantic-style data models / config / parsing).
DOMAINS = {
    'web_api': {'web', 'api', 'rest', 'restful', 'rest-api', 'asgi', 'wsgi', 'web-framework', 'flask',
                'django', 'fastapi', 'starlette', 'aiohttp', 'tornado', 'sanic', 'graphql', 'openapi', 'swagger',
                'websocket', 'websockets', 'server', 'http-server', 'backend', 'microservice', 'webapp', 'jinja2'},
    'http_client': {'http', 'http-client', 'client', 'requests', 'httpx', 'urllib3', 'sdk', 'api-client',
                    'api-wrapper', 'wrapper', 'oauth', 'oauth2', 'scraping', 'scraper',
                    'crawler', 'streaming', 'proxy', 'webhook'},
    'cli_terminal': {'cli', 'terminal', 'console', 'command-line', 'commandline', 'command-line-tool', 'tui', 'shell',
                     'ansi', 'color', 'colors', 'progress', 'progress-bar', 'pretty-print', 'formatting',
                     'formatter', 'markdown', 'table', 'tables', 'logging', 'argparse', 'click', 'prompt', 'repl'},
    'data_models': {'validation', 'serialization', 'deserialization', 'json', 'schema', 'json-schema', 'pydantic',
                    'dataclasses', 'dataclass', 'config', 'configuration', 'settings', 'yaml', 'toml', 'typing',
                    'type-hints', 'marshmallow', 'attrs', 'orm', 'parser', 'parsing', 'template', 'templating'},
}


def domain_of(info, repo):
    if not info or info.get('missing'):
        return 'other', []
    topics = [t.lower() for t in info.get('topics') or []]
    desc = re.sub(r'https?://\S+', ' ', info.get('description') or '')  # a URL's 'http' says nothing about the domain
    words = re.findall(r'[a-z0-9]+(?:-[a-z0-9]+)*', (desc + ' ' + repo.split('/')[1]).lower())
    words += [a + '-' + b for a, b in zip(words, words[1:])]
    score = {d: 2 * sum(t in kw for t in topics) + sum(w in kw for w in words) for d, kw in DOMAINS.items()}
    best = max(score, key=score.get)
    hits = sorted({t for t in topics + words for kw in DOMAINS.values() if t in kw})
    return (best if score[best] >= 1 else 'other'), hits


REPO_LOG = OUT / 'repos.jsonl'
REPO_INFO = {json.loads(l)['repo']: json.loads(l)['info'] for l in open(REPO_LOG)} if REPO_LOG.exists() else {}


def repo_info(repo):
    if repo in REPO_INFO:
        return REPO_INFO[repo]
    try:
        d, _ = gh(f'/repos/{repo}')
        info = {k: d.get(k) for k in ('full_name', 'description', 'topics', 'archived', 'fork', 'stargazers_count', 'language')}
        info['source'] = (d.get('source') or {}).get('full_name')
        if d.get('fork') and info['source']:  # moved repo: the name now holds a fork; the topics live in the source
            s, _ = gh(f"/repos/{info['source']}")
            info['topics'], info['description'] = s.get('topics'), s.get('description') or info['description']
    except urllib.error.HTTPError as e:
        info = {'missing': True, 'http': e.code}
    except Exception as e:
        info = {'missing': True, 'error': f'{type(e).__name__}: {str(e)[:100]}'}
    with open(REPO_LOG, 'a') as fh:
        fh.write(json.dumps({'repo': repo, 'info': info}) + '\n')
    return info


repos = sorted({r['repo'] for r in ROWS.values()})
t0 = time.time()
with cf.ThreadPoolExecutor(8) as ex:
    for k, (repo, info) in enumerate(zip(repos, ex.map(repo_info, repos)), 1):
        REPO_INFO[repo] = info
        dom, hits = domain_of(info, repo)
        print(f"[repo {k:3}/{len(repos)}] {repo[:45]:45} {dom:12} | {', '.join(hits[:6])}"
              + (f" | MISSING {info}" if info.get('missing') else ''), flush=True)
DOMAIN = {r: domain_of(REPO_INFO[r], r)[0] for r in repos}
print(f'repos classified in {time.time() - t0:.0f}s:', dict(collections.Counter(DOMAIN.values())))
print('pool tasks by domain:', dict(collections.Counter(DOMAIN[ROWS[i]['repo']] for i in LEVEL)))

# SELECT: one task from every repo first, then a 2nd, ... (max CAP new tasks per repo), under two quotas:
# level (10% large; core strata in the pool's difficulty proportions) and domain (MATCH_SHARE public-like).
rng = random.Random(SEED)
ids = sorted(LEVEL)
rng.shuffle(ids)
nth, seen = {}, collections.Counter()
for i in ids:
    seen[ROWS[i]['repo']] += 1
    nth[i] = seen[ROWS[i]['repo']]
order = sorted(ids, key=lambda i: nth[i])  # stable: random within each round
n_large = round(0.10 * N_TARGET)
core = collections.Counter(v for v in LEVEL.values() if v != 'large')
lv_want = {lv: round((N_TARGET - n_large) * c / sum(core.values())) for lv, c in core.items()}
lv_want['core d1'] = lv_want.get('core d1', 0) + N_TARGET - n_large - sum(lv_want.values())
lv_want['large'] = n_large
dom_want = {'match': round(MATCH_SHARE * N_TARGET), 'other': N_TARGET - round(MATCH_SHARE * N_TARGET)}
dkind = lambda i: 'other' if DOMAIN[ROWS[i]['repo']] == 'other' else 'match'  # noqa: E731
chosen, per_repo = [], collections.Counter()
for strict_level, strict_domain in ((True, True), (True, False), (False, False)):
    for i in order:
        if len(chosen) >= N_TARGET:
            break
        if i in chosen or per_repo[ROWS[i]['repo']] >= CAP:
            continue
        if strict_level and lv_want[LEVEL[i]] <= 0:
            continue
        if strict_domain and dom_want[dkind(i)] <= 0:
            continue
        chosen.append(i)
        per_repo[ROWS[i]['repo']] += 1
        lv_want[LEVEL[i]] -= 1
        dom_want[dkind(i)] -= 1
    print(f'after pass (level quota={strict_level}, domain quota={strict_domain}): {len(chosen)} chosen | '
          f'unfilled level {dict((k, v) for k, v in lv_want.items() if v > 0)} domain {dict((k, v) for k, v in dom_want.items() if v > 0)}')
TASKS = sorted((i, LEVEL[i]) for i in chosen)
for i in chosen:
    ROWS[i]['domain'] = DOMAIN[ROWS[i]['repo']]
    ROWS[i]['topics'] = (REPO_INFO[ROWS[i]['repo']] or {}).get('topics') or []
print(f'SELECTED {len(TASKS)} tasks from {len(per_repo)} repos | levels', dict(sorted(collections.Counter(l for _, l in TASKS).items())),
      '| domains', dict(collections.Counter(ROWS[i]['domain'] for i in chosen)),
      f"| public-like {100 * sum(dkind(i) == 'match' for i in chosen) / max(len(chosen), 1):.0f}%",
      '| tasks per repo', dict(sorted(collections.Counter(per_repo.values()).items())))


def leak_flags(text, patch):
    low = text.lower()
    files = re.findall(r'^\+\+\+ b/(\S+)', patch, re.M)
    added = [l[1:].strip() for l in patch.splitlines() if l.startswith('+') and not l.startswith('+++')]
    removed = '\n'.join(l[1:] for l in patch.splitlines() if l.startswith('-') and not l.startswith('---'))
    new_defs = {m for l in added for m in re.findall(r'^(?:async\s+)?(?:def|class)\s+(\w+)', l) if m not in removed}
    return {'file': any(Path(f).name.lower() in low for f in files),
            'code_line': any(len(l) >= 20 and not l.startswith('#') and l in text for l in added),
            'new_def': sorted(d for d in new_defs if re.search(rf'\b{re.escape(d)}\b', text))}


PR_LOG = OUT / 'pr.jsonl'
PR_DONE = {json.loads(l)['id']: json.loads(l)['pr'] for l in open(PR_LOG)} if PR_LOG.exists() else {}


def pr_text(iid):
    if iid in PR_DONE:
        return PR_DONE[iid], 'cached'
    r, num = ROWS[iid], int(iid.rsplit('-', 1)[1])
    try:
        info = REPO_INFO.get(r['repo']) or {}
        try:
            d, left = gh(f"/repos/{r['repo']}/pulls/{num}")
        except urllib.error.HTTPError as e:
            # Moved repo: the name now holds a fork and the PRs live in its source, or the repo was renamed.
            moved = info.get('source') or info.get('full_name') or r['repo']
            if e.code != 404 or moved.lower() == r['repo'].lower():
                raise
            d, left = gh(f'/repos/{moved}/pulls/{num}')
        text = ((d.get('title') or '').strip() + '\n\n' + (d.get('body') or '').strip()).strip()
        pr = {'number': num, 'title': d.get('title'), 'body': d.get('body') or '', 'merged': bool(d.get('merged_at')),
              'text': text, 'leak': leak_flags(text, r['patch'])}
    except Exception as e:
        pr, left = None, f'{type(e).__name__}: {str(e)[:120]}'
    with open(PR_LOG, 'a') as fh:
        fh.write(json.dumps({'id': iid, 'pr': pr}) + '\n')
    return pr, left


with cf.ThreadPoolExecutor(8) as ex:
    for k, (iid, (pr, left)) in enumerate(zip([i for i, _ in TASKS], ex.map(lambda t: pr_text(t[0]), TASKS)), 1):
        ROWS[iid]['pr'] = pr
        print(f"[pr {k:3}/{len(TASKS)}] {iid[:44]:44} " + (
            f"merged={pr['merged']!s:5} body={len(pr['body']):5} | {(pr['title'] or '')[:60]!r} (rate left {left})"
            if pr else f'FAILED {left}'), flush=True)
got = [ROWS[i]['pr'] for i, _ in TASKS if ROWS[i].get('pr')]
print(f'PR texts: {len(got)}/{len(TASKS)} | merged {sum(p["merged"] for p in got)} | empty description '
      f'{sum(not p["body"].strip() for p in got)} | names a patched file {sum(p["leak"]["file"] for p in got)} | '
      f'quotes added code {sum(p["leak"]["code_line"] for p in got)} | names a new def/class {sum(bool(p["leak"]["new_def"]) for p in got)}')
'''


def build_cell():
    """The pilot's cell 3, retargeted: TASKS instead of PILOT, gated tasks are not rebuilt (their snapshots may be
    pruned), snapshots over SNAP_CAP_MB are dropped, the log names the real wheel set."""
    src = (ROOT / "kaggle/cells_rebench_pilot/cell3_build.py").read_text()
    reps = [
        ("# 3. BUILD: snapshot + offline wheels per task (network bound, 8 at a time). One line per task; resumes after a restart.",
         "# 3. BUILD: snapshot + offline wheels per task (network bound, 8 at a time). One line per task; resumes after a restart.\n"
         "#    Same as the pilot's cell 3; snapshots over SNAP_CAP_MB are dropped (disk: /kaggle/working holds 20 GB)."),
        ("print(f'resume: {len(built)} tasks",
         "SNAP_CAP_MB = 150\nGATED = set(json.loads((OUT / 'gate.json').read_text())) if (OUT / 'gate.json').exists() else set()\n"
         "print(f'resume: {len(built)} tasks"),
        ("    tgz = OUT / 'snapshots' / f'{iid}.tgz'\n    code, log = sh(f'tar czf {tgz} -C {d} .')\n    shutil.rmtree(d, ignore_errors=True)\n    if code:\n        return None, 'tar failed: ' + log[-200:]\n",
         "    tgz = OUT / 'snapshots' / f'{iid}.tgz'\n    code, log = sh(f'tar czf {tgz} -C {d} .')\n    shutil.rmtree(d, ignore_errors=True)\n    if code:\n        return None, 'tar failed: ' + log[-200:]\n"
         "    if tgz.stat().st_size > SNAP_CAP_MB * 1e6:\n        mb = tgz.stat().st_size / 1e6\n        tgz.unlink()\n        return None, f'snapshot too big ({mb:.0f} MB > {SNAP_CAP_MB})'\n"),
        ("todo = [i for i, _ in PILOT if i not in built]", "todo = [i for i, _ in TASKS if i not in built and i not in GATED]"),
        ("as Linux/CPython 3.12 wheels", "as {WHEEL_SET} wheels"),
    ]
    for old, new in reps:
        assert src.count(old) == 1, old[:60]
        src = src.replace(old, new)
    assert "PILOT" not in src
    return src


CELL4 = r'''# 4. GATE, 3 tasks at a time (never two of one repo: the install step's import name is per repo). Per task: gold
#    must PASS, empty must FAIL, then gold twice more (flaky tests -> dropped). Subprocess sandbox with ood45_harness's
#    install step, as the pilot. One line per task; resumes (rebench/gate.json).
import asyncio, contextvars, gc, logging, tarfile, tempfile, warnings
warnings.filterwarnings('ignore')
logging.getLogger('swegemma.sandbox.subprocess').setLevel(logging.ERROR)
from adk_submission import ModelRegistry
from swegemma.config import EvalConfig
from swegemma.evaluate import Evaluator
from swegemma.harness.verification import verify_task
from swegemma.models import Task

sys.path.insert(0, str(OOD_DIR / 'tools'))
import ood45_harness as ood  # noqa: E402
print('swegemma', ood.check_swegemma())
ood._STATE['house'] = OOD_DIR / 'wheels' / 'house'  # the Docker image's extras (pytest-timeout, hatchling, ...)
ood.ENV_LOG['path'] = str(OUT / 'gate_env_install.jsonl')
ood.patch_harness()

# Host-only pytest plugins (Kaggle image, not the scoring image) are hidden in each sandbox venv (pilot 1: typeguard's
# plugin broke 16/40 tasks), unless the task ships that distribution itself.
import importlib.metadata as _md
KEEP_PLUGIN_DISTS = {'pytest', 'pytest-timeout', 'pytest-asyncio', 'pytest-xdist', 'pytest-httpbin', 'anyio'}
HOST_PLUGINS = sorted({(ep.value.split(':')[0], (ep.dist.name if ep.dist else '').lower().replace('_', '-'))
                       for ep in _md.entry_points(group='pytest11')})
print('host pytest plugins:', HOST_PLUGINS)


def shadow_host_plugins(site):
    shadowed = []
    for module, dist in HOST_PLUGINS:
        if dist in KEEP_PLUGIN_DISTS or list(site.glob(f"{dist.replace('-', '_')}-*.dist-info")):
            continue
        parts = module.split('.')
        if (site / parts[0]).exists() or (site / f'{parts[0]}.py').exists():
            continue
        if len(parts) == 1:
            (site / f'{parts[0]}.py').write_text('# hidden by the gate: host-only pytest plugin\n')
        else:
            pkg = site.joinpath(*parts[:-1])
            pkg.mkdir(parents=True, exist_ok=True)
            for k in range(1, len(parts)):
                site.joinpath(*parts[:k], '__init__.py').touch()
            (pkg / f'{parts[-1]}.py').write_text('# hidden by the gate: host-only pytest plugin\n')
        shadowed.append(module)
    return shadowed


ood._shadow_host_plugins = shadow_host_plugins
# Tag every install record with the task being gated (the sandbox threads inherit this context) -> env_partial.
CUR_TASK = contextvars.ContextVar('gate_task', default=None)
ENV_BY_TASK = collections.defaultdict(list)
_orig_log_env = ood._log_env


def _log_env(record):
    record['task'] = CUR_TASK.get()
    ENV_BY_TASK[record['task']].append(record)
    _orig_log_env(record)


ood._log_env = _log_env
# The harness caches one unpacked-wheel tar per wheel set (in /tmp; hundreds of MB each). Record which tars each
# running task uses so the cleanup after each task deletes only tars no running task needs (lock: no task can pick
# up a tar between the cleanup's check and its delete).
import threading
from swegemma.harness import container_setup as _cs
TAR_LOCK, TAR_USERS = threading.Lock(), collections.defaultdict(set)
_orig_tar = _cs._build_unpacked_wheels_tar


def _tar(selected, cache_name, marker):
    with TAR_LOCK:
        p = _orig_tar(selected, cache_name, marker)
        TAR_USERS[Path(p)].add(CUR_TASK.get())
        return p


_cs._build_unpacked_wheels_tar = _tar
WHEEL_ROOT = Path('/tmp/rb_wheels')
ood.materialize_wheels(OUT, WHEEL_SET, WHEEL_ROOT / WHEEL_SET)

_plugins = sorted({m.group(1).lower().replace('_', '-') for i, _ in TASKS for m in
                   re.finditer(r'(?m)^(pytest[-_](?:asyncio|xdist|httpbin|timeout))==', ROWS[i]['requirements'] or '')})
if _plugins:
    print('host pytest plugins:', _plugins, sh(f'{sys.executable} -m pip install -q ' + ' '.join(_plugins))[0])


def import_name(r):
    """The package that holds the first patched source file (deepest directory with an __init__.py, src/ aware),
    read from the snapshot; single-file modules -> their name; fallback: the repo name."""
    tgz = OUT / 'snapshots' / f"{r['instance_id']}.tgz"
    names = set()
    if tgz.exists():
        with tarfile.open(tgz) as tf:
            names = {m.name[2:] if m.name.startswith('./') else m.name for m in tf if m.name.endswith('__init__.py')}
    skip = ('tests/', 'test/', 'testing/', 'docs/', 'doc/', 'examples/', 'example/', 'scripts/', 'tools/', 'benchmarks/')
    for f in re.findall(r'^diff --git a/(\S+)', r['patch'], re.M):
        if not f.endswith('.py') or f.startswith(skip) or '/tests/' in f:
            continue
        root, parts = ('src/', f.split('/')[1:]) if f.startswith('src/') else ('', f.split('/'))
        if len(parts) == 1:
            return parts[0][:-3]
        for k in range(len(parts) - 1, 0, -1):
            if root + '/'.join(parts[:k]) + '/__init__.py' in names:
                return '.'.join(parts[:k])
    return r['repo'].split('/')[1].lower().replace('-', '_')


def as_task(r):
    return Task(instance_id=r['instance_id'], repo=r['repo'], base_commit=r['base_commit'],
                problem_statement=r['problem_statement'], patch=r['patch'], test_patch=r['test_patch'],
                hints_text='', created_at=r['created_at'], FAIL_TO_PASS=tuple(r['FAIL_TO_PASS']),
                PASS_TO_PASS=tuple(r['PASS_TO_PASS']))


GATE = OUT / 'gate.json'
gate = json.loads(GATE.read_text()) if GATE.exists() else {}
RUNNING = {}  # task -> start time; caches older than the oldest running task are deleted
CACHE_DIR = Path(tempfile.gettempdir()) / 'swegemma_sp_cache_v8'


def clean_tmp():
    """Delete the wheel tars no running task uses, and sandbox / staging dirs created before the oldest running
    task started (a running task's own dirs are newer than its start)."""
    oldest = min(RUNNING.values(), default=time.time()) - 5
    with TAR_LOCK:
        for p in list(TAR_USERS):
            TAR_USERS[p] &= set(RUNNING)
            if not TAR_USERS[p]:
                p.unlink(missing_ok=True)
                del TAR_USERS[p]
    for p in list(CACHE_DIR.glob('staging_*')) + [Path(p) for p in glob.glob('/tmp/swegemma_sandbox_*')]:
        try:
            if p.stat().st_mtime < oldest:
                shutil.rmtree(p, ignore_errors=True)
        except FileNotFoundError:
            pass


def tail(text, n=6):
    return ' / '.join((text or '').strip().splitlines()[-n:])[-600:]


async def run_patch(cfg, ev, task, iid, patch):
    t0 = time.perf_counter()
    try:
        res = await verify_task(ev.docker, cfg, task, OUT / 'snapshots' / f'{iid}.tgz', agent_patch=patch, start_time=t0)
        return ('PASS' if res.resolved else 'FAIL'), res, round(time.perf_counter() - t0), None
    except Exception as e:
        return 'ERROR', None, round(time.perf_counter() - t0), f'{type(e).__name__}: {str(e)[:400]}'


async def gate_task(iid):
    r = ROWS[iid]
    CUR_TASK.set(iid)
    ood.IMPORT_NAMES[r['repo']] = import_name(r)
    cfg = EvalConfig(tasks_path=DATA_DIR / 'tasks.jsonl', snapshots_dir=OUT / 'snapshots', results_dir=Path('/tmp/rb_gate_results'),
                     submission_dir=DATA_DIR / 'sample_submission', models=ModelRegistry(), sandbox='subprocess',
                     wheels_dir=WHEEL_ROOT / WHEEL_SET / iid, timeout_seconds=600)
    ev, task, row = Evaluator(cfg), as_task(r), {'import': ood.IMPORT_NAMES[r['repo']], 'gold_runs': []}
    for label, patch in (('gold', r['patch']), ('empty', ''), ('gold', r['patch']), ('gold', r['patch'])):
        verdict, res, secs, err = await run_patch(cfg, ev, task, iid, patch)
        row[label + '_s'] = row.get(label + '_s', 0) + secs
        if label == 'empty':
            row['empty'] = verdict
            if verdict != 'FAIL':
                row['why'] = 'the empty patch passes' if verdict == 'PASS' else err
                break
            continue
        row['gold_runs'].append(verdict)
        if verdict != 'PASS':
            out = (res.test_output or '') if res else ''
            row['why'] = err if err else (res.error or '')[:300]
            row['tail'] = tail(out)
            row['missing_modules'] = sorted(set(re.findall(r"No module named '([A-Za-z0-9_.]+)", out)))
            break
    row['gold'] = 'PASS' if row['gold_runs'] and all(v == 'PASS' for v in row['gold_runs']) else 'FAIL'
    row['flaky'] = row['gold_runs'][:1] == ['PASS'] and row['gold'] == 'FAIL'  # passed once, failed on a rerun
    row['usable'] = row['gold_runs'] == ['PASS'] * 3 and row.get('empty') == 'FAIL'
    recs = ENV_BY_TASK.pop(iid, [])
    row['env_partial'] = any(rec['editable'] and rec['editable'][-1]['exit'] != 0 for rec in recs)
    return row


async def gate_all(ids):
    sem, locks, done = asyncio.Semaphore(3), collections.defaultdict(asyncio.Lock), [0]

    async def one(iid):
        async with locks[ROWS[iid]['repo']]:
            async with sem:
                if time.time() - T_START > DEADLINE_H * 3600:
                    return
                RUNNING[iid] = time.time()
                try:
                    row = await gate_task(iid)
                finally:
                    RUNNING.pop(iid, None)
                gate[iid] = row
                GATE.write_text(json.dumps(gate, indent=1))
                done[0] += 1
                b = built[iid]
                el = (time.time() - t_g) / 60
                print(f"[{done[0]:3}/{len(ids)}] {iid[:44]:44} {LEVEL[iid]:7} gold {'/'.join(row['gold_runs']):14} "
                      f"empty {row.get('empty', '-'):5} usable={row['usable']!s:5}{' env_partial' if row['env_partial'] else ''}"
                      f" | {row.get('gold_s', 0) + row.get('empty_s', 0):4}s | pins failed {len(b['pins_failed'])} | "
                      f"{el:.0f} min, ETA {el / done[0] * (len(ids) - done[0]):.0f} min"
                      + (f"\n      why: {(row.get('why') or '')[:240]}\n      tail: {row.get('tail', '')[:300]}" if not row['usable'] else ''),
                      flush=True)
                clean_tmp()
                gc.collect()

    await asyncio.gather(*(one(i) for i in ids))


# Interleave repos so the per-repo locks rarely block a slot.
_by_repo = collections.defaultdict(list)
for i, _ in TASKS:
    if built.get(i, {}).get('snapshot') and i not in gate:
        _by_repo[ROWS[i]['repo']].append(i)
ids = [q[k] for k in range(CAP) for q in _by_repo.values() if k < len(q)]
print(f'gating {len(ids)} tasks ({len(gate)} already gated), 3 at a time', flush=True)
t_g = time.time()
try:
    asyncio.run(gate_all(ids))
except RuntimeError:  # notebook already has a running loop
    import nest_asyncio; nest_asyncio.apply(); asyncio.get_event_loop().run_until_complete(gate_all(ids))
skipped = [i for i in ids if i not in gate]
print(f'gate done in {(time.time() - t_g) / 60:.1f} min: usable {sum(g["usable"] for g in gate.values())}/{len(gate)}'
      + (f' | NOT GATED (deadline): {len(skipped)} -> re-run with this output attached' if skipped else ''))
'''

CELL5 = r'''# 5. LEAKAGE of every usable task's issue text and PR text: OOD-45's checker (tools/check_statement_leakage.py,
#    unchanged), base sources from the snapshots. Public target (measured in pilot 2): 44/129 = 34%.
sys.path.insert(0, str(OOD_DIR / 'tools'))
import check_statement_leakage as chk  # noqa: E402


def tar_sources(tgz):
    def base_sources(_iid, paths):
        out = {p: '' for p in paths}
        if not Path(tgz).exists():
            return out
        with tarfile.open(tgz) as tf:
            for m in tf:
                name = m.name[2:] if m.name.startswith('./') else m.name
                if name in out and m.isfile():
                    out[name] = tf.extractfile(m).read().decode('utf-8', 'replace')
        return out
    return base_sources


def residues(task, text, tgz):
    chk.base_sources = tar_sources(tgz)
    try:
        return [f.kind for f in chk.check_task(task, text or '', ()) if not f.allowed]
    except Exception as e:
        return [f'checker_error: {type(e).__name__}']


LEAK_FILE = OUT / 'leakage.json'
LEAK = json.loads(LEAK_FILE.read_text()) if LEAK_FILE.exists() else {}
usable = [i for i, _ in TASKS if gate.get(i, {}).get('usable')]
t0 = time.time()
for k, iid in enumerate(usable, 1):
    if iid in LEAK:
        continue
    r, tgz = ROWS[iid], OUT / 'snapshots' / f'{iid}.tgz'
    task = {**r, 'FAIL_TO_PASS': list(r['FAIL_TO_PASS'])}
    LEAK[iid] = {'issue': residues(task, r['problem_statement'], tgz),
                 'pr': residues(task, r['pr']['text'], tgz) if r.get('pr') else None}
    LEAK_FILE.write_text(json.dumps(LEAK, indent=1))
    print(f"[leak {k:3}/{len(usable)}] {iid[:44]:44} issue {sorted(set(LEAK[iid]['issue'])) or '-'} | pr "
          f"{sorted(set(LEAK[iid]['pr'] or [])) or ('-' if LEAK[iid]['pr'] is not None else 'no PR text')}", flush=True)
L = [LEAK[i] for i in usable if i in LEAK]
n = max(len(L), 1)
print(f'leakage checked in {time.time() - t0:.0f}s | usable {len(L)} | issue texts leak {sum(bool(x["issue"]) for x in L)} '
      f'({100 * sum(bool(x["issue"]) for x in L) / n:.0f}%) | PR texts leak {sum(bool(x["pr"]) for x in L if x["pr"] is not None)}'
      f'/{sum(x["pr"] is not None for x in L)} | both leak {sum(bool(x["issue"]) and bool(x["pr"]) for x in L)} | neither '
      f'{sum(not x["issue"] and x["pr"] is not None and not x["pr"] for x in L)} (public target 34%)')
'''

CELL6 = r'''# 6. FINISH: summary (paste this output to Claude), tasks.jsonl with the usable tasks and all labels, and pruning:
#    snapshots of unusable tasks and wheels no usable task needs are deleted (the output becomes the dataset).
rows = []
for iid, lv in TASKS:
    b, g = built.get(iid, {}), gate.get(iid, {})
    rows.append({'id': iid, 'level': lv, 'domain': ROWS[iid].get('domain'), 'snap': bool(b.get('snapshot')),
                 'gated': iid in gate, 'gold': g.get('gold', '-'), 'runs': '/'.join(g.get('gold_runs', [])),
                 'empty': g.get('empty', '-'), 'usable': bool(g.get('usable')), 'flaky': bool(g.get('flaky')),
                 'env_partial': bool(g.get('env_partial')),
                 'why': (g.get('why') or b.get('snapshot_error') or '')[:90]})
print(f"part {PART} | selected {len(rows)} | snapshot ok {sum(r['snap'] for r in rows)} | gated {sum(r['gated'] for r in rows)} "
      f"| usable {sum(r['usable'] for r in rows)} (env_partial {sum(r['usable'] and r['env_partial'] for r in rows)}) "
      f"| flaky dropped {sum(r['flaky'] for r in rows)}")
for key in ('level', 'domain'):
    print(f'usable by {key}:')
    for v in sorted({r[key] or '-' for r in rows}):
        sub = [r for r in rows if (r[key] or '-') == v]
        print(f"  {v:14} {sum(r['usable'] for r in sub):3}/{len(sub):3} usable")
U = [r for r in rows if r['usable']]
print(f"usable public-like domain share: {100 * sum(r['domain'] != 'other' for r in U) / max(len(U), 1):.0f}% (target 80%)")
reasons = collections.Counter()
for r in rows:
    if not r['usable']:
        w = r['why'].lower()
        reasons['snapshot: ' + r['why'][:40] if not r['snap'] else 'not gated (deadline)' if not r['gated'] else
                'flaky gold' if r['flaky'] else 'missing module' if 'no module' in w else
                'sandbox env' if 'sandboxenv' in w or 'importable' in w else 'empty patch passes' if r['empty'] == 'PASS'
                else 'tests fail with gold' if r['gold'] == 'FAIL' else 'harness error'] += 1
print('not usable, by first reason:', dict(reasons.most_common()))

with open(OUT / 'tasks.jsonl', 'w') as fh:
    for iid, lv in TASKS:
        g = gate.get(iid, {})
        if not g.get('usable'):
            continue
        r = ROWS[iid]
        fh.write(json.dumps({**{k: r[k] for k in ('instance_id', 'repo', 'base_commit', 'problem_statement', 'patch',
                                                  'test_patch', 'FAIL_TO_PASS', 'PASS_TO_PASS', 'created_at')},
                             'hints_text': '', 'license': r['license_name'], 'source': 'nebius/SWE-rebench (CC-BY-4.0)',
                             'python_original': r['install_config']['python'], 'level': lv, 'domain': r.get('domain'),
                             'topics': r.get('topics'), 'difficulty': r['meta']['llm_score']['difficulty_score'],
                             'pr': r.get('pr'), 'leak': LEAK.get(iid), 'env_partial': g.get('env_partial'),
                             'gate': g}) + '\n')
with open(OUT / 'gated_all.jsonl', 'w') as fh:  # every selected task's verdict (for the funnel; no texts)
    for r in rows:
        fh.write(json.dumps(r) + '\n')

# Prune: the dataset keeps only what the usable tasks need.
keep = {i for i, _ in TASKS if gate.get(i, {}).get('usable')}
for p in (OUT / 'snapshots').glob('*.tgz'):
    if p.stem not in keep:
        p.unlink()
manifest = {i: built[i]['wheels'] for i in sorted(keep)}
(OUT / 'wheels' / WHEEL_SET / 'manifest.json').write_text(json.dumps(manifest, indent=1))
need = {w for ws in manifest.values() for w in ws}
dropped = [p for p in HOUSE.glob('*.whl') if p.name not in need]
for p in dropped:
    p.unlink()
shutil.rmtree('/tmp/rb_gate_results', ignore_errors=True)
snap_gb = sum(p.stat().st_size for p in (OUT / 'snapshots').glob('*.tgz')) / 1e9
house_gb = sum(p.stat().st_size for p in HOUSE.glob('*.whl')) / 1e9
print(f"wrote {OUT / 'tasks.jsonl'}: {len(keep)} usable tasks | snapshots {snap_gb:.2f} GB | wheel house "
      f"{len(list(HOUSE.glob('*.whl')))} wheels {house_gb:.2f} GB ({len(dropped)} unused wheels deleted) | "
      f"session {(time.time() - T_START) / 3600:.1f} h")
'''


def domain_of_repo():
    """Cell 2b's classifier, run here on part 1's fetched repo info (rebench/repos.jsonl)."""
    ns = {"re": re}
    exec(CELL2B[CELL2B.index("DOMAINS = {"):CELL2B.index("REPO_LOG =")], ns)
    info = {json.loads(l)["repo"]: json.loads(l)["info"] for l in open(PART1_OUT / "repos.jsonl")}
    return {r: ns["domain_of"](i, r)[0] for r, i in info.items()}


def pool_1b():
    """Part 1 top-up (2026-10-21): part 1 reached only 51% public-like usable tasks (its pool has few such repos at
    3 per repo, and the first classifier needed 2 keyword hits). Its public-like tasks (fixed classifier) that part 1
    did not select, up to 6 more per repo."""
    dom = domain_of_repo()
    done = {json.loads(l)["id"] for l in open(PART1_OUT / "gated_all.jsonl")}
    repo = {json.loads(l)["instance_id"]: json.loads(l)["repo"] for l in open(ROOT / "data/swe_rebench/candidates.jsonl")}
    return [(i, lv) for i, lv in pool_of(1) if i not in done and dom.get(repo[i], "other") != "other"]


def attempted():
    """Every task an earlier build already tried (selected and built/gated), usable or not."""
    out = {json.loads(l)["instance_id"] for l in open(PILOT_DIR)}
    for d in ("2026-10-21_rebench_full_new-data", "2026-10-21_rebench_full_p1b", "2026-10-21_rebench_full_p2"):
        out |= {json.loads(l)["id"] for l in open(ROOT / "data/results" / d / "rebench/gated_all.jsonl")}
    return out


def pool_new(half):
    """Parts 3 and 4 (user 2026-10-22): the never-attempted candidates, split by the same repo halves as parts 1/2,
    minus OOD-45's and the public tasks' repos. Gemma runs on all of them; the TEST repos are chosen at assembly
    (repos with no training task, by repo, before any run) and their runs are the base model's test score."""
    sys.path.insert(0, str(ROOT / "scripts/datasets"))
    from assemble_rebench import OOD45_REPOS
    banned = OOD45_REPOS | {json.loads(l)["repo"] for l in open(ROOT / "data/tasks.jsonl")}
    repo = {json.loads(l)["instance_id"]: json.loads(l)["repo"] for l in open(ROOT / "data/swe_rebench/candidates.jsonl")}
    done = attempted()
    return [(i, lv) for i, lv in pool_of(half) if i not in done and repo[i] not in banned]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=350)
    ap.add_argument("--new", action="store_true", help="write parts 3 and 4 (never-attempted candidates) only")
    args = ap.parse_args()
    cell3 = build_cell()
    if args.new:
        for part, half, seed in ((3, 1, 20261031), (4, 2, 20261041)):
            pool = pool_new(half)
            repo_n = collections.Counter(i.rsplit("-", 1)[0] for i, _ in pool)
            n = sum(min(3, v) for v in repo_n.values())  # every repo, at most 3 tasks each
            write_part(part, pool, n, 0.8, 3, seed, cell3)
        return
    pb = pool_1b()
    # Part 1 already ran (2026-10-21, commit 9335570's cells, first classifier): its cells are not regenerated.
    for part, pool, n, share, cap, seed in ((2, pool_of(2), args.n, 0.8, 3, 20261023), ("1b", pb, len(pb), 1.0, 6, 20261121)):
        write_part(part, pool, n, share, cap, seed, cell3)


def write_part(part, pool, n, share, cap, seed, cell3):
    out = ROOT / f"kaggle/cells_rebench_full_p{part}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "cell1.py").write_text((ROOT / "kaggle/cells_rebench_pilot/cell1.py").read_text())
    (out / "cell2.py").write_text(CELL2.format(part=part, n=n, pool=pool, match_share=share, cap=cap, seed=seed))
    (out / "cell2b_select.py").write_text(CELL2B)
    (out / "cell3_build.py").write_text(cell3)
    (out / "cell4_gate.py").write_text(CELL4)
    (out / "cell5_leakage.py").write_text(CELL5)
    (out / "cell6_finish.py").write_text(CELL6)
    lv = collections.Counter(x for _, x in pool)
    print(f"part {part}: pool {len(pool)} tasks, {len({i.rsplit('-', 1)[0] for i, _ in pool})} repos, levels "
          f"{dict(sorted(lv.items()))}, target {n} -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
