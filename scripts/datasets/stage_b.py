"""Stage B: replay the selected teacher episodes through the REAL competition harness, so every training sample is
exactly the prompt our agent receives and exactly the reply it should write.

    python stage_b.py --selection selection_v1.json --episodes <dir> [<dir> ...] --submission submissions/mix_12b \
        --out <dir> --tokenizer-dir <dir with chat_template.jinja + tokenizer.json> \
        (--vllm-base http://127.0.0.1:8000/v1 | --fake-summarizer) [--limits harness|full] [--limit N] [--shard i/n]

How (decided with the user, docs/PLAN.md "stage B"):
- The real submission is compiled with the competition compiler, run by ADK with the harness's plugins, task prompt
  (build_agent_prompt with the episode's issue text and workspace tree), session state and compaction settings.
- The model is a small local HTTP server that speaks vLLM's OpenAI API. For the agent's calls it answers with the
  teacher's next step (thinking, text, tool calls) and reports the exact prompt size (Gemma chat template +
  tokenizer, checked token-exact against vLLM), so ADK compacts exactly when it would on the scorer. Calls without
  tools are ADK's compaction summaries: those go to the real vLLM (the model being trained writes them).
- The tools are the harness's real tool functions; only the sandbox under them is fake: it hands back the teacher's
  recorded output for that call (command output and exit code; file contents rebuilt from the teacher's `cat -n`
  views and edit snippets). So the JSON shapes, error formats, truncation and budget warnings are the harness's own.
- Every request/reply is recorded by scripts/request_logger.py, tagged with the episode id and an attempt id; the
  attempt counts only if the episode's line in status.jsonl says ok. Crash-safe: episodes finished are skipped on
  restart; an unfinished attempt is simply redone under a new attempt id.

--limits harness: tool outputs cut as the scorer cuts them (5,000 chars per command, 150 lines / 10,000 chars per
read). --limits full: the teacher's whole output (what the teacher actually saw when it wrote its next step).
"""
import argparse
import asyncio
import contextvars
import json
import os
import re
import secrets
import sys
import threading
import time
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

os.environ["REQUEST_LOGGER_AUTO"] = "0"  # stage B installs its own (tagged) logger; no notebook-wide one
HERE = Path(__file__).resolve().parent
for p in (HERE, HERE.parent):  # request_logger.py, render_traces.py (scripts/ locally; same folder on Kaggle)
    sys.path.insert(0, str(p))

EPISODE = contextvars.ContextVar("stage_b_episode", default=None)
ATTEMPT = uuid.uuid4().hex[:12]
REPLAYS = {}  # index -> Replay, read by the HTTP server thread
STATS = {"tokenize_checked": 0, "tokenize_exact": 0, "tokenize_off": 0, "tokenize_errors": 0}

# ---------------------------------------------------------------------------------------------------------------
# Teacher outputs -> what the fake sandbox returns
# ---------------------------------------------------------------------------------------------------------------
OH_EXIT = re.compile(r"\[The command completed with exit code (-?\d+)\.\]")
OH_TRAILER = re.compile(r"(?:\n?\[(?:The command completed with exit code -?\d+\.|Current working directory: [^\n]*|"
                        r"Python interpreter: [^\n]*|Command finished with exit code -?\d+)\])+\s*$")
OH_NO_OUTPUT = "[The command has no new output after"
OH_VIEW = re.compile(r"^Here's the result of running `cat -n` on (?:a snippet of )?(\S+?):\n")
OH_EDITED = re.compile(r"^The file (\S+) has been edited\. Here's the result of running `cat -n` on a snippet of "
                       r"\S+?:\n")
OH_REVIEW = re.compile(r"\nReview the changes and make sure they are as expected\..*$", re.S)
OH_DIR = re.compile(r"^Here's the files and directories up to \d+ levels deep in \S+?, excluding hidden items:\n")
NUMBERED = re.compile(r"^ *(\d+)\t(.*)$")
STDERR_HINT = re.compile(r"Traceback \(most recent call last\)|^(?:bash|/bin/sh|sh|ls|cat|grep|find|sed|head|tail|cd"
                         r"|python3?): .*(?:No such file|not found|cannot|Permission denied)|command not found", re.M)


class Unrepresentable(Exception):
    """The teacher saw something our harness would never show for this call (episode is skipped)."""


OBSERVATION = re.compile(r"^OBSERVATION:\n")  # some OpenHands runs prefix every tool output with this line


