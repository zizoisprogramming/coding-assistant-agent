"""Offline check for history AT the edit (A) and AT the read (B) (user 2026-11-19: 'yes run the offline check first, then plan
both A and B'). CPU; bash / git / grep / sed / awk / python3 on our own fixed step only, on the sparse *.py checkouts (scratchpad
wt/, at base_commit); nothing from the repositories is executed. Run: python3 -I scripts/mine_bank/hist_at_edit_check.py CLONE_DIR
A = sb1h's heredoc edit whose fixed step also prints how the replaced lines changed before (git log -L on the old text's lines in
    HEAD, 2 commits, 16 lines per commit). B = a read command that prints the lines with numbers and how they changed before.
1. A on the real fixes of 15 tasks (every source hunk: old = context + removed lines): the edit still gives the real patch,
   history printed, chars, seconds, commits; the full output goes to the log for reading.
2. A on the model's own edits in r118 (sb1h + sb1hpp heredoc edits, old text and path taken from the call): old text found once
   in HEAD, history printed, chars, seconds, a 'real-fix commit' shown (one of the last 3 commits of each real-fix region).
   Per run: the first edit / any edit shows a real-fix commit.
3. B on the model's own reads in r118 (sb1h + sb1hpp read_file calls; whole-file reads -> the first 80 lines as a stand-in is
   NOT used: whole-file reads are counted apart), chars, seconds, real-fix commit shown; per run: a read before the first
   edit shows one."""
import ast, collections, glob, json, re, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLONES = Path(sys.argv[1])
src = (ROOT / "scripts/mine_bank/single_cmd_precheck.py").read_text()
ns = {"__name__": "x"}
exec(src[:src.index("# the model's names and picks")].replace("CLONES = Path(sys.argv[1])", "CLONES = Path(" + repr(str(CLONES)) + ")"), ns)
WT, T, ENV, TEST = ns["WT"], ns["T"], ns["ENV"], ns["TEST"]
AG = CLONES.parent / "agent_hist"
TASKS = ["cta-observatory__pyirf-193", "RDFLib__pySHACL-285", "Netflix-Skunkworks__policyuniverse-147", "terryyin__lizard-144",
         "lucianopaz__compress_pickle-28", "terryyin__lizard-370", "klen__peewee_migrate-203", "hgrecco__pint-pandas-264",
         "fastapi_11194", "rich_3278", "rich_3676", "rich_3506", "rich_3521", "geopandas__geopandas-3240", "fastapi_15589"]

# --- A: the candidate edit command (no double quotes, backticks, backslashes; braces only in awk's {n=0}) ---
A_STEP = """rm -f .git/agent/range
python3 - PATH <<'EOF'
import pathlib, subprocess, sys
p = pathlib.Path(sys.argv[1])
s, old, new = p.read_text(), open('.git/agent/old').read(), open('.git/agent/new').read()
print('old text found', s.count(old), 'times')
if s.count(old) == 1:
    h = subprocess.run(['git', 'show', 'HEAD:' + sys.argv[1]], capture_output=True, text=True).stdout
    if h.count(old) == 1:
        a = h[:h.index(old)].count(chr(10)) + 1
        open('.git/agent/range', 'w').write(str(a) + ',' + str(a + old.count(chr(10)) - 1) + ':' + sys.argv[1])
    p.write_text(s.replace(old, new))
    print('EDITED', p)
EOF
git diff -U1 -- PATH | head -40
test -s .git/agent/range && echo '== HOW THESE LINES CHANGED BEFORE, newest first:' && git log -L $(cat .git/agent/range) -n 2 --format='commit %h %ad %s' --date=short | grep -v -E '^(diff|index|---|[+][+][+])' | awk '/^commit /{n=0} n++<16' | cut -c1-150
"""
B_CMD = """grep -n '' PATH | sed -n S,Ep
echo '== HOW THESE LINES CHANGED BEFORE, newest first:'
git log -L S,E:PATH -n 2 --format='commit %h %ad %s' --date=short | grep -v -E '^(diff|index|---|[+][+][+])' | awk '/^commit /{n=0} n++<16' | cut -c1-150
"""
for c in (A_STEP, B_CMD):
    assert '"' not in c and "`" not in c and "\\" not in c and c.count("{") == 1 == c.count("}")


