"""Writes kaggle/cells_skill_s6i/: sk_nav_s6_32i (sk_nav_s6_32 + install as route step 1) alone on all 16 dev16
tasks, 1 pass (user 2026-10-28; the 7-task set: TASKS = WINNABLE7, PASSES = 2). Earlier: kaggle/cells_skill_s6 =
b57d56d (sk_nav_s6 3/16, sk_nav_s6_32 6/16). Earlier: kaggle/cells_skill_nav32 = 8750b35 (sk_nav_32 4/16, 387 s/task). Arms may differ only in
max_tool_calls. Earlier: kaggle/cells_skill_nav2 = 8220cc6 (sk_nav2 2/7, sk_nav2_32 3/7, pass 1 only). Earlier: kaggle/cells_skill_nav = 329307b (sk_nav 5 + 3 of 7). Earlier: kaggle/cells_skill_a5 = 3bef97a (sk_a5 3/16, sk_a5r 3/16).
Earlier: kaggle/cells_skill_a4p1 = 32f7f2a (sk_a4 2/16, sk_p1 6/32, sk_a2_t05 3/16). Earlier runs: kaggle/cells_skill_a3 = 6c5d224 (sk_a3 2/16), kaggle/cells_skill_a2 = 6216e2e
(sk_a2 7/32, sk_ad2 3/32), kaggle/cells_skill_ad = 333285f, kaggle/cells_skill_arms = 82c8d56.

    python3 scripts/make_skill_arms.py && python3 scripts/train/make_skill_arms_cells.py

After pass 1, an arm that solved EARLY_STOP_MAX or fewer tasks is dropped from pass 2; with none left the run ENDS BY
ITSELF (a cancelled saved version loses all output files). After every run, the log gets a DIGEST line from the model replies (survives a cancel):
reading-tool use (find / outline / show / note / pin), raw reads (cat, sed, grep, read_file), NOT SHOWN AGAIN
refusals, the call of the first edit, compactions, model seconds vs tool seconds per call; results/digest.jsonl too.

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

OUT = ROOT / "kaggle/cells_skill_d40"
ARMS = ["sk_a2"]
# the winnable dev16 tasks: tier 1 (mix 55-95%) + tier 2 (14-35% over all arms); the other 9 were 0 in ~150 runs
WINNABLE7 = ["rich_3882", "fastapi_15589", "fastapi_11194", "rich_4079", "rich_3521", "fastapi_14419", "rich_3470"]
SPLITS = json.load(open(ROOT / "data/splits_public.json"))
# d40 (user 2026-10-29): the 8 winnable dev16 + val 16 + test 16 = 40 tasks; 8 tasks alone are +-2 noise per pass
SPLIT_OF = {t: k for k in ("dev16", "val", "test") for t in SPLITS[k]}
TASKS = sorted(WINNABLE7 + ["rich_3180"] + SPLITS["val"] + SPLITS["test"])  # the 8 winnable only: sorted(WINNABLE7 + ["rich_3180"])
PASSES = 1  # d40 baseline: one pass (~2.4 h); early stop needs a pass 2, so it does nothing here
CONCURRENCY = 2
EARLY_STOP_MAX = 3  # user: after pass 1, an arm that solved 3 or fewer stops (mix: 3.67 per pass)


def arm_files(arm):
    base = ROOT / "submissions" / arm
    return {p.relative_to(base).as_posix(): p.read_text() for p in sorted(base.rglob("*")) if p.is_file()}


def gen_reference():
    """val/test: the 10-24 generation run (mix, T1.0, 15 min, 1 run each), re-graded on CPU: task -> solved."""
    g = json.load(open(ROOT / "data/results/2026-10-24_gen_combined/regrade.json"))
    return {t: int(g[t]["resolved"]) for t in sorted(TASKS) if t in g}


def mix_reference():
    """Pure mix (arms mix, mix_r1, mix_r2) on dev16: task -> [solved, no patch, runs]."""
    dev = set(TASKS)
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
# SKILL ARMS (scripts/train/make_skill_arms_cells.py): a dev16 task set, pass 1 before pass 2.
ATTEMPTS = {passes!r}  # passes; after pass 1 an arm with EARLY_STOP_MAX or fewer solved is dropped (none left: the run ends)
EARLY_STOP_MAX = {early_stop_max!r}
ARMS = {arms!r}
ARM_FILES = {arm_files!r}
TASK_SET = {dev16!r}
MIX_REF = {mix_ref!r}  # mix (T0.2, 8 min, 2 at once) on these tasks: task -> [solved, no patch, runs]
GEN_REF = {gen_ref!r}  # val/test: mix at T1.0, 15 min, 1 run each (2026-10-24 generation run, re-graded): task -> solved
SPLIT_OF = {split_of!r}
ROWS = {{}}
for l in open(DATA_DIR / 'tasks.jsonl'):
    r = json.loads(l)
    if r['instance_id'] in TASK_SET:
        _sp = SPLIT_OF[r['instance_id']]
        ROWS[r['instance_id']] = {{**r, 'src': 'public', 'level': _sp, 'domain': 'public', 'text_kind': 'public',
                                   'leak': False, 'unfair_names': [], 'env_partial': False, 'split': _sp}}
assert len(ROWS) == len(TASK_SET), f'tasks missing from tasks.jsonl: {{sorted(set(TASK_SET) - set(ROWS))}}'
print(f"SKILL ARMS: {{len(ROWS)}} tasks {{dict(Counter(SPLIT_OF[t] for t in ROWS))}} {{sorted(ROWS)}} | arms {{ARMS}} | {{ATTEMPTS}} passes | {{CONCURRENCY}} at once | "
      f"after pass 1, arms solving {{EARLY_STOP_MAX}} or fewer stop")
SUB_ROOT = WORKING_DIR / 'submissions'
shutil.rmtree(SUB_ROOT, ignore_errors=True)
for arm, files in ARM_FILES.items():
    for rel, text in files.items():
        (SUB_ROOT / arm / rel).parent.mkdir(parents=True, exist_ok=True)
        (SUB_ROOT / arm / rel).write_text(text, encoding='utf-8')
    _ev = (SUB_ROOT / arm / 'eval_config.yaml').read_text()
    _cp = SUB_ROOT / arm / 'skills/agent/scripts/commands.txt'
    _cmds = _cp.read_text().split() if _cp.exists() else ['(no skill)']
    print(arm, '| tools', [l.split('#')[0].strip()[2:] for l in (SUB_ROOT / arm / 'agent.yaml').read_text().splitlines() if l.strip().startswith('- ')][:8],
          '| skill commands', _cmds, '| budgets', ' '.join(l.strip() for l in _ev.splitlines() if ':' in l and 'evaluation' not in l))
    assert 'max_time_minutes: 8' in _ev, 'arms run with the 8-minute limit (as mix\\'s dev16 runs)'
'''

CELL5 = r'''# 5. SKILL ARMS SUMMARY (paste this output to Claude): per pass, per arm vs mix's 64 dev16 runs, per task.
rows = [json.loads(l) for l in open(PER_TASK)] if PER_TASK.exists() else []
mix_solved = sum(s / n for s, _, n in MIX_REF.values())
mix_nopatch = sum(p / n for _, p, n in MIX_REF.values())
print(f'{len(rows)} runs | {(time.time() - T_START) / 3600:.1f} h | mix reference per pass over these tasks: solved {mix_solved:.2f}, '
      f'no patch {mix_nopatch:.2f}')
for n in range(1, ATTEMPTS + 1):
    rs = [r for r in rows if r['attempt'].endswith(f'.{n}')]
    if not rs:
        continue
    print(f'\n== PASS {n}: {len(rs)} runs')
    for arm in ARMS:
        a = [r for r in rs if r['arm'] == arm]
        print('  ' + arm + ' by split: ' + ' | '.join(f"{sp} {sum(r['resolved'] for r in a if SPLIT_OF[r['instance_id']] == sp)}/"
              f"{sum(1 for r in a if SPLIT_OF[r['instance_id']] == sp)}" for sp in ('dev16', 'val', 'test'))
              + ' | reference: mix T0.2 8 min ' + ' '.join(f"{sp} {sum(s / n for t, (s, _, n) in MIX_REF.items() if SPLIT_OF.get(t) == sp):.1f}"
                                                       for sp in ('dev16', 'val'))
              + f" | gen T1.0 15 min test {sum(v for t, v in GEN_REF.items() if SPLIT_OF.get(t) == 'test')}")
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
    ref = f'mix {s}/{n} ({p})' if n else f"gen {'S' if GEN_REF.get(iid) else '-'}"
    print(f'  {iid:16} {SPLIT_OF.get(iid, "?"):5} {ref:12}  ' + '   '.join(f'{c:>4}' for c in cells))
dig = [json.loads(l) for l in open(RESULTS / 'digest.jsonl')] if (RESULTS / 'digest.jsonl').exists() else []
print('\nper arm, mean per run (from the model replies; see the DIGEST lines):')
for arm in ARMS:
    d = [x for x in dig if x['arm'] == arm]
    if d:
        m = lambda k: sum(x.get(k) or 0 for x in d) / len(d)
        fe = sorted(x['first_edit'] for x in d if x.get('first_edit'))
        print(f"  {arm:8} runs {len(d)} | a.py find {m('find'):.1f} outline {m('outline'):.1f} show {m('show'):.1f} "
              f"| replace {m('replace'):.1f} run {m('run'):.1f} failed edits {m('edit_fail'):.1f} "
              f"| callers shown {m('callers'):.1f} ping-pong {m('pingpong'):.1f} WHERE written {sum(1 for x in d if x.get('where_at'))}/{len(d)} "
              f"| plan {m('plan'):.1f} blocked {m('blocked'):.1f} debug flags {m('debug_flag'):.1f} "
              f"| raw reads {m('raw_read') + m('read_file'):.1f} | scripts/tests before edit {m('pre_edit_runs'):.1f} | reshown {m('reshown'):.1f} | banner runs "
              f"{sum(1 for x in d if x.get('banner') or x.get('stop_banner'))} | call 1 wrong "
              f"{sum(1 for x in d if x.get('call1_wrong'))} | pip {m('pip'):.1f} | repro {m('repro'):.1f} pytest {m('pytest'):.1f} | edited {len(fe)}/{len(d)}, median "
              f"first edit at call {fe[len(fe) // 2] if fe else '-'} | compactions {m('compactions'):.1f} | model "
              f"{m('model_s'):.0f}s + tools {m('tool_s'):.0f}s")
req = WORKING_DIR / 'requests' / 'requests.jsonl'
print('request log:', f'{req.stat().st_size / 1e6:.0f} MB' if req.exists() else 'MISSING')
'''


DIGEST = r'''

# DIGEST (make_skill_arms_cells.py): per run (job task#a<arm>.<pass>), counted from the model replies as they come:
# what the agent did with its calls and where the time went. Cell 4 prints one line after each run (it stays in the
# log even if the session is cancelled) and appends it to results/digest.jsonl.
import collections, re
from google.adk.models import lite_llm as _ll

DIGEST = collections.defaultdict(collections.Counter)
_A_PY = re.compile(r'\.git/agent/a\.py\s+(\w+)')
_RAW = re.compile(r'(^|[;&|(]\s*)(cat|sed|head|tail|grep|nl|less|awk)\s|git grep|git show \S+:')


def _dump(o):
    if hasattr(o, 'model_dump'):
        try:
            return o.model_dump()
        except Exception:
            return {}
    return o if isinstance(o, dict) else {}


def _text(content):
    if isinstance(content, list):
        return ' '.join(str(_dump(c).get('text') or c) for c in content)
    return str(content or '')


def _digest(job, messages, resp, seconds):
    d = DIGEST[job]
    d['model_calls'] += 1
    d['model_ms'] += int(seconds * 1000)
    last = _dump(messages[-1]) if messages else {}
    if last.get('role') == 'tool':
        out = _text(last.get('content'))
        d['refused'] += 'NOT SHOWN AGAIN' in out
        d['reshown'] += 'ALREADY SHOWN' in out
        d['banner'] += 'NO EDIT YET' in out
        d['stop_banner'] += 'STOP READING' in out
        d['blocked'] += 'BLOCKED: ' in out
        d['debug_flag'] += 'DEBUG LINE IN YOUR DIFF' in out
        d['callers'] += 'CALLED FROM' in out
        d['pingpong'] += 'PING-PONG:' in out
        d['edit_fail'] += any(k in out for k in ('FileEditError', 'old_string not found', 'REPLACE FAILED'))
    r = _dump(resp)
    usage = r.get('usage') or {}
    pt = usage.get('prompt_tokens') or 0
    if d['last_prompt'] and pt < 0.7 * d['last_prompt']:
        d['compactions'] += 1
    d['last_prompt'] = pt
    d['max_prompt'] = max(d['max_prompt'], pt)
    d['out_tokens'] += usage.get('completion_tokens') or 0
    msg = ((r.get('choices') or [{}])[0] or {}).get('message') or {}
    if msg.get('tool_calls') and 'WHERE:' in _text(msg.get('content')) + str(msg.get('reasoning_content') or '') and not d['where_at']:
        d['where_at'] = d['tool_calls'] + 1  # the call that came with the first WHERE / WHY / CHANGE lines
    for tc in msg.get('tool_calls') or []:
        fn = (tc or {}).get('function') or {}
        name, args = fn.get('name') or '?', fn.get('arguments') or ''
        try:
            a = json.loads(args) if isinstance(args, str) else (args or {})
        except Exception:
            a = {}
        d['tool_calls'] += 1
        n = d['tool_calls']
        edit = False
        if name == 'run_command':
            cmd = str(a.get('command', ''))
            subs = _A_PY.findall(cmd)
            for c in subs:
                d[c if c in ('find', 'outline', 'show', 'note', 'pin', 'impact', 'check', 'plan', 'replace', 'run') else 'a_other'] += 1
            if not subs and _RAW.search(cmd):
                d['raw_read'] += 1
            if 'pytest' in cmd:
                d['pytest'] += 1
            if not d['first_edit'] and (('run' in subs) or (re.search(r'pytest|python3?\s+(-c\b|-\s*<<|-m\b|\S+\.py)', cmd)
                                                            and not subs)):
                d['pre_edit_runs'] += 1  # a script or test run before the first edit (solved 8/17 at 0-4, 2/11 at 5+)
            if re.search(r'\bpip\b', cmd):
                d['pip'] += 1
            if 'repro.py' in cmd:
                d['repro'] += 1
            edit = 'git apply' in cmd or 'sed -i' in cmd or ('.write' in cmd and '<<' in cmd) or 'replace' in subs
        elif name in ('edit_file', 'write_file'):
            path = str(a.get('filepath') or a.get('file_path') or a.get('path') or '')
            if '.git/agent/' in path:
                d['repro'] += 1
            else:
                d[name] += 1
                edit = True
        elif name == 'run_skill_script':
            d['install'] += 1
            d['install_at'] = d['install_at'] or n
        else:
            d[name] += 1
        if n == 1 and name != 'run_skill_script':
            d['call1_wrong'] = 1
        if edit and not d['first_edit']:
            d['first_edit'] = n


_inner = _ll.LiteLLMClient.acompletion
if not getattr(_inner, '_digest', False):
    async def _acompletion_digest(self, model, messages, tools, **kwargs):
        t0 = time.time()
        resp = await _inner(self, model, messages, tools, **kwargs)
        try:
            _digest(JOB.get(), messages, resp, time.time() - t0)
        except Exception as e:  # never break a run over the digest
            DIGEST[JOB.get()]['digest_errors'] += 1
        return resp
    _acompletion_digest._digest = True
    _ll.LiteLLMClient.acompletion = _acompletion_digest


def digest_row(job, agent_s):
    d = DIGEST.get(job) or collections.Counter()
    model_s = d['model_ms'] / 1000
    n = max(d['tool_calls'], 1)
    keys = ('install', 'install_at', 'find', 'outline', 'show', 'note', 'pin', 'impact', 'check', 'a_other', 'raw_read',
            'read_file', 'pre_edit_runs', 'plan', 'blocked', 'debug_flag', 'replace', 'run', 'callers', 'pingpong', 'where_at', 'edit_fail', 'refused', 'reshown', 'banner', 'stop_banner', 'pip', 'call1_wrong', 'repro', 'pytest', 'edit_file', 'write_file', 'first_edit', 'compactions',
            'max_prompt', 'out_tokens', 'model_calls', 'tool_calls', 'get_status', 'submit_patch', 'digest_errors')
    row = {k: d[k] for k in keys}
    row.update(model_s=round(model_s), tool_s=round(max(agent_s - model_s, 0)),
               model_s_per_call=round(model_s / max(d['model_calls'], 1), 1),
               tool_s_per_call=round(max(agent_s - model_s, 0) / n, 1))
    return row


def digest_line(r):
    return (f"      DIGEST install@{r['install_at'] or '-'} | a.py find {r['find']} outline {r['outline']} show "
            f"{r['show']} note {r['note']} pin {r['pin']} | raw reads {r['raw_read']} read_file {r['read_file']} | "
            f"scripts/tests before edit {r['pre_edit_runs']} | a.py replace {r['replace']} run {r['run']} | failed edits "
            f"{r['edit_fail']} | navigator: callers {r['callers']} ping-pong {r['pingpong']} WHERE at call {r['where_at'] or '-'} | plan {r['plan']} blocked {r['blocked']} debug flags "
            f"{r['debug_flag']} | refused {r['refused']} reshown {r['reshown']} | banners {r['banner']}+{r['stop_banner']} stop | pip {r['pip']} | "
            f"edit_file/write_file {r['edit_file'] + r['write_file']}, first edit at call {r['first_edit'] or '-'} | "
            f"repro {r['repro']} pytest {r['pytest']} | compactions {r['compactions']} max prompt {r['max_prompt']} | "
            f"model {r['model_s']}s ({r['model_s_per_call']}s/call) tools {r['tool_s']}s ({r['tool_s_per_call']}s/call) "
            f"| out tokens {r['out_tokens']}" + (f" | DIGEST ERRORS {r['digest_errors']}" if r['digest_errors'] else ''))
print('DIGEST on: one line per run after its result line (results/digest.jsonl)')
'''


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    src, comb = ROOT / "kaggle/cells_gen", ROOT / "kaggle/cells_gen_combined"
    (OUT / "cell1.py").write_text((src / "cell1.py").read_text())

    c2 = G.CELL2.format(submission=G.submission(), embedded_prev=[], sample=[], sub_name="mix")
    mode_line = next(l for l in c2.splitlines() if l.startswith("MODE = "))
    c2 = c2.replace(mode_line, "MODE = 'skill_arms'  # skill arms on a dev16 task set (make_skill_arms_cells.py)")
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
    dev16 = sorted(TASKS)
    assert set(TASKS) <= set(SPLIT_OF)
    c2 = must_replace(c2, host, host + BLOCK.format(passes=PASSES, arms=ARMS, early_stop_max=EARLY_STOP_MAX, arm_files={a: arm_files(a) for a in ARMS}, dev16=dev16,
                                                    mix_ref=mix_reference(), gen_ref=gen_reference(),
                                                    split_of={t: SPLIT_OF[t] for t in dev16}))
    (OUT / "cell2.py").write_text(c2 + "\n" + G.sandbox_env())
    (OUT / "cell2c_public_setup.py").write_text((comb / "cell2c_public_setup.py").read_text())
    (OUT / "cell3.py").write_text((src / "cell3.py").read_text())  # vLLM as the scorer (LoRA on, no adapter)
    (OUT / "cell3b_request_logger.py").write_text((src / "cell3b_request_logger.py").read_text().replace(
        "(training data: tagged task#attempt)", "(skill arms: tagged task#a<arm>.<pass>)") + DIGEST)

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
         "EVAL_CFGS = {a: read_eval_config(SUB_ROOT / a) for a in ARMS}  # arms may differ only in max_tool_calls\n"
         "EVAL_CFG = EVAL_CFGS[ARMS[0]]\n"
         "assert all({**c, 'max_tool_calls': 0} == {**EVAL_CFG, 'max_tool_calls': 0} for c in EVAL_CFGS.values()), "
         "'arms differ in budgets other than max_tool_calls'\n"),
        ("display_mode='quiet', **EVAL_CFG))", "display_mode='quiet', **EVAL_CFGS[arm]))"),
        ("def evaluator_for(iid):\n", "def evaluator_for(iid, arm):\n"),
        ("results_dir=RESULTS / 'gen', submission_dir=SUB_DIR,", "results_dir=RESULTS / 'gen', submission_dir=SUB_ROOT / arm,"),
        ("adapter_manifest=MANIFEST,", "adapter_manifest=MANIFESTS[arm],"),
        ("evaluator_for(ORDER[0])  # fail before any task if the submission does not build into a config\n"
         "print('budgets', EVAL_CFG, '| adapters', list(MANIFEST.adapters))\n",
         "for _a in ARMS:  # fail before any task if a submission does not build into a config\n"
         "    evaluator_for(ORDER[0], _a)\n"
         "    print(_a, '| budgets', EVAL_CFGS[_a], '| adapters', list(MANIFESTS[_a].adapters))\n"),
        ("evaluator_for(iid), time.time()", "evaluator_for(iid, attempt.split('.')[0]), time.time()"),
        ("row = {'instance_id': iid, 'attempt': attempt, 'mode': MODE,",
         "row = {'instance_id': iid, 'attempt': attempt, 'arm': attempt.split('.')[0], 'mode': MODE,"),
        ("    await asyncio.gather(*(one(i, a) for i, a in jobs))\n",
         "    await asyncio.gather(*(one(i, a) for i, a in jobs))  # jobs are queued in pass order (pass 1 first)\n"),
    ):
        c4 = must_replace(c4, old, new)
    # a line when a pass ends; after pass 1 the run ends by itself unless an arm solved more than EARLY_STOP_MAX
    c4 = must_replace(c4, "    print('PHASE', json.dumps(PHASE_STATS[-1]), flush=True)\n",
                      "    print('PHASE', json.dumps(PHASE_STATS[-1]), flush=True)\n"
                      "    print('=' * 20, f'PASS {phase_no} COMPLETE: every arm ran once more on all {len(ROWS)} tasks', '=' * 20, flush=True)\n")
    c4 = must_replace(c4, "async def run_all():\n    for k, (conc, jobs) in enumerate(PHASES, 1):\n"
                          "        await run_phase(conc, jobs, k)\n",
                      "async def run_all():\n    global N_JOBS\n    for k, (conc, jobs) in enumerate(PHASES, 1):\n"
                      "        await run_phase(conc, jobs, k)\n"
                      "        if k == 1 and len(PHASES) > 1:  # per arm: only arms above EARLY_STOP_MAX get pass 2\n"
                      "            per_arm = {a: sum(r['resolved'] for r in DONE if r['arm'] == a and r['phase'] == 1) for a in ARMS}\n"
                      "            keep = [a for a in ARMS if per_arm[a] > EARLY_STOP_MAX]\n"
                      "            if not keep:\n"
                      "                print(f'EARLY STOP: pass 1 solved {per_arm}, no arm above {EARLY_STOP_MAX} -> pass 2 skipped, '\n"
                      "                      'the run ends here (outputs saved)', flush=True)\n"
                      "                break\n"
                      "            dropped = [a for a in ARMS if a not in keep]\n"
                      "            PHASES[1:] = [(c, [(i, at) for i, at in js if at.split('.')[0] in keep]) for c, js in PHASES[1:]]\n"
                      "            N_JOBS = len(DONE) + sum(len(js) for _, js in PHASES[1:])\n"
                      "            print(f'pass 1 solved {per_arm}: pass 2 runs {keep}' + (f'; dropped {dropped} '\n"
                      "                  f'({EARLY_STOP_MAX} or fewer)' if dropped else ''), flush=True)\n")
    # the DIGEST line after each run's result line (cell 3b counts it from the model replies)
    c4 = must_replace(c4, "                  + (f\"\\n      err: {row['error'][:200]!r}\" if row['end'] not in ('ok', 'time', 'tool_budget') else ''),\n"
                          "                  flush=True)\n",
                      "                  + (f\"\\n      err: {row['error'][:200]!r}\" if row['end'] not in ('ok', 'time', 'tool_budget') else ''),\n"
                          "                  flush=True)\n"
                          "            dg = {'job': f'{iid}#a{attempt}', 'instance_id': iid, 'arm': row['arm'], 'attempt': attempt,\n"
                          "                  'resolved': row['resolved'], 'end': row['end'], 'patch_chars': row['patch_chars'],\n"
                          "                  **digest_row(f'{iid}#a{attempt}', row['agent_s'])}\n"
                          "            print(digest_line(dg), flush=True)\n"
                          "            with open(RESULTS / 'digest.jsonl', 'a', encoding='utf-8') as fh:\n"
                          "                fh.write(json.dumps(dg) + '\\n')\n")
    (OUT / "cell4_run.py").write_text(c4)
    (OUT / "cell5_summary.py").write_text(CELL5)
    print("wrote", OUT.relative_to(ROOT), sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
