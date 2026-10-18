"""Stage A of training-data prep: download, filter and normalize teacher runs into "episodes" (no rendering yet).

Runs on Kaggle (CPU session, internet on) so the big downloads never touch the user's connection:

    python stage_a.py --out /kaggle/working/stage_a [--max-files 1] [--resume-from /kaggle/input/<prev output>]

Locally, a dry run on the small sample (data/samples/open_swe_traces_sample.json, no downloads):

    data/venv_train/bin/python scripts/datasets/stage_a.py --sample data/samples/open_swe_traces_sample.json \
        --out /tmp/stage_a_dry --no-trees

What one episode holds: the task (repo, base commit, issue text from the source dataset), the workspace tree the
harness would show (rebuilt from the commit's file list with the harness's own `find` command), and the teacher's
steps translated to OUR tools (run_command / read_file / edit_file / write_file / submit_patch) with their raw
outputs, plus quality stats. Stage B replays episodes through the real harness (exact prompts, budget warnings,
ADK compaction with Gemma-written summaries) and renders the training samples.

Crash safety: after every source file, the finished batch file and state.json are written before moving on; a
restart (same session, or a new one with the previous output attached via --resume-from) skips finished files.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from decontam import is_contaminated  # noqa: E402

DATASET = "nvidia/Open-SWE-Traces"
THINKING_FOLDERS = ("qwen38_27b", "qwen38_flash_next", "deepseek_v4_flash_0731", "minimax_m25")
MAX_CALLS = 28                  # our harness budget (submit_patch / get_status are free)
BATCH_EPISODES = 500            # episodes per output batch file

# --- the harness's workspace tree, verbatim from swegemma.harness.agent_runner (checked in self_test) ---
PRUNED_TOP_DIRS = ("docs", "docs_src", "tests", "test_data", "examples", "benchmarks", "assets", "imgs", "questions",
                   "site", "g3doc", "google3")


def workspace_tree_command(workspace_dir, max_lines=200):
    prune = " ".join(f'-not -path "./{d}/*"' for d in PRUNED_TOP_DIRS)
    return (f'cd {workspace_dir} && find . -mindepth 1 -maxdepth 3 '
            '-not -path "./.*" -not -name ".*" '
            '-not -name "*.pyc" -not -name "__pycache__" -not -path "*/__pycache__/*" '
            '-not -path "./*.egg-info*" '
            f'{prune} '
            f"| awk -F/ '{{print NF, $0}}' | sort -n -k1,1 -k2 | head -{max_lines} "
            "| cut -d' ' -f2- | sort")


def tree_from_paths(paths):
    """Recreate the repository's file list as empty files and run the harness's own tree command on it."""
    with tempfile.TemporaryDirectory() as d:
        for p in paths:
            if p.startswith("/") or ".." in p.split("/"):
                continue
            f = Path(d, p)
            f.parent.mkdir(parents=True, exist_ok=True)
            f.touch()
        r = subprocess.run(["/bin/bash", "-c", workspace_tree_command(d)], capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else None


def git_file_list(repo_url, commit, timeout=120):
    """File paths at `commit` without downloading file contents (shallow, blob-less fetch of that one commit)."""
    with tempfile.TemporaryDirectory() as d:
        env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
        steps = [["git", "init", "-q"], ["git", "remote", "add", "origin", repo_url],
                 ["git", "fetch", "-q", "--depth", "1", "--filter=blob:none", "origin", commit],
                 ["git", "ls-tree", "-r", "--name-only", "FETCH_HEAD"]]
        out = None
        for s in steps:
            r = subprocess.run(s, cwd=d, capture_output=True, text=True, timeout=timeout, env=env)
            if r.returncode != 0:
                return None
            out = r.stdout
        return out.splitlines()


# --- source tasks: clean issue text + base commit ---
def build_source_index(cache_path):
    """instance_id -> {repo_url, base_commit, problem_statement} for every task of both source datasets. Built once
    (reads only the needed columns / fields) and cached on disk, so a restart does not rebuild it."""
    cache_path = Path(cache_path)
    if cache_path.exists():
        return json.loads(cache_path.read_text())
    import pyarrow.parquet as pq
    from huggingface_hub import HfFileSystem
    fs = HfFileSystem()
    idx = {}
    for f in fs.glob("datasets/nebius/SWE-rebench-V2/**/*.parquet"):
        with fs.open(f, "rb") as fh:
            t = pq.ParquetFile(fh).read(columns=["instance_id", "repo", "base_commit", "problem_statement"])
        for r in t.to_pylist():
            idx[r["instance_id"]] = {"repo_url": f"https://github.com/{r['repo']}.git",
                                     "base_commit": r["base_commit"], "problem_statement": r["problem_statement"]}
    print(f"source index: {len(idx)} SWE-rebench-V2 tasks", flush=True)
    with fs.open("datasets/AweAI-Team/Scale-SWE/processed_to_upload.jsonl", "rb", block_size=2 ** 22) as fh:
        for line in fh:
            r = json.loads(line)
            idx[r["instance_id"]] = {"repo_url": r["github_url"] + ".git", "base_commit": r["parent_commit"],
                                     "problem_statement": r["problem_statement"]}
    print(f"source index: {len(idx)} tasks in total", flush=True)
    tmp = cache_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(idx))
    tmp.replace(cache_path)
    return idx


# --- teacher run -> our tools ---
ROOT_PATTERNS = [re.compile(r"/testbed(?=/|\b)"), re.compile(r"/workspace/[A-Za-z0-9_.-]+__[A-Za-z0-9_.-]+(?=/|\b)")]


def norm_cmd(cmd):
    """Teacher's repo root (/testbed, /workspace/<owner>__<repo>__<ver>) -> our /workspace."""
    for p in ROOT_PATTERNS:
        cmd = p.sub("/workspace", cmd)
    return cmd


