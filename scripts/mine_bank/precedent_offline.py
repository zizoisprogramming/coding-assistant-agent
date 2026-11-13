"""Would past commits whose MESSAGE resembles the issue point at the real fix? (2026-11-13, user: "search the web and get
brand new idea"; offline check before building a 'precedent' evidence section; git history only, no repository code runs.)
Run: python3 -I scripts/mine_bank/precedent_offline.py SNAPSHOT_DIR [SNAPSHOT_DIR ...]

Literature: commit-history memory for localization (arXiv 2510.01003), ExpeRepair / SWE-Exp (retrieved past repairs as
examples), Multi-CoLoR (similar historical issues prune the search), STAIR (2607.29658). Our evidence stage searches
history only by code names (git log -S); the competition's issue texts are PR titles and descriptions, so the repo's
own past PR subjects are the same kind of text.

Per public task whose base is found in a snapshot (fix_line_age.find_base): the last N first-parent commits before the
base, scored by BM25 of their subject against the issue's words (title weighted x2); the top K. Reported per task:
whether a top-K commit touched a real-fix file / a real-fix function (its diff's hunk headers or changed def lines name
the function), versus how often evidc-family evidence outputs in the bank (the fixer prompt's REPOSITORY EVIDENCE block)
named a real-fix file; plus the cost (seconds) and the size of the output a section would add."""
import collections, glob, importlib.util, json, math, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("fla", os.path.join(HERE, "fix_line_age.py"))
fla = importlib.util.module_from_spec(spec); spec.loader.exec_module(fla)
T = {json.loads(l)["instance_id"]: json.loads(l) for l in open("data/tasks.jsonl")}
N, K = 3000, 3
STOP = set("the a an and or of to in for on with by from is are be this that it as at not no when if into via use uses using "
           "add adds added fix fixes fixed update updates support make allow docs doc test tests refactor remove deprecated new".split())
NAMES = {}
TEST_RE = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$")


def words(s):
    s = re.sub(r"https?://\S+|`|#\d+|@\w+", " ", s)
    out = []
    for w in re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", s):
        for p in [w.lower()] + [x.lower() for x in re.split(r"_|(?<=[a-z])(?=[A-Z])", w) if len(x) > 2]:
            if p not in STOP:
                out.append(p)
    return out


def gold(task):
    files = [f for f in re.findall(r"^\+\+\+ b/(\S+)", task["patch"], re.M) if f.endswith(".py") and not TEST_RE.search(f)]
    fns = set(re.findall(r"^@@[^@]*@@\s*(?:async\s+)?(?:def|class)\s+(\w+)", task["patch"], re.M))
    fns |= set(re.findall(r"^[+-]\s*(?:async\s+)?def\s+(\w+)", task["patch"], re.M))
    return files, fns


def evidence_hits():
    """task -> [runs, runs whose evidence block named a real-fix file] over evidc-family fixer prompts in the bank."""
    res = collections.defaultdict(lambda: [0, 0])
    for f in glob.glob("data/results/2026-1*/requests/requests.jsonl"):
        seen = set()
        for l in open(f, errors="replace"):
            if "REPOSITORY EVIDENCE (found before you started" not in l:
                continue
            try:
                r = json.loads(l)
            except Exception:
                continue
            job = r.get("job") or ""
            if job in seen:
                continue
            msgs = (r.get("request") or {}).get("messages") or []
            sysm = str(msgs[0].get("content")) if msgs else ""
            i = sysm.find("REPOSITORY EVIDENCE (found before you started")
            if i < 0:
                continue
            seen.add(job)
            iid = job.partition("#a")[0]
            if iid not in T:
                continue
            files, _ = gold(T[iid])
            block = sysm[i:]
            res[iid][0] += 1
            res[iid][1] += any(g in block for g in files)
    return res


