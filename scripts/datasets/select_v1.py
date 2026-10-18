"""Selection v1 for the 12B test: 500 training + 50 validation episodes from the stage A stats (user decisions
2026-10-18). Nothing is deleted: this only writes an id list (with file + line, to fetch the episodes later).

    python3 scripts/datasets/select_v1.py data/results/2026-10-18_stats/stats.jsonl.gz

Filters: every step thinks <= 2,048 tokens (our mix budget); env_confusion <= 2; no repeated commands; error rate
<= 0.2. Dedup (user rule): one run per task, the best by (error rate + calls/100 + thinking/40,000). Teacher mix kept
as it comes out (user: keep it). Sampling: categories in their natural proportions, fixed seed. Validation: 50
episodes from repositories that do not appear in the training set.
"""
import gzip
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

N_TRAIN, N_VAL, SEED = 500, 50, 20261018
ROOT = Path(__file__).resolve().parents[2]


def score(r):  # lower is better: few errors, efficient, concise thinking
    return r["error_rate"] + r["calls"] / 100 + r["thinking_tokens"] / 40000


def main():
    rows = [json.loads(l) for l in gzip.open(sys.argv[1], "rt")]
    pool = [r for r in rows if r["steps_over_2048"] == 0 and r["env_confusion"] <= 2
            and r["repeated_commands"] == 0 and r["error_rate"] <= 0.2]
    best = {}
    for r in pool:
        b = best.get(r["instance_id"])
        if b is None or score(r) < score(b):
            best[r["instance_id"]] = r
    cands = sorted(best.values(), key=lambda r: r["id"])
    rng = random.Random(SEED)
    rng.shuffle(cands)

    # validation first: whole repositories are held out
    by_repo = defaultdict(list)
    for r in cands:
        by_repo[r["repo"]].append(r)
    repos = sorted(by_repo)
    rng.shuffle(repos)
    val, val_repos = [], set()
    for repo in repos:
        if len(val) >= N_VAL:
            break
        val.append(by_repo[repo][0])  # one episode per held-out repo: more diverse validation
        val_repos.add(repo)
    rest = [r for r in cands if r["repo"] not in val_repos]

    # training: categories in their natural proportions among the remaining candidates
    by_cat = defaultdict(list)
    for r in rest:
        by_cat[r["category"] or "other"].append(r)
    total = len(rest)
    train = []
    for cat, items in sorted(by_cat.items()):
        train += items[:round(N_TRAIN * len(items) / total)]
    train += [r for r in rest if r not in train][:N_TRAIN - len(train)]
    train = train[:N_TRAIN]

    keep = ("id", "file", "line", "instance_id", "repo", "teacher", "category", "calls", "approx_tokens",
            "thinking_tokens", "error_rate")
    out = {"version": "v1", "seed": SEED, "source": "stage A episodes (Kaggle outputs dataset-loader-test-resume, "
           "dataset-loader-test-2-resume)", "pool_after_filters": len(pool), "tasks_after_dedup": len(cands),
           "train": [{k: r[k] for k in keep} for r in train], "val": [{k: r[k] for k in keep} for r in val]}
    path = ROOT / "data" / "selection_v1.json"
    path.write_text(json.dumps(out, indent=1))
    for name, s in (("train", train), ("val", val)):
        print(f"{name}: {len(s)} episodes, {len({r['repo'] for r in s})} repos, teachers {dict(Counter(r['teacher'] for r in s))}, "
              f"categories {dict(Counter(r['category'] for r in s))}, ~{sum(r['approx_tokens'] for r in s) / 1e6:.1f}M tokens")
    assert not {r["repo"] for r in train} & {r["repo"] for r in val}
    print("wrote", path)


if __name__ == "__main__":
    main()
