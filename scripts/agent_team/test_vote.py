"""Tests for vote.py and evidence_team.py's team set-up (r90 evteam). Run: python3 -I scripts/agent_team/test_vote.py

Each test builds a small git repository the way the harness does (everything committed, tag _swegemma_baseline),
runs the evidence script's team_setup, lets 'Fixer A' edit the repository and 'Fixer B' its copy, then calls
vote.py done a / done b / final as the agents would."""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
VOTE = os.path.join(HERE, "vote.py")


CORE = "def clamp(x, lo, hi):\n    if x < lo:\n        return lo\n    return x\n"
GOOD = "def clamp(x, lo, hi):\n    if x < lo:\n        return lo\n    if x > hi:\n        return hi\n    return x\n"
BREAKS = "def clamp(x, lo, hi):\n    return hi\n"
TEST = ("from pkg.core import clamp\n\n\ndef test_low():\n    assert clamp(-1, 0, 5) == 0\n\n\n"
        "def test_mid():\n    assert clamp(3, 0, 5) == 3\n")


def setup():
    d = tempfile.mkdtemp(prefix="vote_ws_")
    scratch = tempfile.mkdtemp(prefix="vote_tmp_")
    os.makedirs(os.path.join(scratch, "b"))
    env = {"VOTE_SCRATCH_A": scratch, "VOTE_SCRATCH_B": os.path.join(scratch, "b"), "VOTE_BASE": os.path.join(scratch, "team", "wt_0")}
    os.makedirs(os.path.join(d, "pkg")); os.makedirs(os.path.join(d, "tests"))
    open(os.path.join(d, "pkg", "__init__.py"), "w").write("")
    open(os.path.join(d, "pkg", "core.py"), "w").write(CORE)
    open(os.path.join(d, "tests", "test_core.py"), "w").write(TEST)
    for c in (["git", "init", "-q"], ["git", "add", "-A"], ["git", "-c", "user.email=a@b", "-c", "user.name=t", "commit", "-qm", "base"],
              ["git", "tag", "-f", "_swegemma_baseline"]):
        subprocess.run(c, cwd=d, check=True, capture_output=True)
    os.environ.update(env)
    # the evidence script makes wt_0 under /tmp/team; point it at this test's scratch dir
    src = open(os.path.join(HERE, "evidence_team.py")).read().replace(
        'os.path.join(tmp, "team", "wt_0")', repr(env["VOTE_BASE"])).replace('os.makedirs(os.path.join(tmp, "b"), exist_ok=True)', "pass")
    ns = {"__name__": "ev_team_test"}
    exec(compile(src, "evidence_team.py", "exec"), ns)
    ns["VOTE_SOURCE"] = open(VOTE).read()
    ns["team_setup"].__globals__["VOTE_SOURCE"] = ns["VOTE_SOURCE"]
    ns["team_setup"](d)
    return d, scratch, env


def vote(d, env, *args):
    r = subprocess.run([sys.executable, os.path.join(d, ".git", "agent", "vote.py"), *args], cwd=d, capture_output=True,
                       text=True, timeout=120, env={**os.environ, **env})
    assert r.returncode == 0, r.stderr
    return r.stdout


def write(path, text):
    open(path, "w").write(text)


def ws_core(d):
    return open(os.path.join(d, "pkg", "core.py")).read()


def test_setup_made_copies():
    d, scratch, env = setup()
    team = json.load(open(os.path.join(d, ".git", "agent", "team.json")))
    assert team["wt_b"] and team["wt_0"], team
    assert open(os.path.join(d, ".git", "agent", "wt_b", "pkg", "core.py")).read() == CORE
    st = subprocess.run(["git", "status", "--short"], cwd=d, capture_output=True, text=True).stdout
    assert st.strip() == "", st  # nothing of the team shows in the repository's status (never part of the patch)


def test_b_wins_when_a_breaks_tests():
    d, scratch, env = setup()
    write(os.path.join(d, "pkg", "core.py"), BREAKS)
    write(os.path.join(d, ".git", "agent", "wt_b", "pkg", "core.py"), GOOD)
    out_a = vote(d, env, "done", "a")
    assert "still working" in out_a and "M pkg/core.py" in out_a, out_a
    out_b = vote(d, env, "done", "b")
    assert "WINNER: B" in out_b and "-> dropped (breaks tests)" in out_b, out_b
    assert ws_core(d) == GOOD
    diff = subprocess.run(["git", "diff", "_swegemma_baseline"], cwd=d, capture_output=True, text=True).stdout
    assert "if x > hi" in diff and "return hi\n" in diff, diff


def test_a_kept_on_a_tie():
    d, scratch, env = setup()
    write(os.path.join(d, "pkg", "core.py"), GOOD)
    write(os.path.join(d, ".git", "agent", "wt_b", "pkg", "core.py"), GOOD.replace("return hi", "return hi  # top"))
    vote(d, env, "done", "b")
    out = vote(d, env, "done", "a")
    assert "WINNER: A" in out, out
    assert ws_core(d) == GOOD


