import glob, json, os, re, sys, collections as C
R = '/Users/ziadsamer/Projects/coding-assistant-agent/data/'
for iid in sys.argv[1:]:
    t = next(t for t in map(json.loads, open(R + 'tasks.jsonl')) if t['instance_id'] == iid)
    ps = re.sub(r'<!--.*?-->', '', t['problem_statement'], flags=re.S)
    ps = re.sub(r'## (AI Disclaimer|Checklist).*', '', ps, flags=re.S)
    print('#' * 25, iid, '\nISSUE:', ps.strip()[:900])
    print('GOLD:\n' + '\n'.join(l for l in t['patch'].splitlines() if l[:1] in '+-')[:1400])
    tp = '\n'.join(l for l in t['test_patch'].splitlines() if re.search(r'assert|raises|def test', l))
    print('TEST asserts:\n' + tp[:900])
    groups = C.defaultdict(list)
    for f in glob.glob(R + 'results/*/results/*/task_results.jsonl'):
        d = os.path.dirname(f)
        for r in map(json.loads, open(f)):
            if r['instance_id'] != iid: continue
            p = f"{d}/patches/{iid}.patch"
            patch = open(p).read() if os.path.exists(p) else ''
            key = '\n'.join(l for l in patch.splitlines() if l[:1] in '+-' and not l.startswith(('+++', '---')))
            groups[key].append((r['resolved'], (r.get('error') or 'ok')[:30]))
    n = sum(len(v) for v in groups.values())
    print(f'RUNS {n}: empty {len(groups.get("", []))} | ends', dict(C.Counter(x[1] for v in groups.values() for x in v)))
    for key, v in sorted(groups.items(), key=lambda kv: -len(kv[1]))[:3]:
        if key: print(f'  -- {len(v)} runs:', key[:500].replace('\n', '\n     '))
