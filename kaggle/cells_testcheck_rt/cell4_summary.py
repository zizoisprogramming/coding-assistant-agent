# 4. TEST CHECK SUMMARY (bars set before the run: docs/PLAN.md RUN BUILT testcheck). Send this output to Claude.
TC = [json.loads(l) for l in open(RESULTS / 'testcheck.jsonl')]
print(f'base by reverse apply {sum(r["base_method"] == "reverse" for r in TC)}, by stash {sum(r["base_method"] == "stash" for r in TC)}, cached {sum(r["base_method"] == "cached" for r in TC)}')
print(f'rows {len(TC)} | hook fired {sum(r["fired"] for r in TC)} | apply failed {sum(r["apply_error"] for r in TC)} | errors {sum(bool(r["error"]) for r in TC)}')
for kind in ('gold', 'solved', 'wrong'):
    x = [r for r in TC if r['kind'] == kind and r['fired']]
    if not x:
        continue
    picked = [r for r in x if r['files']]
    nf = [r for r in x if r['new_fail']]
    print(f"{kind:6} {len(x):3} | a test file picked {len(picked):3} (hidden-test file among them {sum(r['hidden_in_picks'] for r in picked)}) | "
          f"NEW failure {len(nf):3} = {100 * len(nf) / len(x):4.1f}% of all, {100 * len(nf) / max(1, len(picked)):4.1f}% of picked | "
          f"any failure with the patch {sum(bool(r['patched_fail']) for r in x)} | base already failing {sum(bool(r['base_fail']) for r in picked)} | no source edit {sum(r['noedit'] for r in x)}")
w = [r for r in TC if r['kind'] == 'wrong' and r['fired'] and r['touches_fix']]
print(f"wrong patches that touch a real-fix file: {len(w)} | NEW failure {sum(bool(r['new_fail']) for r in w)} = {100 * sum(bool(r['new_fail']) for r in w) / max(1, len(w)):.1f}%")
x = [r for r in TC if r['kind'] == 'wrong' and r['fired']]
s = [r for r in TC if r['kind'] == 'solved' and r['fired']]
pw, ps = sum(bool(r['new_fail']) for r in x) / max(1, len(x)), sum(bool(r['new_fail']) for r in s) / max(1, len(s))
print(f"BARS: wrong with a NEW failure {100 * pw:.1f}% (bar >= 20%) | solved with a NEW failure {100 * ps:.1f}% (bar <= 5%) -> "
      f"{'PASS: the idea has room' if pw >= 0.20 and ps <= 0.05 else 'FAIL: drop the idea'}")
print('\nper task: kind -> patches / with a NEW failure')
for iid in sorted({r['iid'] for r in TC}):
    parts = []
    for kind in ('gold', 'solved', 'wrong'):
        y = [r for r in TC if r['iid'] == iid and r['kind'] == kind and r['fired']]
        if y:
            parts.append(f"{kind} {sum(bool(r['new_fail']) for r in y)}/{len(y)}")
    g = next((r for r in TC if r['iid'] == iid and r['kind'] == 'gold'), {})
    print(f"  {iid[:46]:46} {' | '.join(parts):40} picks {g.get('files', [])} base {g.get('base', '-')}")