def test_b_used_when_a_has_no_patch():
    d, scratch, env = setup()
    write(os.path.join(d, ".git", "agent", "wt_b", "pkg", "core.py"), GOOD)
    vote(d, env, "done", "b")
    out = vote(d, env, "done", "a")
    assert "A: no source patch" in out and "WINNER: B" in out, out
    assert ws_core(d) == GOOD


def test_check_scripts_decide():
    d, scratch, env = setup()
    # both pass the existing tests; B's fix makes the fixer's own check pass, A's does not
    write(os.path.join(d, "pkg", "core.py"), CORE.replace("return x", "return x if x < 100 else 100"))
    write(os.path.join(d, ".git", "agent", "wt_b", "pkg", "core.py"), GOOD)
    write(os.path.join(scratch, "b", "check.py"), "from pkg.core import clamp\nassert clamp(9, 0, 5) == 5, clamp(9, 0, 5)\nprint('ok')\n")
    vote(d, env, "done", "a")
    out = vote(d, env, "done", "b")
    assert "WINNER: B" in out and "check.py:fixed" in out, out
    assert ws_core(d) == GOOD


def test_final_votes_when_a_fixer_never_said_done():
    d, scratch, env = setup()
    write(os.path.join(d, ".git", "agent", "wt_b", "pkg", "core.py"), GOOD)
    vote(d, env, "done", "b")  # A ran out of calls before its done call, with no patch
    out = vote(d, env, "final")
    assert "WINNER: B" in out and "submit_patch" in out, out
    out2 = vote(d, env, "final")
    assert "already made: WINNER B" in out2, out2  # no second vote when nothing changed
    assert ws_core(d) == GOOD


def test_new_file_from_b_and_a_cleaned():
    d, scratch, env = setup()
    write(os.path.join(d, "pkg", "extra_a.py"), "X = 1\n")  # A created a file, no other change -> A's patch = a new file
    write(os.path.join(d, "pkg", "core.py"), BREAKS)
    write(os.path.join(d, ".git", "agent", "wt_b", "pkg", "core.py"), GOOD)
    write(os.path.join(d, ".git", "agent", "wt_b", "pkg", "helper.py"), "Y = 2\n")
    vote(d, env, "done", "a")
    out = vote(d, env, "done", "b")
    assert "WINNER: B" in out, out
    assert not os.path.exists(os.path.join(d, "pkg", "extra_a.py")) and os.path.exists(os.path.join(d, "pkg", "helper.py"))
    subprocess.run(["git", "add", "-N", "."], cwd=d, check=True)
    diff = subprocess.run(["git", "diff", "--binary", "_swegemma_baseline"], cwd=d, capture_output=True, text=True).stdout
    assert "pkg/helper.py" in diff and "extra_a" not in diff and ".git/agent" not in diff, diff


def test_neither_has_a_patch():
    d, scratch, env = setup()
    vote(d, env, "done", "a")
    out = vote(d, env, "done", "b")
    assert "WINNER: none" in out, out


def test_index_untouched_and_skill_wrapper_ignored():
    d, scratch, env = setup()
    write(os.path.join(d, "pkg", "core.py"), GOOD)
    write(os.path.join(d, "pkg", "new_a.py"), "Z = 3\n")
    write(os.path.join(d, ".adk_exec_1234abcd.py"), "print('the harness skill wrapper')\n")  # present during the coordinator's call
    out = vote(d, env, "final")
    assert "WINNER: A" in out and ".adk_exec" not in out and "new_a.py" in out, out
    st = subprocess.run(["git", "status", "--porcelain"], cwd=d, capture_output=True, text=True).stdout
    assert "?? pkg/new_a.py" in st and "?? .adk_exec_1234abcd.py" in st, st  # still untracked: the real index never changed


def test_scripts_with_the_real_workspace_path():
    d, scratch, env = setup()
    # the sandbox writes its real path into heredoc scripts: a check that reads A's file by absolute path must read B's
    # file when it runs for B
    write(os.path.join(d, "pkg", "core.py"), CORE.replace("return x", "return x  # A"))
    write(os.path.join(d, ".git", "agent", "wt_b", "pkg", "core.py"), GOOD)
    write(os.path.join(scratch, "check.py"), f"import sys\nsrc = open({os.path.join(d, 'pkg', 'core.py')!r}).read()\n"
          "print('FIXED' if 'x > hi' in src else 'BUG')\nsys.exit(0 if 'x > hi' in src else 1)\n")
    vote(d, env, "done", "a")
    out = vote(d, env, "done", "b")
    assert "WINNER: B" in out and "check.py:fixed" in out, out


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            try:
                fn(); print("ok  ", name)
            except Exception as e:  # noqa: BLE001
                fails += 1; print("FAIL", name, repr(e)[:900])
    sys.exit(1 if fails else 0)
