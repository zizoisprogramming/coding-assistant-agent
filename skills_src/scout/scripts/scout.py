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
import ast
import inspect
import json
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


MODES = ("find", "show", "history", "plan", "check")
ALIASES = {"path": "file", "filename": "file", "file_path": "file", "pattern": "query", "name": "query",
           "q": "query", "search": "query", "line": "start", "start_line": "start", "from": "start",
           "end_line": "end", "to": "end", "sha": "commit", "test_file": "test", "content": "text", "plan": "text"}


def literal(text):
    """A dict or list written as JSON or as a Python repr (ADK passes a nested dict as str(dict)), else None."""
    text = text.strip()
    if not text[:1] in "{[":
        return None
    for load in (json.loads, ast.literal_eval):
        try:
            return load(text)
        except (ValueError, SyntaxError):
            pass
    return None


def as_int(value):
    try:
        return int(float(str(value).strip()))
    except ValueError:
        return None


def parse(argv):
    """Read every argument shape the model produces: {"mode": ...} (--mode X), a nested {"args": {...}}, a list of
    ["--mode", "show", ...] or ["--mode=show"], positional ["show", "pkg/a.py", "40", "160"], "file:line" and "40-160".
    Missing or zero line numbers get defaults instead of an error."""
    opts, pos, tokens = {}, [], list(argv)
    while tokens:
        tok = tokens.pop(0)
        if tok == "--":
            continue
        val = literal(tok)
        if isinstance(val, dict):
            opts.update({str(k).lstrip("-"): v for k, v in val.items()})
        elif isinstance(val, list):
            tokens = [str(v) for v in val] + tokens
        elif tok.startswith("--") or (tok.startswith("-") and len(tok) > 1 and not tok[1].isdigit()):
            key, eq, value = tok.lstrip("-").partition("=")
            if not eq:
                value = tokens.pop(0) if tokens and not tokens[0].startswith("--") else ""
            inner = literal(value) if key == "args" else None
            if isinstance(inner, dict):
                opts.update({str(k).lstrip("-"): v for k, v in inner.items()})
            elif isinstance(inner, list):
                tokens = [str(v) for v in inner] + tokens
            else:
                opts[key] = value
        else:
            pos.append(tok)
    opts = {ALIASES.get(k, k): v for k, v in opts.items()}
    if "args" in opts and isinstance(opts["args"], dict):
        opts.update(opts.pop("args"))
    mode = str(opts.get("mode", "")).strip().lower()
    if mode not in MODES and pos and pos[0].lower() in MODES:
        mode = pos.pop(0).lower()
    if mode not in MODES:  # infer the mode from what was given
        mode = "show" if opts.get("file") else "plan" if opts.get("text") else "history" if opts.get("commit") else \
            "find" if opts.get("query") else "check" if opts.get("test") or opts.get("k") else ""
    a = argparse.Namespace(mode=mode, **{k: opts.get(k) for k in ("query", "file", "start", "end", "text",
                                                                    "commit", "test", "k")})
    if mode == "show":
        if not a.file and pos:
            a.file = pos.pop(0)
        if pos and a.start is None:
            a.start = pos.pop(0)
        if pos and a.end is None:
            a.end = pos.pop(0)
        if a.file and ":" in str(a.file):  # pkg/a.py:120 or pkg/a.py:100-160
            a.file, _, where = str(a.file).partition(":")
            a.start = a.start if a.start is not None else where
        if a.start is not None and "-" in str(a.start).strip("-") and a.end is None:
            a.start, _, a.end = str(a.start).partition("-")
        a.start, a.end = as_int(a.start) if a.start is not None else None, as_int(a.end) if a.end is not None else None
        if a.file:
            a.file = str(a.file).strip().removeprefix("/workspace/").removeprefix("./")
    elif mode in ("find", "history"):
        if not a.query and not a.commit and pos:
            a.query = " ".join(pos)
        if mode == "history" and a.query and not a.commit and all(c in "0123456789abcdef" for c in a.query) \
                and 7 <= len(a.query) <= 40:
            a.commit, a.query = a.query, None
    elif mode == "plan":
        if not a.text and pos:
            a.text = " ".join(pos)
    elif mode == "check":
        if not a.test and pos:
            a.test = pos.pop(0)
    return a


def main():
    a = parse(sys.argv[1:])
    if not a.mode:
        sys.exit('scout needs a mode: args={"mode": "find", "query": "NAME"} or {"mode": "show", "file": "pkg/a.py", '
                 '"start": 1, "end": 150}; also history, plan, check')
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
        if not a.file:
            sys.exit('scout show needs args={"mode": "show", "file": "path.py", "start": 40, "end": 160}')
        used = reading_budget()
        start = max(a.start or 1, 1)
        end = a.end if a.end and a.end >= start else start + 149
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
