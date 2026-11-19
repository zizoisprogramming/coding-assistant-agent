"""History window check (user 2026-11-19: 'yes run the offline check with both windows').
Which window shows a USEFUL commit after the model's own edits: L = the replaced lines (sbA as built), F = the whole enclosing
function (smallest def / async def around the replaced lines, found with ast on HEAD's text; module-level code -> L); each with
2 commits (sbA) and 3. Same output form as sbA (make_sbab.LOG: 16 lines per commit, 150 chars per line).
CPU; git / bash on the sparse checkouts (scratchpad wt/, at base_commit); ast.parse only reads the file text; nothing from the
repositories is executed.
Run: python3 -I scripts/mine_bank/hist_window_check.py CLONE_DIR dump    -> runs git, caches outputs in data/analysis/hist_window_cache.json,
                                                                         prints every distinct commit shown per task (for labelling)
     python3 -I scripts/mine_bank/hist_window_check.py CLONE_DIR score   -> scores with scripts/mine_bank/hist_useful_commits.json
Edits: r118 (sb1 edit_file calls with old_string; sb1h / sb1hpp / sb7h heredoc edits) + r119 (sb1h / sbA / sbB heredoc edits).
An edit gets history only when its old text occurs once in HEAD's file (as in sbA); later edits of the model's own new text get none
in both windows. Labels (useful / not) are my judgement from the commit subject, its hunk and the real fix."""
import ast, collections, glob, importlib.util, json, re, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLONES = Path(sys.argv[1])
MODE = sys.argv[2]
src = (ROOT / "scripts/mine_bank/single_cmd_precheck.py").read_text()
ns = {"__name__": "x"}
exec(src[:src.index("# the model's names and picks")].replace("CLONES = Path(sys.argv[1])", "CLONES = Path(" + repr(str(CLONES)) + ")"), ns)
WT, T, ENV = ns["WT"], ns["T"], ns["ENV"]
spec = importlib.util.spec_from_file_location("make_sbab", ROOT / "scripts/make_sbab.py")
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
CACHE = ROOT / "data/analysis/hist_window_cache.json"
LABELS = ROOT / "scripts/mine_bank/hist_useful_commits.json"
HEREDOC = re.compile(r"cat > \.git/agent/old <<'OLD_TEXT'\n(.*?)OLD_TEXT\n.*?python3 - (\S+) <<'EOF'", re.S)


def git(args, w, timeout=300):
    r = subprocess.run(["git"] + args, cwd=w, env=ENV, capture_output=True, text=True, timeout=timeout)
    return r.stdout


def hist(w, a, b, path, n):
    cmd = f"git log -L {a},{b}:{path} -n {n} " + B.LOG
    t0 = time.time()
    r = subprocess.run(["/bin/bash", "-c", cmd], cwd=w, env=ENV, capture_output=True, text=True, timeout=600)
    return r.stdout, time.time() - t0


def func_range(text, a, b):
    try:
        tree = ast.parse(text)
    except Exception:
        return None
    best = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            s = min([node.lineno] + [d.lineno for d in node.decorator_list])
            if s <= a and node.end_lineno >= b and (best is None or node.end_lineno - s < best[1] - best[0]):
                best = (s, node.end_lineno, node.name)
    return best


def edits():
    """(run key, iid, path, old) in call order per run."""
    out = []
    for d in sorted(glob.glob(str(ROOT / "data/results/2026-11-19_skill_r11[89]_p*"))):
        rnd = "r118" if "_r118_" in d else "r119"
        runs = collections.defaultdict(list)
        for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
            try:
                r = json.loads(l)
            except Exception:
                continue
            if len(r["request"]["messages"]) == 1:
                continue
            runs[r["job"]].append((float(r["t"]), str(r["reply"])))
        for job, rs in runs.items():
            rs.sort()
            for _, rep in rs:
                try:
                    calls = (ast.literal_eval(rep).get("message") or {}).get("tool_calls") or []
                except Exception:
                    continue
                for c in calls:
                    try:
                        a = json.loads(c["function"]["arguments"])
                    except Exception:
                        continue
                    if c["function"]["name"] == "edit_file" and a.get("old_string") and a.get("filepath"):
                        out.append((f"{rnd}/{d[-2:]}/{job}", job.split("#")[0], a["filepath"], a["old_string"]))
                    elif c["function"]["name"] == "run_command":
                        m = HEREDOC.search(a.get("command", ""))
                        if m:
                            out.append((f"{rnd}/{d[-2:]}/{job}", job.split("#")[0], m.group(2), m.group(1)))
    return out


def commits(out):
    return [(m.group(1)[:7], m.group(2)) for m in re.finditer(r"^commit ([0-9a-f]{7,}) \S+ (.*)$", out, re.M)]


