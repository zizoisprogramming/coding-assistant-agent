"""The agent's reading tool with a memory, run through run_command (one flat string, never a garbled tool call).

  python3 .git/agent/a.py find "exact text" [PATH]    where it appears (grouped by file, test files marked)
  python3 .git/agent/a.py outline FILE                every class / function with its line numbers
  python3 .git/agent/a.py show FILE NAME              the whole function or class NAME (Class.method works)
  python3 .git/agent/a.py show FILE START END         numbered lines (at most 150)
  python3 .git/agent/a.py note "one line"             keep a finding (shown in every later output)
  python3 .git/agent/a.py pin FILE START END          keep these lines visible in every later output
  python3 .git/agent/a.py impact                      after an edit: other places that use what you changed
  python3 .git/agent/a.py check                       after an edit: .git/agent/repro.py + the nearest tests + git status

Every output starts with the MEMORY header (what was read, notes, pinned lines): older tool outputs get dropped from
the conversation, the header in the newest output never is. Installed by the skill into <repo>/.git/agent/ (git never
puts .git in the patch); its state lives next to it. Never edits the repository. Always exits 0.

Options (extra words in commands.txt, 2026-10-25, from the sk_a / sk_ad digests):
  banner   while the repository has no change: after NO_EDIT_LOOKS looks or NO_EDIT_SECONDS since setup, every output
           starts and ends with NO EDIT YET (later STOP READING): the edit came after call 28 in 6 of 32 runs
  reshow   a repeat of a recent read is shown again (at most RESHOW_MAX lines, marked ALREADY SHOWN) instead of
           refused: NOT SHOWN AGAIN cost 2-3 of the 28 calls per run
"""
import ast
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPRO = os.path.join(HERE, "repro.py")  # per task (2 tasks may run at once: a shared /tmp/repro.py would mix them up)
WS = os.path.dirname(os.path.dirname(HERE))  # <repo>/.git/agent/a.py -> <repo>
STATE = os.path.join(HERE, "state.json")
SHOW_MAX, FIND_MAX, PIN_MAX, NOTES_MAX, RECENT = 150, 30, 40, 20, 3
NO_EDIT_LOOKS, NO_EDIT_SECONDS, STOP_LOOKS, STOP_SECONDS, RESHOW_MAX = 10, 210, 15, 300, 40
OPTIONS = {"banner", "reshow"}
TEST_RE = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)conftest\.py$")
try:  # the commands this agent was taught (written by the skill's install.py)
    COMMANDS = open(os.path.join(HERE, "commands.txt")).read().split()
except OSError:
    COMMANDS = "find outline show note pin impact check".split()
OPTS = OPTIONS & set(COMMANDS)
COMMANDS = [c for c in COMMANDS if c not in OPTIONS]
STOP = {"self", "None", "True", "False", "return", "import", "from", "class", "def", "pass", "raise", "with", "else",
        "elif", "while", "for", "lambda", "yield", "assert", "async", "await", "print", "str", "int", "bool", "dict",
        "list", "tuple", "set", "type", "Optional", "Union", "Any", "List", "Dict", "Tuple", "kwargs", "args", "cls",
        "value", "result", "name", "data", "text", "isinstance", "len", "range", "super", "init", "object", "Exception"}


def load():
    try:
        return json.load(open(STATE))
    except Exception:  # noqa: BLE001
        return {"looks": 0, "reads": [], "notes": [], "pins": [], "t0": time.time()}


def save(st):
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(st, f)
    os.replace(tmp, STATE)


def run(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, cwd=WS, shell=True, capture_output=True, text=True, timeout=timeout)
        return (r.stdout + r.stderr).rstrip()
    except subprocess.TimeoutExpired:
        return f"(timed out after {timeout}s)"


def q(s):
    return "'" + s.replace("'", "'\\''") + "'"


def rel(path):
    path = path.strip().removeprefix("/workspace/").removeprefix("./")
    return os.path.relpath(path, WS) if os.path.isabs(path) else path


def file_lines(path):
    with open(os.path.join(WS, path), encoding="utf-8", errors="replace") as f:
        return f.read().split("\n")


