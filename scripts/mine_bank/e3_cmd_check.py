"""Checks sbE3's exact commands (make_expect_arms: expect_cmd3 / CHECK3 / EDIT_STEP3) in throwaway git repos made here with our own
code only (reuses expect_cmd_check's repo / sh helpers). Run: python3 -I scripts/mine_bank/e3_cmd_check.py SCRATCH_DIR"""
import re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
src = (ROOT / "scripts/mine_bank/expect_cmd_check.py").read_text()
src = src[:src.index('\nfor arm in ("sbE1"')]  # helpers only
g = {"__name__": "e3", "__file__": str(ROOT / "scripts/mine_bank/expect_cmd_check.py")}
exec(compile(src, "expect_cmd_check_helpers", "exec"), g)
X, repo, sh, check, bad, EXP, ENV = g["X"], g["repo"], g["sh"], g["check"], g["bad"], g["EXP"], g["ENV"]
E = X.EV3
FIX_OLD = "    if not text:\n        return dict()\n"
FIX_NEW = "    if not text:\n        return dict()\n    if strict and '=' not in text:\n        raise ValueError('missing =')\n"


def edit(w, old, new):
    return sh(w, "mkdir -p .git/agent\ncat > .git/agent/old <<'OLD_TEXT'\n" + old + "OLD_TEXT\ncat > .git/agent/new <<'NEW_TEXT'\n" + new + "NEW_TEXT\n" + X.EDIT_STEP3.replace("PATH", "pkg/parser.py"))


def diff(w):
    return subprocess.run(["git", "diff"], cwd=w, env=ENV, capture_output=True, text=True).stdout


print("#### sbE3")
w = repo(10)
rc, out, err = edit(w, FIX_OLD, FIX_NEW)
check("0 first edit with no expectation -> held back once, file unchanged, no EDITED line", rc == 0 and E["refused"] in out and not re.search(r"(?m)^EDITED ", out) and diff(w) == "", out + err)
rc, out, err = edit(w, "    nothing like this\n", "x\n")
check("0b found 0 after the hold: no edit, no second hold line", rc == 0 and "found 0 times" in out and E["refused"] not in out, out + err)
rc, out, err = sh(w, X.expect_cmd3("import sys\nsys.path.insert(0, '.')\nfrom pkg.parser import parse\nassert parse('a=1')['a'] == '1'\n"))
check("1 passes before any edit -> 'not the one in the issue'", rc == 0 and E["nothing"] in out and E["late"] not in out, out + err)
rc, out, err = sh(w, X.expect_cmd3("import sys\nsys.path.insert(0, '.')\nfrom pkg.parser import parse\ntry\n    pass\n"))
check("2 broken script -> 'script broken', not 'shown'", rc == 0 and E["broken"] in out and E["shown"] not in out, out + err)
rc, out, err = sh(w, X.expect_cmd3(EXP))
check("3 fails before any edit -> 'shown' + the failure lines", rc == 0 and E["shown"] in out and "AssertionError: strict mode accepted" in out, out + err)
rc, out, err = edit(w, "    if not text:\n        return dict()\n", "    if not text:\n        raise ValueError('empty')\n")
check("4 a wrong edit -> applied, 'still fails'", rc == 0 and re.search(r"(?m)^EDITED ", out) and E["still"] in out, out + err)
rc, out, err = edit(w, "    if not text:\n        raise ValueError('empty')\n", FIX_NEW)
check("5 the fixing edit -> 'passes with your edit'", rc == 0 and E["done"] in out, out + err)
rc, out, err = sh(w, X.RERUN)
check("6 the short re-run repeats the verdict", rc == 0 and E["done"] in out, out + err)
st = subprocess.run(["git", "status", "--short", "--untracked-files=all"], cwd=w, env=ENV, capture_output=True, text=True).stdout
st = "\n".join(l for l in st.splitlines() if "__pycache__" not in l)  # the harness git-excludes bytecode (swegemma agent_runner setup_git_exclude)
check("7 only the source file changed (bytecode excluded as the harness does)", st.strip() == "M pkg/parser.py", st)
w = repo(10)
sh(w, X.expect_cmd3(EXP))
rc, out, err = edit(w, FIX_OLD, FIX_NEW)
check("8 expectation first -> the first edit is applied (no hold)", rc == 0 and re.search(r"(?m)^EDITED ", out) and E["refused"] not in out and E["done"] in out, out + err)
w = repo(10)
edit(w, FIX_OLD, FIX_NEW)
rc, out, err = edit(w, FIX_OLD, FIX_NEW)
check("9 the same edit sent twice without an expectation -> applied the second time", rc == 0 and re.search(r"(?m)^EDITED ", out) and E["refused"] not in out, out + err)
for age, want in ((400, True), (100, False), (None, False)):
    w = repo(age)
    rc, out, err = sh(w, X.expect_cmd3(EXP))
    check(f"10 baseline age {age}: late line {'shown' if want else 'absent'}", rc == 0 and (E["late"] in out) == want and E["shown"] in out, out + err)
w = repo(400)
sh(w, X.expect_cmd3(EXP))
rc, out, err = edit(w, FIX_OLD, FIX_NEW)
check("11 late run after an edit: no late line", rc == 0 and E["late"] not in out and E["done"] in out, out + err)
print("problems:", bad or "none")
