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
print('Recording model requests to', REQUEST_LOG, '(diagnostics only: OOD-45 is our yardstick, never training data)')