if MODE == "dump":
    E = edits()
    cache = {}
    heads = {}
    for k, (run, iid, path, old) in enumerate(E):
        w = WT / iid
        key = f"{iid}|{path}|{old}"
        if key in cache:
            continue
        if (iid, path) not in heads:
            heads[(iid, path)] = git(["show", "HEAD:" + path], w) if (w / ".git").exists() else ""
        h = heads[(iid, path)]
        row = dict(found=h.count(old) if old else 0)
        if row["found"] == 1:
            a = h[:h.index(old)].count("\n") + 1
            b = a + old.count("\n") - (1 if old.endswith("\n") else 0)
            b = max(a, b)
            fr = func_range(h, a, b)
            row.update(L=[a, b], F=list(fr[:2]) if fr else None, func=fr[2] if fr else None)
            row["L3"], row["Ls"] = hist(w, a, b, path, 3)
            if fr:
                row["F3"], row["Fs"] = hist(w, fr[0], fr[1], path, 3)
        cache[key] = row
        print(f"  {k + 1}/{len(E)} {iid[:24]} {path[-30:]} found {row['found']} L {row.get('L')} F {row.get('F')} {row.get('func')}", flush=True)
    CACHE.write_text(json.dumps(dict(edits=E, cache=cache)))
    # every distinct commit shown, per task, with the window that showed it and its first changed lines
    seen = collections.defaultdict(dict)
    for key, row in cache.items():
        iid = key.split("|")[0]
        for win in ("L3", "F3"):
            out = row.get(win) or ""
            parts = re.split(r"(?m)^(?=commit [0-9a-f]{7,} )", out)
            for p in parts:
                m = re.match(r"commit ([0-9a-f]{7,}) (\S+) (.*)", p)
                if m:
                    h = m.group(1)[:7]
                    e = seen[iid].setdefault(h, dict(date=m.group(2), subj=m.group(3), wins=set(), hunk=""))
                    e["wins"].add(win[0])
                    if not e["hunk"]:
                        e["hunk"] = "\n".join(l for l in p.splitlines()[1:] if l[:1] in "+-")[:500]
    for iid in sorted(seen):
        gold = ns["gold_commits"](T[iid], CLONES / T[iid]["repo"].replace("/", "__"))
        print(f"\n######## {iid} | real-fix-line commits (last 3 per region): {sorted(gold)}")
        fix = "\n".join(l for l in T[iid]["patch"].splitlines() if l.startswith(("+", "-", "@@")) and not l.startswith(("+++", "---")))
        print("  REAL FIX (first 25 lines):\n" + "\n".join("    " + l[:140] for l in fix.splitlines()[:25]))
        for h, e in sorted(seen[iid].items(), key=lambda x: x[1]["date"], reverse=True):
            print(f"  -- {h} {e['date']} [{''.join(sorted(e['wins']))}] {'GOLD ' if h in gold else ''}{e['subj'][:110]}")
            for l in e["hunk"].splitlines()[:6]:
                print("       " + l[:130])

if MODE == "score":
    D = json.loads(CACHE.read_text())
    E, cache = D["edits"], D["cache"]
    lab = json.loads(LABELS.read_text())
    TIER = sys.argv[3] if len(sys.argv) > 3 else "useful"
    useful = {t: set(v["useful"]) | (set(v["weak"]) if TIER == "weak" else set()) for t, v in lab.items() if not t.startswith("_")}
    print(f"#### tier: {TIER} ({'useful only' if TIER == 'useful' else 'useful + weak'}) | labelled tasks:", len(useful))

    def shown(row, win, n):
        if row.get("found") != 1:
            return []
        out = row.get("F3") if win == "F" and row.get("F") else row.get("L3")  # module-level code: F falls back to L
        return [h for h, _ in commits(out or "")][:n]

    def chars(row, win, n):
        out = (row.get("F3") if win == "F" and row.get("F") else row.get("L3")) or ""
        parts = [p for p in re.split(r"(?m)^(?=commit [0-9a-f]{7,} )", out) if p.startswith("commit")]
        return len("".join(parts[:n]))

    WINS = [("L", 2), ("L", 3), ("F", 2), ("F", 3)]
    rows = [(run, iid, cache[f"{iid}|{path}|{old}"]) for run, iid, path, old in E if iid in useful]
    uniq = {}
    for run, iid, row in rows:
        uniq[id(row)] = (iid, row)
    once = [(i, r) for i, r in uniq.values() if r["found"] == 1]
    print(f"\nedits {len(rows)} (distinct {len(uniq)}) | old text found once in HEAD {len(once)} distinct | module-level (F = L) "
          f"{sum(r.get('F') is None for _, r in once)}")
    print("per distinct edit with history:")
    for w, n in WINS:
        cs = [chars(r, w, n) for _, r in once]
        print(f"  {w}{n}: shows a useful commit {sum(bool(set(shown(r, w, n)) & useful[i]) for i, r in once):3}/{len(once)}"
              f" | chars median {sorted(cs)[len(cs) // 2]:5} p90 {sorted(cs)[int(len(cs) * .9)]:5} max {max(cs):5}")
    secs = [r.get("Fs", 0) for _, r in once]
    print(f"  git seconds: L median {sorted(r['Ls'] for _, r in once)[len(once) // 2]:.2f} max {max(r['Ls'] for _, r in once):.1f}"
          f" | F median {sorted(secs)[len(secs) // 2]:.2f} max {max(secs):.1f}")
    byrun = collections.defaultdict(list)
    for run, iid, row in rows:
        byrun[(run, iid)].append(row)
    print(f"\nper run ({len(byrun)} runs with an edit on a labelled task): the first edit found once in HEAD / any edit shows a useful commit")
    for w, n in WINS:
        first = anyx = 0
        for (run, iid), rs in byrun.items():
            ok = [r for r in rs if r["found"] == 1]
            first += bool(ok) and bool(set(shown(ok[0], w, n)) & useful[iid])
            anyx += any(set(shown(r, w, n)) & useful[iid] for r in ok)
        print(f"  {w}{n}: first edit {first:3}/{len(byrun)} | any edit {anyx:3}/{len(byrun)}")
    print("\nper task (runs whose first edit shows a useful commit: L2 L3 F2 F3 / runs):")
    for t in sorted(useful):
        rr = [(k, rs) for k, rs in byrun.items() if k[1] == t]
        cells = []
        for w, n in WINS:
            c = 0
            for k, rs in rr:
                ok = [r for r in rs if r["found"] == 1]
                c += bool(ok) and bool(set(shown(ok[0], w, n)) & useful[t])
            cells.append(c)
        print(f"  {t[:34]:34} {cells} / {len(rr)}   useful: {lab[t].get('why', '')[:90]}")
