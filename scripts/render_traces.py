"""Rebuild the exact prompt vLLM saw at each model call of a harness trace, in Gemma 4's chat format.

Run with the harness venv (exact competition versions):
    data/venv_harness/bin/python scripts/render_traces.py data/results/<run>/results/<arm>/traces/trace_<task>.json

It rebuilds the OpenAI-style request the way the harness builds it (ADK LiteLlm conversion + adk_submission's
reasoning patch + the real swegemma tool definitions), renders it with data/gemma4_tokenizer/chat_template.jinja,
tokenizes it, and compares the token count with the prompt_tokens vLLM recorded for that step. Equal counts mean the
rendering matches what the model was actually trained against at inference time; the training samples are built on
top of this.
"""
import argparse
import json
import sys
from pathlib import Path

import jinja2
from tokenizers import Tokenizer

ROOT = Path(__file__).resolve().parents[1]
TOK_DIR = ROOT / "data" / "gemma4_tokenizer"
DEFAULT_TOOLS = ["run_command", "read_file", "edit_file", "write_file", "get_status", "submit_patch"]


def tool_params(names):
    """OpenAI tool dicts for the harness tools, built by the same code path the harness uses."""
    import adk_submission  # noqa: F401  (installs the schema / reasoning patches on ADK's LiteLlm module)
    from google.adk.models import lite_llm
    from google.adk.tools import FunctionTool
    from swegemma.tools import create_tools

    class _Ctx:  # the factories only close over ctx; nothing is called here
        def __getattr__(self, name):
            return None

    funcs = create_tools(_Ctx())
    return [lite_llm._function_declaration_to_tool_param(FunctionTool(funcs[n])._get_declaration()) for n in names]


def load_template():
    env = jinja2.Environment(trim_blocks=True, lstrip_blocks=True, extensions=["jinja2.ext.loopcontrols"])
    env.filters["tojson"] = lambda v, **k: json.dumps(v, **k)
    tmpl = env.from_string((TOK_DIR / "chat_template.jinja").read_text())
    cfg = json.loads((TOK_DIR / "tokenizer_config.json").read_text())
    return tmpl, cfg.get("bos_token", "<bos>")


def render(tmpl, bos, messages, tools, enable_thinking=True, add_generation_prompt=True):
    return tmpl.render(messages=messages, tools=tools, bos_token=bos, enable_thinking=enable_thinking,
                       add_generation_prompt=add_generation_prompt)


def messages_until(trace, step_index, agent_name="swe_agent", agent_description=None, args_as="dict"):
    """The OpenAI messages the harness sent for the model call made at trace step `step_index`.

    ADK builds the system prompt as the agent instruction, then (identity processor) a blank line and
    'You are an agent. Your internal name is "<name>".' plus the description if the agent has one."""
    identity = f'You are an agent. Your internal name is "{agent_name}".'
    if agent_description:
        identity += f' The description about you is "{agent_description}".'
    steps = trace["steps"]
    msgs = []
    pending_text = None  # a visible-text step: content of the next assistant message
    for st in steps[:step_index]:
        src = st.get("source")
        etype = (st.get("extra") or {}).get("event_type")
        if src == "system" and etype == "system_instruction":
            msgs.append({"role": "system", "content": st["message"] + "\n\n" + identity})
        elif src == "user" or (src == "system" and st.get("message") and etype not in (None, "usage")):
            # the task prompt and harness nudges (continuation_nudge, ...) are user messages
            msgs.append({"role": "user", "content": st["message"]})
        elif src == "agent":
            if etype == "text" and not st.get("tool_calls"):
                pending_text = (pending_text + "\n" if pending_text else "") + (st.get("message") or "")
                continue
            calls = []
            for tc in st.get("tool_calls") or []:
                args = tc.get("arguments") or {}
                calls.append({"id": tc.get("tool_call_id", ""), "type": "function",
                              "function": {"name": tc["function_name"],
                                           "arguments": args if args_as == "dict" else json.dumps(args)}})
            thought = (st.get("message") or None) if etype != "text" else None
            content = pending_text if etype != "text" else st.get("message")
            pending_text = None
            msgs.append({"role": "assistant", "content": content, "tool_calls": calls or None,
                         "reasoning_content": thought, "reasoning": thought})
            obs = st.get("observation") or {}
            if calls and isinstance(obs, dict) and "content" in obs:
                msgs.append({"role": "tool", "tool_call_id": calls[0]["id"], "content": obs["content"]})
    return msgs


