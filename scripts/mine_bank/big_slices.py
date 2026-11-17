"""The big failure slices (user 2026-11-17: 'lets go for the big slices'; two-agent designs and history closed).
Run: python3 -I scripts/mine_bank/big_slices.py [ARM,ARM,...]   (repo root; logs only; default: every logged 31B agent)

Every logged run in data/results/2026-1* (requests.jsonl + gen_per_task.jsonl), real fix from data/tasks.jsonl or
data/swe_rebench/candidates.jsonl. Each run falls in one slice:
  solved | no patch | wrong file only (no real-fix source file touched) | missing a real-fix file | right files, wrong logic
Tool results are paired with the calls of the previous reply (the tool messages after the last assistant message of the
next request), so an edit counts as made only when its result is not an error.
No patch is split by what happened: never tried an edit / every edit attempt failed / a made edit was undone (git
checkout, restore, stash, reset) / edits only in test or scratch files / other. Also per slice: first made source edit
(call index, seconds), calls, seconds per reply, failed edit attempts, read the real-fix lines before the first edit."""
import ast, collections, glob, json, os, re, statistics as st, sys

ARMS = sys.argv[1].split(",") if len(sys.argv) > 1 else None
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)conftest\.py$")
GOLD = {}
for f in ("data/swe_rebench/candidates.jsonl", "data/tasks.jsonl"):
    for l in open(f):
        j = json.loads(l)
        GOLD[j["instance_id"]] = j["patch"]
CURRENT = {"pub024", "sa2", "sb1"}
RT = {json.loads(l)["instance_id"] for l in open("data/swe_rebench/candidates.jsonl")} - {json.loads(l)["instance_id"] for l in open("data/tasks.jsonl")}


def gold(iid):
    files, lines, cur = set(), collections.defaultdict(set), None
    for l in GOLD[iid].splitlines():
        if l.startswith("--- a/"):
            cur = l[6:]
        m = re.match(r"@@ -(\d+)(?:,(\d+))?", l)
        if m and cur and not TEST.search(cur) and cur.endswith(".py"):
            a, n = int(m.group(1)), int(m.group(2) or 1)
            lines[cur].update(range(a, a + max(n, 1)))
            files.add(cur)
    return files, lines


def src(patch):
    return {f for f in re.findall(r"^\+\+\+ b/(\S+)", patch, re.M) if f.endswith(".py") and not TEST.search(f)}


def lit(x):
    if isinstance(x, (dict, list)):
        return x
    for p in (json.loads, ast.literal_eval):
        try:
            return p(x)
        except Exception:
            pass
    return x


def calls(rep):
    rep = lit(rep)
    m = (rep or {}).get("message") if isinstance(rep, dict) else None
    tc = lit((m or {}).get("tool_calls") or [])
    out = []
    for c in tc if isinstance(tc, list) else []:
        f = c.get("function", {})
        a = lit(f.get("arguments", ""))
        out.append((f.get("name"), a if isinstance(a, dict) else {"_raw": str(a)}))
    return out, (m or {}).get("content") or ""


def results_after(req):
    msgs = req["request"]["messages"] if isinstance(req["request"], dict) else []
    last = max((i for i, m in enumerate(msgs) if m.get("role") == "assistant"), default=-1)
    return [str(m.get("content")) for m in msgs[last + 1:] if m.get("role") == "tool"]


def is_err(res):
    return bool(re.search(r"'status': 'error'|\"status\": \"error\"|error_message|old_string not found|not present|Path traversal", res))


def path_of(a):
    return str(a.get("filepath", a.get("path", a.get("file_path", "")))).replace("/workspace/", "").lstrip("./")


