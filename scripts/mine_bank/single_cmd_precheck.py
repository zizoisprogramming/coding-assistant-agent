"""Offline check for a SINGLE-call history stage with an automatic pick (user 2026-11-19: 'group multiple things from
history in single command' -> 'yes plan it, run the offline check first'). CPU, git / grep / sed / sort only on the
sparse *.py checkouts (scratchpad wt/); nothing from the repositories is executed.
Run: python3 -I scripts/mine_bank/single_cmd_precheck.py CLONE_DIR   (repo root)

Names = the ones the model itself chose in r116 (sb7f) and r117 (sb7g) history stages (its last names='...' line),
so the pick is tested on real inputs. One bash command (written to be copied from a fenced block: no double quotes,
backticks, backslashes or braces) lists the functions that use the names (git grep -p with git's python funcname
driver), picks automatically, prints git log -L of the picks (-n 4, 12 lines per commit, 3,500 chars). Pick rules:
  count2  : the 2 'def' functions with the most hit groups
  named2  : 'def' functions whose name is one of the names first, then by hit groups; 2
  count3  : as count2, 3 functions
Scored per run, and for the model's own picks (its funcs='...' line, re-run on the checkout): a picked function is
a real-fix function (hunk headers / defs on changed lines of the real patch); the printed history shows a commit that
also changed the real-fix lines (the last 3 commits of each real-fix region at base_commit: 'gold')."""
import collections, json, os, re, subprocess, sys
from pathlib import Path

CLONES = Path(sys.argv[1])
WT = CLONES.parent / "wt"
AG = CLONES.parent / "agent_scratch1"
ENV = dict(os.environ, GIT_CONFIG_COUNT="2", GIT_CONFIG_KEY_0="core.hooksPath", GIT_CONFIG_VALUE_0="/dev/null",
           GIT_CONFIG_KEY_1="core.fsmonitor", GIT_CONFIG_VALUE_1="false", GIT_TERMINAL_PROMPT="0")
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$")
T = {}
for f in ("data/swe_rebench/candidates.jsonl", "data/tasks.jsonl"):
    for l in open(f):
        j = json.loads(l)
        T[j["instance_id"]] = j

# the single command; NAMES and PICK are filled per run (PICK = the sort / filter stage of the pick rule)
LIST = ("names='NAMES'\n"
        "a=.git/agent/attr; mkdir -p .git/agent; echo '*.py diff=python' > $a\n"
        "for nm in $names; do git -c core.attributesFile=$a grep -n -p -w -F -e $nm -- '*.py' | grep -E '^[^:=]+=[0-9]+=' | grep -v -E 'test|doc|example|benchmark'; done > .git/agent/hits\n")
HIST = ("for x in $(PICK); do\n"
        "  f=$(echo $x | cut -d@ -f1); fn=$(echo $x | cut -d@ -f2)\n"
        "  echo == $f $fn\n"
        "  git -c core.attributesFile=$a log -L ':def '$fn'[(]:'$f -n 4 --format='commit %h %ad %s' --date=short 2>&1 | grep -v -E '^(diff|index|---|[+][+][+])' | sed -E 's/^(.{150}).*/\\1/' | AWKCAP\n"
        "done > .git/agent/history\n"
        "head -c 3500 .git/agent/history; echo; echo '== HISTORY FETCHED'\n")
DEFS = "grep -E '^[^=]+=[0-9]+=[[:space:]]*(async[[:space:]]+)?def[[:space:]]' .git/agent/hits | sed -E 's/^([^=]+)=[0-9]+=[[:space:]]*(async[[:space:]]+)?def[[:space:]]+([A-Za-z0-9_]+).*/\\1@\\3/'"
PICKS = {
    "count2": DEFS + " | sort | uniq -c | sort -rn | head -2 | sed -E 's/^ *[0-9]+ //'",
    "count3": DEFS + " | sort | uniq -c | sort -rn | head -3 | sed -E 's/^ *[0-9]+ //'",
}
# per-commit cap without braces: number the lines of each commit with sed is hard; use awk only in this offline check
# to measure what a cap gives (the prompt version is decided after this check)
AWKCAP = "awk '/^commit /{n=0} n++<12'"


