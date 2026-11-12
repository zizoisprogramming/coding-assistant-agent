"""Code path of a script: which functions of this repository it ran, file by file, with their line ranges.
(r84 evtrace, user 2026-11-12 "all in": failed runs edit the wrong place in the right file; scripts/mine_bank/edit_place.py)

    python3 .git/agent/trace.py /tmp/check.py [args ...]
    python3 .git/agent/trace.py - <<'EOF'
    ...python code...
    EOF

The script runs as usual (its own output and errors are printed first); then a CODE PATH block lists the repository
functions it called (tests, the standard library, installed packages, module and class bodies, comprehensions and
everything that runs while modules are imported are left out): a 'files:' line with every file and its function count,
then per file (the modules the check script imports first, the rest in first-call order) its functions in call order,
each as 'first-last name (calls)', and, if it raised, the deepest repository line on the way. The idea comes from
SWE-Doctor (runtime evidence of where the failure goes, arXiv 2607.00990) and spectrum-based fault localization:
same-task data show solved runs edit the real-fix lines 89% vs failed 49%, and failed runs often never read them.
Installed into /workspace/.git/agent/ by the evidence script (inside .git: never part of the patch)."""
import io
import os
import re
import runpy
import sys
import threading
import traceback

MAX_FILES = 5
MAX_FUNCS = 12
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)conftest\.py$")


def repo_root():
    here = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(here) == "agent" and os.path.basename(os.path.dirname(here)) == ".git":
        return os.path.dirname(os.path.dirname(here))
    cur = os.getcwd()
    while cur != os.path.dirname(cur):
        if os.path.isdir(os.path.join(cur, ".git")):
            return cur
        cur = os.path.dirname(cur)
    return os.getcwd()


ROOT = os.path.realpath(repo_root())
SELF = os.path.realpath(__file__)
calls, order, last_line = {}, [], {}


_REL = {}


def relevant(fn):
    """repository-relative path of a code file worth listing, else None (cached: called on every function call)."""
    if fn in _REL:
        return _REL[fn]
    _REL[fn] = r = _relevant(fn)
    return r


def _relevant(fn):
    if not fn or fn.startswith("<"):
        return None
    p = os.path.realpath(fn)
    if not p.startswith(ROOT + os.sep) or p == SELF:
        return None
    rel = os.path.relpath(p, ROOT)
    if rel.startswith(".git" + os.sep) or TEST.search(rel) or "site-packages" in rel:
        return None
    return rel


def code_end(code):
    try:
        return max(l for _, _, l in code.co_lines() if l) or code.co_firstlineno
    except Exception:
        return code.co_firstlineno


CO_OPTIMIZED = 0x0001  # set for function code; module and class bodies lack it


def during_import(frame):
    """True when the call happens while a module is being imported (decorators, registrations, constants)."""
    f, depth = frame.f_back, 0
    while f is not None and depth < 200:
        if f.f_code.co_filename.startswith("<frozen importlib"):
            return True
        f, depth = f.f_back, depth + 1
    return False


def prof(frame, event, arg):
    if event != "call":
        return
    code = frame.f_code
    if not (code.co_flags & CO_OPTIMIZED) or code.co_name.startswith("<"):
        return  # module bodies, class bodies, comprehensions, lambdas
    rel = relevant(code.co_filename)
    if rel is None or during_import(frame):
        return
    key = (rel, code.co_firstlineno, code.co_name)
    if key not in calls:
        calls[key] = 0
        order.append(key)
        last_line[key] = code_end(code)
    calls[key] += 1


SOURCE = [""]  # the check script's text: the repository modules it imports are listed first


def script_files():
    """repository files of the modules the check script imports or names (pkg.mod -> pkg/mod.py or pkg/mod/__init__.py)."""
    mods = []
    for a, b in re.findall(r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", SOURCE[0], re.M):
        if (a or b) not in mods:
            mods.append(a or b)  # source order
    out = []
    for m in mods:
        parts = m.split(".")
        for k in range(len(parts), 0, -1):
            base = os.path.join(*parts[:k])
            for cand in (base + ".py", os.path.join(base, "__init__.py")):
                if os.path.isfile(os.path.join(ROOT, cand)) and cand not in out:
                    out.append(cand)
            if any(o.startswith(base) for o in out):
                break
    return out


def report(exc):
    out = ["", "== CODE PATH: functions of this repository the script ran (file: first-last name, calls)"]
    files = []
    for rel, _, _ in order:
        if rel not in files:
            files.append(rel)
    first = [f for f in script_files() if f in files]  # the modules the script imports first, then first-call order
    files = first + [f for f in files if f not in first]
    if files:
        counts = {f: sum(1 for k in order if k[0] == f) for f in files}
        out.append("files: " + ", ".join(f"{f} ({counts[f]})" for f in files[:10]) + (f", ... {len(files) - 10} more" if len(files) > 10 else ""))
    if not files:
        out.append("  (none: the script never called code from this repository)")
    for rel in files[:MAX_FILES]:
        keys = [k for k in order if k[0] == rel]
        out.append(f"{rel}:")
        for k in keys[:MAX_FUNCS]:
            out.append(f"  {k[1]}-{last_line[k]} {k[2]} ({calls[k]})")
        if len(keys) > MAX_FUNCS:
            out.append(f"  ... {len(keys) - MAX_FUNCS} more")
    if len(files) > MAX_FILES:
        out.append(f"... {len(files) - MAX_FILES} more files: " + ", ".join(files[MAX_FILES:MAX_FILES + 6]))
    if exc is not None:
        tb = [f for f in traceback.extract_tb(exc.__traceback__) if relevant(f.filename)]
        if tb:
            f = tb[-1]
            out.append(f"raised {type(exc).__name__} at {relevant(f.filename)}:{f.lineno} in {f.name}: {(f.line or '').strip()[:120]}")
    sys.stdout.flush()
    sys.stderr.flush()
    print("\n".join(out), flush=True)


def main():
    args = sys.argv[1:]
    if not args:
        print("usage: python3 .git/agent/trace.py /tmp/check.py [args]   or   python3 .git/agent/trace.py - <<'EOF' ... EOF")
        return 2
    target = args[0]
    if target == "-":
        source, name = sys.stdin.read(), "<stdin>"
        SOURCE[0] = source
    else:
        try:
            source, name = open(target, errors="replace").read(), target
            SOURCE[0] = source
        except OSError as e:
            print(f"cannot read {target}: {e}")
            return 2
    sys.argv = [name] + args[1:]
    sys.path.insert(0, ROOT)
    if target != "-":
        sys.path.insert(0, os.path.dirname(os.path.abspath(target)))
    os.chdir(ROOT) if os.getcwd() != ROOT and not os.path.isdir(os.path.join(os.getcwd(), ".git")) else None
    exc, code = None, 0
    threading.setprofile(prof)
    sys.setprofile(prof)
    try:
        g = {"__name__": "__main__", "__file__": name, "__builtins__": __builtins__}
        exec(compile(source, name, "exec"), g)
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    except BaseException as e:
        exc, code = e, 1
    finally:
        sys.setprofile(None)
        threading.setprofile(None)
    if exc is not None:
        traceback.print_exception(type(exc), exc, exc.__traceback__)
    report(exc)
    return code


if __name__ == "__main__":
    sys.exit(main())
