"""Decontamination: no training sample may come from the competition's repositories.

    data/venv_train/bin/python scripts/datasets/decontam.py            # scan all sources, write data/decontam_report.json

Rule (repo level, strictest): drop every row whose task repository is one the competition draws from (fastapi,
requests, rich, httpx, read from data/tasks.jsonl). Matching only our 129 public tasks would not be enough: the
hidden scoring tasks are other pull requests of the same repositories, and a public dataset may contain their fixes.

Each source names its task differently; repo_of() handles all of them:
  repo column             "Textualize/rich"
  SWE-bench style id      "fastapi__fastapi-15661", "psf__requests-6757"
  SWE-smith style id      "tiangolo__fastapi.ab12cd34.func_pm_remove_assign__x1y2"
  CoderForge run id       "0b01001001__spectree-64_run2"
  docker image            "qingyangwu/sweb.eval.x86_64.0b01001001_1776_spectree-64"
  R2E-Gym image           "qingyangwu/aiohttp_final:3c31b3837404fa2fed3cdd42e89f9d6f25c6931e"
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def competition_repo_names():
    """Repositories of the competition's tasks (data/tasks.jsonl when present; on Kaggle without the competition
    data attached, the same four names, checked against tasks.jsonl in self_test)."""
    path = ROOT / "data" / "tasks.jsonl"
    if not path.exists():
        return {"fastapi", "requests", "rich", "httpx"}
    names = {json.loads(line)["repo"].split("/")[-1].lower() for line in open(path)}
    assert names, "data/tasks.jsonl has no tasks"
    return names


BLOCKED = competition_repo_names()  # {'fastapi', 'requests', 'rich', 'httpx'}


def repo_of(row):
    """Short repository name (lower case) of a dataset row, or None if it cannot be told."""
    repo = row.get("repo")
    if isinstance(repo, str) and repo:
        return repo.rsplit("/", 1)[-1].lower()
    for key in ("instance_id", "trajectory_id"):
        v = row.get(key)
        if isinstance(v, str) and "__" in v:
            name = v.split("__", 1)[1]
            name = re.split(r"\.[0-9a-f]{6,40}\.", name)[0]          # SWE-smith: repo.commit.bugtype
            name = re.sub(r"_run\d+$", "", name)                      # CoderForge run suffix
            name = re.sub(r"-[0-9a-f]{7,40}$|-\d+$", "", name)        # PR number or commit hash
            return name.lower()
    img = row.get("image")
    if isinstance(img, str) and "_1776_" in img:                   # sweb.eval.x86_64.owner_1776_repo-NUM
        return re.sub(r"-\d+$", "", img.split("_1776_", 1)[1]).lower()
    m = re.match(r"^[^/]+/([A-Za-z0-9_.-]+?)_final:[0-9a-f]+$", img or "")  # R2E-Gym: user/repo_final:commit
    if m:
        return m.group(1).lower()
    return None


def is_contaminated(row):
    """True if the row comes from a competition repository, or if its repository cannot be identified (unknown
    provenance is dropped too: garbage in, garbage out)."""
    name = repo_of(row)
    return name is None or name in BLOCKED


# where each source keeps its trajectories (only these parquet files are scanned) and its id columns
SOURCES = {
    "nebius/SWE-rebench-openhands-trajectories": ("trajectories.parquet", ["repo", "instance_id", "resolved"]),
    "nvidia/SWE-Hero-openhands-trajectories": ("data/*.parquet", ["repo", "instance_id"]),
    "nvidia/Open-SWE-Traces": ("data/**/*.parquet", ["repo", "instance_id", "language", "resolved"]),
    "togethercomputer/CoderForge-Preview": ("trajectories/*.parquet", ["trajectory_id", "image", "reward"]),
    "SWE-Lego/SWE-Lego-Real-Data": ("data/**/*.parquet", ["instance_id"]),
    "SWE-Lego/SWE-Lego-Synthetic-Data": ("data/**/*.parquet", ["instance_id"]),
}


def scan(dataset, pattern, columns, fs):
    """Read only the id columns of every parquet file (no trajectories are downloaded)."""
    import pyarrow.parquet as pq
    files = sorted(fs.glob(f"datasets/{dataset}/{pattern}"))
    total, blocked, unknown, per_repo, examples = 0, 0, 0, Counter(), {}
    for f in files:
        with fs.open(f, "rb") as fh:
            pf = pq.ParquetFile(fh)
            cols = [c for c in columns if c in pf.schema_arrow.names]
            t = pf.read(columns=cols).to_pylist()
        for row in t:
            total += 1
            name = repo_of(row)
            if name is None:
                unknown += 1
            elif name in BLOCKED:
                blocked += 1
                per_repo[name] += 1
                examples.setdefault(name, row.get("instance_id") or row.get("trajectory_id"))
    return {"files": len(files), "rows": total, "from_competition_repos": blocked, "repo_unknown": unknown,
            "per_repo": dict(per_repo), "examples": examples}


def self_test():
    cases = {
        "fastapi__fastapi-15661": "fastapi", "psf__requests-6757": "requests", "Textualize__rich-3905": "rich",
        "tiangolo__fastapi.ab12cd34.func_pm_remove_assign__x1y2": "fastapi",
        "0b01001001__spectree-64_run2": "spectree", "pandas-dev__pandas-dbf8aaf4a3f3b41e5c1a402473df5da43813948f":
        "pandas", "getmoto__moto-8365": "moto", "encode__httpx.4b5a92e8.lm_rewrite__abc": "httpx",
    }
    for iid, want in cases.items():
        got = repo_of({"instance_id": iid})
        assert got == want, (iid, got, want)
    assert repo_of({"image": "qingyangwu/sweb.eval.x86_64.0b01001001_1776_spectree-64"}) == "spectree"
    assert repo_of({"trajectory_id": "qingyangwu_aiohttp_final_3c31b383_run5",
                    "image": "qingyangwu/aiohttp_final:3c31b3837404fa2fed3cdd42e89f9d6f25c6931e"}) == "aiohttp"
    assert repo_of({"repo": "Textualize/rich"}) == "rich" and is_contaminated({"repo": "psf/requests"})
    assert not is_contaminated({"repo": "psf/requests-html"}) and is_contaminated({})
    assert BLOCKED == {"fastapi", "requests", "rich", "httpx"}, "update the fallback list in competition_repo_names"
    print("self-test ok; blocked repos:", sorted(BLOCKED))


if __name__ == "__main__":
    self_test()
    if "--test" in sys.argv:
        sys.exit(0)
    from huggingface_hub import HfFileSystem
    fs = HfFileSystem()
    report = {}
    for ds, (pattern, cols) in SOURCES.items():
        try:
            report[ds] = scan(ds, pattern, cols, fs)
        except Exception as e:
            report[ds] = {"error": repr(e)[:300]}
        print(ds, json.dumps(report[ds]))
        (ROOT / "data" / "decontam_report.json").write_text(json.dumps(report, indent=1))
