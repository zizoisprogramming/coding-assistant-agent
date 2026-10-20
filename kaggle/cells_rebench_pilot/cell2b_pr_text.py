# 2b. PR texts (option B, user 2026-10-20): the public tasks' texts are mostly the PR's own description (57%), while
#     SWE-rebench has the issue. Fetch each task's pull request (title + description) from GitHub; the number in a
#     SWE-rebench id is the PR number. Token: Add-ons -> Secrets -> GITHUB_TOKEN (fine-grained, public repos read-only);
#     without it GitHub allows 60 requests/hour (enough for this pilot). Flags how often the PR text gives the fix away.
import base64, html, urllib.error
try:
    from kaggle_secrets import UserSecretsClient
    GH_TOKEN = UserSecretsClient().get_secret('GITHUB_TOKEN')
except Exception as e:
    GH_TOKEN = None
    print('no GITHUB_TOKEN secret (', type(e).__name__, '): unauthenticated, 60 requests/hour')


def gh(path):
    req = urllib.request.Request('https://api.github.com' + path, headers={
        'Accept': 'application/vnd.github+json', **({'Authorization': f'Bearer {GH_TOKEN}'} if GH_TOKEN else {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r), r.headers.get('X-RateLimit-Remaining')


def leak_flags(text, patch):
    # What only the fix can supply (a lexical subset of OOD-45's checker): a patched file's name, a verbatim added
    # code line, or a function / class the patch defines.
    low = text.lower()
    files = re.findall(r'^\+\+\+ b/(\S+)', patch, re.M)
    added = [l[1:].strip() for l in patch.splitlines() if l.startswith('+') and not l.startswith('+++')]
    removed = '\n'.join(l[1:] for l in patch.splitlines() if l.startswith('-') and not l.startswith('---'))
    new_defs = {m for l in added for m in re.findall(r'^(?:async\s+)?(?:def|class)\s+(\w+)', l) if m not in removed}
    return {'file': any(Path(f).name.lower() in low for f in files),
            'code_line': any(len(l) >= 20 and not l.startswith('#') and l in text for l in added),
            'new_def': sorted(d for d in new_defs if re.search(rf'\b{re.escape(d)}\b', text))}


pr_ok = 0
for k, (iid, _) in enumerate(PILOT, 1):
    r = ROWS[iid]
    num = int(iid.rsplit('-', 1)[1])
    try:
        try:
            d, left = gh(f"/repos/{r['repo']}/pulls/{num}")
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
            # Moved repo: the name now holds a fork and the PRs live in its source (e.g. dr-prodigy/python-holidays ->
            # vacanza/holidays), or the repo was renamed (/repos/{name} follows the rename).
            info = gh(f"/repos/{r['repo']}")[0]
            moved = (info.get('source') or {}).get('full_name') or info.get('full_name') or r['repo']
            if moved.lower() == r['repo'].lower():
                raise
            d, left = gh(f"/repos/{moved}/pulls/{num}")
        text = (d.get('title') or '').strip() + '\n\n' + (d.get('body') or '').strip()
        r['pr'] = {'number': num, 'title': d.get('title'), 'body': d.get('body') or '', 'merged': bool(d.get('merged_at')),
                   'text': text.strip(), 'leak': leak_flags(text, r['patch'])}
        pr_ok += 1
        lk = r['pr']['leak']
        print(f"[{k:2}/{len(PILOT)}] {iid[:44]:44} merged={r['pr']['merged']!s:5} body={len(r['pr']['body']):5} chars "
              f"leak: file={lk['file']!s:5} code={lk['code_line']!s:5} defs={lk['new_def']} | {(d.get('title') or '')[:60]!r}"
              f" (rate left {left})", flush=True)
    except Exception as e:
        r['pr'] = None
        print(f"[{k:2}/{len(PILOT)}] {iid[:44]:44} PR fetch failed: {e!r}"[:200], flush=True)
got = [ROWS[i]['pr'] for i, _ in PILOT if ROWS[i].get('pr')]
print(f'PR texts: {pr_ok}/{len(PILOT)} | merged {sum(p["merged"] for p in got)} | empty description '
      f'{sum(not p["body"].strip() for p in got)} | names a patched file {sum(p["leak"]["file"] for p in got)} | '
      f'quotes added code {sum(p["leak"]["code_line"] for p in got)} | names a new def/class {sum(bool(p["leak"]["new_def"]) for p in got)}')
