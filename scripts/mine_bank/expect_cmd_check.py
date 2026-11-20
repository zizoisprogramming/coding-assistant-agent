"""Checks the expectation arms' exact commands (make_expect_arms: expect_cmd / check_sh / EDIT_STEP) in throwaway git repos made
here with our own code only. Run: python3 -I scripts/mine_bank/expect_cmd_check.py SCRATCH_DIR"""
import importlib.util, os, re, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("X", ROOT / "scripts/make_expect_arms.py")
X = importlib.util.module_from_spec(spec)
spec.loader.exec_module(X)
SCR = Path(sys.argv[1]); SCR.mkdir(parents=True, exist_ok=True)
ENV = dict(os.environ, GIT_CONFIG_COUNT="2", GIT_CONFIG_KEY_0="core.hooksPath", GIT_CONFIG_VALUE_0="/dev/null", GIT_CONFIG_KEY_1="core.fsmonitor",
           GIT_CONFIG_VALUE_1="false", GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
E = X.EV
bad = []
PARSER = "def parse(text, strict=False):\n    if not text:\n        return dict()\n    key, _, value = text.partition('=')\n    return dict([(key, value)])\n"
EXP = ("import sys\nsys.path.insert(0, '.')\nfrom pkg.parser import parse\n\ntry:\n    parse('a', strict=True)\nexcept ValueError:\n    pass\nelse:\n"
       "    raise AssertionError('strict mode accepted text without =')\nassert parse('a=1', strict=True)['a'] == '1'\n")


def check(name, ok, info=""):
    print(f"  {'ok ' if ok else 'BAD'} {name}" + (f" | {info[:700]}" if not ok else ""))
    if not ok:
        bad.append(name)


def repo(age):
    w = Path(tempfile.mkdtemp(dir=SCR))
    (w / "pkg").mkdir()
    (w / "pkg/__init__.py").write_text("")
    (w / "pkg/parser.py").write_text(PARSER)
    subprocess.run(["git", "init", "-q"], cwd=w, env=ENV, check=True)
    subprocess.run(["git", "add", "-A"], cwd=w, env=ENV, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=w, env=ENV, check=True)
    if age is not None:
        d = str(int(time.time()) - age)
        e = dict(ENV, GIT_COMMITTER_DATE=d + " +0000", GIT_AUTHOR_DATE=d + " +0000")
        subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "baseline"], cwd=w, env=e, check=True)
        subprocess.run(["git", "tag", "-f", "_swegemma_baseline"], cwd=w, env=e, check=True, capture_output=True)
    return w


def sh(w, cmd):
    r = subprocess.run(["/bin/bash", "-c", cmd], cwd=w, env=ENV, capture_output=True, text=True, timeout=120)
    return r.returncode, r.stdout, r.stderr


def edit(w, old, new):
    return sh(w, "mkdir -p .git/agent\ncat > .git/agent/old <<'OLD_TEXT'\n" + old + "OLD_TEXT\ncat > .git/agent/new <<'NEW_TEXT'\n" + new + "NEW_TEXT\n" + X.EDIT_STEP.replace("PATH", "pkg/parser.py"))


for arm in ("sbE1", "sbE2", "sbX1"):
    print("####", arm)
    w = repo(10)
    rc, out, err = edit(w, "    if not text:\n", "    if not text:\n")
    check("0 an edit before any expectation exists: no check line, exit 0", rc == 0 and "EXPECTATION" not in out, out + err)
    subprocess.run(["git", "checkout", "-q", "--", "."], cwd=w, env=ENV)
    rc, out, err = sh(w, X.expect_cmd(arm, "import sys\nsys.path.insert(0, '.')\nfrom pkg.parser import parse\nassert parse('a=1')['a'] == '1'\n"))
    check("1 passes before any edit -> 'does not show the problem'", rc == 0 and E["nothing"] in out and E["late"] not in out, out + err)
    rc, out, err = sh(w, X.expect_cmd(arm, "import sys\nsys.path.insert(0, '.')\nfrom pkg.parser import parse\ntry\n    pass\n"))
    check("2 broken script -> 'itself is broken', not 'shown'", rc == 0 and E["broken"] in out and "problem is shown" not in out, out + err)
    rc, out, err = sh(w, X.expect_cmd(arm, EXP))
    shown = E["shown_x"] if arm == "sbX1" else E["shown_e"]
    check("3 fails before any edit -> 'the problem is shown' (+ the failure lines)", rc == 0 and shown in out and "AssertionError: strict mode accepted" in out, out + err)
    rc, out, err = edit(w, "    if not text:\n        return dict()\n", "    if not text:\n        raise ValueError('empty')\n")
    check("4 an edit that does not fix it -> 'still fails'", rc == 0 and re.search(r"(?m)^EDITED ", out) and E["still"] in out, out + err)
    rc, out, err = edit(w, "    if not text:\n        raise ValueError('empty')\n", "    if not text:\n        return dict()\n    if strict and '=' not in text:\n        raise ValueError('missing =')\n")
    check("5 the fixing edit -> 'passes with your edit'", rc == 0 and E["done"] in out, out + err)
    rc, out, err = sh(w, X.RERUN)
    check("6 the short re-run command repeats the verdict", rc == 0 and E["done"] in out, out + err)
    st = subprocess.run(["git", "status", "--short", "--untracked-files=all"], cwd=w, env=ENV, capture_output=True, text=True).stdout
    check("7 only the source file changed (expect.py / check.sh / expect.out stay in .git/agent)", st.strip() == "M pkg/parser.py", st)
    for age, name in ((400, "late run"), (None, "no baseline tag")):
        w2 = repo(age)
        rc, out, err = sh(w2, X.expect_cmd(arm, EXP))
        want_late = arm == "sbE2" and age == 400
        check(f"8 {name}: late line {'shown' if want_late else 'absent'}", rc == 0 and (E["late"] in out) == want_late and shown in out, out + err)
    if arm == "sbE2":
        rc, out, err = sh(w2, "true")
        w3 = repo(400)
        sh(w3, X.expect_cmd(arm, EXP))
        rc, out, err = edit(w3, "    if not text:\n        return dict()\n", "    if not text:\n        return dict()\n    if strict and '=' not in text:\n        raise ValueError('missing =')\n")
        check("9 late run after an edit: no late line", rc == 0 and E["late"] not in out and E["done"] in out, out + err)
print("problems:", bad or "none")
