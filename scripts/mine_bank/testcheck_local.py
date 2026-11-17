"""Local, git-only test of the test-picking command (scripts/agent_tc/testsel_cmd.sh) on the bank patches of the CPU
check: in blob-less clones of the test repos (no repository code runs; the command's last line, the pytest run, is
replaced by an echo; git with hooks and fsmonitor off). Per patch: the files picked; whether a picked file is a file the
hidden tests live in (from test_patch). Run: python3 -I scripts/mine_bank/testcheck_local.py CLONES_DIR"""
import collections, json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import testcheck_patches as tp

clones = sys.argv[1]
cmd = open("scripts/agent_tc/testsel_cmd.sh").read().rstrip("\n").split("\n")
assert cmd[-1].startswith("timeout 150 python -m pytest")
cmd = "\n".join(cmd[:-1] + ["echo PYTEST_WOULD_RUN $files"])
env = dict(os.environ, GIT_CONFIG_COUNT="2", GIT_CONFIG_KEY_0="core.hooksPath", GIT_CONFIG_VALUE_0="/dev/null",
           GIT_CONFIG_KEY_1="core.fsmonitor", GIT_CONFIG_VALUE_1="false", GIT_PAGER="cat")
out, gold = tp.collect()
rows = []
for iid in sorted(gold):
    g = gold[iid]
    repo = os.path.join(clones, g["repo"].replace("/", "__"))
    run = lambda *a, **k: subprocess.run(a, cwd=repo, env=env, capture_output=True, text=True, **k)
    hidden = set(re.findall(r"^\+\+\+ b/(\S+)", g["test_patch"], re.M))
    for c in [dict(iid=iid, kind="gold", arm="-", patch=g["patch"])] + [c for c in out if c["iid"] == iid]:
        run("git", "checkout", "-q", "-f", g["base_commit"]); run("git", "clean", "-fdq"); run("rm", "-rf", ".git/agent")
        a = run("git", "apply", "--whitespace=nowarn", "-", input=c["patch"])
        if a.returncode:
            rows.append(dict(iid=iid, kind=c["kind"], picked=None, err="apply: " + a.stderr[:100])); continue
        o = run("/bin/bash", "-c", cmd)
        m = re.search(r"^== TESTS THAT USE THEM: ?(.*)$", o.stdout, re.M)
        picked = m.group(1).split() if m else []
        rows.append(dict(iid=iid, kind=c["kind"], picked=picked, hit=bool(set(picked) & hidden), err=o.stderr.strip()[:200],
                         noedit="No source file is edited yet" in o.stdout))
    run("git", "checkout", "-q", "-f", g["base_commit"]); run("git", "clean", "-fdq"); run("rm", "-rf", ".git/agent")
    r0 = [r for r in rows if r["iid"] == iid]
    print(f"{iid[:46]:46} gold picks {r0[0]['picked']} hit={r0[0].get('hit')} | patches {len(r0) - 1}: some test picked {sum(bool(r['picked']) for r in r0[1:])}, "
          f"hidden-test file picked {sum(bool(r.get('hit')) for r in r0[1:])}, no source edit {sum(bool(r.get('noedit')) for r in r0[1:])}, errors {sum(bool(r['err']) for r in r0)}", flush=True)
for k in ("gold", "solved", "wrong"):
    x = [r for r in rows if r["kind"] == k]
    print(f"{k:6} {len(x):3}: some test picked {sum(bool(r['picked']) for r in x)}, hidden-test file among the picks {sum(bool(r.get('hit')) for r in x)}, "
          f"apply failed {sum((r['err'] or '').startswith('apply') for r in x)}, stderr {sum(bool(r['err']) and not r['err'].startswith('apply') for r in x)}")
errs = collections.Counter(r["err"][:80] for r in rows if r["err"])
print("errors:", errs.most_common(5))
