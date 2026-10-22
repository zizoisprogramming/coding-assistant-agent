# 5. SUMMARY (paste this output to Claude): this session + all sessions so far, throughput, where runs end.
ALL = PREV + [r for r in DONE if r not in PREV]
print('this session:', MODE, '| phases', json.dumps(PHASE_STATS))
if MODE == 'trial' and len(PHASE_STATS) == 2:
    a, b = PHASE_STATS
    print(f"throughput: concurrency {a['concurrency']} -> {a['attempts_per_hour']}/h (agent {a['mean_agent_s']}s), "
          f"concurrency {b['concurrency']} -> {b['attempts_per_hour']}/h (agent {b['mean_agent_s']}s); "
          f"full pass of {len(ROWS)} tasks at the better one: {len(ROWS) / max(a['attempts_per_hour'], b['attempts_per_hour']):.1f} h")
by_task = collections.defaultdict(list)
for r in ALL:
    by_task[r['instance_id']].append(r)
print(f"all sessions: {len(ALL)} attempts on {len(by_task)}/{len(ROWS)} tasks | tasks with a resolved run: "
      f"{sum(any(x['resolved'] for x in v) for v in by_task.values())} | resolved attempts {sum(r['resolved'] for r in ALL)}")
for key in ('attempt', 'level', 'domain', 'text_kind', 'leak', 'unfair', 'env_partial'):
    c = collections.defaultdict(lambda: [0, 0])
    for r in ALL:
        c[r[key]][0] += r['resolved']
        c[r[key]][1] += 1
    print(f'  by {key:11}', {k: f'{v[0]}/{v[1]}' for k, v in sorted(c.items(), key=lambda kv: str(kv[0]))})
print('  ends', dict(Counter(r['end'] for r in ALL)))
med = lambda xs: sorted(xs)[len(xs) // 2] if xs else None  # noqa: E731
print(f"  median agent_s {med([r['agent_s'] for r in ALL])} | median tool calls {med([r['tool_calls'] or 0 for r in ALL])} "
      f"| median llm calls {med([r['llm_calls'] or 0 for r in ALL])} | submitted {sum(r['submitted'] for r in ALL)}/{len(ALL)}")
req = WORKING_DIR / 'requests' / 'requests.jsonl'
print('request log:', f'{req.stat().st_size / 1e6:.0f} MB, {sum(1 for _ in open(req))} calls' if req.exists() else 'MISSING')
