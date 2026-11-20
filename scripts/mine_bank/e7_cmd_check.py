"""sbE7 command checks in throwaway git repos made here with our own code (expect.py written as write_file would; commands run WITH
their '# end of command' line). Run: python3 -I scripts/mine_bank/e7_cmd_check.py SCRATCH_DIR"""
import re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
src = (ROOT / "scripts/mine_bank/e6_cmd_check.py").read_text()
src = src[:src.index('print("#### sbE6 solver commands")')]
g = {"__name__": "e7", "__file__": str(ROOT / "scripts/mine_bank/e6_cmd_check.py")}
exec(compile(src, "e6_helpers", "exec"), g)
repo, sh, check, bad, EXP, X6, E, END, edit, writer, status, ED, FIX_OLD, FIX_NEW = (g[k] for k in (
    "repo", "sh", "check", "bad", "EXP", "X6", "E", "END", "edit", "writer", "status", "ED", "FIX_OLD", "FIX_NEW"))
print("#### sbE7")
w = repo(10)
rc, out, err = edit(w, FIX_OLD, FIX_NEW)
check("1 edit before any expectation -> held back once, file unchanged", rc == 0 and E["refused"] in out and not ED.search(out), out + err)
rc, out, err = sh(w, X6.XA.RERUN + "\n" + END)
check("2 re-run before the check command ever ran -> 'No such file'", "check.sh: No such file" in out + err, out + err)
writer(w, "import sys\nsys.path.insert(0, '.')\nfrom pkg.parser import parse\nassert parse('a=1')['a'] == '1'\n")
rc, out, err = sh(w, X6.CHECK_CMD + END)
check("3 write_file + check command, passes unedited -> 'not the one in the issue'", rc == 0 and E["nothing"] in out, out + err)
writer(w, EXP)
rc, out, err = sh(w, X6.XA.RERUN + "\n" + END)
check("4 rewrite with write_file + re-run -> 'shown'", rc == 0 and E["shown"] in out, out + err)
rc, out, err = edit(w, FIX_OLD, FIX_NEW)
check("5 the held edit sent again -> applied, 'passes with your edit'", rc == 0 and ED.search(out) and E["done"] in out, out + err)
check("6 only the source file changed", status(w) == "M pkg/parser.py", status(w))
w = repo(10)
rc, out, err = sh(w, X6.CHECK_CMD + END)
check("7 check command with no expect.py -> 'no expectation file'", rc == 0 and E["missing"] in out and E["shown"] not in out, out + err)
print("problems:", bad or "none")
