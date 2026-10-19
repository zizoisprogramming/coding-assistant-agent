"""Run a stage B notebook's cells 2, 4, 5 locally against a fake vLLM (summaries + /tokenize from our renderer),
with local episode folders standing in for the Kaggle inputs. Catches notebook-level bugs before a GPU run.

    data/venv_harness/bin/python scripts/datasets/sim_stage_b_notebook.py <cells dir> <scratch dir> <episode dir> [...]

<scratch dir> gets kg/input/<i>/stage_a (links to the episode files) and kg/working.
"""
import json
import shutil
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "datasets"))
from stage_b import Counter  # noqa: E402

CELLS, SC = Path(sys.argv[1]), Path(sys.argv[2])
kg = SC / "kg"
shutil.rmtree(kg, ignore_errors=True)
for i, d in enumerate(sys.argv[3:]):
    dst = kg / "input" / str(i) / "stage_a"
    dst.mkdir(parents=True)
    for f in Path(d).rglob("episodes_*.jsonl"):
        (dst / f.name).symlink_to(f.resolve())
(kg / "working").mkdir(parents=True)
counter = Counter(ROOT / "data" / "gemma4_tokenizer")


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path.endswith("/tokenize"):
            n = counter.prompt_tokens(body)
            out = {"tokens": list(range(n)), "count": n}
        else:
            out = {"id": "x", "object": "chat.completion", "created": 0, "model": body["model"],
                   "choices": [{"index": 0, "finish_reason": "stop", "message": {
                       "role": "assistant", "content": "Summary: the agent located the bug and is editing.",
                       "reasoning_content": "think"}}],
                   "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}
        d = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(d)))
        self.end_headers()
        self.wfile.write(d)


srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
ns = {"server_instance": SimpleNamespace(base_url=f"http://127.0.0.1:{srv.server_address[1]}/v1", stop=lambda: None),
      "MODEL_PATH": Path("fake-12b"), "TOK_DIR": ROOT / "data" / "gemma4_tokenizer"}
for cell in ("cell2_setup.py", "cell4_run.py", "cell5_report.py"):
    src = (CELLS / cell).read_text()
    src = src.replace("/kaggle/input", str(kg / "input")).replace("/kaggle/working", str(kg / "working"))
    src = src.replace("sys.executable, '-u'", f"'{ROOT}/data/venv_harness/bin/python', '-u'")
    if cell == "cell2_setup.py":  # stage A inputs: any number of local folders instead of exactly the two
        src = src.replace("assert len(EP_DIRS) == 2,", "assert len(EP_DIRS) >= 1,")
    print(f"########## {cell}", flush=True)
    exec(compile(src, cell, "exec"), ns)
