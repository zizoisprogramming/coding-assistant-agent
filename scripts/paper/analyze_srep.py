import json,collections,statistics as st,re,math
d='data/results/2026-11-06_skill_srep'
T={json.loads(l)['instance_id']:json.loads(l) for l in open('data/tasks.jsonl')}
SP=json.load(open('data/splits_public.json')); DEV=set(SP['dev16'])
R=[json.loads(l) for l in open(d+'/results/gen_per_task.jsonl')]
A={a:{r['instance_id']:r for r in R if r['arm']==a} for a in ('srep7','pub024')}
short=lambda t:len(T[t]['problem_statement'])<150
def sign(a,b):
    n=a+b
    return round(min(1,2*sum(math.comb(n,k) for k in range(max(a,b),n+1))/2**n),3) if n else 1
for nm,F in (('all',lambda t:True),('short gradable',short),('dev16',lambda t:t in DEV),('dev16 long',lambda t:t in DEV and not short(t))):
    ts=[t for t in A['srep7'] if F(t) and t in A['pub024']]
    s,p=A['srep7'],A['pub024']
    os=sum(s[t]['resolved'] and not p[t]['resolved'] for t in ts); op=sum(p[t]['resolved'] and not s[t]['resolved'] for t in ts)
    print(f"{nm:15} n={len(ts)} srep {sum(s[t]['resolved'] for t in ts)} pub {sum(p[t]['resolved'] for t in ts)} | only srep {os} only pub {op} p {sign(os,op)} | mean s {round(st.mean(s[t]['agent_s'] for t in ts))} {round(st.mean(p[t]['agent_s'] for t in ts))} wall {round(st.mean(s[t]['wall_s'] for t in ts))} {round(st.mean(p[t]['wall_s'] for t in ts))} | nopatch {sum(not s[t]['patch_chars'] for t in ts)} {sum(not p[t]['patch_chars'] for t in ts)} | cap {sum(s[t]['end']=='time' for t in ts)} {sum(p[t]['end']=='time' for t in ts)}")
for a in A:
    print(a,collections.Counter((('fin' if r['end']=='ok' else r['end']),'patch' if r['patch_chars'] else 'empty','Y' if r['resolved'] else 'n') for r in A[a].values()).most_common())
print(f"{'task':15}{'chars':>6} srep pub")
for t in sorted(A['srep7'],key=lambda t:len(T[t]['problem_statement'])):
    f=lambda a:(lambda r:('Y' if r['resolved'] else ('e' if r['patch_chars'] else '.'))+str(round(r['agent_s'])))(A[a][t])
    print(f"{t:15}{len(T[t]['problem_statement']):>6} {f('srep7'):6}{f('pub024')}")
# reporter analysis
rep=collections.defaultdict(lambda:dict(calls=0,start=None,end=None,text=None,fix_start=None,names=collections.Counter(),bug=0,nofail=0,ref=0))
for l in open(d+'/requests/requests.jsonl'):
    r=json.loads(l); j=r.get('job') or ''
    if 'srep7' not in j or not isinstance(r.get('reply'),dict): continue
    m=r['request']['messages']; sy=str(m[0].get('content'))
    x=rep[j]
    if 'skill_name look' in sy:
        x['calls']+=1; x['start']=x['start'] or r['t']; x['end']=r['t']+r['seconds']
        ms=r['reply']['message']
        for t in ms.get('tool_calls') or []: x['names'][t['function']['name']]+=1
        if not ms.get('tool_calls') and (ms.get('content') or '').strip(): x['text']=ms['content']
        c=str(m[-1].get('content'))
        if 'BUG SHOWN' in c: x['bug']+=1
        if 'NO FAILURE' in c: x['nofail']+=1
        if 'REFUSED: report now' in c: x['ref']+=1
    elif 'skill_name work' in sy and x['fix_start'] is None: x['fix_start']=r['t']
jobs=list(rep)
G=lambda j:A['srep7'][j.split('#')[0]]
print('reporter runs',len(jobs),'with report text',sum(1 for j in jobs if rep[j]['text']),'reached fixer',sum(1 for j in jobs if rep[j]['fix_start']))
dur=[rep[j]['end']-rep[j]['start'] for j in jobs if rep[j]['end']]
print('reporter seconds median',round(st.median(dur)),'max',round(max(dur)),'calls median',st.median(rep[j]['calls'] for j in jobs),'refused report-now runs',sum(1 for j in jobs if rep[j]['ref']),'undeclared',sum(rep[j]['names'][n] for j in jobs for n in ('edit_file','submit_patch','run_command')))
sh=lambda j:(lambda t:(re.search(r'SHOWN:\s*(yes|no)',t,re.I)[1].lower() if re.search(r'SHOWN:\s*(yes|no)',t,re.I) else 'nofmt') if t else 'none')(rep[j]['text'])
c=collections.defaultdict(lambda:[0,0])
for j in jobs:
    k=(sh(j),'short' if short(j.split('#')[0]) else 'long'); c[k][1]+=1; c[k][0]+=G(j)['resolved']
    k=('bug_shown_clock' if rep[j]['bug'] else 'no_bug_clock','short' if short(j.split('#')[0]) else 'long'); c[k][1]+=1; c[k][0]+=G(j)['resolved']
for k,v in sorted(c.items()): print(k,v)
print('--- reports (short tasks)')
n=0
for j in sorted(jobs):
    t=j.split('#')[0]
    if short(t) and rep[j]['text'] and n<40:
        n+=1
        g=G(j)
        print(f"## {t} {'SOLVED' if g['resolved'] else 'fail'} shown={sh(j)} rep {round(rep[j]['end']-rep[j]['start'])}s | ISSUE: {T[t]['problem_statement'].split(chr(10))[0][:50]!r}")
        print('  ',rep[j]['text'].replace('\n',' / ')[:330])
print('=====TIME')
for nm,F in (('short',short),('long',lambda t:not short(t))):
    J=[j for j in jobs if F(j.split('#')[0])]
    D=[rep[j]['end']-rep[j]['start'] for j in J]
    print(nm,'reporter s median',round(st.median(D)),'mean',round(st.mean(D)),'over 150 s',sum(x>150 for x in D),'of',len(D))
for lo,hi in ((0,120),(120,180),(180,240),(240,999)):
    J=[j for j in jobs if lo<=rep[j]['end']-rep[j]['start']<hi]
    print(f'report took {lo}-{hi}s: runs',len(J),'solved',sum(G(j)['resolved'] for j in J),'no patch',sum(not G(j)['patch_chars'] for j in J),'cap',sum(G(j)['end']=='time' for j in J))
print('share of model time in reporter/fixer')
tt=collections.Counter(); ct=collections.Counter(); mx=[]
for l in open(d+'/requests/requests.jsonl'):
    r=json.loads(l); j=r.get('job') or ''
    if 'srep7' not in j or not isinstance(r.get('reply'),dict): continue
    sy=str(r['request']['messages'][0].get('content')); k='reporter' if 'skill_name look' in sy else 'fixer' if 'skill_name work' in sy else 'other'
    tt[k]+=r['seconds']; ct[k]+=1
    if k=='reporter': mx.append(r['reply']['usage']['completion_tokens'])
print({k:(round(v/38),ct[k]) for k,v in tt.items()},'reporter calls >=1000 tokens',sum(x>=1000 for x in mx),'time in them approx',round(sum(x for x in mx if x>=1000)/30/38),'s per run')
