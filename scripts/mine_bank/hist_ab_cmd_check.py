"""The exact sbA edit step and sbB read command (scripts/make_sbab.py, asserted equal to the prompts' blocks) on the sparse checkouts.
CPU; bash / git / sed / awk / python3 on our own fixed step only; nothing from the repositories is executed.
Run: python3 -I scripts/mine_bank/hist_ab_cmd_check.py CLONE_DIR   (repo root)
A: (1) the real fixes of 15 tasks hunk by hunk = the real patch, exit 0, history or no-history line after each EDITED;
   (2) old text not in the file: exit 0, neither history nor no-history line; (3) a second edit of lines just added: exit 0,
   the no-history line; (4) a new untracked file edited: exit 0, the no-history line.
B: (1) r118 sb1h / sb1hpp ranged reads through the read command: exit 0, header printed, sed lines = the file's lines;
   (2) a start after the end: 'has only N lines'; (3) an untracked file: 'There is no path'."""
import collections, hashlib, importlib.util, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("make_sbab", ROOT / "scripts/make_sbab.py")
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
CLONES = Path(sys.argv[1])
WT = CLONES.parent / "wt"
AG = CLONES.parent / "agent_ab"
src = (ROOT / "scripts/mine_bank/hist_at_edit_check.py").read_text()
ENV = dict(__import__("os").environ, GIT_CONFIG_COUNT="2", GIT_CONFIG_KEY_0="core.hooksPath", GIT_CONFIG_VALUE_0="/dev/null",
           GIT_CONFIG_KEY_1="core.fsmonitor", GIT_CONFIG_VALUE_1="false", GIT_TERMINAL_PROMPT="0")
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$")
hs_src = (ROOT / "scripts/mine_bank/heredoc_edit_check.py").read_text()
hns = {}
exec(hs_src[hs_src.index("def hunks"):hs_src.index("def run(")], {"re": re, "TEST": TEST}, hns)
T = {}
for f in ("data/swe_rebench/candidates.jsonl", "data/tasks.jsonl"):
    for l in open(ROOT / f):
        j = json.loads(l)
        T[j["instance_id"]] = j
TASKS = ["cta-observatory__pyirf-193", "RDFLib__pySHACL-285", "Netflix-Skunkworks__policyuniverse-147", "terryyin__lizard-144",
         "lucianopaz__compress_pickle-28", "terryyin__lizard-370", "klen__peewee_migrate-203", "hgrecco__pint-pandas-264",
         "fastapi_11194", "rich_3278", "rich_3676", "rich_3506", "rich_3521", "geopandas__geopandas-3240", "fastapi_15589"]


def sh(cmd, w):
    r = subprocess.run(["/bin/bash", "-c", cmd.replace(".git/agent", str(AG))], cwd=w, env=ENV, capture_output=True, text=True, timeout=900)
    return r.returncode, r.stdout, r.stderr


def reset(w):
    subprocess.run(["git", "checkout", "-q", "--", "."], cwd=w, env=ENV)
    subprocess.run(["git", "clean", "-q", "-f", "--", "pkg_new_ab.py"], cwd=w, env=ENV)
    AG.mkdir(exist_ok=True)
    for q in AG.iterdir():
        q.unlink()


def a_cmd(path, old, new):
    return "mkdir -p .git/agent\ncat > .git/agent/old <<'OLD_TEXT'\n" + old + "OLD_TEXT\ncat > .git/agent/new <<'NEW_TEXT'\n" + new + "NEW_TEXT\n" + B.A_STEP.replace("PATH", path)