def split_run_output(call):
    """(output text, exit code, timed out) from a teacher's run_command record (OpenHands or mini-swe-agent)."""
    out = call.get("output")
    out = OBSERVATION.sub("", "" if out is None else str(out))
    code = call.get("exit_code")
    if out.lstrip().startswith("{") and '"returncode"' in out[:200]:  # mini-swe-agent: {"returncode": N, "output": ...}
        try:
            d = json.loads(out)
            return str(d.get("output") or ""), int(d.get("returncode") or 0), False
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
    if OH_NO_OUTPUT in out:
        return out.split(OH_NO_OUTPUT)[0].rstrip("\n"), None, True
    m = OH_EXIT.findall(out)
    if m:
        code = int(m[-1])
    out = OH_TRAILER.sub("", out)
    if call.get("converted_from") == "view_dir":  # OpenHands directory view -> plain path list (our `find`)
        out = OH_DIR.sub("", out)
        out = "\n".join(l.rstrip("/") for l in out.splitlines() if l.startswith("/"))
    return out, (0 if code is None else int(code)), False


def numbered_lines(body):
    """{line number: text} from `cat -n` output; stops at the first line that is not numbered (clip notes)."""
    lines, clipped = {}, False
    for raw in body.split("\n"):
        m = NUMBERED.match(raw)
        if not m:
            if raw.strip():
                clipped = True
            continue
        lines[int(m.group(1))] = m.group(2)
    return lines, clipped


def norm_path(fp):
    """The path our file tools would use; paths they refuse (outside /workspace, e.g. /tmp) cannot be replayed."""
    try:
        from swegemma.tools.workspace import _resolve_workspace_path
    except ImportError:  # CPU check notebook without the harness: same rule (relative to /workspace, never outside)
        def _resolve_workspace_path(fp, allow_root=False):
            rel = "" if fp == "/workspace" else fp[len("/workspace/"):] if fp.startswith("/workspace/") else fp
            if rel.startswith("/"):
                raise ValueError(f"Path traversal detected: '{fp}' escapes workspace root.")
            full = os.path.normpath(os.path.join("/workspace", rel))
            if not (full == "/workspace" or full.startswith("/workspace/")) or (not allow_root and full == "/workspace"):
                raise ValueError(f"Path traversal detected: '{fp}' escapes workspace root.")
            return full
    try:
        return str(_resolve_workspace_path(fp, allow_root=False))
    except ValueError as e:
        raise Unrepresentable(f"file tool path refused by our harness: {e}") from None


def file_sizes(ep):
    """Best known line count per file: whole-file views give it exactly; otherwise the largest line number seen."""
    size = {}
    for s in ep["steps"]:
        for c in s["calls"]:
            if c["tool"] not in ("read_file", "edit_file"):
                continue
            out = str(c.get("output") or "")
            m = re.search(r"number of lines in the file: `(\d+)`", out)
            if m:
                size[c["args"].get("filepath")] = max(size.get(c["args"].get("filepath"), 0), int(m.group(1)))
            nums, _ = numbered_lines(out)
            if nums:
                fp = c["args"].get("filepath")
                size[fp] = max(size.get(fp, 0), max(nums))
    return size


