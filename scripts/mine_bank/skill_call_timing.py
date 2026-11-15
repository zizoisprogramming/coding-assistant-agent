"""Time a native run_command vs a skill call (run_skill_script) in the harness's DOCKER sandbox and in the SUBPROCESS
sandbox our notebooks use (2026-11-15, user "yes do so": test whether skill calls cost more on the scorer).
Run (repo root, Docker running, image swebench-sandbox:latest built from data/docker/Dockerfile.sandbox):
    data/venv_harness/bin/python scripts/mine_bank/skill_call_timing.py [N]

Uses the harness's own code: swegemma ContainerManager / get_sandbox (Docker; as the scorer's agent_runner) or
adk_eval_core SubprocessSandbox (as our notebooks), adk_eval_core AdkSandboxCodeExecutor (what run_skill_script
executes through), and google-adk's _SkillScriptCodeExecutor._build_wrapper_code (the self-extracting wrapper ADK
builds for a skill script). Workspace = a dummy git repo with a few files; no task code runs. Skills timed: sq1c2's
'work' shell (run.py, the heavy-use skill) and evidc's 'evidence' script, each with a trivial command / name."""
import asyncio, pathlib, statistics as st, sys, tempfile, time

N = int(sys.argv[1]) if len(sys.argv) > 1 else 15
ROOT = pathlib.Path(__file__).resolve().parents[2]
from google.adk.code_executors.code_execution_utils import CodeExecutionInput
from google.adk.skills._utils import _load_skill_from_dir
from google.adk.tools.skill_toolset import _SkillScriptCodeExecutor
from adk_eval_core.sandbox.base import AdkSandboxCodeExecutor

WS_FILES = {"pkg/__init__.py": "", "pkg/core.py": "def header_value(raw):\n    return raw\n", "README.md": "dummy\n"}
SKILLS = [("work", ROOT / "submissions/sq1c2/skills/work", "scripts/run.py", ["echo hi"]),
          ("evidence", ROOT / "submissions/evidc/skills/evidence", "scripts/evidence.py", ["header_value"])]


def timeit(fn, n):
    out = []
    for _ in range(n):
        t = time.perf_counter(); fn(); out.append(time.perf_counter() - t)
    return out


def bench(name, sandbox, n):
    ex = AdkSandboxCodeExecutor(sandbox=sandbox, timeout_seconds=120)
    rows = [("native run_command: echo", lambda: sandbox.run_command("echo hi", timeout=60)),
            ("native run_command: python3 -c", lambda: sandbox.run_command("python3 -c 'print(1)'", timeout=60)),
            ("native run_command: git status", lambda: sandbox.run_command("git status --short", timeout=60))]
    for sname, sdir, fpath, args in SKILLS:
        skill = _load_skill_from_dir(sdir)
        code = _SkillScriptCodeExecutor(ex, 120)._build_wrapper_code(skill, fpath, None, None, args)
        rows.append((f"skill call: {sname} ({len(code) // 1024} KB wrapper)", lambda c=code: ex.execute_code(None, CodeExecutionInput(code=c))))
    print(f"\n== {name} sandbox, {n} calls each (seconds per call)")
    res = {}
    for label, fn in rows:
        fn()  # warm-up
        t = timeit(fn, n)
        res[label] = st.median(t)
        print(f"  {label:44} median {st.median(t):6.3f}  mean {st.mean(t):6.3f}  max {max(t):6.3f}")
    return res


def docker_sandbox():
    from swegemma.sandbox.docker import ContainerConfig, ContainerManager
    mgr = ContainerManager(ContainerConfig())
    cid = mgr.start()
    sb = mgr.get_sandbox(cid, work_dir="/workspace")
    for p, c in WS_FILES.items():
        sb.write_file(p, c)
    sb.run_command("git init -q . && git add -A && git -c user.email=a@b -c user.name=t commit -qm init", timeout=60)
    return mgr, cid, sb


def subprocess_sandbox():
    from adk_eval_core.sandbox.subprocess_sandbox import SubprocessSandbox
    d = tempfile.mkdtemp(prefix="sktime_")
    sb = SubprocessSandbox(work_dir=d) if "work_dir" in SubprocessSandbox.__init__.__code__.co_varnames else SubprocessSandbox()
    sb.initialize(WS_FILES)
    sb.run_command("git init -q . && git add -A && git -c user.email=a@b -c user.name=t commit -qm init", timeout=60)
    return sb


if __name__ == "__main__":
    mgr, cid, dsb = docker_sandbox()
    try:
        d = bench("DOCKER (scorer)", dsb, N)
    finally:
        try:
            mgr.stop(cid)
        except Exception as e:  # noqa: BLE001
            print("stop failed:", e)
    s = bench("SUBPROCESS (our notebooks)", subprocess_sandbox(), N)
    print("\nextra cost of one skill call over a native call (median, s):")
    for label in d:
        if label.startswith("skill"):
            print(f"  {label:44} docker +{d[label] - d['native run_command: python3 -c']:.3f} vs python3 -c   |   subprocess +{s[label] - s['native run_command: python3 -c']:.3f}")