def norm_path(path):
    """Absolute teacher path -> path relative to our /workspace ('' = the root itself)."""
    p = norm_cmd(path)
    if p == "/workspace":
        return ""
    return p[len("/workspace/"):] if p.startswith("/workspace/") else p


def parse_bash_output(text):
    """(exit_code, output) from the three harness styles: mini-swe-agent <returncode>/<output>, SWE-agent
    'OBSERVATION:\\n...', OpenHands plain text with '[The command completed with exit code N.]'."""
    text = text or ""
    m = re.match(r"\s*<returncode>(-?\d+)</returncode>\s*<output>\n?(.*?)</output>\s*$", text, re.S)
    if m:
        return int(m.group(1)), m.group(2)
    if text.startswith("OBSERVATION:\n"):
        text = text[len("OBSERVATION:\n"):]
    m = re.search(r"\n?\[The command completed with exit code (-?\d+)\.\]\s*$", text)
    if m:
        return int(m.group(1)), text[:m.start()]
    return None, text


# the teacher reasoning about which copy of the package is imported, stale installs, sys.path, ... (noise for us)
CONFUSION_RE = re.compile(r"site-packages|dist-packages|installed (?:copy|version|package)|egg-link|sys\.path|"
                          r"PYTHONPATH|different (?:copy|location)|stale copy|__file__", re.I)
ERROR_RE = re.compile(r"Traceback \(most recent call last\)|command not found|No such file or directory|"
                      r"SyntaxError|did not appear verbatim|No replacement was performed|Invalid `|ERROR:", re.I)


