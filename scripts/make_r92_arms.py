"""r92 arms evpipe, evloop, evroute (user 2026-11-12/13 "build all actually and i will run them, test them on 4 samples all
dev16, the solvable hard ones"): the three agent structures never built before (docs/PLAN.md NEW DIRECTION 2026-11-13).
Run: python3 scripts/make_r92_arms.py. All three keep evidc's evidence stage byte for byte (asserted).

evpipe  = a fixed pipeline (Agentless / Co-PatcheR style), SequentialAgent:
          evidence -> locator (fresh context; only tool the look skill: def / find / tests / show, refused after 6
          calls; replies LOCATION blocks with the exact code, output_key location) -> proposers (ParallelAgent of three
          TOOL-LESS agents, fresh context, T 0.2 / 0.7 / 1.0 + top_k 64; each replies SEARCH/REPLACE blocks, output_key
          prop_a/b/c: no tool calls -> no function events -> no ADK #4740 compaction crash, no call budget) -> applier
          (fresh context with the issue, evidence, location and the three proposals; evidc's tools; applies the change
          most proposals agree on, checks once, submits). Budget evidc's (29 calls, 8 min).
evloop  = rounds with fresh contexts, SequentialAgent: evidence -> LoopAgent (max_iterations 2) [attempt (fresh
          context: issue, evidence, the last round's report; tools: the act skill = one shell command per call, refused
          after 8 per round, and edit_file; ends with ROUND DONE, never submits), check (thinking off; calls check.py
          once: the source diff + the related existing tests' result; copies it, output_key report; advances the
          round)] -> finisher (submit_patch). 32 calls, 8 min.
evroute = routing by ADK's agent transfer (never used before): SequentialAgent: evidence -> router (thinking off,
          fresh context with the issue; sub_agents bug_fixer / feature_fixer / docs_fixer, one transfer_to_agent call)
          -> the specialist (evidc's tools and sampling, full history; a prompt written for its kind of task; no
          transfers back). Budget evidc's.
Every prompt written fresh (scripts/agent_struct/*.md), no budget numbers (asserted)."""
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / "submissions"
SRC = ROOT / "scripts/agent_struct"
EVIDC = SUB / "evidc"
MODEL = "gemma-4-31b-it-qat-w4a16-ct"
EVIDENCE_FILES = ["evidence.yaml", "prompts/evidence.md", "configs/evidence_sampling.yaml", "skills/evidence/SKILL.md",
                  "skills/evidence/scripts/evidence.py", "configs/sampling.yaml"]
FIXER_TOOLS = ["run_command", "read_file", "edit_file", "write_file", "get_status", "submit_patch"]


def files(d):
    return sorted(p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file() and "__pycache__" not in p.parts)


def no_budget(text, name):
    low = text.lower()
    assert "budget" not in low and "minute" not in low and not re.search(r"\b\d+\s*(tool\s*)?calls?\b|\bby call\b|\bcall \d+", low), name


def llm(name, desc, prompt, tools=None, skills=None, sampling="configs/sampling.yaml", include_none=False, output_key=None,
        sub_agents=None, no_transfer=False):
    y = [f"name: {name}", f"model: {MODEL}", f'description: "{desc}"', f"instruction: !include prompts/{prompt}"]
    if include_none:
        y.append("include_contents: none")
    if tools:
        y.append("tools:")
        y += [f"  - {t}" for t in tools]
    if skills:
        y.append("skills:")
        y += [f"  - skills/{s}" for s in skills]
    if sub_agents:
        y.append("sub_agents:")
        y += [f"  - config_path: {s}" for s in sub_agents]
    if no_transfer:
        y += ["disallow_transfer_to_parent: true", "disallow_transfer_to_peers: true"]
    if output_key:
        y.append(f"output_key: {output_key}")
    y.append(f"generate_content_config: !include {sampling}")
    return "\n".join(y) + "\n"


def seq(comment, name, cls, subs, extra=""):
    return (comment + f"name: {name}\nagent_class: {cls}\n" + extra + "sub_agents:\n" + "".join(f"  - config_path: {s}\n" for s in subs))


def sampling(t, top_k=None, thinking=True):
    s = f"temperature: {t}\ntop_p: 0.95\n" + (f"top_k: {top_k}\n" if top_k else "")
    if thinking:
        return s + "max_output_tokens: 8192\nthinking_config:\n  thinking_budget: 4096\n  include_thoughts: true\n"
    return s + "max_output_tokens: 1024\nthinking_config:\n  thinking_budget: 0\n  include_thoughts: false\n"


def eval_cfg(calls):
    return f"evaluation:\n  timeout_seconds: 240\n  max_tool_calls: {calls}\n  max_time_minutes: 8\n  max_turns: 80\n"


def skill(out, name, desc, body, scripts):
    d = out / "skills" / name
    (d / "scripts").mkdir(parents=True)
    (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: \"{desc}\"\n---\n\n{body}\n")
    for s in scripts:
        shutil.copy(SRC / s, d / "scripts" / s)