def sh(cmd, w):
    r = subprocess.run(["/bin/bash", "-c", cmd.replace(".git/agent", str(AG))], cwd=w, env=ENV, capture_output=True, text=True, timeout=900)
    return r.returncode, r.stdout, r.stderr


def gold_funcs(p):
    out, f = set(), None
    for l in p.splitlines():
        m = re.match(r"^\+\+\+ b/(\S+)", l)
        if m:
            f = m.group(1) if m.group(1).endswith(".py") and not TEST.search(m.group(1)) else None
            continue
        if f is None:
            continue
        m = re.match(r"^@@ .*? @@\s*(?:async\s+)?(?:def|class)\s+(\w+)", l)
        if m:
            out.add((f, m.group(1)))
        m = re.match(r"^[-+ ]\s*(?:async\s+)?def\s+(\w+)", l)
        if m:
            out.add((f, m.group(1)))
    return out


def gold_commits(t, clone):
    regions, f, ln = collections.defaultdict(list), None, 0
    for l in t["patch"].splitlines():
        m = re.match(r"^--- a/(\S+)", l)
        if m:
            f = m.group(1) if m.group(1).endswith(".py") and not TEST.search(m.group(1)) else None
            continue
        if l.startswith(("--- ", "+++ ")):
            continue
        m = re.match(r"^@@ -(\d+)", l)
        if m:
            ln = int(m.group(1))
            continue
        if f is None:
            continue
        if l.startswith("-"):
            regions[f].append(ln)
            ln += 1
        elif l.startswith("+"):
            regions[f].append(max(1, ln - 1))
        else:
            ln += 1
    gold = set()
    for f, ls in regions.items():
        ls = sorted(set(ls))
        groups, s = [], ls[0]
        for a, b in zip(ls, ls[1:] + [10 ** 9]):
            if b - a > 3:
                groups.append((s, a))
                s = b
        for s, e in groups[:3]:
            out = subprocess.run(["git", "log", f"-L{s},{e}:{f}", "-n3", "--format=COMMIT %h", t["base_commit"]], cwd=clone, env=ENV,
                                 capture_output=True, text=True, timeout=900).stdout
            gold |= {h[:7] for h in re.findall(r"^COMMIT (\w+)", out, re.M)}
    return gold


# the model's names and picks per run, from the r116 / r117 history-stage requests
runs = []
for d, arm, key in (("data/results/2026-11-18_skill_sb7fh4_p1", "sb7f", "You run two commands"), ("data/results/2026-11-18_skill_sb7fh4_p2", "sb7f", "You run two commands"),
                    ("data/results/2026-11-19_skill_r117_p1", "sb7g", "You fetch the history"), ("data/results/2026-11-19_skill_r117_p2", "sb7g", "You fetch the history")):
    seen = collections.defaultdict(lambda: {"names": None, "funcs": None})
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        r = json.loads(l)
        if f"#a{arm}." not in r["job"] or not r["request"]["messages"][0]["content"].startswith(key):
            continue
        rep = str(r["reply"])
        for nm in re.findall(r"names=\\*'([^'\\]+)\\*'", rep):
            seen[r["job"]]["names"] = nm
        for fs in re.findall(r"funcs=\\*'([^'\\]+)\\*'", rep):
            seen[r["job"]]["funcs"] = fs
    for job, v in seen.items():
        runs.append(dict(src=d[-2:] + " " + arm, iid=job.split("#")[0], **v))

