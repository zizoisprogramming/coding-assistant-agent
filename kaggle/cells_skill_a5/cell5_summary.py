# 5. SKILL ARMS SUMMARY (paste this output to Claude): per pass, per arm vs mix's 64 dev16 runs, per task.
rows = [json.loads(l) for l in open(PER_TASK)] if PER_TASK.exists() else []
mix_solved = sum(s / n for s, _, n in MIX_REF.values())
mix_nopatch = sum(p / n for _, p, n in MIX_REF.values())
print(f'{len(rows)} runs | {(time.time() - T_START) / 3600:.1f} h | mix reference per 16-task pass: solved {mix_solved:.2f}, '
      f'no patch {mix_nopatch:.2f}')
for n in range(1, ATTEMPTS + 1):
    rs = [r for r in rows if r['attempt'].endswith(f'.{n}')]
    if not rs:
        continue
    print(f'\n== PASS {n}: {len(rs)} runs')
    for arm in ARMS:
        a = [r for r in rs if r['arm'] == arm]
        print(f"  {arm:8} solved {sum(r['resolved'] for r in a):2}/{len(a):2} (mix {mix_solved:.1f}) | no patch "
              f"{sum(not r['patch_chars'] for r in a):2} (mix {mix_nopatch:.1f}) | ends {dict(Counter(r['end'] for r in a))} "
              f"| median tools {sorted(r['tool_calls'] or 0 for r in a)[len(a) // 2] if a else '-'}")
print('\nper task: mix solved/runs (no patch) | ' + ' | '.join(ARMS) + '   (S = solved, E = edited, 0 = no patch)')
for iid in sorted(ROWS):
    s, p, n = MIX_REF.get(iid, [0, 0, 0])
    cells = []
    for arm in ARMS:
        a = sorted((r for r in rows if r['arm'] == arm and r['instance_id'] == iid), key=lambda r: r['attempt'])
        cells.append(''.join('S' if r['resolved'] else ('E' if r['patch_chars'] else '0') for r in a) or '-')
    print(f'  {iid:16} mix {s}/{n} ({p})   ' + '   '.join(f'{c:>4}' for c in cells))
dig = [json.loads(l) for l in open(RESULTS / 'digest.jsonl')] if (RESULTS / 'digest.jsonl').exists() else []
print('\nper arm, mean per run (from the model replies; see the DIGEST lines):')
for arm in ARMS:
    d = [x for x in dig if x['arm'] == arm]
    if d:
        m = lambda k: sum(x.get(k) or 0 for x in d) / len(d)
        fe = sorted(x['first_edit'] for x in d if x.get('first_edit'))
        print(f"  {arm:8} runs {len(d)} | a.py find {m('find'):.1f} outline {m('outline'):.1f} show {m('show'):.1f} "
              f"| replace {m('replace'):.1f} run {m('run'):.1f} failed edits {m('edit_fail'):.1f} "
              f"| plan {m('plan'):.1f} blocked {m('blocked'):.1f} debug flags {m('debug_flag'):.1f} "
              f"| raw reads {m('raw_read') + m('read_file'):.1f} | scripts/tests before edit {m('pre_edit_runs'):.1f} | reshown {m('reshown'):.1f} | banner runs "
              f"{sum(1 for x in d if x.get('banner') or x.get('stop_banner'))} | call 1 wrong "
              f"{sum(1 for x in d if x.get('call1_wrong'))} | pip {m('pip'):.1f} | repro {m('repro'):.1f} pytest {m('pytest'):.1f} | edited {len(fe)}/{len(d)}, median "
              f"first edit at call {fe[len(fe) // 2] if fe else '-'} | compactions {m('compactions'):.1f} | model "
              f"{m('model_s'):.0f}s + tools {m('tool_s'):.0f}s")
req = WORKING_DIR / 'requests' / 'requests.jsonl'
print('request log:', f'{req.stat().st_size / 1e6:.0f} MB' if req.exists() else 'MISSING')
