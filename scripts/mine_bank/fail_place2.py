"""fail_place.py, but for EVERY logged run: the edit location is read from the agent's own edit calls in requests.jsonl (many older
folders have no saved .diff). Text method: an edit is at the RIGHT SPOT when its old text (edit_file old_string / heredoc or
.replace() old text in a run_command) shares a distinctive line with the real fix's changed or context lines in the same file;
RIGHT FILE when it names a real-fix file; WRONG FILE otherwise. write_file over a real-fix file counts as right spot when the
real fix's removed lines are no longer all in the written text. Checked against the .diff method on runs that have both.
Run: python3 -I scripts/mine_bank/fail_place2.py"""
import ast, collections, glob, json, re, statistics as st, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/mine_bank")); sys.argv = [sys.argv[0]]
SCR = re.compile(r"(repro|reproduce|check|debug|scratch|\.git/agent|/tmp/|test)")
GENERIC = {"return", "else:", "pass", "try:", "finally:", ")", "]", "}", "return None", "return True", "return False", "break", "continue"}


def gold_info(patch):
    files, lines = set(), collections.defaultdict(set)
    removed = collections.defaultdict(list)
    f = None
    for l in patch.split("\n"):
        if l.startswith("+++ "):
            p = l[4:].strip(); f = p[2:] if p.startswith("b/") else None
            if f: files.add(f)
        elif f and l[:1] in ("-", " ") and not l.startswith("---"):
            s = l[1:].strip()
            if len(s) >= 8 and s not in GENERIC:
                lines[f].add(s)
                if l[:1] == "-": removed[f].append(s)
    return files, lines, removed


T = {}
for l in open(ROOT / "data/tasks.jsonl"):
    t = json.loads(l); T[t["instance_id"]] = gold_info(t["patch"])
rows = [json.loads(l) for l in open(ROOT / "data/analysis/ska2_deep_runs.jsonl")]
solvers = collections.defaultdict(set)
for r in rows:
    if r["solved"]: solvers[r["task"]].add(r["arm"])
reach = {t for t, s in solvers.items() if len(s) >= 2 and t in T}
need = collections.defaultdict(set)
for r in rows:
    if r["task"] in reach and not r["solved"] and r["patch"] > 0:
        need[r["folder"]].add(r["task"])


def parse(x):
    if isinstance(x, dict): return x
    try: return ast.literal_eval(str(x))
    except Exception:
        try: return json.loads(str(x))
        except Exception: return {}


EDITS = collections.defaultdict(list)  # (folder, task, arm) -> [(file or None, old text, full text)]
for folder, tasks in need.items():
    fp = ROOT / "data/results" / folder / "requests/requests.jsonl"
    for l in open(fp, errors="replace"):
        if not any(t in l for t in tasks): continue
        try: r = json.loads(l)
        except Exception: continue
        job = r.get("job", ""); task = job.split("#")[0]
        if task not in tasks: continue
        arm = job.split("#a")[1].split(".")[0] if "#a" in job else ""
        m = (parse(r.get("reply")) or {}).get("message") or {}
        for c in m.get("tool_calls") or []:
            fn = c.get("function") or {}
            try: a = json.loads(fn.get("arguments") or "{}")
            except Exception: a = {}
            if not isinstance(a, dict): continue
            n = fn.get("name")
            if n == "edit_file":
                p = str(a.get("filepath") or a.get("path") or "")
                if p.endswith(".py") and not SCR.search(p): EDITS[(folder, task, arm)].append((p, str(a.get("old_string", "")), "edit"))
            elif n == "write_file":
                p = str(a.get("filepath") or a.get("path") or "")
                if p.endswith(".py") and not SCR.search(p): EDITS[(folder, task, arm)].append((p, str(a.get("content", "")), "write"))
            elif n == "run_command":
                cmd = str(a.get("command", ""))
                if ("OLD_TEXT" in cmd or ".replace(" in cmd or "sed -i" in cmd) and "a.py" not in cmd:
                    paths = [p for p in re.findall(r"[\w./-]+\.py", cmd) if not SCR.search(p)]
                    EDITS[(folder, task, arm)].append((paths[0] if paths else None, cmd, "shell"))


def bucket_text(task, edits):
    files, glines, removed = T[task]
    if not edits: return None
    hit_file = False
    for p, text, kind in edits:
        gf = [g for g in files if p and (p.lstrip("./").endswith(g) or g.endswith(p.lstrip("./").replace("/workspace/", "")))]
        if kind == "shell" and not gf:
            gf = [g for g in files if g in text]
        if not gf: continue
        hit_file = True
        for g in gf:
            tl = {s.strip() for s in text.replace("\\n", "\n").split("\n")}
            if kind == "write":
                if removed[g] and not all(s in tl for s in removed[g]): return "RIGHT SPOT, WRONG LOGIC"
                continue
            if tl & glines[g]: return "RIGHT SPOT, WRONG LOGIC"
    return "WRONG SPOT" if hit_file else "WRONG FILE"