bad = collections.Counter()
c = collections.Counter()
print("#### A")
for iid in TASKS:
    w = WT / iid
    if not (w / ".git").exists():
        print(iid, "no checkout")
        continue
    reset(w)
    hs = hns["hunks"](T[iid]["patch"])
    files = sorted({h[0] for h in hs})
    texts = {f: (w / f).read_text() for f in files}
    for f, o, n in hs:
        texts[f] = texts[f].replace(o, n, 1)
    ref = hashlib.md5("".join(texts[f] for f in files).encode()).hexdigest()
    for f, o, n in hs:
        rc, out, err = sh(a_cmd(f, o, n), w)
        c["hunks"] += 1
        c["rc0"] += rc == 0
        c["hist"] += B.A_HEAD in out
        c["nohist"] += B.A_NOHIST in out
        if rc or not ((B.A_HEAD in out) ^ (B.A_NOHIST in out)) or "EDITED" not in out:
            bad["A1"] += 1
            print("  A1 bad", iid, f, rc, err[:150])
    mine = hashlib.md5("".join((w / f).read_text() for f in files).encode()).hexdigest()
    c["same"] += mine == ref
    # (3) second edit of lines just added: the last hunk's new text -> itself plus a comment line
    f, o, n = hs[-1]
    added = [l for l in n.splitlines(keepends=True) if l not in o.splitlines(keepends=True)]
    if added:
        rc, out, err = sh(a_cmd(f, added[0], added[0] + "# ab\n"), w)
        ok3 = rc == 0 and B.A_NOHIST in out and B.A_HEAD not in out if "old text found 1 times" in out else rc == 0
        c["second"] += 1
        c["second_ok"] += ok3
        if not ok3:
            bad["A3"] += 1
            print("  A3 bad", iid, rc, out[-300:])
    reset(w)
    # (2) old text not in the file
    rc, out, err = sh(a_cmd(hs[0][0], "this line is not in the file xyz\n", "x\n"), w)
    if not (rc == 0 and "old text found 0 times" in out and B.A_HEAD not in out and B.A_NOHIST not in out):
        bad["A2"] += 1
        print("  A2 bad", iid, rc, out[-200:])
    # (4) a new untracked file, then an edit of it
    rc0, _, _ = sh("cat > pkg_new_ab.py <<'NEW_TEXT'\nX = 1\nNEW_TEXT\n", w)
    rc, out, err = sh(a_cmd("pkg_new_ab.py", "X = 1\n", "X = 2\n"), w)
    if not (rc == 0 and B.A_NOHIST in out and "EDITED" in out):
        bad["A4"] += 1
        print("  A4 bad", iid, rc, out[-200:], err[:200])
    reset(w)
    print(f"  {iid[:34]:34} hunks {len(hs)} | = real patch {mine == ref}", flush=True)
print(f"A: hunks {c['hunks']} exit 0 {c['rc0']} | history {c['hist']} no-history {c['nohist']} | tasks = real patch {c['same']} | second edits {c['second']} ok {c['second_ok']}")

print("#### B")
import ast
reads = []
for d in sorted((ROOT / "data/results").glob("2026-11-19_skill_r118_p*")):
    for l in open(d / "requests/requests.jsonl", errors="replace"):
        r = json.loads(l)
        if "#asb1h." not in r["job"] and "#asb1hpp." not in r["job"]:
            continue
        try:
            calls = (ast.literal_eval(str(r["reply"])).get("message") or {}).get("tool_calls") or []
        except Exception:
            continue
        for x in calls:
            if x["function"]["name"] == "read_file":
                a = json.loads(x["function"]["arguments"])
                if a.get("start_line") and a.get("end_line"):
                    reads.append((r["job"].split("#")[0], a["filepath"], int(a["start_line"]), int(a["end_line"])))
n = ok = same = 0
for iid, path, s0, e0 in reads:
    w = WT / iid
    if not (w / ".git").exists() or not (w / path).exists():
        continue
    rc, out, err = sh(B.B_READ.replace("S,E", f"{s0},{e0}").replace("PATH", path), w)
    n += 1
    ok += rc == 0 and B.B_HEAD in out
    lines = (w / path).read_text().splitlines(keepends=True)[s0 - 1:e0]
    same += out.startswith("".join(lines))
print(f"B: reads {n} | exit 0 with header {ok} | sed lines = file lines {same}")
w = WT / "rich_3521"
rc, out, err = sh(B.B_READ.replace("S,E", "800,840").replace("PATH", "rich/segment.py"), w)
print("B after the end: rc", rc, "|", err.strip()[:80])
bad["B2"] += "has only 751 lines" not in err
sh("cat > pkg_new_ab.py <<'NEW_TEXT'\nX = 1\nNEW_TEXT\n", w)
rc, out, err = sh(B.B_READ.replace("S,E", "1,1").replace("PATH", "pkg_new_ab.py"), w)
print("B untracked: rc", rc, "|", err.strip()[:80])
bad["B3"] += "There is no path pkg_new_ab.py in the commit" not in err
reset(w)
print("problems:", dict(bad) or "none")
