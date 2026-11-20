"""sbE6 command checks in throwaway git repos made here with our own code. Run: python3 -I scripts/mine_bank/e6_cmd_check.py SCRATCH_DIR
Commands run WITH their '# end of command' line. The writer's expect.py is written as write_file would (a plain file write)."""
import importlib.util, os, re, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
src = (ROOT / "scripts/mine_bank/expect_cmd_check.py").read_text()
src = src[:src.index('\nfor arm in ("sbE1"')]
g = {"__name__": "e6", "__file__": str(ROOT / "scripts/mine_bank/expect_cmd_check.py")}
exec(compile(src, "helpers", "exec"), g)
repo, sh, check, bad, EXP, ENV = g["repo"], g["sh"], g["check"], g["bad"], g["EXP"], g["ENV"]
sp = importlib.util.spec_from_file_location("X6", ROOT / "scripts/make_expect_e6.py"); X6 = importlib.util.module_from_spec(sp); sp.loader.exec_module(X6)
E, END = X6.EV6, "# end of command\n"
FIX_OLD = "    if not text:\n        return dict()\n"
FIX_NEW = "    if not text:\n        return dict()\n    if strict and '=' not in text:\n        raise ValueError('missing =')\n"
ED = re.compile(r"(?m)^EDITED ")
def edit(w, old, new):
    return sh(w, "mkdir -p .git/agent\ncat > .git/agent/old <<'OLD_TEXT'\n" + old + "OLD_TEXT\ncat > .git/agent/new <<'NEW_TEXT'\n" + new + "NEW_TEXT\n" + X6.EDIT6.replace("PATH", "pkg/parser.py") + END)
def writer(w, body):
    (w / ".git/agent").mkdir(parents=True, exist_ok=True); (w / ".git/agent/expect.py").write_text(body + "# end of content\n")
def status(w):
    st = subprocess.run(["git", "status", "--short", "--untracked-files=all"], cwd=w, env=ENV, capture_output=True, text=True).stdout
    return "\n".join(l for l in st.splitlines() if "__pycache__" not in l).strip()

print("#### sbE6 solver commands")
w = repo(10)
rc, out, err = sh(w, X6.CHECK_CMD + END)
check("1 check command with NO expect.py -> 'no expectation file', not 'shown'", rc == 0 and E["missing"] in out and E["shown"] not in out, out + err)
writer(w, EXP)
rc, out, err = sh(w, X6.CHECK_CMD + END)
check("2 the writer's failing expect.py -> 'shown' + the failure", rc == 0 and E["shown"] in out and "AssertionError: strict mode accepted" in out, out + err)
rc, out, err = sh(w, X6.expect_cmd6(("import sys\nsys.path.insert(0, '.')\nfrom pkg.parser import parse\nassert parse('a=1')['a'] == '1'\n")) + END)
check("3 rewrite via the expectation command, passes unedited -> 'not the one in the issue'", rc == 0 and E["nothing"] in out, out + err)
rc, out, err = sh(w, X6.expect_cmd6("import sys\nsys.path.insert(0, '.')\ntry\n    pass\n") + END)
check("4 broken script -> 'script broken'", rc == 0 and E["broken"] in out and E["shown"] not in out, out + err)
rc, out, err = sh(w, X6.expect_cmd6(EXP) + END)
check("5 rewrite back to the failing one -> 'shown'", rc == 0 and E["shown"] in out, out + err)
rc, out, err = edit(w, FIX_OLD, "    if not text:\n        raise ValueError('empty')\n")
check("6 wrong edit -> applied (expect.py exists: no hold), 'still fails'", rc == 0 and ED.search(out) and E["refused"] not in out and E["still"] in out, out + err)
rc, out, err = edit(w, "    if not text:\n        raise ValueError('empty')\n", FIX_NEW)
check("7 fixing edit -> 'passes with your edit'", rc == 0 and E["done"] in out, out + err)
check("8 only the source file changed", status(w) == "M pkg/parser.py", status(w))
w = repo(10)
rc, out, err = edit(w, FIX_OLD, FIX_NEW)
check("9 writer wrote nothing + edit first -> held back once", rc == 0 and E["refused"] in out and not ED.search(out), out + err)
w = repo(400); writer(w, EXP)
rc, out, err = sh(w, X6.CHECK_CMD + END)
check("10 late run, unedited -> 'shown' + the late line", rc == 0 and E["shown"] in out and E["late"] in out, out + err)

print("#### sbE6 search script restart guard")
S = ROOT / "submissions/sbE6/skills/evidence/scripts/evidence.py"
env = dict(ENV); env.pop("PYTHONPATH", None)
w = Path(tempfile.mkdtemp(dir=sys.argv[1] if len(sys.argv) > 1 else None))
(w / "pkg").mkdir(); (w / "pkg/reader.py").write_text("class Reader:\n    pass\n")
for c in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "i"]):
    subprocess.run(["git", *c], cwd=w, env=ENV, check=True)
r = subprocess.run([sys.executable, "-I", str(S), "Reader"], cwd=w, env=env, capture_output=True, text=True, timeout=60)
check("11 first call, no expect.py -> the normal search result", "WHERE THE ISSUE'S NAMES ARE" in r.stdout and "pkg/reader.py:1:class Reader:" in r.stdout, r.stdout + r.stderr)
(w / ".git/agent").mkdir(parents=True, exist_ok=True); (w / ".git/agent/expect.py").write_text("assert False\n")
r = subprocess.run([sys.executable, "-I", str(S), "Reader"], cwd=w, env=env, capture_output=True, text=True, timeout=60)
check("12 restart with expect.py present -> EXPECTATION ALREADY WRITTEN only", r.stdout.strip() == X6.P6.ALREADY, r.stdout + r.stderr)
print("problems:", bad or "none")