rows = []
GC = {}
for run in runs:
    iid = run["iid"]
    t = T[iid]
    clone = CLONES / t["repo"].replace("/", "__")
    w = WT / iid
    if not (w / ".git").exists() or not run["names"]:
        print(run["src"], iid, "skip (no checkout or no names)", run["names"])
        continue
    if iid not in GC:
        GC[iid] = gold_commits(t, clone)
    gf, gc = gold_funcs(t["patch"]), GC[iid]
    AG.mkdir(exist_ok=True)
    names = " ".join(n.split(".")[-1] for n in run["names"].split())
    rc, out, err = sh(LIST.replace("NAMES", names), w)
    row = dict(src=run["src"], iid=iid, names=names, gold_fn=len(gf), gold_c=len(gc))
    hits = (AG / "hits").read_text() if (AG / "hits").exists() else ""
    row["listed"] = len(set(re.findall(r"^([^=]+)=\d+=", hits, re.M)))
    for rule, pick in PICKS.items():
        rc, out, err = sh(LIST.replace("NAMES", names) + HIST.replace("PICK", pick).replace("AWKCAP", AWKCAP), w)
        picked = set(tuple(x.split(" ", 1)) for x in re.findall(r"^== (\S+ \S+)$", out, re.M))
        shown = {h[:7] for h in re.findall(r"^commit ([0-9a-f]+)", out[:out.find("== HISTORY FETCHED")], re.M)}
        row[rule] = (bool(picked & gf), bool(shown & gc), len(out), rc)
    # named2: functions named like a name first
    named = DEFS + " | sort | uniq -c | sort -rn | sed -E 's/^ *[0-9]+ //' > .git/agent/ranked; (grep -E '@(" + "|".join(re.escape(n) for n in names.split()) + ")$' .git/agent/ranked; cat .git/agent/ranked) | awk '!s[$0]++' | head -2"
    rc, out, err = sh(LIST.replace("NAMES", names) + HIST.replace("$(PICK)", "$(" + named + ")").replace("AWKCAP", AWKCAP), w)
    picked = set(tuple(x.split(" ", 1)) for x in re.findall(r"^== (\S+ \S+)$", out, re.M))
    shown = {h[:7] for h in re.findall(r"^commit ([0-9a-f]+)", out[:out.find("== HISTORY FETCHED")], re.M)}
    row["named2"] = (bool(picked & gf), bool(shown & gc), len(out), rc)
    # the model's own pick, re-run
    if run["funcs"]:
        own = " ".join(x.replace("::", ":").replace(":", "@", 1) for x in run["funcs"].split())
        rc, out, err = sh(LIST.replace("NAMES", names) + HIST.replace("$(PICK)", "'" + own + "'").replace("for x in '", "for x in ").replace(own + "'", own).replace("AWKCAP", AWKCAP), w)
        picked = set(tuple(x.split(" ", 1)) for x in re.findall(r"^== (\S+ \S+)$", out, re.M))
        shown = {h[:7] for h in re.findall(r"^commit ([0-9a-f]+)", out[:out.find("== HISTORY FETCHED")], re.M)}
        row["model"] = (bool(picked & gf), bool(shown & gc), len(out), rc)
    else:
        row["model"] = (False, False, 0, None)
    rows.append(row)
    print(f"{row['src']} {iid[:30]:30} names '{names[:36]}' listed {row['listed']:2} | " + " | ".join(
        f"{k} fn {'Y' if row[k][0] else '-'} commit {'Y' if row[k][1] else '-'} {row[k][2]:5}c" for k in ("model", "count2", "named2", "count3")), flush=True)

n = len(rows)
print(f"\nruns {n} (tasks {len({r['iid'] for r in rows})}) | picks a real-fix function / history shows a real-fix-lines commit:")
for k in ("model", "count2", "named2", "count3"):
    print(f"  {k:7} function {sum(r[k][0] for r in rows):2}/{n} | commit {sum(r[k][1] for r in rows):2}/{n} | median chars {sorted(r[k][2] for r in rows)[n // 2]} | errors {sum(1 for r in rows if r[k][3] not in (0, None))}")