def convert_run(row):
    """Teacher run -> (episode, None) or (None, reason it was dropped)."""
    msgs = row["messages"] or []
    steps, final_text, calls_counted, submitted, env_confusion = [], None, 0, False, 0
    pending_thought = []
    by_id = {}
    for m in msgs:
        if m.get("role") == "tool" and m.get("tool_call_id"):
            by_id[m["tool_call_id"]] = m.get("content") or ""
    tool_msgs = [m for m in msgs if m.get("role") == "tool"]
    tool_pos = 0
    for m in msgs:
        if m.get("role") != "assistant":
            continue
        raw_thinking = (m.get("reasoning_content") or "").strip()
        env_confusion += len(CONFUSION_RE.findall(raw_thinking))  # the teacher puzzling over its own sandbox
        thinking = norm_cmd(raw_thinking)
        text = norm_cmd((m.get("content") or "").strip())
        calls = []
        for tc in m.get("tool_calls") or []:
            fn = tc.get("function") or {}
            name = fn.get("name")
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                return None, "bad tool arguments"
            out = by_id.get(tc.get("id"))
            if out is None and tool_pos < len(tool_msgs):
                out = tool_msgs[tool_pos].get("content") or ""
            tool_pos += 1
            if name == "think":  # OpenHands' think tool = more reasoning, not an action
                pending_thought.append((args.get("thought") or "").strip())
                continue
            if name in ("bash", "execute_bash"):
                if args.get("is_input") in (True, "true"):
                    return None, "interactive shell input"
                command = args.get("command", "")
                if "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT" in command:  # mini-swe-agent's "I'm done" signal
                    submitted = True
                    calls.append({"tool": "submit_patch", "args": {}, "output": None})
                    final_text = text or final_text
                    continue
                code, output = parse_bash_output(out)
                # mini-swe-agent writes its diff to patch.txt in the repo; in our harness that file would be
                # submitted too, so it goes to /tmp
                command = re.sub(r"(?<![\w/.-])patch\.txt\b", "/tmp/patch.txt", norm_cmd(command))
                calls.append({"tool": "run_command", "args": {"command": command},
                              "output": norm_cmd(output), "exit_code": code})
            elif name == "str_replace_editor":
                cmd, path = args.get("command"), norm_path(args.get("path", ""))
                if cmd == "view":
                    if path == "" or "." not in Path(path).name and not args.get("view_range"):
                        # viewing a directory: our agent lists it with run_command
                        calls.append({"tool": "run_command", "args": {"command": f"find /workspace/{path} -maxdepth 2 "
                                      "-not -path '*/.*' | head -100".replace("/workspace/ ", "/workspace ")},
                                      "output": out, "exit_code": 0, "converted_from": "view_dir"})
                    else:
                        a = {"filepath": path}
                        vr = args.get("view_range")
                        if isinstance(vr, list) and len(vr) == 2:
                            try:
                                start, end = int(vr[0]), int(vr[1])
                            except (TypeError, ValueError):  # e.g. ["start", "end"]: not a usable line range
                                return None, "bad view_range"
                            a["start_line"] = start
                            if end > 0:
                                a["end_line"] = end
                        calls.append({"tool": "read_file", "args": a, "output": norm_cmd(out or "")})
                elif cmd == "create":
                    calls.append({"tool": "write_file", "args": {"filepath": path, "content": args.get("file_text", "")},
                                  "output": norm_cmd(out or "")})
                elif cmd == "str_replace":
                    calls.append({"tool": "edit_file", "args": {"filepath": path, "old_string": args.get("old_str", ""),
                                                                "new_string": args.get("new_str", "")},
                                  "output": norm_cmd(out or "")})
                elif cmd == "insert":
                    return None, "editor insert (no exact equivalent)"
                else:
                    return None, f"editor command {cmd}"
            elif name in ("submit", "finish"):
                submitted = True
                calls.append({"tool": "submit_patch", "args": {}, "output": out})
                if name == "finish":
                    final_text = (args.get("message") or "").strip() or None
            else:
                return None, f"unknown tool {name}"
        if pending_thought:
            thinking = "\n\n".join([thinking] + pending_thought).strip() if thinking else "\n\n".join(pending_thought)
            pending_thought = []
        if not calls:
            if text:
                final_text = final_text or text
            continue
        calls_counted += sum(1 for c in calls if c["tool"] != "submit_patch")
        steps.append({"thinking": thinking, "text": text, "calls": calls})
    if not steps:
        return None, "no tool steps"
    if calls_counted > MAX_CALLS:
        return None, "over call budget"
    errors = sum(1 for s in steps for c in s["calls"]
                 if (c.get("exit_code") not in (None, 0)) or ERROR_RE.search(str(c.get("output") or "")[:3000]))
    cmds = [c["args"].get("command") for s in steps for c in s["calls"] if c["tool"] == "run_command"]
    repeats = len(cmds) - len(set(cmds))
    meta = row.get("metadata") or {}
    return {
        "id": row.get("trajectory_id"), "instance_id": row["instance_id"], "repo": row["repo"],
        "teacher": (meta.get("teacher_model") or {}).get("name"), "category": meta.get("category"),
        "source_dataset": row.get("hf_dataset_name"), "license": row.get("license"),
        "teacher_task_message": next((m.get("content") for m in msgs if m.get("role") == "user"), None),
        "steps": steps, "final_text": final_text, "submitted": submitted,
        "model_patch": (meta.get("model_patch") or {}).get("patch"),
        "stats": {"calls": calls_counted, "errors": errors, "error_rate": round(errors / max(calls_counted, 1), 3),
                  "repeated_commands": repeats, "thinking_chars": sum(len(s["thinking"]) for s in steps),
                  "steps": len(steps), "env_confusion": env_confusion,
                  "max_step_thinking_chars": max(len(s["thinking"]) for s in steps),
                  "steps_thinking_over_8k_chars": sum(1 for s in steps if len(s["thinking"]) > 8000)},
    }, None


def keep_row(row):
    if row.get("language") != "python" or row.get("resolved") != 1 or is_contaminated(row):
        return False
    return bool(((row.get("metadata") or {}).get("teacher_model") or {}).get("enable_thinking"))


# --- driver ---
class State:
    def __init__(self, out):
        self.path = Path(out) / "state.json"
        self.d = json.loads(self.path.read_text()) if self.path.exists() else {
            "done_files": [], "next_batch": 0, "counts": {}, "drop_reasons": {}, "kept": 0, "seen": 0}

    def save(self):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.d, indent=1))
        tmp.replace(self.path)


def write_batch(out, state, episodes):
    if not episodes:
        return
    shard = state.d.get("shard", "0/1").split("/")[0]
    name = f"episodes_s{shard}_{state.d['next_batch']:04d}.jsonl"
    tmp = Path(out) / (name + ".tmp")
    with open(tmp, "w") as f:
        for e in episodes:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    tmp.replace(Path(out) / name)
    state.d["next_batch"] += 1


