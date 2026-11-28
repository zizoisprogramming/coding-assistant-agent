# 1. COLLECTOR setup (scripts/train/make_collect_cells.py): CPU, Internet ON, the Kaggle token from a Kaggle secret.
import hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path
from kaggle_secrets import UserSecretsClient
try:
    os.environ['KAGGLE_API_TOKEN'] = UserSecretsClient().get_secret('KAGGLE_API_TOKEN')  # never printed
except Exception as e:
    raise SystemExit('Add-ons -> Secrets: add a secret named KAGGLE_API_TOKEN (your Kaggle API token) and tick it for this '
                     f'notebook; Settings -> Internet ON. ({type(e).__name__})')
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '--upgrade', 'kaggle', 'six'], check=True)
r = subprocess.run(['kaggle', '--version'], capture_output=True, text=True)
print('kaggle CLI:', (r.stdout or r.stderr).strip())
WORK = Path('/kaggle/working/runs')
WORK.mkdir(parents=True, exist_ok=True)
SOURCES = {'r165_A': 'ziad23samer/fork-of-fork-of-generation-all-shards-gpu/119', 'r165_B': 'engziadsamer/arms-again/30', 'r166_D': 'ziad23samer/fork-of-fork-of-generation-all-shards-gpu/121', 'r166_A': 'ziad23samer/fork-of-fork-of-generation-all-shards-gpu/122', 'r166_C': 'engziadsamer/arms-again/31', 'r166_B': 'ziadsamer/fork-of-generation-all-shards-gpu', 'r167_A': 'ziad23samer/fork-of-fork-of-generation-all-shards-gpu/123', 'r167_B': 'engziadsamer/arms-again/32', 'r168_A': 'ziad23samer/fork-of-fork-of-generation-all-shards-gpu/125', 'r168_B': 'fatmazenhom/generation-shard-4-gpu'}
EXPECTED = {'r165_A': {'gen_md5': '2d2975a622a9d6ce6d12226ef97259cf', 'phases_md5': '9cbe20f6bc6622b928f9d1179d7c342c', 'rows': 165}, 'r165_B': {'gen_md5': '823dcffc4aafa328251f7f0e2a44477b', 'phases_md5': 'c1cceb2812f046c1ee5819974450b569', 'rows': 165}, 'r166_D': {'gen_md5': '849ef172a3cdaa04f2505cbf9d581234', 'phases_md5': 'ede61c933357c9c55816879f9dab65b6', 'rows': 132}, 'r166_A': {'gen_md5': '45d62e60897bffb3df5b2cab3ee7884d', 'phases_md5': 'efe8afe30289c7c74d70bbc04ae5fbb2', 'rows': 49}, 'r166_C': {'gen_md5': '390562149c00a915a702137630572614', 'phases_md5': 'c7a898cadfc8bcc45f98c331310beed4', 'rows': 126}, 'r166_B': {'gen_md5': '71a1b9a226c57b6381aefacb10cac3cc', 'phases_md5': 'bae7f1574a722bc2229bd12d979df748', 'rows': 74}, 'r167_A': {'gen_md5': 'e1c62f0d5609b59746bd07642a265eb5', 'phases_md5': '09ea002b962598417ef3538c19f06e40', 'rows': 9}, 'r167_B': {'gen_md5': '13b59d9d1ff714193b3e6ba5a122bd1a', 'phases_md5': 'ff1d8e967814e2c9b5844e40eca4ac9d', 'rows': 27}, 'r168_A': {'gen_md5': 'c48d2bddf5117d754a8466a87598cef9', 'phases_md5': 'fd89c97abffdeafaae3777249d059d43', 'rows': 240}, 'r168_B': {'gen_md5': 'eb979bc3ad9bab24990514425fb352c9', 'phases_md5': '71909d53dff54c3e2876c88545679baf', 'rows': 240}}  # md5 of our local copies (the run each version must hold)
PATTERN = r'.*(gen_per_task\.jsonl|phases\.json|requests\.jsonl|\.diff)$'
print(f'{len(SOURCES)} runs to collect, {sum(e["rows"] for e in EXPECTED.values())} result rows expected')
