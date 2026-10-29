"""Team setup, run once per fixer as its first call (run_skill_script, skill team, scripts/setup_<letter>.py).

Fixer A works in the repository itself; it also copies judge.py into <repo>/.git/agent/ (git never puts .git in the
patch), starts the clock and makes wt_0, a clean copy the judge compares against. Fixers B and C each get their own
copy, <repo>/.git/agent/wt_b and wt_c (git worktrees of the baseline commit). make_skill_arms.py writes setup_a.py,
setup_b.py and setup_c.py from this file with LETTER set."""
import inspect
import json
import os
import random
import shutil
import subprocess
import sys
import time

LETTER = "a"
SECOND = False  # sa2 lead: also make wt_b, the copy its second fixer (an agent_tool) works in


def workspace():
    """The repository root. The skill wrapper chdirs into a temp dir, so look for the directory it started in."""
    for frame in inspect.stack():
        cwd = frame.frame.f_locals.get("_orig_cwd")
        if isinstance(cwd, str) and os.path.isdir(os.path.join(cwd, ".git")):
            return cwd
    for cand in (os.environ.get("PYTHONPATH", "").split(os.pathsep)[0], "/workspace", os.getcwd()):
        if cand and os.path.isdir(os.path.join(cand, ".git")):
            return cand
    sys.exit("team setup: repository not found")


def worktree(ws, name):
    """A clean copy of the baseline commit at .git/agent/<name>; retried: three fixers start at the same moment."""
    path = os.path.join(ws, ".git", "agent", name)
    if os.path.isdir(os.path.join(path, ".git")) or os.path.isfile(os.path.join(path, ".git")):
        return path, ""
    ref = "_swegemma_baseline" if subprocess.run(["git", "rev-parse", "-q", "--verify", "_swegemma_baseline"], cwd=ws,
                                                 capture_output=True).returncode == 0 else "HEAD"
    err = ""
    for _ in range(6):
        r = subprocess.run(["git", "worktree", "add", "--detach", "-f", path, ref], cwd=ws, capture_output=True, text=True)
        if r.returncode == 0:
            return path, ""
        err = (r.stderr or r.stdout)[-300:]
        shutil.rmtree(path, ignore_errors=True)
        subprocess.run(["git", "worktree", "prune"], cwd=ws, capture_output=True)
        time.sleep(0.5 + random.random() * 1.5)
    return None, err


ws = workspace()
agent = os.path.join(ws, ".git", "agent")
os.makedirs(agent, exist_ok=True)
here = os.path.dirname(os.path.abspath(__file__))
shutil.copyfile(os.path.join(here, "judge.py"), os.path.join(agent, "judge.py"))
if LETTER == "a":
    for stale in os.listdir(agent):
        if stale.startswith(("done_", "repro_")) or stale == "team.json":
            os.remove(os.path.join(agent, stale))
    with open(os.path.join(agent, "team.json"), "w") as f:
        json.dump({"t0": time.time()}, f)
    path, err = worktree(ws, "wt_0")
    if SECOND:
        worktree(ws, "wt_b")
    print("READY. You are Fixer A: you work in the repository itself (/workspace), as usual."
          + ("" if path else f" (the clean copy for the judge failed: {err})"))
else:
    path, err = worktree(ws, f"wt_{LETTER}")
    if not path:
        print(f"SETUP FAILED: {err}\nYour copy could not be made. Reply with one sentence and no tool call: your team "
              f"continues without you.")
        sys.exit(0)
    rel = f".git/agent/wt_{LETTER}"
    print(f"READY. You are Fixer {LETTER.upper()}. YOUR REPOSITORY is the folder {rel}: an exact copy, separate from your "
          f"teammates.\n  every command: cd {rel} && ...        (tests: cd {rel} && PYTHONPATH=. timeout 150 python -m pytest ...)\n"
          f"  every file path for read_file / edit_file / write_file starts with {rel}/   e.g. {rel}/pkg/module.py\n"
          f"Never touch files outside {rel} except your repro script .git/agent/repro_{LETTER}.py.")
