"""CPU test check notebook (user 2026-11-17: 'yes build the CPU check'). Run: .venv/bin/python -I scripts/train/make_testcheck_cells.py

Question: does running the EXISTING tests of the edited code tell a wrong patch from a right one? For the 24 SWE-rebench
test tasks, every bank patch (scripts/mine_bank/testcheck_patches.py: wrong <= 10, solved <= 5 per task, deduplicated)
plus the real fix goes through the scorer's own verify_task (same workspace build: wheels, snapshot, editable install,
test dependencies, pytest config, baseline commit, the patch applied). Its final pytest call (the hidden tests) is
intercepted: instead, the test-picking command a future agent would run (scripts/agent_tc/testsel_cmd.sh, no double
quotes / backticks / backslashes) runs on the patched tree, then the same picked test files run again with the patch
stashed (the base). A NEW failure = a test that fails with the patch and not at the base. The hidden tests are never
applied here (test_patch is emptied; a placeholder FAIL_TO_PASS keeps verify_task going).

Bars (set before the run, docs/PLAN.md): wrong patches with a new failure >= 20% and solved patches <= 5% -> the idea
has room (an agent told 'these tests now fail' could catch those); otherwise it is dropped. Real fixes with a new
failure are reported too (old tests that encode the old behaviour would mislead an agent).

Cells (kaggle/cells_testcheck_rt): cell1 = the GPU notebooks' wheelhouse install without the 4x L4 check; cell2 = the
GPU notebooks' setup cell (task set, verified sandbox) with the 24 test tasks; cell3_check = the check; cell4_summary.
Runs on a CPU session of a notebook pinned to the original environment (Python 3.12, like the GPU runs), INTERNET OFF."""
import base64, gzip, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/mine_bank"))
import testcheck_patches as tp  # noqa: E402

SRC = ROOT / "kaggle/cells_skill_sb5h12"
OUT = ROOT / "kaggle/cells_testcheck_rt"
DEADLINE_H = 9.0
CONC = 3


def cell1():
    t = (SRC / "cell1.py").read_text()
    i = t.index("# Preflight: the 4x L4 shape")
    t = t[:i] + "# CPU session (no GPU needed: no model runs in the test check).\nprint('CPUs:', os.cpu_count())\n"
    return t.replace("# 1. Install the competition wheelhouse", "# 1 (CPU test check). Install the competition wheelhouse", 1)


def cell2(ids):
    t = (SRC / "cell2.py").read_text()
    reps = {"TASK_SET = ": f"TASK_SET = {ids!r}", "SPLIT_OF = ": f"SPLIT_OF = {dict.fromkeys(ids, 'rtest')!r}",
            "GEN_REF = ": "GEN_REF = {}", "MIX_REF = ": "MIX_REF = {}",
            "STOP_NEW_TASKS_AFTER_H = ": f"STOP_NEW_TASKS_AFTER_H = {DEADLINE_H}  # the test check's deadline (cell 3), counted from this cell"}
    lines = t.split("\n")
    for k, v in reps.items():
        hit = [n for n, l in enumerate(lines) if l.startswith(k)]
        assert len(hit) == 1, (k, hit)
        lines[hit[0]] = v
    t = "\n".join(lines)
    t = t.replace("# 2. GENERATION setup", "# 2. TEST CHECK setup (the GPU notebooks' setup cell, scripts/train/make_testcheck_cells.py; the agent parts are unused).\n# Was: GENERATION setup", 1)
    return t


