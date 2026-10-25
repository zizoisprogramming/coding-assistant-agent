# 5. TEST SUMMARY (paste this output to Claude): per arm, per task, where runs end.
rows = [json.loads(l) for l in open(PER_TASK)] if PER_TASK.exists() else []
by = collections.defaultdict(list)
for r in rows:
    by[(r['arm'], r['instance_id'])].append(r['resolved'])
print(f'{len(rows)} runs | {(time.time() - T_START) / 3600:.1f} h')
GROUPS = {'test (24, unseen repos)': {i for i, r in ROWS.items() if r.get('split') == 'test'},
          'dev16 (public, never trained)': {i for i, r in ROWS.items() if r.get('split') == 'dev16'}}
for gname, gids in GROUPS.items():
    print(f'== {gname}')
    for arm in ARMS:
        rs = [r for r in rows if r['arm'] == arm and r['instance_id'] in gids]
        tasks = {i for (a, i) in by if a == arm and i in gids}
        print(f"  {arm:9} runs {sum(r['resolved'] for r in rs):2}/{len(rs):2} | tasks solved at least once "
              f"{sum(any(by[(arm, i)]) for i in tasks):2}/{len(tasks)} | per run {sum(r['resolved'] for r in rs) / max(len(rs), 1) * len(gids):.1f}/{len(gids)} "
              f"| ends {dict(Counter(r['end'] for r in rs))} | median tools {sorted(r['tool_calls'] or 0 for r in rs)[len(rs) // 2] if rs else '-'}")
print('\nper task (runs solved / runs):', ' | '.join(ARMS))
for iid in sorted(ROWS, key=lambda i: (ROWS[i].get('split'), i)):
    cells = [f"{sum(by[(a, iid)])}/{len(by[(a, iid)])}" if by[(a, iid)] else '-' for a in ARMS]
    print(f'  {iid[:45]:45} ' + '   '.join(f'{c:>5}' for c in cells))
arms = list(ARMS)
for other in arms[1:]:  # paired: per task, solve share of the adapter arm vs the base arm
    win = sum(1 for i in ROWS if by[(other, i)] and by[(arms[0], i)] and
              sum(by[(other, i)]) / len(by[(other, i)]) > sum(by[(arms[0], i)]) / len(by[(arms[0], i)]))
    lose = sum(1 for i in ROWS if by[(other, i)] and by[(arms[0], i)] and
               sum(by[(other, i)]) / len(by[(other, i)]) < sum(by[(arms[0], i)]) / len(by[(arms[0], i)]))
    print(f'{other} vs {arms[0]}: better on {win} tasks, worse on {lose}, equal on the rest')
req = WORKING_DIR / 'requests' / 'requests.jsonl'
print('request log:', f'{req.stat().st_size / 1e6:.0f} MB' if req.exists() else 'MISSING')
