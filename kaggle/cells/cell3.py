# 3. Start vLLM once for all configs (no adapters → LoRA off → more KV cache). Takes ~6–8 min.
import litellm, torch
from adk_submission import VllmConfig, VllmServer

litellm.drop_params = True
TARGET_MODEL_NAME = 'gemma-4-31b-it-qat-w4a16-ct'
MODEL_PATH = Path(glob.glob('/kaggle/input/models/google/gemma-4/**/gemma-4-31b-it-qat-w4a16-ct/2', recursive=True)[0])
gpu_count = torch.cuda.device_count() if torch.cuda.is_available() else 1
tp_size = 4 if gpu_count >= 4 else (2 if gpu_count >= 2 else 1)

vllm_cfg = VllmConfig(
    model=str(MODEL_PATH),
    port=8000,
    host='127.0.0.1',
    tool_call_parser='gemma4',
    reasoning_parser='gemma4',
    max_model_len=32768,
    dtype='bfloat16' if (torch.cuda.is_available() and torch.cuda.is_bf16_supported()) else 'auto',
    gpu_memory_utilization=0.90,
    enable_auto_tool_choice=True,
    enable_lora=False,
    tensor_parallel_size=tp_size,
    startup_timeout=60 * 20,
)
server_instance = VllmServer(vllm_cfg)
server_instance.start()
print(f'vLLM server started on {server_instance.base_url} (tp={tp_size})')
models = server_instance.create_model_registry(aliases=[TARGET_MODEL_NAME], model_prefix='openai/', api_key='EMPTY')

# Installed harness versions (the wheelhouse changes over time; rung-1i notes).
from importlib.metadata import version, PackageNotFoundError
def _ver(p):
    try:
        return version(p)
    except PackageNotFoundError:
        return None
print('VERSIONS', {p: _ver(p) for p in ('adk-submission', 'swegemma', 'adk-eval-core', 'google-adk', 'vllm')})

# Sampling diagnostic (rung-1j): replay the REAL first orchestrator request (full 1b prompt + harness task message)
# under several sampling settings, thinking off. Counts hidden reasoning, thought markers leaking into text, and
# whether a proper tool call came back. Task text is read at runtime from the competition data (never committed).
def _sampling_diagnostic(task_ids=("rich_3882", "fastapi_15589"), samples=3):
    import json as _json, time, types, urllib.request as _url
    from swegemma.harness.agent_runner import build_agent_prompt
    _base = server_instance.base_url.rstrip("/")
    _base = _base if _base.endswith("/v1") else _base + "/v1"
    _served = _json.load(_url.urlopen(_base + "/models"))["data"][0]["id"]
    def _fn(name, desc, props=None, req=()):
        return {"type": "function", "function": {"name": name, "description": desc, "parameters":
                {"type": "object", "properties": props or {}, "required": list(req)}}}
    _s = {"type": "string"}; _i = {"type": "integer"}
    _tools = [_fn("run_command", "Run a shell command in the workspace.", {"command": _s}, ["command"]),
              _fn("read_file", "Read a file.", {"filepath": _s, "start_line": _i, "end_line": _i}, ["filepath"]),
              _fn("get_status", "Budget and progress."), _fn("submit_patch", "Submit the current diff."),
              _fn("search_similar_code", "Semantic code search.", {"query": _s}, ["query"]),
              _fn("get_code_neighbors", "Graph neighbors of a symbol.", {"symbol": _s}, ["symbol"]),
              _fn("get_code_subgraph", "Graph around a symbol.", {"symbol": _s}, ["symbol"]),
              _fn("executor", "Makes the code change.", {"request": _s}, ["request"]),
              _fn("verifier", "Checks the change.", {"request": _s}, ["request"])]
    _tasks = {}
    for _line in (DATA_DIR / "tasks.jsonl").read_text().splitlines():
        _d = _json.loads(_line)
        if _d.get("instance_id") in task_ids:
            _tasks[_d["instance_id"]] = types.SimpleNamespace(**_d)
    class _NS(types.SimpleNamespace):
        def __getattr__(self, _name):  # any field the harness reads but we did not set -> None
            return None
    _cfg = _NS(budget=_NS(time_minutes=5.0, tool_calls=80, turns=90), harness=_NS(command_timeout_seconds=240, max_stdout_chars=5000),
               enable_sandbox_testing=True)
    _instr = (SUB_ROOT / "1b" / "prompts" / "orchestrator.md").read_text()
    _settings = [("T1.0 p0.95 k64", 1.0, 0.95, 64), ("T1.0 p0.80 k20", 1.0, 0.80, 20), ("T0.6 p0.95 k64", 0.6, 0.95, 64),
                 ("T0.4 p0.95 k64", 0.4, 0.95, 64), ("T0.2 p0.95 k64", 0.2, 0.95, 64)]
    _summary = {}
    for _tid, _task in _tasks.items():
        try:
            _user = build_agent_prompt(_task, _cfg, "", declared_tools=[t["function"]["name"] for t in _tools])
        except Exception as _e:
            print("build_agent_prompt failed, using plain task text:", repr(_e))
            _user = "Problem Statement:\n" + _task.problem_statement
        _msgs = [{"role": "system", "content": _instr.replace("{problem_description}", _task.problem_statement)},
                 {"role": "user", "content": _user}]
        for _name, _t, _p, _k in _settings:
            for _rep in range(samples):
                _body = {"model": _served, "messages": _msgs, "tools": _tools, "temperature": _t, "top_p": _p,
                         "top_k": _k, "max_tokens": 1024, "chat_template_kwargs": {"enable_thinking": False}}
                _t0 = time.time()
                _req = _url.Request(_base + "/chat/completions", data=_json.dumps(_body).encode(),
                                    headers={"Content-Type": "application/json"})
                _r = _json.load(_url.urlopen(_req, timeout=600))
                _m = _r["choices"][0]["message"]
                _reason = _m.get("reasoning_content") or _m.get("reasoning") or ""
                _content = _m.get("content") or ""
                _ok = bool(_m.get("tool_calls"))
                _leak = "<|channel>" in _content or "<channel|>" in _content
                _row = (time.time() - _t0, _r["usage"]["completion_tokens"], len(_reason), _leak, _ok)
                _summary.setdefault(_name, []).append(_row)
                print(f"{_tid:14} {_name}  #{_rep + 1}: {_row[0]:5.1f}s  out_tok={_row[1]:5}  reasoning_chars={_row[2]:5}  "
                      f"marker_in_text={_leak}  tool_call={_ok}  prompt_tok={_r['usage']['prompt_tokens']}")
                if (_reason or _leak) and _rep == 0:
                    print("    starts:", repr((_reason or _content)[:160]))
    print("SAMPLING SUMMARY (per setting over all tasks and samples)")
    for _name, _rows in _summary.items():
        _n = len(_rows)
        print(f"  {_name}: mean {sum(r[0] for r in _rows) / _n:5.1f}s  mean out_tok {sum(r[1] for r in _rows) / _n:6.0f}  "
              f"with reasoning {sum(r[2] > 0 for r in _rows)}/{_n}  marker leaks {sum(r[3] for r in _rows)}/{_n}  "
              f"proper tool calls {sum(r[4] for r in _rows)}/{_n}")
try:
    _sampling_diagnostic()
except Exception as _e:  # never block the evaluation
    print("sampling diagnostic failed:", repr(_e))