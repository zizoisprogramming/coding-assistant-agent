"""How do runs on the out-of-family test set (24 SWE-rebench test tasks, r99 / r100 / later) fail? (2026-11-16, user:
"thinking of another agent while that run finishes"; basis for the next agent.)
Run: python3 -I scripts/mine_bank/rtest_failures.py [ARM ...]   (repo root; default pub024)

Per run (data/results/2026-11-1*_skill_{rtest,sa1rt,sa2rt}*): outcome; the agent's patch (results/gen/patches/*.diff)
vs the real fix (data/swe_rebench/candidates.jsonl 'patch', public SWE-rebench data): touched a real-fix file, covered
every real-fix source file, patch size vs real; from the request log: did the agent read the real-fix lines before its
first edit (read_file range or sed -n range overlapping a real-fix hunk of that file), did it run a test command
(pytest / unittest / tox) after its last edit and what that test's result said (passed / failed / error / not run),
repeated identical calls. Prints counts only; no repository code runs."""
import ast, collections, glob, json, os, re, sys

ARMS = sys.argv[1:] or ["pub024"]
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$")
GOLD = {}
for l in open("data/swe_rebench/candidates.jsonl"):
    r = json.loads(l)
    GOLD[r["instance_id"]] = r


def hunks(patch):
    """file -> list of (start, end) old-line ranges, source files only."""
    out, f = collections.defaultdict(list), None
    for line in patch.splitlines():
        m = re.match(r"^\+\+\+ b/(\S+)", line)
        if m:
            f = m.group(1)
            continue
        m = re.match(r"^@@ -(\d+)(?:,(\d+))? ", line)
        if m and f and f.endswith(".py") and not TEST.search(f):
            s, n = int(m.group(1)), int(m.group(2) or 1)
            out[f].append((s, s + max(n, 1) - 1))
    return out


def changed_lines(patch):
    return sum(1 for l in patch.splitlines() if (l.startswith("+") or l.startswith("-")) and not l.startswith(("+++", "---")))


def calls(rep):
    if isinstance(rep, str):
        try:
            rep = ast.literal_eval(rep)
        except Exception:
            return []
    m = (rep or {}).get("message") or {}
    tc = m.get("tool_calls") or []
    if isinstance(tc, str):
        try:
            tc = ast.literal_eval(tc)
        except Exception:
            return []
    out = []
    for c in tc:
        f = c.get("function", {})
        a = f.get("arguments", "")
        try:
            a = json.loads(a) if isinstance(a, str) else a
        except Exception:
            a = {"_raw": a}
        out.append((f.get("name"), a if isinstance(a, dict) else {"_raw": a}, c.get("id")))
    return out


def tool_result(msgs, cid):
    for m in msgs:
        if m.get("role") == "tool" and m.get("tool_call_id") == cid:
            return str(m.get("content"))
    return ""


rows = []
for d in sorted(glob.glob("data/results/2026-11-1*_skill_*")):
    if not any(k in d for k in ("rtest", "sa1rt", "sa2rt", "sa3mf")):
        continue
    gp = os.path.join(d, "results/gen_per_task.jsonl")
    if not os.path.exists(gp):
        continue
    res = {json.loads(l)["instance_id"] + "#a" + json.loads(l)["attempt"]: json.loads(l) for l in open(gp)}
    seqs = collections.defaultdict(list)
    for l in open(os.path.join(d, "requests/requests.jsonl"), errors="replace"):
        r = json.loads(l)
        if r.get("job") in res:
            seqs[r["job"]].append(r)
    for job, R in seqs.items():
        g = res[job]
        if g["arm"] not in ARMS:
            continue
        iid = g["instance_id"]
        gold = GOLD.get(iid)
        if not gold:
            continue
        R.sort(key=lambda r: float(r["t"]))
        last = max(R, key=lambda r: len(r["request"]["messages"]))
        msgs = last["request"]["messages"]
        seq = []
        for r in R:
            for n, a, cid in calls(r["reply"]):
                seq.append((n, a, cid))
        gh = hunks(gold["patch"])
        pfile = os.path.join(d, "results/gen/patches", f"{iid}__a{g['attempt']}.diff")
        mine = open(pfile, errors="replace").read() if os.path.exists(pfile) else ""
        mh = hunks(mine)
        edit_idx = [i for i, (n, a, _) in enumerate(seq) if n in ("edit_file", "write_file")]
        first_edit = edit_idx[0] if edit_idx else len(seq)
        read_gold = False
        for n, a, _ in seq[:first_edit]:
            fp = (a.get("filepath") or a.get("path") or "").lstrip("./").replace("/workspace/", "")
            ranges = []
            if n == "read_file" and fp in gh:
                s, e = a.get("start_line") or 1, a.get("end_line") or (int(a.get("start_line") or 1) + 150)
                ranges.append((int(s), int(e), fp))
            if n == "run_command":
                cmd = a.get("command", "")
                for m in re.finditer(r"sed -n '?(\d+),(\d+)p'? (\S+)", cmd):
                    f = m.group(3).lstrip("./").replace("/workspace/", "")
                    if f in gh:
                        ranges.append((int(m.group(1)), int(m.group(2)), f))
            for s, e, f in ranges:
                if any(s <= he and e >= hs for hs, he in gh[f]):
                    read_gold = True
        test_after = "no test after last edit"
        last_edit = edit_idx[-1] if edit_idx else -1
        for n, a, cid in seq[last_edit + 1:]:
            if n == "run_command" and re.search(r"pytest|unittest|tox\b|nox\b|-m test", a.get("command", "")):
                out = tool_result(msgs, cid)
                if not out:
                    test_after = "test run (output compacted away)"
                elif re.search(r"\b\d+ failed|FAILED|Error|error:|Traceback", out) and not re.search(r"\b0 failed", out):
                    test_after = "test run: failures / errors"
                elif re.search(r"\b\d+ passed|\bOK\b", out):
                    test_after = "test run: passed"
                else:
                    test_after = "test run: unclear"
        sig = [(n, json.dumps(a, sort_keys=True)) for n, a, _ in seq]
        rep = sum(c - 1 for c in collections.Counter(sig).values() if c > 1)
        out = "solved" if g["resolved"] else ("no patch" if not mine.strip() else "wrong patch")
        rows.append(dict(arm=g["arm"], iid=iid, out=out, file_hit=bool(set(mh) & set(gh)), all_files=bool(gh) and set(gh) <= set(mh),
                         gold_files=len(gh), read_gold=read_gold, test_after=test_after, repeats=rep,
                         size=changed_lines(mine), gold_size=changed_lines(gold["patch"])))

for arm in ARMS:
    A = [r for r in rows if r["arm"] == arm]
    print(f"\n== {arm}: {len(A)} runs on the test set")
    for out in ("solved", "wrong patch", "no patch"):
        B = [r for r in A if r["out"] == out]
        if not B:
            continue
        n = len(B)
        pct = lambda k: sum(1 for r in B if r[k]) / n
        print(f"  {out:12} {n:3} | touched a real-fix file {pct('file_hit'):4.0%} | covered all real-fix files {pct('all_files'):4.0%} "
              f"(real fix spans >1 source file in {sum(r['gold_files'] > 1 for r in B)}) | read the real-fix lines before the first edit {pct('read_gold'):4.0%} "
              f"| repeated identical calls {sum(r['repeats'] > 0 for r in B) / n:4.0%} | patch lines / real median "
              f"{sorted(r['size'] / max(1, r['gold_size']) for r in B)[n // 2]:.2f}")
        print("               after the last edit:", dict(collections.Counter(r["test_after"] for r in B)))
