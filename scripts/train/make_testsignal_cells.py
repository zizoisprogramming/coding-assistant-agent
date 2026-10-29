"""Writes kaggle/cells_testsignal/: does "the EXISTING tests still pass" pick the solved patch? (CPU, no GPU quota)

    python3 scripts/train/make_testsignal_cells.py      # also writes data/testsignal/candidates.jsonl (local only)

Why (2026-10-29, scripts/picker_offline.py): best-of-3 attempts with a naive pick (any non-empty patch) = 19.5 of 40
vs 17.8 for one attempt; a perfect picker = 22.1. The gap needs an execution signal a runtime picker could use. Here,
per d40 task: every candidate patch from our 8 GPU arm-runs (+ the reference patch as a calibration row, + no patch as
the baseline) is run through the harness's own verify_task with the hidden test_patch REPLACED by existing test files
of the repo that exercise the changed modules (chosen like a runtime picker could: tests/ files importing the module or
named after it, max SEL_MAX). Output results/testsignal/rows.jsonl: per candidate passed / failed / errors counts and
exit code; compared locally with 'resolved' (the hidden grade) to see whether fewer failures = solved.

Inputs: the competition, the wheelhouse, the gold-check output (test_deps_wheels), and the private dataset with
candidates.jsonl (made by this script from data/results; uploaded with the Kaggle CLI). CPU, internet off.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/train"))
import make_regrade_cells as RG  # noqa: E402
from make_test_cells import must_replace  # noqa: E402

OUT = ROOT / "kaggle/cells_testsignal"
DATA_OUT = ROOT / "data/testsignal"  # gitignored: patches of competition tasks stay local / private on Kaggle
SRC = [("2026-10-29_skill_d40", "sk_a2"), ("2026-10-29_skill_d40_32", "sk_a2_32"), ("2026-10-29_skill_s20_fr", "sk_fr"),
       ("2026-10-29_skill_s20_fr2_pub", "sk_fr2"), ("2026-10-29_skill_s20_fr2_pub", "pub024"),
       ("2026-10-29_skill_u20", "sk_a2_32"), ("2026-10-29_skill_u20", "sk_fr2"), ("2026-10-29_skill_u20", "pub024")]


def candidates():
    rows = []
    for d, arm in SRC:
        for r in map(json.loads, open(ROOT / f"data/results/{d}/results/gen_per_task.jsonl")):
            if r["arm"] != arm:
                continue
            p = ROOT / f"data/results/{d}/results/gen/patches/{r['instance_id']}__a{arm}.1.diff"
            rows.append({"instance_id": r["instance_id"], "src": f"{d}:{arm}", "resolved": bool(r["resolved"]),
                         "patch": p.read_text() if p.exists() else ""})
    return rows


CELL3 = r'''# 3. TEST SIGNAL (scripts/train/make_testsignal_cells.py): per d40 task, the baseline (no patch), the reference patch
#    (calibration) and every distinct candidate patch, each run on EXISTING test files of the changed modules through the
#    harness's verify_task (hidden test_patch replaced). One line per run. Writes results/testsignal/rows.jsonl.
import dataclasses, io, logging, tarfile, warnings
warnings.filterwarnings('ignore')
logging.getLogger('swegemma.sandbox.subprocess').setLevel(logging.ERROR)
from adk_submission import ModelRegistry
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.apps._configs import EventsCompactionConfig
from swegemma.config import EvalConfig, build_submission_limits
from swegemma.deduplication import resolve_task_snapshot_paths
from swegemma.evaluate import Evaluator
from swegemma.harness.verification import verify_task
from swegemma.models import load_tasks
from swegemma.models.task import Task

SEL_MAX = {sel_max}
TEST_RE = re.compile(r"(^|/)(tests?|testing)/.*\.py$|(^|/)test_[^/]*\.py$")
SUB = WORKING_DIR / 'submission'
for rel, text in {submission!r}.items():
    (SUB / rel).parent.mkdir(parents=True, exist_ok=True)
    (SUB / rel).write_text(text)
OUT = WORKING_DIR / 'results' / 'testsignal'
OUT.mkdir(parents=True, exist_ok=True)
limits, gen_constraints = build_submission_limits()
config = EvalConfig(
    tasks_path=DATA_DIR / 'tasks.jsonl', snapshots_dir=DATA_DIR / 'snapshots', results_dir=OUT / 'eval',
    submission_dir=SUB, models=ModelRegistry(), sandbox='subprocess', wheels_dir=DATA_DIR / 'wheels',
    graph_dir=str(DATA_DIR / 'graphs'), embeddings_dir=str(DATA_DIR / 'embeddings'), task_ids=sorted({{c['instance_id'] for c in CANDS}}),
    limits=limits, generation_constraints=gen_constraints,
    context_cache_config=ContextCacheConfig(min_tokens=2048, ttl_seconds=1800, cache_intervals=10),
    events_compaction_config=EventsCompactionConfig(compaction_interval=5, overlap_size=2, token_threshold=14336,
                                                    event_retention_size=5),
    display_mode='quiet', timeout_seconds=600, max_tool_calls=28, max_time_minutes=15.0, max_turns=80)
TASKS = {{t.instance_id: t for t in load_tasks(DATA_DIR / 'tasks.jsonl')}}


@dataclasses.dataclass(frozen=True)
class SelTask(Task):
    """A task whose verification runs the given EXISTING test files (no hidden test_patch)."""
    sel_files: tuple = ()

    @property
    def test_files(self):
        return list(self.sel_files)


def changed_sources(patch):
    return [f for f in re.findall(r'^\+\+\+ b/(\S+)', patch, re.M) if f.endswith('.py') and not TEST_RE.search(f)]


def snapshot_files(iid):
    """{{path: text}} of the repo's test files in the task snapshot (base + patch layers)."""
    task = TASKS[iid]
    snap, base_snap, patch_path = resolve_task_snapshot_paths(config.snapshots_dir, iid, task.repo)
    out = {{}}
    for p in [base_snap, snap]:
        if not p or not Path(p).exists() or not str(p).endswith(('.tgz', '.tar.gz', '.tar')):
            continue
        with tarfile.open(p) as tf:
            for m in tf.getmembers():
                name = m.name.split('/', 1)[1] if m.name.startswith(('./', 'workspace/')) else m.name
                name = name.removeprefix('./')
                if m.isfile() and TEST_RE.search(name) and not name.endswith('conftest.py'):
                    out[name] = tf.extractfile(m).read().decode('utf-8', 'replace')
    return out


