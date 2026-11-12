"""Read-only look-around for evpipe's locator stage (r92, user 2026-11-12 "build all": the fixed pipeline).

    run_skill_script skill look, file look.py, positional_args:
      ["find", "TEXT"]                 source lines (tests left out) that contain TEXT, with file:line
      ["tests", "TEXT"]                test lines that contain TEXT, with file:line
      ["def", "NAME"]                  where def / class NAME is defined, and its whole body (raw lines)
      ["show", "FILE", "START", "END"] raw lines START-END of FILE

Bounded by structure: after LIMIT calls every call is refused with a line that says to reply now (this model follows
tool-output refusals, not length rules: memory event-triggered-rules-only; r88's drafter with free tools ran 9-78
calls). Raw lines are printed without line numbers so the locator can copy them exactly into its LOCATION reply, which
the tool-less proposers read. Never writes inside the repository except the call counter in .git/agent."""
import ast
import inspect
import os
import re
import subprocess
import sys

LIMIT = 6
MAX_LINES = 90
FIND_LINES, TEST_LINES = 25, 15
LINE_MAX = 160
TEST_RE = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)conftest\.py$")


def workspace():
    """The repository root. The skill wrapper chdirs into a temp dir, so look for the directory it started in."""
    for frame in inspect.stack():
        cwd = frame.frame.f_locals.get("_orig_cwd")
        if isinstance(cwd, str) and os.path.isdir(os.path.join(cwd, ".git")):
            return cwd
    for cand in (os.environ.get("PYTHONPATH", "").split(os.pathsep)[0], "/workspace", os.getcwd()):
        if cand and os.path.isdir(os.path.join(cand, ".git")):
            return cand
    sys.exit("repository not found")


def git(ws, args):
    try:
        r = subprocess.run(["git", "-c", "core.quotepath=off"] + args, cwd=ws, capture_output=True, text=True, timeout=10,
                           stdin=subprocess.DEVNULL, errors="replace")
    except subprocess.TimeoutExpired:
        return []
    return r.stdout.splitlines() if r.returncode in (0, 1) else []


def cut(line):
    line = line.rstrip()
    return line if len(line) <= LINE_MAX else line[:LINE_MAX] + " ..."


def grep(ws, text, tests):
    hits = [h for h in git(ws, ["grep", "-n", "-I", "-F", "-e", text, "--", "*.py"]) if bool(TEST_RE.search(h.split(":", 1)[0])) == tests]
    n = TEST_LINES if tests else FIND_LINES
    out = [cut(h) for h in hits[:n]]
    if len(hits) > n:
        out.append(f"... {len(hits) - n} more lines")
    return out or [f"no {'test' if tests else 'source'} line contains {text!r}"]


def region(ws, path, a, b):
    full = os.path.join(ws, path)
    try:
        lines = open(full, encoding="utf-8", errors="replace").read().splitlines()
    except OSError as e:
        return [f"cannot read {path}: {e.strerror}"]
    a, b = max(1, a), min(len(lines), b)
    if b < a:
        return [f"{path} has {len(lines)} lines"]
    if b - a + 1 > MAX_LINES:
        b = a + MAX_LINES - 1
    return [f"== {path} lines {a}-{b} (of {len(lines)}), raw:"] + [l.rstrip("\n") for l in lines[a - 1:b]]


def define(ws, name):
    name = name.split(".")[-1].strip("()` ")
    hits = git(ws, ["grep", "-n", "-I", "-E", "-e", rf"^[[:space:]]*(async def|def|class) {re.escape(name)}([^[:alnum:]_]|$)", "--", "*.py"])  # POSIX ERE: no \s / \b
    hits = [h for h in hits if not TEST_RE.search(h.split(":", 1)[0])]
    if not hits:
        return [f"no def or class named {name!r} in the source"]
    out = []
    for h in hits[:2]:
        path, ln = h.split(":", 2)[:2]
        ln = int(ln)
        end = ln
        try:
            tree = ast.parse(open(os.path.join(ws, path), encoding="utf-8", errors="replace").read())
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == name and node.lineno <= ln <= (node.end_lineno or ln):
                    start = min([d.lineno for d in node.decorator_list] + [node.lineno])
                    if start <= ln:
                        end = node.end_lineno or ln
                        ln = start
                        break
        except (OSError, SyntaxError, ValueError):
            end = ln + 30
        out += region(ws, path, ln, end)
    if len(hits) > 2:
        out.append("also defined at: " + ", ".join(h.split(":", 2)[0] + ":" + h.split(":", 2)[1] for h in hits[2:6]))
    return out


def main(argv):
    ws = workspace()
    agent = os.path.join(ws, ".git", "agent")
    os.makedirs(agent, exist_ok=True)
    counter = os.path.join(agent, "look_count")
    try:
        used = int(open(counter).read().strip() or 0)
    except (OSError, ValueError):
        used = 0
    if used >= LIMIT:
        return ("LOOK LIMIT REACHED: no more looking. Reply now with your LOCATION block, built from the lines you have "
                "already seen.")
    args = [a for a in argv if a != "--"]
    if len(args) == 1 and " " in args[0]:
        args = args[0].split(None, 3) if args[0].split(None, 1)[0] == "show" else args[0].split(None, 1)
    verb = (args[0] if args else "").lower()
    with open(counter, "w") as f:
        f.write(str(used + 1))
    left = LIMIT - used - 1
    if verb in ("find", "tests") and len(args) >= 2:
        out = grep(ws, " ".join(args[1:]).strip("`'\""), verb == "tests")
    elif verb == "def" and len(args) >= 2:
        out = define(ws, args[1])
    elif verb == "show" and len(args) >= 4:
        try:
            out = region(ws, args[1].lstrip("./") if not args[1].startswith("/") else os.path.relpath(args[1], ws), int(args[2]), int(args[3]))
        except ValueError:
            out = ["show needs FILE START END, for example: show fastapi/routing.py 120 160"]
    else:
        out = ['usage: positional_args ["find", "TEXT"] | ["tests", "TEXT"] | ["def", "NAME"] | ["show", "FILE", "START", "END"]']
    out.append(f"[{left} look(s) left]" if left else "[that was the last look: reply now with your LOCATION block]")
    return "\n".join(out)


if __name__ == "__main__":
    print(main(sys.argv[1:]))
