"""r90 arms evval and evteam (user 2026-11-12 "i want to try everything": both leads left in
docs/RESEARCH_PROBLEMS_2026-11-12.md). Run: python3 scripts/make_r90_arms.py

evval  = evtrace2 (the arm whose fixers used the code-path tool in 6/6 runs, r85) with the tool's runtime evidence:
         scripts/agent_trace/trace_v3.py lists, per repository function the check ran, the lines that ran and the first
         call's arguments -> returned value (or the exception), plus the locals where a failing check raised
         (SWE-Doctor, arXiv 2607.00990: runtime values and the executed branch). Changed: the embedded TRACE_SOURCE,
         the how-to line under the evidence header (it names the new output), the fixer prompt (written fresh around
         the new output: scripts/agent_trace/fixer_val.md) and the agent.yaml comment; the rest is evtrace2's byte for
         byte (asserted). Note: 112 of 129 public issues hold no code at all (CHECK 2026-11-12), so the check script is
         usually the fixer's own guess at the bug.
evteam = the crash-free wait-for-all team (RACE INVESTIGATION step 2): SequentialAgent [evidence (evidc's stage; its
         script also makes Fixer B's copy .git/agent/wt_b, a clean baseline /tmp/team/wt_0 and .git/agent/vote.py),
         coordinator (thinking off; tools: agent_tool team, the team skill's vote.py, get_status, submit_patch)];
         team = ParallelAgent [fix_a (works in /workspace), fix_b (works in wt_b)], inside the AgentTool so the child
         session has no compaction (no ADK #4740 crash). Each fixer's last call is `vote.py done a|b`; the second one
         runs the vote (the 2026-10-29 picker rules: drop a patch that breaks more existing tests than no patch, then
         the fixers' own /tmp checks, ties -> A; A empty -> B) and leaves the winner in /workspace; the coordinator
         votes again only if something changed, then submits. The vote lives in the fixers' own calls because the
         call budget is shared and only submit_patch / get_status are free (swegemma tools/execution.py), so a vote
         after the team returns would be refused in the common case. Fixers declare submit_patch (an undeclared call
         raises in ADK 1.36.1 functions._get_tool and kills the task; the harness warning names submit_patch) but are
         told the coordinator submits. Budget: 50 calls (evidence 1 + fixers ~24 each + vote 1), 160 turns, 8 min.
         Fixer sampling: evidc's (T 0.2, top_p 0.95, thinking 4096) with max output 6144 instead of 8192: the child
         session never compacts, and a request over max_model_len 32,768 (prompt + max output) kills the whole task.
         Fixer prompts written fresh from evidc's procedure (no budget numbers); the issue and the evidence are in
         their instructions (inside an AgentTool a fixer sees only the coordinator's request text)."""
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / "submissions"
SCRIPT_REL, PROMPT_REL = "skills/evidence/scripts/evidence.py", "prompts/fixer.md"
MODEL = "gemma-4-31b-it-qat-w4a16-ct"
OLD_HINT = (" after the script's own output it lists the functions of this repository the check went through, with line ranges.")
NEW_HINT = (" after the script's own output it lists the functions of this repository the check went through, with line ranges,"
            " the lines that ran and the first call's arguments -> returned value.")


def files(d):
    return sorted(p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file() and "__pycache__" not in p.parts)


def no_budget(p, name):
    low = p.lower()
    assert "budget" not in low and "minute" not in low and not re.search(r"\b\d+\s*(tool\s*)?calls?\b|\bby call\b|\bcall \d+", low), name


def build_evval():
    parent, out = SUB / "evtrace2", SUB / "evval"
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(parent, out, ignore=shutil.ignore_patterns("__pycache__"))
    ev = (parent / SCRIPT_REL).read_text()
    v3 = (ROOT / "scripts/agent_trace/trace_v3.py").read_text()
    ev2, n = re.subn(r"^TRACE_SOURCE = .*$", lambda m: "TRACE_SOURCE = " + repr(v3), ev, count=1, flags=re.M)
    assert n == 1
    assert ev2.count(OLD_HINT) == 1
    ev2 = ev2.replace(OLD_HINT, NEW_HINT, 1)
    compile(ev2, SCRIPT_REL, "exec")
    (out / SCRIPT_REL).write_text(ev2)
    p = (ROOT / "scripts/agent_trace/fixer_val.md").read_text()
    assert "{evidence?}" in p and "== CODE PATH" in p and "ran 312-315" in p
    no_budget(p, "fixer_val.md")
    (out / PROMPT_REL).write_text(p)
    first, rest = (parent / "agent.yaml").read_text().split("\n", 1)
    assert first.startswith("# evtrace2 (r85)")
    (out / "agent.yaml").write_text("# evval (r90): evtrace2 + the code-path tool's runtime evidence (lines that ran, first-call args -> returned, locals where it raised) + a fixer prompt written around it (scripts/make_r90_arms.py)\n" + rest)
    assert files(out) == files(parent)
    for f in files(parent):
        if f not in (SCRIPT_REL, PROMPT_REL, "agent.yaml"):
            assert (out / f).read_bytes() == (parent / f).read_bytes(), f
    # the script differs from evtrace2's only in the embedded tool and the hint line
    a, b = ev.splitlines(), ev2.splitlines()
    assert len(a) == len(b) and sum(x != y for x, y in zip(a, b)) == 2, sum(x != y for x, y in zip(a, b))
    return out


