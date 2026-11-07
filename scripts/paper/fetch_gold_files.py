"""Download the files each task's real fix changes, at its base commit, from public GitHub, into data/analysis/gold_files (gitignored). Files are only read as text."""
import json, os, re, time, urllib.request
T = [json.loads(l) for l in open("data/tasks.jsonl")]
n = miss = 0
for t in T:
    for g in re.findall(r"^\+\+\+ b/(\S+)", t["patch"], re.M):
        out = f"data/analysis/gold_files/{t['instance_id']}/{g}"
        if os.path.exists(out): continue
        url = f"https://raw.githubusercontent.com/{t['repo']}/{t['base_commit']}/{g}"
        try:
            body = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "research-script"}), timeout=30).read()
        except Exception:
            miss += 1  # a new file in the fix has no base version
            continue
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, "wb").write(body)
        n += 1
        time.sleep(0.05)
print("fetched", n, "missing (new files in the fix)", miss)
