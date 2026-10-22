# 2. Inputs: every generation output, the task set, the tokenizer.
GENS = sorted({Path(p).parent.parent for p in glob.glob('/kaggle/input/**/results/gen_per_task.jsonl', recursive=True)})
assert GENS, 'attach the generation notebook output (it has results/gen_per_task.jsonl and requests/requests.jsonl)'
for g in GENS:
    req = g / 'requests' / 'requests.jsonl'
    print(f"generation output {g}: {sum(1 for _ in open(g / 'results' / 'gen_per_task.jsonl'))} attempts | request log "
          + (f'{req.stat().st_size / 1e6:.0f} MB' if req.exists() else 'MISSING'))
_sets = sorted(Path(p).parent for p in glob.glob('/kaggle/input/**/rebench/verify_gate.json', recursive=True))
assert len(_sets) == 1, f'attach exactly one task set (rebench-final-cp312); found {_sets}'
TASKS = _sets[0] / 'tasks.jsonl'
_tok = sorted(p for p in glob.glob('/kaggle/input/models/google/gemma-4/**/gemma-4-31b-it-qat-w4a16-ct/*', recursive=True)
              if Path(p, 'tokenizer.json').exists() and Path(p, 'chat_template.jinja').exists())
assert _tok, 'attach the model google/gemma-4 -> gemma-4-31b-it-qat-w4a16-ct (its tokenizer and chat template are used)'
TOK_DIR = Path(_tok[-1])
print('task set:', TASKS, '| tokenizer:', TOK_DIR)
