"""Copy a.py into <repository>/.git/agent/ (git never puts .git in the patch), write the commands this agent uses,
reset the memory. Run once per task through run_skill_script."""
import inspect
import os
import shutil
import sys


def workspace():
    """The repository root. The skill wrapper chdirs into a temp dir, so look for the directory it started in."""
    for frame in inspect.stack():
        cwd = frame.frame.f_locals.get("_orig_cwd")
        if isinstance(cwd, str) and os.path.isdir(os.path.join(cwd, ".git")):
            return cwd
    for cand in (os.environ.get("PYTHONPATH", "").split(os.pathsep)[0], "/workspace", os.getcwd()):
        if cand and os.path.isdir(os.path.join(cand, ".git")):
            return cand
    sys.exit("agent tool: repository not found")


here = os.path.dirname(os.path.abspath(__file__))
target = os.path.join(workspace(), ".git", "agent")
os.makedirs(target, exist_ok=True)
shutil.copyfile(os.path.join(here, "a.py"), os.path.join(target, "a.py"))
shutil.copyfile(os.path.join(here, "commands.txt"), os.path.join(target, "commands.txt"))
for stale in ("state.json", "state.json.tmp", "repro.py"):
    if os.path.exists(os.path.join(target, stale)):
        os.remove(os.path.join(target, stale))
cmds = open(os.path.join(here, "commands.txt")).read().split()
usage = {
    "find": 'find "exact text" [PATH]      where it appears',
    "outline": "outline FILE                  classes and functions with line numbers",
    "show": "show FILE NAME | FILE START END   a whole function, or numbered lines",
    "note": 'note "one line"               keep a finding in your memory',
    "pin": "pin FILE START END            keep these lines visible in every output",
    "impact": "impact                        after an edit: other places using what you changed",
    "check": "check                         after an edit: .git/agent/repro.py + nearest tests + git status",
}
print("INSTALLED. Use it with run_command: python3 .git/agent/a.py COMMAND ...\n" +
      "\n".join("  " + usage[c] for c in cmds if c in usage) +
      "\nEvery output starts with your MEMORY (what you read, notes, pinned lines).")
