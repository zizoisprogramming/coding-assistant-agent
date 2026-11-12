"""Shell for evloop's attempt rounds (r92, user 2026-11-12 "build all": LoopAgent rounds with fresh contexts).

    run_skill_script skill act, file act.py, positional_args ["<one shell command>"]

Runs the command with bash in the repository root (timeout 120 s, output cut to 4,000 characters) and counts the
calls of the current round (.git/agent/round, advanced by check.py). After LIMIT calls in a round every call is refused
with a line that says to make the edit now and end the round: a refusal is the one limit this model follows (memory
event-triggered-rules-only), and the shared call budget has no per-agent limit (r88: a free drafter ran 9-78 calls).
'/workspace' and '/tmp' in the command are mapped as the harness maps them in run_command (swegemma's subprocess
sandbox rewrites them only in command strings, and this command reaches bash through Python)."""
import inspect
import os
import re
import subprocess
import sys
import tempfile

LIMIT = 8
TIMEOUT = 120
OUT_MAX = 4000


def workspace():
    for frame in inspect.stack():
        cwd = frame.frame.f_locals.get("_orig_cwd")
        if isinstance(cwd, str) and os.path.isdir(os.path.join(cwd, ".git")):
            return cwd
    for cand in (os.environ.get("PYTHONPATH", "").split(os.pathsep)[0], "/workspace", os.getcwd()):
        if cand and os.path.isdir(os.path.join(cand, ".git")):
            return cand
    sys.exit("repository not found")


def read_int(path, default):
    try:
        return int(open(path).read().strip() or default)
    except (OSError, ValueError):
        return default


def main(argv):
    ws = workspace()
    agent = os.path.join(ws, ".git", "agent")
    os.makedirs(agent, exist_ok=True)
    rnd = read_int(os.path.join(agent, "round"), 1)
    counter = os.path.join(agent, f"act_count_{rnd}")
    used = read_int(counter, 0)
    if used >= LIMIT:
        return ("ROUND LIMIT REACHED: this round's commands are used up. If you have not edited the source yet, make "
                "your best edit now with edit_file. Then reply with one line, ROUND DONE: <what you changed>.")
    cmd = " ".join(a for a in argv if a != "--").strip()
    if not cmd:
        return 'usage: positional_args ["<one shell command>"], for example ["git grep -n -F convert_underscores -- \'*.py\' | head -20"]'
    with open(counter, "w") as f:
        f.write(str(used + 1))
    tmp = tempfile.gettempdir()
    cmd = re.sub(r"(?<![\w.-])/workspace(?![\w.-])", ws, cmd)
    cmd = re.sub(r"(?<![\w.-])/tmp(?![\w.-])", tmp, cmd)
    try:
        r = subprocess.run(["/bin/bash", "-c", cmd], cwd=ws, capture_output=True, text=True, timeout=TIMEOUT,
                           stdin=subprocess.DEVNULL, errors="replace")
        out = (r.stdout or "") + (("\n[stderr]\n" + r.stderr) if r.stderr.strip() else "") + f"\n[exit {r.returncode}]"
    except subprocess.TimeoutExpired:
        out = f"[timed out after {TIMEOUT} s]"
    if len(out) > OUT_MAX:
        out = out[:OUT_MAX // 2] + "\n[... cut ...]\n" + out[-OUT_MAX // 2:]
    left = LIMIT - used - 1
    return out + (f"\n[{left} command(s) left in this round]" if left else
                  "\n[that was this round's last command: edit now if you have not, then reply ROUND DONE]")


if __name__ == "__main__":
    print(main(sys.argv[1:]))
