# 5. Summary (paste this output to Claude). Writes rebench/tasks.jsonl with every built task + its gate verdict.
st_of = dict(PILOT)
rows = []
for iid, _ in PILOT:
    b, g = built.get(iid, {}), gate.get(iid, {})
    rows.append({'id': iid, 'level': st_of[iid], 'snap': bool(b.get('snapshot')), 'pins_failed': len(b.get('pins_failed', {})),
                 'built': len(b.get('pins_built', [])), 'gold': g.get('gold', '-'), 'empty': g.get('empty', '-'),
                 'usable': bool(g.get('usable')), 'why': (g.get('why') or b.get('snapshot_error') or '')[:90]})
print('funnel: pilot', len(rows), '| snapshot ok', sum(r['snap'] for r in rows),
      '| all pins installed', sum(r['snap'] and r['pins_failed'] == 0 for r in rows),
      '| gold PASS', sum(r['gold'] == 'PASS' for r in rows), '| usable (gold PASS + empty FAIL)', sum(r['usable'] for r in rows))
for s in sorted({r['level'] for r in rows}):
    sub = [r for r in rows if r['level'] == s]
    print(f"  {s}: {len(sub):2} tasks, usable {sum(r['usable'] for r in sub)}")
print('\nnot usable, by first reason:')
reasons = collections.Counter()
for r in rows:
    if not r['usable']:
        w = r['why'].lower()
        reasons['snapshot' if not r['snap'] else 'missing module' if 'no module' in w else
                'sandbox env' if 'sandboxenv' in w or 'importable' in w else 'empty patch passes' if r['gold'] == 'PASS'
                else 'tests fail with gold' if r['gold'] == 'FAIL' else 'harness error'] += 1
print(dict(reasons))
print(f"\n{'task':46} {'level':12} {'built':>5} {'pfail':>5} {'gold':5} {'empty':7} why")
for r in rows:
    print(f"{r['id'][:46]:46} {r['level']:12} {r['built']:5} {r['pins_failed']:5} {r['gold']:5} {r['empty']:7} {r['why']}")
gates = [g.get('gold_s', 0) + g.get('empty_s', 0) for g in gate.values()]
print(f"\ngate per task: median {sorted(gates)[len(gates) // 2] if gates else '-'} s (build time: see the end of cell 3)")
with open(OUT / 'tasks.jsonl', 'w') as fh:
    for iid, _ in PILOT:
        r, g = ROWS[iid], gate.get(iid, {})
        if not built.get(iid, {}).get('snapshot'):
            continue
        fh.write(json.dumps({**{k: r[k] for k in ('instance_id', 'repo', 'base_commit', 'problem_statement', 'patch',
                                                  'test_patch', 'FAIL_TO_PASS', 'PASS_TO_PASS', 'created_at')},
                             'hints_text': '', 'license': r['license_name'], 'source': 'nebius/SWE-rebench (CC-BY-4.0)',
                             'python_original': r['install_config']['python'], 'gate': g}) + '\n')
print('wrote', OUT / 'tasks.jsonl')
