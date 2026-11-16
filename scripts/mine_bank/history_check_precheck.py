"""Step 0 for the post-edit history check (user 2026-11-16: 'yes run step 0 with both'). CPU only, no GPU.
Run: python3 -I scripts/mine_bank/history_check_precheck.py CLONE_DIR [rtest|dev16]   (repo root; network: blob-less clones of the
PUBLIC repos of the 24 test tasks; only git commands run, hooks and fsmonitor off; no repository code runs)

The check stage would run after the fixer's edit, keyed on the files and lines the fixer actually changed.
Part 1 (co-change list): for each edited source file F, the source .py files (not tests) that changed in the same
  commits as F, counted over F's last 30 commits before base_commit, that are NOT in the patch; listed when the share
  count / commits-of-F >= a cut-off (20 / 30 / 40 %), at most 3 per edited file.
  Starting points = the agents' real patches in r104 + r105 (sa2, sb1, sb2; data/results/2026-11-16_skill_sb1rt_p*,
  _sb2mf_p*). Per run: multi-file tasks -> does the list name a real-fix file missing from the patch (useful)?
  single-file tasks -> how many files does it list (all of them unneeded for this fix)?
Part 2 (line history): for the real fix's first hunk in each real-fix file that existed at base, the last commit that
  touched those lines (git log -L start,end:FILE base -1): its subject, date and the size of what the stage would print.
  Printed next to the issue title so each can be labelled related / unrelated by reading.
dev16 (user 2026-11-16: "not just the 24, add dev16"): tasks from data/tasks.jsonl (local only, never committed), patches
from every 2026-11-1* run folder that has dev16 runs. Files under docs/, docs_src/, examples/, scripts/, benchmarks/
are not source for list 1 (fastapi commits touch docs_src/*.py examples)."""
import ast, collections, glob, json, os, re, subprocess, sys
from pathlib import Path

CLONES = Path(sys.argv[1])
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$|^(docs|docs_src|examples?|scripts|benchmarks?)/")
SET = sys.argv[2] if len(sys.argv) > 2 else "rtest"
src = open("scripts/train/make_skill_arms_cells.py").read()
i = src.index("RTEST24 = [")
RT = ast.literal_eval(src[i + 10:src.index("]", i) + 1])
G = {json.loads(l)["instance_id"]: json.loads(l) for l in open("data/swe_rebench/candidates.jsonl") if json.loads(l)["instance_id"] in RT}
if SET == "dev16":
    RT = json.load(open("data/splits_public.json"))["dev16"]
    G = {json.loads(l)["instance_id"]: json.loads(l) for l in open("data/tasks.jsonl") if json.loads(l)["instance_id"] in RT}
CUTS = (0.2, 0.3, 0.4)


def git(d, *args, timeout=600):
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


def src_files(patch):
    return {f for f in re.findall(r"^\+\+\+ b/(\S+)", patch, re.M) if f.endswith(".py") and not TEST.search(f)}


def new_files(patch):
    return set(re.findall(r"^diff --git a/(\S+) b/\S+\nnew file mode", patch, re.M)) | set(re.findall(r"^--- /dev/null\n\+\+\+ b/(\S+)", patch, re.M))


def hunks(patch):
    out, f = collections.defaultdict(list), None
    for line in patch.splitlines():
        m = re.match(r"^\+\+\+ b/(\S+)", line)
        if m:
            f = m.group(1)
            continue
        m = re.match(r"^@@ -(\d+)(?:,(\d+))? ", line)
        if m and f:
            s, n = int(m.group(1)), int(m.group(2) or 1)
            out[f].append((s, s + max(n, 1) - 1))
    return out


COCH = {}


def cochange(d, base, f):
    """{other source file: count} over f's last 30 commits, and the number of those commits."""
    if (d, f) not in COCH:
        shas = git(d, "log", "--format=%H", "-30", base, "--", f).split()
        cnt = collections.Counter()
        for out in git(d, "log", "--full-diff", "--format=", "--name-only", "-30", base, "--", f).splitlines():
            if out.strip() and out != f and out.endswith(".py") and not TEST.search(out):
                cnt[out] += 1
        COCH[(d, f)] = (cnt, len(shas))
    return COCH[(d, f)]