def merge(ranges):
    out = []
    for a, b in sorted(ranges):
        if out and a <= out[-1][1] + 1:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def header(st):
    by = {}
    for r in st["reads"]:
        by.setdefault(r["file"], []).append((r["a"], r["b"]))
    if "note" in COMMANDS or st["notes"] or st["pins"]:
        lines = [f"===== MEMORY (survives context trimming) | looks {st['looks']} | notes {len(st['notes'])} | pinned "
                 f"lines {sum(p['b'] - p['a'] + 1 for p in st['pins'])} ====="]
    else:
        lines = [f"===== MEMORY (survives context trimming) | looks {st['looks']} ====="]
    if by:
        lines.append("read so far: " + " | ".join(f"{f} " + ",".join(f"{a}-{b}" for a, b in merge(rs)) for f, rs in by.items()))
    for i, n in enumerate(st["notes"], 1):
        lines.append(f"note {i}: {n}")
    for p in st["pins"]:
        try:
            src = file_lines(p["file"])
            lines.append(f"pinned {p['file']} {p['a']}-{p['b']}:")
            lines += [f"{i:6}| {src[i - 1]}" for i in range(p["a"], min(p["b"], len(src)) + 1)]
        except OSError:
            lines.append(f"pinned {p['file']} {p['a']}-{p['b']}: (file gone)")
    lines.append("=" * 40)
    return "\n".join(lines)


def outline_items(path):
    """[(qualname, start, end, kind)] for every class / function in a Python file."""
    try:
        tree = ast.parse("\n".join(file_lines(path)))
    except SyntaxError:
        return None
    items = []

    def walk(node, prefix):
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                start = min([d.lineno for d in ch.decorator_list] + [ch.lineno])
                kind = "class" if isinstance(ch, ast.ClassDef) else "def"
                items.append((prefix + ch.name, start, ch.end_lineno, kind))
                walk(ch, prefix + ch.name + ".")
    walk(tree, "")
    return items


def cmd_find(st, args):
    path_args = [a for a in args[1:] if os.path.exists(os.path.join(WS, rel(a)))]
    text = " ".join([args[0]] + [a for a in args[1:] if a not in path_args]) if args else ""  # unquoted words
    if not text:
        return 'usage: find "exact text" [PATH]'
    st["looks"] += 1
    where = " ".join(q(rel(p)) for p in path_args) or "."
    out = run(f"git grep -n -I -F -e {q(text)} -- {where}")
    note = ""
    if not out:
        out = run(f"git grep -n -I -i -F -e {q(text)} -- {where}")
        note = "(no exact match; case-insensitive matches)\n" if out else ""
    if not out:
        words = [w for w in re.findall(r"[A-Za-z_][A-Za-z0-9_]{3,}", text) if w not in STOP]
        if len(words) > 1:
            return f'(no match for "{text}") try one word at a time: ' + ", ".join(f'find "{w}"' for w in words[:4])
        return f'(no match for "{text}")'
    hits = out.split("\n")
    groups = {}
    for h in hits:
        f, _, rest = h.partition(":")
        groups.setdefault(f, []).append(rest)
    order = sorted(groups, key=lambda f: (bool(TEST_RE.search(f)), f))
    shown, lines = 0, [note + f'{len(hits)} matches for "{text}" in {len(groups)} files:']
    for f in order:
        if shown >= FIND_MAX:
            break
        lines.append(f + (" [TEST]" if TEST_RE.search(f) else ""))
        for r in groups[f][:max(1, FIND_MAX - shown)]:
            lines.append("   " + r[:200])
            shown += 1
            if shown >= FIND_MAX:
                break
    if len(hits) > shown:
        lines.append(f"... {len(hits) - shown} more: add a PATH or use a more exact text")
    return "\n".join(lines)