def sh(cmd, w):
    t0 = time.time()
    r = subprocess.run(["/bin/bash", "-c", cmd.replace(".git/agent", str(AG))], cwd=w, env=ENV, capture_output=True, text=True, timeout=900)
    return r.returncode, r.stdout, r.stderr, time.time() - t0


def a_cmd(path, old, new):
    return ("mkdir -p .git/agent\ncat > .git/agent/old <<'OLD_TEXT'\n" + old + "OLD_TEXT\ncat > .git/agent/new <<'NEW_TEXT'\n" + new
            + "NEW_TEXT\n" + A_STEP.replace("PATH", path))


def hist_part(out):
    k = out.find("== HOW THESE LINES CHANGED BEFORE")
    return out[k:] if k >= 0 else ""


def reset(w):
    subprocess.run(["git", "checkout", "-q", "--", "."], cwd=w, env=ENV)
    AG.mkdir(exist_ok=True)
    for q in AG.iterdir():
        q.unlink()


GC = {}


def gold(iid):
    if iid not in GC:
        t = T[iid]
        GC[iid] = ns["gold_commits"](t, CLONES / t["repo"].replace("/", "__"))
    return GC[iid]


# ---------------- 1. A on the real fixes ----------------
hs_src = (ROOT / "scripts/mine_bank/heredoc_edit_check.py").read_text()
hns = {}
exec(hs_src[hs_src.index("def hunks"):hs_src.index("def run(")], {"re": re, "TEST": TEST}, hns)
print("#### 1. A on the real fixes (each source hunk through the A command)")
tot = collections.Counter()
secs = []
for iid in TASKS:
    w = WT / iid
    if not (w / ".git").exists():
        print(iid, "no checkout")
        continue
    hs = hns["hunks"](T[iid]["patch"])
    reset(w)
    gc = gold(iid)
    first_hist = None
    for f, old, new in hs:
        rc, out, err, s = sh(a_cmd(f, old, new), w)
        hp = hist_part(out)
        shown = {x[:7] for x in re.findall(r"^commit ([0-9a-f]+)", hp, re.M)}
        tot["hunks"] += 1
        tot["edited"] += f"EDITED {f}" in out
        tot["hist"] += bool(shown)
        tot["gold"] += bool(shown & gc)
        secs.append(s)
        tot["chars"] += len(out)
        tot["hchars"] += len(hp)
        if first_hist is None:
            first_hist = hp
        if err.strip():
            print("   stderr", f, err.strip()[:160])
    reset(w)
    print(f"\n== {iid} hunks {len(hs)} | real-fix commits {sorted(gc)}\n" + (first_hist or "(no history)")[:2200], flush=True)
n = tot["hunks"]
print(f"\nA on real fixes: hunks {n} | EDITED {tot['edited']} | history printed {tot['hist']} | shows a real-fix commit {tot['gold']}"
      f" | output chars mean {tot['chars'] / n:.0f} (history part {tot['hchars'] / n:.0f}) | seconds median {sorted(secs)[len(secs) // 2]:.2f} max {max(secs):.1f}")


# ---------------- 2./3. the model's own edits and reads in r118 ----------------
def calls_of(rep):
    try:
        d = ast.literal_eval(rep)
        return [(c["function"]["name"], c["function"]["arguments"]) for c in (d.get("message") or {}).get("tool_calls") or []]
    except Exception:
        return []


R = collections.defaultdict(list)
for d in sorted(glob.glob(str(ROOT / "data/results/2026-11-19_skill_r118_p*"))):
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        r = json.loads(l)
        if "#asb1h." in r["job"] or "#asb1hpp." in r["job"]:
            R[(d[-2:], r["job"])].append((float(r["t"]), str(r["reply"])))
