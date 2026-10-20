"""Split the 129 public competition tasks (user decision 2026-10-20):

    val   = the 16 tasks of pilot #2 (mix on the 31B; Gemma's own runs = the gemma-val set)
    test  = 16 more, sampled from the remaining gradable tasks (stratified fastapi / rich, fixed seed)
    dev16 = our historic eval set (every rung / LB comparison so far): held out by default
    train = every other gradable task → self-distillation (the 31B's own resolved runs)

    python3 scripts/datasets/make_public_splits.py   → data/splits_public.json (task ids only)

Gradable = gold patch resolves and empty patch fails on Kaggle (data/results/2026-10-17_gold_check_v5; 84/113
non-dev tasks; requests and httpx are not gradable there).
"""
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEED = 20261020
DEV16 = ['fastapi_15589', 'fastapi_13920', 'fastapi_14258', 'fastapi_11194', 'fastapi_14487', 'fastapi_15280',
         'fastapi_14419', 'fastapi_15800', 'fastapi_14306', 'rich_3882', 'rich_3470', 'rich_4079', 'rich_3521',
         'rich_3934', 'rich_3468', 'rich_3180']

all_ids = [json.loads(l)['instance_id'] for l in open(ROOT / 'data/tasks.jsonl')]
gold = json.load(open(ROOT / 'data/results/2026-10-17_gold_check_v5/gold_check.json'))
gradable = sorted(i for i, g in gold.items() if g.get('usable'))
val = sorted(json.loads(l)['instance_id'] for l in open(ROOT / 'data/results/2026-10-19_gemma_val/all/status.jsonl'))
assert len(val) == 16 and set(val) <= set(gradable) and not set(val) & set(DEV16)
rest = [i for i in gradable if i not in val and i not in DEV16]
rng = random.Random(SEED)
test = []
for repo in ('fastapi', 'rich'):  # same repo mix as the remaining pool
    pool = sorted(i for i in rest if i.startswith(repo + '_'))
    k = round(16 * len(pool) / len(rest))
    test += rng.sample(pool, k)
test = sorted(test[:16])
train = sorted(i for i in rest if i not in test)
not_gradable = sorted(set(all_ids) - set(gradable) - set(DEV16))
out = {'seed': SEED, 'val': val, 'test': test, 'dev16': sorted(DEV16), 'train': train, 'not_gradable': not_gradable}
(ROOT / 'data/splits_public.json').write_text(json.dumps(out, indent=1))
for k, v in out.items():
    if k != 'seed':
        print(f"{k:13} {len(v):3}  fastapi {sum(i.startswith('fastapi') for i in v):2}  rich {sum(i.startswith('rich') for i in v):2}"
              f"  other {sum(not i.startswith(('fastapi', 'rich')) for i in v)}")
print('total', sum(len(v) for k, v in out.items() if k != 'seed'), 'of', len(all_ids))
