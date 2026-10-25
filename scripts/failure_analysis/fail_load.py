"""Load exported failed runs + gold + regrade; per run: issue, gold files, our files, calls by kind, end, final thinking."""
import glob, gzip, json, re, sys
R = '/Users/ziadsamer/Projects/coding-assistant-agent/'
sys.path.insert(0, R + 'scripts'); import triage as T
TASKS = {}
for p in glob.glob(R + 'data/results/2026-10-2*_rebench_*/rebench/tasks.jsonl') + [R + 'data/tasks.jsonl']:
    for t in map(json.loads, open(p)): TASKS[t['instance_id']] = t
RG = json.load(open(R + 'data/results/2026-10-24_gen_combined/regrade.json'))
def src_files(p): return {f for f in T.diff_files(p or '') if not re.search(r'(^|/)tests?/|test_|conftest', f)}
def load():
    runs = []
    for f in sorted(glob.glob(R + 'data/results/2026-10-25_failed/*.jsonl.gz')):
        for r in map(json.loads, gzip.open(f, 'rt')):
            row = r['row']; iid = row['instance_id']
            if row.get('level') == 'public':
                row['resolved'] = bool(RG.get(iid, {}).get('resolved'))
            if row['resolved']: continue
            recs = [x for x in r['records'] if 'request' in x]
            calls, thoughts = [], []
            for x in recs:
                msgs = x['request']['messages'] + [dict((x.get('reply') or {}).get('message') or {}, role='assistant')]
                for m in msgs:
                    if m.get('role') == 'assistant':
                        for tc in m.get('tool_calls') or []:
                            fn = tc.get('function') or {}
                            try: a = json.loads(fn.get('arguments') or '{}')
                            except Exception: a = {}
                            calls.append((tc.get('id'), fn.get('name'), a if isinstance(a, dict) else {}))
                        if m.get('reasoning_content'): thoughts.append(m['reasoning_content'])
            seen, uniq = set(), []
            for c in calls:
                if c[0] not in seen: seen.add(c[0]); uniq.append(c)
            t = TASKS.get(iid, {})
            runs.append(dict(job=r['job'], iid=iid, level=row.get('level'), end=row.get('end'), row=row, patch=r.get('patch') or '',
                             gold=t.get('patch', ''), test=t.get('test_patch', ''), issue=t.get('problem_statement', ''),
                             gold_files=src_files(t.get('patch')), our_files=src_files(r.get('patch')), calls=uniq,
                             thoughts=thoughts, summaries=[x.get('summary') for x in r['records'] if x.get('summary_call')]))
    return runs
