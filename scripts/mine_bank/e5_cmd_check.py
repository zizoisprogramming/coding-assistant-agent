"""r130 command checks in throwaway git repos made here with our own code. Run: python3 -I scripts/mine_bank/e5_cmd_check.py SCRATCH_DIR
Every command is run WITH its trailing '# end of command' line (what the model may copy). sbE5w: expect.py written as write_file would
(a plain file write), the fixed check command, the re-run, 'No such file' before the check command ever ran, the hold-back, edits.
sbE5f: the heredoc expectation + the same events."""
import importlib.util, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
src = (ROOT / "scripts/mine_bank/expect_cmd_check.py").read_text()
src = src[:src.index('\nfor arm in ("sbE1"')]
g = {"__name__": "e5", "__file__": str(ROOT / "scripts/mine_bank/expect_cmd_check.py")}
exec(compile(src, "helpers", "exec"), g)
repo, sh, check, bad, EXP, ENV = g["repo"], g["sh"], g["check"], g["bad"], g["EXP"], g["ENV"]
sp = importlib.util.spec_from_file_location("X5", ROOT / "scripts/make_expect_e5.py"); X5 = importlib.util.module_from_spec(sp); sp.loader.exec_module(X5)
X, E, END = X5.X, X5.X.EV3, "# end of command\n"
FIX_OLD = "    if not text:\n        return dict()\n"
FIX_NEW = "    if not text:\n        return dict()\n    if strict and '=' not in text:\n        raise ValueError('missing =')\n"
EDITED = re.compile(r"(?m)^EDITED ")


def edit(w, old, new):
    return sh(w, "mkdir -p .git/agent\ncat > .git/agent/old <<'OLD_TEXT'\n" + old + "OLD_TEXT\ncat > .git/agent/new <<'NEW_TEXT'\n" + new + "NEW_TEXT\n" + X.EDIT_STEP.replace("PATH", "pkg/parser.py") + END)


def write_file(w, body):  # what the harness's write_file does: create parents, write the content (the model may add '# end of content')
    (w / ".git/agent").mkdir(parents=True, exist_ok=True); (w / ".git/agent/expect.py").write_text(body + "# end of content\n")


def status(w):
    st = subprocess.run(["git", "status", "--short", "--untracked-files=all"], cwd=w, env=ENV, capture_output=True, text=True).stdout
    return "\n".join(l for l in st.splitlines() if "__pycache__" not in l).strip()


print("#### sbE5w")
w = repo(10)
rc, out, err = edit(w, FIX_OLD, FIX_NEW)
check("1 edit before any expectation -> held back", rc == 0 and E["refused"] in out and not EDITED.search(out), out + err)
rc, out, err = sh(w, X.RERUN + "\n" + END)
check("2 the re-run before the check command ever ran -> 'No such file' (the WHEN line's text)", "No such file or directory" in out + err and "check.sh" in out + err, out + err)
write_file(w, "import sys\nsys.path.insert(0, '.')\nfrom pkg.parser import parse\nassert parse('a=1')['a'] == '1'\n")
rc, out, err = sh(w, X.CHECK_CMD + END)
check("3 check command, expectation passes before any edit -> 'not the one in the issue'", rc == 0 and E["nothing"] in out, out + err)
write_file(w, "import sys\nsys.path.insert(0, '.')\ntry\n    pass\n")
rc, out, err = sh(w, X.RERUN + "\n" + END)
check("4 broken script via the re-run -> 'script broken'", rc == 0 and E["broken"] in out and E["shown"] not in out, out + err)
write_file(w, EXP)
rc, out, err = sh(w, X.RERUN + "\n" + END)
check("5 failing expectation -> 'shown' + the failure", rc == 0 and E["shown"] in out and "AssertionError: strict mode accepted" in out, out + err)
rc, out, err = edit(w, FIX_OLD, "    if not text:\n        raise ValueError('empty')\n")
check("6 a wrong edit (expectation exists) -> applied, 'still fails'", rc == 0 and EDITED.search(out) and E["still"] in out, out + err)
rc, out, err = edit(w, "    if not text:\n        raise ValueError('empty')\n", FIX_NEW)
check("7 the fixing edit -> 'passes with your edit'", rc == 0 and E["done"] in out, out + err)
check("8 only the source file changed", status(w) == "M pkg/parser.py", status(w))
w = repo(10)
write_file(w, EXP)
rc, out, err = sh(w, X.CHECK_CMD + END)
check("9 write_file then the check command as the first run -> 'shown'", rc == 0 and E["shown"] in out, out + err)
rc, out, err = edit(w, FIX_OLD, FIX_NEW)
check("10 expectation written first -> the first edit is applied, 'passes with your edit'", rc == 0 and EDITED.search(out) and E["refused"] not in out and E["done"] in out, out + err)
w = repo(400)
write_file(w, EXP)
rc, out, err = sh(w, X.CHECK_CMD + END)
check("11 late run, unedited -> the late line", rc == 0 and E["late"] in out, out + err)

print("#### sbE5f")
w = repo(10)
rc, out, err = edit(w, FIX_OLD, FIX_NEW)
check("12 edit before any expectation -> held back", rc == 0 and E["refused"] in out and not EDITED.search(out), out + err)
rc, out, err = sh(w, X.expect_cmd(EXP) + END)
check("13 heredoc expectation with the end line -> 'shown'", rc == 0 and E["shown"] in out, out + err)
rc, out, err = edit(w, FIX_OLD, FIX_NEW)
check("14 the same edit again -> applied, 'passes with your edit'", rc == 0 and EDITED.search(out) and E["done"] in out, out + err)
check("15 only the source file changed", status(w) == "M pkg/parser.py", status(w))
print("problems:", bad or "none")
