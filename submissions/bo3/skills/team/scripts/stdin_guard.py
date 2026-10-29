"""Keeps scripts from hanging on input() in the agent's sandbox (installed by the skills' setup scripts).

The sandbox starts every command with subprocess.Popen and no stdin (adk_eval_core subprocess_sandbox.py), so a
command inherits the notebook's stdin: open, but nothing ever arrives. A script that asks for input (rich's
Prompt.ask in rich_3882) then waits until the 240 s command timeout: 2 such runs cost 240 s each. Loaded by a .pth
file in the sandbox venv, this wraps a non-terminal stdin: a read that gets no data within WAIT seconds returns '' (end
of input), so input() raises EOFError at once; piped data (echo x | python3 ...) is there at once and reads normally.
"""
import select
import sys

WAIT = 2.0


class _Guarded:
    def __init__(self, f):
        self._f = f

    def _ready(self):
        try:
            return bool(select.select([self._f], [], [], WAIT)[0])
        except Exception:  # noqa: BLE001  no fileno (already replaced, closed): behave as before
            return True

    def readline(self, *a):
        return self._f.readline(*a) if self._ready() else ""

    def read(self, *a):
        return self._f.read(*a) if self._ready() else ""

    def readlines(self, *a):
        return self._f.readlines(*a) if self._ready() else []

    def __iter__(self):
        while True:
            line = self.readline()
            if not line:
                return
            yield line

    def __getattr__(self, name):
        return getattr(self._f, name)


def install():
    try:
        if sys.stdin is not None and not sys.stdin.isatty() and not isinstance(sys.stdin, _Guarded):
            sys.stdin = _Guarded(sys.stdin)
    except Exception:  # noqa: BLE001  never break interpreter start-up
        pass


install()
