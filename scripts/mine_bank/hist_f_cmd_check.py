"""The exact sbF edit step (scripts/make_sbF.py, asserted equal to the prompt's blocks) on the sparse checkouts.
CPU; bash / git / sed / awk / python3 on our own fixed step only; nothing from the repositories is executed.
Run: python3 -I scripts/mine_bank/hist_f_cmd_check.py CLONE_DIR [sbF|sbF2]   (repo root)
A: (1) the real fixes of 15 tasks hunk by hunk = the real patch, exit 0, history or no-history line after each EDITED;
   (2) old text not in the file: exit 0, neither history nor no-history line; (3) a second edit of lines just added: exit 0,
   the no-history line; (4) a new untracked file edited: exit 0, the no-history line.
B: (1) r118 sb1h / sb1hpp ranged reads through the read command: exit 0, header printed, sed lines = the file's lines;
   (2) a start after the end: 'has only N lines'; (3) an untracked file: 'There is no path'."""
import collections, hashlib, importlib.util, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("make_sbF", ROOT / "scripts/make_sbF.py")
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
VARIANT = sys.argv[2] if len(sys.argv) > 2 else 'sbF'
STEP = B.STEPS[VARIANT]
print('variant', VARIANT)
CLONES = Path(sys.argv[1])
WT = CLONES.parent / "wt"
AG = CLONES.parent / "agent_f"
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
    return "mkdir -p .git/agent\ncat > .git/agent/old <<'OLD_TEXT'\n" + old + "OLD_TEXT\ncat > .git/agent/new <<'NEW_TEXT'\n" + new + "NEW_TEXT\n" + STEP.replace("PATH", path)


bad = collections.Counter()
c = collections.Counter()
print("#### F")
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
        c["hist"] += B.F_HEAD in out
        c["nohist"] += B.F_NOHIST in out
        if rc or not ((B.F_HEAD in out) ^ (B.F_NOHIST in out)) or "EDITED" not in out:
            bad["A1"] += 1
            print("  A1 bad", iid, f, rc, err[:150])
    mine = hashlib.md5("".join((w / f).read_text() for f in files).encode()).hexdigest()
    c["same"] += mine == ref
    # (3) second edit of lines just added: the last hunk's new text -> itself plus a comment line
    f, o, n = hs[-1]
    added = [l for l in n.splitlines(keepends=True) if l not in o.splitlines(keepends=True)]
    if added:
        rc, out, err = sh(a_cmd(f, added[0], added[0] + "# ab\n"), w)
        ok3 = rc == 0 and B.F_NOHIST in out and B.F_HEAD not in out if "old text found 1 times" in out else rc == 0
        c["second"] += 1
        c["second_ok"] += ok3
        if not ok3:
            bad["A3"] += 1
            print("  A3 bad", iid, rc, out[-300:])
    reset(w)
    # (2) old text not in the file
    rc, out, err = sh(a_cmd(hs[0][0], "this line is not in the file xyz\n", "x\n"), w)
    if not (rc == 0 and "old text found 0 times" in out and B.F_HEAD not in out and B.F_NOHIST not in out):
        bad["A2"] += 1
        print("  A2 bad", iid, rc, out[-200:])
    # (4) a new untracked file, then an edit of it
    rc0, _, _ = sh("cat > pkg_new_ab.py <<'NEW_TEXT'\nX = 1\nNEW_TEXT\n", w)
    rc, out, err = sh(a_cmd("pkg_new_ab.py", "X = 1\n", "X = 2\n"), w)
    if not (rc == 0 and B.F_NOHIST in out and "EDITED" in out):
        bad["A4"] += 1
        print("  A4 bad", iid, rc, out[-200:], err[:200])
    reset(w)
    print(f"  {iid[:34]:34} hunks {len(hs)} | = real patch {mine == ref}", flush=True)
print(f"A: hunks {c['hunks']} exit 0 {c['rc0']} | history {c['hist']} no-history {c['nohist']} | tasks = real patch {c['same']} | second edits {c['second']} ok {c['second_ok']}")