def main(dirs):
    global NAMES
    snap = fla.snapshots(dirs)
    spec2 = importlib.util.spec_from_file_location('eo', os.path.join(HERE, 'evidence_offline.py'))
    eo = importlib.util.module_from_spec(spec2); sys.argv, _a = [sys.argv[0], '/dev/null'], sys.argv; spec2.loader.exec_module(eo); sys.argv = _a
    NAMES = eo.stage_names()
    ev = evidence_hits()
    rows = []
    for iid, t in sorted(T.items()):
        repo = iid.split("_")[0]
        if repo not in snap:
            continue
        top, _, tip = snap[repo]
        base = fla.find_base(top, t, tip)
        if not base:
            continue
        files, fns = gold(t)
        if not files:
            continue
        t0 = time.time()
        log = fla.git(top, "log", "--first-parent", "-n", str(N), "--format=%H\t%s", base).splitlines()
        docs = [(h, s, words(s)) for h, _, s in (x.partition("\t") for x in log)]
        df = collections.Counter(w for _, _, ws in docs for w in set(ws))
        avg = sum(len(ws) for _, _, ws in docs) / max(1, len(docs))
        text = t["problem_statement"]
        title = text.strip().splitlines()[0] if text.strip() else ""
        if os.environ.get("QUERY") == "names":  # what the evidence script receives: the stage's names (bank), not the issue
            nm = NAMES.get(iid)
            if not nm:
                continue
            q = collections.Counter(words(" ".join(nm)))
        elif os.environ.get("QUERY") == "names+title":  # the names plus the issue's first line
            nm = NAMES.get(iid) or []
            q = collections.Counter(words(" ".join(nm)) + words(title) * 2)
        else:
            q = collections.Counter(words(title) * 2 + words(" ".join(text.split()[:80])))

        def bm25(ws):
            tf = collections.Counter(ws)
            s = 0.0
            for w, qn in q.items():
                if w in tf:
                    idf = math.log(1 + (len(docs) - df[w] + 0.5) / (df[w] + 0.5))
                    s += qn * idf * tf[w] * 2.2 / (tf[w] + 1.2 * (0.25 + 0.75 * len(ws) / avg))
            return s
        ranked = sorted(((bm25(ws), h, s) for h, s, ws in docs if ws), reverse=True)[:K]
        file_hit = fn_hit = False
        shown = []
        for sc, h, s in ranked:
            changed = fla.git(top, "show", "--format=", "--name-only", h).split()
            diff = fla.git(top, "show", "--format=", "-U0", h, "--", *[f for f in files if f in changed]) if set(files) & set(changed) else ""
            fh = bool(set(files) & set(changed))
            nh = fh and any(re.search(rf"(def|class)\s+{re.escape(fn)}\b", diff) for fn in fns)
            file_hit |= fh; fn_hit |= nh
            shown.append(f"{sc:.1f} {'F' if fh else '-'}{'f' if nh else '-'} {s[:70]}")
        secs = time.time() - t0
        e = ev.get(iid, [0, 0])
        rows.append((iid, file_hit, fn_hit, e, secs, shown, title[:70]))
    n = len(rows)
    print(f"tasks with a base in the snapshots: {n} (top {K} of the last {N} first-parent commits by BM25 on the subject)")
    print(f"  a top-{K} commit touched a real-fix file: {sum(r[1] for r in rows)} / {n}; a real-fix function: {sum(r[2] for r in rows)} / {n}")
    with_ev = [r for r in rows if r[3][0]]
    print(f"  tasks with evidc-family evidence in the bank: {len(with_ev)}; evidence named a real-fix file in >= half of its runs: "
          f"{sum(1 for r in with_ev if r[3][1] * 2 >= r[3][0])}; precedent hits the file where evidence mostly did not: "
          f"{sum(1 for r in with_ev if r[1] and r[3][1] * 2 < r[3][0])}; evidence hits where precedent does not: {sum(1 for r in with_ev if not r[1] and r[3][1] * 2 >= r[3][0])}")
    print(f"  time per task: median {sorted(r[4] for r in rows)[n // 2]:.2f} s, max {max(r[4] for r in rows):.2f} s")
    dev16 = set(json.load(open("data/splits_public.json"))["dev16"])
    for r in rows:
        if r[0] in dev16:
            print(f"  dev16 {r[0]:15} file {'Y' if r[1] else '-'} fn {'Y' if r[2] else '-'} | evidence {r[3][1]}/{r[3][0]} | issue: {r[6]}")
            for s in r[5]:
                print("        ", s)


if __name__ == "__main__":
    main(sys.argv[1:])
