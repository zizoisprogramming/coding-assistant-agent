"""Tests for evidence_prec.py's PAST CHANGES section (r93 evidc_p). Run: python3 -I scripts/agent_evidence/test_evidence_prec.py"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "evidence_prec.py")


def commit(d, msg, files):
    for path, text in files.items():
        os.makedirs(os.path.dirname(os.path.join(d, path)) or d, exist_ok=True)
        open(os.path.join(d, path), "w").write(text)
    subprocess.run(["git", "add", "-A"], cwd=d, check=True)
    subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=t", "commit", "-qm", msg], cwd=d, check=True)


def repo():
    d = tempfile.mkdtemp(prefix="prec_")
    subprocess.run(["git", "init", "-q", d], check=True)
    core = "class Parser:\n    def header_value(self, raw):\n        return raw\n\n\ndef helper():\n    return 1\n"
    commit(d, "Initial", {"pkg/__init__.py": "", "pkg/core.py": core, "docs_src/ex.py": "x = 1\n"})
    commit(d, "Update release notes", {"README.md": "notes\n"})
    commit(d, "Fix header_value for empty headers (#12)", {
        "pkg/core.py": core.replace("        return raw\n", "        if not raw:\n            return ''\n        return raw\n"),
        "docs_src/ex.py": "x = 2\n", "tests/test_core.py": "def test_x():\n    pass\n"})
    commit(d, "Add helper option", {"pkg/core.py": open(os.path.join(d, "pkg/core.py")).read().replace("return 1", "return 2")})
    return d


def run(d, *names):
    r = subprocess.run([sys.executable, "-I", SCRIPT, *names], cwd=d, capture_output=True, text=True, timeout=60,
                       env={**os.environ, "PYTHONPATH": d})
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_precedent_names_the_function_library_first():
    d = repo()
    out = run(d, "header_value")
    sec = out.split("\n== ")[0]
    assert "PAST CHANGES LIKE THIS ONE" in sec, out
    assert "Fix header_value for empty headers (#12)" in sec, sec
    lines = sec.splitlines()
    i = next(k for k, l in enumerate(lines) if "Fix header_value" in l)
    assert lines[i + 1].strip().startswith("pkg/core.py: Parser.header_value (+2 -0)"), lines[i + 1]
    assert "tests/test_core.py" not in sec  # tests never listed
    assert sec.index("pkg/core.py") < sec.index("docs_src/ex.py")  # library source before docs examples
    assert "release notes" not in sec


def test_no_section_without_shared_words():
    d = repo()
    out = run(d, "zzqqxx_unrelated")
    assert "PAST CHANGES" not in out, out
    assert "== zzqqxx_unrelated" in out  # the per-name sections still run


def test_at_most_three_commits_and_fast():
    d = repo()
    for k in range(6):
        commit(d, f"Tweak header_value number {k}", {"pkg/core.py": open(os.path.join(d, "pkg/core.py")).read() + f"\n# {k}\n"})
    import time
    t = time.time()
    out = run(d, "header_value")
    sec = out.split("\n== ")[0]
    assert sec.count("past change ") == 3, sec
    assert time.time() - t < 10


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            try:
                fn(); print("ok  ", name)
            except Exception as e:  # noqa: BLE001
                fails += 1; print("FAIL", name, repr(e)[:700])
    sys.exit(1 if fails else 0)
