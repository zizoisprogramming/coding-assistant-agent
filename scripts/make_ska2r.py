"""sk_a2r = sk_a2 with ONE change: run the code instead of tracing it by hand (TIMEOUT STUDY 2026-11-22 in docs/PLAN.md).
r138 + r139: runs that hit the 480 s cap spent 47% of their model time in replies that used the whole thinking allowance
(~70 s each) hand-tracing the function just shown ('pos = int((2 / 3) * 4) - 1 = 1 ... Correct. What if cut = 2'), then
re-reading a few lines of it; after a.py show 12% of replies do this, after a re-read (ALREADY SHOWN) 26%.
Event (a.py, option word 'runit' in commands.txt): every show that covers a function of a non-test .py file ends with a
RUN IT block: a ready python3 heredoc with the import line built from the path and the call built from the signature, so
running the code (~1 s) is the easiest next step. ALREADY SHOWN now says: edit if you know the lines, else run it.
Prompt: the reading section names RUN IT, the ALREADY SHOWN rule is split, and a second worked example shows the event.
User 2026-11-22: 'yes build it, 2 notebooks with sk_a2 control'. Run: python3 -I scripts/make_ska2r.py"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC, OUT = ROOT / "submissions/sk_a2", ROOT / "submissions/sk_a2r"

PROBE = '''

def probe(path, a, b):
    """sk_a2r: a ready-to-run call for the function shown at lines a-b ('' when there is none)."""
    if not path.endswith(".py") or TEST_RE.search(path):
        return ""
    try:
        tree = ast.parse("\\n".join(file_lines(path)))
    except SyntaxError:
        return ""
    best = []

    def walk(node, chain):
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, ast.ClassDef):
                start = min([d.lineno for d in ch.decorator_list] + [ch.lineno])
                if a <= start <= b and sum(isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)) for x in ch.body) > 1:
                    best.append((10 ** 6, 0, None, None))  # a whole class with several methods: no single call to offer
                if all(isinstance(x, ast.ClassDef) for x in chain):
                    walk(ch, chain + [ch])
            elif isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef)):
                start = min([d.lineno for d in ch.decorator_list] + [ch.lineno])
                over = min(b, ch.end_lineno) - max(a, start) + 1
                if over > 0 and all(isinstance(x, ast.ClassDef) for x in chain):
                    best.append((over, -(ch.end_lineno - start), ch, chain))
    walk(tree, [])
    if not best or max(best, key=lambda x: x[:2])[2] is None:  # none, or a whole class
        return ""
    _, _, fn, chain = max(best, key=lambda x: x[:2])
    mod = path[:-3]
    for pre in ("src/", "lib/"):
        mod = mod[len(pre):] if mod.startswith(pre) else mod
    mod = mod[:-len("/__init__")] if mod.endswith("/__init__") else mod
    if not mod or "-" in mod or "." in mod:
        return ""
    mod = mod.replace("/", ".")
    decos = {d.id if isinstance(d, ast.Name) else d.attr if isinstance(d, ast.Attribute) else "" for d in fn.decorator_list}
    params = [x.arg for x in fn.args.posonlyargs + fn.args.args]
    if chain and params and "staticmethod" not in decos:
        params = params[1:]  # self / cls
    args = ", ".join(params + [f"{x.arg}={x.arg}" for x, d in zip(fn.args.kwonlyargs, fn.args.kw_defaults) if d is None])
    if chain:
        top, owner = chain[0].name, ".".join(c.name for c in chain)
        if fn.name == "__init__":
            call = f"{owner}({args})"
        elif "staticmethod" in decos or "classmethod" in decos:
            call = f"{owner}.{fn.name}({args})"
        elif "property" in decos:
            call = f"{owner}(...).{fn.name}"
        else:
            call = f"{owner}(...).{fn.name}({args})"
    else:
        top, call = fn.name, f"{fn.name}({args})"
    if isinstance(fn, ast.AsyncFunctionDef):
        call = f"asyncio.run({call})"
    imp = ("import asyncio\\n  " if isinstance(fn, ast.AsyncFunctionDef) else "") + f"from {mod} import {top}"
    return ("\\nRUN IT, DO NOT TRACE IT: to see what this code does on an input, run it (about 1 second) instead of "
            "stepping through it by hand. Put 2-3 real inputs from the issue in place of the names (and of ... ), one "
            "print each:\\n  python3 - <<'EOF'\\n  " + imp + "\\n  print(" + call + ")\\n  EOF")
'''


def sub(t, a, b):
    assert t.count(a) == 1, a[:60]
    return t.replace(a, b)


def build():
    a = (SRC / "skills/agent/scripts/a.py").read_text()
    a = sub(a, 'OPTIONS = {"banner", "reshow"}', 'OPTIONS = {"banner", "reshow", "runit"}')
    a = sub(a, "\n\ndef cmd_note(st, args):", PROBE + "\n\ndef cmd_note(st, args):")
    a = sub(a, '''    st["reads"].append({"file": path, "a": a, "b": b})
    return extra + "\\n".join(f"{i:6}| {src[i - 1]}" for i in range(a, b + 1))''',
            '''    st["reads"].append({"file": path, "a": a, "b": b})
    tail = probe(path, a, b) if "runit" in OPTS else ""  # sk_a2r
    if tail:  # a re-read of a function: running it is the other way out
        extra = extra.replace("If these are the lines to change, your next call is the edit.\\n", "If these are the lines to "
                              "change, your next call is the edit; if you are unsure what they do, your next call runs them "
                              "(RUN IT below).\\n")
    return extra + "\\n".join(f"{i:6}| {src[i - 1]}" for i in range(a, b + 1)) + tail''')
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SRC, OUT)
    (OUT / "skills/agent/scripts/a.py").write_text(a)
    c = (SRC / "skills/agent/scripts/commands.txt").read_text().split()
    (OUT / "skills/agent/scripts/commands.txt").write_text(" ".join(c + ["runit"]) + "\n")
    p = (SRC / "prompts/system.md").read_text()
    p = sub(p, """so far. Older tool outputs are removed from the conversation as it grows: trust MEMORY instead of reading again.
