# 2b. Domains (GitHub topics) -> SELECT this part's tasks -> their PR texts. One line per repo / task.
import concurrent.futures as cf, urllib.error


def gh(path, tries=4):
    for k in range(tries):
        req = urllib.request.Request('https://api.github.com' + path, headers={
            'Accept': 'application/vnd.github+json', **({'Authorization': f'Bearer {GH_TOKEN}'} if GH_TOKEN else {})})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r), r.headers.get('X-RateLimit-Remaining')
        except urllib.error.HTTPError as e:
            if e.code in (403, 429, 500, 502, 503) and k < tries - 1:
                time.sleep(20 * (k + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            if k == tries - 1:
                raise
            time.sleep(10)


# Public-like domains: what the graded tasks are (fastapi = web/API framework, rich = terminal rendering,
# requests/httpx = HTTP clients) plus the libraries they lean on (pydantic-style data models / config / parsing).
DOMAINS = {
    'web_api': {'web', 'api', 'rest', 'restful', 'rest-api', 'asgi', 'wsgi', 'web-framework', 'flask',
                'django', 'fastapi', 'starlette', 'aiohttp', 'tornado', 'sanic', 'graphql', 'openapi', 'swagger',
                'websocket', 'websockets', 'server', 'http-server', 'backend', 'microservice', 'webapp', 'jinja2'},
    'http_client': {'http', 'http-client', 'client', 'requests', 'httpx', 'urllib3', 'sdk', 'api-client',
                    'api-wrapper', 'wrapper', 'oauth', 'oauth2', 'scraping', 'scraper',
                    'crawler', 'streaming', 'proxy', 'webhook'},
    'cli_terminal': {'cli', 'terminal', 'console', 'command-line', 'commandline', 'command-line-tool', 'tui', 'shell',
                     'ansi', 'color', 'colors', 'progress', 'progress-bar', 'pretty-print', 'formatting',
                     'formatter', 'markdown', 'table', 'tables', 'logging', 'argparse', 'click', 'prompt', 'repl'},
    'data_models': {'validation', 'serialization', 'deserialization', 'json', 'schema', 'json-schema', 'pydantic',
                    'dataclasses', 'dataclass', 'config', 'configuration', 'settings', 'yaml', 'toml', 'typing',
                    'type-hints', 'marshmallow', 'attrs', 'orm', 'parser', 'parsing', 'template', 'templating'},
}


def domain_of(info, repo):
    if not info or info.get('missing'):
        return 'other', []
    topics = [t.lower() for t in info.get('topics') or []]
    desc = re.sub(r'https?://\S+', ' ', info.get('description') or '')  # a URL's 'http' says nothing about the domain
    words = re.findall(r'[a-z0-9]+(?:-[a-z0-9]+)*', (desc + ' ' + repo.split('/')[1]).lower())
    words += [a + '-' + b for a, b in zip(words, words[1:])]
    score = {d: 2 * sum(t in kw for t in topics) + sum(w in kw for w in words) for d, kw in DOMAINS.items()}
    best = max(score, key=score.get)
    hits = sorted({t for t in topics + words for kw in DOMAINS.values() if t in kw})
    return (best if score[best] >= 1 else 'other'), hits


REPO_LOG = OUT / 'repos.jsonl'
REPO_INFO = {json.loads(l)['repo']: json.loads(l)['info'] for l in open(REPO_LOG)} if REPO_LOG.exists() else {}


def repo_info(repo):
    if repo in REPO_INFO:
        return REPO_INFO[repo]
    try:
        d, _ = gh(f'/repos/{repo}')
        info = {k: d.get(k) for k in ('full_name', 'description', 'topics', 'archived', 'fork', 'stargazers_count', 'language')}
        info['source'] = (d.get('source') or {}).get('full_name')
        if d.get('fork') and info['source']:  # moved repo: the name now holds a fork; the topics live in the source
            s, _ = gh(f"/repos/{info['source']}")
            info['topics'], info['description'] = s.get('topics'), s.get('description') or info['description']
    except urllib.error.HTTPError as e:
        info = {'missing': True, 'http': e.code}
    except Exception as e:
        info = {'missing': True, 'error': f'{type(e).__name__}: {str(e)[:100]}'}
    with open(REPO_LOG, 'a') as fh:
        fh.write(json.dumps({'repo': repo, 'info': info}) + '\n')
    return info


repos = sorted({r['repo'] for r in ROWS.values()})
t0 = time.time()
with cf.ThreadPoolExecutor(8) as ex:
    for k, (repo, info) in enumerate(zip(repos, ex.map(repo_info, repos)), 1):
        REPO_INFO[repo] = info
        dom, hits = domain_of(info, repo)
        print(f"[repo {k:3}/{len(repos)}] {repo[:45]:45} {dom:12} | {', '.join(hits[:6])}"
              + (f" | MISSING {info}" if info.get('missing') else ''), flush=True)
DOMAIN = {r: domain_of(REPO_INFO[r], r)[0] for r in repos}
print(f'repos classified in {time.time() - t0:.0f}s:', dict(collections.Counter(DOMAIN.values())))
print('pool tasks by domain:', dict(collections.Counter(DOMAIN[ROWS[i]['repo']] for i in LEVEL)))

# SELECT: one task from every repo first, then a 2nd, ... (max CAP new tasks per repo), under two quotas:
# level (10% large; core strata in the pool's difficulty proportions) and domain (MATCH_SHARE public-like).
rng = random.Random(SEED)
ids = sorted(LEVEL)
rng.shuffle(ids)
nth, seen = {}, collections.Counter()
for i in ids:
    seen[ROWS[i]['repo']] += 1
    nth[i] = seen[ROWS[i]['repo']]
order = sorted(ids, key=lambda i: nth[i])  # stable: random within each round
n_large = round(0.10 * N_TARGET)
core = collections.Counter(v for v in LEVEL.values() if v != 'large')
lv_want = {lv: round((N_TARGET - n_large) * c / sum(core.values())) for lv, c in core.items()}
lv_want['core d1'] = lv_want.get('core d1', 0) + N_TARGET - n_large - sum(lv_want.values())
lv_want['large'] = n_large
dom_want = {'match': round(MATCH_SHARE * N_TARGET), 'other': N_TARGET - round(MATCH_SHARE * N_TARGET)}
dkind = lambda i: 'other' if DOMAIN[ROWS[i]['repo']] == 'other' else 'match'  # noqa: E731
chosen, per_repo = [], collections.Counter()
for strict_level, strict_domain in ((True, True), (True, False), (False, False)):
    for i in order:
        if len(chosen) >= N_TARGET:
            break
        if i in chosen or per_repo[ROWS[i]['repo']] >= CAP:
            continue
        if strict_level and lv_want[LEVEL[i]] <= 0:
            continue
        if strict_domain and dom_want[dkind(i)] <= 0:
            continue
        chosen.append(i)
        per_repo[ROWS[i]['repo']] += 1
        lv_want[LEVEL[i]] -= 1
        dom_want[dkind(i)] -= 1
    print(f'after pass (level quota={strict_level}, domain quota={strict_domain}): {len(chosen)} chosen | '
          f'unfilled level {dict((k, v) for k, v in lv_want.items() if v > 0)} domain {dict((k, v) for k, v in dom_want.items() if v > 0)}')
TASKS = sorted((i, LEVEL[i]) for i in chosen)
for i in chosen:
    ROWS[i]['domain'] = DOMAIN[ROWS[i]['repo']]
    ROWS[i]['topics'] = (REPO_INFO[ROWS[i]['repo']] or {}).get('topics') or []
print(f'SELECTED {len(TASKS)} tasks from {len(per_repo)} repos | levels', dict(sorted(collections.Counter(l for _, l in TASKS).items())),
      '| domains', dict(collections.Counter(ROWS[i]['domain'] for i in chosen)),
      f"| public-like {100 * sum(dkind(i) == 'match' for i in chosen) / max(len(chosen), 1):.0f}%",
      '| tasks per repo', dict(sorted(collections.Counter(per_repo.values()).items())))


def leak_flags(text, patch):
    low = text.lower()
    files = re.findall(r'^\+\+\+ b/(\S+)', patch, re.M)
    added = [l[1:].strip() for l in patch.splitlines() if l.startswith('+') and not l.startswith('+++')]
    removed = '\n'.join(l[1:] for l in patch.splitlines() if l.startswith('-') and not l.startswith('---'))
    new_defs = {m for l in added for m in re.findall(r'^(?:async\s+)?(?:def|class)\s+(\w+)', l) if m not in removed}
    return {'file': any(Path(f).name.lower() in low for f in files),
            'code_line': any(len(l) >= 20 and not l.startswith('#') and l in text for l in added),
            'new_def': sorted(d for d in new_defs if re.search(rf'\b{re.escape(d)}\b', text))}


PR_LOG = OUT / 'pr.jsonl'
PR_DONE = {json.loads(l)['id']: json.loads(l)['pr'] for l in open(PR_LOG)} if PR_LOG.exists() else {}


def pr_text(iid):
    if iid in PR_DONE:
        return PR_DONE[iid], 'cached'
    r, num = ROWS[iid], int(iid.rsplit('-', 1)[1])
    try:
        info = REPO_INFO.get(r['repo']) or {}
        try:
            d, left = gh(f"/repos/{r['repo']}/pulls/{num}")
        except urllib.error.HTTPError as e:
            # Moved repo: the name now holds a fork and the PRs live in its source, or the repo was renamed.
            moved = info.get('source') or info.get('full_name') or r['repo']
            if e.code != 404 or moved.lower() == r['repo'].lower():
                raise
            d, left = gh(f'/repos/{moved}/pulls/{num}')
        text = ((d.get('title') or '').strip() + '\n\n' + (d.get('body') or '').strip()).strip()
        pr = {'number': num, 'title': d.get('title'), 'body': d.get('body') or '', 'merged': bool(d.get('merged_at')),
              'text': text, 'leak': leak_flags(text, r['patch'])}
    except Exception as e:
        pr, left = None, f'{type(e).__name__}: {str(e)[:120]}'
    with open(PR_LOG, 'a') as fh:
        fh.write(json.dumps({'id': iid, 'pr': pr}) + '\n')
    return pr, left


with cf.ThreadPoolExecutor(8) as ex:
    for k, (iid, (pr, left)) in enumerate(zip([i for i, _ in TASKS], ex.map(lambda t: pr_text(t[0]), TASKS)), 1):
        ROWS[iid]['pr'] = pr
        print(f"[pr {k:3}/{len(TASKS)}] {iid[:44]:44} " + (
            f"merged={pr['merged']!s:5} body={len(pr['body']):5} | {(pr['title'] or '')[:60]!r} (rate left {left})"
            if pr else f'FAILED {left}'), flush=True)
got = [ROWS[i]['pr'] for i, _ in TASKS if ROWS[i].get('pr')]
print(f'PR texts: {len(got)}/{len(TASKS)} | merged {sum(p["merged"] for p in got)} | empty description '
      f'{sum(not p["body"].strip() for p in got)} | names a patched file {sum(p["leak"]["file"] for p in got)} | '
      f'quotes added code {sum(p["leak"]["code_line"] for p in got)} | names a new def/class {sum(bool(p["leak"]["new_def"]) for p in got)}')