CELL3 = r'''# 3. TEST CHECK (user 2026-11-17 'yes build the CPU check'; scripts/train/make_testcheck_cells.py). One line per patch.
#    Per patch: the scorer's verify_task builds the workspace and applies the patch; its hidden-test pytest call is replaced
#    by the test-picking command (as a future agent would run it) on the patched tree, then the same test files with the
#    patch stashed (the base, once per task and file set). Resumes from results/testcheck.jsonl.
import asyncio, base64, contextvars, gc, gzip, logging, warnings
warnings.filterwarnings('ignore')
logging.getLogger('swegemma.sandbox.subprocess').setLevel(logging.ERROR)
logging.getLogger('swegemma.harness.verification').setLevel(logging.CRITICAL)
from adk_submission import ModelRegistry
from swegemma.config import EvalConfig
from swegemma.evaluate import Evaluator
from swegemma.models import Task
import swegemma.harness.verification as V

PATCHES = json.loads(gzip.decompress(base64.b64decode(PATCHES_B64)).decode())
TESTSEL = TESTSEL_TEXT
CONC = CONC_VALUE  # patches at once (never two of one repo: the install step's import name is per repo)
DEADLINE = T_START + STOP_NEW_TASKS_AFTER_H * 3600
CHECK = RESULTS / 'testcheck.jsonl'
DONE_TC = {(r['iid'], r['pid']) for r in map(json.loads, open(CHECK))} if CHECK.exists() else set()
JOB = contextvars.ContextVar('tc_job', default=None)
BASE = collections.defaultdict(dict)  # iid -> tuple(files) -> base pytest output
_orig_exec = V.sandbox_exec
print(f'test check: {len(PATCHES)} bank patches + {len(ROWS)} real fixes on {len(ROWS)} tasks | {len(DONE_TC)} already done | '
      f'{CONC} at a time | deadline {STOP_NEW_TASKS_AFTER_H} h from cell 2')


def summary(out):
    m = re.findall(r'^=*\s*((?:\d+ (?:failed|passed|errors?|skipped|xfailed|xpassed|deselected|warnings?)(?:, )?)+) in [\d.]+s', out, re.M)
    if m:
        return m[-1]
    if 'Interrupted' in out or 'error during collection' in out:
        return 'collection error'
    return 'no summary (timeout or crash)'


def fails(out):
    ids = set()
    for l in out.splitlines():
        if l.startswith(('FAILED ', 'ERROR ')):
            ids.add(l.split(' ', 1)[1].split(' - ')[0].strip())
    if summary(out) in ('collection error', 'no summary (timeout or crash)'):
        ids.add('<' + summary(out) + '>')
    return ids


async def _exec(docker, sid, command, *, timeout=None):
    job = JOB.get()
    if job is None or '--junitxml=' not in command:
        return await _orig_exec(docker, sid, command, timeout=timeout)
    job['fired'] = True
    r1 = await _orig_exec(docker, sid, 'cd /workspace\n' + TESTSEL, timeout=260)
    out = (r1.stdout or '') + (r1.stderr or '')
    m = re.search(r'^== TESTS THAT USE THEM: ?(.*)$', out, re.M)
    files = m.group(1).split() if m else []
    job.update(sel_out=out[-3000:], files=files, noedit='No source file is edited yet' in out)
    if files:
        key = tuple(sorted(files))
        if key not in BASE[job['iid']]:
            # the base: take exactly this patch out again (reverse apply); stash only if that fails (it would also hide
            # untracked files the harness made after its baseline commit)
            enc = base64.b64encode(job['patch'].encode()).decode()
            rv = await _orig_exec(docker, sid, 'cd /workspace && echo ' + enc + ' | base64 -d > .git/agent/tc_rev.patch && '
                                  'git apply -R --whitespace=nowarn .git/agent/tc_rev.patch && echo TC_REVERTED', timeout=120)
            job['base_method'] = 'reverse' if 'TC_REVERTED' in (rv.stdout or '') else 'stash'
            if job['base_method'] == 'stash':
                await _orig_exec(docker, sid, 'cd /workspace && git stash push -u -q -m tc_base', timeout=120)
            rb = await _orig_exec(docker, sid, 'cd /workspace && timeout 150 python -m pytest ' + ' '.join(files)
                                  + ' -q -rfE -p no:cacheprovider 2>&1 | tail -40', timeout=260)
            BASE[job['iid']][key] = (rb.stdout or '') + (rb.stderr or '')
        job['base_out'] = BASE[job['iid']][key]
    return await _orig_exec(docker, sid, 'exit 1')


V.sandbox_exec = _exec


def as_task(r):
    return Task(instance_id=r['instance_id'], repo=r['repo'], base_commit=r['base_commit'],
                problem_statement=r['problem_statement'], patch=r['patch'], test_patch='',
                hints_text='', created_at=r['created_at'], FAIL_TO_PASS=('testcheck::placeholder',), PASS_TO_PASS=())


async def check_one(item):
    iid = item['iid']
    r = ROWS[iid]
    CUR_TASK.set(iid)
    ood.IMPORT_NAMES[r['repo']] = import_name(r)
    cfg = EvalConfig(tasks_path=DATA_DIR / 'tasks.jsonl', snapshots_dir=OUT / 'snapshots', results_dir=Path('/tmp/tc_results'),
                     submission_dir=DATA_DIR / 'sample_submission', models=ModelRegistry(), sandbox='subprocess',
                     wheels_dir=WHEEL_ROOT / WHEEL_SET / iid, timeout_seconds=600)
    ev = Evaluator(cfg)
    job = {'iid': iid, 'fired': False, 'patch': item['patch'], 'base_method': 'cached'}
    JOB.set(job)
    t0 = time.time()
    try:
        res = await V.verify_task(ev.docker, cfg, as_task(r), OUT / 'snapshots' / f'{iid}.tgz', agent_patch=item['patch'], start_time=time.perf_counter())
        err = res.error or ''
    except Exception as e:
        err = f'{type(e).__name__}: {str(e)[:300]}'
    po, bo = job.get('sel_out', ''), job.get('base_out', '')
    pf, bf = fails(po) if job.get('files') else set(), fails(bo) if job.get('files') else set()
    row = {'iid': iid, 'pid': item['pid'], 'kind': item['kind'], 'arm': item.get('arm', '-'), 'touches_fix': item.get('touches_fix', True),
           'fired': job['fired'], 'base_method': job['base_method'] if job.get('files') else '-', 'apply_error': 'Failed to apply agent patch' in err, 'error': '' if job['fired'] else err[:300],
           'noedit': job.get('noedit', False), 'files': job.get('files', []),
           'hidden_in_picks': bool(set(job.get('files', [])) & set(re.findall(r'^\+\+\+ b/(\S+)', r['test_patch'], re.M))),
           'patched': summary(po) if job.get('files') else '-', 'base': summary(bo) if job.get('files') else '-',
           'patched_fail': sorted(pf)[:40], 'base_fail': sorted(bf)[:40], 'new_fail': sorted(pf - bf)[:40],
           'secs': round(time.time() - t0), 'sel_tail': po[-1500:]}
    return row


async def check_all(items):
    sem, locks, done = asyncio.Semaphore(CONC), collections.defaultdict(asyncio.Lock), [0]

    async def one(item):
        async with locks[ROWS[item['iid']]['repo']]:
            async with sem:
                if time.time() > DEADLINE:
                    return
                RUNNING[item['iid']] = time.time()
                try:
                    row = await check_one(item)
                finally:
                    RUNNING.pop(item['iid'], None)
                with open(CHECK, 'a') as fh:
                    fh.write(json.dumps(row) + '\n')
                done[0] += 1
                el = (time.time() - t_c) / 60
                print(f"[{done[0]:3}/{len(items)}] {row['iid'][:40]:40} {row['kind']:6} {row['arm']:8} | picked {len(row['files'])} "
                      f"(hidden-test file {'yes' if row['hidden_in_picks'] else 'no '}) | with patch: {row['patched'][:34]:34} | base: {row['base'][:34]:34} "
                      f"| NEW FAIL {len(row['new_fail']):2}{' (no source edit)' if row['noedit'] else ''}{' APPLY FAILED' if row['apply_error'] else ''}"
                      f"{' NOT FIRED: ' + row['error'][:120] if not row['fired'] else ''} | {row['secs']:3}s | {el:.0f} min, "
                      f"ETA {el / done[0] * (len(items) - done[0]):.0f} min", flush=True)
                if done[0] == 1 and not row['fired'] and not row['apply_error']:
                    raise SystemExit('the pytest hook did not fire: this harness version runs the hidden tests differently; stop and send this output to Claude')
                clean_tmp()
                gc.collect()

    await asyncio.gather(*(one(i) for i in items))


_items = collections.defaultdict(list)
for _iid in sorted(ROWS):
    _items[_iid].append({'iid': _iid, 'pid': 'gold', 'kind': 'gold', 'arm': 'real fix', 'patch': ROWS[_iid]['patch']})
for _k, _p in enumerate(PATCHES):
    _items[_p['iid']].append({**_p, 'pid': f"p{_k}"})
_q = [v for v in _items.values()]
ITEMS = [q[k] for k in range(max(map(len, _q))) for q in _q if k < len(q) and (q[k]['iid'], q[k]['pid']) not in DONE_TC]  # round robin over tasks
print(f'to check now: {len(ITEMS)} | kinds', dict(Counter(i['kind'] for i in ITEMS)), flush=True)
t_c = time.time()
try:
    asyncio.run(check_all(ITEMS))
except RuntimeError:  # notebook already has a running loop
    import nest_asyncio; nest_asyncio.apply(); asyncio.get_event_loop().run_until_complete(check_all(ITEMS))
V.sandbox_exec = _orig_exec
print(f'test check done in {(time.time() - t_c) / 60:.1f} min; rows in {CHECK}: {sum(1 for _ in open(CHECK)) if CHECK.exists() else 0}')
'''

