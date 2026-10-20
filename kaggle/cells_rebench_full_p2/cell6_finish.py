# 6. FINISH: summary (paste this output to Claude), tasks.jsonl with the usable tasks and all labels, and pruning:
#    snapshots of unusable tasks and wheels no usable task needs are deleted (the output becomes the dataset).
rows = []
for iid, lv in TASKS:
    b, g = built.get(iid, {}), gate.get(iid, {})
    rows.append({'id': iid, 'level': lv, 'domain': ROWS[iid].get('domain'), 'snap': bool(b.get('snapshot')),
                 'gated': iid in gate, 'gold': g.get('gold', '-'), 'runs': '/'.join(g.get('gold_runs', [])),
                 'empty': g.get('empty', '-'), 'usable': bool(g.get('usable')), 'flaky': bool(g.get('flaky')),
                 'env_partial': bool(g.get('env_partial')),
                 'why': (g.get('why') or b.get('snapshot_error') or '')[:90]})
print(f"part {PART} | selected {len(rows)} | snapshot ok {sum(r['snap'] for r in rows)} | gated {sum(r['gated'] for r in rows)} "
      f"| usable {sum(r['usable'] for r in rows)} (env_partial {sum(r['usable'] and r['env_partial'] for r in rows)}) "
      f"| flaky dropped {sum(r['flaky'] for r in rows)}")
for key in ('level', 'domain'):
    print(f'usable by {key}:')
    for v in sorted({r[key] or '-' for r in rows}):
        sub = [r for r in rows if (r[key] or '-') == v]
        print(f"  {v:14} {sum(r['usable'] for r in sub):3}/{len(sub):3} usable")
U = [r for r in rows if r['usable']]
print(f"usable public-like domain share: {100 * sum(r['domain'] != 'other' for r in U) / max(len(U), 1):.0f}% (target 80%)")
reasons = collections.Counter()
for r in rows:
    if not r['usable']:
        w = r['why'].lower()
        reasons['snapshot: ' + r['why'][:40] if not r['snap'] else 'not gated (deadline)' if not r['gated'] else
                'flaky gold' if r['flaky'] else 'missing module' if 'no module' in w else
                'sandbox env' if 'sandboxenv' in w or 'importable' in w else 'empty patch passes' if r['empty'] == 'PASS'
                else 'tests fail with gold' if r['gold'] == 'FAIL' else 'harness error'] += 1
print('not usable, by first reason:', dict(reasons.most_common()))

with open(OUT / 'tasks.jsonl', 'w') as fh:
    for iid, lv in TASKS:
        g = gate.get(iid, {})
        if not g.get('usable'):
            continue
        r = ROWS[iid]
        fh.write(json.dumps({**{k: r[k] for k in ('instance_id', 'repo', 'base_commit', 'problem_statement', 'patch',
                                                  'test_patch', 'FAIL_TO_PASS', 'PASS_TO_PASS', 'created_at')},
                             'hints_text': '', 'license': r['license_name'], 'source': 'nebius/SWE-rebench (CC-BY-4.0)',
                             'python_original': r['install_config']['python'], 'level': lv, 'domain': r.get('domain'),
                             'topics': r.get('topics'), 'difficulty': r['meta']['llm_score']['difficulty_score'],
                             'pr': r.get('pr'), 'leak': LEAK.get(iid), 'env_partial': g.get('env_partial'),
                             'gate': g}) + '\n')
with open(OUT / 'gated_all.jsonl', 'w') as fh:  # every selected task's verdict (for the funnel; no texts)
    for r in rows:
        fh.write(json.dumps(r) + '\n')

# Prune: the dataset keeps only what the usable tasks need.
keep = {i for i, _ in TASKS if gate.get(i, {}).get('usable')}
for p in (OUT / 'snapshots').glob('*.tgz'):
    if p.stem not in keep:
        p.unlink()
manifest = {i: built[i]['wheels'] for i in sorted(keep)}
(OUT / 'wheels' / WHEEL_SET / 'manifest.json').write_text(json.dumps(manifest, indent=1))
need = {w for ws in manifest.values() for w in ws}
dropped = [p for p in HOUSE.glob('*.whl') if p.name not in need]
for p in dropped:
    p.unlink()
shutil.rmtree('/tmp/rb_gate_results', ignore_errors=True)
snap_gb = sum(p.stat().st_size for p in (OUT / 'snapshots').glob('*.tgz')) / 1e9
house_gb = sum(p.stat().st_size for p in HOUSE.glob('*.whl')) / 1e9
print(f"wrote {OUT / 'tasks.jsonl'}: {len(keep)} usable tasks | snapshots {snap_gb:.2f} GB | wheel house "
      f"{len(list(HOUSE.glob('*.whl')))} wheels {house_gb:.2f} GB ({len(dropped)} unused wheels deleted) | "
      f"session {(time.time() - T_START) / 3600:.1f} h")
