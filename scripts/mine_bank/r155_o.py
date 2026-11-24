"""r155 sk_a2o follow-up: does the model see the real-fix lines before its edit; which spot would EDIT MATERIAL need (most-shown top-k vs gold).
Run: python3 -I scripts/mine_bank/r155_o.py "$PWD" (reads data/tasks.jsonl and data/results r153-r155, writes nothing)."""
import ast, collections, glob, json, re, sys
root = sys.argv[1]
def parse(x):
    if isinstance(x, dict): return x
    try: return ast.literal_eval(str(x))
    except Exception:
        try: return json.loads(str(x))
        except Exception: return {}
gold = {}
for l in open(root + "/data/tasks.jsonl"):
    t = json.loads(l); gold[t["instance_id"]] = t["patch"]
def hunks(task):
    cur = None; out = []
    for line in gold[task].split("\n"):
        if line.startswith("+++ b/"): cur = line[6:]
        m = re.match(r"^@@ -(\d+)(?:,(\d+))?", line)
        if m: out.append((cur, int(m.group(1)), int(m.group(1)) + int(m.group(2) or 1)))
    return out
def hit(task, path, a, b): return any(p == path and s <= b and e >= a for p, s, e in hunks(task))
def dec(x):
    try: return str(json.loads(x).get("stdout", x))
    except Exception: return str(x)
c = collections.Counter()
for d in sorted(glob.glob(root + "/data/results/2026-11-2[34]_skill_r15[345]_s*")):
    by = collections.defaultdict(list)
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        r = json.loads(l); by[r["job"]].append(r)
    for job, rs in by.items():
        task = job.split("#")[0]
        if task not in gold: continue
        rs = sorted([r for r in rs if len(r["request"]["messages"]) > 1], key=lambda r: float(r["t"]))
        res = {}
        for r in rs:
            for m in r["request"]["messages"]:
                if m.get("role") == "tool": res[m.get("tool_call_id")] = dec(m.get("content"))
        edited = False; ranges = []; first_already = None; anyhit = False
        for r in rs:
            for cl in ((parse(r.get("reply")) or {}).get("message") or {}).get("tool_calls") or []:
                fn = cl.get("function") or {}
                try: ad = json.loads(fn.get("arguments") or "")
                except Exception: ad = {}
                if not isinstance(ad, dict): ad = {}
                cmd = str(ad.get("command", "")); out = res.get(cl.get("id"), "")
                if fn.get("name") == "edit_file": edited = True
                if edited: continue
                # numbered lines shown: "  123| text"
                if "a.py show" in cmd:
                    path = cmd.split("a.py show", 1)[1].split()[0]
                    nums = [int(x) for x in re.findall(r"^\s*(\d+)\|", out, re.M)]
                    if nums:
                        h = hit(task, path, min(nums), max(nums)); anyhit |= h
                        ranges.append(h)
                        if "ALREADY SHOWN" in out and first_already is None: first_already = h
        if ranges:
            c["runs"] += 1; c["gold seen before edit"] += anyhit; c["last show before edit = gold"] += ranges[-1]
            if first_already is not None: c["ALREADY SHOWN runs"] += 1; c["ALREADY SHOWN range = gold"] += first_already
print(dict(c))
# top-k most-shown spots (by show target) at the first STOP READING / at the first edit: is gold among them?
k = collections.Counter()
for d in sorted(glob.glob(root + "/data/results/2026-11-2[34]_skill_r15[345]_s*")):
    by = collections.defaultdict(list)
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        r = json.loads(l); by[r["job"]].append(r)
    for job, rs in by.items():
        task = job.split("#")[0]
        rs = sorted([r for r in rs if len(r["request"]["messages"]) > 1], key=lambda r: float(r["t"]))
        res = {}
        for r in rs:
            for m in r["request"]["messages"]:
                if m.get("role") == "tool": res[m.get("tool_call_id")] = dec(m.get("content"))
        spots = collections.OrderedDict(); done = False
        for r in rs:
            for cl in ((parse(r.get("reply")) or {}).get("message") or {}).get("tool_calls") or []:
                if done: break
                fn = cl.get("function") or {}
                try: ad = json.loads(fn.get("arguments") or "")
                except Exception: ad = {}
                if not isinstance(ad, dict): ad = {}
                cmd = str(ad.get("command", "")); out = res.get(cl.get("id"), "")
                if fn.get("name") == "edit_file" or "STOP READING" in out:
                    if spots:
                        rank = sorted(spots.items(), key=lambda kv: -kv[1][0])
                        k["runs"] += 1
                        for K in (1, 2, 3):
                            k[f"gold in top{K}"] += any(v[1] for _, v in rank[:K])
                        k["gold in any"] += any(v[1] for _, v in rank)
                        k["spots"] += len(rank)
                    done = True; break
                if "a.py show" in cmd:
                    parts = cmd.split("a.py show", 1)[1].split()
                    nums = [int(x) for x in re.findall(r"^\s*(\d+)\|", out, re.M)]
                    if nums:
                        key = (parts[0], parts[1] if len(parts) > 1 and not parts[1][0].isdigit() else str(min(nums) // 40))
                        n0, h0 = spots.get(key, (0, False))
                        spots[key] = (n0 + 1, h0 or hit(task, parts[0], min(nums), max(nums)))
print(dict(k))
