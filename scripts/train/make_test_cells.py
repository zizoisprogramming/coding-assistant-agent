"""Writes kaggle/cells_test_31b/: does the self-distilled LoRA beat mix? (the agreed test, user 2026-10-24)

    python3 scripts/train/make_test_cells.py

The 24 TEST tasks (rebench-new-cp312, split 'test': 21 repos in no training source, fixed before any run) + the 16
public dev16 tasks (never generated on, so never trained on; but fastapi/rich = repos of trained public tasks: reported
apart), three arms, ATTEMPTS runs each, in ONE session with one vLLM server (base + adapter):
  base_t02  mix as submitted (T0.2), no adapter
  sd_t02    mix + the self-distilled adapter (adapter_31b/final, r16 alpha16 = scale 1.0), T0.2
  sd_t07    the same adapter at T0.7 (Apple SSD paper: the best sampling temperature rises after self-distillation)
Conditions as the generation runs (6 at once, 15 min, 28 calls, 80 turns), so mix's T1.0 runs on the same tasks
(combined run, 11/24) stay a reference. Everything else is the combined generation notebook (cells_gen_combined): the
verified sandbox for our tasks, the competition's own setup + pins + test deps for public ones, the vLLM start, the
request logger. Jobs: attempt "<arm>.<n>" (job tag task#a<arm>.<n>), so scripts/triage.py reads this run as
it reads generation runs. Arms of a task run back to back (rotating first arm), so a cut session stays comparable.

Inputs: the competition, the wheelhouse, the model google/gemma-4 -> gemma-4-31b-it-qat-w4a16-ct,
rodrigospalma/ood45-bugfix-split, rebench-new-cp312 (the parts 3/4 task set), the gold-check output (test_deps_wheels),
and the training output (a dataset holding adapter_31b/final). GPU L4x4, Python 3.12, INTERNET OFF.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/train"))
import make_gen_cells as G  # noqa: E402

OUT = ROOT / "kaggle/cells_test_31b"
ADAPTER = "sd"
ARMS = {"base_t02": (None, 0.2), "sd_t02": (ADAPTER, 0.2), "sd_t07": (ADAPTER, 0.7)}  # arm: (adapter, temperature)


def must_replace(text, old, new):
    assert text.count(old) == 1, f"pattern not found once: {old[:70]!r}"
    return text.replace(old, new)


def arm_submissions():
    out = {}
    for arm, (adapter, temp) in ARMS.items():
        files = G.submission()  # mix byte for byte + the generation conditions (15 min); temperature set below
        files["configs/sampling.yaml"] = must_replace(
            files["configs/sampling.yaml"],
            "temperature: 1.0  # generation (user 2026-10-21): varied runs; the submission uses 0.2\n",
            f"temperature: {temp}  # test arm {arm}\n")
        if adapter:
            files["agent.yaml"] = must_replace(files["agent.yaml"], "model: gemma-4-31b-it-qat-w4a16-ct\n",
                                               f"model: gemma-4-31b-it-qat-w4a16-ct\nadapter: {adapter}\n")
        out[arm] = files
    return out


TEST_BLOCK = '''
# TEST (scripts/train/make_test_cells.py): the 24 test tasks of the parts 3/4 set + public dev16, three arms.
ATTEMPTS = 2  # runs per (task, arm): 40 x 3 x 2 = 240 runs, ~6 h at 6 at once + ~0.5 h startup (= ~13 h quota)
DEV16 = {dev16!r}  # public tasks never generated on (data/splits_public.json)
ARMS = {arms!r}  # arm: (adapter, temperature)
ARM_FILES = {arm_files!r}
assert 200 <= len(ROWS) <= 269, (f'the attached task set has {{len(ROWS)}} tasks: attach rebench-new-cp312 (269, the '
                                 f'parts 3/4 set with the test split), not rebench-final-cp312 / rebench-extra-cp312; found {{OUT}}')
ROWS = {{i: r for i, r in ROWS.items() if r.get('split') == 'test'}}
assert len(ROWS) == 24, f'expected the 24 test tasks, found {{len(ROWS)}}'
for l in open(DATA_DIR / 'tasks.jsonl'):
    r = json.loads(l)
    if r['instance_id'] in DEV16:
        ROWS[r['instance_id']] = {{**r, 'src': 'public', 'level': 'dev16', 'domain': 'public', 'text_kind': 'public',
                                   'leak': False, 'unfair_names': [], 'env_partial': False, 'split': 'dev16'}}
assert len(ROWS) == 40, f'dev16 tasks missing from tasks.jsonl: {{sorted(set(DEV16) - set(ROWS))}}'
print(f"TEST: {{len(ROWS)}} tasks from {{len({{r['repo'] for r in ROWS.values()}})}} repos | levels",
      dict(Counter(r['level'] for r in ROWS.values())))
SUB_ROOT = WORKING_DIR / 'submissions'
ALL_ADAPTERS = WORKING_DIR / 'all_adapters'  # every adapter once, for the one vLLM server
shutil.rmtree(SUB_ROOT, ignore_errors=True)
shutil.rmtree(ALL_ADAPTERS, ignore_errors=True)
for arm, files in ARM_FILES.items():
    for rel, text in files.items():
        (SUB_ROOT / arm / rel).parent.mkdir(parents=True, exist_ok=True)
        (SUB_ROOT / arm / rel).write_text(text, encoding='utf-8')
_ad = sorted(glob.glob('/kaggle/input/**/adapter_31b/final/adapter_config.json', recursive=True))
assert len(_ad) == 1, f'attach the training output (a dataset with adapter_31b/final) exactly once; found {{_ad}}'
ADAPTER_SRC = Path(_ad[0]).parent
_cfg = json.loads((ADAPTER_SRC / 'adapter_config.json').read_text())
print('adapter:', ADAPTER_SRC, '| r', _cfg['r'], '| lora_alpha', _cfg['lora_alpha'], '| scale', _cfg['lora_alpha'] / _cfg['r'],
      '| base', _cfg.get('base_model_name_or_path'), '|', round((ADAPTER_SRC / 'adapter_model.safetensors').stat().st_size / 1e6), 'MB')
assert _cfg['r'] == 16 and _cfg['lora_alpha'] == 16, 'not the trained r16/alpha16 adapter: stop and send me this output'
for arm, (adapter, temp) in ARMS.items():
    if adapter:
        for dst in (SUB_ROOT / arm / 'adapters' / adapter, ALL_ADAPTERS / 'adapters' / adapter):
            if not dst.exists():
                shutil.copytree(ADAPTER_SRC, dst)
    print(arm, '| adapter', adapter, '| temperature', temp, '|',
          [l for l in (SUB_ROOT / arm / 'agent.yaml').read_text().splitlines() if l.startswith(('model:', 'adapter:'))])
'''

CELL5 = r'''# 5. TEST SUMMARY (paste this output to Claude): per arm, per task, where runs end.
rows = [json.loads(l) for l in open(PER_TASK)] if PER_TASK.exists() else []
by = collections.defaultdict(list)
for r in rows:
    by[(r['arm'], r['instance_id'])].append(r['resolved'])
print(f'{len(rows)} runs | {(time.time() - T_START) / 3600:.1f} h')
GROUPS = {'test (24, unseen repos)': {i for i, r in ROWS.items() if r.get('split') == 'test'},
          'dev16 (public, never trained)': {i for i, r in ROWS.items() if r.get('split') == 'dev16'}}
for gname, gids in GROUPS.items():
    print(f'== {gname}')
    for arm in ARMS:
        rs = [r for r in rows if r['arm'] == arm and r['instance_id'] in gids]
        tasks = {i for (a, i) in by if a == arm and i in gids}
        print(f"  {arm:9} runs {sum(r['resolved'] for r in rs):2}/{len(rs):2} | tasks solved at least once "
              f"{sum(any(by[(arm, i)]) for i in tasks):2}/{len(tasks)} | per run {sum(r['resolved'] for r in rs) / max(len(rs), 1) * len(gids):.1f}/{len(gids)} "
              f"| ends {dict(Counter(r['end'] for r in rs))} | median tools {sorted(r['tool_calls'] or 0 for r in rs)[len(rs) // 2] if rs else '-'}")
print('\nper task (runs solved / runs):', ' | '.join(ARMS))
for iid in sorted(ROWS, key=lambda i: (ROWS[i].get('split'), i)):
    cells = [f"{sum(by[(a, iid)])}/{len(by[(a, iid)])}" if by[(a, iid)] else '-' for a in ARMS]
    print(f'  {iid[:45]:45} ' + '   '.join(f'{c:>5}' for c in cells))
arms = list(ARMS)
for other in arms[1:]:  # paired: per task, solve share of the adapter arm vs the base arm
    win = sum(1 for i in ROWS if by[(other, i)] and by[(arms[0], i)] and
              sum(by[(other, i)]) / len(by[(other, i)]) > sum(by[(arms[0], i)]) / len(by[(arms[0], i)]))
    lose = sum(1 for i in ROWS if by[(other, i)] and by[(arms[0], i)] and
               sum(by[(other, i)]) / len(by[(other, i)]) < sum(by[(arms[0], i)]) / len(by[(arms[0], i)]))
    print(f'{other} vs {arms[0]}: better on {win} tasks, worse on {lose}, equal on the rest')
req = WORKING_DIR / 'requests' / 'requests.jsonl'
print('request log:', f'{req.stat().st_size / 1e6:.0f} MB' if req.exists() else 'MISSING')
'''


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    src = ROOT / "kaggle/cells_gen"
    (OUT / "cell1.py").write_text((src / "cell1.py").read_text())

    c2 = G.CELL2.format(submission=G.submission(), embedded_prev=[], sample=[], sub_name="mix")
    mode_line = next(l for l in c2.splitlines() if l.startswith("MODE = "))
    c2 = c2.replace(mode_line, "MODE = 'test'  # three arms on the 24 test tasks (make_test_cells.py)")
    c2 = must_replace(c2, "STOP_NEW_TASKS_AFTER_H = 10.5  # Kaggle ends GPU sessions at 12 h; a task takes <= ~10 min\n",
                      "STOP_NEW_TASKS_AFTER_H = 10.5  # = min(10.5, this account's GPU quota in hours / 2 - 0.4): L4x4 bills 2x,\n"
                      "# a run ends within 15 min, Kaggle ends sessions at 12 h; a killed run loses its output\n")
    # earlier results: only this notebook's own (a re-run in the same session); the training output has none
    c2 = must_replace(c2, "for p in sorted(glob.glob('/kaggle/input/**/results/gen_per_task.jsonl', recursive=True)) + ([str(PER_TASK)] if PER_TASK.exists() else []):\n",
                      "for p in ([str(PER_TASK)] if PER_TASK.exists() else []):\n")
    c2 = must_replace(c2, "ood.patch_harness()\n",  # as cells_gen_combined: public tasks keep the harness's own install
                      "from swegemma.harness import container_setup as _cs0\n"
                      "_HARNESS_INSTALL, _HARNESS_COMPAT = _cs0.install_test_dependencies, _cs0._is_wheel_compatible_py313  # public tasks\n"
                      "ood.patch_harness()\n")
    host = "print('host pytest plugins:', [Path(p).name for p in _host], '-> exit', _r.returncode, _r.stderr[-200:])\n"
    dev16 = sorted(json.load(open(ROOT / "data/splits_public.json"))["dev16"])
    c2 = must_replace(c2, host, host + TEST_BLOCK.format(arms=ARMS, arm_files=arm_submissions(), dev16=dev16))
    (OUT / "cell2.py").write_text(c2 + "\n" + G.sandbox_env())
    comb = ROOT / "kaggle/cells_gen_combined"
    (OUT / "cell2c_public_setup.py").write_text((comb / "cell2c_public_setup.py").read_text())

    c3 = (src / "cell3.py").read_text()
    c3 = must_replace(c3, "# 3. Start vLLM with LoRA on (as the host notebook / scorer). ~6–10 min.",
                      "# 3. Start vLLM with LoRA on and the adapter under test (as the scorer). ~6–10 min.")
    c3 = must_replace(c3, "ADAPTERS = None  # no adapter in this notebook",
                      "ADAPTERS = discover_adapters(str(ALL_ADAPTERS), adapter_extensions=ALLOWED_ADAPTER_EXTENSIONS)")
    tail = "assert str(MODEL_PATH) in _served, 'vLLM does not serve the model: stop and send me this output'\n"
    c3 = must_replace(c3, tail, tail + f'''assert {ADAPTER!r} in _served, 'vLLM does not serve the adapter: stop and send me this output'
def _ask(model):
    body = {{'model': model, 'max_tokens': 60, 'temperature': 0, 'messages': [{{'role': 'user', 'content':
            'You are fixing a bug in /workspace. What is your first tool call? Answer in one line.'}}]}}
    req = _url.Request(_base + '/chat/completions', data=_json.dumps(body).encode(), headers={{'Content-Type': 'application/json'}})
    return _json.load(_url.urlopen(req))['choices'][0]['message'].get('content')
for _m in (str(MODEL_PATH), {ADAPTER!r}):  # greedy: base and adapter answer, both sensible, usually a little different
    print(f'{{_m[-30:]:>30}}:', repr(_ask(_m)))
''')
    (OUT / "cell3.py").write_text(c3)
    (OUT / "cell3b_request_logger.py").write_text((src / "cell3b_request_logger.py").read_text().replace(
        "(training data: tagged task#attempt)", "(test: tagged task#a<arm>.<n>)"))

    c4 = (comb / "cell4_run.py").read_text()  # the combined run's cell 4: public tasks routed to their own setup
    for old, new in (
        ("    PHASES = [(CONCURRENCY, [(i, (i, 1)) for i in ORDER])]\n", None),  # (marker; not in CELL4)
        ("elif MODE == 'prompt':",
         "elif MODE == 'test':  # per task: every arm x attempt back to back, the first arm rotating from task to task\n"
         "    _arms = list(ARMS)\n"
         "    PHASES = [(CONCURRENCY, [(i, f'{_arms[(k + j) % len(_arms)]}.{n}') for k, i in enumerate(ORDER)\n"
         "                             for n in range(1, ATTEMPTS + 1) for j in range(len(_arms))\n"
         "                             if (i, f'{_arms[(k + j) % len(_arms)]}.{n}') not in DONE_JOBS])]\n"
         "elif MODE == 'prompt':"),
        ("MANIFEST = discover_adapters(str(SUB_DIR), adapter_extensions=ALLOWED_ADAPTER_EXTENSIONS)\n",
         "MANIFESTS = {a: discover_adapters(str(SUB_ROOT / a), adapter_extensions=ALLOWED_ADAPTER_EXTENSIONS) for a in ARMS}\n"),
        ("EVAL_CFG = read_eval_config(SUB_DIR)\n",
         "EVAL_CFG = read_eval_config(SUB_ROOT / list(ARMS)[0])\n"
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
    ):
        if new is None:
            continue
        c4 = must_replace(c4, old, new)
    (OUT / "cell4_run.py").write_text(c4)
    (OUT / "cell5_summary.py").write_text(CELL5)
    print("wrote", OUT.relative_to(ROOT), sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
