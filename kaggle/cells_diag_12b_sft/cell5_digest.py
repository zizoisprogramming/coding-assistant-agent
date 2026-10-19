# 5. Digest: every model call of every task, compact (paste this output to Claude). Also: requests.zip to download.
import json, shutil
recs = [json.loads(l) for l in open('/kaggle/working/requests/requests.jsonl')]
print(len(recs), 'model calls recorded')
task, n = None, 0
for r in recs:
    msgs = r['request']['messages']
    first_user = next((m.get('content') for m in msgs if m.get('role') == 'user'), '')
    first_user = first_user if isinstance(first_user, str) else json.dumps(first_user)
    if not r['request'].get('tools'):
        print('    [compaction summary call]'); continue
    if 'Problem Statement' in first_user and first_user[:300] != task:
        task, n = first_user[:300], 0
        print('\n=== TASK:', first_user.split('Problem Statement:')[-1].strip()[:100].replace('\n', ' '))
    n += 1
    last = msgs[-1]
    if last.get('role') == 'tool':
        print(f'      <- {str(last.get("content"))[:160]!r}')
    elif last.get('role') == 'user' and n > 1:
        print(f'      <- USER: {str(last.get("content"))[:120]!r}')
    rep = r.get('reply') or {}
    m = rep.get('message') or {}
    think = m.get('reasoning_content') or m.get('reasoning') or ''
    calls = [(c['function']['name'], c['function']['arguments'][:140]) for c in (m.get('tool_calls') or [])]
    use = rep.get('usage') or {}
    print(f'  {n:2}. prompt {use.get("prompt_tokens")} out {use.get("completion_tokens")} finish {rep.get("finish_reason")} '
          f'| think {len(think)} ch: {think[:120]!r}')
    if m.get('content'):
        print(f'      TEXT: {m["content"][:200]!r}')
    for name, args in calls:
        print(f'      -> {name} {args}')
    if r.get('error'):
        print('      ERROR', r['error'][:200])
shutil.make_archive('/kaggle/working/requests', 'zip', '/kaggle/working/requests')
print('\nfiles: requests.zip (all raw calls), results.zip (harness results + traces)')
