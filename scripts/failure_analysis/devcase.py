"""Print one dev16 task: issue, gold patch, each mix run's patch + test tail. usage: devcase.py TASK [--full]"""
import glob, json, re, sys
R = '/Users/ziadsamer/Projects/coding-assistant-agent/'
iid = sys.argv[1]
t = next(t for t in map(json.loads, open(R + 'data/tasks.jsonl')) if t['instance_id'] == iid)
print('=' * 30, iid, '\nISSUE:\n', t['problem_statement'][:3500])
print('\nGOLD PATCH:\n', t['patch'][:4000])
print('\nTEST PATCH (names only):', re.findall(r'^\+\s*(?:async )?def (test_\w+)', t['test_patch'], re.M)[:15])
for d in sorted(glob.glob(R + 'data/results/2026-10-1[3-7]_rung3*/results/mix*')):
    if not re.search(r'/mix(_r\d|_c32_r\d)?$', d):
        continue
    rows = [r for r in map(json.loads, open(d + '/task_results.jsonl')) if r['instance_id'] == iid]
    if not rows:
        continue
    r = rows[0]
    p = f"{d}/patches/{iid}.patch"
    patch = open(p).read() if glob.glob(p) else ''
    to = glob.glob(f"{d}/test_outputs/{iid}*")
    tail = open(to[0]).read()[-1200:] if to else ''
    print('\n' + '-' * 20, d.split('results/')[1], '| resolved', r['resolved'], '| calls', r.get('tool_calls'), '| s', r.get('duration_seconds'), '| err', (r.get('error') or '')[:80])
    print(patch[:2500] if patch else '(no patch)')
    if '--full' in sys.argv:
        print('TEST OUTPUT tail:\n', tail)