def select_tests(iid, sources):
    """Existing test files a runtime picker could choose: they import a changed module or are named after it."""
    tests = snapshot_files(iid)
    scored = []
    for path, text in tests.items():
        s = 0
        for src in sources:
            mod = src[:-3].replace('/', '.').removesuffix('.__init__')
            pkg, _, stem = mod.rpartition('.')
            if re.search(rf'\b(import|from)\s+{{re.escape(mod)}}\b', text) or (pkg and re.search(rf'from\s+{{re.escape(pkg)}}\s+import\s+[^\n]*\b{{re.escape(stem)}}\b', text)):
                s += 2
            if stem and stem not in ('__init__', 'utils', 'main') and stem in Path(path).stem:
                s += 3
        if s:
            scored.append((-s, len(text), path))
    return [p for _, _, p in sorted(scored)[:SEL_MAX]]


def counts(out):
    m = {{k: int(v) for v, k in re.findall(r'(\d+) (passed|failed|errors?|skipped)', out or '')}}
    return m.get('passed', 0), m.get('failed', 0), m.get('error', 0) + m.get('errors', 0)


async def run_one(iid, files, patch):
    task = TASKS[iid]
    st = SelTask(**{{f.name: getattr(task, f.name) for f in dataclasses.fields(Task)}}, sel_files=tuple(files))
    st = dataclasses.replace(st, test_patch='')
    snap, base_snap, patch_path = resolve_task_snapshot_paths(config.snapshots_dir, iid, task.repo)
    t0 = time.perf_counter()
    try:
        res = await verify_task(EVAL.docker, config, st, snap, agent_patch=patch, base_snapshot_path=base_snap,
                                patch_path=patch_path, start_time=t0)
        p, f, e = counts(res.test_output)
        row = {{'ok': bool(res.resolved), 'exit': res.test_exit_code, 'passed': p, 'failed': f, 'errors': e,
               'error': (res.error or '')[:200], 'tail': ' / '.join((res.test_output or '').strip().splitlines()[-2:])[-240:]}}
    except Exception as ex:
        row = {{'ok': False, 'exit': -9, 'passed': 0, 'failed': 0, 'errors': 0, 'error': f'{{type(ex).__name__}}: {{str(ex)[:200]}}', 'tail': ''}}
    for d in glob.glob('/tmp/swegemma_sandbox_*'):
        shutil.rmtree(d, ignore_errors=True)
    row['seconds'] = round(time.perf_counter() - t0)
    return row


