"""Writes kaggle/cells_repro/: do the agents' OWN scripts tell which candidate patch fixes the issue? (CPU)

    python3 scripts/train/make_repro_cells.py     # also writes data/testsignal/scripts.jsonl (local only)

Why (2026-10-29, test signal): breaking existing tests rejects wrong patches (0/19 solved) but cannot say "fixed";
best-of-3 + that filter = 20.0 of 40, a perfect picker 22.1. The agents already write repro / check scripts (write_file
of a .py in /tmp or .git/agent, python3 - << EOF heredocs): 336 distinct ones for 39 d40 tasks in our 8 GPU arm-runs,
taken from the request logs. Here every script of a task runs (python, 30 s, no stdin, '/workspace' -> the sandbox
dir) against: no patch, the reference patch, every distinct candidate patch. Runtime signal per candidate: scripts that
fail without a patch and pass with it ("fixes"), scripts that pass without and fail with it ("regresses").

Mechanism: verify_task with the hidden test_patch replaced by a new file tests/test_zz_probe.py whose one test runs the
scripts and writes results/repro/<task>__<variant>.json (subprocess sandbox = the notebook's file system).
Inputs: as kaggle/cells_testsignal (the private dataset now also has scripts.jsonl). CPU, internet off.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/train"))
import make_testsignal_cells as TS  # noqa: E402

OUT = ROOT / "kaggle/cells_repro"
TEST_RE = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|conftest\.py$")
HEREDOC = re.compile(r"python3?\s+-\s*<<\s*'?(\w+)'?\n(.*?)\n\1\b", re.S)


def scripts():
    """{task: [(src, code)]}: distinct scripts the agents wrote, from the request logs of the arm-runs."""
    per = {}
    for d, arm in TS.SRC:
        seen = set()
        for line in open(ROOT / f"data/results/{d}/requests/requests.jsonl"):
            r = json.loads(line)
            if f"#a{arm}." not in r["job"]:
                continue
            m = r["reply"]
            msg = (m.get("choices") or [{}])[0].get("message") if "choices" in m else m.get("message", {})
            for tc in (msg or {}).get("tool_calls") or []:
                fn = tc["function"]
                try:
                    a = json.loads(fn["arguments"])
                except Exception:
                    continue
                code = None
                if fn["name"] == "write_file":
                    path = str(a.get("filepath") or a.get("path") or "")
                    if path.endswith(".py") and not TEST_RE.search(path.removeprefix("/workspace/")) and (
                            "/tmp" in path or ".git/agent" in path or "repro" in path or "check" in path):
                        code = a.get("content")
                elif fn["name"] == "run_command":
                    h = HEREDOC.search(str(a.get("command", "")))
                    code = h.group(2) if h else None
                key = r["job"].split("#")[0]
                if code and code not in seen and code not in [c for _, c in per.get(key, [])]:
                    seen.add(code)
                    per.setdefault(key, []).append((f"{d}:{arm}", code))
    return per


CELL3 = r'''# 3. REPRO SIGNAL (scripts/train/make_repro_cells.py): per d40 task, every script the agents wrote for it, run
#    against no patch / the reference patch / each distinct candidate patch. One line per run.
import dataclasses, logging, warnings
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

_s = glob.glob('/kaggle/input/**/scripts.jsonl', recursive=True)
assert len(_s) == 1, f'the private dataset needs scripts.jsonl (new version of ziad23samer/testsignal-candidates); found {{_s}}'
SCRIPTS = {{}}
for l in open(_s[0]):
    r = json.loads(l)
    SCRIPTS.setdefault(r['instance_id'], []).append(r['code'])
print(f'{{sum(len(v) for v in SCRIPTS.values())}} scripts for {{len(SCRIPTS)}} tasks')
SUB = WORKING_DIR / 'submission'
for rel, text in {submission!r}.items():
    (SUB / rel).parent.mkdir(parents=True, exist_ok=True)
    (SUB / rel).write_text(text)
OUT = WORKING_DIR / 'results' / 'repro'
OUT.mkdir(parents=True, exist_ok=True)
limits, gen_constraints = build_submission_limits()
config = EvalConfig(
    tasks_path=DATA_DIR / 'tasks.jsonl', snapshots_dir=DATA_DIR / 'snapshots', results_dir=OUT / 'eval',
    submission_dir=SUB, models=ModelRegistry(), sandbox='subprocess', wheels_dir=DATA_DIR / 'wheels',
    graph_dir=str(DATA_DIR / 'graphs'), embeddings_dir=str(DATA_DIR / 'embeddings'), task_ids=sorted(SCRIPTS),
    limits=limits, generation_constraints=gen_constraints,
    context_cache_config=ContextCacheConfig(min_tokens=2048, ttl_seconds=1800, cache_intervals=10),
    events_compaction_config=EventsCompactionConfig(compaction_interval=5, overlap_size=2, token_threshold=14336,
                                                    event_retention_size=5),
    display_mode='quiet', timeout_seconds=1200, max_tool_calls=28, max_time_minutes=15.0, max_turns=80)
TASKS = {{t.instance_id: t for t in load_tasks(DATA_DIR / 'tasks.jsonl')}}
SCRIPT_TIMEOUT = {script_timeout}

PROBE = """import json, os, subprocess, sys, tempfile
SCRIPTS = %r
OUT = %r


