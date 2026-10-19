# 5. Report + small files for checking (download only these: stage_b_report.json, status.jsonl, sample_requests.jsonl);
#    the full request logs stay here as the training notebook's input.
import collections, shutil

rows = [json.loads(l) for l in (OUT / 'status.jsonl').read_text().splitlines() if l.strip()]
ok = [r for r in rows if r['status'] == 'ok']
report = {
    'episodes_ok': len(ok), 'episodes_bad': len(rows) - len(ok),
    'ok_by_split_category': collections.Counter(f"{r['split']}/{r['category']}" for r in ok),
    'ok_by_teacher': collections.Counter(r['teacher'] for r in ok),
    'compactions': sum(r['summaries'] for r in ok),
    'episodes_with_compaction': sum(1 for r in ok if r['summaries']),
    'runs': [json.loads(p.read_text()) for p in sorted(OUT.glob('run_*.json'))],
    'request_log_mb': round(sum(p.stat().st_size for p in OUT.glob('requests_*.jsonl')) / 1e6, 1),
}
(WORKING_DIR / 'stage_b_report.json').write_text(json.dumps(report, indent=1))
shutil.copy(OUT / 'status.jsonl', WORKING_DIR / 'status.jsonl')
# 3 complete episodes (one with a compaction) for me to inspect
pick = [r for r in ok if r['summaries']][:1] + [r for r in ok if not r['summaries']][:2]
keys = {(r['id'], r['attempt']) for r in pick}
with open(WORKING_DIR / 'sample_requests.jsonl', 'w') as f:
    for p in OUT.glob('requests_*.jsonl'):
        for l in p.open():
            r = json.loads(l)
            if (r.get('episode_id'), r.get('attempt')) in keys:
                f.write(l)
print(json.dumps({k: v for k, v in report.items() if k != 'runs'}, indent=1))
server_instance.stop()
