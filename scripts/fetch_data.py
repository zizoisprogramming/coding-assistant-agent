"""Download competition data and harness wheels into data/ (gitignored).

Usage:
    python3 scripts/fetch_data.py --wheelhouse              # harness wheels -> data/wheelhouse/
    python3 scripts/fetch_data.py --test-wheels             # sandbox test-dependency wheels -> data/wheels/
    python3 scripts/fetch_data.py --tasks fastapi_15588,rich_3962
                                                            # snapshots + graphs + embeddings for those tasks

Files that already exist with the expected size are skipped.
"""

import argparse
import io
import json
import sys
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from kaggle_api import TOKEN, get  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
COMPETITION = "gemma-4-developer-agent"
WHEELHOUSE = "metric/gemma-4-developer-agent-wheelhouse"
# Only the pure-Python harness packages; vllm, flashinfer and the other wheels are Linux/GPU-only.
HARNESS_WHEEL_PREFIXES = ("swegemma-", "adk_submission-", "adk_eval_core-", "google_adk-", "google_genai-")


def download(url, dest, expected_size=None):
    """Stream `url` to `dest`, unwrapping Kaggle's single-file zip wrapper if present."""
    if dest.exists() and (expected_size is None or dest.stat().st_size == expected_size):
        print(f"  skip {dest.relative_to(ROOT)} (exists)")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + TOKEN})
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(req, timeout=600) as resp, open(tmp, "wb") as out:
        while chunk := resp.read(1 << 20):
            out.write(chunk)
    # Kaggle sometimes wraps a single file in a zip named after it; a real .whl/.tgz never has that layout.
    if zipfile.is_zipfile(tmp):
        with zipfile.ZipFile(tmp) as z:
            if z.namelist() == [dest.name]:
                tmp.write_bytes(z.read(dest.name))
    tmp.rename(dest)
    size = dest.stat().st_size
    note = "  <-- 0 bytes! (known 0-byte graph/embedding issue, forum 742911)" if size == 0 else ""
    print(f"  got  {dest.relative_to(ROOT)} ({size / 1e6:.1f} MB){note}")


def competition_files():
    """All competition data files as {name: size}, from the API (cached in research/raw/all_files.json)."""
    cached = ROOT / "research" / "raw" / "all_files.json"
    files = json.loads(cached.read_text())
    return {f["name"]: f.get("totalBytes") for f in files}


def competition_url(name):
    return (f"https://www.kaggle.com/api/v1/competitions/data/download/{COMPETITION}/"
            + urllib.parse.quote(name, safe=""))


def fetch_wheelhouse():
    files, token = [], None
    while True:
        path = f"/api/v1/datasets/list/{WHEELHOUSE}"
        if token:
            path += "?pageToken=" + urllib.parse.quote(token)
        page = get(path)
        files += page.get("datasetFiles", [])
        token = page.get("nextPageTokenNullable")
        if not token:
            break
    for f in files:
        if f["name"].startswith(HARNESS_WHEEL_PREFIXES):
            url = f"https://www.kaggle.com/api/v1/datasets/download/{WHEELHOUSE}/{f['name']}"
            download(url, DATA / "wheelhouse" / f["name"], f.get("totalBytes"))


def fetch_test_wheels():
    for name, size in competition_files().items():
        if name.startswith("wheels/"):
            download(competition_url(name), DATA / name, size)


def fetch_tasks(task_ids):
    tasks = {}
    for line in (DATA / "tasks.jsonl").read_text().splitlines():
        t = json.loads(line)
        tasks[t["instance_id"]] = t
    files = competition_files()
    for task_id in task_ids:
        t = tasks[task_id]
        key = f"{t['repo'].split('/')[-1]}_{t['base_commit']}"
        print(f"{task_id} ({key})")
        for name in (f"snapshots/{task_id}.tgz", f"graphs/{key}.json", f"embeddings/{key}.npz"):
            if name not in files:
                print(f"  missing from competition data: {name}")
                continue
            download(competition_url(name), DATA / name, files[name])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--wheelhouse", action="store_true")
    ap.add_argument("--test-wheels", action="store_true")
    ap.add_argument("--tasks", default="", help="comma-separated instance ids")
    args = ap.parse_args()
    if args.wheelhouse:
        fetch_wheelhouse()
    if args.test_wheels:
        fetch_test_wheels()
    if args.tasks:
        fetch_tasks([t for t in args.tasks.split(",") if t])


if __name__ == "__main__":
    main()
