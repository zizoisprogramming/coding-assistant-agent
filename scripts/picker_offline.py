"""Offline picker check: for each d40 task, all runs' patches + resolved; simulate picking 1 of k candidates."""
import json, itertools, re, collections, statistics as st, sys
R = 'data/results/'
SRC = [('2026-10-29_skill_d40', 'sk_a2'), ('2026-10-29_skill_d40_32', 'sk_a2_32'), ('2026-10-29_skill_s20_fr', 'sk_fr'),
       ('2026-10-29_skill_s20_fr2_pub', 'sk_fr2'), ('2026-10-29_skill_s20_fr2_pub', 'pub024'),
       ('2026-10-29_skill_u20', 'sk_a2_32'), ('2026-10-29_skill_u20', 'sk_fr2'), ('2026-10-29_skill_u20', 'pub024')]
TEST_RE = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|conftest\.py$")
runs = collections.defaultdict(list)
for d, arm in SRC:
    res = {r['instance_id']: r for r in map(json.loads, open(R + d + '/results/gen_per_task.jsonl')) if r['arm'] == arm}
    for t, r in res.items():
        try:
            p = open(f'{R}{d}/results/gen/patches/{t}__a{arm}.1.diff').read()
        except FileNotFoundError:
            p = ''
        runs[t].append({'ok': bool(r['resolved']), 'patch': p, 'src': f'{d}:{arm}'})

def files(p):
    return re.findall(r'^\+\+\+ b/(\S+)', p, re.M)

def lines(p, src_only=True):
    out, f = set(), None
    for l in p.splitlines():
        if l.startswith('+++ '):
            f = l[6:] if l.startswith('+++ b/') else None
        elif f and l[:1] in '+-' and not l.startswith(('+++', '---')):
            if src_only and TEST_RE.search(f):
                continue
            s = re.sub(r'\s+', '', l[1:])
            if s:
                out.add((f, l[0], s))
    return out

def sim(a, b):
    A, B = lines(a), lines(b)
    return len(A & B) / len(A | B) if A | B else 0.0

def size(p): return len(lines(p))

def pick(cands, how):
    ne = [c for c in cands if lines(c['patch'])]
    if not ne:
        return cands[0]
    if how.startswith('tests_'):  # drop candidates that break existing tests (unless all do), then pick
        keep = [c for c in ne if not c['breaks']] or ne
        return pick(keep, 'agree_small' if how == 'tests_agree' else 'first_list')
    if how == 'first_list':
        return ne[0]
    if how == 'repro':  # drop test-breakers, then the highest repro score; ties: the first (random order)
        keep = [c for c in ne if not c['breaks']] or ne
        best = max(c['score'] for c in keep)
        return [c for c in keep if c['score'] == best][0]
    if how == 'first':
        return ne[0]
    if how == 'smallest':
        return min(ne, key=lambda c: size(c['patch']))
    if how == 'largest':
        return max(ne, key=lambda c: size(c['patch']))
    if how.startswith('agree'):
        tb = how.split('_')[1]
        score = lambda c: sum(sim(c['patch'], o['patch']) for o in ne if o is not c)
        key = (lambda c: (score(c), -size(c['patch']))) if tb == 'small' else (lambda c: (score(c), size(c['patch'])))
        return max(ne, key=key)

# existing-test signal (kaggle/cells_testsignal, 2026-10-29): a candidate "breaks" when it fails more existing tests
# of the changed modules than no patch does
TS = 'data/results/2026-10-29_testsignal/results/testsignal/rows.jsonl'
BREAKS = {}
try:
    _rows = [json.loads(l) for l in open(TS)]
    _base = {r['instance_id']: r for r in _rows if r['kind'] == 'baseline'}
    for r in _rows:
        if r['kind'] == 'candidate' and r['instance_id'] in _base and r['error'] != 'empty patch':
            b = _base[r['instance_id']]
            BREAKS[(r['instance_id'], r['src'])] = ((r['failed'] + r['errors']) > (b['failed'] + b['errors'])
                                                   or r['passed'] + r['failed'] + r['errors'] == 0)
except FileNotFoundError:
    pass
# repro signal (kaggle/cells_repro): the agents' own scripts vs no patch (scripts/repro_signal.py)
SCORE = {}
try:
    sys.path.insert(0, 'scripts')
    import repro_signal as RS
    _rows, _base = RS.load()
    for r in _rows:
        if r['variant'].startswith('cand') and r['instance_id'] in _base:
            SCORE[(r['instance_id'], r['src'])] = RS.signal(r, _base[r['instance_id']])['score']
except FileNotFoundError:
    pass
for t, rs in runs.items():
    for r in rs:
        r['score'] = SCORE.get((t, r['src']), 0)
        r['breaks'] = BREAKS.get((t, r['src']), False)
        r['t'] = t

methods = ['first', 'smallest', 'largest', 'agree_small', 'agree_large', 'tests_first', 'tests_agree', 'repro']
for k in (2, 3, 4, 5):
    tot = collections.Counter(); per = collections.defaultdict(collections.Counter)
    for t, rs in runs.items():
        combos = list(itertools.combinations(rs, k))
        exp = lambda f: sum(f(c) for c in combos) / len(combos)
        per[t]['pass@1'] = sum(r['ok'] for r in rs) / len(rs)
        per[t][f'oracle'] = exp(lambda c: any(x['ok'] for x in c))
        for m in methods:
            # 'first' over combos in all orders = random pick among non-empty
            if m == 'tests_first':  # random among the non-breaking non-empty ones (all orders)
                def tf(c):
                    ne = [x for x in c if lines(x['patch'])]
                    keep = [x for x in ne if not x['breaks']] or ne
                    return sum(x['ok'] for x in keep) / len(keep) if keep else 0
                per[t][m] = sum(tf(c) for c in combos) / len(combos)
            elif m == 'repro':  # ties broken at random: average over the tied candidates
                def rp(c):
                    ne = [x for x in c if lines(x['patch'])]
                    if not ne:
                        return 0
                    keep = [x for x in ne if not x['breaks']] or ne
                    best = max(x['score'] for x in keep)
                    top = [x for x in keep if x['score'] == best]
                    return sum(x['ok'] for x in top) / len(top)
                per[t][m] = sum(rp(c) for c in combos) / len(combos)
            elif m == 'first':
                per[t][m] = sum(sum(x['ok'] for x in c if lines(x['patch'])) / max(1, sum(1 for x in c if lines(x['patch']))) if any(lines(x['patch']) for x in c) else 0 for c in combos) / len(combos)
            else:
                per[t][m] = exp(lambda c: pick(list(c), m)['ok'])
        for m, v in per[t].items():
            tot[m] += v
    print(f'k={k} over {len(runs)} tasks, {st.mean(len(v) for v in runs.values()):.1f} runs/task:', {m: round(v, 2) for m, v in tot.items()})
    if k == 3:
        print('  sometimes-tasks:')
        for t in sorted(runs):
            if 0 < per[t]['pass@1'] < 1:
                print('   ', t, {m: round(v, 2) for m, v in per[t].items()})
