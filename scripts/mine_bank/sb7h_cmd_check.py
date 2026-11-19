"""sb7h's one-call history command, taken from scripts/agent_sb7h/history.md, on the sparse *.py checkouts (scratchpad wt/)
with the names the model chose in r116 / r117's 32 history stages (single_cmd_precheck.py's run list). git / grep / sed /
sort / cut / awk only; nothing from the repositories is executed. Run: python3 -I scripts/mine_bank/sb7h_cmd_check.py CLONE_DIR
Per run: exit status, the last line (HISTORY FETCHED / NO HISTORY), chars, the picked functions, a real-fix function picked,
a shown commit that also changed the real-fix lines. Also once: the command wrapped in its fence lines (the error example 3 shows)."""
import json, re, subprocess, sys
from pathlib import Path

CLONES = Path(sys.argv[1])
src = open("scripts/mine_bank/single_cmd_precheck.py").read()
ns = {"__name__": "x"}
exec(src[:src.index("rows = []")].replace("CLONES = Path(sys.argv[1])", "CLONES = Path(" + repr(str(CLONES)) + ")"), ns)
runs, WT, T, AG = ns["runs"], ns["WT"], ns["T"], CLONES.parent / "agent_h7"
h = open("scripts/agent_sb7h/history.md").read()
CMD = re.findall(r"command:\n```\n(.*?)```", h, re.S)[0]
FIRST = "names='parse_config strict'\n"
assert CMD.startswith(FIRST)


def sh(cmd, w):
    r = subprocess.run(["/bin/bash", "-c", cmd.replace(".git/agent", str(AG))], cwd=w, env=ns["ENV"], capture_output=True, text=True, timeout=900)
    return r.returncode, r.stdout, r.stderr


n = ok = fn_hit = c_hit = 0
for run in runs:
    iid = run["iid"]
    w = WT / iid
    if not (w / ".git").exists() or not run["names"]:
        continue
    AG.mkdir(exist_ok=True)
    for p in AG.iterdir():
        p.unlink()
    names = " ".join(x.split(".")[-1] for x in run["names"].split())
    rc, out, err = sh(f"names='{names}'\n" + CMD[len(FIRST):], w)
    last = out.rstrip().splitlines()[-1] if out.strip() else ""
    good = rc == 0 and (last.startswith("== HISTORY FETCHED") or last.startswith("== NO HISTORY"))
    picked = set(tuple(x.split(" ", 1)) for x in re.findall(r"^== (\S+ \S+)$", out, re.M))
    shown = {x[:7] for x in re.findall(r"^commit ([0-9a-f]+)", out, re.M)}
    gf, gc = ns["gold_funcs"](T[iid]["patch"]), ns["gold_commits"](T[iid], CLONES / T[iid]["repo"].replace("/", "__"))
    n += 1
    ok += good
    fn_hit += bool(picked & gf)
    c_hit += bool(shown & gc)
    print(f"{run['src']} {iid[:30]:30} '{names[:30]:30}' rc {rc} {last[:22]:22} chars {len(out):5} picks {sorted(a.split('/')[-1] + ':' + b for a, b in picked)[:3]} fn {'Y' if picked & gf else '-'} commit {'Y' if shown & gc else '-'}", flush=True)
    if n == 1:
        rc2, out2, err2 = sh("```\n" + f"names='{names}'\n" + CMD[len(FIRST):] + "```", w)
        print("   fenced copy: rc", rc2, "| stderr", err2.strip()[:140])
print(f"\nruns {n} | ran and ended with its == line {ok} | real-fix function picked {fn_hit} | shows a real-fix-lines commit {c_hit}")
