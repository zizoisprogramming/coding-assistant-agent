# 4. TEMPERATURE REPLAY (no tasks, no sandbox): real pub024 requests from the moment just before their first source edit are
#    re-sent at several temperatures, thinking 2048. Question: does a hotter model put the edit on the right lines more often,
#    or break the call more often? It measures where edits land, not whether they pass the hidden tests. Scored locally by
#    scripts/paper/analyze_replay_temp.py. Attach a finished skill-arms notebook's output (it holds requests/requests.jsonl). Ends by itself.
import concurrent.futures as cf, glob as _glob, json as _j, os as _os, random as _r, re as _re, threading, time as _t, urllib.request as _u
from collections import Counter, defaultdict
from pathlib import Path as _P

SEED, N_CONTEXTS, CONCURRENCY = 20261106, 30, 4
TEMPERATURES, SAMPLES = (0.2, 0.7, 1.0), 3
MAX_PER_TASK = 2
STOP_NEW_AFTER_S = 85 * 60  # no new call after this; a call lasts at most ~4 min, so the cell ends by itself
OUT_DIR = _P(_os.environ.get('PROBE_OUT', '/kaggle/working/replay')); OUT_DIR.mkdir(parents=True, exist_ok=True)
INPUT = _os.environ.get('PROBE_INPUT', '/kaggle/input/**/requests/requests.jsonl')
TEST_RE = _re.compile(r'(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$|pytest\.ini$')
try:
    BASE = _os.environ.get('PROBE_BASE_URL') or server_instance.base_url.rstrip('/')
    MODEL = _os.environ.get('PROBE_MODEL') or str(MODEL_PATH)
except NameError as e:
    raise SystemExit('run cells 1 and 3 first') from e
BASE = BASE if BASE.endswith('/v1') else BASE + '/v1'


def first_source_edit(tool_calls):
    for c in tool_calls or []:
        if c['function']['name'] != 'edit_file':
            continue
        try:
            a = _j.loads(c['function']['arguments'])
        except ValueError:
            a = {}
        p = str(a.get('filepath') or '')
        if p and not p.startswith('/tmp') and '.git/agent' not in p and not TEST_RE.search(p):
            return {'filepath': p, 'old_string': a.get('old_string'), 'new_string': a.get('new_string')}
    return None


def load_contexts():
    files = sorted(_glob.glob(INPUT, recursive=True))
    assert files, f'no requests.jsonl under {INPUT}: attach a finished skill-arms notebook output'
    by_job = defaultdict(list)
    for f in files:
        for l in open(f, encoding='utf-8'):
            try:
                r = _j.loads(l)
            except ValueError:
                continue
            if isinstance(r.get('reply'), dict) and 'apub024' in (r.get('job') or '') and (r.get('request') or {}).get('tools'):
                by_job[f, r['job']].append(r)
    rows = []
    for (f, job), q in by_job.items():
        q.sort(key=lambda r: r['t'])
        for r in q:
            orig = first_source_edit(r['reply']['message'].get('tool_calls'))
            if orig:
                rows.append((job, r['request'], orig))
                break
    print(f'{len(files)} request files, {len(by_job)} pub024 runs, {len(rows)} with a source edit call')
    _r.Random(SEED).shuffle(rows)
    picked, per_task = [], Counter()
    for row in rows:
        t = row[0].split('#')[0]
        if per_task[t] < MAX_PER_TASK:
            per_task[t] += 1; picked.append(row)
        if len(picked) == N_CONTEXTS:
            break
    assert len(picked) >= 8, f'only {len(picked)} contexts'
    print(f'{len(picked)} contexts from {len(per_task)} tasks')
    return picked


CONTEXTS = load_contexts()
JOBS = [dict(ctx=i, T=T, sample=s) for i in range(len(CONTEXTS)) for T in TEMPERATURES for s in range(SAMPLES)]
_r.Random(SEED + 1).shuffle(JOBS)  # a cut run stays balanced
print(f'{len(JOBS)} calls planned ({len(CONTEXTS)} contexts x {len(TEMPERATURES)} temperatures x {SAMPLES})')
T0, DONE, LOCK, RESULTS = _t.time(), [0], threading.Lock(), OUT_DIR / 'results.jsonl'
TALLY = defaultdict(Counter)


def call(job):
    job_id, req, orig = CONTEXTS[job['ctx']]
    body = {'model': MODEL, 'messages': req['messages'], 'tools': req['tools'], 'temperature': job['T'], 'top_p': 0.95, 'max_tokens': 4096,
            'seed': SEED + 1000 * job['ctx'] + 10 * job['sample'] + int(job['T'] * 10),
            'chat_template_kwargs': {'enable_thinking': True}, 'thinking_token_budget': 2048}  # direct to the server: extra_body's keys at the top level
    q = _u.Request(BASE + '/chat/completions', data=_j.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    t = _t.time()
    with _u.urlopen(q, timeout=300) as f:
        rep = _j.load(f)
    return job_id, orig, rep, _t.time() - t


def work(job):
    if _t.time() - T0 > STOP_NEW_AFTER_S:
        return
    try:
        job_id, orig, rep, secs = call(job)
        m = rep['choices'][0]['message']
        calls = [{'name': c['function']['name'], 'arguments': c['function']['arguments']} for c in m.get('tool_calls') or []]
        row = dict(job, job_id=job_id, orig=orig, calls=calls, seconds=round(secs, 1), tokens=(rep.get('usage') or {}).get('completion_tokens'), finish=rep['choices'][0].get('finish_reason'))
        first = calls[0]['name'] if calls else 'text'
    except Exception as e:
        row, first = dict(job, error=repr(e)[:300]), 'ERROR'
    with LOCK:
        with open(RESULTS, 'a') as f:
            f.write(_j.dumps(row) + '\n')
        DONE[0] += 1
        TALLY[job['T']][first] += 1
        if DONE[0] % 5 == 0 or first == 'ERROR':
            el = _t.time() - T0
            print(f"[{DONE[0]:3}/{len(JOBS)}] T={job['T']} -> {first} | {row.get('seconds', '-')} s, {row.get('tokens', '-')} tokens | {el/60:.1f} min, {DONE[0]/max(el/60, .01):.1f} calls/min", flush=True)


with cf.ThreadPoolExecutor(CONCURRENCY) as ex:
    list(ex.map(work, JOBS))
print(f'done: {DONE[0]} of {len(JOBS)} calls in {(_t.time() - T0)/60:.1f} min -> {RESULTS}')
for T in TEMPERATURES:
    print(f'T={T}: first tool call', dict(TALLY[T].most_common()))
