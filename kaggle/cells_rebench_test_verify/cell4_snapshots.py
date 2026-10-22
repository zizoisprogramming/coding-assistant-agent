# 4. SNAPSHOT CHECK (no later commit, and so no fix, can be inside): HEAD == base_commit, only refs/heads/main,
#    no remote, every commit reachable from HEAD, no unreachable objects, clean working tree. 8 at a time.
import concurrent.futures as cf, tempfile


def sh(cmd, cwd=None, timeout=600):
    try:
        r = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr)
    except subprocess.TimeoutExpired:
        return 124, f'timed out after {timeout}s'


def check_snapshot(iid):
    r = ROWS[iid]
    d = Path(tempfile.mkdtemp(prefix='snapchk_'))
    try:
        code, out = sh(f"tar xzf {OUT / 'snapshots' / (iid + '.tgz')} -C {d}")
        if code:
            return ['untar failed: ' + out[-150:]]
        bad = []
        head = sh('git rev-parse HEAD', d)[1].strip()
        if head != r['base_commit']:
            bad.append(f'HEAD {head[:12]} != base {r["base_commit"][:12]}')
        refs = sh("git for-each-ref --format='%(refname)'", d)[1].split()
        if refs != ['refs/heads/main']:
            bad.append(f'refs {refs[:4]}')
        if sh('git remote', d)[1].strip():
            bad.append('has a remote')
        n_all, n_head = sh('git rev-list --all | wc -l', d)[1].strip(), sh('git rev-list HEAD | wc -l', d)[1].strip()
        if n_all != n_head:
            bad.append(f'commits not under HEAD: {n_all} vs {n_head}')
        code, out = sh('git fsck --unreachable --no-reflogs --connectivity-only 2>/dev/null | head -5', d)
        if out.strip():
            bad.append('unreachable objects: ' + out.strip().splitlines()[0][:80])
        if sh('git stash list', d)[1].strip():
            bad.append('stash entries')
        status = sh('git status --porcelain | head -5', d)[1].strip()
        if status:
            bad.append('dirty tree: ' + status.splitlines()[0][:80])
        return bad
    finally:
        shutil.rmtree(d, ignore_errors=True)


SNAP_BAD = {}
t0 = time.time()
with cf.ThreadPoolExecutor(8) as ex:
    for k, (iid, bad) in enumerate(zip(sorted(ROWS), ex.map(check_snapshot, sorted(ROWS))), 1):
        if bad:
            SNAP_BAD[iid] = bad
        if bad or k % 25 == 0 or k == len(ROWS):
            print(f"[snap {k:3}/{len(ROWS)}] {iid[:44]:44} {'OK' if not bad else 'BAD: ' + '; '.join(bad)}", flush=True)
print(f'snapshot check done in {(time.time() - t0) / 60:.1f} min: {len(ROWS) - len(SNAP_BAD)} clean, {len(SNAP_BAD)} bad')
