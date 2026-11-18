"""Step 0c: FUNCTION-level history instead of line history (user 2026-11-18: 'no don't close the history idea, just
see what can we do more'). CPU only, git commands only, on the sparse *.py checkouts made by name_history_precheck.py.
Run: python3 -I scripts/mine_bank/func_history_precheck.py CLONE_DIR   (repo root)

r113 / r114: line history at the def / use line of the issue's names (+-2 lines) showed refactor / format / declaration
commits (rich_3521: 'class Segment' NamedTuple swaps, a type-ignore cleanup) instead of the commits that changed the
buggy function body. `git log -L :FUNC:FILE` follows a whole function. Two variants, both compared with the real-fix
lines' last 3 commits (the 'gold' history of line_history_precheck.py):
  A (what a stage could do): names from the issue (the same stand-in as Step 0b), for each the function(s) whose name
    is or contains it (def / class, also with a leading _), at most 2, git log -L :name:file -n 3.
  O (upper bound): the function that holds each real-fix hunk (nearest def above it), git log -L :name:file -n 3.
Printed per task: functions used, a shown commit that also changed the real-fix lines, chars after the per-commit cap."""
import collections, json, os, re, subprocess, sys
from pathlib import Path

CLONES = Path(sys.argv[1])
WT = CLONES.parent / "wt"
src = open("scripts/mine_bank/name_history_precheck.py").read()
ns = {}
exec(src[:src.index("CMD = next(")].replace("CLONES = Path(sys.argv[1])", "CLONES = Path(" + repr(str(CLONES)) + ")"), ns)
T, git, names_of, TEST = ns["T"], ns["git"], ns["names_of"], ns["TEST"]
changed_lines, regions = ns["ns"]["changed_lines"], ns["ns"]["regions"]
ENV = dict(os.environ, GIT_CONFIG_COUNT="2", GIT_CONFIG_KEY_0="core.hooksPath", GIT_CONFIG_VALUE_0="/dev/null",
           GIT_CONFIG_KEY_1="core.fsmonitor", GIT_CONFIG_VALUE_1="false", GIT_TERMINAL_PROMPT="0")
ATTR = CLONES.parent / "attr_py"  # '*.py diff=python': git's built-in python funcname driver, so indented methods count as functions (config flag, the repo is not changed)
ATTR.write_text("*.py diff=python\n")
AWK = "awk '/^commit /{n=0} !/^(diff|index|---|[+][+][+])/ && n++<16' | cut -c1-150"


def func_log(w, f, fn):
    r = subprocess.run(["/bin/bash", "-c", f"git -c core.attributesFile={ATTR} log -L :{fn}:{f} -n 3 --format='commit %h %ad %s' --date=short 2>/dev/null | {AWK}"],
                       cwd=w, env=ENV, capture_output=True, text=True, timeout=900)
    return r.stdout


rows = []
for iid in sorted(T):
    t = T[iid]
    d = CLONES / t["repo"].replace("/", "__")
    w = WT / iid
    if not (w / ".git").exists():
        print(iid, "no checkout")
        continue
    base = t["base_commit"]
    gl = changed_lines(t["patch"])
    gold = set()
    for f, ls in gl.items():
        for s, e in regions(ls):
            gold |= set(re.findall(r"^COMMIT (\w+)", git(d, "log", f"-L{s},{e}:{f}", "-n3", "--format=COMMIT %h", base), re.M))
    # A: names from the issue -> functions named like them
    outA, funcsA = "", []
    for nm in names_of(t["problem_statement"]):
        g = subprocess.run(["git", "grep", "-n", "-E", r"^[[:space:]]*(async[[:space:]]+)?(def|class)[[:space:]]+_?" + nm + r"([^A-Za-z0-9_]|$)", "--", "*.py"], cwd=w, env=ENV, capture_output=True, text=True).stdout
        hits = [l.split(":", 2) for l in g.splitlines() if not TEST.search(l.split(":", 1)[0])]
        for f, _, line in hits[:2]:
            fn = re.search(r"(def|class)\s+(\w+)", line).group(2)
            funcsA.append(f"{f}:{fn}")
            outA += f"== {f} {fn}\n" + func_log(w, f, fn)
        if len(funcsA) >= 3:
            break
    # O: the function holding each real-fix hunk
    outO, funcsO = "", []
    for f, ls in gl.items():
        p = w / f
        if not p.exists():
            continue
        lines = p.read_text(errors="replace").splitlines()
        for s, e in regions(ls)[:2]:
            fn = None
            for k in range(min(s, len(lines)) - 1, -1, -1):
                m = re.match(r"\s*(async\s+)?def\s+(\w+)", lines[k])
                if m:
                    fn = m.group(2)
                    break
            if fn and f"{f}:{fn}" not in funcsO:
                funcsO.append(f"{f}:{fn}")
                outO += f"== {f} {fn}\n" + func_log(w, f, fn)
    shA = set(re.findall(r"^commit (\w+) ", outA[:3500], re.M)) & gold
    shO = set(re.findall(r"^commit (\w+) ", outO[:3500], re.M)) & gold
    rows.append(dict(iid=iid, A=bool(shA), O=bool(shO), fa=bool(funcsA), fo=bool(funcsO), ca=len(outA), co=len(outO)))
    print(f"{iid[:44]:44} A {funcsA[:3]} shares {bool(shA)} chars {len(outA)} | O {funcsO[:2]} shares {bool(shO)} chars {len(outO)}", flush=True)

n = len(rows)
print(f"\ntasks {n} | A (issue names -> functions): a function found {sum(r['fa'] for r in rows)}, shows a real-fix-lines commit {sum(r['A'] for r in rows)}"
      f" | O (function holding the fix): found {sum(r['fo'] for r in rows)}, shows a real-fix-lines commit {sum(r['O'] for r in rows)}"
      f" | chars median A {sorted(r['ca'] for r in rows)[n // 2]} O {sorted(r['co'] for r in rows)[n // 2]} | line variant (Step 0b) for reference: 14/40")