EDIT = re.compile(r"cat > \.git/agent/old <<'OLD_TEXT'\n(.*?)OLD_TEXT\n.*?python3 - (\S+) <<'EOF'", re.S)
A_rows, B_rows = [], []
for (p, job), rs in sorted(R.items()):
    iid = job.split("#")[0]
    w = WT / iid
    if not (w / ".git").exists():
        continue
    rs.sort()
    gc = gold(iid)
    seen_edit = False
    for _, rep in rs:
        for name, args in calls_of(rep):
            try:
                a = json.loads(args)
            except Exception:
                continue
            if name == "run_command" and "OLD_TEXT" in a.get("command", ""):
                m = EDIT.search(a["command"])
                if not m:
                    continue
                old, path = m.group(1), m.group(2)
                reset(w)
                rc, out, err, s = sh(a_cmd(path, old, old), w)  # new = old: only the history part matters here
                hp = hist_part(out)
                shown = {x[:7] for x in re.findall(r"^commit ([0-9a-f]+)", hp, re.M)}
                A_rows.append(dict(p=p, job=job, first=not seen_edit, found1="old text found 1 times" in out, hist=bool(shown),
                                   gold=bool(shown & gc), chars=len(hp), s=s))
                seen_edit = True
            elif name == "read_file":
                path = a.get("filepath") or a.get("path") or ""
                st_, en = a.get("start_line"), a.get("end_line")
                if not (st_ and en):
                    B_rows.append(dict(p=p, job=job, before=not seen_edit, whole=True, hist=False, gold=False, chars=0, s=0, err=""))
                    continue
                reset(w)
                rc, out, err, s = sh(B_CMD.replace("PATH", path).replace("S,E", f"{int(st_)},{int(en)}"), w)
                hp = hist_part(out)
                shown = {x[:7] for x in re.findall(r"^commit ([0-9a-f]+)", hp, re.M)}
                B_rows.append(dict(p=p, job=job, before=not seen_edit, whole=False, hist=bool(shown), gold=bool(shown & gc), chars=len(out),
                                   hchars=len(hp), s=s, err=err.strip()[:80]))
    reset(w)

print("\n#### 2. A on the model's own edits (r118 sb1h + sb1hpp)")
n = len(A_rows)
f1 = [x for x in A_rows if x["found1"]]
print(f"  heredoc edits {n} | old text found once in HEAD {len(f1)} | history printed {sum(x['hist'] for x in f1)} | shows a real-fix commit"
      f" {sum(x['gold'] for x in f1)} | history chars median {sorted(x['chars'] for x in f1)[len(f1) // 2] if f1 else 0} max {max([x['chars'] for x in f1] or [0])}"
      f" | seconds median {sorted(x['s'] for x in A_rows)[n // 2]:.2f} max {max(x['s'] for x in A_rows):.1f}")
runs = collections.defaultdict(list)
for x in A_rows:
    runs[(x["p"], x["job"])].append(x)
print(f"  runs with an edit {len(runs)} | first edit shows a real-fix commit {sum(v[0]['gold'] for v in runs.values())}"
      f" | any edit shows one {sum(any(x['gold'] for x in v) for v in runs.values())} | any edit prints history {sum(any(x['hist'] for x in v) for v in runs.values())}")

print("\n#### 3. B on the model's own reads (r118 sb1h + sb1hpp read_file calls)")
n = len(B_rows)
rng = [x for x in B_rows if not x["whole"]]
print(f"  read_file calls {n} | whole-file reads (no line range) {n - len(rng)} | ranged {len(rng)}: history printed {sum(x['hist'] for x in rng)},"
      f" real-fix commit {sum(x['gold'] for x in rng)}, output chars median {sorted(x['chars'] for x in rng)[len(rng) // 2] if rng else 0}"
      f" (history part median {sorted(x['hchars'] for x in rng)[len(rng) // 2] if rng else 0}, max {max([x['hchars'] for x in rng] or [0])}),"
      f" seconds median {sorted(x['s'] for x in rng)[len(rng) // 2] if rng else 0:.2f} max {max([x['s'] for x in rng] or [0]):.1f},"
      f" git errors {sum(bool(x['err']) for x in rng)} {collections.Counter(re.sub(r'[0-9]+', 'N', x['err'])[:60] for x in rng if x['err']).most_common(3)}")
runs = collections.defaultdict(list)
for x in B_rows:
    runs[(x["p"], x["job"])].append(x)
print(f"  runs with a read {len(runs)} | a ranged read before the first edit {sum(any(x['before'] and not x['whole'] for x in v) for v in runs.values())}"
      f" | one of those shows a real-fix commit {sum(any(x['before'] and x['gold'] for x in v) for v in runs.values())}"
      f" | any read shows one {sum(any(x['gold'] for x in v) for v in runs.values())}")
allruns = {k for k in R if (WT / k[1].split('#')[0] / '.git').exists()}
print(f"  sb1h + sb1hpp runs with a checkout {len(allruns)}")
