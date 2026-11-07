import json,glob,re,collections,statistics as st,random
R=[json.loads(l) for l in open('data/analysis/run_table.jsonl')]
GR=[('bf',['bf']),('mix',['mix','mix_r1','mix_r2']),('pub',['pub024']),('skA2',['sk_a2','sk_a2_32']),('sq1',['sq1','sq2']),('clock8',['sq1c','sq1c2','sq1c3','sq1c4','sq1c2a8','sq1c2a8ra','sq1c2a8rc']),('t7',['sq1c2t7']),('clock6',['sq1c2t6','sq1c2f6','sq1c2f6ra','sq1c2f6rc','sq1c2a6','sq1c2a6c','sq1c2a6rc','sq1c2a6rn','sq1c2a6rnt','sq1c2a6i'])]
print('== did the edit land? share of runs')
for lab,arms in GR:
    x=[r for r in R if r['arm'] in arms];n=len(x)
    att=[r for r in x if r['first_attempt'] is not None or r['n_edits']]
    land=[r for r in x if r['n_edits']]
    nl=[r for r in x if r['first_attempt'] is not None and not r['n_edits']]
    f=lambda k:sum(r['kinds'].get(k,0)>0 for r in nl)
    only=lambda k:sum(r['kinds'].get(k,0)>0 and all(not r['kinds'].get(o,0) for o in ('em_malformed','em_budget','em_mismatch') if o!=k) for r in nl)
    mal=[r for r in land if r['kinds'].get('em_malformed',0)]
    lost=[r['first_edit']-r['first_attempt'] for r in land if r['first_attempt'] is not None and r['first_edit']>r['first_attempt']]
    print(f"{lab:7} runs {n:4} never tried {n-len(att):4} ({(n-len(att))/n:.0%}) | tried, never landed {len(nl):3} ({len(nl)/n:.0%}): malformed-only {only('em_malformed')}, budget-only {only('em_budget')}, mismatch-only {only('em_mismatch')}, mixed {len(nl)-only('em_malformed')-only('em_budget')-only('em_mismatch')} | landed {len(land)} ({len(land)/n:.0%}), of those first try failed {len(lost)} (delay mean {st.mean(lost) if lost else 0:.0f} s) | runs with any malformed {sum(r['kinds'].get('em_malformed',0)>0 for r in x)/n:.0%}, malformed calls/run {sum(r['kinds'].get('em_malformed',0) for r in x)/n:.2f}")
print('\n== never-landed runs: when they tried, and the budget')
for lab,arms in GR[:4]:
    nl=[r for r in R if r['arm'] in arms and r['first_attempt'] is not None and not r['n_edits']]
    if nl: print(f"{lab:7} first attempt at call median {st.median(r['first_attempt_call'] for r in nl):.0f}, s median {st.median(r['first_attempt'] for r in nl):.0f}; attempted at call>=27: {sum(r['first_attempt_call']>=27 for r in nl)}/{len(nl)}; attempts per run {st.mean(sum(r['kinds'].get(k,0) for k in ('em_malformed','em_budget','em_mismatch')) for r in nl):.1f}")
print('\n== what would landing be worth? same task: landed-edit runs solve rate; runs that tried and did not land')
d=collections.defaultdict(lambda:[0,0,0])
X=[r for r in R if r['arm'] in sum((a for _,a in GR[:4]),[])]
for r in X:
    c=d[r['iid']]
    if r['n_edits']: c[0]+=r['resolved'];c[1]+=1
    elif r['first_attempt'] is not None: c[2]+=1
