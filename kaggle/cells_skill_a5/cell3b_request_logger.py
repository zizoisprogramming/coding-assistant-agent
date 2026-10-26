# 3b. Record every model request and reply exactly as sent to vLLM (training data). Prints nothing during the run.
# Wraps ADK's LiteLLMClient.acompletion (the only path ADK uses to call the model) and appends one JSON line per call
# to a plain JSONL file (uncompressed on purpose: a browser download unpacked a multi-block .gz and kept only
# its first record): the exact messages, tools and extra request fields, and the reply (content, reasoning, tool calls,
# usage). Training samples are rendered from these records with Gemma's chat template (scripts/render_traces.py).
import json, os, threading, time
from pathlib import Path


def install_request_logger(path, tag=None):
    """tag: optional callable returning extra fields for each record (stage B: which episode / attempt)."""
    from google.adk.models import lite_llm

    lock = threading.Lock()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    orig = lite_llm.LiteLLMClient.acompletion
    if getattr(orig, '_request_logger', False):
        return path

    def _plain(obj):
        if hasattr(obj, 'model_dump'):
            try:
                return obj.model_dump()
            except Exception:
                pass
        if isinstance(obj, dict):
            return {k: _plain(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_plain(v) for v in obj]
        return obj if isinstance(obj, (str, int, float, bool, type(None))) else repr(obj)

    def _reply(resp):
        resp = _plain(resp)
        if not isinstance(resp, dict):
            return {'raw': resp}
        msg = ((resp.get('choices') or [{}])[0] or {}).get('message') or {}
        return {'message': {k: msg.get(k) for k in ('content', 'reasoning_content', 'reasoning', 'tool_calls')},
                'finish_reason': ((resp.get('choices') or [{}])[0] or {}).get('finish_reason'),
                'usage': resp.get('usage')}

    def _write(record):
        if tag is not None:
            record.update(tag())
        line = json.dumps(record, ensure_ascii=False, default=repr)
        with lock, open(path, 'a', encoding='utf-8') as f:
            f.write(line + '\n')

    async def acompletion(self, model, messages, tools, **kwargs):
        t0 = time.time()
        # messages as they go over the wire: LiteLLM drops keys whose value is None
        wire = [{k: v for k, v in m.items() if v is not None} if isinstance(m, dict) else m for m in _plain(messages)]
        request = {'model': model, 'messages': wire, 'tools': _plain(tools),
                   'kwargs': {k: _plain(v) for k, v in kwargs.items() if k not in ('api_key', 'api_base')}}
        try:
            resp = await orig(self, model, messages, tools, **kwargs)
        except Exception as e:
            _write({'t': t0, 'seconds': time.time() - t0, 'request': request, 'error': repr(e)})
            raise
        if kwargs.get('stream'):
            _write({'t': t0, 'seconds': time.time() - t0, 'request': request, 'reply': 'stream (not recorded)'})
            return resp
        _write({'t': t0, 'seconds': time.time() - t0, 'request': request, 'reply': _reply(resp)})
        return resp

    acompletion._request_logger = True
    lite_llm.LiteLLMClient.acompletion = acompletion
    return path


import contextvars
JOB = contextvars.ContextVar('ood_job', default=None)  # set by cell 4 around each task: which variant and task
REQUEST_LOG = install_request_logger(Path('/kaggle/working') / 'requests' / 'requests.jsonl',
                                     tag=lambda: {'job': JOB.get()})
print('Recording model requests to', REQUEST_LOG, '(skill arms: tagged task#a<arm>.<pass>)')


# DIGEST (make_skill_arms_cells.py): per run (job task#a<arm>.<pass>), counted from the model replies as they come:
# what the agent did with its calls and where the time went. Cell 4 prints one line after each run (it stays in the
# log even if the session is cancelled) and appends it to results/digest.jsonl.
import collections, re
from google.adk.models import lite_llm as _ll

DIGEST = collections.defaultdict(collections.Counter)
_A_PY = re.compile(r'\.git/agent/a\.py\s+(\w+)')
_RAW = re.compile(r'(^|[;&|(]\s*)(cat|sed|head|tail|grep|nl|less|awk)\s|git grep|git show \S+:')


def _dump(o):
    if hasattr(o, 'model_dump'):
        try:
            return o.model_dump()
        except Exception:
            return {}
    return o if isinstance(o, dict) else {}


def _text(content):
    if isinstance(content, list):
        return ' '.join(str(_dump(c).get('text') or c) for c in content)
    return str(content or '')


def _digest(job, messages, resp, seconds):
    d = DIGEST[job]
    d['model_calls'] += 1
    d['model_ms'] += int(seconds * 1000)
    last = _dump(messages[-1]) if messages else {}
    if last.get('role') == 'tool':
        out = _text(last.get('content'))
        d['refused'] += 'NOT SHOWN AGAIN' in out
        d['reshown'] += 'ALREADY SHOWN' in out
        d['banner'] += 'NO EDIT YET' in out
        d['stop_banner'] += 'STOP READING' in out
        d['blocked'] += 'BLOCKED: ' in out
        d['debug_flag'] += 'DEBUG LINE IN YOUR DIFF' in out
        d['edit_fail'] += any(k in out for k in ('FileEditError', 'old_string not found', 'REPLACE FAILED'))
    r = _dump(resp)
    usage = r.get('usage') or {}
    pt = usage.get('prompt_tokens') or 0
    if d['last_prompt'] and pt < 0.7 * d['last_prompt']:
        d['compactions'] += 1
    d['last_prompt'] = pt
    d['max_prompt'] = max(d['max_prompt'], pt)
    d['out_tokens'] += usage.get('completion_tokens') or 0
    msg = ((r.get('choices') or [{}])[0] or {}).get('message') or {}
    for tc in msg.get('tool_calls') or []:
        fn = (tc or {}).get('function') or {}
        name, args = fn.get('name') or '?', fn.get('arguments') or ''
        try:
            a = json.loads(args) if isinstance(args, str) else (args or {})
        except Exception:
            a = {}
        d['tool_calls'] += 1
        n = d['tool_calls']
        edit = False
        if name == 'run_command':
            cmd = str(a.get('command', ''))
            subs = _A_PY.findall(cmd)
            for c in subs:
                d[c if c in ('find', 'outline', 'show', 'note', 'pin', 'impact', 'check', 'plan', 'replace', 'run') else 'a_other'] += 1
            if not subs and _RAW.search(cmd):
                d['raw_read'] += 1
            if 'pytest' in cmd:
                d['pytest'] += 1
            if not d['first_edit'] and (('run' in subs) or (re.search(r'pytest|python3?\s+(-c\b|-\s*<<|-m\b|\S+\.py)', cmd)
                                                            and not subs)):
                d['pre_edit_runs'] += 1  # a script or test run before the first edit (solved 8/17 at 0-4, 2/11 at 5+)
            if re.search(r'\bpip\b', cmd):
                d['pip'] += 1
            if 'repro.py' in cmd:
                d['repro'] += 1
            edit = 'git apply' in cmd or 'sed -i' in cmd or ('.write' in cmd and '<<' in cmd) or 'replace' in subs
        elif name in ('edit_file', 'write_file'):
            path = str(a.get('filepath') or a.get('file_path') or a.get('path') or '')
            if '.git/agent/' in path:
                d['repro'] += 1
            else:
                d[name] += 1
                edit = True
        elif name == 'run_skill_script':
            d['install'] += 1
            d['install_at'] = d['install_at'] or n
        else:
            d[name] += 1
        if n == 1 and name != 'run_skill_script':
            d['call1_wrong'] = 1
        if edit and not d['first_edit']:
            d['first_edit'] = n


_inner = _ll.LiteLLMClient.acompletion
if not getattr(_inner, '_digest', False):
    async def _acompletion_digest(self, model, messages, tools, **kwargs):
        t0 = time.time()
        resp = await _inner(self, model, messages, tools, **kwargs)
        try:
            _digest(JOB.get(), messages, resp, time.time() - t0)
        except Exception as e:  # never break a run over the digest
            DIGEST[JOB.get()]['digest_errors'] += 1
        return resp
    _acompletion_digest._digest = True
    _ll.LiteLLMClient.acompletion = _acompletion_digest


def digest_row(job, agent_s):
    d = DIGEST.get(job) or collections.Counter()
    model_s = d['model_ms'] / 1000
    n = max(d['tool_calls'], 1)
    keys = ('install', 'install_at', 'find', 'outline', 'show', 'note', 'pin', 'impact', 'check', 'a_other', 'raw_read',
            'read_file', 'pre_edit_runs', 'plan', 'blocked', 'debug_flag', 'replace', 'run', 'edit_fail', 'refused', 'reshown', 'banner', 'stop_banner', 'pip', 'call1_wrong', 'repro', 'pytest', 'edit_file', 'write_file', 'first_edit', 'compactions',
            'max_prompt', 'out_tokens', 'model_calls', 'tool_calls', 'get_status', 'submit_patch', 'digest_errors')
    row = {k: d[k] for k in keys}
    row.update(model_s=round(model_s), tool_s=round(max(agent_s - model_s, 0)),
               model_s_per_call=round(model_s / max(d['model_calls'], 1), 1),
               tool_s_per_call=round(max(agent_s - model_s, 0) / n, 1))
    return row


def digest_line(r):
    return (f"      DIGEST install@{r['install_at'] or '-'} | a.py find {r['find']} outline {r['outline']} show "
            f"{r['show']} note {r['note']} pin {r['pin']} | raw reads {r['raw_read']} read_file {r['read_file']} | "
            f"scripts/tests before edit {r['pre_edit_runs']} | a.py replace {r['replace']} run {r['run']} | failed edits "
            f"{r['edit_fail']} | plan {r['plan']} blocked {r['blocked']} debug flags "
            f"{r['debug_flag']} | refused {r['refused']} reshown {r['reshown']} | banners {r['banner']}+{r['stop_banner']} stop | pip {r['pip']} | "
            f"edit_file/write_file {r['edit_file'] + r['write_file']}, first edit at call {r['first_edit'] or '-'} | "
            f"repro {r['repro']} pytest {r['pytest']} | compactions {r['compactions']} max prompt {r['max_prompt']} | "
            f"model {r['model_s']}s ({r['model_s_per_call']}s/call) tools {r['tool_s']}s ({r['tool_s_per_call']}s/call) "
            f"| out tokens {r['out_tokens']}" + (f" | DIGEST ERRORS {r['digest_errors']}" if r['digest_errors'] else ''))
print('DIGEST on: one line per run after its result line (results/digest.jsonl)')
