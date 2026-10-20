# 5. Summary (paste this output to Claude), then STOP THE SESSION.
#    Per variant: resolved overall, without the 14 env_overlay tasks, macro average per repo (great-tables holds 12),
#    how runs ended, and loop signs from the traces. Then one row per task across variants.
import collections, glob, json, statistics
from pathlib import Path

RES = Path('/kaggle/working/results')
rows = [json.loads(l) for l in open(RES / 'ood_per_task.jsonl')] if (RES / 'ood_per_task.jsonl').exists() else []
variants = list(dict.fromkeys(r['variant'] for r in rows))


def trace_stats(variant, iid):
    f = RES / variant / 'traces' / f'trace_{iid}.json'
    if not f.exists():
        return None
    calls = []
    for s in json.load(open(f)).get('steps', []):
        if s.get('source') == 'agent':
            calls += [(c.get('function_name'), json.dumps(c.get('arguments'), sort_keys=True)) for c in s.get('tool_calls') or []]
    return {'calls': len(calls), 'max_same': max(collections.Counter(calls).values(), default=0)}


summary = {}
print(f"{'variant':12} {'resolved':>9} {'no-overlay':>10} {'repo-macro':>10} {'empty':>5} {'loops':>5} {'med-agent-s':>11} ends")
for v in variants:
    rs = [r for r in rows if r['variant'] == v]
    no = [r for r in rs if not r['env_overlay']]
    by_repo = collections.defaultdict(list)
    for r in rs:
        by_repo[r['repo']].append(r['resolved'])
    macro = statistics.mean(sum(x) / len(x) for x in by_repo.values()) if by_repo else 0
    st = [trace_stats(v, r['instance_id']) for r in rs]
    loops = sum(1 for s in st if s and s['max_same'] >= 4)  # same exact call 4+ times in one run
    summary[v] = {'resolved': sum(r['resolved'] for r in rs), 'n': len(rs),
                  'resolved_no_overlay': sum(r['resolved'] for r in no), 'n_no_overlay': len(no),
                  'repo_macro': round(macro, 3), 'empty_patch': sum(r['patch_chars'] == 0 for r in rs), 'loops': loops,
                  'median_agent_s': statistics.median([r['agent_s'] for r in rs]) if rs else None,
                  'ends': dict(collections.Counter(r['end'] for r in rs))}
    s = summary[v]
    print(f"{v:12} {s['resolved']:>4}/{s['n']:<4} {s['resolved_no_overlay']:>5}/{s['n_no_overlay']:<4} "
          f"{100 * s['repo_macro']:>9.1f}% {s['empty_patch']:>5} {loops:>5} {s['median_agent_s']:>11} {s['ends']}")
(RES / 'summary.json').write_text(json.dumps(summary, indent=2))

print('\nper task (R = resolved, . = not, - = not run; calls / max repeats of one identical call):')
ids = sorted({r['instance_id'] for r in rows})
by = {(r['variant'], r['instance_id']): r for r in rows}
print(f"{'task':24} " + ' '.join(f'{v:>16}' for v in variants))
for i in ids:
    cells = []
    for v in variants:
        r, s = by.get((v, i)), trace_stats(v, i)
        cells.append('-' if r is None else ('R' if r['resolved'] else '.') + (f" {s['calls']}c/x{s['max_same']}" if s else '')
                     + f" {r['end'][:6]}")
    print(f'{i:24} ' + ' '.join(f'{c:>16}' for c in cells))
env = RES / 'ood_env_install.jsonl'
if env.exists():
    recs = [json.loads(l) for l in open(env)]
    bad = [r for r in recs if not any(a.get('exit') == 0 for a in r.get('editable') or [])]
    print(f'\nsandbox installs logged: {len(recs)}, editable install never succeeded: {len(bad)}',
          sorted({r['repo'] for r in bad}))
