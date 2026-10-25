"""One dev16 task over ALL local runs: issue, gold, hidden test, then patches grouped by their added/removed lines."""
import glob, json, os, re, sys, collections as C
R = '/Users/ziadsamer/Projects/coding-assistant-agent/data/'
iid = sys.argv[1]; maxg = int(sys.argv[2]) if len(sys.argv) > 2 else 8
t = next(t for t in map(json.loads, open(R + 'tasks.jsonl')) if t['instance_id'] == iid)
print('=' * 20, iid, '\nISSUE:\n', t['problem_statement'][:2500], '\n\nGOLD:\n', t['patch'][:3000], '\n\nTEST PATCH:\n', t['test_patch'][:2500])
groups = C.defaultdict(list)
for f in glob.glob(R + 'results/*/results/*/task_results.jsonl'):
    d = os.path.dirname(f)
    for r in map(json.loads, open(f)):
        if r['instance_id'] != iid: continue
        p = f"{d}/patches/{iid}.patch"
        patch = open(p).read() if os.path.exists(p) else ''
        key = '\n'.join(l for l in patch.splitlines() if l[:1] in '+-' and not l.startswith(('+++', '---')))
        groups[key].append((r['resolved'], d.split('results/')[1], (r.get('error') or '')[:40]))
print(f'\n{sum(len(v) for v in groups.values())} runs, {len(groups)} distinct patches')
for key, v in sorted(groups.items(), key=lambda kv: -len(kv[1]))[:maxg]:
    s = sum(x[0] for x in v)
    print(f"\n--- {len(v)} runs, solved {s} | ends {dict(C.Counter(x[2] or 'ok' for x in v))} | e.g. {v[0][1]}")
    print(key[:1500] if key else '(EMPTY PATCH)')
