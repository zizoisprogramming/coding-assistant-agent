"""Writes kaggle/cells_merge/: ONE training file from every self-distillation source (CPU, free; before the GPU training).

    python3 scripts/train/make_merge_cells.py

Sources, attached as inputs, in any mix:
  - samples outputs (a folder selfdistill/<name>/ with samples.pt + metrics.jsonl + status.jsonl), e.g. filtration-cpu
  - generation outputs (results/gen_per_task.jsonl + requests/requests.jsonl): turned into samples here first, with the
    same code as kaggle/cells_samples (e.g. when a samples output was replaced by a later version of its notebook);
    a re-grade output (results/regrade/gen_per_task.jsonl) is applied as there.
Rules (user 2026-10-21/24): one run per task across all sources (the one with the fewest model replies); segments over
MAX_LEN tokens dropped; never a test task; leaking texts capped at LEAK_CAP of the training runs (public share 34%);
validation = up to VAL_RUNS runs (by the samples' own hash split), the rest of the validation runs go to training.
Output: /kaggle/working/merged/samples.pt (+ report.json): what the training notebook attaches.
Inputs: the samples / generation outputs, the task set(s) the generation outputs need (rebench-final-cp312 for the
first runs), the model google/gemma-4 -> gemma-4-31b-it-qat-w4a16-ct (tokenizer only).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/train"))
import make_samples_cells as S  # noqa: E402

OUT = ROOT / "kaggle/cells_merge"

CELL3 = r'''# 3. MERGE every source into one training file. Prints what each rule removes and the final totals.
import hashlib, random
import torch

MAX_LEN, LEAK_CAP, VAL_RUNS, SEED = 16384, 0.34, 16, 20261024
SRC = sorted({Path(p).parent for p in glob.glob('/kaggle/input/**/selfdistill/*/samples.pt', recursive=True)}
             | {Path(p).parent for p in glob.glob('/kaggle/working/selfdistill/*/samples.pt')})
assert SRC, 'no samples found: attach samples outputs or generation outputs'
runs = {}  # (source, episode_id) -> {'segs': [...], 'meta': metrics row}
for d in SRC:
    meta = {(m['instance_id'], f"a{m['attempt']}"): m for m in map(json.loads, open(d / 'metrics.jsonl'))}
    att = {s['id']: s['attempt'] for s in map(json.loads, open(d / 'status.jsonl'))}
    segs = torch.load(d / 'samples.pt')
    for s in segs:
        runs.setdefault((str(d), s['episode_id']), {'segs': [], 'meta': meta.get((s['episode_id'], att.get(s['episode_id'])), {})})['segs'].append(s)
    print(f"source {str(d)[-70:]}: {len({s['episode_id'] for s in segs})} runs, {len(segs)} segments, "
          f"{sum(len(s['input_ids']) for s in segs) / 1e6:.2f}M tokens")
n0 = len(runs)
# never a test task (the samples filter already excludes them; checked again here)
runs = {k: v for k, v in runs.items() if v['meta'].get('split', 'train') != 'test'}
print(f'test-task runs removed: {n0 - len(runs)}')
# one run per task: the one with the fewest model replies
best = {}
for (src, eid), v in sorted(runs.items()):
    v['replies'] = sum(s['replies'] for s in v['segs'])
    if eid not in best or v['replies'] < best[eid]['replies']:
        best[eid] = dict(v, src=src)
print(f'one run per task: {len(runs)} runs -> {len(best)} tasks')
# segments over MAX_LEN
long = sum(1 for v in best.values() for s in v['segs'] if len(s['input_ids']) > MAX_LEN)
for v in best.values():
    v['segs'] = [s for s in v['segs'] if len(s['input_ids']) <= MAX_LEN]
best = {k: v for k, v in best.items() if v['segs']}
print(f'segments over {MAX_LEN} tokens dropped: {long} (tasks left {len(best)})')
# validation: up to VAL_RUNS of the runs the samples marked val (stable hash order); the other val runs train
val_ids = sorted((k for k, v in best.items() if v['segs'][0]['split'] == 'val'),
                 key=lambda k: hashlib.sha1(k.encode()).hexdigest())
keep_val = set(val_ids[:VAL_RUNS])
print(f'validation: {len(keep_val)} runs kept as validation, {len(val_ids) - len(keep_val)} moved to training')
# leaking texts: at most LEAK_CAP of the training runs (OOD and public texts count as not leaking)
train_ids = sorted(k for k in best if k not in keep_val)
leaky = [k for k in train_ids if best[k]['meta'].get('leak')]
max_leaky = int(LEAK_CAP * (len(train_ids) - len(leaky)) / (1 - LEAK_CAP))
rng = random.Random(SEED)
rng.shuffle(leaky)
drop = set(leaky[max_leaky:])
print(f'leaking texts: {len(leaky)}/{len(train_ids)} training runs ({100 * len(leaky) / max(len(train_ids), 1):.0f}%) -> '
      f'dropped {len(drop)} to reach <= {100 * LEAK_CAP:.0f}%')
out = []
for k in sorted(best):
    if k in drop:
        continue
    split = 'val' if k in keep_val else 'train'
    for s in best[k]['segs']:
        out.append(dict(s, split=split, source=best[k]['src'].rsplit('/', 1)[-1]))
M = Path('/kaggle/working/merged')
M.mkdir(parents=True, exist_ok=True)
torch.save(out, M / 'samples.pt')
rep = {}
for split in ('train', 'val'):
    s = [x for x in out if x['split'] == split]
    tok = sum(len(x['input_ids']) for x in s)
    rep[split] = {'runs': len({x['episode_id'] for x in s}), 'segments': len(s), 'tokens': tok,
                  'trained_tokens': sum(int(x['labels_mask'].sum()) for x in s),
                  'by_category': dict(collections.Counter(best[e]['segs'][0].get('category') for e in {x['episode_id'] for x in s})),
                  'by_source': dict(collections.Counter(x['source'] for x in s))}
    print(f"{split.upper()}: {rep[split]['runs']} runs, {len(s)} segments, {tok / 1e6:.2f}M tokens "
          f"({rep[split]['trained_tokens'] / 1e6:.2f}M trained) | {rep[split]['by_category']}")
hours = rep['train']['tokens'] / 60 / 3600
rep['estimate'] = f'one epoch at ~60 tok/s (31B probe): {hours:.1f} h of real time, ~{2 * hours:.0f} h of GPU quota'
print('==>', rep['estimate'], '| wrote', M / 'samples.pt')
(M / 'report.json').write_text(json.dumps(rep, indent=1))
'''


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cell1.py").write_text((ROOT / "kaggle/cells_samples/cell1.py").read_text())
    c2 = (ROOT / "kaggle/cells_samples/cell2.py").read_text()
    old = "assert GENS, 'attach the generation notebook output (it has results/gen_per_task.jsonl and requests/requests.jsonl)'\n"
    assert c2.count(old) == 1
    c2 = c2.replace(old, "# (merge: generation outputs are optional, attached samples outputs are used as they are)\n")
    (OUT / "cell2.py").write_text(c2)
    (OUT / "cell2b_samples.py").write_text((ROOT / "kaggle/cells_samples/cell3_samples.py").read_text().replace(
        "# 3. Episodes -> cut", "# 2b. (only for attached GENERATION outputs) Episodes -> cut", 1))
    (OUT / "cell3_merge.py").write_text(CELL3)
    print("wrote", OUT.relative_to(ROOT), sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