# (5) the model's own r118 / r119 edits: the step's commits = the offline window check's F3 commits (data/analysis/hist_window_cache.json)
import re as _re
D = json.loads((ROOT / "data/analysis/hist_window_cache.json").read_text())
n5 = same5 = nochg = 0
H5 = []
for key, row in D["cache"].items():
    if row.get("found") != 1 or not row.get("F"):
        continue
    iid, path, old = key.split("|", 2)
    if not old.endswith("\n"):  # sb1's edit_file old_strings: a heredoc holds whole lines only
        old += "\n"
    w = WT / iid
    reset(w)
    rc, out, err = sh(a_cmd(path, old, old + "# f\n"), w)
    mine = _re.findall(r"^commit ([0-9a-f]{7,}) ", out, _re.M)
    ref = _re.findall(r"^commit ([0-9a-f]{7,}) ", row["F3"], _re.M)
    n5 += 1
    same5 += [x[:7] for x in mine] == [x[:7] for x in ref]
    hp = out.split(B.F_HEAD, 1)[1] if B.F_HEAD in out else ""
    H5.append(len(hp))
    for part in _re.split(r"(?m)^(?=commit [0-9a-f]{7,} )", hp):
        if part.startswith("commit") and VARIANT == "sbF2":
            body = part.splitlines()[1:]
            nochg += not any(l[:1] in "+-" for l in body)
            bad["F7"] += any(l and l[:1] not in "+-" for l in body)
    if rc or [x[:7] for x in mine] != [x[:7] for x in ref]:
        bad["F5"] += 1
        print("  F5 differs", iid, path, rc, mine, ref, err[:120])
    reset(w)
print(f"model edits inside a function: {n5} | same commits as the window check {same5}")
print(f"history chars (header excluded): median {sorted(H5)[len(H5) // 2] if H5 else 0} p90 {sorted(H5)[int(len(H5) * .9)] if H5 else 0} max {max(H5 or [0])}"
      f" | commits with no visible changed line {nochg}")
# (6) a throwaway repo (scratchpad): a tracked non-Python file and a tracked .py file ast cannot parse -> the step still edits
#     and prints the history of the replaced lines; a module-level line -> the replaced lines too; a nested function -> the inner one
import shutil, tempfile
tmp = Path(tempfile.mkdtemp(dir=CLONES.parent))
def g(*a):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a], cwd=tmp, env=ENV, check=True, capture_output=True)
g("init", "-q")
(tmp / "notes.txt").write_text("alpha\nbeta\n")
(tmp / "old2.py").write_text("print 'hi'\nx = 1\n")
(tmp / "mod.py").write_text("X = 1\n\n\ndef outer(a):\n    def inner(b):\n        return b + 1\n    return inner(a)\n")
g("add", "-A"); g("commit", "-q", "-m", "first")
(tmp / "mod.py").write_text("X = 2\n\n\ndef outer(a):\n    def inner(b):\n        return b + 2\n    return inner(a)\n")
g("commit", "-q", "-am", "second")
AG.mkdir(exist_ok=True)
for f, o, n, want in (("notes.txt", "beta\n", "gamma\n", "1,"), ("old2.py", "x = 1\n", "x = 3\n", "1,"), ("mod.py", "X = 2\n", "X = 3\n", "1,"),
                      ("mod.py", "        return b + 2\n", "        return b + 3\n", "2,")):
    for q in AG.iterdir():
        q.unlink()
    rc, out, err = sh(a_cmd(f, o, n), tmp)
    rng = (AG / "range").read_text() if (AG / "range").exists() else ""
    ok = rc == 0 and "EDITED" in out and B.F_HEAD in out and "Traceback" not in out + err
    print(f"  {f:9} {o.strip():14} rc {rc} EDITED {'EDITED' in out} history {B.F_HEAD in out} range {rng}")
    bad["F6"] += not ok
    subprocess.run(["git", "checkout", "-q", "--", "."], cwd=tmp, env=ENV)
# expected ranges: notes.txt line 2 only; old2.py line 2 only (ast fails); mod.py line 1 only (module level); inner def lines 5-6
print("  ranges expected: notes.txt 2,2 | old2.py 2,2 | mod.py 1,1 | mod.py 5,6 (inner)")
shutil.rmtree(tmp)
print("problems:", dict(bad) or "none")
