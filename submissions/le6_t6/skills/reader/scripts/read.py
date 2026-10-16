"""The locator's reader, run through run_command (one flat string, so the tool call is never garbled).

  python3 .git/agent/read.py find "exact name or message"     git grep hits with the code that follows
  python3 .git/agent/read.py show path/to/file.py 40 160       numbered lines, at most 150 (also file.py:40-160)
  python3 .git/agent/read.py history NAME | SHA                commits that added/removed NAME, or one commit

All three share LIMIT reads. At the limit it refuses and tells the locator to call the editor, while the task still
has tool calls left for the edit. Always exits 0 so the result reaches the model as normal output.
"""
import os
import re
import subprocess
import sys

LIMIT = 16
WARN_FROM = 13
HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.dirname(os.path.dirname(HERE))        # <repo>/.git/agent/read.py -> <repo>
COUNTER = os.path.join(HERE, "reads")
USAGE = ('usage: python3 .git/agent/read.py find "NAME" | show path/to/file.py START END | history NAME')


def run(cmd, timeout=60):
    try:
        res = subprocess.run(cmd, cwd=WS, shell=True, capture_output=True, text=True, timeout=timeout)
        return (res.stdout + res.stderr).rstrip()
    except subprocess.TimeoutExpired:
        return f"(timed out after {timeout}s)"


def take_read():
    used = int(open(COUNTER).read() or 0) if os.path.exists(COUNTER) else 0
    if used >= LIMIT:
        print(f"READING LIMIT REACHED ({LIMIT} reads used). Stop reading. Call the editor now: the request is your plan "
              "(FILE / WHAT IT DOES / CHANGE ... WITH ... / CONTRACT). After it answers, check the diff and submit.")
        sys.exit(0)
    used += 1
    with open(COUNTER, "w") as f:
        f.write(str(used))
    return used


def footer(used):
    left = LIMIT - used
    msg = f"[read {used} of {LIMIT}"
    if used >= WARN_FROM:
        msg += f"; {left} left: decide the change and call the editor" if left else "; none left: call the editor now"
    return msg + "]"


def quote(text):
    return "'" + text.replace("'", "'\\''") + "'"


def main(argv):
    if not argv:
        print(USAGE)
        return
    mode, rest = argv[0].lower().lstrip("-"), argv[1:]
    if mode == "find":
        query = " ".join(rest).strip()
        if not query:
            print(USAGE)
            return
        used = take_read()
        out = run(f"git grep -n -I -A 12 -e {quote(query)} -- '*.py' '*.md' '*.txt' '*.toml' | head -70")
        if not out:
            out = run(f"git grep -n -I -i -e {quote(query)} -- . | head -30") or "(no match)"
        print(out)
        print(footer(used))
    elif mode == "show":
        if not rest:
            print(USAGE)
            return
        path, nums = rest[0], [a for a in rest[1:]]
        m = re.match(r"^(.*?):(\d+)(?:-(\d+))?$", path)
        if m:
            path, nums = m.group(1), [m.group(2)] + ([m.group(3)] if m.group(3) else [])
        nums = [int(x) for x in re.findall(r"\d+", " ".join(nums))]
        path = path.removeprefix("/workspace/").removeprefix("./")
        start = max(nums[0] if nums else 1, 1)
        end = nums[1] if len(nums) > 1 and nums[1] >= start else start + 149
        end = min(end, start + 149)
        full = os.path.join(WS, path)
        if not os.path.isfile(full):
            print(f"(no such file: {path})")
            return
        used = take_read()
        lines = open(full, encoding="utf-8", errors="replace").read().split("\n")
        print("\n".join(f"{i:5}| {lines[i - 1]}" for i in range(start, min(end, len(lines)) + 1)))
        print(footer(used))
    elif mode == "history":
        query = " ".join(rest).strip()
        if not query:
            print(USAGE)
            return
        used = take_read()
        if re.fullmatch(r"[0-9a-f]{7,40}", query):
            print(run(f"git show --stat --format='%h %s' {query} | head -20 && git show --format= {query} | head -80"))
        else:
            print(run(f"git log --oneline -S{quote(query)} | head -15") or "(no commit adds or removes it)")
            print("recent commits:\n" + run("git log --oneline -8"))
        print(footer(used))
    else:
        print(USAGE)


if __name__ == "__main__":
    main(sys.argv[1:])