def cmd_outline(st, args):
    if not args:
        return "usage: outline FILE"
    path = rel(args[0])
    if not os.path.isfile(os.path.join(WS, path)):
        return no_file(path)
    st["looks"] += 1
    items = outline_items(path)
    n = len(file_lines(path))
    if items is None:
        defs = [f"{i:6}| {l.strip()[:100]}" for i, l in enumerate(file_lines(path), 1)
                if re.match(r"\s*(def|class|async def)\s", l)]
        return f"{path} ({n} lines, not parsable as Python; def/class lines):\n" + "\n".join(defs[:80])
    lines = [f"{path} ({n} lines):"]
    for name, a, b, kind in items[:80]:
        lines.append(f"  {'  ' * name.count('.')}{kind} {name.split('.')[-1]}  {a}-{b}")
    if len(items) > 80:
        lines.append(f"  ... {len(items) - 80} more")
    return "\n".join(lines)


def no_file(path):
    base = os.path.basename(path)
    guess = run(f"git ls-files | grep -F {q(base)} | head -5")
    return f"(no such file: {path})" + (f" did you mean: {guess.replace(chr(10), ', ')}" if guess else "")


def cmd_show(st, args):
    if not args:
        return "usage: show FILE NAME | show FILE START END"
    path, rest = args[0], args[1:]
    m = re.match(r"^(.*?):(\d+)(?:-(\d+))?$", path)
    if m:
        path, rest = m.group(1), [m.group(2)] + ([m.group(3)] if m.group(3) else [])
    path = rel(path)
    if not os.path.isfile(os.path.join(WS, path)):
        return no_file(path)
    src = file_lines(path)
    extra = ""
    nums = [int(x) for x in re.findall(r"\d+", " ".join(rest))]
    if rest and not nums:  # a name
        name = rest[0]
        items = outline_items(path) or []
        hits = [it for it in items if it[0] == name or it[0].endswith("." + name)]
        if not hits:
            return f"(no class or function named {name} in {path}; use outline {path})"
        _, a, b, _ = hits[0]
        if len(hits) > 1:
            extra = "other definitions: " + ", ".join(f"{h[0]} {h[1]}-{h[2]}" for h in hits[1:5]) + "\n"
    else:
        a = max(nums[0] if nums else 1, 1)
        b = nums[1] if len(nums) > 1 and nums[1] >= a else a + 79
    b = min(b, len(src))
    if b - a + 1 > SHOW_MAX:
        extra += f"(continues to line {b}: show {path} {a + SHOW_MAX} {b})\n"
        b = a + SHOW_MAX - 1
    want = set(range(a, b + 1))
    for k, r in enumerate(reversed(st["reads"][-RECENT:])):
        seen = set(range(r["a"], r["b"] + 1))
        if r["file"] == path and len(want & seen) > 0.5 * len(want):
            if "reshow" not in OPTS:
                return (f"NOT SHOWN AGAIN: {path} lines {r['a']}-{r['b']} were shown {k + 1} look(s) ago and are still "
                        f"above in this conversation. Use them, or ask for lines you have not seen.")
            b = min(b, a + RESHOW_MAX - 1)
            extra = extra + (f"ALREADY SHOWN {k + 1} look(s) ago ({path} {r['a']}-{r['b']}); again below, at most {RESHOW_MAX} "
                     f"lines. If these are the lines to change, your next call is the edit.\n")
            break
    st["looks"] += 1
    st["reads"].append({"file": path, "a": a, "b": b})
    return extra + "\n".join(f"{i:6}| {src[i - 1]}" for i in range(a, b + 1))


def cmd_note(st, args):
    text = " ".join(args).strip()
    if not text:
        return 'usage: note "one line"'
    st["notes"] = (st["notes"] + [text[:200]])[-NOTES_MAX:]
    return f"noted ({len(st['notes'])} notes)"


def cmd_pin(st, args):
    nums = [int(x) for x in re.findall(r"\d+", " ".join(args[1:]))] if len(args) > 1 else []
    if not args or len(nums) < 1:
        return "usage: pin FILE START END"
    path = rel(args[0])
    if not os.path.isfile(os.path.join(WS, path)):
        return no_file(path)
    a, b = nums[0], nums[1] if len(nums) > 1 else nums[0]
    b = min(max(a, b), a + PIN_MAX - 1)
    st["pins"].append({"file": path, "a": a, "b": b})
    while sum(p["b"] - p["a"] + 1 for p in st["pins"]) > PIN_MAX and len(st["pins"]) > 1:
        st["pins"].pop(0)
    return f"pinned {path} {a}-{b}"