When a.py prints NO EDIT YET, STOP READING or ALREADY SHOWN, your next call is the edit.""",
            """so far. Older tool outputs are removed from the conversation as it grows: trust MEMORY instead of reading again.
After a function, show prints RUN IT: its import and call, ready to run. To learn what code does on an input, run it
that way (about 1 second); never step through code by hand in your thinking (a minute or more, and often wrong).
When a.py prints NO EDIT YET or STOP READING, your next call is the edit. When it prints ALREADY SHOWN, your next call
is the edit if you know the lines to change, otherwise the RUN IT call.""")
    p = sub(p, """retries. Found it: the very next call is the edit that adds the same kind of check, raising
ValueError("timeout must be >= 0"). Then the client tests under timeout 90, then submit: 6 calls.""",
            """retries. Found it: the very next call is the edit that adds the same kind of check, raising
ValueError("timeout must be >= 0"). Then the client tests under timeout 90, then submit: 6 calls.

## Example 2: RUN IT (an invented package)
Task: "wrap() drops the last word when the width is exact." show pkg/text.py wrap prints a loop over words and ends
with RUN IT: from pkg.text import wrap / print(wrap(text, width)). Not sure which branch loses the word, so the next
call runs it instead of tracing the loop by hand:
  python3 - <<'EOF'
  from pkg.text import wrap
  print(wrap("ab cd", 5))
  print(wrap("ab cd", 4))
  EOF
It prints ['ab cd'] and ['ab'], so 'cd' is lost when the line is full: the next call is the edit in that branch, then
the text tests under timeout 90, then submit.""")
    (OUT / "prompts/system.md").write_text(p)
    y = (SRC / "agent.yaml").read_text()
    (OUT / "agent.yaml").write_text(sub(y, "# sk_a2: mix + the agent's reading tool",
                                        "# sk_a2r (2026-11-22): sk_a2 + RUN IT after show (scripts/make_ska2r.py). sk_a2 was: mix + the agent's reading tool"))
    print("wrote", OUT.relative_to(ROOT))


if __name__ == "__main__":
    build()
