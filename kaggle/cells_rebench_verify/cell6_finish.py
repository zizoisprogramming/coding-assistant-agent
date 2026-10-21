# 6. FINISH: the dataset. tasks.jsonl = tasks that passed the snapshot check and the offline re-gate; README.md;
#    everything else pruned. Then: Output -> New Dataset -> make it PUBLIC (generation runs on the other account).
final = [i for i in sorted(ROWS) if i not in SNAP_BAD and gate.get(i, {}).get('usable')]
dropped = {i: ('snapshot: ' + '; '.join(SNAP_BAD[i]) if i in SNAP_BAD else 'not gated (deadline)' if i not in gate else
               'gate: ' + (gate[i].get('why') or f"gold {'/'.join(gate[i].get('gold_runs', []))} empty {gate[i].get('empty')}"))[:160]
           for i in sorted(ROWS) if i not in final}
with open(OUT / 'tasks.jsonl', 'w') as fh:
    for i in final:
        row = {k: v for k, v in ROWS[i].items() if k != 'requirements'}
        fh.write(json.dumps({**row, 'gate': gate[i]}) + '\n')
for p in (OUT / 'snapshots').glob('*.tgz'):
    if p.stem not in final:
        p.unlink()
manifest = {i: built[i]['wheels'] for i in final}
(OUT / 'wheels' / WHEEL_SET / 'manifest.json').write_text(json.dumps(manifest, indent=1))
need = {w for ws in manifest.values() for w in ws}
for p in HOUSE.glob('*.whl'):
    if p.name not in need:
        p.unlink()
for f in ('gate.json', 'gate_env_install.jsonl'):
    (OUT / f).rename(OUT / f'verify_{f}') if (OUT / f).exists() else None
(OUT / 'dropped.json').write_text(json.dumps(dropped, indent=1))

F = [ROWS[i] for i in final]
n = max(len(F), 1)
share = lambda pred: f'{sum(1 for r in F if pred(r))} ({100 * sum(1 for r in F if pred(r)) / n:.0f}%)'  # noqa: E731
summary = {
    'tasks': len(F), 'repos': len({r['repo'] for r in F}),
    'domain': dict(collections.Counter(r['domain'] for r in F)), 'level': dict(sorted(collections.Counter(r['level'] for r in F).items())),
    'text': dict(collections.Counter(r['text_kind'] for r in F)), 'leaking text': share(lambda r: r['leak']),
    'unfair tests': share(lambda r: r['unfair_names']), 'env_partial': share(lambda r: r['env_partial']),
    'public-like domain': share(lambda r: r['domain'] != 'other'),
}
print('FINAL', json.dumps(summary))
print(f'dropped {len(dropped)}:', json.dumps(dropped, indent=1)[:3000])
(OUT / 'README.md').write_text(f"""# SWE-rebench Python tasks, re-gated for the Gemma 4 Developer Agent harness

{len(F)} Python bug-fix / feature tasks from {summary['repos']} GitHub repositories, rebuilt from
[nebius/SWE-rebench](https://huggingface.co/datasets/nebius/SWE-rebench) (CC-BY-4.0) for offline agent runs with the
competition harness (swegemma, subprocess sandbox) on Python {sys.version_info.major}.{sys.version_info.minor}.

Every task passed, offline (internet off), the harness's own `verify_task`: the reference fix PASSES (3 times when
built), an empty patch FAILS. Snapshots hold the repository at `base_commit` with its history up to that commit
only (checked: one branch, no remote, nothing unreachable).

Layout (same as rodrigospalma/ood45-bugfix-split, so its tools/ood45_harness.py loads it):
- `tasks.jsonl`: one task per line. `problem_statement` = the text the agent sees: the issue (`text_kind` = issue)
  or the pull request's title + description (`pr`). Labels: `domain` (from GitHub topics), `level` (`core dN` =
  <=130 changed lines with Nebius difficulty N, `large` = 131-500), `leak` (the text gives away part of the fix,
  OOD-45 checker), `unfair_names` (names the tests need that the fix creates and the text never mentions),
  `env_partial` (the editable install failed but the tests import the repo from its root), `gate` (verdicts).
- `snapshots/<instance_id>.tgz`: the repository at `base_commit`.
- `wheels/house/*.whl` + `wheels/{WHEEL_SET}/manifest.json`: every task's dependencies as wheels.
- `wheels/host/*.whl`: pytest plugins to install on the host (the harness leaves them out of task wheel sets).

Summary: {json.dumps(summary)}

Licenses: task metadata from SWE-rebench (CC-BY-4.0); each snapshot keeps its repository's own license (field
`license`, permissive only). Not competition data.
""")
snap_gb = sum(p.stat().st_size for p in (OUT / 'snapshots').glob('*.tgz')) / 1e9
house_gb = sum(p.stat().st_size for p in HOUSE.glob('*.whl')) / 1e9
shutil.rmtree('/tmp/rb_gate_results', ignore_errors=True)
print(f"wrote {OUT}: {len(F)} tasks | snapshots {snap_gb:.2f} GB | wheels {len(need)} {house_gb:.2f} GB | "
      f"session {(time.time() - T_START) / 3600:.1f} h")
