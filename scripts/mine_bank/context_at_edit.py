"""Context at the first source edit (2026-11-18; first run inline for the CONTEXT AT THE EDIT entry, kept for r112+).
Run: python3 -I scripts/mine_bank/context_at_edit.py 'GLOB of result folders' ARM[,ARM...]   (repo root; logs only)
     e.g. python3 -I scripts/mine_bank/context_at_edit.py 'data/results/2026-11-1*' pub024,sa2,sb1

For each run: the request whose reply made the first edit_file / write_file on a .py file (else the last request).
In the messages after the system prompt: share of the real fix's base-side source lines (removed + context, >= 18
chars) present; share of the issue's names / code strings present (system prompt counts too); compacted ('For
context:' summary present); issue text start present. Also per arm: line history (git log -L) run in the 2 calls before
that first edit. Split solved / failed / no edit, and same-task solved vs failed."""
import collections, glob, json, os, re, statistics as st, sys

DIRS, ARMS = sys.argv[1], set(sys.argv[2].split(","))
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$")
G, PS = {}, {}
for f in ("data/swe_rebench/candidates.jsonl", "data/tasks.jsonl"):
    for l in open(f):
        j = json.loads(l)
        G[j["instance_id"]] = j["patch"]
        PS[j["instance_id"]] = j.get("problem_statement", "")


def gold_lines(p):
    out, cur = [], None
    for l in p.splitlines():
        if l.startswith("--- a/"):
            cur = l[6:]
        elif cur and cur.endswith(".py") and not TEST.search(cur) and l[:1] in ("-", " ") and not l.startswith("---"):
            s = l[1:].strip()
            if len(s) >= 18:
                out.append(s)
    return out


def issue_strs(ps):
    xs = set(re.findall(r"`([^`\n]{4,60})`", ps)) | set(re.findall(r"\b[A-Za-z_]+(?:_[A-Za-z0-9]+)+\b|\b[a-z]+[A-Z][A-Za-z]+\b", ps))
    return [x for x in sorted(xs) if len(x) >= 5][:40]


EDIT = re.compile(r"'name': '(edit_file|write_file)'")
rows = []
for per in sorted(glob.glob(f"{DIRS}/**/gen_per_task.jsonl", recursive=True)):
    d = per.split("/")[2]
    rq = f"data/results/{d}/requests/requests.jsonl"
    if not os.path.exists(rq):
        continue
    res = {}
    for l in open(per):
        g = json.loads(l)
        if g.get("arm") in ARMS and g["instance_id"] in G:
            res[g["instance_id"] + "#a" + str(g.get("attempt"))] = g
    if not res:
        continue
    J = collections.defaultdict(list)
    for l in open(rq, errors="replace"):
        try:
            r = json.loads(l)
        except Exception:
            continue
        if r.get("job") in res:
            J[r["job"]].append(r)
    for job, R in J.items():
        g = res[job]
        iid = g["instance_id"]
        R.sort(key=lambda r: float(r["t"]))
        gl, isx = gold_lines(G[iid]), issue_strs(PS[iid])
        if len(gl) < 2 or len(isx) < 2:
            continue
        k = next((i for i, r in enumerate(R) if EDIT.search(str(r.get("reply"))) and ".py" in str(r.get("reply"))), None)
        idx = k if k is not None else len(R) - 1
        msgs = R[idx]["request"]["messages"] if isinstance(R[idx]["request"], dict) else []
        ctx = "\n".join(str(m.get("content")) for m in msgs[1:])
        sysm = str(msgs[0].get("content")) if msgs else ""
        hist = k is not None and any("git log -L" in str(R[j].get("reply")) for j in range(max(0, k - 2), k))
        rows.append(dict(arm=g["arm"], iid=iid, solved=g.get("resolved") in (True, "True"), edit=k is not None, hist=hist,
                         any_hist=any("git log -L" in str(r.get("reply")) for r in R),
                         gold=sum(s in ctx for s in gl) / len(gl), issue=sum((s in ctx) or (s in sysm) for s in isx) / len(isx),
                         comp="For context:" in ctx, task_msg=PS[iid][:60] in ctx or PS[iid][:60] in sysm))


def show(xs, t):
    if xs:
        print(f"  {t:24} n {len(xs):4} | real-fix lines in context {100 * st.mean(r['gold'] for r in xs):4.0f}% | issue strings {100 * st.mean(r['issue'] for r in xs):4.0f}%"
              f" | compacted {100 * st.mean(r['comp'] for r in xs):3.0f}% | issue start {100 * st.mean(r['task_msg'] for r in xs):3.0f}%"
              f" | git log -L in 2 calls before {sum(r['hist'] for r in xs):3} | any git log -L {sum(r['any_hist'] for r in xs):3}")


for arm in sorted({r["arm"] for r in rows}):
    A = [r for r in rows if r["arm"] == arm]
    print(f"\n#### {arm}: {len(A)} runs")
    show([r for r in A if r["edit"]], "first edit, all")
    show([r for r in A if r["edit"] and r["solved"]], "first edit, solved")
    show([r for r in A if r["edit"] and not r["solved"]], "first edit, failed")
    show([r for r in A if not r["edit"]], "no edit: last request")
by = collections.defaultdict(lambda: collections.defaultdict(list))
for r in rows:
    if r["edit"]:
        by[r["iid"]][r["solved"]].append(r["gold"])
m = [(st.mean(v[True]), st.mean(v[False])) for v in by.values() if v[True] and v[False]]
if m:
    print(f"\nsame task ({len(m)} tasks with both): real-fix lines in context at first edit solved {100 * st.mean(a for a, b in m):.0f}% vs failed "
          f"{100 * st.mean(b for a, b in m):.0f}%; tasks solved > failed {sum(a > b + .05 for a, b in m)}, less {sum(a < b - .05 for a, b in m)}")