def prepare_call(c, ep, sizes):
    """What the fake sandbox must hand to the real tool for this call."""
    tool, a = c["tool"], c["args"]
    out = OBSERVATION.sub("", "" if c.get("output") is None else str(c["output"]))
    if tool == "run_command":
        text, code, timed_out = split_run_output(c)
        if timed_out:
            return {"tool": tool, "command": a["command"], "stdout": text, "stderr": "", "exit_code": -1,
                    "timed_out": True}
        if code != 0 and "2>&1" not in a["command"] and STDERR_HINT.search(text):
            stdout, stderr = "", text
        else:
            stdout, stderr = text, ""
        return {"tool": tool, "command": a["command"], "stdout": stdout, "stderr": stderr, "exit_code": code,
                "timed_out": False}
    if tool == "read_file":
        if a.get("end_line") == -1:
            a.pop("end_line")
        if "does not exist" in out[:300]:
            return {"tool": tool, "path": norm_path(a["filepath"]), "content": None}
        if out.startswith("ERROR"):
            raise Unrepresentable("read_file error: " + out[:80])
        m = OH_VIEW.match(out)
        if not m:
            raise Unrepresentable("read_file output not a cat -n view: " + out[:200])
        nums, clipped = numbered_lines(out[m.end():])
        if not nums:
            raise Unrepresentable("empty view")
        start, end = a.get("start_line"), a.get("end_line")
        lo, hi = min(nums), max(nums)
        if clipped and (start is None or end is None or end > hi):
            raise Unrepresentable("teacher view was clipped")
        total = max(sizes.get(a["filepath"], hi), hi)
        lines = [nums.get(i, "") for i in range(1, total + 1)]
        return {"tool": tool, "path": norm_path(a["filepath"]), "content": "\n".join(lines) + "\n",
                "known": (lo, hi)}
    if tool == "edit_file":
        path = norm_path(a["filepath"])
        old, new = a.get("old_string", ""), a.get("new_string", "")
        if "does not exist" in out[:300]:
            return {"tool": tool, "path": path, "content": None}
        if "did not appear verbatim" in out:
            return {"tool": tool, "path": path, "content": "\n"}
        m = re.search(r"Multiple occurrences of old_str .*? in lines \[([\d, ]+)\]", out, re.S)
        if m:
            n = len(m.group(1).split(","))
            return {"tool": tool, "path": path, "content": (old + "\n") * n}
        m = OH_EDITED.match(out)
        if not m:
            raise Unrepresentable("edit_file output: " + out[:80])
        nums, _ = numbered_lines(OH_REVIEW.sub("", out[m.end():]))
        content = None
        if nums and new:
            first = min(nums)
            snippet = "\n".join(nums.get(i, "") for i in range(first, max(nums) + 1))
            if snippet.count(new) >= 1:
                pre = snippet.replace(new, old, 1)
                cand = "\n" * (first - 1) + pre + "\n"
                if cand.count(old) == 1:
                    content = cand
        if content is None:  # deletion or snippet without the new text: the edit alone, at the right line if known
            first = min(nums) if nums else 1
            content = "\n" * max(first - 1, 0) + old + "\n"
        return {"tool": tool, "path": path, "content": content}
    if tool == "write_file":
        norm_path(a["filepath"])
        if out and not out.startswith("File created successfully"):
            raise Unrepresentable("write_file output: " + out[:80])
        return {"tool": tool}
    if tool in ("submit_patch", "get_status"):
        return {"tool": tool}
    raise Unrepresentable("unknown tool " + tool)


# ---------------------------------------------------------------------------------------------------------------
# One episode's state, shared by the fake model (HTTP thread) and the fake sandbox (tool calls)
# ---------------------------------------------------------------------------------------------------------------
NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]{7,}")


def shown_text(prep, call, harness):
    """What our tool shows the model for this call (before JSON wrapping), and what the teacher saw."""
    if prep["tool"] == "run_command":
        cut = harness.max_stdout_chars
        shown = prep["stdout"][:cut] + "\n" + prep["stderr"][:cut] if cut else prep["stdout"] + prep["stderr"]
        return shown, prep["stdout"] + "\n" + prep["stderr"]
    if prep["tool"] == "read_file" and prep.get("content") is not None:
        lines = prep["content"].split("\n")
        a = call["args"]
        start = max(int(a.get("start_line") or 1), 1)
        end = min(int(a.get("end_line") or len(lines)), len(lines))
        if harness.max_file_lines:
            end = min(end, start + harness.max_file_lines - 1)
        shown = "\n".join(lines[start - 1:end])
        if harness.max_file_chars:
            shown = shown[:harness.max_file_chars]
        return shown, "\n".join(lines[start - 1:])
    out = "" if call.get("output") is None else str(call["output"])
    return out, out


def uses_cut_output(ep, steps, harness):
    """True if the teacher's next two steps use a name it could only have read in output our limits would cut."""
    seen = set(NAME.findall((ep.get("problem_statement") or "") + (ep.get("workspace_tree") or "")))
    for i, (s, preps) in enumerate(zip(ep["steps"], steps)):
        seen |= set(NAME.findall(s.get("thinking", "") + s.get("text", "")))
        for c, prep in zip(s["calls"], preps):
            seen |= set(NAME.findall(json.dumps(c["args"])))
            shown, full = shown_text(prep, c, harness)
            only_cut = set(NAME.findall(full)) - set(NAME.findall(shown)) - seen
            if only_cut:
                nxt = " ".join(t.get("thinking", "") + t.get("text", "") + json.dumps([x["args"] for x in t["calls"]])
                               for t in ep["steps"][i + 1:i + 3])
                if only_cut & set(NAME.findall(nxt)):
                    return True
            seen |= set(NAME.findall(shown))
    return False


