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

methods = ['first', 'smallest', 'largest', 'agree_small', 'agree_large']
for k in (2, 3):
    tot = collections.Counter(); per = collections.defaultdict(collections.Counter)
    for t, rs in runs.items():
        combos = list(itertools.combinations(rs, k))
        exp = lambda f: sum(f(c) for c in combos) / len(combos)
        per[t]['pass@1'] = sum(r['ok'] for r in rs) / len(rs)
        per[t][f'oracle'] = exp(lambda c: any(x['ok'] for x in c))
        for m in methods:
            # 'first' over combos in all orders = random pick among non-empty
            if m == 'first':
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