import fail_place as FP  # noqa: E402  (diff method, for the check)
agree = collections.Counter()
B = collections.defaultdict(list)
for r in rows:
    if r["task"] not in reach: continue
    if r["solved"]: b = "solved"
    elif r["patch"] == 0: b = "no source: time" if r["end"] == "time" else "no source: ended"
    else:
        b = bucket_text(r["task"], EDITS.get((r["folder"], r["task"], r["arm"]), []))
        if b is None: b = "no source: time" if r["end"] == "time" else "no source: ended"  # patch only scratch / non-source
        db = getattr(r, "bucket", None)
    r["bucket"] = b; B[r["arm"]].append(r)
# check against the diff method where a .diff exists
for a, rs in FP.B.items():
    for x in rs:
        if x["bucket"] in ("WRONG FILE", "WRONG SPOT", "RIGHT SPOT, WRONG LOGIC"):
            tb = bucket_text(x["task"], EDITS.get((x["folder"], x["task"], x["arm"]), []))
            agree[(x["bucket"], tb)] += 1
print("\n\n######## TEXT METHOD (all runs). Check vs the .diff method (diff bucket, text bucket): count")
for k, v in sorted(agree.items(), key=str): print("  ", k, v)
KEYS = ["solved", "RIGHT SPOT, WRONG LOGIC", "WRONG SPOT", "WRONG FILE", "no source: ended", "no source: time"]
print(f"\n== agents with >= 30 runs on the {len(reach)} reachable tasks, sorted by wrong edits (wrong place + wrong logic) per run")
print(f"{'arm':18}{'runs':>5}{'tasks':>6}" + "".join(f"{k[:14]:>16}" for k in KEYS) + f"{'wrong edits':>13}")
arms = sorted((a for a in B if len(B[a]) >= 30), key=lambda a: sum(x["bucket"] in KEYS[1:4] for x in B[a]) / len(B[a]))
for a in arms:
    rs = B[a]; c = collections.Counter(x["bucket"] for x in rs)
    print(f"{a:18}{len(rs):5}{len({x['task'] for x in rs}):6}" + "".join(f"{c[k] / len(rs):16.0%}" for k in KEYS) + f"{sum(c[k] for k in KEYS[1:4]) / len(rs):13.0%}")
print("\n== share of FAILED runs that are wrong edits vs no edit (where does each agent fail?)")
for a in arms:
    f = [x for x in B[a] if x["bucket"] != "solved"]
    if f: print(f"  {a:18} failed {len(f):4} | wrong edit {sum(x['bucket'] in KEYS[1:4] for x in f)/len(f):4.0%} (wrong place {sum(x['bucket'] in KEYS[2:4] for x in f)/len(f):4.0%}, wrong logic {sum(x['bucket']==KEYS[1] for x in f)/len(f):4.0%}) | no source change {sum(x['bucket'].startswith('no') for x in f)/len(f):4.0%}")


def matched(a, o="pub024"):
    ta, to = collections.defaultdict(list), collections.defaultdict(list)
    for x in B[a]: ta[x["task"]].append(x)
    for x in B[o]: to[x["task"]].append(x)
    com = sorted(set(ta) & set(to))
    if len(com) < 8: return None
    res = {}
    for k, fn in (("solved", lambda x: x["bucket"] == "solved"), ("wrong place", lambda x: x["bucket"] in ("WRONG FILE", "WRONG SPOT")),
                  ("wrong logic", lambda x: x["bucket"] == "RIGHT SPOT, WRONG LOGIC"), ("no source", lambda x: x["bucket"].startswith("no source"))):
        res[k] = (st.mean(st.mean(map(fn, ta[t])) for t in com), st.mean(st.mean(map(fn, to[t])) for t in com))
    return len(com), sum(len(ta[t]) for t in com), res


print("\n== TASK-MATCHED vs pub024 (agent | pub024; the most-run agent, so every comparison shares one yardstick), >= 8 common tasks, >= 16 runs, sorted by wrong edits")
out = []
for a in B:
    if a == "pub024" or len(B[a]) < 16: continue
    m = matched(a)
    if m: out.append((m[2]["wrong place"][0] + m[2]["wrong logic"][0], a, m))
for d, a, (nt, na, res) in sorted(out):
    print(f"  {a:18} tasks {nt:2} runs {na:3} | wrong edits {d:4.0%} vs {res['wrong place'][1]+res['wrong logic'][1]:4.0%} (place {res['wrong place'][0]:.0%}/{res['wrong place'][1]:.0%}, logic {res['wrong logic'][0]:.0%}/{res['wrong logic'][1]:.0%}) | no source {res['no source'][0]:.0%}/{res['no source'][1]:.0%} | solved {res['solved'][0]:.0%}/{res['solved'][1]:.0%}")