AGENT = """# evteam (r90): evidc's evidence stage + a coordinator whose one tool is a two-fixer team (AgentTool around a ParallelAgent: no shared-session compaction crash); the fixers' done calls run a test vote (scripts/make_r90_arms.py)
name: swe_agent
agent_class: SequentialAgent
sub_agents:
  - config_path: evidence.yaml
  - config_path: coordinator.yaml
"""
COORD = f"""name: coordinator
model: {MODEL}
description: Runs the two-fixer team once, makes sure the voted patch is in /workspace, and submits it.
instruction: !include prompts/coordinator.md
tools:
  - get_status
  - submit_patch
  - agent_tool:
      config_path: team.yaml
skills:
  - skills/team
generate_content_config: !include configs/coordinator_sampling.yaml
"""
TEAM = """name: team
agent_class: ParallelAgent
description: Two engineers fix the issue at the same time, each on their own; a test vote keeps the better patch.
sub_agents:
  - config_path: fix_a.yaml
  - config_path: fix_b.yaml
"""
FIXER = """name: {name}
model: {model}
description: "{desc}"
instruction: !include prompts/{name}.md
tools:
  - run_command
  - read_file
  - edit_file
  - write_file
  - get_status
  - submit_patch  # declared although the prompt says the coordinator submits: an undeclared call raises in ADK and kills the task
generate_content_config: !include configs/fixer_sampling.yaml
"""
FIXER_SAMPLING = """# r90 evteam fixers: evidc's fixer sampling with max output 6144 (was 8192): inside the AgentTool the session never
# compacts, and a request whose prompt + max output passes max_model_len 32,768 kills the whole task.
temperature: 0.2
top_p: 0.95
max_output_tokens: 6144
thinking_config:
  thinking_budget: 4096
  include_thoughts: true
"""
COORD_SAMPLING = """# r90 evteam coordinator: thinking off (thinking_budget 0, as evidc's evidence stage); three fixed calls.
temperature: 0.2
top_p: 0.95
max_output_tokens: 1024
thinking_config:
  thinking_budget: 0
  include_thoughts: false
"""
TEAM_SKILL = """---
name: team
description: The two-fixer team's vote. Call run_skill_script with skill_name team and file_path scripts/vote.py, with no other arguments, after the team returns.
---

Call run_skill_script with skill_name team and file_path scripts/vote.py, with no other arguments. It makes sure the
better of the two fixers' patches is in /workspace and prints which one was kept.
"""
EVAL = """evaluation:
  timeout_seconds: 240
  max_tool_calls: 50
  max_time_minutes: 8
  max_turns: 160
"""


def build_evteam():
    parent, out = SUB / "evidc", SUB / "evteam"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir()
    for f in ("evidence.yaml", "prompts/evidence.md", "configs/evidence_sampling.yaml", "skills/evidence/SKILL.md"):
        (out / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(parent / f, out / f)
    vote = (ROOT / "scripts/agent_team/vote.py").read_text()
    ev = (ROOT / "scripts/agent_team/evidence_team.py").read_text()
    ev, n1 = re.subn(r"^TEAM_SETUP = False", "TEAM_SETUP = True", ev, count=1, flags=re.M)
    ev, n2 = re.subn(r"^VOTE_SOURCE = ''", lambda m: "VOTE_SOURCE = " + repr(vote), ev, count=1, flags=re.M)
    assert n1 == n2 == 1
    compile(ev, SCRIPT_REL, "exec")
    (out / SCRIPT_REL).parent.mkdir(parents=True, exist_ok=True)
    (out / SCRIPT_REL).write_text(ev)
    # evidc's script + the team set-up only: every evidc line is still there, in order
    old = (parent / SCRIPT_REL).read_text().splitlines()
    new = ev.splitlines()
    it = iter(new)
    assert all(any(l == m for m in it) for l in old if not l.startswith('"""') and "start = time.time()" not in l)
    (out / "agent.yaml").write_text(AGENT)
    (out / "coordinator.yaml").write_text(COORD)
    (out / "team.yaml").write_text(TEAM)
    for name, desc in (("fix_a", "Fixer A: fixes the issue in /workspace, then hands its patch to the vote."),
                       ("fix_b", "Fixer B: fixes the issue in its own copy (.git/agent/wt_b), then hands its patch to the vote.")):
        (out / f"{name}.yaml").write_text(FIXER.format(name=name, model=MODEL, desc=desc))
        p = (ROOT / f"scripts/agent_team/{name}.md").read_text()
        assert "{problem_description}" in p and "{evidence?}" in p and f"vote.py done {name[-1]}" in p
        no_budget(p, name)
        (out / "prompts").mkdir(exist_ok=True)
        (out / f"prompts/{name}.md").write_text(p)
    c = (ROOT / "scripts/agent_team/coordinator.md").read_text()
    no_budget(c, "coordinator")
    (out / "prompts/coordinator.md").write_text(c)
    (out / "configs/fixer_sampling.yaml").write_text(FIXER_SAMPLING)
    (out / "configs/coordinator_sampling.yaml").write_text(COORD_SAMPLING)
    (out / "skills/team/scripts").mkdir(parents=True)
    (out / "skills/team/SKILL.md").write_text(TEAM_SKILL)
    v2 = vote.replace("MODE = None  #", "MODE = 'final'  #", 1)
    assert v2 != vote
    (out / "skills/team/scripts/vote.py").write_text(v2)
    (out / "eval_config.yaml").write_text(EVAL)
    return out


if __name__ == "__main__":
    for b in (build_evval, build_evteam):
        o = b()
        print("wrote", o.relative_to(ROOT), "|", files(o))