def test_zz_probe():
    ws = os.getcwd()
    env = {{k: v for k, v in os.environ.items() if k != 'PYTHONSAFEPATH'}}  # the agents ran scripts from the repo
    env['PYTHONPATH'] = ws + os.pathsep + env.get('PYTHONPATH', '')
    res = []
    for i, code in enumerate(SCRIPTS):
        path = os.path.join(tempfile.gettempdir(), 'zz_probe_%%d_%%d.py' %% (os.getpid(), i))
        with open(path, 'w') as f:
            f.write(code.replace('/workspace', ws))
        try:
            r = subprocess.run([sys.executable, path], cwd=ws, capture_output=True, text=True, timeout=%d,
                               stdin=subprocess.DEVNULL, env=env)
            res.append({{'i': i, 'exit': r.returncode, 'out': r.stdout[-400:], 'err': r.stderr[-400:]}})
        except subprocess.TimeoutExpired:
            res.append({{'i': i, 'exit': 'timeout', 'out': '', 'err': ''}})
        except Exception as e:
            res.append({{'i': i, 'exit': 'error', 'out': '', 'err': repr(e)[:300]}})
    with open(OUT, 'w') as f:
        json.dump(res, f)
"""


def probe_patch(iid, variant):
    body = PROBE % (SCRIPTS[iid], str(OUT / f'{{iid}}__{{variant}}.json'), SCRIPT_TIMEOUT)
    lines = body.split('\n')
    return ('diff --git a/tests/test_zz_probe.py b/tests/test_zz_probe.py\nnew file mode 100644\n--- /dev/null\n'
            '+++ b/tests/test_zz_probe.py\n' + f'@@ -0,0 +1,{{len(lines)}} @@\n' + '\n'.join('+' + l for l in lines) + '\n')


async def run_variant(iid, variant, patch):
    task = dataclasses.replace(TASKS[iid], test_patch=probe_patch(iid, variant))
    snap, base_snap, patch_path = resolve_task_snapshot_paths(config.snapshots_dir, iid, task.repo)
    out = OUT / f'{{iid}}__{{variant}}.json'
    out.unlink(missing_ok=True)
    t0 = time.perf_counter()
    try:
        res = await verify_task(EVAL.docker, config, task, snap, agent_patch=patch, base_snapshot_path=base_snap,
                                patch_path=patch_path, start_time=t0)
        err = (res.error or '')[:160]
    except Exception as ex:
        err = f'{{type(ex).__name__}}: {{str(ex)[:160]}}'
    for d in glob.glob('/tmp/swegemma_sandbox_*'):
        shutil.rmtree(d, ignore_errors=True)
    got = json.loads(out.read_text()) if out.exists() else None
    return got, err, round(time.perf_counter() - t0)


async def main():
    global EVAL
    EVAL = Evaluator(config)
    by_task = collections.defaultdict(list)
    for c in CANDS:
        by_task[c['instance_id']].append(c)
    fh = open(OUT / 'rows.jsonl', 'w')
    tasks = [t for t in sorted(by_task) if SCRIPTS.get(t)]
    for k, iid in enumerate(tasks, 1):
        print(f'[{{k:2}}/{{len(tasks)}}] {{iid}}: {{len(SCRIPTS[iid])}} scripts', flush=True)
        variants, seen = [('baseline', '', None), ('reference', TASKS[iid].patch, None)], {{}}
        for n, c in enumerate(by_task[iid]):
            key = re.sub(r'^index .*$', '', c['patch'], flags=re.M).strip()
            if key:
                variants.append((f'cand{{n}}', c['patch'], c))
        for name, patch, c in variants:
            key = re.sub(r'^index .*$', '', patch, flags=re.M).strip()
            if c is not None and key in seen:
                got, err, s = seen[key]
                dup = True
            else:
                got, err, s = await run_variant(iid, name, patch)
                seen[key] = (got, err, s)
                dup = False
            row = {{'instance_id': iid, 'variant': name, 'src': c['src'] if c else name, 'resolved': c['resolved'] if c else None,
                   'exits': [g['exit'] for g in got] if got else None, 'results': got, 'error': err, 'seconds': s, 'dup': dup}}
            fh.write(json.dumps(row) + '\n'); fh.flush()
            ex = row['exits']
            print(f"    {{name:9}} {{row['src'][-26:]:26}} hidden={{row['resolved']!s:5}} exit0 {{sum(1 for e in ex if e == 0) if ex else '-'}}/"
                  f"{{len(ex) if ex else '-'}} ({{s}}s){{' dup' if dup else ''}} {{'' if ex else err[:90]}}", flush=True)


with concurrent.futures.ThreadPoolExecutor(max_workers=1) as _pool:
    _pool.submit(lambda: asyncio.run(main())).result()
print('==> done:', OUT / 'rows.jsonl')
'''


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    per = scripts()
    with open(TS.DATA_OUT / "scripts.jsonl", "w") as fh:
        for t, items in sorted(per.items()):
            for src, code in items:
                fh.write(json.dumps({"instance_id": t, "src": src, "code": code}) + "\n")
    import make_gen_cells as G
    (OUT / "cell1.py").write_text((ROOT / "kaggle/cells_testsignal/cell1.py").read_text())
    (OUT / "cell2.py").write_text((ROOT / "kaggle/cells_testsignal/cell2.py").read_text())
    (OUT / "cell3_repro.py").write_text(CELL3.format(submission=G.submission(), script_timeout=20))
    print("wrote", OUT.relative_to(ROOT), "| scripts", sum(len(v) for v in per.values()), "for", len(per), "tasks")


if __name__ == "__main__":
    main()
