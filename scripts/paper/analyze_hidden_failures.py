import glob,json,re,collections,statistics as st
T={json.loads(l)['instance_id']:json.loads(l) for l in open('data/tasks.jsonl')}
GOLD={i:[g for g in re.findall(r"^\+\+\+ b/(\S+)",t['patch'],re.M)] for i,t in T.items()}
cat=collections.Counter();task=collections.defaultdict(collections.Counter);n=0;gold=collections.Counter();byk=collections.Counter()
for tr in glob.glob('data/results/*/results/*/task_results.jsonl'):
    d=tr.split('/')[2];arm=tr.split('/')[4]
    if not re.match(r'(mix|bf|le\d?|r4|af|lo)',arm):continue
    base=tr.rsplit('/',1)[0]
    for r in map(json.loads,open(tr)):
        i=r['instance_id']
        if r['resolved'] or not r.get('agent_patch_size') or i not in T:continue
        p=f"{base}/test_outputs/{i}.log"
        try:t=open(p,errors='replace').read()
        except OSError:
            cat['no log']+=1;continue
        n+=1
        pa=f"{base}/patches/{i}.patch"
        try:files=re.findall(r"^\+\+\+ b/(\S+)",open(pa,errors='replace').read(),re.M)
        except OSError:files=[]
        src=[g for g in GOLD[i] if not re.search(r"tests?/",g)]
        ingold=any(f in src for f in files)
        allg=all(g in files for g in src) if src else False
        L=t
        if re.search(r"ImportError|ModuleNotFoundError|cannot import",L):k='name missing: import'
        elif re.search(r"AttributeError",L):k='name missing: attribute'
        elif re.search(r"TypeError[^\n]*(unexpected keyword|got an unexpected|positional argument)",L):k='signature differs'
        elif re.search(r"NameError",L):k='name missing: name'
        elif re.search(r"\bAssertionError\b|\nE +assert |assert .* ==|DeprecationWarning|DID NOT (RAISE|WARN)|Failed: DID",L):k='behaviour: assertion'
        elif re.search(r"Timeout|timed out",L,re.I):k='timeout'
        elif re.search(r"SyntaxError|IndentationError",L):k='syntax'
        elif re.search(r"TypeError|ValueError|KeyError|Exception|Error\b",L):k='behaviour: other exception'
        elif not L.strip() or 'STDOUT:\n\n' in L[:12]:k='empty output'
        else:k='other'
        cat[k]+=1;task[i][k]+=1;gold['in gold' if ingold else 'not in gold']+=1;gold['all gold' if allg else 'not all gold']+=1
        byk[k,'in gold' if ingold else 'other file']+=1
print('wrong patches with a hidden-test log:',n)
for k,v in cat.most_common():print(f"  {k:30}{v:4} {v/n:.0%}  in gold file {byk[k,'in gold']}/{v}")
print(gold)
print('tasks',len(task))
for i,c in sorted(task.items(),key=lambda kv:-sum(kv[1].values()))[:16]:print(' ',i,len(T[i]['problem_statement']),dict(c.most_common(3)))
