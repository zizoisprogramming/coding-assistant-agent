"""dev16 (or any split): per run, where calls / time / output tokens go, from ATIF traces. Groups: mix-family vs all."""
import ast, glob, json, os, re, sys, statistics as S, collections as C
R = '/Users/ziadsamer/Projects/coding-assistant-agent/data/'
split = sys.argv[1] if len(sys.argv) > 1 else 'dev16'
ids = set(json.load(open(R + 'splits_public.json'))[split])
def lit(v):
    if isinstance(v, str):
        try: return ast.literal_eval(v)
        except Exception: return {}
    return v or {}
def kind(name, a):
    cmd = (a.get('command') or '').strip()
    if name in ('edit_file',): return 'edit'
    if name == 'write_file': return 'scratch' if str(a.get('filepath', '')).startswith('/tmp') else 'write-in-repo'
    if name == 'run_command':
        if re.search(r"sed -i|\.write_text\(|open\([^)]*['\"]w['\"]\)|git apply", cmd): return 'edit'
        if re.search(r'pytest|unittest', cmd): return 'test'
        if re.match(r'(python3?|cat\s*>+)', cmd): return 'script'
        if re.search(r'git (status|diff)', cmd): return 'diff'
        if re.search(r'grep|^find|^ls|git (ls-files|log|show|blame)', cmd): return 'search'
        if re.search(r'sed -n|^cat |^head|^tail|^nl ', cmd): return 'read'
        return 'cmd'
    return {'read_file': 'read', 'submit_patch': 'submit', 'get_status': 'status'}.get(name, name or 'none')
runs = []
for f in glob.glob(R + 'results/*/results/*/task_results.jsonl'):
    d = os.path.dirname(f); arm = d.split('/results/')[-1]
    for r in map(json.loads, open(f)):
        if r['instance_id'] not in ids: continue
        tr = f"{d}/traces/trace_{r['instance_id']}.json"
        if not os.path.exists(tr): continue
        steps = json.load(open(tr))['steps']
        t0 = next((lit(s.get('extra')).get('timestamp') for s in steps if lit(s.get('extra')).get('timestamp')), None)
        prev, seq, ptoks = t0, [], []
        for s in steps:
            e = lit(s.get('extra')); t = e.get('timestamp')
            if s.get('source') != 'agent' or not t: 
                prev = t or prev; continue
            m = lit(s.get('metrics')); tcs = lit(s.get('tool_calls')) or []
            obs = str(s.get('observation') or '')
            for i, tc in enumerate(tcs or [None]):
                a = (tc or {}).get('arguments') if isinstance((tc or {}).get('arguments'), dict) else {}
                k = kind((tc or {}).get('function_name'), a) if tc else 'text'
                empty = k == 'search' and ('"exit_code": 1' in obs or "'exit_code': 1" in obs or '\\"stdout\\": \\"\\"' in obs)
                seq.append(dict(k=k, dt=(t - prev) if i == 0 else 0, out=(m.get('completion_tokens') or 0) if i == 0 else 0,
                                p=m.get('prompt_tokens') or 0, empty=empty, refused='BudgetExceeded' in obs, cmd=(a.get('command') or a.get('filepath') or '')[:80]))
            ptoks.append(m.get('prompt_tokens') or 0)
            prev = t
        work = [x for x in seq if x['k'] not in ('submit', 'status', 'text')]
        fe = next((i + 1 for i, x in enumerate(work) if x['k'] == 'edit' and not x['refused']), None)
        comp = sum(1 for a, b in zip(ptoks, ptoks[1:]) if b < a * 0.7)
        runs.append(dict(task=r['instance_id'], arm=arm, mix=arm.startswith('mix') and '12b' not in arm, resolved=r['resolved'], patch=r.get('agent_patch_size') or 0,
                         err=(r.get('error') or 'ok'), seq=seq, work=work, first_edit=fe, comp=comp))
def show(name, sel):
    if not sel: return
    calls = C.Counter(x['k'] for r in sel for x in r['work']); tc = sum(calls.values())
    secs = C.Counter(); [secs.update({x['k']: x['dt']}) for r in sel for x in r['seq']]; ts = sum(secs.values())
    out = C.Counter(); [out.update({x['k']: x['out']}) for r in sel for x in r['seq']]
    print(f"\n== {name}: {len(sel)} runs | ends {dict(C.Counter(re.sub(r'[(].*', '', r['err'])[:28] for r in sel))}")
    print('  calls per run (median)', S.median(len(r['work']) for r in sel), '| compactions/run', round(S.mean(r['comp'] for r in sel), 2),
          '| empty searches/run', round(S.mean(sum(x['empty'] for x in r['work']) for r in sel), 1),
          '| refused calls/run', round(S.mean(sum(x['refused'] for x in r['seq']) for r in sel), 1),
          '| write-in-repo runs', sum(any(x['k'] == 'write-in-repo' for x in r['work']) for r in sel))
    print('  share of CALLS :', ' '.join(f"{k} {100*v/tc:.0f}%" for k, v in calls.most_common()))
    print('  share of TIME  :', ' '.join(f"{k} {100*v/ts:.0f}%" for k, v in secs.most_common(8)), f'| median run {S.median(sum(x["dt"] for x in r["seq"]) for r in sel):.0f}s')
    print('  output tokens/run (median)', S.median(sum(x['out'] for x in r['seq']) for r in sel), '| s per call (median)', round(S.median(x['dt'] for r in sel for x in r['seq'] if x['dt']), 1))
mixr = [r for r in runs if r['mix']]
noedit = lambda rs: [r for r in rs if not r['first_edit'] and not r['resolved']]
show(f'{split} MIX-family, NO EDIT, not solved', noedit(mixr))
show(f'{split} MIX-family, SOLVED', [r for r in mixr if r['resolved']])
show(f'{split} MIX-family, edited but not solved', [r for r in mixr if r['first_edit'] and not r['resolved']])
show(f'{split} ALL versions, NO EDIT, not solved', noedit(runs))
print('\nfirst edit at call (mix, solved):', sorted(r['first_edit'] for r in mixr if r['resolved'] and r['first_edit']))
print('first edit at call (mix, edited, failed):', sorted(r['first_edit'] for r in mixr if r['first_edit'] and not r['resolved']))
json.dump([{k: v for k, v in r.items() if k != 'seq'} for r in runs], open(f'/tmp/devtime_{split}.json', 'w'))
