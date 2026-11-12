"""Code path of a script with runtime values: which functions of this repository it ran, file by file, with their
line ranges, the lines that ran, and the values of the first call. (r90 evval, user 2026-11-12 "i want to try
everything": lead 1 of docs/RESEARCH_PROBLEMS_2026-11-12.md, SWE-Doctor-style runtime evidence; v2 = trace.py.)

    python3 .git/agent/trace.py /tmp/check.py [args ...]
    python3 .git/agent/trace.py - <<'EOF'
    ...python code...
    EOF

The script runs as usual (its own output and errors are printed first); then a CODE PATH block lists the repository
functions it called (tests, the standard library, installed packages, module and class bodies, comprehensions and
everything that runs while modules are imported are left out): a 'files:' line with every file and its function count,
then per file (the modules the check script imports first, the rest in first-call order) its functions in call order,
each as 'first-last name (calls)' followed by v3's runtime evidence:
  ran L-L,L          the lines of the function that ran (all calls together): which branch was taken
  args -> value      the arguments of the first call and what it returned (or 'raised X'), short reprs
and, if the script raised, the deepest repository line on the way with that frame's local variables.
SWE-Doctor (arXiv 2607.00990) gets its gain from runtime values and the executed branch along the failure path
(removing the diagnosis stage: -8 points); our v2 already listed the real fix's function 6/6 (r85) without moving
solves, so v3 adds what went wrong there, not only where the check went.
Installed into /workspace/.git/agent/ by the evidence script (inside .git: never part of the patch)."""
import io
import os
import re
import reprlib
import runpy
import sys
import threading
import traceback

MAX_FILES = 4
MAX_FUNCS = 8
MAX_ARGS = 110  # characters of 'args -> value' per function
MAX_LOCALS = 8
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
ran, first_args, first_out, pending = {}, {}, {}, {}


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


class _Short(reprlib.Repr):
    def __init__(self):
        super().__init__()
        self.maxstring, self.maxother, self.maxlevel = 40, 40, 2
        self.maxlist = self.maxtuple = self.maxset = self.maxfrozenset = self.maxdeque = self.maxarray = 3
        self.maxdict = 3

    def repr_instance(self, x, level):
        try:
            s = repr(x)
        except Exception:
            return f"<{type(x).__name__}>"
        if " object at 0x" in s:  # default repr: show the class and a few attributes instead of an address
            try:
                items = [(k, v) for k, v in vars(x).items() if not k.startswith("_")][:3]
                s = f"{type(x).__name__}(" + ", ".join(f"{k}={self.repr1(v, level - 1)}" for k, v in items) + ")"
            except Exception:
                s = f"<{type(x).__name__}>"
        return reprlib.Repr.repr_instance(self, s, level) if len(s) > self.maxother else s


SHORT = _Short()


def short(v):
    try:
        return SHORT.repr(v)
    except Exception:
        return "<?>"


def arg_text(frame):
    code = frame.f_code
    n = code.co_argcount + code.co_kwonlyargcount + bool(code.co_flags & 0x04) + bool(code.co_flags & 0x08)
    loc = frame.f_locals
    parts = []
    for name in code.co_varnames[:n]:
        if name in ("self", "cls") or name not in loc:
            continue
        parts.append(f"{name}={short(loc[name])}")
    return ", ".join(parts)


def local_tracer(key):
    """lines that ran; for the first call, its return value or the exception it raised (pending[frame]: '' = running,
    'Name' = an exception is passing through; a later line event in the same frame means it was caught there)."""
    def tracer(frame, event, arg):
        if event == "line":
            ran[key].add(frame.f_lineno)
            if pending.get(frame):
                pending[frame] = ""
        elif event == "exception":
            if frame in pending:
                pending[frame] = getattr(arg[0], "__name__", "exception")
        elif event == "return":
            if frame in pending:
                exc = pending.pop(frame)
                first_out[key] = f"raised {exc}" if exc else short(arg)
        return tracer
    return tracer


def trace(frame, event, arg):
    if event != "call":
        return None
    code = frame.f_code
    if not (code.co_flags & CO_OPTIMIZED) or code.co_name.startswith("<"):
        return None  # module bodies, class bodies, comprehensions, lambdas
    rel = relevant(code.co_filename)
    if rel is None or during_import(frame):
        return None
    key = (rel, code.co_firstlineno, code.co_name)
    if key not in calls:
        calls[key] = 0
        order.append(key)
        last_line[key] = code_end(code)
        ran[key] = set()
        first_args[key] = arg_text(frame)
        pending[frame] = ""
    calls[key] += 1
    return local_tracer(key)


def ranges(lines):
    out, run = [], []
    for n in sorted(lines):
        if run and n == run[-1] + 1:
            run.append(n)
        else:
            if run:
                out.append(run)
            run = [n]
    if run:
        out.append(run)
    return ",".join(f"{r[0]}-{r[-1]}" if len(r) > 1 else str(r[0]) for r in out)


def evidence(k):
    bits = []
    if ran.get(k):
        bits.append("ran " + ranges(ran[k]))
    a, o = first_args.get(k, ""), first_out.get(k)
    io_ = f"{a} -> {o}" if o is not None else (f"{a} -> (still running)" if a else "")
    if io_:
        bits.append(io_ if len(io_) <= MAX_ARGS else io_[:MAX_ARGS - 3] + "...")
    return ("  | " + " | ".join(bits)) if bits else ""


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
    out = ["", "== CODE PATH: functions of this repository the script ran (file: first-last name (calls) | lines that ran | first call: args -> returned)"]
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
            out.append(f"  {k[1]}-{last_line[k]} {k[2]} ({calls[k]}){evidence(k)}")
        if len(keys) > MAX_FUNCS:
            out.append(f"  ... {len(keys) - MAX_FUNCS} more")
    if len(files) > MAX_FILES:
        out.append(f"... {len(files) - MAX_FILES} more files: " + ", ".join(files[MAX_FILES:MAX_FILES + 6]))
    if exc is not None:
        tb = [f for f in traceback.extract_tb(exc.__traceback__) if relevant(f.filename)]
        if tb:
            f = tb[-1]
            out.append(f"raised {type(exc).__name__} at {relevant(f.filename)}:{f.lineno} in {f.name}: {(f.line or '').strip()[:120]}")
            frames = [fr for fr, _ in __import__("traceback").walk_tb(exc.__traceback__) if relevant(fr.f_code.co_filename)]
            if frames:
                loc = {k: v for k, v in frames[-1].f_locals.items() if not k.startswith("__")}
                shown = [f"{k}={short(v)}" for k, v in list(loc.items())[:MAX_LOCALS]]
                if shown:
                    out.append("  locals there: " + ", ".join(shown) + (f", ... {len(loc) - MAX_LOCALS} more" if len(loc) > MAX_LOCALS else ""))
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
    threading.settrace(trace)
    sys.settrace(trace)
    try:
        g = {"__name__": "__main__", "__file__": name, "__builtins__": __builtins__}
        exec(compile(source, name, "exec"), g)
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    except BaseException as e:
        exc, code = e, 1
    finally:
        sys.settrace(None)
        threading.settrace(None)
    if exc is not None:
        traceback.print_exception(type(exc), exc, exc.__traceback__)
    report(exc)
    return code


if __name__ == "__main__":
    sys.exit(main())