async def main():
    global EVAL
    EVAL = Evaluator(config)
    by_task = collections.defaultdict(list)
    for c in CANDS:
        by_task[c['instance_id']].append(c)
    fh = open(OUT / 'rows.jsonl', 'w')
    for k, (iid, cs) in enumerate(sorted(by_task.items()), 1):
        sources = sorted({{s for c in cs for s in changed_sources(c['patch'])}} | set(changed_sources(TASKS[iid].patch)))
        files = select_tests(iid, sources)
        print(f'[{{k:2}}/{{len(by_task)}}] {{iid}}: changed {{sources}} -> tests {{files}}', flush=True)
        if not files:
            fh.write(json.dumps({{'instance_id': iid, 'kind': 'no_tests', 'sources': sources}}) + '\n')
            continue
        seen = {{}}
        jobs = [('baseline', '', None), ('reference', TASKS[iid].patch, None)] + [('candidate', c['patch'], c) for c in cs]
        for kind, patch, c in jobs:
            key = re.sub(r'^index .*$', '', patch, flags=re.M).strip()
            if key in seen and kind == 'candidate':
                row = dict(seen[key]); row['dedup'] = True
            elif not patch.strip() and kind == 'candidate':
                row = {{'ok': False, 'exit': None, 'passed': 0, 'failed': 0, 'errors': 0, 'error': 'empty patch', 'tail': '', 'seconds': 0}}
            else:
                row = await run_one(iid, files, patch)
                seen[key] = row
            row.update(instance_id=iid, kind=kind, tests=files, src=c['src'] if c else kind,
                       resolved=c['resolved'] if c else None)
            fh.write(json.dumps(row) + '\n'); fh.flush()
            print(f"    {{kind:9}} {{row['src'][-28:]:28}} hidden={{row['resolved']!s:5}} existing ok={{row['ok']!s:5}} "
                  f"pass {{row['passed']}} fail {{row['failed']}} err {{row['errors']}} ({{row['seconds']}}s){{' dedup' if row.get('dedup') else ''}} "
                  f"{{row['error'][:80]}}", flush=True)


with concurrent.futures.ThreadPoolExecutor(max_workers=1) as _pool:
    _pool.submit(lambda: asyncio.run(main())).result()
print('==> done:', OUT / 'rows.jsonl')
'''


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    DATA_OUT.mkdir(parents=True, exist_ok=True)
    cands = candidates()
    with open(DATA_OUT / "candidates.jsonl", "w") as fh:
        for c in cands:
            fh.write(json.dumps(c) + "\n")
    (DATA_OUT / "dataset-metadata.json").write_text(json.dumps(
        {"title": "testsignal-candidates", "id": "ziad23samer/testsignal-candidates", "licenses": [{"name": "other"}]}, indent=1))
    old = RG.CELL2[RG.CELL2.index("_gens = sorted("):RG.CELL2.index("_dirs = glob.glob(")]
    c2 = must_replace(RG.CELL2, old, (
        "_c = glob.glob('/kaggle/input/**/candidates.jsonl', recursive=True)\n"
        "assert len(_c) == 1, f'attach the private dataset ziad23samer/testsignal-candidates (candidates.jsonl); found {_c}'\n"
        "CANDS = [json.loads(l) for l in open(_c[0])]\n"
        "print(f'{len(CANDS)} candidate patches for {len({c[\"instance_id\"] for c in CANDS})} tasks, '\n"
        "      f'{sum(c[\"resolved\"] for c in CANDS)} solved (hidden grade), {sum(1 for c in CANDS if not c[\"patch\"].strip())} empty')\n\n"))
    c2 = c2.replace("# 2. RE-GRADE setup (scripts/train/make_regrade_cells.py)", "# 2. TEST SIGNAL setup (scripts/train/make_testsignal_cells.py, from make_regrade_cells.py)")
    (OUT / "cell1.py").write_text((ROOT / "kaggle/cells_datagen_pilot/cell1_cpu.py").read_text())
    (OUT / "cell2.py").write_text(c2)
    import make_gen_cells as G
    (OUT / "cell3_testsignal.py").write_text(CELL3.format(sel_max=4, submission=G.submission()))
    print("wrote", OUT.relative_to(ROOT), "| candidates", len(cands), "->", (DATA_OUT / "candidates.jsonl").relative_to(ROOT))


if __name__ == "__main__":
    main()
