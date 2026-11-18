"""sb7g's stage commands on real checkouts of r117's 12 tasks (CPU, git / grep / awk only; nothing from the repositories
is executed). Run: python3 -I scripts/mine_bank/sb7g_cmd_check.py CLONE_DIR   (repo root; sparse *.py worktrees go next
to CLONE_DIR in wt/, as name_history_precheck.py makes them)
Commands are taken from scripts/agent_sb7g/history.md exactly as indented there (the model may copy the indentation),
with .git/agent swapped for a scratch folder (a worktree's .git is a file). Per task: names (the issue stand-in of
Step 0b), command 1 status / lines / NEXT line; the pick (a listed function that holds the real fix if any, else the
first listed); command 2 status / chars / commits / 'fatal' / ends with FETCHED. Also once: command 1 wrapped in a ```
fence, to confirm the error text example 3 shows."""
import json, os, re, subprocess, sys
from pathlib import Path

CLONES = Path(sys.argv[1])
WT = CLONES.parent / "wt"
AG = CLONES.parent / "agent_scratch"
TASKS = ["cta-observatory__pyirf-193", "RDFLib__pySHACL-285", "Netflix-Skunkworks__policyuniverse-147", "terryyin__lizard-144",
         "lucianopaz__compress_pickle-28", "terryyin__lizard-370", "klen__peewee_migrate-203", "hgrecco__pint-pandas-264",
         "fastapi_11194", "rich_3278", "rich_3676", "rich_3506"]
T = {}
for f in ("data/swe_rebench/candidates.jsonl", "data/tasks.jsonl"):
    for l in open(f):
        j = json.loads(l)
        if j["instance_id"] in TASKS:
            T[j["instance_id"]] = j
src = open("scripts/mine_bank/name_history_precheck.py").read()
ns = {}
exec(src[src.index("def names_of"):src.index("CMD = next(")], {"re": re}, ns)
names_of = ns["names_of"]
src16 = open("scripts/mine_bank/r116_sb7f.py").read()
ns16 = {"re": re, "TEST": re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$")}
exec(src16[src16.index("def gold_funcs"):src16.index("rows = []")], ns16)
gold_funcs = ns16["gold_funcs"]
ENV = dict(os.environ, GIT_CONFIG_COUNT="2", GIT_CONFIG_KEY_0="core.hooksPath", GIT_CONFIG_VALUE_0="/dev/null",
           GIT_CONFIG_KEY_1="core.fsmonitor", GIT_CONFIG_VALUE_1="false", GIT_TERMINAL_PROMPT="0")
h = open("scripts/agent_sb7g/history.md").read()
cmds = [m.group(1).rstrip("\n") for m in re.finditer(r"command:\n((?:    .*\n|\n(?=    ))+)", h)]
C1, C2 = cmds[0], cmds[1]


def worktree(d, iid, base):
    w = WT / iid
    if not (w / ".git").exists():
        WT.mkdir(exist_ok=True)
        run = lambda *a, cwd=d: subprocess.run(["git", *a], cwd=cwd, env=ENV, capture_output=True, text=True, timeout=1800)
        run("worktree", "add", "--no-checkout", "--detach", str(w), base)
        run("sparse-checkout", "set", "--no-cone", "*.py", cwd=w)
        run("checkout", "-q", base, cwd=w)
    return w


def bash(cmd, w):
    cmd = cmd.replace(".git/agent", str(AG))
    r = subprocess.run(["/bin/bash", "-c", cmd], cwd=w, env=ENV, capture_output=True, text=True, timeout=900)
    return r.returncode, r.stdout, r.stderr


ok1 = ok2 = good = 0
for iid in TASKS:
    t = T[iid]
    d = CLONES / t["repo"].replace("/", "__")
    if not d.exists():
        print(iid, "no clone", d)
        continue
    w = worktree(d, iid, t["base_commit"])
    AG.mkdir(exist_ok=True)
    for p in AG.iterdir():
        p.unlink()
    names = " ".join(names_of(t["problem_statement"])[:3]) or "xyz_none"
    c1 = C1.replace("    names='parse_config strict'", f"    names='{names}'", 1)
    rc, out, err = bash(c1, w)
    listed = [l for l in out.splitlines() if re.match(r"^[^:=]+=[0-9]+=", l)]
    nxt = out.strip().splitlines()[-1][:40] if out.strip() else ""
    ok1 += rc == 0 and nxt.startswith("== NEXT")
    gf = gold_funcs(t["patch"])
    picks = []
    for l in listed:
        f, _, rest = l.split("=", 2)
        m = re.search(r"(?:def|class)\s+(\w+)", rest)
        if m:
            picks.append((f, m.group(1)))
    hit = [p for p in picks if p in gf]
    pick = (hit or picks)[:1]
    good += bool(hit)
    line = f"{iid[:34]:34} names '{names[:40]}' | cmd1 rc {rc} listed {len(listed)} {nxt!r}"
    if pick:
        funcs = " ".join(f"{f}:{fn}" for f, fn in pick)
        c2 = C2.replace("    funcs='pkg/config.py:parse_config'", f"    funcs='{funcs}'", 1)
        rc2, out2, err2 = bash(c2, w)
        titles = re.findall(r'^commit [0-9a-f]+ [^ ]+ (.{0,40})', out2, re.M)[:3]
        fetched = out2.rstrip().endswith("make no other call.") and "== HISTORY FETCHED" in out2
        ok2 += rc2 == 0 and fetched
        line += (f" | pick {funcs} ({'real-fix' if hit else 'first listed'}) | cmd2 rc {rc2} chars {len(out2)} commits {len(re.findall(r'^commit ', out2, re.M))}"
                 f" fatal {'fatal' in out2} fetched {fetched} | titles {titles}")
    print(line, flush=True)
    if iid == TASKS[0]:
        rc, out, err = bash("```\n" + c1 + "\n```", w)
        print("   fenced command 1: rc", rc, "stderr", err.strip()[:120])
print(f"\ntasks {len(TASKS)} | command 1 ran and ended with NEXT {ok1} | a listed function holds the real fix {good} | command 2 ran and ended with HISTORY FETCHED {ok2}")
