"""Checks scripts/edit_fallback.halve on sb1hl's and sbE3's edit steps in throwaway git repos made here with our own code (a regex
line with backslashes, written by us). Run: python3 -I scripts/mine_bank/edit_fallback_check.py SCRATCH_DIR"""
import importlib.util, os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
def load(name, path):
    sp = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
F = load("F", ROOT / "scripts/edit_fallback.py")
X = load("X", ROOT / "scripts/make_expect_arms.py")
SCR = Path(sys.argv[1]); SCR.mkdir(parents=True, exist_ok=True)
ENV = dict(os.environ, GIT_CONFIG_COUNT="2", GIT_CONFIG_KEY_0="core.hooksPath", GIT_CONFIG_VALUE_0="/dev/null", GIT_CONFIG_KEY_1="core.fsmonitor",
           GIT_CONFIG_VALUE_1="false", GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
B = chr(92)
LINE = "    r'(?:" + B + "x1b([(@-Z" + B + B + "-_]|" + B + "[[0-?]*[ -/]*[@-~]))'\n"   # the file: \x1b ... \\- ... \[
NEWL = "    r'(?:" + B + "x1b([0-?@-Z" + B + B + "-_]|" + B + "[[0-?]*[ -/]*[@-~]))'\n"
SRC = "import re\n\nRE = re.compile(\n" + LINE + ")\n"
dbl = lambda t: t.replace(B, B + B)
bad = []

def check(name, ok, info=""):
    print(f"  {'ok ' if ok else 'BAD'} {name}" + ("" if ok else " | " + info[:600]))
    if not ok: bad.append(name)

def repo(text):
    w = Path(tempfile.mkdtemp(dir=SCR)); (w / "pkg").mkdir(); (w / "pkg/ansi.py").write_text(text)
    for c in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "i"]):
        subprocess.run(["git", *c], cwd=w, env=ENV, check=True)
    return w

def run(w, step, old, new):
    cmd = "mkdir -p .git/agent\ncat > .git/agent/old <<'OLD_TEXT'\n" + old + "OLD_TEXT\ncat > .git/agent/new <<'NEW_TEXT'\n" + new + "NEW_TEXT\n" + step.replace("PATH", "pkg/ansi.py")
    r = subprocess.run(["/bin/bash", "-c", cmd], cwd=w, env=ENV, capture_output=True, text=True, timeout=60)
    return r.stdout + r.stderr, (w / "pkg/ansi.py").read_text()

import importlib
H = load("H", ROOT / "scripts/make_sb1h.py")
for name, step in (("sb1hl", F.halve(H.PY_STEP)), ("sbE3", F.halve(X.EDIT_STEP3))):
    print("####", name)
    pre = (lambda w: (w / ".git/agent").mkdir(exist_ok=True) or (w / ".git/agent/expect.py").write_text("pass\n")) if name == "sbE3" else (lambda w: None)
    w = repo(SRC); pre(w)
    out, txt = run(w, step, dbl(LINE), dbl(NEWL))
    check("1 doubled old + new (what the model sends) -> halved, applied, file = the intended new line", "read as single" in out and "old text found 1 times" in out and txt == SRC.replace(LINE, NEWL), out)
    w = repo(SRC); pre(w)
    out, txt = run(w, step, LINE, NEWL)
    check("2 exact old text -> applied as before, no halving note", "read as single" not in out and "old text found 1 times" in out and txt == SRC.replace(LINE, NEWL), out)
    w = repo(SRC); pre(w)
    out, txt = run(w, step, dbl(LINE).replace("@-Z", "A-Z"), NEWL)
    check("3 doubled but otherwise wrong -> found 0, file unchanged", "old text found 0 times" in out and "read as single" not in out and txt == SRC, out)
    two = SRC + "\nRE2 = re.compile(\n" + LINE + ")\n"
    w = repo(two); pre(w)
    out, txt = run(w, step, dbl(LINE), dbl(NEWL))
    check("4 halved text occurs twice -> not applied (found 0)", "old text found 0 times" in out and txt == two, out)
    w = repo("x = 1\n"); pre(w)
    out, txt = run(w, step, "x = 1\n", "x = 2\n")
    check("5 plain edit without backslashes -> unchanged behaviour", "old text found 1 times" in out and "read as single" not in out and txt == "x = 2\n", out)
print("problems:", bad or "none")
