"""Repro signal (kaggle/cells_repro output): per candidate patch, how the agents' own scripts behave vs no patch."""
import json, re, collections, sys

ROWS = 'data/results/2026-10-29_repro/results/repro/rows.jsonl'
POS = re.compile(r'\b(FIXED|PASS(ED)?|SUCCESS|WORKS|OK)\b|✓|correct', re.I)
NEG = re.compile(r'\b(BUG|FAIL(ED|URE)?|NOT FIXED|STILL|REPRODUCED|WRONG|ERROR|Traceback|AssertionError|MISMATCH)\b', re.I)


def norm(s):
    s = re.sub(r'0x[0-9a-f]+', '0x', s or '')
    s = re.sub(r'/tmp/\S+|/var/folders/\S+|swegemma_sandbox_\S+', 'PATH', s)
    return re.sub(r'\d+\.\d+s', 'Ts', s)


def load():
    rows = [json.loads(l) for l in open(ROWS)]
    base = {r['instance_id']: r for r in rows if r['variant'] == 'baseline'}
    return rows, base


def signal(r, b):
    """fixes / breaks / changed / marker score of a variant against the no-patch baseline."""
    out = collections.Counter()
    if not r['results'] or not b['results']:
        return out
    for x, y in zip(b['results'], r['results']):
        bx, cx = x['exit'], y['exit']
        out['fixes'] += bx != 0 and cx == 0
        out['breaks'] += bx == 0 and cx != 0
        changed = (bx, norm(x['out']), norm(x['err'])) != (cx, norm(y['out']), norm(y['err']))
        out['changed'] += changed
        if changed:
            out['pos'] += len(POS.findall(y['out'])) > len(POS.findall(x['out']))
            out['neg_gone'] += len(NEG.findall(y['out'] + y['err'])) < len(NEG.findall(x['out'] + x['err']))
    out['score'] = out['fixes'] + out['pos'] + out['neg_gone'] - out['breaks']
    return out


if __name__ == '__main__':
    rows, base = load()
    ref = {r['instance_id']: signal(r, base[r['instance_id']]) for r in rows if r['variant'] == 'reference'}
    print('reference vs no patch (calibration): mean fixes', round(sum(v['fixes'] for v in ref.values()) / len(ref), 2),
          '| changed', round(sum(v['changed'] for v in ref.values()) / len(ref), 2), '| score>0 in',
          sum(v['score'] > 0 for v in ref.values()), 'of', len(ref), 'tasks')
    C = [r for r in rows if r['variant'].startswith('cand')]
    for key in ('fixes', 'changed', 'score', 'breaks'):
        tab = collections.defaultdict(lambda: [0, 0])
        for r in C:
            s = signal(r, base[r['instance_id']])
            v = s[key]
            bucket = '0' if v == 0 else ('1' if v == 1 else '2+') if v > 0 else '<0'
            tab[bucket][0] += r['resolved']; tab[bucket][1] += 1
        print(f'{key:8}', ' | '.join(f'{k}: {a}/{n} solved ({a / n:.0%})' for k, (a, n) in sorted(tab.items())))
