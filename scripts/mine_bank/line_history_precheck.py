"""Step 0 for line history AT THE EDIT (user 2026-11-18: 'the missing thing is context ... how to make use of git
history, maybe we don't ask the right question'; 'Run Step 0 now'). CPU only, no model, no repository code: only git
commands (hooks and fsmonitor off) on blob-less clones of the public repos (24 SWE-rebench test tasks + dev16).
Run: python3 -I scripts/mine_bank/line_history_precheck.py CLONE_DIR [N_RUNS_PER_TASK]   (repo root)

The 11-16 precheck (history_check_precheck.py, list 2) already read `git log -L` on the REAL-FIX lines: the last 3
commits were related in ~21-23 of 39 tasks, output up to ~4,250 chars. New here:
 A. Formatting commits filtered (they hid the history in the rest): with/without --invert-grep on style words.
 B. History from where the AGENT actually edited: each banked run's first source edit_file (old_string found in the
    base file) -> its lines -> the same command there. Does it reach a commit that also last changed the real-fix
    lines? Split solved / failed, on-target (overlaps real-fix lines) / off-target.
 C. Do those commits touch the hidden-test file (test_patch) = the test that pins this behaviour?
 D. Output size of the command the example would show (-n 2, per-commit diff capped) vs run_command's 5,000 cut."""
import ast, collections, glob, json, os, re, subprocess, sys
from pathlib import Path

CLONES = Path(sys.argv[1])
NRUNS = int(sys.argv[2]) if len(sys.argv) > 2 else 12
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$")
STYLE = ["format", "black", "style", "lint", "ruff", "isort", "pyupgrade", "pre-commit", "typing", "annotation",
         "type hint", "flake8", "pylint", "mypy", "whitespace", "reformat"]
src = open("scripts/train/make_skill_arms_cells.py").read()
i = src.index("RTEST24 = [")
RT = ast.literal_eval(src[i + 10:src.index("]", i) + 1])
DEV = json.load(open("data/splits_public.json"))["dev16"]
T = {}
for f, ids in (("data/swe_rebench/candidates.jsonl", RT), ("data/tasks.jsonl", DEV)):
    for l in open(f):
        j = json.loads(l)
        if j["instance_id"] in ids:
            T[j["instance_id"]] = j


def git(d, *args, timeout=900):
    p = subprocess.run(["git", "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null", "-C", str(d), *args],
                       capture_output=True, text=True, timeout=timeout, errors="replace")
    return p.stdout


def clone(repo, sha):
    d = CLONES / repo.replace("/", "__")
    if not d.exists():
        subprocess.run(["git", "clone", "-q", "--filter=blob:none", "--no-checkout", f"https://github.com/{repo}.git", str(d)],
                       check=True, timeout=1800)
    if not git(d, "cat-file", "-t", sha).strip():
        subprocess.run(["git", "-C", str(d), "fetch", "-q", "--filter=blob:none", "origin", sha], timeout=900)
    return d


def changed_lines(patch):
    """{file: set of base line numbers changed} for source .py files; an insertion counts the line above and below."""
    out, f, ln = collections.defaultdict(set), None, 0
    for l in patch.splitlines():
        m = re.match(r"^--- a/(\S+)", l)
        if m:
            f = m.group(1) if m.group(1).endswith(".py") and not TEST.search(m.group(1)) else None
            continue
        if l.startswith("--- ") or l.startswith("+++ "):
            if l.startswith("--- /dev/null"):
                f = None
            continue
        m = re.match(r"^@@ -(\d+)(?:,(\d+))? ", l)
        if m:
            ln = int(m.group(1))
            continue
        if f is None:
            continue
        if l.startswith("-"):
            out[f].add(ln); ln += 1
        elif l.startswith("+"):
            out[f].update({max(1, ln - 1), ln})
        else:
            ln += 1
    return out


def regions(lines, gap=6):
    xs = sorted(lines); out = []
    for x in xs:
        if out and x - out[-1][1] <= gap:
            out[-1][1] = x
        else:
            out.append([x, x])
    return [tuple(r) for r in out]


