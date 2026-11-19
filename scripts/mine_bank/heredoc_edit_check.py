"""Does sb1h's heredoc edit (scripts/agent_sb1h/system.md example 3, taken from the prompt) reproduce the real fix?
CPU, on the sparse *.py checkouts (scratchpad wt/); only bash / cat / python3 on our own fixed script / git apply / git diff;
nothing from the repositories is executed. Run: python3 -I scripts/mine_bank/heredoc_edit_check.py CLONE_DIR (repo root)
Per task (r117's 12 + rich_3521, geopandas-3240, fastapi_15589): every source hunk of the real patch -> old = context +
removed lines, new = context + added lines -> the example-3 command with them; then the file must equal the file that
`git apply` of the real patch gives. Counts hunks whose text has backslashes, double quotes, triple quotes or tabs."""
import json, os, re, subprocess, sys, hashlib
from pathlib import Path

CLONES = Path(sys.argv[1])
WT = CLONES.parent / "wt"
ENV = dict(os.environ, GIT_CONFIG_COUNT="2", GIT_CONFIG_KEY_0="core.hooksPath", GIT_CONFIG_VALUE_0="/dev/null",
           GIT_CONFIG_KEY_1="core.fsmonitor", GIT_CONFIG_VALUE_1="false", GIT_TERMINAL_PROMPT="0")
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$")
TASKS = ["cta-observatory__pyirf-193", "RDFLib__pySHACL-285", "Netflix-Skunkworks__policyuniverse-147", "terryyin__lizard-144",
         "lucianopaz__compress_pickle-28", "terryyin__lizard-370", "klen__peewee_migrate-203", "hgrecco__pint-pandas-264",
         "fastapi_11194", "rich_3278", "rich_3676", "rich_3506", "rich_3521", "geopandas__geopandas-3240", "fastapi_15589"]
T = {}
for f in ("data/swe_rebench/candidates.jsonl", "data/tasks.jsonl"):
    for l in open(f):
        j = json.loads(l)
        T[j["instance_id"]] = j
prompt = open("scripts/agent_sb1h/system.md").read()
ex3 = prompt[prompt.index("Example 3 -"):prompt.index("Example 4 -")]
CMD = re.findall(r"command:\n```\n(.*?)```", ex3, re.S)[0]
assert CMD.startswith("mkdir -p .git/agent\ncat > .git/agent/old <<'OLD_TEXT'\n")
head, rest = CMD.split("cat > .git/agent/old <<'OLD_TEXT'\n", 1)
_, rest = rest.split("OLD_TEXT\ncat > .git/agent/new <<'NEW_TEXT'\n", 1)
_, tail = rest.split("NEW_TEXT\n", 1)


def build(path, old, new):
    t = tail.replace("pkg/parser.py", path)
    return head + "cat > .git/agent/old <<'OLD_TEXT'\n" + old + "OLD_TEXT\ncat > .git/agent/new <<'NEW_TEXT'\n" + new + "NEW_TEXT\n" + t


def hunks(patch):
    out, f, cur = [], None, None
    for l in patch.splitlines(keepends=True):
        if l.startswith("diff --git"):
            f = None
            continue
        m = re.match(r"^\+\+\+ b/(\S+)", l)
        if m:
            f = m.group(1) if m.group(1).endswith(".py") and not TEST.search(m.group(1)) else None
            continue
        if l.startswith("--- "):
            continue
        if f is None:
            continue
        if l.startswith("@@"):
            cur = [f, "", ""]
            out.append(cur)
            continue
        if cur is None or l.startswith("\\"):
            continue
        tag, body = l[:1], l[1:]
        if not body.endswith("\n"):
            body += "\n"
        if tag in (" ", "-"):
            cur[1] += body
        if tag in (" ", "+"):
            cur[2] += body
    return out


def run(cmd, w):
    return subprocess.run(["/bin/bash", "-c", cmd], cwd=w, env=ENV, capture_output=True, text=True, timeout=300)


tot = dict(hunks=0, found1=0, edited=0, tasks_same=0, tasks=0, bs=0, dq=0, tq=0, tab=0)
for iid in TASKS:
    w = WT / iid
    if not (w / ".git").exists():
        print(iid, "no checkout")
        continue
    t = T[iid]
    hs = hunks(t["patch"])
    files = sorted({h[0] for h in hs})
    src_patch = t["patch"] if not t["patch"].startswith("diff --git") else "".join(blk for blk, fn in re.findall(r"(diff --git a/(\S+) .*?)(?=^diff --git |\Z)", t["patch"], re.S | re.M) if fn in files)
    run("git checkout -q -- . && mkdir -p .git/agent", w)
    pf = CLONES.parent / "gold.patch"
    pf.write_text(src_patch)
    r = run(f"git apply --recount --include='*.py' {pf} && cat " + " ".join(files), w)
    gold = hashlib.md5(r.stdout.encode()).hexdigest() if r.returncode == 0 else None
    run("git checkout -q -- .", w)
    ref = None
    if gold is None:  # dev16 patches that git apply rejects: reference = the same hunks applied by Python string replacement
        texts = {f: (w / f).read_text() for f in files}
        for f, o, n in hs:
            texts[f] = texts[f].replace(o, n, 1)
        ref = hashlib.md5("".join(texts[f] for f in files).encode()).hexdigest()
    found1 = edited = 0
    for f, old, new in hs:
        cmd = build(f, old, new).replace(".git/agent", str(CLONES.parent / "agent_h"))
        (CLONES.parent / "agent_h").mkdir(exist_ok=True)
        r = run(cmd, w)
        found1 += "old text found 1 times" in r.stdout
        edited += f"EDITED {f}" in r.stdout
        txt = old + new
        tot["bs"] += "\\" in txt
        tot["dq"] += '"' in txt
        tot["tq"] += "'''" in txt or '"""' in txt
        tot["tab"] += "\t" in txt
        if "old text found 1 times" not in r.stdout:
            print("   hunk", f, "->", r.stdout.strip().splitlines()[:1], r.stderr.strip()[:120])
    mine = hashlib.md5(run("cat " + " ".join(files), w).stdout.encode()).hexdigest()
    run("git checkout -q -- .", w)
    same = mine == (gold or ref)
    tot["hunks"] += len(hs)
    tot["found1"] += found1
    tot["edited"] += edited
    tot["tasks"] += 1
    tot["tasks_same"] += same
    print(f"{iid[:36]:36} files {len(files)} hunks {len(hs):2} | found once {found1:2} edited {edited:2} | result = reference: {same} (reference {'git apply' if gold else 'python replace'})", flush=True)
print(f"\ntasks {tot['tasks']} | hunks {tot['hunks']} | found once {tot['found1']} | edited {tot['edited']} | tasks identical to the real patch {tot['tasks_same']}"
      f" | hunks with backslashes {tot['bs']}, double quotes {tot['dq']}, triple quotes {tot['tq']}, tabs {tot['tab']}")