tot=sum(c[2] for c in d.values());val=sum(c[2]*(c[0]/c[1]) for c in d.values() if c[1]);noland=sum(c[2] for c in d.values() if not c[1])
print(f"never-landed runs {tot} in bf/mix/pub/skA2 ({tot/len(X):.0%} of {len(X)}); expected extra solves if they landed at their task's rate: {val:.1f} ({val/len(X)*100:.1f} pts); of which {noland} on tasks with no landed run")
print('\n== after a malformed edit: what next?')
# raw shape analysis
fs=sorted(glob.glob('data/results/*/requests/requests.jsonl'))
feat=collections.defaultdict(lambda:[0,0]);order=collections.Counter();run_next=collections.Counter();lens={'ok':[],'malformed':[]}
swallowed=0;mal=0
for f in fs:
    if 'e4b' in f: continue
    seq=collections.defaultdict(list)
    for line in open(f):
        r=json.loads(line)
        if not isinstance(r.get('reply'),dict):continue
        ms=r['request']['messages']
        if not ms or ms[-1].get('role')!='tool':continue
        c=None
        for m in reversed(ms):
            for k in m.get('tool_calls') or []:
                if k.get('id')==ms[-1].get('tool_call_id'):c=k;break
            if c:break
        if not c:continue
        name=c['function']['name'];t=str(ms[-1].get('content'))
        seq[r.get('job')].append((r['t'],name,'mal' if name=='edit_file' and 'mandatory' in t else 'ok' if name=='edit_file' and 'error_type' not in t else 'other'))
        if name!='edit_file':continue
        try:a=json.loads(c['function']['arguments'])
        except Exception:a={}
        ns=str(a.get('new_string',''))
        if 'BudgetExceeded' in t or 'FileEditError' in t:continue
        k='malformed' if 'mandatory' in t else 'ok'
        if k=='malformed':
            mal+=1
            if 'old_string' in ns: swallowed+=1
        ns0=ns.split('old_string')[0] if k=='malformed' else ns
        lens[k].append(len(ns0))
        for lab,val in (('has double quote','"' in ns0),('has triple quote','"""' in ns0),('has single quote',"'" in ns0),('has backslash','\\' in ns0),('has {','{' in ns0),('has colon',':' in ns0),('multi-line','\n' in ns0),('ends with quote',ns0.rstrip().endswith(('"',"'"))),('len>200',len(ns0)>200),('len>600',len(ns0)>600)):
            for v in (val,):
                feat[lab][0 if v else 1]+=0
            feat[lab+('|yes' if val else '|no')][0 if k=='malformed' else 1]+=1
    for j,s in seq.items():
        s.sort()
        for i,(t,n,st_) in enumerate(s):
            if st_=='mal':
                nx=[x for x in s[i+1:]]
                if not nx: run_next['run ended']+=1;continue
                x=nx[0]
                run_next['next: edit_file ok' if x[2]=='ok' else 'next: malformed again' if x[2]=='mal' else 'next: edit_file other error' if x[1]=='edit_file' else 'next: '+x[1]]+=1
print('malformed',mal,'new_string swallowed the text old_string:',swallowed)
print(run_next.most_common(9))
print('median new_string length ok',st.median(lens['ok']),'malformed',st.median(lens['malformed']))
for lab in ('has double quote','has triple quote','has single quote','has backslash','has {','has colon','multi-line','ends with quote','len>200','len>600'):
    y=feat[lab+'|yes'];z=feat[lab+'|no']
    print(f"  {lab:18} malformed rate with {y[0]/max(1,y[0]+y[1]):.0%} (n={y[0]+y[1]}) without {z[0]/max(1,z[0]+z[1]):.0%} (n={z[0]+z[1]})")
print('\n== call-limit what-if: stop at the Nth budget call; solve lost if last edit later or no edit by then')
ARMS=[('pub 8m',['pub024']),('a8 family',['sq1c2a8','sq1c2a8ra','sq1c2a8rc']),('sq1c2',['sq1c2']),('t7',['sq1c2t7'])]
for lab,arms in ARMS:
    x=[r for r in R if r['arm'] in arms]
    for N in (24,28,32,36,40,80):
        tt=[];lost=0
        for r in x:
            ct=r['call_times'];t=ct[N-1] if len(ct)>=N else None
            if t is None: tt.append(r['agent_s']);continue
            tt.append(min(r['agent_s'],t))
            if r['resolved'] and (r['last_edit'] is None or r['last_edit']>t): lost+=1
        print(f"  {lab:10} N={N:2}: solves {sum(r['resolved'] for r in x)-lost}/{len(x)} mean agent s {st.mean(tt):.0f}")
print('\n== same-run pub vs others')
fo=collections.defaultdict(set)
for r in R: fo[r['folder']].add(r['arm'])
for folder,arms in sorted(fo.items()):
    if 'pub024' in arms and len(arms)>1:
        for a in sorted(arms-{'pub024'}):
            P={};Q={}
            for r in R:
                if r['folder']==folder:
                    (P if r['arm']=='pub024' else Q if r['arm']==a else {}).setdefault(r['iid'],[]).append(r)
            c=set(P)&set(Q)
            if not c: continue
            f=lambda D,g:st.mean(st.mean(g(x) for x in D[t]) for t in c)
            print(f"  {folder[11:]:16} {a:12} tasks {len(c):2}: pub {f(P,lambda r:r['resolved']):.0%} {f(P,lambda r:r['agent_s']):.0f}s nopatch {f(P,lambda r:not r['patch']):.0%} | arm {f(Q,lambda r:r['resolved']):.0%} {f(Q,lambda r:r['agent_s']):.0f}s nopatch {f(Q,lambda r:not r['patch']):.0%}")
