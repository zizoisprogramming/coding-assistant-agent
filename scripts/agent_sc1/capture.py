"""Runs sc1's real install.py / a.py on a throwaway toy repository made here (our own code: the Reader story) and returns their
exact outputs, so the prompt's worked examples show what the tools really print. Used by scripts/make_sc1.py."""
import os, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import parts as P  # noqa: E402

FILES = {
    "pkg/__init__.py": "",
    "pkg/parser.py": "def parse(text, strict=False):\n    if not text:\n        return dict()\n    if strict and '=' not in text:\n        raise ValueError('missing = in ' + repr(text))\n    key, _, value = text.partition('=')\n    return dict([(key, value)])\n",
    "pkg/reader.py": "from pkg.parser import parse\n\n\nclass Reader:\n    def __init__(self, strict=False):\n        self.strict = strict\n\n    def read(self, text):\n        return parse(text)\n",
    "tests/test_reader.py": "from pkg.reader import Reader\n\n\ndef test_read():\n    assert Reader().read('a=1')['a'] == '1'\n",
    "tests/test_parser.py": "from pkg.parser import parse\n\n\ndef test_strict():\n    assert parse('a=1', strict=True)['a'] == '1'\n",
}
ENV = dict(os.environ, GIT_CONFIG_COUNT="2", GIT_CONFIG_KEY_0="core.hooksPath", GIT_CONFIG_VALUE_0="/dev/null", GIT_CONFIG_KEY_1="core.fsmonitor",
           GIT_CONFIG_VALUE_1="false", GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
ENV.pop("PYTHONPATH", None)


def skill_dir(where):
    d = Path(where) / "skill_scripts"
    d.mkdir(parents=True)
    (d / "a.py").write_text(P.a_py()); (d / "where.py").write_text(P.where_py()); (d / "install.py").write_text(P.install_py())
    shutil.copy(P.SKA2 / "commands.txt", d / "commands.txt")
    return d


def repo(where):
    w = Path(where) / "repo"
    for k, v in FILES.items():
        (w / k).parent.mkdir(parents=True, exist_ok=True); (w / k).write_text(v)
    for c in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "init"]):
        subprocess.run(["git", *c], cwd=w, env=ENV, check=True)
    return w


def run(w, argv):
    return subprocess.run([sys.executable, "-I", *argv], cwd=w, env=ENV, capture_output=True, text=True, timeout=60).stdout


def capture(scratch=None):
    t = Path(tempfile.mkdtemp(dir=scratch))
    sd = skill_dir(t); w = repo(t)
    A = str(w / ".git/agent/a.py")
    out = {"install": run(w, [str(sd / "install.py"), "Reader", "strict"])}
    out["find"] = run(w, [A, "find", "parse("])
    out["show"] = run(w, [A, "show", "pkg/reader.py", "Reader.read"])
    out["reshow"] = run(w, [A, "show", "pkg/reader.py", "Reader.read"])
    looks = []
    for k in range(14):
        looks.append(run(w, [A, "outline", "pkg/parser.py" if k % 2 else "pkg/reader.py"]))
    out["no_edit"] = next(o for o in looks if P.NO_EDIT in o)
    out["stop"] = next(o for o in looks + [run(w, [A, "find", "strict"])] if P.STOP in o)
    (w / "scratch_repro.py").write_text("print(1)\n")
    out["scratch_still_banner"] = run(w, [A, "outline", "pkg/reader.py"])
    return out, w, sd


if __name__ == "__main__":
    o, w, sd = capture(sys.argv[1] if len(sys.argv) > 1 else None)
    for k, v in o.items():
        print(f"######## {k}\n{v}")


def edit_cmd(path, old, new):
    return ("mkdir -p .git/agent\ncat > .git/agent/old <<'OLD_TEXT'\n" + old + "OLD_TEXT\ncat > .git/agent/new <<'NEW_TEXT'\n" + new
            + "NEW_TEXT\n" + P.edit_step().replace("PATH", path))


REPRO = "python3 - <<'EOF'\nfrom pkg.reader import Reader\nprint(repr(Reader(strict=True).read('a')))\nEOF\n"
OLD = "    def read(self, text):\n        return parse(text)\n"
NEW = "    def read(self, text):\n        return parse(text, strict=self.strict)\n"
OLD_NUM = "     8|     def read(self, text):\n     9|         return parse(text)\n"


def sh(w, cmd):
    r = subprocess.run(["/bin/bash", "-c", cmd], cwd=w, env=ENV, capture_output=True, text=True, timeout=60)
    return r.stdout + r.stderr


def capture_all(scratch=None):
    out, w, sd = capture(scratch)
    subprocess.run(["git", "checkout", "-q", "--", "."], cwd=w, env=ENV)
    (w / "scratch_repro.py").unlink()
    out["repro_before"] = sh(w, REPRO)
    out["edit"] = sh(w, edit_cmd("pkg/reader.py", OLD, NEW))
    out["repro_after"] = sh(w, REPRO)
    subprocess.run(["git", "checkout", "-q", "--", "."], cwd=w, env=ENV)
    out["edit_numbers"] = sh(w, edit_cmd("pkg/reader.py", OLD_NUM, NEW))
    subprocess.run(["git", "checkout", "-q", "--", "."], cwd=w, env=ENV)
    out["edit_found0"] = sh(w, edit_cmd("pkg/reader.py", "    def read(self, text):\n        return parse(text.strip())\n", NEW))
    out["after_edit_banner"] = run(w, [str(w / ".git/agent/a.py"), "outline", "pkg/reader.py"])
    return out