class Replay:
    def __init__(self, ep, harness=None, counter=None, max_output_tokens=None):
        self.ep = ep
        sizes = file_sizes(ep)
        self.steps = [[prepare_call(c, ep, sizes) for c in s["calls"]] for s in ep["steps"]]
        if not ep.get("submitted") or not any(c["tool"] == "submit_patch" for c in ep["steps"][-1]["calls"]):
            raise Unrepresentable("episode does not end with submit_patch")
        if harness is not None and harness.max_stdout_chars and uses_cut_output(ep, self.steps, harness):
            raise Unrepresentable("teacher used output our limits would cut")
        if counter is not None and max_output_tokens:
            for s in ep["steps"]:
                gen = counter.n(s.get("thinking") or s.get("text")) + sum(
                    counter.n(c["tool"] + json.dumps(c["args"])) for c in s["calls"])
                if gen > max_output_tokens:
                    raise Unrepresentable(f"a step writes {gen} tokens > max_output_tokens {max_output_tokens}")
        self.next_step = 0
        self.final_sent = False
        self.pending = []
        self.lock = threading.Lock()
        self.problems = []
        self.agent_calls = self.summaries = 0
        self.max_prompt = 0
        self.over_max_output = 0

    def problem(self, msg):
        with self.lock:
            if len(self.problems) < 20:
                self.problems.append(msg)

    def next_message(self):
        with self.lock:
            if self.pending:
                self.problems.append(f"step {self.next_step}: {len(self.pending)} tool call(s) never executed")
                self.pending = []
            if self.next_step < len(self.ep["steps"]):
                s = self.ep["steps"][self.next_step]
                prepared = self.steps[self.next_step]
                self.next_step += 1
                calls = []
                for c, prep in zip(s["calls"], prepared):
                    cid = "chatcmpl-tool-" + secrets.token_hex(8)
                    calls.append({"id": cid, "type": "function",
                                  "function": {"name": c["tool"], "arguments": json.dumps(c["args"])}})
                    if prep["tool"] != "get_status":  # get_status never touches the sandbox
                        self.pending.append(prep)
                # Gemma's turns before a tool call are thinking only (pilot: no visible text in 13,557 calls): the
                # teacher's visible text is used as its thinking when it did not think, and dropped otherwise
                msg = {"role": "assistant", "content": None,
                       "reasoning_content": s.get("thinking") or s.get("text") or None, "tool_calls": calls}
                return msg, "tool_calls"
            if not self.final_sent:
                self.final_sent = True
                return {"role": "assistant", "content": self.ep.get("final_text") or "Patch submitted.",
                        "reasoning_content": None, "tool_calls": None}, "stop"
            self.problems.append("model called again after the final message")
            return {"role": "assistant", "content": self.ep.get("final_text") or "Patch submitted.",
                    "reasoning_content": None, "tool_calls": None}, "stop"

    def take(self, pred, what):
        with self.lock:
            for i, p in enumerate(self.pending):
                if pred(p):
                    return self.pending.pop(i)
        self.problems.append(f"step {self.next_step}: no recorded call for {what}")
        return None


class FakeSandbox:
    """Stands in for the subprocess/docker sandbox under the harness's real tools."""

    def __init__(self, rep):
        self.rep = rep

    def exec(self, sandbox_id, command, timeout=None):
        from swegemma.sandbox.base import ExecResult
        ok = lambda out="": ExecResult(exit_code=0, stdout=out, stderr="")  # noqa: E731
        with self.rep.lock:  # the teacher's own commands first (one may itself start with `mkdir -p`)
            is_teacher_cmd = any(p["tool"] == "run_command" and p["command"] == command for p in self.rep.pending)
        if not is_teacher_cmd:
            if command == "cd /workspace && git add -N .":
                return ok()
            if command.startswith("mkdir -p "):  # write_file creating the parent folder
                self.rep.take(lambda p: p["tool"] == "write_file", "write_file")
                return ok()
            if command.startswith("cd /workspace && (git diff --binary _swegemma_baseline"):  # submit_patch
                self.rep.take(lambda p: p["tool"] == "submit_patch", "submit_patch")
                return ok(self.rep.ep.get("model_patch") or "")
        p = self.rep.take(lambda p: p["tool"] == "run_command" and p["command"] == command, "command " + command[:60])
        if p is None:
            return ExecResult(exit_code=1, stdout="", stderr="stage B: no recorded output")
        if p["timed_out"]:
            return ExecResult(exit_code=-1, stdout=p["stdout"], stderr="", timed_out=True)
        return ExecResult(exit_code=p["exit_code"], stdout=p["stdout"], stderr=p["stderr"])

    def copy_from(self, sandbox_id, container_path, host_path):
        p = self.rep.take(lambda p: p["tool"] in ("read_file", "edit_file") and p["path"] == str(container_path),
                          "file " + str(container_path))
        if p is not None and p["content"] is not None:
            Path(host_path).write_text(p["content"], encoding="utf-8")

    def copy_to(self, sandbox_id, host_path, container_path):
        pass  # write_file / edit_file push the file back; nothing to keep


