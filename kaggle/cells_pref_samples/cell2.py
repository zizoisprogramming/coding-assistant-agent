# 2. Episodes (every run labelled; errors counted and skipped), samples (the cut), checks, the label gallery.
for mode in ('p', 'o'):
    print(f'===== pref_episodes --mode {mode} =====', flush=True)
    run([sys.executable, CODE / 'pref_episodes.py', '--mode', mode, '--gen', *GENS, '--tasks', *TASK_FILES,
         '--exclude', CODE / 'heldout_eval.json', '--tokenizer-dir', TOK_DIR, '--copy-per-task', COPY_PER_TASK,
         '--out', OUT / f'ep_{mode}'])
    print(f'===== build_samples ({mode}) =====', flush=True)
    run([sys.executable, CODE / 'build_samples.py', '--stage-b', OUT / f'ep_{mode}', '--tokenizer-dir', TOK_DIR,
         '--out', OUT / f'samples_{mode}.pt', '--max-len', 16384, '--split-on-break'])
S = {mode: torch.load(OUT / f'samples_{mode}.pt', weights_only=False) for mode in ('p', 'o')}
key = lambda s: (s['episode_id'], s['segment'], s['label'], len(s['input_ids']), int(s['labels_mask'].sum()))
copy_p = sorted(key(s) for s in S['p'])
copy_o = sorted(key(s) for s in S['o'] if s['copy'])
assert copy_p == copy_o, 'P samples must equal O copy samples (only the labels may differ)'
assert not {s['task'] for m in S for s in S[m]} & set(HELDOUT), 'a held-out task reached the samples'
assert all(bool(s['labels_mask'][-1]) for m in S for s in S[m]), 'a sample does not end on a graded token (the cut)'
report = {}
for mode, ss in S.items():
    c = collections.Counter()
    for s in ss:
        k = ('copy' if s['copy'] else s['label']) + '_' + s['split']
        c[k + '_segments'] += 1
        c[k + '_tokens'] += len(s['input_ids'])
        c[k + '_graded'] += int(s['labels_mask'].sum())
        c[k + '_tasks'] = 0
    for k in list(c):
        if k.endswith('_tasks'):
            kind = k[:-6]
            c[k] = len({s['task'] for s in ss if ('copy' if s['copy'] else s['label']) + '_' + s['split'] == kind})
    report[mode] = dict(sorted(c.items()))
    print(f'samples_{mode}: ' + ' | '.join(f'{k} {v:,}' for k, v in sorted(c.items())), flush=True)
report['copy_samples_identical_p_o'] = True
report['copy_ids_hash'] = hashlib.md5(json.dumps(copy_p).encode()).hexdigest()
# label gallery: one real reply per reason (O) and per copy reason (P), different tasks where possible
gal, seen_tasks = {}, collections.Counter()
for line in open(OUT / 'ep_o' / 'requests_pref.jsonl'):
    r = json.loads(line)
    w = r.get('why')
    if not w or (w in gal and seen_tasks[w] >= 1):
        continue
    msg = (r.get('reply') or {}).get('message') or {}
    calls = [((c.get('function') or {}).get('name'), str((c.get('function') or {}).get('arguments'))[:300]) for c in msg.get('tool_calls') or []]
    last_tool = next((str(m.get('content'))[:400] for m in reversed(r['request']['messages']) if m.get('role') == 'tool'), '')
    gal[w] = {'episode': r['episode_id'], 'thinking': str(msg.get('reasoning_content') or '')[:500],
              'text': str(msg.get('content') or '')[:200], 'calls': calls, 'previous tool output': last_tool}
    seen_tasks[w] += 1
with open(OUT / 'gallery.md', 'w') as fh:
    for w in sorted(gal):
        g = gal[w]
        fh.write(f"## {w}\n- episode: {g['episode']}\n- previous tool output: {g['previous tool output']!r}\n"
                 f"- thinking: {g['thinking']!r}\n- text: {g['text']!r}\n- calls: {g['calls']}\n\n")
report['gallery_reasons'] = sorted(gal)
(OUT / 'report.json').write_text(json.dumps(report, indent=1))
for p in ('ep_p', 'ep_o'):
    shutil.rmtree(OUT / p)  # the episodes are rebuilt from the collector output any time; keep the output small
print('\nGALLERY reasons:', sorted(gal))
print(f"SAMPLES READY: samples_p.pt {len(S['p'])} segments, samples_o.pt {len(S['o'])} segments (copy part identical: "
      f"hash {report['copy_ids_hash'][:10]}) -> make this output a private dataset and share it with the two training accounts")
