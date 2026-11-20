"""Checks sbG's exact edit step (scripts/make_sbG.py G_STEP, asserted equal to the prompt's blocks) in throwaway git repos made
here (scratch dir given as argv[1]); also on a local clone of this project's repo (real history, no network). Only our own
step and git run. Run: python3 -I scripts/mine_bank/gate_cmd_check.py SCRATCH_DIR"""
import importlib.util, os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("make_sbG", ROOT / "scripts/make_sbG.py")
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)
SCR = Path(sys.argv[1])
SCR.mkdir(parents=True, exist_ok=True)
ENV = dict(os.environ, GIT_CONFIG_COUNT="2", GIT_CONFIG_KEY_0="core.hooksPath", GIT_CONFIG_VALUE_0="/dev/null", GIT_CONFIG_KEY_1="core.fsmonitor",
           GIT_CONFIG_VALUE_1="false", GIT_TERMINAL_PROMPT="0", GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
bad = []


def git(w, *a, env=None):
    return subprocess.run(["git", *a], cwd=w, env=env or ENV, capture_output=True, text=True, check=True).stdout


def edit_cmd(path, old, new):
    return "mkdir -p .git/agent\ncat > .git/agent/old <<'OLD_TEXT'\n" + old + "OLD_TEXT\ncat > .git/agent/new <<'NEW_TEXT'\n" + new + "NEW_TEXT\n" + G.G_STEP.replace("PATH", path)


def sh(w, cmd):
    r = subprocess.run(["/bin/bash", "-c", cmd], cwd=w, env=ENV, capture_output=True, text=True, timeout=120)
    return r.returncode, r.stdout, r.stderr


def check(name, ok, info=""):
    print(f"  {'ok ' if ok else 'BAD'} {name}" + (f" | {info}" if info and not ok else ""))
    if not ok:
        bad.append(name)


def repo(baseline_age):
    """a repo with history in pkg/mod.py (f: 3 commits, one 'Fix ... same kind'), a nested function, a module-level line,
    notes.txt, old2.py (Python 2, unparseable), then the harness's baseline commit + tag dated baseline_age s ago (None: no tag)."""
    w = Path(tempfile.mkdtemp(dir=SCR))
    git(w, "init", "-q")
    (w / "pkg").mkdir()
    m = w / "pkg/mod.py"
    m.write_text("X = 1\n\n\ndef f(a):\n    return a + 1\n\n\ndef g(b):\n    return b * 2\n\n\ndef outer(c):\n    def inner(d):\n        return d - 1\n    return inner(c)\n")
    (w / "notes.txt").write_text("alpha\nbeta\n")
    (w / "old2.py").write_text("print 'hi'\nx = 1\n")
    git(w, "add", "-A"); git(w, "commit", "-q", "-m", "Add mod")
    m.write_text(m.read_text().replace("    return a + 1\n", "    if a is None:\n        raise ValueError('a is None')\n    return a + 1\n"))
    git(w, "commit", "-q", "-am", "Fix f raising ValueError for None")
    m.write_text(m.read_text().replace("    return b * 2\n", "    return b * 3\n"))
    git(w, "commit", "-q", "-am", "Change g factor")
    if baseline_age is not None:
        d = str(int(time.time()) - baseline_age)
        e = dict(ENV, GIT_COMMITTER_DATE=d + " +0000", GIT_AUTHOR_DATE=d + " +0000")
        git(w, "add", "-A", env=e); git(w, "commit", "-q", "-m", "baseline", "--allow-empty", env=e); git(w, "tag", "-f", "_swegemma_baseline", env=e)
    return w


print("#### young run (baseline 10 s ago)")
w = repo(10)
m = w / "pkg/mod.py"
before = m.read_text()
rc, out, err = sh(w, edit_cmd("pkg/mod.py", "    return a + 1\n", "    return a + 2\n"))
check("1 first edit into f is held: file unchanged", rc == 0 and m.read_text() == before and G.HOLD_HEAD in out and not re.search(r"(?m)^EDITED ", out), out + err)
check("1 history: 2 commits of f with changed lines", out.count("\ncommit ") == 2 and "Fix f raising ValueError for None" in out and "+    if a is None:" in out, out)
check("1 tail line with the exact apply command", out.rstrip().splitlines()[-1] == G.HOLD_TAIL + "pkg/mod.py", out[-200:])
check("1 history lines are titles and +/- lines only", all(re.match(r"(commit [0-9a-f]{7,} \d{4}-\d\d-\d\d |[-+])", l) for l in out.split(G.HOLD_HEAD)[1].strip().splitlines()[:-1]), out)
rc, out, err = sh(w, G.APPLY.replace("PATH", "pkg/mod.py"))
check("2 apply as it is: EDITED, file changed, diff shown", rc == 0 and "EDITED" in out and "+    return a + 2" in out and "return a + 2" in m.read_text(), out + err)
rc, out, err = sh(w, edit_cmd("pkg/mod.py", "        raise ValueError('a is None')\n", "        raise TypeError('a is None')\n"))
check("3 a later edit into f (shown): applied at once", rc == 0 and re.search(r"(?m)^EDITED ", out) is not None and G.HOLD_HEAD not in out and "TypeError" in m.read_text(), out + err)
rc, out, err = sh(w, edit_cmd("pkg/mod.py", "    return b * 3\n", "    return b * 4\n"))
check("4 first edit into g: held", G.HOLD_HEAD in out and "b * 3" in m.read_text() and "Change g factor" in out, out)
rc, out, err = sh(w, edit_cmd("pkg/mod.py", "    return b * 3\n", "    return b * 5\n"))
check("5 resend changed: the new text applied", "EDITED" in out and "b * 5" in m.read_text() and "b * 4" not in m.read_text(), out + err)
rc, out, err = sh(w, edit_cmd("pkg/mod.py", "X = 1\n", "X = 2\n"))
check("8 module-level line: held, range = the line", G.HOLD_HEAD in out and (w / ".git/agent/seen").read_text().split()[-1] == "1,1:pkg/mod.py", out)
rc, out, err = sh(w, edit_cmd("pkg/mod.py", "        return d - 1\n", "        return d - 2\n"))
check("8b nested function: held, range = the inner def", G.HOLD_HEAD in out and (w / ".git/agent/seen").read_text().split()[-1] == "15,16:pkg/mod.py", (w / ".git/agent/seen").read_text())
rc, out, err = sh(w, edit_cmd("notes.txt", "beta\n", "gamma\n"))
check("9 non-Python file: held, range = the line", G.HOLD_HEAD in out and (w / ".git/agent/seen").read_text().split()[-1] == "2,2:notes.txt" and "Traceback" not in out + err, out + err)
rc, out, err = sh(w, edit_cmd("old2.py", "x = 1\n", "x = 3\n"))
check("10 unparseable .py: held, range = the line", G.HOLD_HEAD in out and (w / ".git/agent/seen").read_text().split()[-1] == "2,2:old2.py" and "Traceback" not in out + err, out + err)
rc, out, err = sh(w, edit_cmd("pkg/mod.py", "    return a + 2\n", "    return a + 7\n"))
check("11 own new lines (not in HEAD): applied, no history", "EDITED" in out and G.HOLD_HEAD not in out and "a + 7" in m.read_text(), out)
rc, out, err = sh(w, edit_cmd("pkg/mod.py", "not in the file\n", "x\n"))
check("12 found 0: count only, nothing else", rc == 0 and out.strip() == "old text found 0 times", out + err)
m.write_text(m.read_text() + "\n\ndef h():\n    return 1\n\n\ndef i():\n    return 1\n")
rc, out, err = sh(w, edit_cmd("pkg/mod.py", "    return 1\n", "    return 2\n"))
check("12b found 2: count only", rc == 0 and out.strip() == "old text found 2 times", out + err)
rc, out, err = sh(w, "rm -rf .git/agent && " + edit_cmd("pkg/mod.py", "    return inner(c)\n", "    return inner(c) + 0\n"))
check("12c a fresh .git/agent (the first edit of a run) works", G.HOLD_HEAD in out, out + err)

print("#### late run (baseline 400 s ago) and no tag")
for age, name in ((400, "6 late run"), (None, "7 no baseline tag")):
    w = repo(age)
    rc, out, err = sh(w, edit_cmd("pkg/mod.py", "    return a + 1\n", "    return a + 2\n"))
    check(f"{name}: applied at once, no history", rc == 0 and "EDITED" in out and G.HOLD_HEAD not in out and "a + 2" in (w / "pkg/mod.py").read_text(), out + err)

print("#### real history: a local clone of this project's repo (no network)")
c = Path(tempfile.mkdtemp(dir=SCR)) / "self"
subprocess.run(["git", "clone", "-q", "--no-hardlinks", str(ROOT), str(c)], env=ENV, check=True)
d = str(int(time.time()) - 5)
e = dict(ENV, GIT_COMMITTER_DATE=d + " +0000", GIT_AUTHOR_DATE=d + " +0000")
git(c, "commit", "-q", "-m", "baseline", "--allow-empty", env=e); git(c, "tag", "-f", "_swegemma_baseline", env=e)
src = (c / "scripts/make_sbab.py").read_text()
old = "    out, prev_new = [], None\n" if "    out, prev_new = [], None\n" in src else None
if old is None:
    old = next(l for l in src.splitlines(keepends=True) if l.startswith("    ") and src.count(l) == 1 and len(l) > 30)
rc, out, err = sh(c, edit_cmd("scripts/make_sbab.py", old, old.replace("\n", "  # x\n")))
fn = re.search(r"seen", "seen") and (c / ".git/agent/seen").read_text().split()[-1]
ref = git(c, "log", "-L", fn, "-n", "3", "--format=commit %h %ad %s", "--date=short")
mine = re.findall(r"^commit ([0-9a-f]+) ", out, re.M)
check("13 real repo: held, same commits as git log -L on the function", G.HOLD_HEAD in out and mine == re.findall(r"^commit ([0-9a-f]+) ", ref, re.M) and len(mine) >= 1, out[:600])
check("13 every shown commit has a changed line, each <= 15", all(0 < len([l for l in part.splitlines()[1:] if l[:1] in "+-"]) <= 15 for part in re.split(r"(?m)^(?=commit )", out.split(G.HOLD_HEAD)[1]) if part.startswith("commit")), out[:800])
print(f"  real-repo held output: {len(out)} chars, {len(mine)} commits")
shutil.rmtree(c.parent)
print("problems:", bad or "none")