# ---------------------------------------------------------------------------------------------------------------
# The fake vLLM
# ---------------------------------------------------------------------------------------------------------------
class Counter:
    def __init__(self, tok_dir):
        from render_traces import load_template
        from tokenizers import Tokenizer
        self.tmpl, self.bos = load_template(tok_dir)
        self.tok = Tokenizer.from_file(str(Path(tok_dir) / "tokenizer.json"))

    def prompt_tokens(self, body):
        from render_traces import render, request_to_template_inputs
        rec = {"request": {"messages": body["messages"], "tools": body.get("tools"),
                           "kwargs": {"chat_template_kwargs": body.get("chat_template_kwargs")}}}
        msgs, tools, think = request_to_template_inputs(rec)
        text = render(self.tmpl, self.bos, msgs, tools, enable_thinking=think)
        return len(self.tok.encode(text, add_special_tokens=False).ids)

    def n(self, text):
        return len(self.tok.encode(text or "", add_special_tokens=False).ids)


def make_handler(args, counter, stats):
    vllm = args.vllm_base.rstrip("/") if args.vllm_base else None

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, obj):
            data = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            m = re.search(r"stage-b-ep(\d+)$", body.get("model", ""))  # the episode is named in the model id
            rep = REPLAYS.get(int(m.group(1))) if m else None
            if rep is None:
                print("unknown episode:", body.get("model"), "live:", sorted(REPLAYS)[:10], flush=True)
                return self._send(404, {"error": "unknown episode"})
            if not body.get("tools"):  # ADK's compaction summary: the real model writes it
                rep.summaries += 1
                if vllm is None:
                    text = "(dry run summary) The agent is working on the task; see the retained events."
                    return self._send(200, {"id": "sum", "object": "chat.completion", "created": int(time.time()),
                                            "model": body["model"], "choices": [{"index": 0, "finish_reason": "stop",
                                            "message": {"role": "assistant", "content": text}}],
                                            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}})
                body = dict(body, model=args.vllm_model)
                req = urllib.request.Request(vllm + "/chat/completions", data=json.dumps(body).encode(),
                                             headers={"Content-Type": "application/json"})
                try:
                    with urllib.request.urlopen(req, timeout=900) as r:
                        return self._send(200, json.loads(r.read()))
                except Exception as e:  # noqa: BLE001
                    rep.problem(f"summary call failed: {e!r}"[:200])
                    return self._send(500, {"error": repr(e)})
            prompt = counter.prompt_tokens(body)
            if args.check_tokenize and stats["tokenize_checked"] < args.check_tokenize and vllm:
                stats["tokenize_checked"] += 1
                try:
                    root = vllm[:-3] if vllm.endswith("/v1") else vllm
                    tb = {"model": args.vllm_model, "messages": body["messages"], "tools": body.get("tools"),
                          "chat_template_kwargs": body.get("chat_template_kwargs"), "add_generation_prompt": True}
                    req = urllib.request.Request(root + "/tokenize", data=json.dumps(tb).encode(),
                                                 headers={"Content-Type": "application/json"})
                    with urllib.request.urlopen(req, timeout=120) as r:
                        want = len(json.loads(r.read())["tokens"])
                    stats["tokenize_exact" if want == prompt else "tokenize_off"] += 1
                    if want != prompt:
                        print(f"tokenize check: vLLM {want}, ours {prompt}", flush=True)
                except Exception as e:  # noqa: BLE001
                    stats["tokenize_errors"] += 1
                    print("tokenize check failed:", repr(e)[:200], flush=True)
            msg, finish = rep.next_message()
            gen = counter.n(msg.get("reasoning_content")) + counter.n(msg.get("content")) + sum(
                counter.n(c["function"]["name"] + c["function"]["arguments"]) for c in msg.get("tool_calls") or [])
            with rep.lock:
                rep.agent_calls += 1
                rep.max_prompt = max(rep.max_prompt, prompt)
                if gen > args.max_output_tokens:
                    rep.over_max_output += 1
            self._send(200, {"id": "chatcmpl-" + secrets.token_hex(8), "object": "chat.completion",
                             "created": int(time.time()), "model": body["model"],
                             "choices": [{"index": 0, "message": msg, "finish_reason": finish}],
                             "usage": {"prompt_tokens": prompt, "completion_tokens": gen,
                                       "total_tokens": prompt + gen}})

    return Handler


