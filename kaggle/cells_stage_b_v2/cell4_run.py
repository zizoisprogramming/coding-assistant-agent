# 4. STAGE B run: a ~30-episode trial first, checked automatically; the full run continues only if the trial is
#    clean (no re-run needed). Everything is written to /kaggle/working/stage_b_v2_out as it goes (crash-safe: re-running
#    this cell resumes, finished episodes are kept).
import subprocess, sys

OUT = WORKING_DIR / 'stage_b_v2_out'
OUT.mkdir(parents=True, exist_ok=True)
BASE = server_instance.base_url.rstrip('/')
BASE = BASE if BASE.endswith('/v1') else BASE + '/v1'
CMD = [sys.executable, '-u', str(CODE / 'stage_b.py'), '--selection', str(SELECTION), '--episodes', *EP_DIRS,
       '--submission', str(SUB_DIR), '--out', str(OUT), '--tokenizer-dir', str(TOK_DIR),
       '--vllm-base', BASE, '--vllm-model', str(MODEL_PATH), '--concurrency', '16', '--print-every', '5', '--rewrite-reads']


def run(extra):
    p = subprocess.Popen(CMD + extra, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    noise = ('LiteLLM', 'BerriAI', 'Unclosed client session', 'client_session:', 'Warning', 'check_feature',
             'events_compaction_config=')
    for line in p.stdout:
        if not line.strip() or any(n in line for n in noise):
            continue
        print(line, end='', flush=True)
    return p.wait()


def check_trial():
    rows = [json.loads(l) for l in (OUT / 'status.jsonl').read_text().splitlines() if l.strip()]
    runs = [json.loads(p.read_text()) for p in sorted(OUT.glob('run_*.json'), key=lambda p: p.stat().st_mtime)]
    tok = runs[-1]['tokenize_check'] if runs else {}
    first = None
    for p in OUT.glob('requests_*.jsonl'):
        for l in p.open():
            r = json.loads(l)
            if r['request'].get('tools'):
                first = r
                break
        if first:
            break
    sums = [json.loads(l) for p in OUT.glob('requests_*.jsonl') for l in p.open()]
    sums = [r for r in sums if not r['request'].get('tools')]
    good_sums = [r for r in sums if isinstance(r.get('reply'), dict) and (r['reply'].get('message') or {}).get('content')]
    checks = {
        'episodes replayed': len(rows),
        'all ok (no problems)': all(r['status'] == 'ok' for r in rows) and len(rows) > 0,
        'prompt token counts equal vLLM /tokenize': tok.get('tokenize_exact', 0) >= 20 and tok.get('tokenize_off', 1) == 0,
        # pilot #2 on this image: tool descriptions keep their docstring indentation (Python 3.13 would strip it)
        'tool declarations equal the pilot (scorer image)': first is not None and all(
            '\n        ' in t['function']['description'] for t in first['request']['tools']
            if t['function']['name'] != 'get_status'),  # get_status has a one-line docstring
        'compaction summaries written by the 12B': len(good_sums) > 0 and len(good_sums) == len(sums),
    }
    for k, v in checks.items():
        print(f'  {k}: {v}')
    for r in rows:
        if r['status'] != 'ok':
            print('  BAD', r['id'], r['problems'][:3])
    # tool declarations only change whitespace in the tool list (same in every request): a mismatch is fixed when the
    # samples are rendered, so it is reported but does not stop the run
    blocking = [k for k in checks if k not in ('episodes replayed', 'tool declarations equal the pilot (scorer image)')]
    return all(checks[k] for k in blocking)


print('=== trial (~30 episodes) ===')
run(['--quota-scale', '0.05', '--check-tokenize', '40'])
TRIAL_OK = check_trial()
print('TRIAL OK' if TRIAL_OK else 'TRIAL FAILED: full run skipped; send me stage_b_v2_out/status.jsonl and the log')
if TRIAL_OK:
    print('=== full run (selection v2) ===')
    run(['--check-tokenize', '0'])
