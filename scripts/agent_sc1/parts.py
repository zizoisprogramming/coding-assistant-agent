"""sc1 parts (user 2026-11-21: 'go' on combining sk_a2 with the other agents' proven parts; docs/PLAN.md SC1 DESIGN).
Builds the skill files from their sources (all our own code) and the edit step:
  a.py       = sk_a2's reading tool (find / outline / show, MEMORY header, ALREADY SHOWN, NO EDIT YET / STOP READING banners) with two
               changes: only a change to a TRACKED file counts as an edit (scratch files no longer silence the banner) and the banner
               text carries no clock numbers (closed line: clock numbers in events);
  where.py   = sbE4A's cut-down evidence search (where each name is defined / used in source + test lines that use it), one-call rule off;
  install.py = sk_a2's installer + prints where.py's lines for the names given as positional_args (evidc's search folded into the
               one install call: no extra call, no extra agent);
  EDIT_STEP  = sb1h's heredoc Python step + the backslash fallback + a line-number fallback (old text copied with a.py's '   12| '
               column is stripped and retried when that is the only difference) + nothing else."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKA2 = ROOT / "submissions/sk_a2/skills/agent/scripts"


def load(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


H = load("make_sb1h", ROOT / "scripts/make_sb1h.py")
F = load("edit_fallback", ROOT / "scripts/edit_fallback.py")

NO_EDIT = ">>> NO EDIT YET: you have read a lot and changed no file. If you know which lines to change, your next call is the edit. <<<"
STOP = ">>> STOP READING: still no edit after all this reading. Make your best edit with your next call: no edit scores zero, an imperfect edit can pass. <<<"
NUMBERS = "line numbers from the show output removed from your text"


def a_py():
    s = (SKA2 / "a.py").read_text()
    reps = [
        ('''def has_change():
    """Any change in the working tree (git status never lists .git, so the tool's own files do not count)."""
    out = run("git status --porcelain --untracked-files=all", 20)
    return bool(out.strip()) and not out.startswith("(timed out")''',
         '''def has_change():
    """sc1: a change to a TRACKED file (an edit of the source); scratch files the agent creates do not count."""
    out = run("git diff --name-only", 20)
    return bool(out.strip()) and not out.startswith("(timed out")'''),
        ('''    secs = int(time.time() - st.get("t0", time.time()))
    used = f"{st['looks']} looks, {secs // 60}:{secs % 60:02d} of the 8 minutes used"
    if st["looks"] >= STOP_LOOKS or secs >= STOP_SECONDS:
        return (f">>> STOP READING: {used}, and still no edit. Make your best edit with your next call: no edit scores "
                f"zero, an imperfect edit can pass. <<<")
    if st["looks"] >= NO_EDIT_LOOKS or secs >= NO_EDIT_SECONDS:
        return f">>> NO EDIT YET: {used}. If you know which lines to change, your next call is the edit. <<<"''',
         '''    secs = int(time.time() - st.get("t0", time.time()))
    if st["looks"] >= STOP_LOOKS or secs >= STOP_SECONDS:  # sc1: no clock numbers in the text
        return "''' + STOP + '''"
    if st["looks"] >= NO_EDIT_LOOKS or secs >= NO_EDIT_SECONDS:
        return "''' + NO_EDIT + '''"'''),
    ]
    for a, b in reps:
        assert s.count(a) == 1, a[:60]
        s = s.replace(a, b)
    return '"""sc1 copy of sk_a2\'s a.py (scripts/agent_sc1/parts.py: tracked-file edits only, no clock numbers in the banner).\n\n' + s.split('"""', 1)[1]


def where_py():
    e4 = load("make_expect_e4", ROOT / "scripts/make_expect_e4.py")
    s = e4.search_script()
    a = "ONCE = True"
    assert s.count(a) == 1
    return s.replace(a, "ONCE = False  # sc1: called by install.py once per task; no one-call file")


def install_py():
    s = (SKA2 / "install.py").read_text()
    s = s.replace('"""Copy a.py into', '"""sc1: sk_a2\'s installer + where.py\'s lines for the names given as positional_args. Copy a.py into', 1)
    s += '''
names = [a for a in sys.argv[1:] if a != "--"]
if names:  # sc1: evidc's search folded into this call
    import runpy
    print()
    sys.argv = [os.path.join(here, "where.py")] + names
    try:
        runpy.run_path(os.path.join(here, "where.py"), run_name="__main__")
    except SystemExit:
        pass
'''
    return s


SKILL_MD = """---
name: agent
description: Sets up the reading tool .git/agent/a.py (outside the patch) and shows where the issue's names are. Call run_skill_script with skill_name agent, file_path scripts/install.py and positional_args holding two to four exact names from the issue, once, as the first call.
---

Call run_skill_script with skill_name agent, file_path scripts/install.py and positional_args holding two to four exact names from
the issue, one name per item. It prints READY with the reading commands, then where each name is defined and test lines that use
it. Then read through run_command: python3 .git/agent/a.py COMMAND ...
Never run pip: the sandbox has no internet and every dependency is already installed.
"""

NUM_ADD = ("if s.count(old) == 0 and old.strip() and all(re.match('^ *[0-9]+[|] ', l) for l in old.splitlines() if l.strip()):\n"
           "    o2, n2 = re.sub('(?m)^ *[0-9]+[|] ', '', old), re.sub('(?m)^ *[0-9]+[|] ', '', new)\n"
           "    if s.count(o2) == 1:\n"
           "        old, new = o2, n2\n"
           "        print('" + NUMBERS + "')\n")


def edit_step():
    s = F.halve(H.PY_STEP)
    s = s.replace("import pathlib, sys\n", "import pathlib, re, sys\n", 1)
    a = "print('old text found', s.count(old), 'times')\n"
    assert s.count(a) == 1
    s = s.replace(a, NUM_ADD + a)
    assert '"' not in s and "`" not in s and "\\" not in s and "{" not in s and "}" not in s
    return s