def changed_source():
    files = [f for f in run("git diff --name-only").split("\n") if f.endswith(".py") and not TEST_RE.search(f)]
    return files


def cmd_impact(st, args):
    files = changed_source()
    if not files:
        return "(no edited source file yet: impact lists other places that use what your edit changed)"
    diff = run("git diff -U3 -- " + " ".join(q(f) for f in files))
    changed, near, defined = set(), set(), set()
    cur = None
    for line in diff.split("\n"):
        if line.startswith("+++ b/"):
            cur = line[6:]
            continue
        if line.startswith(("---", "+++", "diff ", "index ")):
            continue
        if line.startswith("@@"):
            m = re.search(r"@@.*@@\s*(?:async\s+)?(?:def|class)\s+(\w+)", line)
            if m:
                changed.add(m.group(1))
            continue
        body = line[1:]
        ids = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]{4,}", body)) - STOP
        strs = {s for s in re.findall(r"[\"']([A-Za-z_][A-Za-z0-9_.-]{4,})[\"']", body)}
        if line.startswith(("+", "-")):
            defined |= set(re.findall(r"(?:def|class)\s+(\w+)", body)) - STOP
            m = re.findall(r"(?:def|class)\s+(\w+)", body) + re.findall(r"self\.(\w+)\s*=", body) + \
                re.findall(r"(\w+)\s*[:=][^=]", body.split("(")[-1] if "def " in body else "")
            changed |= set(m) - STOP
        else:
            near |= ids | strs
    near -= changed
    edited = {}  # file -> line numbers of the edit (+-3): hits there are the edit itself
    for f in files:
        for m in re.finditer(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", run("git diff -U0 -- " + q(f)), re.M):
            a, n = int(m.group(1)), int(m.group(2) or 1)
            edited.setdefault(f, set()).update(range(a - 3, a + n + 3))
    strings = set()
    for line in diff.split("\n"):
        if line[:1] == " ":
            strings |= set(re.findall(r"[\"']([A-Za-z_][A-Za-z0-9_.-]{4,})[\"']", line))
    out = []
    for title, names in (("NAMES YOUR EDIT CHANGED, used elsewhere", changed), ("NAMES NEXT TO YOUR EDIT (siblings), used elsewhere", near)):
        rows = []
        for name in names:
            hits = [h for h in run(f"git grep -n -w -F -e {q(name)} -- '*.py'").split("\n") if h.count(":") >= 2]
            hits = [h for h in hits if not TEST_RE.search(h.split(":")[0])
                    and int(h.split(":")[1]) not in edited.get(h.split(":")[0], ())]
            nfiles = {h.split(":")[0] for h in hits}
            if not hits or (len(nfiles) > 6 and name not in defined):
                continue  # unused elsewhere, or everywhere (not specific); a changed def/class always counts
            other = nfiles - set(files)
            rank = (name not in defined, name not in strings, not other, len(nfiles), len(hits))
            cap = 10 if name in defined else 6
            rows.append((rank, f"  {name}{' (callers)' if name in defined else ''}: "
                         + ", ".join(sorted(h.split(':')[0] + ':' + h.split(':')[1] for h in hits)[:cap])
                         + (f" ... {len(hits) - cap} more (find {name})" if len(hits) > cap else "")))
        rows = [r for _, r in sorted(rows)[:10]]
        out.append(title + ":\n" + ("\n".join(rows) if rows else "  (none)"))
    out.append("Check each listed place: does it need the same change (a new option passed on, a list or table that names "
               "the siblings, an export, the other sync/async copy)? Then run check.")
    return "\n".join(out)


def cmd_check(st, args):
    out = []
    if os.path.exists(REPRO):
        out.append("$ python3 .git/agent/repro.py\n" + "\n".join(run("python3 .git/agent/repro.py 2>&1", 60).split("\n")[-15:]))
    else:
        out.append("(no .git/agent/repro.py: write the issue's example there with write_file to check the behaviour itself)")
    tests = []
    for f in changed_source()[:3]:
        stem = os.path.splitext(os.path.basename(f))[0].lstrip("_")
        cand = [t for t in run(f"git ls-files | grep -E '(^|/)tests?/(.*/)?test_{re.escape(stem)}\\.py$'").split("\n") if t]
        if not cand:
            mod = os.path.splitext(f)[0].replace("/", ".")
            pattern = q("(from|import) " + re.escape(mod) + r"\b")
            cand = [t for t in run("git grep -l -E " + pattern + " -- 'tests' 'test'").split("\n") if t][:1]
        if not cand:  # tests that use a function or class the edit changed
            names = re.findall(r"^@@.*@@\s*(?:async\s+)?(?:def|class)\s+(\w+)", run("git diff -U0 -- " + q(f)), re.M)
            for name in dict.fromkeys(names):
                hit = [t for t in run(f"git grep -l -w -F -e {q(name)} -- 'tests' 'test'").split("\n") if t]
                if hit:
                    cand = hit[:1]
                    break
        tests += [t for t in cand[:1] if t not in tests]
    if tests:
        res = run("python3 -m pytest " + " ".join(q(t) for t in tests) + " -x -q -p no:anyio -o timeout=0 2>&1", 150)
        out.append("$ pytest " + " ".join(tests) + "\n" + "\n".join(res.split("\n")[-25:]))
    elif changed_source():
        out.append("(no existing test file found for the edited modules)")
    else:
        out.append("(no edited source file yet)")
    status = run("git status --short --untracked-files=all")
    flags = []
    for line in status.split("\n"):
        if not line.strip():
            continue
        code, path = line[:2], line[3:]
        if code.strip() == "??" and not path.startswith(".git/"):
            flags.append(f"  SCRATCH FILE {path}: it would become part of your patch; delete it (rm {path}) or keep scratch in /tmp")
        elif TEST_RE.search(path):
            flags.append(f"  TEST FILE CHANGED {path}: the grader resets tests; restore it (git checkout -- {path})")
    out.append("$ git status --short\n" + (status or "(no changes)") + ("\n" + "\n".join(flags) if flags else ""))
    return "\n\n".join(out)


def has_change():
    """Any change in the working tree (git status never lists .git, so the tool's own files do not count)."""
    out = run("git status --porcelain --untracked-files=all", 20)
    return bool(out.strip()) and not out.startswith("(timed out")


def banner(st):
    if "banner" not in OPTS or has_change():
        return ""
    secs = int(time.time() - st.get("t0", time.time()))
    used = f"{st['looks']} looks, {secs // 60}:{secs % 60:02d} of the 8 minutes used"
    if st["looks"] >= STOP_LOOKS or secs >= STOP_SECONDS:
        return (f">>> STOP READING: {used}, and still no edit. Make your best edit with your next call: no edit scores "
                f"zero, an imperfect edit can pass. <<<")
    if st["looks"] >= NO_EDIT_LOOKS or secs >= NO_EDIT_SECONDS:
        return f">>> NO EDIT YET: {used}. If you know which lines to change, your next call is the edit. <<<"
    return ""


HANDLERS = {"find": cmd_find, "outline": cmd_outline, "show": cmd_show, "note": cmd_note, "pin": cmd_pin,
            "impact": cmd_impact, "check": cmd_check}


def main(argv):
    st = load()
    if not argv or argv[0].lstrip("-").lower() not in COMMANDS:
        body = "commands: " + ", ".join(COMMANDS) + " (python3 .git/agent/a.py COMMAND ...)"
    else:
        try:
            body = HANDLERS[argv[0].lstrip("-").lower()](st, argv[1:])
        except Exception as e:  # noqa: BLE001  never crash: the model gets a message and the header
            body = f"(error in {argv[0]}: {type(e).__name__}: {e})"
    save(st)
    warn = banner(st)
    if warn:
        print(warn)
    print(header(st))
    print(body)
    if warn:
        print(warn)


if __name__ == "__main__":
    main(sys.argv[1:])