rows = []
for per in sorted(glob.glob("data/results/2026-1*/**/gen_per_task.jsonl", recursive=True)):
    d = per.split("/")[2]
    rq = f"data/results/{d}/requests/requests.jsonl"
    if not os.path.exists(rq) or re.search(r"e4b|12b", d, re.I):
        continue
    res = {}
    for l in open(per):
        g = json.loads(l)
        if g.get("arm") and g["instance_id"] in GOLD and (ARMS is None or g["arm"] in ARMS):
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
    pdir = os.path.dirname(per)
    for job, g in res.items():
        R = sorted(J.get(job, []), key=lambda r: float(r["t"]))
        if not R:
            continue
        iid = g["instance_id"]
        pf = os.path.join(pdir, "gen/patches", f"{iid}__a{g.get('attempt')}.diff")
        patch = open(pf, errors="replace").read() if os.path.exists(pf) else ""
        gf, gl = gold(iid)
        mine = src(patch)
        solved = g.get("resolved") in (True, "True", "true")
        if solved:
            sl = "solved"
        elif not os.path.exists(pf):  # 60 older folders keep only patch_chars, not the diff
            sl = "no patch" if not g.get("patch_chars") else "patch, files not on disk"
        elif not patch.strip():
            sl = "no patch"
        elif not (mine & gf):
            sl = "wrong file only"
        elif not gf <= mine:
            sl = "missing a real-fix file"
        else:
            sl = "right files, wrong logic"
        t0 = float(R[0]["t"])
        seq = []  # (name, args, result or None, t)
        for i, r in enumerate(R):
            cs, _ = calls(r.get("reply") or r.get("response") or {})
            outs = results_after(R[i + 1]) if i + 1 < len(R) else []
            for k, (n, a) in enumerate(cs):
                seq.append((n, a, outs[k] if k < len(outs) else None, float(r["t"]) - t0))
        made = [(k, n, a, t) for k, (n, a, o, t) in enumerate(seq) if n in ("edit_file", "write_file") and o is not None and not is_err(o)]
        tried = [k for k, (n, a, o, t) in enumerate(seq) if n in ("edit_file", "write_file")]
        shell_edit = [k for k, (n, a, o, t) in enumerate(seq) if n == "run_command" and re.search(r"sed -i|> *[\w/.-]+\.py\b|tee [\w/.-]+\.py|open\([^)]*['\"]w", str(a.get("command", "")))]
        made_src = [m for m in made if path_of(m[2]).endswith(".py") and not TEST.search(path_of(m[2]))]
        undo = [k for k, (n, a, o, t) in enumerate(seq) if n == "run_command" and re.search(r"git (checkout|restore|stash|reset)", str(a.get("command", "")))]
        reads_gold = []
        for k, (n, a, o, t) in enumerate(seq):
            p = path_of(a)
            if n == "read_file" and p in gl:
                try:
                    s, e = int(a.get("start_line") or 1), int(a.get("end_line") or 10 ** 6)
                except (TypeError, ValueError):
                    s, e = 1, 10 ** 6  # garbled range: count as reading the file
                if gl[p] & set(range(s, e + 1)):
                    reads_gold.append(k)
            cmd = str(a.get("command", ""))
            for m in re.finditer(r"sed -n '?(\d+),(\d+)p'? +([\w/.-]+)", cmd):
                if m.group(3).lstrip("./") in gl and gl[m.group(3).lstrip("./")] & set(range(int(m.group(1)), int(m.group(2)) + 1)):
                    reads_gold.append(k)
            if re.search(r"\bcat ([\w/.-]+)", cmd) and any(f in cmd for f in gl):
                reads_gold.append(k)
        first = made_src[0] if made_src else None
        sub = ""
        if sl == "no patch":
            if not tried and not shell_edit:
                sub = "never tried an edit"
            elif not made and not shell_edit:
                sub = "every edit attempt failed"
            elif made_src and undo and max(undo) > made_src[0][0]:
                sub = "a made edit was undone"
            elif made and not made_src:
                sub = "edits only in test / scratch files"
            else:
                sub = "other (edit made, diff empty)"
        nrep = len(R)
        rows.append(dict(arm=g["arm"], iid=iid, dir=d, sl=sl, sub=sub, calls=len(seq), replies=nrep,
                         s_per_reply=sum(float(r.get("seconds") or 0) for r in R) / max(1, nrep),
                         agent_s=float(g.get("agent_s") or 0), end=g.get("end"),
                         first_k=first[0] + 1 if first else None, first_t=first[3] if first else None,
                         tried=len(tried), failed=len(tried) - len([m for m in made if m[1] in ("edit_file", "write_file")]),
                         read_gold_before=bool(reads_gold) and (first is None or min(reads_gold) < first[0]),
                         budget="Tool call budget exhausted" in json.dumps([s[2] for s in seq if s[2]])))


def report(rs, title):
    print(f"\n#### {title}: {len(rs)} runs, {len({r['iid'] for r in rs})} tasks, agents {len({r['arm'] for r in rs})}")
    c = collections.Counter(r["sl"] for r in rs)
    for sl in ("solved", "no patch", "patch, files not on disk", "wrong file only", "missing a real-fix file", "right files, wrong logic"):
        x = [r for r in rs if r["sl"] == sl]
        if not x:
            continue
        fk = [r["first_k"] for r in x if r["first_k"]]
        ft = [r["first_t"] for r in x if r["first_t"] is not None]
        print(f"  {sl:26} {len(x):5} ({100 * len(x) / len(rs):4.1f}%) | calls {st.median([r['calls'] for r in x]):4.0f} | s/reply {st.median([r['s_per_reply'] for r in x]):5.1f}"
              f" | first made source edit: call {st.median(fk) if fk else '-':>4}, {st.median(ft) if ft else 0:4.0f} s, none {sum(1 for r in x if not r['first_k']):4}"
              f" | edit attempts {st.mean([r['tried'] for r in x]):4.1f}, failed {st.mean([r['failed'] for r in x]):4.1f} | read real-fix lines before first edit {100 * st.mean([r['read_gold_before'] for r in x]):3.0f}%"
              f" | budget hit {100 * st.mean([r['budget'] for r in x]):3.0f}%")
    nps = [r for r in rs if r["sl"] == "no patch"]
    if nps:
        print("  no patch, by what happened:", dict(collections.Counter(r["sub"] for r in nps).most_common()))
        nt = [r for r in nps if r["sub"] == "never tried an edit"]
        if nt:
            print(f"    never tried: s/reply {st.median([r['s_per_reply'] for r in nt]):.1f}, calls {st.median([r['calls'] for r in nt]):.0f}, budget hit {sum(r['budget'] for r in nt)}, read real-fix lines {sum(r['read_gold_before'] for r in nt)}/{len(nt)}")


report(rows, "all logged 31B runs")
report([r for r in rows if r["arm"] in CURRENT], "current line (pub024, sa2, sb1)")
report([r for r in rows if r["arm"] in CURRENT and r["iid"] in RT], "current line, SWE-rebench test set only (24 tasks)")
report([r for r in rows if r["arm"] in CURRENT and r["iid"] not in RT], "current line, other tasks (dev16 etc.)")