CACHE = {}


def line_log(d, base, f, s, e, n=3, filt=False):
    key = (str(d), base, f, s, e, n, filt)
    if key not in CACHE:
        args = ["log", f"-L{s},{e}:{f}", f"-n{n}", "--format=COMMIT %h %ad %s", "--date=short", base]
        if filt:
            args[1:1] = ["--invert-grep", "-i"] + [f"--grep={w}" for w in STYLE]
        out = git(d, *args)
        CACHE[key] = (re.findall(r"^COMMIT (\w+) ", out, re.M), out)
    return CACHE[key]


def files_of(d, sha):
    return set(git(d, "show", "--name-only", "--format=", sha).split())


def lit(x):
    if isinstance(x, (dict, list)):
        return x
    for p in (json.loads, ast.literal_eval):
        try:
            return p(x)
        except Exception:
            pass
    return None


def first_edit(R):
    """(path, old_string) of the first edit_file on a source .py file in a run's replies (time order)."""
    for r in R:
        rep = lit(r.get("reply"))
        m = (rep or {}).get("message") if isinstance(rep, dict) else None
        for c in (lit((m or {}).get("tool_calls")) or []) if m else []:
            fn = c.get("function", {})
            if fn.get("name") != "edit_file":
                continue
            a = lit(fn.get("arguments")) or {}
            p = str(a.get("filepath", a.get("path", ""))).replace("/workspace/", "").lstrip("./")
            if p.endswith(".py") and not TEST.search(p) and a.get("old_string"):
                return p, a["old_string"]
    return None


# ---- bank runs per task (every 31B arm), first source edit
runs = collections.defaultdict(list)
for per in sorted(glob.glob("data/results/2026-11-1*/**/gen_per_task.jsonl", recursive=True)):
    d = per.split("/")[2]
    rq = f"data/results/{d}/requests/requests.jsonl"
    if not os.path.exists(rq):
        continue
    res = {}
    for l in open(per):
        g = json.loads(l)
        if g.get("arm") and g["instance_id"] in T:
            res[g["instance_id"] + "#a" + str(g.get("attempt"))] = g
    if not res:
        continue
    J = collections.defaultdict(list)
    for l in open(rq, errors="replace"):
        if '"job"' not in l:
            continue
        try:
            r = json.loads(l)
        except Exception:
            continue
        if r.get("job") in res:
            J[r["job"]].append(r)
    for job, R in J.items():
        g = res[job]
        R.sort(key=lambda r: float(r["t"]))
        fe = first_edit(R)
        if fe:
            runs[g["instance_id"]].append(dict(arm=g["arm"], solved=g.get("resolved") in (True, "True"), path=fe[0], old=fe[1]))
print(f"bank: {sum(len(v) for v in runs.values())} runs with a first source edit on {len(runs)} tasks", flush=True)

