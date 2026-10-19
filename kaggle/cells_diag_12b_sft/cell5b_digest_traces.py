# 5b. Digest from the harness's own files (works even without the request logger / after an interrupt):
#     finished tasks -> traces/trace_<task>.json (every thought, tool call, tool output); unfinished -> logs/<task>.log tail.
import glob, json, re
from pathlib import Path

ANSI = re.compile(r'\x1b\[[0-9;]*[A-Za-z]')
for f in sorted(glob.glob('/kaggle/working/results/**/task_results.jsonl', recursive=True)):
    for l in open(f):
        j = json.loads(l)
        print('RESULT', j.get('instance_id'), 'resolved' if j.get('resolved') else 'NOT resolved', '| tool calls',
              j.get('tool_calls'), '|', (j.get('error') or '')[:80])
done = set()
for f in sorted(glob.glob('/kaggle/working/results/**/traces/trace_*.json', recursive=True)):
    t = json.load(open(f))
    name = Path(f).stem.replace('trace_', '')
    done.add(name)
    print(f'\n=== TRACE {name}: {len(t["steps"])} steps')
    n = 0
    for s in t['steps']:
        if s.get('source') != 'agent':
            continue
        msg = (s.get('message') or '').strip().replace('\n', ' ')
        calls = s.get('tool_calls') or []
        if msg and not calls:
            print(f'      ({(s.get("extra") or {}).get("event_type", "")}) {msg[:160]!r}')
        for c in calls:
            n += 1
            obs = s.get('observation') or {}
            out = obs.get('content') if isinstance(obs, dict) else obs
            m = (s.get('metrics') or {})
            print(f'  {n:2}. {msg[:110]!r}' if msg else f'  {n:2}.', f'[out {m.get("completion_tokens")}]' if m else '')
            print(f'      -> {c.get("function_name")} {json.dumps(c.get("arguments"))[:170]}')
            print(f'      <- {str(out)[:180]!r}')
for f in sorted(glob.glob('/kaggle/working/results/**/logs/*.log', recursive=True)):
    name = Path(f).stem
    if name in done:
        continue
    lines = [ANSI.sub('', l).rstrip() for l in open(f, errors='replace')]
    lines = [l for l in lines if l.strip()]
    print(f'\n=== LIVE LOG (unfinished) {name}: {len(lines)} lines; first 60 and last 30:')
    print('\n'.join(lines[:60]))
    print('   ...')
    print('\n'.join(lines[-30:]))
