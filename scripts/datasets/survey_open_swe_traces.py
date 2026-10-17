"""Per teacher/harness folder of nvidia/Open-SWE-Traces: rows, and how many are Python + resolved + clean (not from a
competition repo), and whether the teacher's thinking was on. Reads only small columns.

    data/venv_train/bin/python scripts/datasets/survey_open_swe_traces.py   # -> data/open_swe_traces_survey.json
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq
from huggingface_hub import HfFileSystem

sys.path.insert(0, str(Path(__file__).resolve().parent))
from decontam import ROOT, is_contaminated  # noqa: E402

fs = HfFileSystem()
groups = defaultdict(list)
for f in fs.glob("datasets/nvidia/Open-SWE-Traces/data/**/*.parquet"):
    groups["/".join(f.split("/")[4:-1])].append(f)
out = {}
for g, files in sorted(groups.items()):
    s = {"rows": 0, "python": 0, "python_resolved": 0, "python_resolved_clean": 0, "thinking": None}
    for f in sorted(files):
        with fs.open(f, "rb") as fh:
            pf = pq.ParquetFile(fh)
            t = pf.read(columns=["repo", "language", "resolved"]).to_pylist()
            if s["thinking"] is None:
                meta = pf.read_row_group(0, columns=["metadata"]).slice(0, 1).to_pylist()[0]["metadata"]
                s["thinking"] = ((meta or {}).get("teacher_model") or {}).get("enable_thinking")
                s["teacher"] = ((meta or {}).get("teacher_model") or {}).get("name")
        for r in t:
            s["rows"] += 1
            if r["language"] == "python":
                s["python"] += 1
                if r["resolved"] == 1:
                    s["python_resolved"] += 1
                    s["python_resolved_clean"] += not is_contaminated(r)
    out[g] = s
    print(f"{g:45} {json.dumps(s)}", flush=True)
(ROOT / "data" / "open_swe_traces_survey.json").write_text(json.dumps(out, indent=1))
