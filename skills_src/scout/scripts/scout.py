"""Scout: the locator's only way to read the repository, with a built-in reading budget.

Called through run_skill_script with named args, e.g. args={"mode": "find", "query": "convert_underscores"}.
Modes:
  find  --query TEXT                     git grep hits with surrounding code (counts as a reading call)
  show  --file PATH --start N --end M    numbered lines, at most 150 (counts as a reading call)
  plan  --text TEXT                      write the plan for the editor to /tmp/plan.md (free)
  history --query TEXT | --commit SHA    commits that added/removed TEXT, or one commit's change (counts)
  check [--test PATH] [--k EXPR]         git diff of the current changes + optional targeted pytest (free)
After LIMIT reading calls, find/show refuse and tell the locator to write the plan and call the editor.
"""
import argparse
import inspect
import os
import subprocess
import sys
import tempfile

LIMIT = 16
WARN_FROM = 13
TMP = tempfile.gettempdir()          # the task's /tmp (per-task directory in the subprocess sandbox)
COUNTER = os.path.join(TMP, "scout_reads")
PLAN = os.path.join(TMP, "plan.md")


def workspace():
    """The repository root. The skill wrapper chdirs into a temp dir, so look for the directory it started in."""
    for frame in inspect.stack():
        cwd = frame.frame.f_locals.get("_orig_cwd")
        if isinstance(cwd, str) and os.path.isdir(os.path.join(cwd, ".git")):
            return cwd
    for cand in (os.environ.get("PYTHONPATH", "").split(os.pathsep)[0], "/workspace"):
        if cand and os.path.isdir(os.path.join(cand, ".git")):
            return cand
    sys.exit("scout: repository not found")


def run(cmd, cwd, timeout=120):
    try:
        res = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, timeout=timeout)
        return (res.stdout + res.stderr).rstrip()
    except subprocess.TimeoutExpired:
        return f"(timed out after {timeout}s)"


def reading_budget():
    """Increment and return the number of reading calls, or refuse when the budget is spent."""
    used = int(open(COUNTER).read() or 0) if os.path.exists(COUNTER) else 0
    if used >= LIMIT:
        print(f"READING LIMIT REACHED ({LIMIT} reading calls used). Write your plan now with mode plan, then call the "
              "editor. You can still use mode check after the editor has answered.")
        sys.exit(0)
    used += 1
    with open(COUNTER, "w") as f:
        f.write(str(used))
    return used


def footer(used):
    left = LIMIT - used
    msg = f"[reading {used} of {LIMIT} used"
    if used >= WARN_FROM:
        msg += f"; {left} left: start writing the plan" if left else "; none left: write the plan now"
    return msg + "]"


def main():
    ap = argparse.ArgumentParser(prog="scout")
    ap.add_argument("--mode", required=True, choices=["find", "show", "history", "plan", "check"])
    ap.add_argument("--query")
    ap.add_argument("--file")
    ap.add_argument("--start", type=int)
    ap.add_argument("--end", type=int)
    ap.add_argument("--text")
    ap.add_argument("--commit")
    ap.add_argument("--test")
    ap.add_argument("--k")
    a = ap.parse_args()
    ws = workspace()

    if a.mode == "find":
        if not a.query:
            sys.exit('scout find needs args={"mode": "find", "query": "NAME or message"}')
        used = reading_budget()
        q = a.query.replace("'", "'\\''")
        out = run(f"git grep -n -I -A 20 -e '{q}' -- '*.py' '*.md' | head -80", ws)
        if not out:
            out = run(f"git grep -n -I -i -e '{q}' -- . | head -30", ws) or "(no match)"
        print(out)
        print(footer(used))
    elif a.mode == "show":
        if not (a.file and a.start):
            sys.exit('scout show needs args={"mode": "show", "file": "path.py", "start": 40, "end": 160}')
        used = reading_budget()
        start, end = max(a.start, 1), a.end or a.start + 120
        end = min(end, start + 149)
        path = os.path.join(ws, a.file)
        if not os.path.isfile(path):
            print(f"(no such file: {a.file})")
        else:
            lines = open(path, encoding="utf-8", errors="replace").read().split("\n")
            print("\n".join(f"{i:5}| {lines[i - 1]}" for i in range(start, min(end, len(lines)) + 1)))
        print(footer(used))
    elif a.mode == "history":
        if not (a.query or a.commit):
            sys.exit('scout history needs args={"mode": "history", "query": "NAME"} or {"mode": "history", "commit": "SHA"}')
        used = reading_budget()
        if a.commit:
            sha = a.commit.replace("'", "")
            print(run(f"git show --stat --format='%h %s' '{sha}' | head -20 && git show --format= '{sha}' | head -80", ws))
        else:
            q = a.query.replace("'", "'\\''")
            print(run(f"git log --oneline -S'{q}' | head -15", ws) or "(no commit adds or removes it)")
            print("recent commits:\n" + run("git log --oneline -8", ws))
        print(footer(used))
    elif a.mode == "plan":
        if not a.text:
            sys.exit('scout plan needs args={"mode": "plan", "text": "FILE: ...\\nCHANGE: ..."}')
        with open(PLAN, "w", encoding="utf-8") as f:
            f.write(a.text.strip() + "\n")
        print(f"PLAN SAVED to /tmp/plan.md ({len(a.text)} chars). Now call the editor.")
    else:  # check
        diff = run("git diff --stat && git diff | head -80", ws)
        print("CURRENT CHANGES:\n" + (diff or "(no changes)"))
        if a.test:
            k = f" -k '{a.k}'" if a.k else ""
            print("\nTEST:\n" + run(f"{sys.executable} -m pytest {a.test} -x -q -p no:cacheprovider{k} 2>&1 | tail -25", ws, 200))


if __name__ == "__main__":
    main()
