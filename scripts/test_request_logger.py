"""Local check of the request logger (no GPU): a fake OpenAI-compatible server stands in for vLLM.

    data/venv_harness/bin/python scripts/test_request_logger.py

Compiles submissions/mix with the competition compiler and the same model registry the notebook builds, runs it
through ADK for three model calls (thinking + run_command, thinking + submit_patch, final text), and checks that every
call was recorded with the exact messages, tools, thinking switch and reply, and that earlier thinking is carried in
the history the way the harness sends it.
"""
import asyncio
import gzip
import json
import socket
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

REPLIES = [
    {"reasoning_content": "Find the function first.", "content": None,
     "tool_calls": [{"id": "c1", "type": "function",
                     "function": {"name": "run_command", "arguments": json.dumps({"command": "git grep -n foo"})}}]},
    {"reasoning_content": "Found it; submit.", "content": None,
     "tool_calls": [{"id": "c2", "type": "function", "function": {"name": "submit_patch", "arguments": "{}"}}]},
    {"reasoning_content": None, "content": "Done.", "tool_calls": None},
]
SEEN = []


class FakeVllm(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        SEEN.append(body)
        msg = dict(REPLIES[min(len(SEEN) - 1, len(REPLIES) - 1)], role="assistant")
        out = {"id": f"r{len(SEEN)}", "object": "chat.completion", "created": 0, "model": body["model"],
               "choices": [{"index": 0, "message": msg,
                            "finish_reason": "tool_calls" if msg.get("tool_calls") else "stop"}],
               "usage": {"prompt_tokens": 100 * len(SEEN), "completion_tokens": 10, "total_tokens": 100 * len(SEEN) + 10}}
        data = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


async def run_agent(agent):
    from google.adk.runners import InMemoryRunner
    from google.genai import types
    runner = InMemoryRunner(agent=agent, app_name="t")
    session = await runner.session_service.create_session(app_name="t", user_id="u")
    msg = types.Content(role="user", parts=[types.Part(text="Problem Statement:\nFix foo.")])
    async for _ in runner.run_async(user_id="u", session_id=session.session_id if hasattr(session, "session_id")
                                    else session.id, new_message=msg):
        pass


def main():
    port = free_port()
    server = HTTPServer(("127.0.0.1", port), FakeVllm)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    from request_logger import install_request_logger
    log = Path(tempfile.mkdtemp()) / "requests.jsonl.gz"
    install_request_logger(log)

    from adk_submission import VllmConfig, VllmServer, compile_submission
    from swegemma.config import build_submission_limits
    srv = VllmServer(VllmConfig(model="gemma-4-31b-it-qat-w4a16-ct", port=port, host="127.0.0.1"))
    models = srv.create_model_registry(aliases=["gemma-4-31b-it-qat-w4a16-ct"], model_prefix="openai/", api_key="EMPTY")
    limits, gen = build_submission_limits()

    def run_command(command: str) -> str:
        """Run a shell command."""
        return json.dumps({"status": "ok", "stdout": "pkg/a.py:3:def foo():\n", "stderr": "", "exit_code": 0})

    def submit_patch() -> str:
        """Submit the patch."""
        return json.dumps({"status": "ok", "patch_size": 10})

    def other(**_):
        return "{}"
    tools = {n: other for n in ("read_file", "edit_file", "write_file", "get_status")}
    tools.update(run_command=run_command, submit_patch=submit_patch)
    agent = compile_submission(submission_dir=ROOT / "submissions" / "mix", tool_registry=tools, model_registry=models,
                               limits=limits, generation_constraints=gen)
    asyncio.run(run_agent(agent))
    server.shutdown()

    recs = [json.loads(l) for l in gzip.open(log, "rt")]
    print(f"fake server got {len(SEEN)} requests; logger recorded {len(recs)}")
    assert len(recs) == len(SEEN) == 3, "every call must be recorded"
    for i, (rec, sent) in enumerate(zip(recs, SEEN)):
        req = rec["request"]
        if req["messages"] != sent["messages"]:
            for a, b in zip(req["messages"], sent["messages"]):
                if a != b:
                    print("RECORDED:", json.dumps(a)[:400]); print("SENT:    ", json.dumps(b)[:400])
            raise SystemExit(f"call {i}: recorded messages differ from what was sent")
        assert [t["function"]["name"] for t in req["tools"]] == [t["function"]["name"] for t in sent["tools"]]
        ctk = (sent.get("chat_template_kwargs") or (sent.get("extra_body") or {}).get("chat_template_kwargs"))
        print(f"call {i}: {len(req['messages'])} messages, {len(req['tools'])} tools, "
              f"sent chat_template_kwargs={ctk}, thinking budget sent={sent.get('thinking_token_budget')}, "
              f"reply tool_calls={[c['function']['name'] for c in (rec['reply']['message']['tool_calls'] or [])]}")
    hist = recs[1]["request"]["messages"]
    asst = [m for m in hist if m["role"] == "assistant"]
    print("assistant message in call 1's history:", json.dumps(asst[0])[:300])
    assert asst and (asst[0].get("reasoning_content") or asst[0].get("reasoning")), "earlier thinking must be in history"
    print("roles in call 2:", [m["role"] for m in recs[2]["request"]["messages"]])
    from render_traces import request_to_template_inputs, load_template, render
    tmpl, bos = load_template()
    msgs, tools_r, think = request_to_template_inputs(recs[2])
    text = render(tmpl, bos, msgs, tools_r, enable_thinking=think)
    assert "<|think|>" in text and "Find the function first." in text and "call:run_command{command:" in text
    print("rendered call 2 (tail):", repr(text[-420:]))
    print("OK: logger records exactly what the model was sent, and the records render with Gemma's template")


if __name__ == "__main__":
    main()