def request_to_template_inputs(record):
    """messages, tools and enable_thinking from a request recorded by scripts/request_logger.py, prepared the way
    vLLM prepares them (tool-call arguments parsed from JSON strings into dicts)."""
    req = record["request"]
    msgs = []
    for m in req["messages"]:
        m = dict(m)
        if m.get("tool_calls"):
            calls = []
            for c in m["tool_calls"]:
                c = json.loads(json.dumps(c))
                args = c["function"].get("arguments")
                if isinstance(args, str):
                    try:
                        c["function"]["arguments"] = json.loads(args) if args.strip() else {}
                    except json.JSONDecodeError:
                        pass
                calls.append(c)
            m["tool_calls"] = calls
        msgs.append(m)
    kw = req.get("kwargs") or {}
    ctk = kw.get("chat_template_kwargs") or (kw.get("extra_body") or {}).get("chat_template_kwargs") or {}
    return msgs, req.get("tools"), bool(ctk.get("enable_thinking"))


def check_requests(path, limit=None):
    """Render every recorded request and compare with the prompt_tokens vLLM reported for it."""
    import gzip
    tmpl, bos = load_template()
    tok = Tokenizer.from_file(str(TOK_DIR / "tokenizer.json"))
    exact = off = 0
    for n, line in enumerate(gzip.open(path, "rt")):
        if limit and n >= limit:
            break
        rec = json.loads(line)
        usage = (rec.get("reply") or {}).get("usage") if isinstance(rec.get("reply"), dict) else None
        if not usage:
            continue
        msgs, tools, think = request_to_template_inputs(rec)
        got = len(tok.encode(render(tmpl, bos, msgs, tools, enable_thinking=think), add_special_tokens=False).ids)
        want = usage["prompt_tokens"]
        exact, off = (exact + 1, off) if got == want else (exact, off + 1)
        if got != want and off <= 10:
            print(f"request {n}: vLLM {want} rendered {got} diff {got - want:+d}")
    print(f"requests rendered exactly: {exact}, different: {off}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("trace", help="a harness trace (.json) or a request log (.jsonl.gz from request_logger.py)")
    ap.add_argument("--steps", type=int, default=6, help="how many model calls to check")
    ap.add_argument("--show", action="store_true", help="print the rendered text of the first call")
    a = ap.parse_args()
    if a.trace.endswith(".jsonl.gz"):
        return check_requests(a.trace)
    trace = json.loads(Path(a.trace).read_text())
    tmpl, bos = load_template()
    tok = Tokenizer.from_file(str(TOK_DIR / "tokenizer.json"))
    tools = tool_params(DEFAULT_TOOLS)
    checked = 0
    for i, st in enumerate(trace["steps"]):
        if st.get("source") != "agent" or not st.get("metrics"):
            continue
        want = st["metrics"]["prompt_tokens"]
        text = render(tmpl, bos, messages_until(trace, i), tools)
        got = len(tok.encode(text, add_special_tokens=False).ids)
        print(f"step {i:3}: vLLM prompt_tokens={want:6}  rendered={got:6}  diff={got - want:+d}")
        if a.show and checked == 0:
            print(text[:3000])
        checked += 1
        if checked >= a.steps:
            break


if __name__ == "__main__":
    sys.exit(main())
