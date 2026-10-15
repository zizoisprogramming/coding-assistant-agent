"""Copy read.py into <repository>/.git/agent/ (git never puts .git in the patch) and reset its read counter."""
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
    sys.exit("reader: repository not found")


here = os.path.dirname(os.path.abspath(__file__))
target_dir = os.path.join(workspace(), ".git", "agent")
os.makedirs(target_dir, exist_ok=True)
shutil.copyfile(os.path.join(here, "read.py"), os.path.join(target_dir, "read.py"))
counter = os.path.join(target_dir, "reads")
if os.path.exists(counter):
    os.remove(counter)
print("INSTALLED .git/agent/read.py. Read the code with run_command:\n"
      '  python3 .git/agent/read.py find "exact name or message"\n'
      "  python3 .git/agent/read.py show path/to/file.py 40 160\n"
      "  python3 .git/agent/read.py history NAME\n"
      "16 reads in total; every result shows the count.")
