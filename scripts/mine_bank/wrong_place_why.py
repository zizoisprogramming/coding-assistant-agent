"""Why do edits land in the wrong place or carry the wrong logic? (user 2026-11-23: 'we need another way to address why it gets the location
wrong at first place or makes the wrong edit'). For every logged 31B run with a saved patch: the lines the agent SAW before its first source
edit (a.py show output, read_file output, sed -n ranges; numbered lines mapped to the file named in the call), vs the real fix's changed
lines (old-file positions). Buckets as fail_place.py. Reports, per bucket: saw the real-fix lines (within 3 lines) before the first edit /
saw the real-fix file only / never opened it; and the first edit's call index. sk_a2 family and all agents.
Run: python3 -I scripts/mine_bank/wrong_place_why.py [--examples]"""
import ast, collections, glob, json, re, statistics as st, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/mine_bank")); sys.argv_ = sys.argv; sys.argv = [sys.argv[0]]
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    from fail_place import changed  # noqa: E402
EXAMPLES = "--examples" in sys.argv_
T = {}
for l in open(ROOT / "data/tasks.jsonl"):
    t = json.loads(l); T[t["instance_id"]] = (changed(t["patch"]), t["problem_statement"])
NUM = re.compile(r"(?m)^\s*(\d+)\| ")
SRC = re.compile(r"(repro|reproduce|check|debug|scratch|\.git/agent|/tmp/|test)")


def parse(x):
    if isinstance(x, dict): return x
    try: return ast.literal_eval(str(x))
    except Exception:
        try: return json.loads(str(x))
        except Exception: return {}


def norm(p):
    return str(p or "").strip().replace("/workspace/", "").lstrip("./")


def seen_lines(name, a, res):
    """(file, set(lines)) this call put in front of the model, or None."""
    c = str(a.get("command", "")) if isinstance(a, dict) else ""
    if name == "read_file":
        f = norm(a.get("filepath") or a.get("path"))
        nums = {int(x) for x in NUM.findall(res)}
        if not nums:
            s = int(a.get("start_line") or a.get("offset") or 1); nums = set(range(s, s + 150))
        return f, nums
    m = re.search(r"a\.py show\s+(\S+)", c)
    if m:
        f = norm(m.group(1).split(":")[0]); return f, {int(x) for x in NUM.findall(res)}
    m = re.search(r"sed -n ['\"]?(\d+),(\d+)p['\"]?\s+(\S+)", c)
    if m:
        return norm(m.group(3)), set(range(int(m.group(1)), int(m.group(2)) + 1))
    m = re.search(r"(?:^|\s)(?:cat|nl -ba)\s+(\S+\.py)\b", c)
    if m and "<<" not in c:
        return norm(m.group(1)), set(range(1, 400))
    return None


def is_src_edit(name, a):
    if name == "edit_file":
        p = norm(a.get("filepath") or a.get("path")); return p.endswith(".py") and not SRC.search(p)
    c = json.dumps(a)
    return ("OLD_TEXT" in c or ".replace(" in c or "sed -i" in c) and "a.py" not in c and "repro" not in c and "check.py" not in c


S = collections.defaultdict(collections.Counter); FE = collections.defaultdict(list); EX = collections.defaultdict(list)
for d in sorted(glob.glob(str(ROOT / "data/results/*/"))):
    pdir = Path(d) / "results/gen/patches"; rp = Path(d) / "requests/requests.jsonl"; gp = Path(d) / "results/gen_per_task.jsonl"
    if not pdir.exists() or not rp.exists() or not gp.exists(): continue
    G = {}
    for l in open(gp, errors="replace"):
        try: g = json.loads(l); G[g["instance_id"] + "#a" + g["attempt"]] = g
        except Exception: pass
    by = collections.defaultdict(list)
    for l in open(rp, errors="replace"):
        try: r = json.loads(l)
        except Exception: continue
        if "31b" not in str((r.get("request") or {}).get("model", "")).lower(): continue
        by[r.get("job", "")].append(r)
    for job, rs in by.items():
        g = G.get(job); task = job.split("#")[0]
        if not g or task not in T or not T[task][0]: continue
        arm = g.get("arm"); gold = T[task][0]
        pf = list(pdir.glob(f"{task}__a{g['attempt']}.diff")) or list(pdir.glob(f"{task}__a{arm}.*.diff"))
        solved = g.get("resolved") in (True, "True")
        ch = changed(pf[0].read_text(errors="replace")) if pf else {}
        if solved: b = "solved"
        elif not ch: continue
        elif not set(ch) & set(gold): b = "WRONG FILE"
        elif not any(abs(x - y) <= 5 for f in set(ch) & set(gold) for x in ch[f] for y in gold[f]): b = "WRONG SPOT"
        else: b = "RIGHT SPOT, WRONG LOGIC"
        rs = sorted([r for r in rs if len((r.get("request") or {}).get("messages") or []) > 1], key=lambda r: float(r["t"]))
        results = {}
        for r in rs:
            for mm in r["request"]["messages"]:
                if mm.get("role") == "tool": results[mm.get("tool_call_id")] = str(mm.get("content"))
        saw_line = saw_file = False; idx = 0; fe = None; edited_files = []
        for r in rs:
            for c in ((parse(r.get("reply")) or {}).get("message") or {}).get("tool_calls") or []:
                fn = c.get("function") or {}
                try: a = json.loads(fn.get("arguments") or "{}")
                except Exception: a = {}
                if not isinstance(a, dict): a = {}
                if is_src_edit(fn.get("name"), a):
                    fe = idx; break
                sl = seen_lines(fn.get("name"), a, results.get(c.get("id"), "").replace("\\n", "\n"))
                if sl:
                    f, nums = sl
                    for gf, gl in gold.items():
                        if f and (gf.endswith(f) or f.endswith(gf)):
                            saw_file = True
                            if any(abs(x - y) <= 3 for x in nums for y in gl): saw_line = True
                idx += 1
            if fe is not None: break
        fam = "sk_a2 family" if str(arm).startswith("sk_a2") else "other agents"
        seen = "saw the real-fix lines" if saw_line else "opened the file, not the lines" if saw_file else "never opened the real-fix file"
        for grp in (fam, "ALL"):
            S[(grp, b)][seen] += 1; S[(grp, b)]["n"] += 1
            if fe is not None: FE[(grp, b)].append(fe)
        if fam == "sk_a2 family" and b != "solved": EX[(b, seen)].append((Path(d).name, job, sorted(ch), sorted(gold)))
KEYS = ["saw the real-fix lines", "opened the file, not the lines", "never opened the real-fix file"]
for grp in ("sk_a2 family", "other agents", "ALL"):
    print(f"\n== {grp}: lines seen BEFORE the first source edit")
    for b in ("solved", "RIGHT SPOT, WRONG LOGIC", "WRONG SPOT", "WRONG FILE"):
        c = S[(grp, b)]; n = c["n"]
        if not n: continue
        fe = FE[(grp, b)]
        print(f"  {b:24} runs {n:4} | " + " | ".join(f"{k} {c[k] / n:4.0%}" for k in KEYS) + f" | first edit call median {st.median(fe) if fe else '-'}")
if EXAMPLES:
    for k, v in sorted(EX.items()):
        print("\n##", k, len(v))
        for x in v[:8]: print("  ", x)
