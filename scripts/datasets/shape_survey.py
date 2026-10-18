"""How many Open-SWE-Traces runs pass the cheap filters, reading only tiny columns (roles, tool names, flags):
Python, resolved, clean repo, thinking teacher, and at most MAX_CALLS tool calls. Per folder and per file, so the
Kaggle job downloads only files that contain keepers.

    data/venv_train/bin/python scripts/datasets/shape_survey.py   # -> data/shape_survey.json
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq
from huggingface_hub import HfFileSystem

sys.path.insert(0, str(Path(__file__).resolve().parent))
from decontam import ROOT, is_contaminated  # noqa: E402

MAX_CALLS = 28
THINKING = ("qwen38_27b", "qwen38_flash_next", "deepseek_v4_flash_0731", "minimax_m25")
COLS = ["repo", "instance_id", "language", "resolved", "metadata.teacher_model.enable_thinking",
        "messages.list.element.role", "messages.list.element.tool_calls.list.element.function.name"]

fs = HfFileSystem()
files = [f for f in sorted(fs.glob("datasets/nvidia/Open-SWE-Traces/data/**/*.parquet"))
         if f.split("/")[5] in THINKING]
out = {"max_calls": MAX_CALLS, "files": {}, "folders": defaultdict(lambda: defaultdict(int)), "calls_hist": defaultdict(int)}
for i, f in enumerate(files):
    with fs.open(f, "rb") as fh:
        rows = pq.ParquetFile(fh).read(columns=COLS).to_pylist()
    keep = 0
    folder = "/".join(f.split("/")[4:-1])
    for r in rows:
        if r["language"] != "python" or r["resolved"] != 1 or is_contaminated(r):
            continue
        if not ((r.get("metadata") or {}).get("teacher_model") or {}).get("enable_thinking"):
            continue
        msgs = r["messages"] or []
        calls = sum(len(m.get("tool_calls") or []) for m in msgs)
        if calls == 0:  # mini-swe-agent: one bash block per assistant turn, no tool_calls field
            calls = sum(1 for m in msgs if m.get("role") == "assistant")
        out["calls_hist"][min(calls // 5 * 5, 100)] += 1
        out["folders"][folder]["python_resolved_clean_thinking"] += 1
        if calls <= MAX_CALLS:
            keep += 1
            out["folders"][folder][f"le_{MAX_CALLS}_calls"] += 1
    out["files"][f] = keep
    print(f"[{i + 1}/{len(files)}] {folder} keep {keep}", flush=True)
    (ROOT / "data" / "shape_survey.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out["folders"], indent=1))
print("calls histogram (bucket of 5):", dict(sorted(out["calls_hist"].items())))
print("files with keepers:", sum(1 for v in out["files"].values() if v), "of", len(files),
      "| keepers:", sum(out["files"].values()))