def process_rows(rows, out, state, src_index, trees, no_trees, file_label):
    episodes = []
    for row in rows:
        state.d["seen"] += 1
        if not keep_row(row):
            reason = "filtered (language/resolved/contaminated/no thinking)"
            state.d["drop_reasons"][reason] = state.d["drop_reasons"].get(reason, 0) + 1
            continue
        try:
            ep, why = convert_run(row)
        except Exception as e:  # one odd row must never stop the run: drop it and count why
            ep, why = None, f"converter error: {type(e).__name__}"
        if ep is None:
            state.d["drop_reasons"][why] = state.d["drop_reasons"].get(why, 0) + 1
            continue
        src = src_index.get(row["instance_id"]) or {}
        ep["base_commit"] = src.get("base_commit")
        ep["repo_url"] = src.get("repo_url")
        ep["problem_statement"] = src.get("problem_statement")
        if not no_trees and ep["repo_url"] and ep["base_commit"]:
            key = f"{ep['repo_url']}@{ep['base_commit']}"
            if key not in trees:
                files = git_file_list(ep["repo_url"], ep["base_commit"])
                trees[key] = tree_from_paths(files) if files else None
            ep["workspace_tree"] = trees[key]
        ep["source_file"] = file_label
        episodes.append(ep)
        state.d["kept"] += 1
        t = ep["teacher"] or "?"
        state.d["counts"][t] = state.d["counts"].get(t, 0) + 1
    return episodes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-files", type=int, default=0, help="stop after this many source files (trial run)")
    ap.add_argument("--survey", help="data/shape_survey.json: only files with keepers are downloaded")
    ap.add_argument("--resume-from", help="a previous run's output folder (copied in, finished files skipped)")
    ap.add_argument("--sample", help="local dry run: a JSON of rows per harness instead of downloads")
    ap.add_argument("--no-trees", action="store_true", help="skip workspace trees (no git access)")
    ap.add_argument("--shard", default="0/1", help="i/n: this run takes every n-th source file starting at i")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.resume_from and not (out / "state.json").exists():
        for f in Path(a.resume_from).iterdir():
            if f.is_file():
                shutil.copy2(f, out / f.name)
        print("resumed from", a.resume_from)
    state = State(out)
    trees_path = out / "trees.json"
    trees = json.loads(trees_path.read_text()) if trees_path.exists() else {}

    if a.sample:
        groups = json.load(open(a.sample))
        rows = [r for rs in groups.values() for r in rs]
        src = {}
        eps = process_rows(rows, out, state, src, trees, a.no_trees, "sample")
        write_batch(out, state, eps)
        state.save()
        print(json.dumps({k: state.d[k] for k in ("seen", "kept", "counts", "drop_reasons")}, indent=1))
        return

    import pyarrow.parquet as pq
    from huggingface_hub import HfFileSystem
    fs = HfFileSystem()
    files = [f for f in sorted(fs.glob(f"datasets/{DATASET}/data/**/*.parquet")) if f.split("/")[5] in THINKING_FOLDERS]
    if a.survey:
        keep = json.load(open(a.survey))["files"]
        files = [f for f in files if keep.get(f, 1) > 0]
    shard_i, shard_n = (int(x) for x in a.shard.split("/"))
    files = files[shard_i::shard_n]
    state.d["shard"] = a.shard
    src = build_source_index(out / "source_index.json")
    todo = [f for f in files if f not in state.d["done_files"]]
    if a.max_files:
        todo = todo[:a.max_files]
    print(f"{len(files)} source files, {len(state.d['done_files'])} done, {len(todo)} to do now")
    for i, f in enumerate(todo):
        t0 = time.time()
        local = Path(tempfile.gettempdir()) / "stage_a_current.parquet"
        for attempt in range(5):
            try:
                fs.get(f, str(local))
                break
            except Exception as e:
                print("   download retry", attempt + 1, repr(e)[:120])
                time.sleep(10 * (attempt + 1))
        else:
            print("   SKIP (download failed):", f)
            continue
        rows = [r for r in pq.read_table(local).to_pylist() if keep_row(r)]
        local.unlink(missing_ok=True)
        eps = process_rows(rows, out, state, src, trees, a.no_trees, f)
        write_batch(out, state, eps)
        trees_path.write_text(json.dumps(trees))
        state.d["done_files"].append(f)
        state.save()
        print(f"[{i + 1}/{len(todo)}] {f.split('data/')[-1]}: kept {len(eps)} "
              f"(total {state.d['kept']}) in {time.time() - t0:.0f}s", flush=True)
    print(json.dumps({k: state.d[k] for k in ("seen", "kept", "counts", "drop_reasons", "next_batch")}, indent=1))


if __name__ == "__main__":
    main()