# ---------------------------------------------------------------------------------------------------------------
# Running one episode through the harness (mirrors swegemma.harness.agent_runner.run_agent_sandbox)
# ---------------------------------------------------------------------------------------------------------------
def build_eval_config(submission, out):
    import yaml
    from google.adk.agents.context_cache_config import ContextCacheConfig
    from google.adk.apps._configs import EventsCompactionConfig
    from adk_submission.registry import ModelRegistry
    from swegemma.config import EvalConfig, build_submission_limits
    raw = yaml.safe_load((Path(submission) / "eval_config.yaml").read_text()) if (
        Path(submission) / "eval_config.yaml").exists() else {}
    sec = (raw or {}).get("evaluation", raw or {})
    limits, gen = build_submission_limits()
    nowhere = Path(out) / "_none"
    return EvalConfig(
        tasks_path=nowhere / "tasks.jsonl", snapshots_dir=nowhere, results_dir=Path(out), submission_dir=Path(submission),
        models=ModelRegistry(), graph_dir=str(nowhere / "graphs"), embeddings_dir=str(nowhere / "embeddings"),
        limits=limits, generation_constraints=gen,
        context_cache_config=ContextCacheConfig(min_tokens=2048, ttl_seconds=1800, cache_intervals=10),
        events_compaction_config=EventsCompactionConfig(compaction_interval=5, overlap_size=2, token_threshold=14336,
                                                        event_retention_size=5),
        timeout_seconds=int(sec.get("timeout_seconds", 300)), max_tool_calls=sec.get("max_tool_calls"),
        max_time_minutes=float(sec.get("max_time_minutes", 5.0)), max_turns=sec.get("max_turns"),
    )


async def run_episode(idx, rep, cfg, args, port, harness):
    from adk_eval_core.plugins import ModelRetryPlugin
    from adk_submission import compile_submission
    from adk_submission.registry import ModelRegistry
    from google.adk.apps.app import App
    from google.adk.models.lite_llm import LiteLlm
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types as genai_types
    from swegemma.budget import EvaluationBudget
    from swegemma.context import SwegemmaContext
    from swegemma.harness.agent_runner import ToolErrorPlugin, _extract_declared_tools, build_agent_prompt

    ep = rep.ep
    EPISODE.set(ep["id"])
    task = SimpleNamespace(instance_id=ep["instance_id"], repo=ep["repo"], problem_statement=ep["problem_statement"],
                           hints_text="", base_commit=ep.get("base_commit"), test_files=())
    # no wall clock in a replay: time limits off for the tools; the prompt still states the real budget
    ctx = SwegemmaContext(docker_manager=FakeSandbox(rep), container_id="replay", task=task,
                          budget=EvaluationBudget(time_minutes=None, tool_calls=cfg.budget.tool_calls,
                                                  turns=cfg.budget.turns), harness=harness,
                          graph_dir=cfg.graph_dir, embeddings_dir=cfg.embeddings_dir)
    models = ModelRegistry()
    alias = args.model_alias
    # one endpoint for all episodes; the model id tells the fake server which episode is asking (LiteLLM reuses
    # HTTP clients across api_base paths, so the path cannot carry it)
    models.register(alias, LiteLlm(model=f"openai/stage-b-ep{idx}", api_base=f"http://127.0.0.1:{port}/v1",
                                   api_key="EMPTY"))
    agent = compile_submission(submission_dir=cfg.submission_dir, tool_registry=ctx.create_tools(),
                               model_registry=models, limits=cfg.limits, generation_constraints=cfg.generation_constraints,
                               script_timeout=cfg.harness.command_timeout_seconds)
    # a fresh compaction config per episode: ADK stores the summarizer (with this episode's model) on it at the
    # first compaction, and a shared one would send later episodes' summaries to that first episode
    app = App(name="swegemma_eval", root_agent=agent, plugins=[ModelRetryPlugin(), ToolErrorPlugin()],
              context_cache_config=cfg.context_cache_config,
              events_compaction_config=cfg.events_compaction_config.model_copy(update={"summarizer": None}))
    service = InMemorySessionService()
    runner = Runner(app=app, session_service=service)
    session = await service.create_session(app_name="swegemma_eval", user_id="eval_user",
                                           state={"problem_description": task.problem_statement})
    prompt = build_agent_prompt(task=task, config=cfg, workspace_tree=ep.get("workspace_tree") or "",
                                enable_sandbox_testing=True, declared_tools=_extract_declared_tools(agent))
    message = genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])
    ctx.start_agent_session()
    nudges = 0
    while True:
        tool_call_seen = False
        async for event in runner.run_async(user_id="eval_user", session_id=session.id, new_message=message):
            ctx.handle_adk_event(event, agent_name=agent.name)
            parts = getattr(getattr(event, "content", None), "parts", None) or []
            if any(getattr(p, "function_call", None) for p in parts):
                tool_call_seen = True
            if event.is_final_response() and ctx.patch_submitted and any(
                    getattr(p, "text", None) and not getattr(p, "thought", False) for p in parts):
                break
        if ctx.patch_submitted:
            break
        if (ctx.budget.tool_calls is not None and ctx.tool_calls_used >= ctx.budget.tool_calls) or nudges >= 3:
            rep.problem("ended without submitting")
            break
        nudges = 0 if tool_call_seen else nudges + 1
        rep.problem("harness nudge needed")
        message = genai_types.Content(role="user", parts=[genai_types.Part(
            text="Please continue your work using the available tools, or call submit_patch when you have completed "
                 "and verified your changes.")])
    if rep.next_step < len(rep.ep["steps"]):
        rep.problem(f"only {rep.next_step} of {len(rep.ep['steps'])} steps replayed")
    if not rep.final_sent:
        rep.problem("final message not sent")
    return ctx


