"""Writes kaggle/cells_skill_arms/: the three skill arms (submissions/sk_a, sk_abc, sk_abcd) on dev16 (user 2026-10-25).

    python3 scripts/make_skill_arms.py && python3 scripts/train/make_skill_arms_cells.py

Conditions = mix's 64 earlier dev16 runs (rung 3e-3m): T0.2, 8 min, 28 calls, 80 turns, 2 tasks at once, so those
runs are the control (embedded per task; no new mix runs). PASS 1 = every arm once on all 16 tasks (48 runs) before
PASS 2 starts (early stopping: stop the session after pass 1 and the comparison is complete). Attempts are
"<arm>.<pass>" (job tag task#a<arm>.<pass>), so scripts/triage.py reads the run. Everything else is the test notebook
(kaggle/cells_test_31b): the combined-run sandbox setup (competition setup + pins + test deps for public tasks).

Inputs: as the test notebook, minus the adapter: the competition, the wheelhouse, the model google/gemma-4 ->
gemma-4-31b-it-qat-w4a16-ct, rodrigospalma/ood45-bugfix-split, rebench-new-cp312, the gold-check output
(test_deps_wheels). GPU L4x4, Python 3.12, INTERNET OFF.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/train"))
import make_gen_cells as G  # noqa: E402
from make_test_cells import must_replace  # noqa: E402

OUT = ROOT / "kaggle/cells_skill_arms"
ARMS = ["sk_a", "sk_abc", "sk_abcd"]
CONCURRENCY = 2


def arm_files(arm):
    base = ROOT / "submissions" / arm
    return {p.relative_to(base).as_posix(): p.read_text() for p in sorted(base.rglob("*")) if p.is_file()}


def mix_reference():
    """Pure mix (arms mix, mix_r1, mix_r2) on dev16: task -> [solved, no patch, runs]."""
    dev = set(json.load(open(ROOT / "data/splits_public.json"))["dev16"])
    ref = {}
    for f in sorted((ROOT / "data/results").glob("*/results/*/task_results.jsonl")):
        if f.parent.name not in ("mix", "mix_r1", "mix_r2"):
            continue
        for r in map(json.loads, open(f)):
            if r["instance_id"] in dev:
                x = ref.setdefault(r["instance_id"], [0, 0, 0])
                x[0] += bool(r["resolved"])
                x[1] += not (r.get("agent_patch_size") or 0)
                x[2] += 1
    return dict(sorted(ref.items()))


BLOCK = '''
# SKILL ARMS (scripts/train/make_skill_arms_cells.py): dev16 only, three arms, pass 1 before pass 2.
ATTEMPTS = 2  # passes; stop the session after "PASS 1 COMPLETE" for the early comparison
ARMS = {arms!r}
ARM_FILES = {arm_files!r}
DEV16 = {dev16!r}
MIX_REF = {mix_ref!r}  # mix (T0.2, 8 min, 2 at once) on dev16, 64 runs: task -> [solved, no patch, runs]
ROWS = {{}}
for l in open(DATA_DIR / 'tasks.jsonl'):
    r = json.loads(l)
    if r['instance_id'] in DEV16:
        ROWS[r['instance_id']] = {{**r, 'src': 'public', 'level': 'dev16', 'domain': 'public', 'text_kind': 'public',
                                   'leak': False, 'unfair_names': [], 'env_partial': False, 'split': 'dev16'}}
assert len(ROWS) == 16, f'dev16 tasks missing from tasks.jsonl: {{sorted(set(DEV16) - set(ROWS))}}'
print(f"SKILL ARMS: {{len(ROWS)}} dev16 tasks | arms {{ARMS}} | {{ATTEMPTS}} passes | {{CONCURRENCY}} at once")
SUB_ROOT = WORKING_DIR / 'submissions'
shutil.rmtree(SUB_ROOT, ignore_errors=True)
for arm, files in ARM_FILES.items():
    for rel, text in files.items():
        (SUB_ROOT / arm / rel).parent.mkdir(parents=True, exist_ok=True)
        (SUB_ROOT / arm / rel).write_text(text, encoding='utf-8')
    _ev = (SUB_ROOT / arm / 'eval_config.yaml').read_text()
    _cmds = (SUB_ROOT / arm / 'skills/agent/scripts/commands.txt').read_text().split()
    print(arm, '| tools', [l.split('#')[0].strip()[2:] for l in (SUB_ROOT / arm / 'agent.yaml').read_text().splitlines() if l.strip().startswith('- ')][:8],
          '| skill commands', _cmds, '| budgets', ' '.join(l.strip() for l in _ev.splitlines() if ':' in l and 'evaluation' not in l))
    assert 'max_time_minutes: 8' in _ev, 'arms run with the 8-minute limit (as mix\\'s dev16 runs)'
'''

CELL5 = r'''# 5. SKILL ARMS SUMMARY (paste this output to Claude): per pass, per arm vs mix's 64 dev16 runs, per task.
rows = [json.loads(l) for l in open(PER_TASK)] if PER_TASK.exists() else []
mix_solved = sum(s / n for s, _, n in MIX_REF.values())
mix_nopatch = sum(p / n for _, p, n in MIX_REF.values())
print(f'{len(rows)} runs | {(time.time() - T_START) / 3600:.1f} h | mix reference per 16-task pass: solved {mix_solved:.2f}, '
      f'no patch {mix_nopatch:.2f}')
for n in range(1, ATTEMPTS + 1):
    rs = [r for r in rows if r['attempt'].endswith(f'.{n}')]
    if not rs:
        continue
    print(f'\n== PASS {n}: {len(rs)} runs')
    for arm in ARMS:
        a = [r for r in rs if r['arm'] == arm]
        print(f"  {arm:8} solved {sum(r['resolved'] for r in a):2}/{len(a):2} (mix {mix_solved:.1f}) | no patch "
              f"{sum(not r['patch_chars'] for r in a):2} (mix {mix_nopatch:.1f}) | ends {dict(Counter(r['end'] for r in a))} "
              f"| median tools {sorted(r['tool_calls'] or 0 for r in a)[len(a) // 2] if a else '-'}")
print('\nper task: mix solved/runs (no patch) | ' + ' | '.join(ARMS) + '   (S = solved, E = edited, 0 = no patch)')
for iid in sorted(ROWS):
    s, p, n = MIX_REF.get(iid, [0, 0, 0])
    cells = []
    for arm in ARMS:
        a = sorted((r for r in rows if r['arm'] == arm and r['instance_id'] == iid), key=lambda r: r['attempt'])
        cells.append(''.join('S' if r['resolved'] else ('E' if r['patch_chars'] else '0') for r in a) or '-')
    print(f'  {iid:16} mix {s}/{n} ({p})   ' + '   '.join(f'{c:>4}' for c in cells))
req = WORKING_DIR / 'requests' / 'requests.jsonl'
print('request log:', f'{req.stat().st_size / 1e6:.0f} MB' if req.exists() else 'MISSING')
'''


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    src, comb = ROOT / "kaggle/cells_gen", ROOT / "kaggle/cells_gen_combined"
    (OUT / "cell1.py").write_text((src / "cell1.py").read_text())

    c2 = G.CELL2.format(submission=G.submission(), embedded_prev=[], sample=[], sub_name="mix")
    mode_line = next(l for l in c2.splitlines() if l.startswith("MODE = "))
    c2 = c2.replace(mode_line, "MODE = 'skill_arms'  # three skill arms on dev16 (make_skill_arms_cells.py)")
    c2 = must_replace(c2, "CONCURRENCY = 6  # full / retry: trial 2026-10-21: 40.9 attempts/h at 6 vs 31.4 at 4\n",
                      f"CONCURRENCY = {CONCURRENCY}  # as mix's dev16 runs (rung 3e-3m): 2 at once, 8 min\n")
    c2 = must_replace(c2, "STOP_NEW_TASKS_AFTER_H = 10.5  # Kaggle ends GPU sessions at 12 h; a task takes <= ~10 min\n",
                      "STOP_NEW_TASKS_AFTER_H = 10.5  # = min(10.5, this account's GPU quota in hours / 2 - 0.4): L4x4 bills 2x,\n"
                      "# a run ends within 8 min, Kaggle ends sessions at 12 h; a killed run loses its output\n")
    c2 = must_replace(c2, "for p in sorted(glob.glob('/kaggle/input/**/results/gen_per_task.jsonl', recursive=True)) + ([str(PER_TASK)] if PER_TASK.exists() else []):\n",
                      "for p in ([str(PER_TASK)] if PER_TASK.exists() else []):\n")
    c2 = must_replace(c2, "ood.patch_harness()\n",
                      "from swegemma.harness import container_setup as _cs0\n"
                      "_HARNESS_INSTALL, _HARNESS_COMPAT = _cs0.install_test_dependencies, _cs0._is_wheel_compatible_py313  # public tasks\n"
                      "ood.patch_harness()\n")
    host = "print('host pytest plugins:', [Path(p).name for p in _host], '-> exit', _r.returncode, _r.stderr[-200:])\n"
    dev16 = sorted(json.load(open(ROOT / "data/splits_public.json"))["dev16"])
    c2 = must_replace(c2, host, host + BLOCK.format(arms=ARMS, arm_files={a: arm_files(a) for a in ARMS}, dev16=dev16,
                                                    mix_ref=mix_reference()))
    (OUT / "cell2.py").write_text(c2 + "\n" + G.sandbox_env())
    (OUT / "cell2c_public_setup.py").write_text((comb / "cell2c_public_setup.py").read_text())
    (OUT / "cell3.py").write_text((src / "cell3.py").read_text())  # vLLM as the scorer (LoRA on, no adapter)
    (OUT / "cell3b_request_logger.py").write_text((src / "cell3b_request_logger.py").read_text().replace(
        "(training data: tagged task#attempt)", "(skill arms: tagged task#a<arm>.<pass>)"))

    c4 = (comb / "cell4_run.py").read_text()
    for old, new in (
        ("elif MODE == 'prompt':",
         "elif MODE == 'skill_arms':  # one PHASE per pass (phases run one after another: pass 1 ends before pass 2);\n"
         "    # inside a pass, the first arm rotates from task to task\n"
         "    PHASES = [(CONCURRENCY, [(i, f'{ARMS[(k + j) % len(ARMS)]}.{n}') for k, i in enumerate(ORDER)\n"
         "                             for j in range(len(ARMS)) if (i, f'{ARMS[(k + j) % len(ARMS)]}.{n}') not in DONE_JOBS])\n"
         "              for n in range(1, ATTEMPTS + 1)]\n"
         "elif MODE == 'prompt':"),
        ("MANIFEST = discover_adapters(str(SUB_DIR), adapter_extensions=ALLOWED_ADAPTER_EXTENSIONS)\n",
         "MANIFESTS = {a: discover_adapters(str(SUB_ROOT / a), adapter_extensions=ALLOWED_ADAPTER_EXTENSIONS) for a in ARMS}\n"),
        ("EVAL_CFG = read_eval_config(SUB_DIR)\n",
         "EVAL_CFG = read_eval_config(SUB_ROOT / ARMS[0])\n"
         "assert all(read_eval_config(SUB_ROOT / a) == EVAL_CFG for a in ARMS), 'arms differ in budgets'\n"),
        ("def evaluator_for(iid):\n", "def evaluator_for(iid, arm):\n"),
        ("results_dir=RESULTS / 'gen', submission_dir=SUB_DIR,", "results_dir=RESULTS / 'gen', submission_dir=SUB_ROOT / arm,"),
        ("adapter_manifest=MANIFEST,", "adapter_manifest=MANIFESTS[arm],"),
        ("evaluator_for(ORDER[0])  # fail before any task if the submission does not build into a config\n"
         "print('budgets', EVAL_CFG, '| adapters', list(MANIFEST.adapters))\n",
         "for _a in ARMS:  # fail before any task if a submission does not build into a config\n"
         "    evaluator_for(ORDER[0], _a)\n"
         "    print(_a, '| budgets', EVAL_CFG, '| adapters', list(MANIFESTS[_a].adapters))\n"),
        ("evaluator_for(iid), time.time()", "evaluator_for(iid, attempt.split('.')[0]), time.time()"),
        ("row = {'instance_id': iid, 'attempt': attempt, 'mode': MODE,",
         "row = {'instance_id': iid, 'attempt': attempt, 'arm': attempt.split('.')[0], 'mode': MODE,"),
        ("    await asyncio.gather(*(one(i, a) for i, a in jobs))\n",
         "    await asyncio.gather(*(one(i, a) for i, a in jobs))  # jobs are queued in pass order (pass 1 first)\n"),
    ):
        c4 = must_replace(c4, old, new)
    # a line when pass 1 (phase 1) ends, so the session can be stopped there
    c4 = must_replace(c4, "    print('PHASE', json.dumps(PHASE_STATS[-1]), flush=True)\n",
                      "    print('PHASE', json.dumps(PHASE_STATS[-1]), flush=True)\n"
                      "    print('=' * 20, f'PASS {phase_no} COMPLETE: every arm ran once more on all 16 tasks (stop here for '\n"
                      "          'the early comparison; cell 5 summarises)', '=' * 20, flush=True)\n")
    (OUT / "cell4_run.py").write_text(c4)
    (OUT / "cell5_summary.py").write_text(CELL5)
    print("wrote", OUT.relative_to(ROOT), sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
