# 5. LEAKAGE of every usable task's issue text and PR text: OOD-45's checker (tools/check_statement_leakage.py,
#    unchanged), base sources from the snapshots. Public target (measured in pilot 2): 44/129 = 34%.
sys.path.insert(0, str(OOD_DIR / 'tools'))
import check_statement_leakage as chk  # noqa: E402


def tar_sources(tgz):
    def base_sources(_iid, paths):
        out = {p: '' for p in paths}
        if not Path(tgz).exists():
            return out
        with tarfile.open(tgz) as tf:
            for m in tf:
                name = m.name[2:] if m.name.startswith('./') else m.name
                if name in out and m.isfile():
                    out[name] = tf.extractfile(m).read().decode('utf-8', 'replace')
        return out
    return base_sources


def residues(task, text, tgz):
    chk.base_sources = tar_sources(tgz)
    try:
        return [f.kind for f in chk.check_task(task, text or '', ()) if not f.allowed]
    except Exception as e:
        return [f'checker_error: {type(e).__name__}']


LEAK_FILE = OUT / 'leakage.json'
LEAK = json.loads(LEAK_FILE.read_text()) if LEAK_FILE.exists() else {}
usable = [i for i, _ in TASKS if gate.get(i, {}).get('usable')]
t0 = time.time()
for k, iid in enumerate(usable, 1):
    if iid in LEAK:
        continue
    r, tgz = ROWS[iid], OUT / 'snapshots' / f'{iid}.tgz'
    task = {**r, 'FAIL_TO_PASS': list(r['FAIL_TO_PASS'])}
    LEAK[iid] = {'issue': residues(task, r['problem_statement'], tgz),
                 'pr': residues(task, r['pr']['text'], tgz) if r.get('pr') else None}
    LEAK_FILE.write_text(json.dumps(LEAK, indent=1))
    print(f"[leak {k:3}/{len(usable)}] {iid[:44]:44} issue {sorted(set(LEAK[iid]['issue'])) or '-'} | pr "
          f"{sorted(set(LEAK[iid]['pr'] or [])) or ('-' if LEAK[iid]['pr'] is not None else 'no PR text')}", flush=True)
L = [LEAK[i] for i in usable if i in LEAK]
n = max(len(L), 1)
print(f'leakage checked in {time.time() - t0:.0f}s | usable {len(L)} | issue texts leak {sum(bool(x["issue"]) for x in L)} '
      f'({100 * sum(bool(x["issue"]) for x in L) / n:.0f}%) | PR texts leak {sum(bool(x["pr"]) for x in L if x["pr"] is not None)}'
      f'/{sum(x["pr"] is not None for x in L)} | both leak {sum(bool(x["issue"]) and bool(x["pr"]) for x in L)} | neither '
      f'{sum(not x["issue"] and x["pr"] is not None and not x["pr"] for x in L)} (public target 34%)')
