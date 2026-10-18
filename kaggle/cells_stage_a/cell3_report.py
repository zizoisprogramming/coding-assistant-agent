# 3. STAGE A report + stage_a_trial.zip (episodes, state, trees, report, preview; not the big source index).
import json, statistics, zipfile
from pathlib import Path

OUT = Path('/kaggle/working/stage_a')
state = json.loads((OUT / 'state.json').read_text())
eps = [json.loads(l) for f in sorted(OUT.glob('episodes_*.jsonl')) for l in open(f)]
SHARD = json.loads((OUT / 'state.json').read_text()).get('shard', '0/1').replace('/', 'of')
print(f"files done {len(state['done_files'])} | runs seen {state['seen']} | episodes kept {len(eps)}")
print('per teacher:', state['counts'])
print('dropped:', state['drop_reasons'])


def dist(key):
    v = [e['stats'][key] for e in eps]
    return f'median {statistics.median(v)}, max {max(v)}' if v else '-'


for k in ('calls', 'error_rate', 'repeated_commands', 'thinking_chars', 'max_step_thinking_chars', 'env_confusion'):
    print(f'  {k:24} {dist(k)}')
print('with workspace tree:', sum(1 for e in eps if e.get('workspace_tree')), '| with issue text:',
      sum(1 for e in eps if e.get('problem_statement')), 'of', len(eps))
report = {'state': state, 'n_episodes': len(eps)}
(OUT / 'report.json').write_text(json.dumps(report, indent=1))
with open(OUT / 'preview.md', 'w') as f:  # three episodes in readable form
    for e in eps[:3]:
        f.write(f"# {e['instance_id']} ({e['teacher']}) {e['stats']}\n\n## Task\n{(e.get('problem_statement') or '')[:1500]}\n\n")
        f.write(f"## Tree\n```\n{(e.get('workspace_tree') or '')[:1500]}\n```\n")
        for i, s in enumerate(e['steps']):
            f.write(f"\n### step {i + 1}\n**thinking:** {s['thinking'][:800]}\n")
            for c in s['calls']:
                f.write(f"- `{c['tool']}` {json.dumps(c['args'])[:400]}\n  -> {str(c.get('output'))[:300]!r}\n")
z = Path(f'/kaggle/working/stage_a_{SHARD}.zip')
with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
    for p in sorted(OUT.iterdir()):
        if p.name != 'source_index.json':
            zf.write(p, p.relative_to(OUT.parent))
print(f'\n==> download {z} ({z.stat().st_size / 1e6:.1f} MB), then STOP THE SESSION')
