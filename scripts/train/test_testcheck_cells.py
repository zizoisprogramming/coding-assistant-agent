"""Dry run of kaggle/cells_testcheck_rt cell3_check.py + cell4_summary.py with a FAKE harness (crash-path audit before
the hand-off). Run: python3 -I scripts/train/test_testcheck_cells.py CLONES_DIR [N_TASKS]

The fake verify_task checks out the task's base in a local blob-less clone, applies the patch with git apply and calls
sandbox_exec with a '--junitxml=' pytest command, as the scorer's verify_task does; the fake sandbox_exec runs the
command with bash in the clone (/workspace -> the clone) but never runs pytest (repository code): every
'python -m pytest' is replaced by canned output (with the patch: one failure in the first picked file; at the base:
all pass), so NEW failures, the base cache, the stash, the per-patch lines and the summary are all exercised."""
import asyncio, collections, json, os, re, subprocess, sys, tempfile, time, types
from collections import Counter
from pathlib import Path

clones = sys.argv[1]
n_tasks = int(sys.argv[2]) if len(sys.argv) > 2 else 4
ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "kaggle/cells_testcheck_rt"
GIT_ENV = dict(os.environ, GIT_CONFIG_COUNT="2", GIT_CONFIG_KEY_0="core.hooksPath", GIT_CONFIG_VALUE_0="/dev/null",
               GIT_CONFIG_KEY_1="core.fsmonitor", GIT_CONFIG_VALUE_1="false", GIT_PAGER="cat")
cands = {json.loads(l)["instance_id"]: json.loads(l) for l in open(ROOT / "data/swe_rebench/candidates.jsonl")}
STATE = {"base": False}


class R:
    def __init__(self, code, out, err=""):
        self.exit_code, self.stdout, self.stderr = code, out, err


def fake_exec_sync(sid, command, timeout=None):
    repo = sid
    cmd = command.replace("/workspace", repo)
    if "python -m pytest" in cmd:
        lines = cmd.split("\n")
        for k, l in enumerate(lines):
            if "python -m pytest" in l:
                if l.startswith("timeout 150 python -m pytest $files"):  # the agent command, patched tree
                    lines[k] = "echo 'FAILED '$(echo $files | cut -d' ' -f1)'::test_x - AssertionError: boom'; echo '1 failed, 4 passed in 0.31s'"
                else:  # the base run
                    lines[k] = "cd " + repo + " && echo '5 passed in 0.30s'"
        cmd = "\n".join(lines)
    p = subprocess.run(["/bin/bash", "-c", cmd], cwd=repo, env=GIT_ENV, capture_output=True, text=True, timeout=timeout or 300)
    return R(p.returncode, p.stdout, p.stderr)


async def sandbox_exec(docker, sid, command, *, timeout=None):
    return await asyncio.to_thread(fake_exec_sync, sid, command, timeout)


async def verify_task(docker, cfg, task, snap, *, agent_patch="", start_time=0.0):
    c = cands[task.instance_id]
    repo = os.path.join(clones, c["repo"].replace("/", "__"))
    run = lambda *a, **k: subprocess.run(a, cwd=repo, env=GIT_ENV, capture_output=True, text=True, **k)
    run("git", "stash", "clear"); run("git", "checkout", "-q", "-f", c["base_commit"]); run("git", "clean", "-fdq"); run("rm", "-rf", ".git/agent")
    if agent_patch.strip():
        a = run("git", "apply", "--whitespace=nowarn", "-", input=agent_patch)
        if a.returncode:
            return types.SimpleNamespace(error="Failed to apply agent patch: " + a.stderr[:200], resolved=False)
    V = sys.modules["swegemma.harness.verification"]
    res = await V.sandbox_exec(docker, repo, "cd /workspace && python3 -s -m pytest . --junitxml=/tmp/x.xml -q")
    return types.SimpleNamespace(error=None if res.exit_code == 0 else "tests failed", resolved=res.exit_code == 0)


def mod(name, **kw):
    m = types.ModuleType(name)
    m.__dict__.update(kw)
    sys.modules[name] = m
    return m


mod("swegemma"); mod("swegemma.harness")
mod("swegemma.harness.verification", sandbox_exec=sandbox_exec, verify_task=verify_task)
mod("swegemma.config", EvalConfig=lambda **k: types.SimpleNamespace(**k))
mod("swegemma.evaluate", Evaluator=lambda cfg: types.SimpleNamespace(docker="fake-docker", config=cfg))
mod("swegemma.models", Task=lambda **k: types.SimpleNamespace(**k))
mod("adk_submission", ModelRegistry=lambda: None)

src2 = (D / "cell2.py").read_text()
ids = eval(re.search(r"^TASK_SET = (.*)$", src2, re.M).group(1))
pick = [i for i in ids if os.path.isdir(os.path.join(clones, cands[i]["repo"].replace("/", "__")))][:n_tasks]
tmp = Path(tempfile.mkdtemp())
G = dict(__name__="__main__", collections=collections, Counter=Counter, json=json, re=re, time=time, Path=Path, os=os,
         ROWS={i: cands[i] for i in pick}, RESULTS=tmp, T_START=time.time(), STOP_NEW_TASKS_AFTER_H=9.0, OUT=tmp, DATA_DIR=tmp,
         WHEEL_ROOT=tmp, WHEEL_SET="x", RUNNING={}, clean_tmp=lambda: None, import_name=lambda r: "pkg",
         CUR_TASK=__import__("contextvars").ContextVar("t", default=None), ood=types.SimpleNamespace(IMPORT_NAMES={}))
c3 = (D / "cell3_check.py").read_text()
before = len(c3)
c3 = c3.replace("PATCHES = json.loads(", "PATCHES = [p for p in json.loads(", 1)
c3 = c3.replace(".decode())\n", ".decode()) if p['iid'] in ROWS][:40]\n", 1)
assert len(c3) != before
exec(compile(c3, "cell3_check.py", "exec"), G)
exec(compile((D / "cell4_summary.py").read_text(), "cell4_summary.py", "exec"), G)
rows = [json.loads(l) for l in open(tmp / "testcheck.jsonl")]
assert rows and all(r["fired"] or r["apply_error"] for r in rows), "hook did not fire"
picked = [r for r in rows if r["files"]]
assert all(r["new_fail"] for r in picked), "canned failure not detected as NEW"
print(f"\nDRY RUN OK: {len(rows)} rows, {len(picked)} with picks, all picked rows show the canned NEW failure; base runs cached per task + file set")
for i in pick:  # leave the clones clean
    repo = os.path.join(clones, cands[i]["repo"].replace("/", "__"))
    subprocess.run(["git", "stash", "clear"], cwd=repo, env=GIT_ENV)
    subprocess.run(["git", "checkout", "-q", "-f", cands[i]["base_commit"]], cwd=repo, env=GIT_ENV)
    subprocess.run(["git", "clean", "-fdq"], cwd=repo, env=GIT_ENV)