CELL4 = r'''# 4. TEST CHECK SUMMARY (bars set before the run: docs/PLAN.md RUN BUILT testcheck). Send this output to Claude.
TC = [json.loads(l) for l in open(RESULTS / 'testcheck.jsonl')]
print(f'base by reverse apply {sum(r["base_method"] == "reverse" for r in TC)}, by stash {sum(r["base_method"] == "stash" for r in TC)}, cached {sum(r["base_method"] == "cached" for r in TC)}')
print(f'rows {len(TC)} | hook fired {sum(r["fired"] for r in TC)} | apply failed {sum(r["apply_error"] for r in TC)} | errors {sum(bool(r["error"]) for r in TC)}')
for kind in ('gold', 'solved', 'wrong'):
    x = [r for r in TC if r['kind'] == kind and r['fired']]
    if not x:
        continue
    picked = [r for r in x if r['files']]
    nf = [r for r in x if r['new_fail']]
    print(f"{kind:6} {len(x):3} | a test file picked {len(picked):3} (hidden-test file among them {sum(r['hidden_in_picks'] for r in picked)}) | "
          f"NEW failure {len(nf):3} = {100 * len(nf) / len(x):4.1f}% of all, {100 * len(nf) / max(1, len(picked)):4.1f}% of picked | "
          f"any failure with the patch {sum(bool(r['patched_fail']) for r in x)} | base already failing {sum(bool(r['base_fail']) for r in picked)} | no source edit {sum(r['noedit'] for r in x)}")
w = [r for r in TC if r['kind'] == 'wrong' and r['fired'] and r['touches_fix']]
print(f"wrong patches that touch a real-fix file: {len(w)} | NEW failure {sum(bool(r['new_fail']) for r in w)} = {100 * sum(bool(r['new_fail']) for r in w) / max(1, len(w)):.1f}%")
x = [r for r in TC if r['kind'] == 'wrong' and r['fired']]
s = [r for r in TC if r['kind'] == 'solved' and r['fired']]
pw, ps = sum(bool(r['new_fail']) for r in x) / max(1, len(x)), sum(bool(r['new_fail']) for r in s) / max(1, len(s))
print(f"BARS: wrong with a NEW failure {100 * pw:.1f}% (bar >= 20%) | solved with a NEW failure {100 * ps:.1f}% (bar <= 5%) -> "
      f"{'PASS: the idea has room' if pw >= 0.20 and ps <= 0.05 else 'FAIL: drop the idea'}")
print('\nper task: kind -> patches / with a NEW failure')
for iid in sorted({r['iid'] for r in TC}):
    parts = []
    for kind in ('gold', 'solved', 'wrong'):
        y = [r for r in TC if r['iid'] == iid and r['kind'] == kind and r['fired']]
        if y:
            parts.append(f"{kind} {sum(bool(r['new_fail']) for r in y)}/{len(y)}")
    g = next((r for r in TC if r['iid'] == iid and r['kind'] == 'gold'), {})
    print(f"  {iid[:46]:46} {' | '.join(parts):40} picks {g.get('files', [])} base {g.get('base', '-')}")
'''


