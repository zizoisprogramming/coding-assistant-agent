"""Run an evidence script offline on the local snapshots and measure whether its output reaches the commit that wrote
the lines the real fix changes (2026-11-12; the 'history of the code' check before any GPU run).

    python3 -I scripts/mine_bank/evidence_offline.py SCRIPT [--recent N] [--show] SNAPSHOT_DIR [SNAPSHOT_DIR ...]

--stage-only: only tasks where a real evidence stage chose the names. SCRIPT: an evidence.py (e.g. submissions/evidefs/skills/evidence/scripts/evidence.py). For each public task whose base is
found in a snapshot (fix_line_age.find_base), the snapshot is checked out at that base and SCRIPT runs there with the
names an evidence stage would pass: the names the real stage chose most often in the bank (evid* runs, requests.jsonl),
else up to 4 code-like names from the issue (backticked, snake_case, CamelCase, dotted, called()). Measured per task:
  culprit  = the output shows the commit that wrote the NEWEST line the real fix changes (abbreviated hash match),
  any_fix  = it shows a commit that wrote any of those lines,
  file     = it names a source file the real fix changes,
plus output size and time. --recent N limits the run to tasks whose newest fix line is within N commits (default all).
The snapshots are scratch copies: they are checked out (git checkout -f) and .git/agent is removed between runs."""
import collections, glob, importlib.util, json, os, re, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("fla", os.path.join(HERE, "fix_line_age.py"))
fla = importlib.util.module_from_spec(spec); spec.loader.exec_module(fla)
args = sys.argv[1:]
SCRIPT = os.path.abspath(args.pop(0))
RECENT = int(args[args.index("--recent") + 1]) if "--recent" in args else None
SHOW = "--show" in args
STAGE_ONLY = "--stage-only" in args  # only tasks where a real evidence stage chose the names
DIRS = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] != "--recent")]
TASKS = {json.loads(l)["instance_id"]: json.loads(l) for l in open("data/tasks.jsonl")}
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$")
STAGE = "Your only job is one search of the repository"


def stage_names():
    """task -> the names list the real evidence stage passed most often (bank requests logs)."""
    seen = collections.defaultdict(collections.Counter)
    for f in glob.glob("data/results/2026-*/requests/requests.jsonl"):
        for l in open(f, errors="replace"):
            if STAGE not in l or "run_skill_script" not in l:
                continue
            try:
                r = json.loads(l)
            except Exception:
                continue
            task = str(r.get("job", "")).partition("#a")[0]
            for c in ((r.get("reply") or {}).get("message") or {}).get("tool_calls") or []:
                fn = c.get("function") or {}
                if fn.get("name") != "run_skill_script":
                    continue
                a = fn.get("arguments") or {}
                if isinstance(a, str):
                    try:
                        a = json.loads(a or "{}")
                    except Exception:
                        continue
                if not isinstance(a, dict) or str(a.get("skill_name")) != "evidence":
                    continue
                pa = a.get("positional_args") or []
                if isinstance(pa, list) and pa:
                    seen[task][tuple(str(x) for x in pa)] += 1
    return {t: list(c.most_common(1)[0][0]) for t, c in seen.items()}


def issue_names(task):
    t = TASKS[task]["problem_statement"]
    ranked = []
    for m in re.findall(r"`([^`\n]{2,80})`", t):
        ranked += IDENT.findall(m)
    ranked += [m for m in IDENT.findall(t) if "_" in m.strip("_") or "." in m]
    ranked += [p for m in re.findall(r"\b\w+(?:\.\w+)+\b", t) for p in m.split(".")[-1:] if len(p) >= 3]
    ranked += re.findall(r"([A-Za-z_][A-Za-z0-9_]{2,})\(", t)
    ranked += [m for m in IDENT.findall(t) if re.search(r"[a-z][A-Z]", m)]
    out = []
    for n in ranked:
        if n not in out and not n.startswith("http"):
            out.append(n)
    return out[:4]


def main():
    snap = fla.snapshots(DIRS)
    real = stage_names()
    rows = []
    for iid, t in sorted(TASKS.items()):
        repo = iid.split("_")[0]
        if repo not in snap or (STAGE_ONLY and iid not in real):
            continue
        top, _, tip = snap[repo]
        base = fla.find_base(top, t, tip)
        bl = fla.blame_fix_lines(top, base, t) if base else []
        if not bl:
            continue
        newest = min(b for _, b, _ in bl)
        if RECENT is not None and newest > RECENT:
            continue
        culprit = {c[:7] for c, b, _ in bl if b == newest}
        anyfix = {c[:7] for c, _, _ in bl}
        gold_files = [f for f, *_ in fla.hunks(t["patch"]) if not TEST.search(f)]
        names = real.get(iid) or issue_names(iid)
        subprocess.run(["git", "-C", top, "checkout", "-q", "-f", base], capture_output=True)
        shutil.rmtree(os.path.join(top, ".git", "agent"), ignore_errors=True)
        t0 = time.time()
        p = subprocess.run([sys.executable, "-I", SCRIPT, *names], cwd=top, capture_output=True, text=True, errors="replace", timeout=60)
        out = p.stdout
        hashes = set(re.findall(r"\b([0-9a-f]{7,40})\b", out))
        short = {h[:7] for h in hashes}
        rows.append(dict(iid=iid, newest=newest, names=names, real=iid in real, culprit=bool(culprit & short), anyfix=bool(anyfix & short),
                         file=any(f in out for f in gold_files), chars=len(out), secs=time.time() - t0))
        r = rows[-1]
        print(f"{iid:15s} newest fix line {newest:5d} commits | names {'(stage)' if r['real'] else '(issue)'} {names} | culprit {'Y' if r['culprit'] else '-'} "
              f"any {'Y' if r['anyfix'] else '-'} file {'Y' if r['file'] else '-'} | {r['chars']} chars {r['secs']:.1f} s", flush=True)
        if SHOW:
            print(out)
    for top, _, tip in snap.values():  # leave the scratch snapshots at their own commit
        subprocess.run(["git", "-C", top, "checkout", "-q", "-f", tip], capture_output=True)
    for lab, g in (("all", rows), ("newest fix line <= 50 commits", [r for r in rows if r["newest"] <= 50]),
                   ("<= 300", [r for r in rows if r["newest"] <= 300]), ("> 300", [r for r in rows if r["newest"] > 300])):
        if g:
            n = len(g)
            print(f"{lab:32s} tasks {n:3d} | culprit commit shown {sum(r['culprit'] for r in g):3d} ({100 * sum(r['culprit'] for r in g) / n:.0f}%) | "
                  f"a fix-line commit {sum(r['anyfix'] for r in g):3d} | real-fix file named {sum(r['file'] for r in g):3d} ({100 * sum(r['file'] for r in g) / n:.0f}%) | "
                  f"mean {sum(r['chars'] for r in g) / n:.0f} chars, max {max(r['secs'] for r in g):.1f} s")


if __name__ == "__main__":
    main()
