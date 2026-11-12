"""r85 arms evtrace2 and evgraph (user 2026-11-12 after r84: "favor few shot man if it helps and we try again, make this strategy see the
fixes that can be applied, tool, prompt, etc."). Run: python3 scripts/make_r85_arms.py

r84 (docs/PLAN.md RESULT r84): evtrace 3/6, evall 1/6, evidefs 0/6, evmap 0/6 on 3 mid-rate tasks x 2 notebooks; the
code-path tool was used once in 12 runs while the fixers ran 18-30 plain Python checks per arm (they copied the prompt's
plain heredoc / /tmp example); the MAP was copied only where it was right (fastapi_14419) and points at the wrong file on
rich_4079 -> dropped this round. Fixes, one per mechanism:
  tool use   few-shot: every example that runs Python goes through .git/agent/trace.py (scripts/agent_trace/fixer_trace2.md,
             written fresh; no budget numbers) + a how-to line under the evidence header (evidence_r85.py TRACE_HINT).
  tool output the modules the check script imports are listed first, after a 'files:' line (scripts/agent_trace/trace.py).
evtrace (r84's bundle, unchanged) runs again next to it to replicate the prompt effect; evidefs is the control.
evgraph (user 2026-11-12 "yes go for option 2") = evtrace2 + the evidence script's GRAPH: for each named def, 'called from'
(the defs holding its calls) and 'it calls' (repository defs its body calls), the research-style neighbours (ARISE, CoSIL)
instead of r84's plain map. Offline (scripts/mine_bank/graph_offline.py, the same rule for lines and ranges): the evidence
names the real fix's function in 36% -> 40% of 72 tasks, 27% -> 47% of the 15 with the real stage's names (adds
fastapi_14419 and rich_3521); 0 crashes, <= 1.7 s. Both arms are built from evidence_r86.py (GRAPH off for evtrace2: the
same behaviour as r85's script), so they differ only in GRAPH.
Everything except the evidence script, the fixer prompt and the agent.yaml comment is evidefs's byte for byte (asserted)."""
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / "submissions"
PARENT = SUB / "evidefs"
SCRIPT = ROOT / "scripts/agent_evidence/evidence_r86.py"
TRACE = ROOT / "scripts/agent_trace/trace.py"
PROMPT = ROOT / "scripts/agent_trace/fixer_trace2.md"
SCRIPT_REL, PROMPT_REL = "skills/evidence/scripts/evidence.py", "prompts/fixer.md"
ARMS = {
    "evtrace2": (False, "# evtrace2 (r85): evidefs + the code-path tool (imports listed first) + a fixer prompt whose every Python run goes through it + the how-to line in the evidence (scripts/make_r85_arms.py)\n"),
    "evgraph": (True, "# evgraph (r85): evtrace2 + the evidence script's call-graph neighbours of each named def (called from / it calls) (scripts/make_r85_arms.py)\n"),
}


def files(d):
    return sorted(p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file() and "__pycache__" not in p.parts)


def script(graph):
    s = SCRIPT.read_text()
    for k, v in (("MAP", False), ("TRACE", True), ("TRACE_HINT", True), ("GRAPH", graph)):
        s, n = re.subn(rf"^{k} = \S+", f"{k} = {v!r}", s, flags=re.M)
        assert n == 1, k
    s, n = re.subn(r"^TRACE_SOURCE = ''", lambda m: "TRACE_SOURCE = " + repr(TRACE.read_text()), s, count=1, flags=re.M)
    assert n == 1
    return s


def check_prompt(p):
    assert "{evidence?}" in p and "== CODE PATH" in p
    low = p.lower()
    assert "budget" not in low and "minute" not in low, "no budget words in prompts (user rule 2026-11-10)"
    assert not re.search(r"\b\d+\s*(tool\s*)?calls?\b|\bby call\b|\bcall\s+\d+", low), "no call counts or call plans"
    # every example that runs Python goes through the tool: no plain 'python3 -' heredoc, no 'python3 /tmp/...'
    assert not re.search(r"(?m)^\s*python3? (-|/tmp/)", p), "a Python example outside the code-path tool"
    assert p.count("python3 .git/agent/trace.py") >= 4


def build(name, graph, comment):
    out = SUB / name
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(PARENT, out, ignore=shutil.ignore_patterns("__pycache__"))
    (out / SCRIPT_REL).write_text(script(graph))
    p = PROMPT.read_text()
    check_prompt(p)
    (out / PROMPT_REL).write_text(p)
    first, rest = (PARENT / "agent.yaml").read_text().split("\n", 1)
    assert first.startswith("# evidefs (r82)")
    (out / "agent.yaml").write_text(comment + rest)
    assert files(out) == files(PARENT)
    for f in files(PARENT):
        if f not in (SCRIPT_REL, PROMPT_REL, "agent.yaml"):
            assert (out / f).read_bytes() == (PARENT / f).read_bytes(), f
    s = (out / SCRIPT_REL).read_text()
    assert "MAP = False" in s and "TRACE = True" in s and "TRACE_HINT = True" in s and f"GRAPH = {graph!r}" in s and "def script_files()" in s and "ONCE = True" in s
    compile(s, SCRIPT_REL, "exec")
    return out


outs = {name: build(name, graph, comment) for name, (graph, comment) in ARMS.items()}
a, b = ((outs[n] / SCRIPT_REL).read_text() for n in ("evtrace2", "evgraph"))
assert a.replace("GRAPH = False", "GRAPH = True", 1) == b  # evtrace2 and evgraph differ only in the GRAPH switch
assert (outs["evtrace2"] / PROMPT_REL).read_bytes() == (outs["evgraph"] / PROMPT_REL).read_bytes()
# evtrace runs again exactly as in r84 (bundle committed in 14523dd): its script still embeds the r84 tool
ev = (SUB / "evtrace" / SCRIPT_REL).read_text()
assert "TRACE = True" in ev and "def script_files()" not in ev and (SUB / "evtrace" / PROMPT_REL).read_text() == (ROOT / "scripts/agent_trace/fixer_trace.md").read_text()
for n, o in outs.items():
    print("wrote", o.relative_to(ROOT), "|", files(o))