# ---------------------------------------------------------------------------------------------------------------
def load_candidates(selection, dirs, splits):
    """Candidate episodes in selection order (the first ones are the v1 picks, then reserves), with quotas."""
    sel = json.loads(Path(selection).read_text())
    rows = []
    for s in splits:
        rows += [dict(r, split=s) for r in (sel[f"{s}_candidates"] if f"{s}_candidates" in sel else sel[s])]
    files = {}
    for d in dirs:
        for f in Path(d).rglob("episodes_*.jsonl"):
            files.setdefault(f.name, f)
    want = {}
    for r in rows:
        want.setdefault(r["file"], {})[r["line"]] = r
    eps = {}
    for name, lines in want.items():
        if name not in files:
            continue
        with open(files[name]) as fh:
            for n, line in enumerate(fh):
                if n in lines:
                    ep = json.loads(line)
                    if ep["id"] == lines[n]["id"]:
                        eps[ep["id"]] = ep
    found = [(r, eps[r["id"]]) for r in rows if r["id"] in eps]
    return found, len(rows) - len(found), sel.get("quotas")


async def main_async(args):
    import litellm
    from adk_submission.resolvers.generation import install_litellm_reasoning_patch
    from request_logger import install_request_logger
    from swegemma.budget import HarnessLimits
    litellm.drop_params = True
    install_litellm_reasoning_patch()
    print("python", sys.version.split()[0], "attempt", ATTEMPT, flush=True)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    status_path = out / "status.jsonl"
    prev_rows = []
    for p in [status_path, *map(Path, args.resume_from or [])]:
        if p.is_file():
            prev_rows += [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    ok_ids = {r["id"] for r in prev_rows if r["status"] == "ok"}
    bad_ids = {r["id"] for r in prev_rows if r["status"] == "bad"}
    install_request_logger(out / f"requests_{ATTEMPT}.jsonl",
                           tag=lambda: {"episode_id": EPISODE.get(), "attempt": ATTEMPT})

    cfg = build_eval_config(args.submission, out)
    harness = cfg.harness if args.limits == "harness" else HarnessLimits(
        command_timeout_seconds=cfg.harness.command_timeout_seconds, max_stdout_chars=None, max_file_lines=None,
        max_file_chars=None)
    counter = Counter(args.tokenizer_dir)
    cands, missing, quotas = load_candidates(args.selection, args.episodes, args.split)
    quotas = {s: {c: max(1, round(q * args.quota_scale)) if q else 0 for c, q in quotas[s].items()} for s in args.split}
    print(f"candidates found {len(cands)}, missing {missing}; quotas {quotas}; already ok {len(ok_ids)}", flush=True)

    # 1. checks that need no model (cheap): can our harness show exactly what the teacher saw?
    usable, skipped = {}, {}
    filled = {(s, c): 0 for s in quotas for c in quotas[s]}
    for r, ep in cands:
        key = (r["split"], r["category"] or "other")
        if ep["id"] in ok_ids:
            filled[key] = filled.get(key, 0) + 1
            continue
        if ep["id"] in bad_ids:
            continue
        try:
            rep = Replay(ep, harness if args.limits == "harness" else None, counter, args.max_output_tokens)
        except Exception as e:  # noqa: BLE001  (Unrepresentable, or anything unexpected: skip, never crash the run)
            reason = re.sub(r"\d+", "N", str(e) if isinstance(e, Unrepresentable) else f"error {e!r}")[:60]
            skipped[reason] = skipped.get(reason, 0) + 1
            continue
        usable.setdefault(key, []).append((r, ep, rep))
    print("skipped before replay:", json.dumps(skipped, indent=1), flush=True)
    print("usable per split/category:", {f"{k[0]}/{k[1]}": len(v) for k, v in usable.items()}, flush=True)

    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(args, counter, STATS))
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    sem = asyncio.Semaphore(args.concurrency)
    lock = asyncio.Lock()
    totals = {"ok": 0, "bad": 0, "summaries": 0}
    t0 = time.time()
    seq = iter(range(10 ** 9))

    async def one(r, ep, rep, n_total):
        idx = next(seq)
        async with sem:
            row = {"id": ep["id"], "instance_id": ep["instance_id"], "repo": ep["repo"], "split": r["split"],
                   "category": r["category"], "teacher": ep["teacher"], "attempt": ATTEMPT}
            REPLAYS[idx] = rep
            try:
                await asyncio.wait_for(run_episode(idx, rep, cfg, args, port, harness), timeout=args.episode_timeout)
            except Exception as e:  # noqa: BLE001
                rep.problem(f"exception: {e!r}"[:300])
            REPLAYS.pop(idx, None)
            row.update(status="bad" if rep.problems else "ok", problems=rep.problems, agent_calls=rep.agent_calls,
                       summaries=rep.summaries, max_prompt_tokens=rep.max_prompt)
            async with lock:
                totals[row["status"]] += 1
                totals["summaries"] += rep.summaries
                if row["status"] == "ok":
                    filled[(r["split"], r["category"] or "other")] += 1
                with open(status_path, "a") as f:
                    f.write(json.dumps(row) + "\n")
                n = totals["ok"] + totals["bad"]
                if n % args.print_every == 0 or n == n_total:
                    print(f"[{time.time() - t0:7.0f}s] {n}/{n_total} {totals} tokenize-check {STATS}", flush=True)

    # 2. replay until every quota is filled (a failed replay is replaced by the next usable reserve)
    for round_no in range(1, 6):
        batch = []
        for key, q in (((s, c), q) for s in quotas for c, q in quotas[s].items()):
            need = q - filled.get(key, 0)
            while need > 0 and usable.get(key):
                batch.append(usable[key].pop(0))
                need -= 1
        if not batch:
            break
        print(f"round {round_no}: replaying {len(batch)} episodes", flush=True)
        await asyncio.gather(*(one(r, ep, rep, len(batch)) for r, ep, rep in batch))
    server.shutdown()
    short = {f"{s}/{c}": quotas[s][c] - filled.get((s, c), 0) for s in quotas for c in quotas[s]
             if filled.get((s, c), 0) < quotas[s][c]}
    (out / f"run_{ATTEMPT}.json").write_text(json.dumps({"attempt": ATTEMPT, "python": sys.version.split()[0],
                                                         "totals": totals, "tokenize_check": STATS,
                                                         "skipped_before_replay": skipped, "shortfall": short,
                                                         "quotas": quotas, "limits": args.limits}, indent=1))
    print("DONE", totals, "tokenize-check", STATS, "quota shortfall", short or "none", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selection", required=True)
    ap.add_argument("--episodes", nargs="+", required=True)
    ap.add_argument("--submission", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tokenizer-dir", required=True)
    ap.add_argument("--model-alias", default=None, help="model name in agent.yaml (read from it by default)")
    ap.add_argument("--vllm-base", default=None, help="real vLLM for compaction summaries, e.g. http://127.0.0.1:8000/v1")
    ap.add_argument("--vllm-model", default=None, help="served model id at --vllm-base")
    ap.add_argument("--fake-summarizer", action="store_true", help="dry run: canned summary instead of vLLM")
    ap.add_argument("--check-tokenize", type=int, default=0, help="compare our prompt token count with vLLM /tokenize "
                    "for the first N agent calls")
    ap.add_argument("--limits", choices=("harness", "full"), default="harness")
    ap.add_argument("--split", nargs="+", default=["train", "val"])
    ap.add_argument("--quota-scale", type=float, default=1.0, help="e.g. 0.05 for a ~28-episode trial")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--episode-timeout", type=float, default=3600)
    ap.add_argument("--max-output-tokens", type=int, default=4096)
    ap.add_argument("--print-every", type=int, default=10)
    ap.add_argument("--resume-from", nargs="*", help="status.jsonl files of earlier runs: their episodes are skipped")
    args = ap.parse_args()
    if not args.vllm_base and not args.fake_summarizer:
        ap.error("give --vllm-base (real summaries) or --fake-summarizer (dry run)")
    if args.model_alias is None:
        import yaml
        args.model_alias = yaml.safe_load((Path(args.submission) / "agent.yaml").read_text().replace("!include", ""))[
            "model"]
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
