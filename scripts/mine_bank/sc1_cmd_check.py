"""sc1 command checks on a toy repository made here with our own code (scripts/agent_sc1/capture.py), using the real install.py / a.py /
edit step. Run: python3 -I scripts/mine_bank/sc1_cmd_check.py SCRATCH_DIR"""
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/agent_sc1"))
import capture as C  # noqa: E402
import parts as P  # noqa: E402
bad = []
def check(name, ok, info=""):
    print(f"  {'ok ' if ok else 'BAD'} {name}" + ("" if ok else " | " + info[:500]))
    if not ok: bad.append(name)
o, w, sd = C.capture(sys.argv[1])
A = str(w / ".git/agent/a.py")
check("1 install with names: READY + where lines", o["install"].startswith("READY") and "pkg/reader.py:4:class Reader:" in o["install"], o["install"])
check("2 show prints numbered lines + MEMORY", "MEMORY" in o["show"] and "     9|         return parse(text)" in o["show"], o["show"])
check("3 repeat -> ALREADY SHOWN", "ALREADY SHOWN" in o["reshow"], o["reshow"])
check("4 NO EDIT YET after 10 looks, STOP READING later, no clock numbers", P.NO_EDIT in o["no_edit"] and P.STOP in o["stop"] and "minutes" not in o["stop"], o["stop"])
check("5 a scratch file does not silence the banner", P.STOP in o["scratch_still_banner"], o["scratch_still_banner"])
(w / "scratch_repro.py").unlink()
out = C.sh(w, C.edit_cmd("pkg/reader.py", C.OLD_NUM, C.NEW))
check("6 old text with the number column -> stripped, applied", P.NUMBERS in out and "EDITED pkg/reader.py" in out, out)
after = C.run(w, [A, "outline", "pkg/reader.py"])
check("7 after an applied edit the banner is gone", "NO EDIT YET" not in after and "STOP READING" not in after, after)
subprocess.run(["git", "checkout", "-q", "--", "."], cwd=w, env=C.ENV)
B = chr(92)
(w / "pkg/ansi.py").write_text("RE = r'" + B + "x1b'\n"); subprocess.run(["git", "add", "-A"], cwd=w, env=C.ENV); subprocess.run(["git", "commit", "-qm", "a"], cwd=w, env=C.ENV)
out = C.sh(w, C.edit_cmd("pkg/ansi.py", "RE = r'" + B + B + "x1b'\n", "RE = r'" + B + B + "x1b[0-9]'\n"))
check("8 doubled backslashes -> halved, applied with single ones", "double backslashes" in out and (w / "pkg/ansi.py").read_text() == "RE = r'" + B + "x1b[0-9]'\n", out)
out = C.sh(w, C.edit_cmd("pkg/reader.py", "    nothing like this\n", "x\n"))
check("9 wrong text -> found 0, nothing changed", "old text found 0 times" in out and "EDITED" not in out, out)
w2 = C.repo(Path(sys.argv[1]) / ("r2_" + w.parent.name)) if False else None
r = subprocess.run([sys.executable, "-I", str(sd / "install.py")], cwd=w, env=C.ENV, capture_output=True, text=True, timeout=60).stdout
check("10 install without names -> READY only", r.startswith("READY") and "WHERE" not in r, r)
st = subprocess.run(["git", "status", "--short", "--untracked-files=all"], cwd=w, env=C.ENV, capture_output=True, text=True).stdout
check("11 the tool's files stay out of the patch (.git/agent)", ".git" not in st, st)
print("problems:", bad or "none")
