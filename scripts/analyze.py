"""Summarize an evaluation results directory (task_results.jsonl + traces/*.json, ATIF-v1.7).

Usage:
    python3 scripts/analyze.py results/1a_20261004_231500 [results/1b_... ...]

Per task: outcome bucket, duration, model calls, output tokens, peak prompt tokens, compaction events (detected as
prompt-token drops; they are not separate trace events), nudges, repeated identical commands, tool calls by name,
and for helper agents (agent_tool calls) how often the reply started with the expected format.
"""

import json
import sys
from collections import Counter
from pathlib import Path

NUDGE_PREFIXES = ("Please continue your work", "Your previous response reached the token limit")
HELPER_FORMATS = {"reader": "LOCATION:", "executor": "CHANGED:", "verifier": "VERDICT:"}
TEST_PATHS = ("tests/", "test_", "conftest.py", "pytest.ini")


def bucket(task):
    """Coarse failure bucket from the harness result."""
    error = (task.get("error") or "").lower()
    patch = task.get("agent_patch") or ""
    if task.get("resolved"):
        return "resolved"
    if "context" in error and ("window" in error or "length" in error):
        return "overflow"
    if "not found" in error and "tool" in error:
        return "unknown tool"
    if not patch.strip():
        return "timeout, no patch" if "timeout" in error or "timed out" in error else "no patch"
    changed = [line.split(" b/")[-1] for line in patch.splitlines() if line.startswith("diff --git")]
    if any(any(t in f for t in TEST_PATHS) for f in changed):
        return "edited tests"
    return "wrong fix"


def trace_stats(trace):
    steps = trace.get("steps", [])
    stats = Counter()
    tools = Counter()
    commands = Counter()
    helper_ok = Counter()
    helper_total = Counter()
    last_prompt = None
    peak_prompt = 0
    for step in steps:
        message = str(step.get("message") or "")
        if step.get("source") != "agent" and message.startswith(NUDGE_PREFIXES):
            stats["nudges"] += 1
        metrics = step.get("metrics") or {}
        prompt = metrics.get("prompt_tokens")
        if prompt:
            stats["model_calls"] += 1
            stats["output_tokens"] += metrics.get("completion_tokens") or 0
            peak_prompt = max(peak_prompt, prompt)
            # Compaction replaces old events with a summary: the next prompt is much smaller than the last one.
            if last_prompt and prompt < 0.7 * last_prompt:
                stats["compactions"] += 1
            last_prompt = prompt
        for call in step.get("tool_calls") or []:
            name = call.get("function_name")
            tools[name] += 1
            if name == "run_command":
                commands[(call.get("arguments") or {}).get("command", "")] += 1
            if name in HELPER_FORMATS:
                helper_total[name] += 1
                reply = str((step.get("observation") or {}).get("content", ""))
                if HELPER_FORMATS[name] in reply[:200]:
                    helper_ok[name] += 1
    stats["peak_prompt"] = peak_prompt
    stats["repeated_cmds"] = sum(n - 1 for n in commands.values() if n > 1)
    helpers = {h: f"{helper_ok[h]}/{helper_total[h]}" for h in helper_total}
    return stats, tools, helpers


def analyze(results_dir):
    results_dir = Path(results_dir)
    tasks = [json.loads(line) for line in (results_dir / "task_results.jsonl").read_text().splitlines() if line]
    print(f"\n## {results_dir.name}: {sum(t.get('resolved', False) for t in tasks)}/{len(tasks)} resolved")
    header = (f"{'task':<16} {'outcome':<18} {'sec':>5} {'calls':>5} {'out_tok':>7} {'peak_in':>7} "
              f"{'compact':>7} {'nudge':>5} {'repeat':>6}  tools / helpers")
    print(header)
    print("-" * len(header))
    for task in tasks:
        task_id = task.get("instance_id") or task.get("task_id")
        trace_file = results_dir / "traces" / f"trace_{task_id}.json"
        trace = json.loads(trace_file.read_text()) if trace_file.exists() else {}
        stats, tools, helpers = trace_stats(trace)
        tool_list = ", ".join(f"{name}×{n}" for name, n in tools.most_common())
        helper_list = (" | format ok " + ", ".join(f"{h} {v}" for h, v in helpers.items())) if helpers else ""
        print(f"{task_id:<16} {bucket(task):<18} {task.get('duration_seconds', 0):>5.0f} {stats['model_calls']:>5} "
              f"{stats['output_tokens']:>7} {stats['peak_prompt']:>7} {stats['compactions']:>7} "
              f"{stats['nudges']:>5} {stats['repeated_cmds']:>6}  {tool_list}{helper_list}")
        if task.get("error"):
            print(f"{'':<16} error: {task['error'][:150]}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for d in sys.argv[1:]:
        analyze(d)
