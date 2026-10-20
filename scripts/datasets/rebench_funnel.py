"""SWE-rebench → candidate tasks for our own task set (option B). Prints the filter funnel; writes the survivors.

    .venv/bin/python scripts/datasets/rebench_funnel.py

Input: data/swe_rebench/test_cols.parquet (nebius/SWE-rebench test split, CC-BY-4.0, all columns but `environment`).
Excludes the public competition repos and the 17 OOD-45 repos (our yardstick). llm_score scales follow SWE-bench
Verified's annotation (lower = better: 0 = well specified / valid tests / <15 min fix).
"""
import collections
import json
import re
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "swe_rebench" / "candidates.jsonl"
OOD_REPOS = {  # the 17 OOD-45 repos (tasks.jsonl of rodrigospalma/ood45-bugfix-split)
    "apache/iceberg-python", "caronc/apprise", "feast-dev/feast", "fsspec/filesystem_spec", "has2k1/plotnine",
    "hgrecco/pint", "kedro-org/kedro", "kedro-org/kedro-viz", "pdm-project/pdm", "pola-rs/polars",
    "posit-dev/great-tables", "posit-dev/py-shiny", "pyjanitor-devs/pyjanitor", "tkem/cachetools", "tox-dev/tox",
    "urllib3/urllib3", "wntrblm/nox"}
PUBLIC_REPOS = {"fastapi/fastapi", "tiangolo/fastapi", "textualize/rich", "psf/requests", "encode/httpx"}
PERMISSIVE = re.compile(r"\b(MIT|Apache|BSD|Unlicense|ISC|Zope|PSF|Python Software)", re.I)
TEST_PATH = re.compile(r"(^|/)(tests?|testing)(/|$)|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$")


def patch_stats(patch):
    files, added, removed = set(), 0, 0
    for line in patch.splitlines():
        if line.startswith("diff --git"):
            files.add(line.split(" b/", 1)[-1])
        elif line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            removed += 1
    src = [f for f in files if f.endswith(".py") and not TEST_PATH.search(f)]
    return files, src, added + removed


def main():
    rows = pq.read_table(ROOT / "data/swe_rebench/test_cols.parquet").to_pylist()
    steps = [
        ("not a public / OOD-45 repo", lambda r: r["repo"].lower() not in PUBLIC_REPOS | {x.lower() for x in OOD_REPOS}),
        ("permissive license", lambda r: bool(PERMISSIVE.search(r["license_name"] or ""))),
        ("pytest log parser", lambda r: (r["install_config"] or {}).get("log_parser", "").startswith("parse_log_pytest")),
        ("issue text clear (score<=1)", lambda r: 0 <= r["meta"]["llm_score"]["issue_text_score"] <= 1),
        ("tests valid (score<=1)", lambda r: 0 <= r["meta"]["llm_score"]["test_score"] <= 1),
        ("difficulty <=1 (<1h for a human)", lambda r: 0 <= r["meta"]["llm_score"]["difficulty_score"] <= 1),
        ("1-20 FAIL_TO_PASS tests", lambda r: 1 <= len(r["FAIL_TO_PASS"] or []) <= 20),
        ("patch: 1-3 source .py files, no other files", lambda r: (lambda f, s, n: 1 <= len(s) <= 3 and len(f) == len(s))(*patch_stats(r["patch"]))),
        ("patch: <=60 changed lines", lambda r: patch_stats(r["patch"])[2] <= 60),
        ("python >= 3.8 in install_config", lambda r: tuple(int(x) for x in ((r["install_config"] or {}).get("python") or "0").split(".")[:2]) >= (3, 8)),
    ]
    cur = rows
    print(f"{'step':48} {'left':>6} {'repos':>6}")
    print(f"{'all SWE-rebench test rows':48} {len(cur):6} {len({r['repo'] for r in cur}):6}")
    for name, keep in steps:
        cur = [r for r in cur if keep(r)]
        print(f"{name:48} {len(cur):6} {len({r['repo'] for r in cur}):6}")
    c = collections.Counter
    print("python", c(r["install_config"]["python"] for r in cur).most_common())
    print("year", sorted(c(r["created_at"][:4] for r in cur).items()))
    print("difficulty", sorted(c(r["meta"]["llm_score"]["difficulty_score"] for r in cur).items()))
    per_repo = c(r["repo"] for r in cur)
    print("tasks per repo: repos with 1:", sum(v == 1 for v in per_repo.values()), "| 2-4:",
          sum(2 <= v <= 4 for v in per_repo.values()), "| 5+:", sum(v >= 5 for v in per_repo.values()),
          "| top:", per_repo.most_common(12))
    with open(OUT, "w") as fh:
        for r in cur:
            fh.write(json.dumps(r) + "\n")
    print("wrote", OUT.relative_to(ROOT), len(cur))


if __name__ == "__main__":
    main()
