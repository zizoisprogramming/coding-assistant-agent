"""r129 checks in throwaway git repos made here with our own code. Run: python3 -I scripts/mine_bank/e4_cmd_check.py SCRATCH_DIR
1. e3_cmd_check's 15 checks with the edit step replaced by the r129 one (sbE3's step + the backslash fallback): the hold-back, every
   event, the late line, only the source in the patch still hold;
2. sbE4A's search script (submissions/sbE4A/skills/evidence/scripts/evidence.py): definitions, source uses, test lines, the one-call
   rule, the no-names message, speed."""
import os, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCR = Path(sys.argv[1]); SCR.mkdir(parents=True, exist_ok=True)
src = (ROOT / "scripts/mine_bank/e3_cmd_check.py").read_text()
a = 'E = X.EV3\n'
assert src.count(a) == 1
src = src.replace(a, a + "import importlib.util as _u\n_s = _u.spec_from_file_location('F', ROOT / 'scripts/edit_fallback.py'); F = _u.module_from_spec(_s); _s.loader.exec_module(F)\n"
                  "X.EDIT_STEP3 = F.halve(X.EDIT_STEP3)\nprint('(edit step = sbE3 + backslash fallback)')\n")
sys.argv = [sys.argv[0], str(SCR / "e3part")]
g = {"__name__": "__main__", "__file__": str(ROOT / "scripts/mine_bank/e3_cmd_check.py")}
exec(compile(src, "e3_cmd_check_r129", "exec"), g)
bad = g["bad"]

print("#### sbE4A search script")
ENV = dict(os.environ, GIT_CONFIG_COUNT="2", GIT_CONFIG_KEY_0="core.hooksPath", GIT_CONFIG_VALUE_0="/dev/null", GIT_CONFIG_KEY_1="core.fsmonitor",
           GIT_CONFIG_VALUE_1="false", GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
ENV.pop("PYTHONPATH", None)
w = Path(tempfile.mkdtemp(dir=SCR))
files = {"pkg/__init__.py": "", "pkg/parser.py": "def parse(text, strict=False):\n    return dict()\n",
         "pkg/reader.py": "from pkg.parser import parse\n\n\nclass Reader:\n    def __init__(self, strict=False):\n        self.strict = strict\n\n    def read(self, text):\n        return parse(text)\n",
         "tests/test_reader.py": "from pkg.reader import Reader\n\n\ndef test_read():\n    assert Reader().read('a=1')['a'] == '1'\n"}
for k, v in files.items():
    (w / k).parent.mkdir(parents=True, exist_ok=True); (w / k).write_text(v)
for c in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "i"]):
    subprocess.run(["git", *c], cwd=w, env=ENV, check=True)
S = ROOT / "submissions/sbE4A/skills/evidence/scripts/evidence.py"
def run(*args):
    t = time.time()
    r = subprocess.run([sys.executable, "-I", str(S), *args], cwd=w, env=ENV, capture_output=True, text=True, timeout=60)
    return r.stdout + r.stderr, time.time() - t
def check(name, ok, info=""):
    print(f"  {'ok ' if ok else 'BAD'} {name}" + ("" if ok else " | " + info[:900]))
    if not ok: bad.append(name)
out, dt = run("Reader", "strict")
check("1 header + Reader defined at pkg/reader.py:4", "WHERE THE ISSUE'S NAMES ARE, for Reader, strict" in out and "pkg/reader.py:4:class Reader:" in out, out)
check("2 Reader test lines", "tests that use it: 2 lines" in out and "tests/test_reader.py:5:    assert Reader().read('a=1')['a'] == '1'" in out, out)
check("3 strict (no def) -> used in source", "used in source:" in out and "pkg/parser.py:1:def parse(text, strict=False):" in out, out)
check("4 no history / changelog sections", "commit" not in out.lower() and "changelog" not in out, out)
check("5 one-call rule text + the reply instruction", "a second call is refused" in out and "at most 12 lines" in out, out)
check("6 fast (< 3 s)", dt < 3, f"{dt:.1f} s")
out2, _ = run("parse")
check("7 a second call is refused and shows the first result", out2.startswith("ALREADY DONE") and "pkg/reader.py:4:class Reader:" in out2, out2)
w2 = w
(w / ".git/agent/evidence_done").unlink()
out3, _ = run()
check("8 no names -> the NO NAMES message", out3.startswith("NO NAMES"), out3)
st = subprocess.run(["git", "status", "--short", "--untracked-files=all"], cwd=w, env=ENV, capture_output=True, text=True).stdout
check("9 the repository is left unchanged", st.strip() == "", st)
print("problems:", bad or "none")