def start(name):
    out = SUB / name
    if out.exists():
        shutil.rmtree(out)
    out.mkdir()
    for f in EVIDENCE_FILES:
        (out / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(EVIDC / f, out / f)
    (out / "prompts").mkdir(exist_ok=True)
    return out


def prompt(out, name):
    text = (SRC / name).read_text()
    no_budget(text, name)
    (out / "prompts" / name).write_text(text)
    return text


def build_evpipe():
    out = start("evpipe")
    (out / "agent.yaml").write_text(seq("# evpipe (r92): evidence -> locator (look skill, refused after 6 calls) -> three tool-less proposers in parallel -> applier (scripts/make_r92_arms.py)\n",
                                        "swe_agent", "SequentialAgent", ["evidence.yaml", "locator.yaml", "proposers.yaml", "applier.yaml"]))
    (out / "locator.yaml").write_text(llm("locator", "Finds the exact code to change and copies it for the proposers.", "locator.md",
                                          tools=["get_status"], skills=["look"], include_none=True, output_key="location"))
    (out / "proposers.yaml").write_text(seq("", "proposers", "ParallelAgent", ["prop_a.yaml", "prop_b.yaml", "prop_c.yaml"],
                                            'description: "Three engineers propose a fix each, without tools."\n'))
    for x, t, k in (("a", 0.2, None), ("b", 0.7, None), ("c", 1.0, 64)):
        (out / f"prop_{x}.yaml").write_text(llm(f"prop_{x}", f"Proposes a fix ({x}) as SEARCH/REPLACE blocks, without tools.", "proposer.md",
                                                include_none=True, output_key=f"prop_{x}", sampling=f"configs/prop_{x}_sampling.yaml"))
        (out / f"configs/prop_{x}_sampling.yaml").write_text(f"# r92 evpipe proposer {x}\n" + sampling(t, k))
    (out / "applier.yaml").write_text(llm("applier", "Applies the best proposal, checks it once and submits.", "applier.md",
                                          tools=FIXER_TOOLS, include_none=True))
    for p in ("locator.md", "proposer.md", "applier.md"):
        prompt(out, p)
    skill(out, "look", "Read-only look-around for the locator: def / find / tests / show, a few calls.",
          'Call run_skill_script with skill_name look, file_path scripts/look.py and positional_args ["def", "NAME"], ["find", "TEXT"],\n["tests", "TEXT"] or ["show", "FILE", "START", "END"].',
          ["look.py"])
    (out / "eval_config.yaml").write_text(eval_cfg(29))
    return out


def build_evloop():
    out = start("evloop")
    (out / "agent.yaml").write_text(seq("# evloop (r92): evidence -> LoopAgent of 2 rounds [attempt (fresh context, act skill refused after 8 per round), check (diff + related tests)] -> finisher (scripts/make_r92_arms.py)\n",
                                        "swe_agent", "SequentialAgent", ["evidence.yaml", "rounds.yaml", "finisher.yaml"]))
    (out / "rounds.yaml").write_text(seq("", "rounds", "LoopAgent", ["attempt.yaml", "check.yaml"],
                                         'description: "Two rounds: an attempt in a fresh context, then a report of the diff and the related tests."\nmax_iterations: 2\n'))
    (out / "attempt.yaml").write_text(llm("attempt", "Makes or improves the fix in one round, from a fresh context and the last report.", "attempt.md",
                                          tools=["edit_file", "get_status"], skills=["act"], include_none=True))
    (out / "check.yaml").write_text(llm("check", "Reports the round's diff and the related tests.", "check.md", tools=["get_status"],
                                        skills=["check"], include_none=True, output_key="report", sampling="configs/evidence_sampling.yaml"))
    (out / "finisher.yaml").write_text(llm("finisher", "Submits the patch.", "finisher.md", tools=["submit_patch", "get_status"],
                                           include_none=True, sampling="configs/evidence_sampling.yaml"))
    for p in ("attempt.md", "check.md", "finisher.md"):
        prompt(out, p)
    skill(out, "act", "One shell command in the repository root per call; a few per round.",
          'Call run_skill_script with skill_name act, file_path scripts/act.py and positional_args holding one shell command.', ["act.py"])
    skill(out, "check", "The round report: the source diff and the related existing tests.",
          "Call run_skill_script with skill_name check and file_path scripts/check.py, with no other arguments.", ["check.py"])
    (out / "eval_config.yaml").write_text(eval_cfg(32))
    return out


def build_evroute():
    out = start("evroute")
    (out / "agent.yaml").write_text(seq("# evroute (r92): evidence -> router (one transfer_to_agent) -> bug_fixer / feature_fixer / docs_fixer (scripts/make_r92_arms.py)\n",
                                        "swe_agent", "SequentialAgent", ["evidence.yaml", "router.yaml"]))
    (out / "router.yaml").write_text(llm("router", "Hands the issue to the right specialist.", "router.md", include_none=True,
                                         sampling="configs/evidence_sampling.yaml",
                                         sub_agents=["bug_fixer.yaml", "feature_fixer.yaml", "docs_fixer.yaml"]))
    for n, d in (("bug_fixer", "Fixes bugs: something the code already does is wrong."),
                 ("feature_fixer", "Adds features: something the code does not do yet."),
                 ("docs_fixer", "Fixes documentation example code such as docs_src.")):
        (out / f"{n}.yaml").write_text(llm(n, d, f"{n}.md", tools=FIXER_TOOLS, no_transfer=True))
        prompt(out, f"{n}.md")
    prompt(out, "router.md")
    (out / "eval_config.yaml").write_text(eval_cfg(29))
    return out


if __name__ == "__main__":
    for b in (build_evpipe, build_evloop, build_evroute):
        o = b()
        for f in EVIDENCE_FILES:
            assert (o / f).read_bytes() == (EVIDC / f).read_bytes(), (o.name, f)
        print("wrote", o.relative_to(ROOT), "|", files(o))
