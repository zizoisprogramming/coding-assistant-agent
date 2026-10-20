"""Can a task's pinned environment be installed offline on Kaggle (Linux x86_64, CPython 3.12)? Metadata only:
asks PyPI's JSON API which files each pinned (package, version) release has; downloads no wheels.

    .venv/bin/python scripts/datasets/rebench_wheels_check.py [--sample 300]

Per pin: wheel (a cp312-compatible wheel exists) / sdist_only (no wheel at all: builds offline if pure Python) /
old_binary (wheels exist but none for cp312: compiled package too old for 3.12, needs a compiler and may not build)
/ missing (version not on PyPI). Per task: the worst of its pins. Writes data/swe_rebench/wheels_check.json.
"""
import argparse
import collections
import concurrent.futures as cf
import json
import random
import re
import urllib.request
from pathlib import Path

from packaging.tags import compatible_tags, cpython_tags
from packaging.utils import parse_wheel_filename

ROOT = Path(__file__).resolve().parents[2]
PLATFORMS = [f"manylinux_2_{m}_x86_64" for m in range(35, 4, -1)] + \
    ["manylinux2014_x86_64", "manylinux2010_x86_64", "manylinux1_x86_64"]
SUPPORTED = set(cpython_tags((3, 12), abis=["cp312", "abi3", "none"], platforms=PLATFORMS)) | \
    set(compatible_tags((3, 12), interpreter="cp312", platforms=PLATFORMS))
PIN = re.compile(r"^([A-Za-z0-9_.\-]+)(\[.*\])?==([^\s;]+)")
RANK = {"wheel": 0, "sdist_only": 1, "old_binary": 2, "missing": 3}


def pins(req_text):
    out = []
    for line in (req_text or "").splitlines():
        m = PIN.match(line.strip())
        if m:
            out.append((re.sub(r"[-_.]+", "-", m.group(1)).lower(), m.group(3)))
    return out


def classify(pkg, ver):
    try:
        with urllib.request.urlopen(f"https://pypi.org/pypi/{pkg}/{ver}/json", timeout=30) as r:
            files = [u["filename"] for u in json.load(r)["urls"]]
    except Exception:
        return "missing"
    wheels = [f for f in files if f.endswith(".whl")]
    for w in wheels:
        try:
            if set(parse_wheel_filename(w)[3]) & SUPPORTED:
                return "wheel"
        except Exception:
            pass
    return "old_binary" if wheels else ("sdist_only" if files else "missing")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=300)
    args = ap.parse_args()
    rows = [json.loads(l) for l in open(ROOT / "data/swe_rebench/candidates.jsonl")]
    random.Random(20261020).shuffle(rows)
    rows = rows[:args.sample]
    need = sorted({p for r in rows for p in pins(r["requirements"])})
    print(f"{len(rows)} tasks, {len(need)} unique pins to check", flush=True)
    with cf.ThreadPoolExecutor(16) as ex:
        status = dict(zip(need, ex.map(lambda p: classify(*p), need)))
    print("pins:", collections.Counter(status.values()))
    tasks = {}
    for r in rows:
        st = [status[p] for p in pins(r["requirements"])]
        worst = max(st, key=RANK.get, default="wheel")
        tasks[r["instance_id"]] = {"worst": worst, "py": r["install_config"]["python"],
                                   "bad": [f"{p}=={v}:{status[(p, v)]}" for p, v in pins(r["requirements"])
                                           if status[(p, v)] != "wheel"]}
    print("tasks by worst pin:", collections.Counter(t["worst"] for t in tasks.values()))
    for py in sorted({t["py"] for t in tasks.values()}):
        sub = [t for t in tasks.values() if t["py"] == py]
        print(f"  python {py}: {len(sub)} tasks,", dict(collections.Counter(t["worst"] for t in sub)))
    culprits = collections.Counter(b.split("==")[0] + ":" + b.rsplit(":", 1)[1] for t in tasks.values() for b in t["bad"])
    print("most common non-wheel pins:", culprits.most_common(20))
    (ROOT / "data/swe_rebench/wheels_check.json").write_text(json.dumps(
        {"status": {f"{p}=={v}": s for (p, v), s in status.items()}, "tasks": tasks}, indent=1))


if __name__ == "__main__":
    main()
