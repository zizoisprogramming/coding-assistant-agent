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
req = WORKING_DIR / 'requests' / 'requests.jsonl'
print('request log:', f'{req.stat().st_size / 1e6:.0f} MB' if req.exists() else 'MISSING')
