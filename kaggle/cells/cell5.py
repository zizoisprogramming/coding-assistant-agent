# 5. Comparison table + results.zip (download it from the Output panel), then STOP THE SESSION.
import json
from collections import Counter


NUDGE_PREFIXES = ("Please continue your work", "Your previous response reached the token limit")


HELPER_FORMATS = {"reader": "LOCATION:", "executor": "CHANGED:", "verifier": "VERDICT:"}


TEST_PATHS = ("tests/", "test_", "conftest.py", "pytest.ini")


def bucket(task, patch=""):
    """Coarse failure bucket from the harness result (patch text comes from patches/<id>.patch)."""
    error = (task.get("error") or "").lower()
    patch = patch or task.get("agent_patch") or ""
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
    last_prompt = {}  # per agent: helpers have their own conversations
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
            # Compaction replaces old events with a summary: the agent's next prompt is much smaller than its last.
            # A helper (agent_tool) starts a fresh conversation on every call, so a new call resets its baseline.
            author = (step.get("extra") or {}).get("author")
            previous = last_prompt.get(author)
            if previous and prompt < 0.7 * previous:
                stats["compactions"] += 1
            last_prompt[author] = prompt
        for call in step.get("tool_calls") or []:
            name = call.get("function_name")
            tools[name] += 1
            if name == "run_command":
                commands[(call.get("arguments") or {}).get("command", "")] += 1
            if name in HELPER_FORMATS:
                last_prompt.pop(name, None)
        # Observations are tagged with the tool that produced them. Helper (agent_tool) replies arrive as
        # {"raw": "<final text>"} in the step whose observation is tagged with the helper's name.
        observation = step.get("observation") or {}
        source = (observation.get("extra") or {}).get("tool_name")
        content = str(observation.get("content", ""))
        if '"status": "error"' in content[:40] or "'status': 'error'" in content[:40] or content.startswith('{"error"'):
            stats["tool_errors"] += 1
        if source in HELPER_FORMATS:
            helper_total[source] += 1
            try:
                reply = json.loads(content).get("raw", content)
            except (ValueError, AttributeError):
                reply = content
            if HELPER_FORMATS[source] in reply[:300]:
                helper_ok[source] += 1
            if "<|tool_call>" in reply:
                stats["broken_calls"] += 1
        if "<|tool_call>" in message:
            stats["broken_calls"] += 1
    stats["peak_prompt"] = peak_prompt
    stats["repeated_cmds"] = sum(n - 1 for n in commands.values() if n > 1)
    helpers = {h: f"{helper_ok[h]}/{helper_total[h]}" for h in helper_total}
    return stats, tools, helpers


def analyze(results_dir):
    results_dir = Path(results_dir)
    tasks = [json.loads(line) for line in (results_dir / "task_results.jsonl").read_text().splitlines() if line]
    print(f"\n## {results_dir.name}: {sum(t.get('resolved', False) for t in tasks)}/{len(tasks)} resolved")
    header = (f"{'task':<16} {'outcome':<18} {'sec':>5} {'calls':>5} {'out_tok':>7} {'peak_in':>7} "
              f"{'compact':>7} {'nudge':>5} {'repeat':>6} {'errors':>6} {'broken':>6}  tools / helpers")
    print(header)
    print("-" * len(header))
    for task in tasks:
        task_id = task.get("instance_id") or task.get("task_id")
        trace_file = results_dir / "traces" / f"trace_{task_id}.json"
        trace = json.loads(trace_file.read_text()) if trace_file.exists() else {}
        stats, tools, helpers = trace_stats(trace)
        patch_file = results_dir / "patches" / f"{task_id}.patch"
        patch = patch_file.read_text() if patch_file.exists() else ""
        tool_list = ", ".join(f"{name}×{n}" for name, n in tools.most_common())
        helper_list = (" | format ok " + ", ".join(f"{h} {v}" for h, v in helpers.items())) if helpers else ""
        print(f"{task_id:<16} {bucket(task, patch):<18} {task.get('duration_seconds', 0):>5.0f} {stats['model_calls']:>5} "
              f"{stats['output_tokens']:>7} {stats['peak_prompt']:>7} {stats['compactions']:>7} "
              f"{stats['nudges']:>5} {stats['repeated_cmds']:>6} {stats['tool_errors']:>6} {stats['broken_calls']:>6}  "
              f"{tool_list}{helper_list}")
        if patch:
            changed = [line.split(" b/")[-1] for line in patch.splitlines() if line.startswith("diff --git")]
            print(f"{'':<16} patch: {', '.join(changed)}")
        if task.get("error"):
            print(f"{'':<16} error: {task['error'][:150]}")


for name in CONFIGS:
    analyze(RESULTS / name)
shutil.make_archive(str(WORKING_DIR / 'results'), 'zip', RESULTS)
print('\nWall clock per config (min):', {k: round(v / 60, 1) for k, v in wall.items()})
print('Wrote /kaggle/working/results.zip')