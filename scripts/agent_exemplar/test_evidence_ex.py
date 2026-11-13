"""Tests for the r95 evidence script with a solved example (evex_f / evex_m). Run: python3 -I scripts/agent_exemplar/test_evidence_ex.py"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
spec = importlib.util.spec_from_file_location("mk", os.path.join(ROOT, "scripts/make_r95_arms.py"))
mk = importlib.util.module_from_spec(spec); spec.loader.exec_module(mk)
LIB = json.load(open(os.path.join(HERE, "examples.json")))


def repo():
    d = tempfile.mkdtemp(prefix="ex_")
    subprocess.run(["git", "init", "-q", d], check=True)
    os.makedirs(os.path.join(d, "pkg"))
    open(os.path.join(d, "pkg/core.py"), "w").write("def header_value(raw):\n    return raw\n")
    subprocess.run(["git", "add", "-A"], cwd=d, check=True)
    subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=t", "commit", "-qm", "init"], cwd=d, check=True)
    return d


def run(mode, examples, *names, d=None):
    d = d or repo()
    script = os.path.join(tempfile.mkdtemp(prefix="exs_"), "evidence.py")
    open(script, "w").write(mk.render_script(mode, examples))
    r = subprocess.run([sys.executable, "-I", script, *names], cwd=d, capture_output=True, text=True, timeout=60,
                       env={**os.environ, "PYTHONPATH": d})
    assert r.returncode == 0, r.stderr
    return r.stdout


def fixed():
    return [e for e in LIB if e["repo"] == mk.FIXED_REPO]


def test_fixed_always_monkeytype_after_the_evidence_before_the_reply_line():
    out = run("fixed", fixed(), "header_value")
    assert out.index("== header_value") < out.index("A SOLVED EXAMPLE FROM ANOTHER REPOSITORY (Instagram/MonkeyType)")
    assert out.index("A SOLVED EXAMPLE") < out.index("This was the only search")
    assert "(example fixed;" in out and "leave it out of your reply" in out


def test_matched_picks_a_run_sharing_a_word():
    out = run("matched", LIB, "authority")
    assert "(lipoja/URLExtract)" in out and "matched on authority" in out, out[-600:]
    out = run("matched", LIB, "convert_caption")
    assert "(matthewwithanm/python-markdownify)" in out, out[-600:]


def test_matched_falls_back_to_fixed_without_shared_words():
    out = run("matched", LIB, "zzqqxx")
    assert "(Instagram/MonkeyType)" in out and "fixed (no shared word)" in out


def test_second_call_shows_the_same_result_with_the_example():
    d = repo()
    first = run("matched", LIB, "authority", d=d)
    again = run("matched", LIB, "authority", d=d)
    assert again.startswith("ALREADY DONE") and "(lipoja/URLExtract)" in again
    assert first.count("A SOLVED EXAMPLE") == 1


def test_library_has_no_competition_repo_and_no_reasoning():
    tasks = os.path.join(ROOT, "data/tasks.jsonl")
    comp = {json.loads(l)["repo"].split("/")[-1].lower() for l in open(tasks)} if os.path.exists(tasks) else set()
    for e in LIB:
        assert e["repo"].split("/")[-1].lower() not in comp | {"fastapi", "rich", "requests", "httpx"}, e["repo"]
        assert len(e["text"]) <= 3000
        assert "reasoning" not in e["text"].lower()


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            try:
                fn(); print("ok  ", name)
            except Exception as e:  # noqa: BLE001
                fails += 1; print("FAIL", name, repr(e)[:700])
    sys.exit(1 if fails else 0)