def main():
    out, gold = tp.collect()
    ids = sorted(gold)
    cmd = (ROOT / "scripts/agent_tc/testsel_cmd.sh").read_text().rstrip("\n")
    assert '"' not in cmd and "`" not in cmd and "\\" not in cmd
    assert cmd.splitlines()[-1].startswith("timeout 150 python -m pytest $files -q -rfE -p no:cacheprovider")
    slim = [{k: c[k] for k in ("iid", "kind", "arm", "touches_fix", "patch")} for c in out]
    b64 = base64.b64encode(gzip.compress(json.dumps(slim).encode(), 9)).decode()
    OUT.mkdir(parents=True, exist_ok=True)
    for p in OUT.glob("*.py"):
        p.unlink()
    (OUT / "cell1.py").write_text(cell1())
    (OUT / "cell2.py").write_text(cell2(ids))
    c3 = CELL3.replace("PATCHES_B64", repr(b64), 1).replace("TESTSEL_TEXT", repr(cmd), 1).replace("CONC_VALUE", str(CONC), 1)
    assert "PATCHES_B64" not in c3 and "TESTSEL_TEXT" not in c3 and "CONC_VALUE" not in c3
    (OUT / "cell3_check.py").write_text(c3)
    (OUT / "cell4_summary.py").write_text(CELL4)
    for f in sorted(OUT.glob("*.py")):
        compile(f.read_text(), str(f), "exec")
    print("wrote", OUT.relative_to(ROOT), sorted(p.name for p in OUT.glob("*.py")), "| patches", len(slim),
          "| embedded KB", len(b64) // 1024, "| tasks", len(ids))


if __name__ == "__main__":
    main()
