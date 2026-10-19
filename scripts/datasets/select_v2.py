"""Selection v2 ("thinking first", user 2026-10-19): 500 training + 50 validation episodes for the second 12B run.

    python3 scripts/datasets/select_v2.py <stats.jsonl.gz> <features.jsonl.gz> <flags.jsonl.gz> [...more flag files]

Why v2 (docs/PLAN.md, SFT v1 diagnosis): v1 taught Gemma to narrate instead of reason (thin teacher thinking, v1 even
preferred LESS thinking), to dump whole files and chain bash commands our harness cuts or breaks, and never showed an
error being recovered. Gemma's own resolved runs read narrow ranges with read_file, think about twice as much as its
failed runs, and never chain. Rules (same for every teacher; the mix that comes out is what it is):
- as v1: no sandbox flags, every step <= 2,048 thinking tokens, no repeated commands, env_confusion <= 2;
- stage B can replay it faithfully (features replay_ok);
- REAL thinking: >= 600 thinking chars per step on average (~150 tokens), at most 20% of steps without thinking
  (strict "every step" left only 828 episodes / 639 tasks);
- fits our harness: at most one tool output over our limits (replay_ok already guarantees the teacher never relied
  on the cut part); no print-only sed; never repeats a failed call;
- errors allowed (error rate <= 0.35): recovering from them is part of what we want to teach (target >= 30% with a
  recovered error; reported);
- best run per task by: fewer long &&/; chains, whole-file cats and inline python scripts per call, more thinking
  (capped), fewer calls;
- categories as the competition (65/13/7/15), val = 50 episodes from 50 repos never in train, 2x reserves; fixed seed.
Stage B v2 then rewrites simple reads into read_file (--rewrite-reads). Nothing is deleted: this only writes ids.
"""
import gzip
import json
import random
import sys
from collections import Counter
from pathlib import Path

N_TRAIN, N_VAL, SEED, RESERVE = 500, 50, 20261019, 2.0
QUOTA = {"bug-fix": 0.65, "feature-request": 0.13, "enhancement": 0.07, "other": 0.15}
ROOT = Path(__file__).resolve().parents[2]


def style(r, f):
    """Lower is better: harness-unfriendly bash habits per call, minus a capped thinking bonus, plus length."""
    per_call = (f["long_chains"] + f["cat_whole_file"] + f["inline_python"]) / max(f["calls"], 1)
    return per_call - min(f["thinking_chars_per_step"], 3000) / 6000 + r["calls"] / 100


def main():
    stats = {json.loads(l)["id"]: json.loads(l) for l in gzip.open(sys.argv[1], "rt")}
    feats = {json.loads(l)["id"]: json.loads(l) for l in gzip.open(sys.argv[2], "rt")}
    flagged = {json.loads(l)["id"] for f in sys.argv[3:] for l in gzip.open(f, "rt")}
    print(f"episodes: stats {len(stats)}, features {len(feats)}, flagged (sandbox) {len(flagged)}")
    steps = Counter()
    pool = []
    for i, r in stats.items():
        f = feats.get(i)
        checks = [("sandbox", i not in flagged), ("features", f is not None),
                  ("thinking <=2048/step", r["steps_over_2048"] == 0), ("no repeated commands", r["repeated_commands"] == 0),
                  ("env_confusion <=2", r["env_confusion"] <= 2), ("replay ok", f and f["replay_ok"]),
                  ("<=20% steps without thinking", f and f["steps_no_thinking"] <= 0.2 * f["steps"]),
                  (">=600 thinking chars/step", f and f["thinking_chars_per_step"] >= 600),
                  ("<=1 output over limits", f and f["outputs_over_limit"] <= 1),
                  ("no print-only sed", f and f["print_only_sed"] == 0),
                  ("never repeats a failed call", f and f["repeated_after_error"] == 0),
                  ("error rate <=0.35", r["error_rate"] <= 0.35)]
        ok = True
        for name, passed in checks:
            if ok and not passed:
                steps[name] += 1
                ok = False
        if ok:
            pool.append((r, f))
    print("dropped at the first failing rule:", dict(steps))
    print(f"pool after rules: {len(pool)} episodes, {len({r['instance_id'] for r, _ in pool})} tasks, teachers "
          f"{dict(Counter(r['teacher'] for r, _ in pool))}")
    best = {}
    for r, f in pool:
        b = best.get(r["instance_id"])
        if b is None or style(r, f) < style(*b):
            best[r["instance_id"]] = (r, f)
    cands = sorted(best.values(), key=lambda x: x[0]["id"])
    random.Random(SEED).shuffle(cands)

    def take(items, n, used_repos=None, one_per_repo=False):
        picked, seen = [], set()
        for cat, share in QUOTA.items():
            want = round(n * share)
            for r, f in items:
                if want == 0:
                    break
                if (r["category"] or "other") != cat or any(p[0] is r for p in picked):
                    continue
                if (used_repos and r["repo"] in used_repos) or (one_per_repo and r["repo"] in seen):
                    continue
                picked.append((r, f))
                seen.add(r["repo"])
                want -= 1
        return picked

    val_cands = take(cands, round(N_VAL * RESERVE), one_per_repo=True)
    val_repos = {r["repo"] for r, _ in val_cands}
    train_cands = take(cands, round(N_TRAIN * RESERVE), used_repos=val_repos)
    quotas = {name: {c: round(n * s) for c, s in QUOTA.items()} for name, n in (("train", N_TRAIN), ("val", N_VAL))}

    def first(lst, q):
        left, out = dict(q), []
        for r, f in lst:
            c = r["category"] or "other"
            if left.get(c, 0) > 0:
                out.append((r, f))
                left[c] -= 1
        return out
    val, train = first(val_cands, quotas["val"]), first(train_cands, quotas["train"])
    keep = ("id", "file", "line", "instance_id", "repo", "teacher", "category", "calls", "approx_tokens",
            "thinking_tokens", "error_rate")
    row = lambda r: {k: r[k] for k in keep}  # noqa: E731
    out = {"version": "v2", "seed": SEED, "rules": __doc__.split("Rules")[1].split("Stage B v2")[0].strip(),
           "pool_after_rules": len(pool), "tasks_after_dedup": len(cands), "quotas": quotas,
           "train": [row(r) for r, _ in train], "val": [row(r) for r, _ in val],
           "train_candidates": [row(r) for r, _ in train_cands], "val_candidates": [row(r) for r, _ in val_cands]}
    path = ROOT / "data" / "selection_v2.json"
    path.write_text(json.dumps(out, indent=1))
    for name, s in (("train", train), ("val", val)):
        print(f"{name}: {len(s)} episodes, {len({r['repo'] for r, _ in s})} repos, teachers "
              f"{dict(Counter(r['teacher'] for r, _ in s))}, categories {dict(Counter(r['category'] for r, _ in s))}, "
              f"~{sum(r['approx_tokens'] for r, _ in s) / 1e6:.1f}M tokens | thinking chars/step median "
              f"{sorted(f['thinking_chars_per_step'] for _, f in s)[len(s) // 2]:.0f} | with a recovered error "
              f"{sum(f['errors_recovered'] >= 1 for _, f in s) / max(len(s), 1):.0%} | long chains/call "
              f"{sum(f['long_chains'] for _, f in s) / max(sum(f['calls'] for _, f in s), 1):.2f}")
    print(f"candidates (with reserves): train {len(train_cands)}, val {len(val_cands)}")
    assert not {r["repo"] for r, _ in train_cands} & {r["repo"] for r, _ in val_cands}
    print("wrote", path)


if __name__ == "__main__":
    main()