rows, agent_rows = [], []
for iid in sorted(T):
    t = T[iid]
    try:
        d = clone(t["repo"], t["base_commit"])
    except Exception as ex:
        print(f"  {iid}: clone failed {ex}", flush=True)
        continue
    base = t["base_commit"]
    gl = changed_lines(t["patch"])
    test_files = set(re.findall(r"^\+\+\+ b/(\S+)", t.get("test_patch") or "", re.M))
    gold_commits, info = set(), []
    for f, ls in gl.items():
        if not git(d, "cat-file", "-t", f"{base}:{f}").strip():
            continue  # new file
        for s, e in regions(ls):
            c3, out3 = line_log(d, base, f, s, e, 3)
            f3, fout3 = line_log(d, base, f, s, e, 3, True)
            c2, out2 = line_log(d, base, f, s, e, 2, True)
            gold_commits |= set(c3) | set(f3)
            info.append(dict(f=f, s=s, e=e, c3=c3, f3=f3, chars2=len(out2), chars3=len(out3), fchars3=len(fout3),
                             subj=re.findall(r"^COMMIT \w+ \S+ (.*)$", fout3, re.M)))
    touches_test = sorted({c for c in gold_commits if files_of(d, c) & test_files})
    touches_other_fix = sorted({c for c in gold_commits if len(files_of(d, c) & set(gl)) >= 2})
    rows.append(dict(iid=iid, info=info, gold=gold_commits, ttest=touches_test, tfix=touches_other_fix, ntest=len(test_files)))
    first = info[0] if info else None
    print(f"\n## {iid} | {t['problem_statement'].strip().splitlines()[0][:90] if t['problem_statement'].strip() else ''}", flush=True)
    for x in info[:3]:
        print(f"   {x['f']}:{x['s']}-{x['e']} | last3 {len(x['c3'])} filtered {len(x['f3'])} | chars -n2(filt) {x['chars2']} -n3 {x['chars3']} -n3(filt) {x['fchars3']}")
        for sj in x["subj"]:
            print(f"      - {sj[:110]}")
    print(f"   commits on real-fix lines that also touch the hidden-test file: {len(touches_test)}; touch 2+ real-fix files: {len(touches_other_fix)}")
    # agent locations
    rs = runs.get(iid, [])
    rs = sorted(rs, key=lambda r: (not r["solved"], r["arm"]))[:NRUNS * 3]
    for r in rs:
        blob = git(d, "show", f"{base}:{r['path']}")
        k = blob.find(r["old"])
        if not blob or k < 0:
            agent_rows.append(dict(iid=iid, solved=r["solved"], found=False))
            continue
        s = blob.count("\n", 0, k) + 1
        e = s + r["old"].count("\n")
        on = bool(gl.get(r["path"]) and set(range(s, e + 1)) & gl[r["path"]])
        cf, out = line_log(d, base, r["path"], s, e, 2, True)
        agent_rows.append(dict(iid=iid, solved=r["solved"], found=True, on=on, file_ok=r["path"] in gl, chars=len(out),
                               shares=bool(set(cf) & gold_commits), any_hist=bool(cf),
                               ttest=bool(any(files_of(d, c) & test_files for c in cf))))

print("\n#### real-fix lines (oracle), per task")
n = len(rows)
has = [r for r in rows if any(x["f3"] for x in r["info"])]
print(f"tasks {n}; with a source hunk in an existing file {sum(bool(r['info']) for r in rows)}; with filtered history {len(has)}")
print(f"commits on the real-fix lines touch the hidden-test file: {sum(bool(r['ttest']) for r in rows)} tasks; touch 2+ real-fix files: {sum(bool(r['tfix']) for r in rows)} tasks")
ch = [x["chars2"] for r in rows for x in r["info"]]
if ch:
    ch.sort()
    print(f"output chars, -n 2 filtered, per region: median {ch[len(ch) // 2]}, p80 {ch[int(.8 * len(ch))]}, max {ch[-1]}, <= 4000: {sum(c <= 4000 for c in ch)}/{len(ch)}")
print("\n#### agent's own first-edit location (bank runs)")
A = [a for a in agent_rows if a["found"]]
print(f"runs {len(agent_rows)}, old_string found in base {len(A)}")
for lab, xs in (("solved", [a for a in A if a["solved"]]), ("failed", [a for a in A if not a["solved"]]),
                ("failed, right file, off the real-fix lines", [a for a in A if not a["solved"] and a["file_ok"] and not a["on"]]),
                ("failed, wrong file", [a for a in A if not a["solved"] and not a["file_ok"]])):
    if not xs:
        continue
    cs = sorted(a["chars"] for a in xs)
    print(f"  {lab:44} n {len(xs):4} | on real-fix lines {sum(a['on'] for a in xs):4} | any history {sum(a['any_hist'] for a in xs):4}"
          f" | shares a commit with the real-fix lines {sum(a['shares'] for a in xs):4} | touches hidden-test file {sum(a['ttest'] for a in xs):4}"
          f" | chars median {cs[len(cs) // 2]} p80 {cs[int(.8 * len(cs))]} <=4000 {sum(c <= 4000 for c in cs)}")
