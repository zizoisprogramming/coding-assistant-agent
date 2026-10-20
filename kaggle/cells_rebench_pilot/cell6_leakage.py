# 6. LEAKAGE, one ruler for everything (user 2026-10-20: match the public tasks' leak share). OOD-45's checker
#    (tools/check_statement_leakage.py, unchanged; the public-task variant leakage_public.py's rules) on:
#    the 129 public texts (the target), and each pilot task's issue text and PR text. Base sources come from the
#    snapshots (the repo at base_commit): the competition's for the public tasks, cell 3's for the pilot.
import tarfile
sys.path.insert(0, str(OOD_DIR / 'tools'))
import check_statement_leakage as chk  # noqa: E402
TEST_DEF_RE = re.compile(r'^\+\s*(?:async\s+)?def\s+(test_[A-Za-z0-9_]*)\s*\(', re.M)
HUNK_CTX_RE = re.compile(r'^@@[^@]*@@\s*(?:async\s+)?def\s+(test_[A-Za-z0-9_]*)', re.M)


def tar_sources(tgz):
    def base_sources(_iid, paths):
        out = {p: '' for p in paths}  # missing file = new file, as in the OOD check
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
    return [f.kind for f in chk.check_task(task, text or '', ()) if not f.allowed]


LEAK = {'public': {}, 'issue': {}, 'pr': {}}
t0 = time.time()
pub = [json.loads(l) for l in open(DATA_DIR / 'tasks.jsonl')]
for k, t in enumerate(pub, 1):  # the public tasks ship no FAIL_TO_PASS: test functions the test patch adds (as leakage_public.py)
    f2p = [f'tests/x.py::{n}' for n in sorted(set(TEST_DEF_RE.findall(t['test_patch'])) | set(HUNK_CTX_RE.findall(t['test_patch'])))]
    LEAK['public'][t['instance_id']] = residues({**t, 'FAIL_TO_PASS': f2p}, t['problem_statement'],
                                                DATA_DIR / 'snapshots' / f"{t['instance_id']}.tgz")
    if k % 20 == 0:
        print(f'public {k}/{len(pub)} ({time.time() - t0:.0f}s)', flush=True)
for iid, _ in PILOT:
    r, tgz = ROWS[iid], OUT / 'snapshots' / f'{iid}.tgz'
    task = {**r, 'FAIL_TO_PASS': list(r['FAIL_TO_PASS'])}
    LEAK['issue'][iid] = residues(task, r['problem_statement'], tgz)
    if r.get('pr'):
        LEAK['pr'][iid] = residues(task, r['pr']['text'], tgz)
(WORKING_DIR / 'leakage.json').write_text(json.dumps(LEAK, indent=1))


def show(name, d):
    n, hit = len(d), sum(bool(v) for v in d.values())
    kinds = collections.Counter(k for v in d.values() for k in set(v))
    print(f"{name:26} {hit:3}/{n:<3} leak ({100 * hit / max(n, 1):3.0f}%) | tasks per kind: {dict(kinds.most_common())}")


print(f'leakage checked in {time.time() - t0:.0f}s (OOD-45 checker; a task counts as leaking if any residue is found)')
show('public 129 (target)', LEAK['public'])
for repo in ('fastapi', 'rich', 'requests', 'httpx'):
    show(f'  public {repo}', {k: v for k, v in LEAK['public'].items() if k.startswith(repo)})
show('pilot issue texts', LEAK['issue'])
show('pilot PR texts', LEAK['pr'])
both = [i for i in LEAK['pr'] if LEAK['pr'][i] and LEAK['issue'][i]]
print(f'pilot tasks where BOTH texts leak: {len(both)}; where neither does: '
      f"{sum(1 for i in LEAK['pr'] if not LEAK['pr'][i] and not LEAK['issue'][i])}")
