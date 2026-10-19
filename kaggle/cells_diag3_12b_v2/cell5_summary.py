# 5. Summary per variant x task (paste this output to Claude), then a short per-call digest. Then STOP THE SESSION.
import collections, glob, json
from pathlib import Path


def run_stats(trace):
    calls, thoughts, errors = [], [], 0
    for s in trace['steps']:
        if s.get('source') != 'agent':
            continue
        if s.get('message') and (s.get('extra') or {}).get('event_type') in (None, 'thinking'):
            thoughts.append(s['message'])
        for c in s.get('tool_calls') or []:
            calls.append((c.get('function_name'), json.dumps(c.get('arguments'), sort_keys=True)))
            obs = s.get('observation') or {}
            out = str(obs.get('content') if isinstance(obs, dict) else obs)
            if '"status": "error"' in out or 'No such file' in out or 'Traceback' in out:
                errors += 1
    rep = max(collections.Counter(calls).values(), default=0)
    edits = sum(1 for n, a in calls if n in ('edit_file', 'write_file') or (n == 'run_command' and
                any(k in a for k in ('sed -i', "open(", '> /workspace', 'patch -p'))))
    return {'calls': len(calls), 'distinct': len(set(calls)), 'max_same_call': rep, 'edits': edits, 'errors': errors,
            'think_chars_median': sorted(len(t) for t in thoughts)[len(thoughts) // 2] if thoughts else 0,
            'distinct_thoughts': len(set(thoughts)), 'thoughts': len(thoughts)}


rows = []
for d in sorted(glob.glob('/kaggle/working/results/*/')):
    variant = Path(d).name
    res = {}
    for f in glob.glob(d + 'task_results.jsonl'):
        for l in open(f):
            j = json.loads(l)
            res[j['instance_id']] = j
    for f in sorted(glob.glob(d + 'traces/trace_*.json')):
        task = Path(f).stem.replace('trace_', '')
        st = run_stats(json.load(open(f)))
        r = res.get(task, {})
        rows.append((variant, task, r.get('resolved'), (r.get('error') or '')[:40], st))
print(f"{'variant':16} {'task':14} {'resolved':8} {'calls':5} {'distinct':8} {'max_same':8} {'edits':5} {'errors':6} "
      f"{'think_med':9} {'thoughts(distinct)':18} end")
for v, t, ok, err, s in rows:
    print(f"{v:16} {t:14} {str(bool(ok)):8} {s['calls']:5} {s['distinct']:8} {s['max_same_call']:8} {s['edits']:5} "
          f"{s['errors']:6} {s['think_chars_median']:9} {str(s['thoughts']) + '(' + str(s['distinct_thoughts']) + ')':18} {err}")

print('\n--- first 12 calls of every run ---')
for f in sorted(glob.glob('/kaggle/working/results/*/traces/trace_*.json')):
    t = json.load(open(f))
    print('\n==', Path(f).parent.parent.name, Path(f).stem.replace('trace_', ''))
    n = 0
    for s in t['steps']:
        if s.get('source') != 'agent' or not s.get('tool_calls'):
            continue
        for c in s['tool_calls']:
            n += 1
            if n > 12:
                break
            obs = s.get('observation') or {}
            out = str(obs.get('content') if isinstance(obs, dict) else obs)
            msg = (s.get('message') or '').replace('\n', ' ')
            print(f"  {n:2}. {msg[:100]!r}\n      -> {c.get('function_name')} {json.dumps(c.get('arguments'))[:130]}"
                  f"\n      <- {out[:110]!r}")
