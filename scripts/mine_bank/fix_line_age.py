"""Can git history explain the bug? (2026-11-12, user: get the missing issue information from the repo, e.g. git log.)
Run: python3 -I scripts/mine_bank/fix_line_age.py SNAPSHOT_DIR [SNAPSHOT_DIR ...]
(each SNAPSHOT_DIR = an extracted data/snapshots/<task>.tgz: a repository with its full history)

For every public task whose repository has a snapshot that reaches back to the task's date: find the base (last
first-parent commit before created_at whose files hold the real fix's old lines; the snapshots' hashes differ from
tasks.jsonl's base_commit), then git blame the lines the real fix removes (or, for pure additions, the hunk's context
lines) and report how recently those lines were written: commits back and days back. A fix whose lines were written
recently is likely a regression, and the commit that wrote them (message + diff) is information the repository holds.
Also prints, per task, the bank's solve rate (data/analysis/run_table.jsonl) so recent vs old fixes can be compared.
Importable (scripts/mine_bank/evidence_offline.py): snapshots(), find_base(), blame_fix_lines()."""
import collections, json, re, subprocess, sys
from datetime import datetime


def git(top, *a):
    return subprocess.run(["git", "-C", top, *a], capture_output=True, text=True, errors="replace").stdout


def snapshots(dirs):
    """repo short name -> (toplevel, tip commit time, tip): the tip is refs/heads/main (the snapshot's own commit), not
    HEAD, so checking out older bases (evidence_offline.py) does not shrink later searches; the newest snapshot wins."""
    snap = {}
    for d in dirs:
        top = git(d, "rev-parse", "--show-toplevel").strip()
        tip = git(top, "rev-parse", "-q", "--verify", "refs/heads/main").strip() or git(top, "rev-parse", "HEAD").strip()
        ct = int(git(top, "log", "-1", "--format=%ct", tip).strip())
        repo = re.sub(r"_\d+$", "", d.rstrip("/").split("/")[-1])
        if repo not in snap or ct > snap[repo][1]:
            snap[repo] = (top, ct, tip)
    return snap


def hunks(patch):
    """(file, old_start, old_lines, removed_line_numbers) per hunk of a unified diff."""
    out, f = [], None
    lines = patch.splitlines()
    i = 0
    while i < len(lines):
        l = lines[i]
        if l.startswith("--- "):
            f = l[6:] if l.startswith("--- a/") else None
        m = re.match(r"@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@", l)
        if m and f:
            start = int(m.group(1))
            old, removed, k, ln = [], [], i + 1, start
            while k < len(lines) and not lines[k].startswith(("@@", "--- ", "diff ")):
                s = lines[k]
                if s.startswith("-"):
                    old.append(s[1:]); removed.append(ln); ln += 1
                elif s.startswith(" ") or s == "":
                    old.append(s[1:] if s else ""); ln += 1
                k += 1
            out.append((f, start, old, removed)); i = k; continue
        i += 1
    return out


def find_base(top, task, tip="HEAD", tries=40):
    """Newest first-parent commit (from TIP) before the task's created_at whose files hold every old-side hunk of the real fix."""
    hs = [h for h in hunks(task["patch"]) if h[2]]
    if not hs:
        return None
    for c in git(top, "rev-list", "--first-parent", f"--before={task['created_at']}", "-n", str(tries), tip).split():
        if all(git(top, "show", f"{c}:{f}").splitlines()[start - 1:start - 1 + len(old)] == old for f, start, old, _ in hs):
            return c
    return None


def blame_fix_lines(top, base, task):
    """[(commit, commits_back, days_back)] for the lines the real fix removes (pure additions: the hunk's context lines)."""
    base_t = int(git(top, "log", "-1", "--format=%ct", base).strip())
    out = []
    for f, start, old, removed in (h for h in hunks(task["patch"]) if h[2]):
        for a in removed or list(range(start, start + len(old))):
            por = git(top, "blame", "--porcelain", "-L", f"{a},{a}", base, "--", f)
            m = re.match(r"([0-9a-f]{40})", por)
            tm = re.search(r"^committer-time (\d+)", por, re.M)
            if m and tm:
                out.append((m.group(1), int(git(top, "rev-list", "--count", f"{m.group(1)}..{base}").strip() or 0), (base_t - int(tm.group(1))) / 86400))
    return out


def main(dirs):
    T = [json.loads(l) for l in open("data/tasks.jsonl")]
    snap = snapshots(dirs)
    rate = collections.defaultdict(lambda: [0, 0])
    try:
        for l in open("data/analysis/run_table.jsonl"):
            r = json.loads(l); rate[r["iid"]][0] += r["resolved"]; rate[r["iid"]][1] += 1
    except FileNotFoundError:
        pass
    rows = []
    for t in T:
        repo = t["instance_id"].split("_")[0]
        if repo not in snap:
            continue
        top, _, tip = snap[repo]
        base = find_base(top, t, tip)
        if not base:
            rows.append(dict(iid=t["instance_id"], base=None)); continue
        bl = blame_fix_lines(top, base, t)
        if not bl:
            rows.append(dict(iid=t["instance_id"], base=None)); continue
        back = sorted(b for _, b, _ in bl)
        rs = rate[t["instance_id"]]
        rows.append(dict(iid=t["instance_id"], base=base[:9], short=len(t["problem_statement"]) < 150, lines=len(bl),
                         min_back=back[0], min_days=min(d for _, _, d in bl), med_back=back[len(back) // 2], solved=rs[0], runs=rs[1]))
    ok = [r for r in rows if r.get("base")]
    print(f"tasks with a snapshot: {len(rows)}, base found: {len(ok)}")
    for r in sorted(ok, key=lambda r: r["min_back"]):
        print(f"  {r['iid']:15s} {'short' if r['short'] else '     '} lines {r['lines']:3d} | newest touched line {r['min_back']:5d} commits / {r['min_days']:6.0f} days back "
              f"(median line {r['med_back']:5d} commits) | bank solved {r['solved']}/{r['runs']}")
    for lim in (20, 50, 100, 300):
        g = [r for r in ok if r["min_back"] <= lim]
        print(f"newest touched line within {lim:3d} commits: {len(g):3d}/{len(ok)} tasks ({100 * len(g) / len(ok):.0f}%)")
    for lab, g in (("recent (<= 50 commits)", [r for r in ok if r["min_back"] <= 50]), ("older", [r for r in ok if r["min_back"] > 50])):
        s = sum(r["solved"] for r in g); n = sum(r["runs"] for r in g)
        print(f"{lab:24s} tasks {len(g):3d} | bank solve rate {100 * s / max(n, 1):.0f}% ({s}/{n}) | short statements {sum(r['short'] for r in g)}")


if __name__ == "__main__":
    main(sys.argv[1:])