def listed(d, base, patch, cut):
    files = src_files(patch) - new_files(patch)
    out = set()
    for f in files:
        cnt, n = cochange(d, base, f)
        top = [o for o, c in cnt.most_common() if n and c / n >= cut and o not in files][:3]
        out |= set(top)
    return out


# the agents' real patches
runs = []
FOLDERS = (sorted(glob.glob("data/results/2026-11-16_skill_sb1rt_p*") + glob.glob("data/results/2026-11-16_skill_sb2mf_p*")) if SET == "rtest"
           else sorted(glob.glob("data/results/2026-11-1*_skill_*")))
for dd in FOLDERS:
    if not os.path.exists(os.path.join(dd, "results/gen_per_task.jsonl")):
        continue
    for l in open(os.path.join(dd, "results/gen_per_task.jsonl")):
        g = json.loads(l)
        if g["instance_id"] not in RT:
            continue
        pf = os.path.join(dd, "results/gen/patches", f"{g['instance_id']}__a{g['attempt']}.diff")
        if os.path.exists(pf) and open(pf, errors="replace").read().strip():
            runs.append((g["instance_id"], g["arm"], open(pf, errors="replace").read()))

print(f"PART 1 ({SET}): co-change list after the agent's real edit ({len(runs)} patches)")
stats = {c: collections.defaultdict(list) for c in CUTS}
for iid in sorted(RT):
    g = G[iid]
    d = clone(g["repo"], g["base_commit"])
    base = g["base_commit"]
    gold = src_files(g["patch"])
    gold_old = gold - new_files(g["patch"])
    multi = len(gold) >= 2
    rr = [p for t, a, p in runs if t == iid]
    line = f"  {'multi ' if multi else 'single'} {iid[:46]:46} runs {len(rr):2}"
    for c in CUTS:
        useful, sizes = 0, []
        for p in rr:
            L = listed(d, base, p, c)
            sizes.append(len(L))
            missing = gold_old - src_files(p)
            useful += bool(L & missing)
            stats[c]["multi" if multi else "single"].append((bool(L & missing), len(L), bool(missing)))
        line += f" | >={int(c * 100)}%: useful {useful:2}/{len(rr):2} mean listed {sum(sizes) / max(1, len(sizes)):.1f}"
    print(line, flush=True)
for c in CUTS:
    m, s = stats[c]["multi"], stats[c]["single"]
    mm = [x for x in m if x[2]]
    print(f"cut >= {int(c * 100)}%: multi-file runs missing a real-fix file {len(mm)}: list names one in {sum(x[0] for x in mm)}"
          f" | single-file runs {len(s)}: list empty {sum(x[1] == 0 for x in s)}, <= 2 files {sum(x[1] <= 2 for x in s)}, mean {sum(x[1] for x in s) / max(1, len(s)):.2f}")

print(f"\nPART 2 ({SET}): last 3 commits that touched the real-fix lines (first hunk of each real-fix file existing at base)")
for iid in sorted(RT):
    g = G[iid]
    d = CLONES / g["repo"].replace("/", "__")
    base = g["base_commit"]
    title = g["problem_statement"].strip().splitlines()[0][:110]
    print(f"\n== {iid} | issue: {title}")
    hk = hunks(g["patch"])
    for f in sorted(src_files(g["patch"]) - new_files(g["patch"])):
        s, e = hk[f][0]
        out = git(d, "log", "-L", f"{s},{e}:{f}", base, "-3", "--format=@@COMMIT %h %ad %s", "--date=short", timeout=900)
        heads = [x[9:90] for x in out.splitlines() if x.startswith("@@COMMIT")]
        print(f"   {f}:{s}-{e} | {len(out)} chars | " + " || ".join(heads))
