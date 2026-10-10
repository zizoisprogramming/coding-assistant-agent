import json, glob, re, os, collections
# markers that the agent has SEEN the code where the gold fix goes (from tool outputs), and edited it
SEEN = {'fastapi_15589': r'processed_keys', 'rich_3470': r'_record_buffer\.extend'}
EDIT_OK = {'fastapi_15589': r'processed_keys|received_params', 'rich_3470': r'self\.record'}
rows = []
for tr in glob.glob('data/results/**/trace_*.json', recursive=True):
    tid = tr.split('trace_')[1][:-5]
    if tid not in SEEN or '/1b' in tr or 'sample' in tr or '/results/1a' not in tr and '/1a' not in tr: continue
    d = os.path.dirname(os.path.dirname(tr)); resf = os.path.join(d, 'task_results.jsonl')
    if not os.path.exists(resf): continue
    ok = any(json.loads(l)['instance_id'] == tid and json.loads(l)['resolved'] for l in open(resf))
    steps = json.load(open(tr))['steps']; t0 = next(s['extra']['timestamp'] for s in steps if (s.get('extra') or {}).get('timestamp'))
    seen = fe = fe_ok = None; scripts_before = 0; reads_before_seen = 0; calls = 0
    for s in steps:
        t = (s.get('extra') or {}).get('timestamp')
        for tc in s.get('tool_calls') or []:
            calls += 1
            a = tc.get('arguments') if isinstance(tc.get('arguments'), dict) else {}
            cmd = a.get('command') or ''
            obs = json.dumps(s.get('observation') or {})
            is_edit = tc.get('function_name') == 'edit_file' or "open(p, 'w')" in cmd
            if seen is None and re.search(SEEN[tid], obs) and t: seen = (round(t - t0), calls)
            if seen is None: reads_before_seen += 1
            if is_edit and t:
                fe = fe or round(t - t0)
                if fe_ok is None and re.search(EDIT_OK[tid], json.dumps(a)): fe_ok = round(t - t0)
            if fe is None and re.match(r'cat >+ /tmp/', cmd): scripts_before += 1
    when = d.split('data/results/')[1].split('/')[0]
    rows.append((tid, ok, when, d.split('/')[-1], seen, fe, fe_ok, scripts_before, calls))
for tid in SEEN:
    print('=' * 12, tid)
    for r in sorted([r for r in rows if r[0] == tid], key=lambda r: (not r[1], r[2])):
        print(f"{'OK' if r[1] else '--'} {r[2][:16]:16} {r[3]:12} saw-target {str(r[4]):12} first-edit {str(r[5]):5} edit-at-target {str(r[6]):5} scripts-before-edit {r[7]:2} calls {r[8]}")
