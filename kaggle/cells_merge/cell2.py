# 2. Inputs: every generation output, the task set, the tokenizer.
GENS = sorted({Path(p).parent.parent for p in glob.glob('/kaggle/input/**/results/gen_per_task.jsonl', recursive=True)})
# (merge: generation outputs are optional, attached samples outputs are used as they are)
for g in GENS:
    req = g / 'requests' / 'requests.jsonl'
    print(f"generation output {g}: {sum(1 for _ in open(g / 'results' / 'gen_per_task.jsonl'))} attempts | request log "
          + (f'{req.stat().st_size / 1e6:.0f} MB' if req.exists() else 'MISSING'))
# Reference patches and labels: a generation output that ran several task sets (cells_gen_extra: our extra tasks +
# OOD-45) ships its own results/tasks_used.jsonl; the others need the task set they ran (rebench-final-cp312).
_sets = sorted(Path(p).parent for p in glob.glob('/kaggle/input/**/rebench/verify_gate.json', recursive=True))
TASKS_OF = {g: g / 'results' / 'tasks_used.jsonl' for g in GENS if (g / 'results' / 'tasks_used.jsonl').exists()}
if len(TASKS_OF) < len(GENS):
    assert len(_sets) == 1, f'attach exactly one task set (rebench-final-cp312) for {sorted(set(GENS) - set(TASKS_OF))}; found {_sets}'
    TASKS_OF.update({g: _sets[0] / 'tasks.jsonl' for g in GENS if g not in TASKS_OF})
_tok = sorted(p for p in glob.glob('/kaggle/input/models/google/gemma-4/**/gemma-4-31b-it-qat-w4a16-ct/*', recursive=True)
              if Path(p, 'tokenizer.json').exists() and Path(p, 'chat_template.jinja').exists())
assert _tok, 'attach the model google/gemma-4 -> gemma-4-31b-it-qat-w4a16-ct (its tokenizer and chat template are used)'
TOK_DIR = Path(_tok[-1])
# Re-graded rows (kaggle/cells_regrade_public output): applied to the generation output they came from.
OVERRIDE = sorted(glob.glob('/kaggle/input/**/results/regrade/gen_per_task.jsonl', recursive=True))
assert len(OVERRIDE) <= 1, f'attach at most one re-grade output; found {OVERRIDE}'
print('tasks per output:', {str(g): str(t) for g, t in TASKS_OF.items()}, '| tokenizer:', TOK_DIR, '| re-grade:', OVERRIDE)
