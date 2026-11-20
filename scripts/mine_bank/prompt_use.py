"""Which parts of the sb1h-family prompt are used (user 2026-11-20: 'we need to work on this prompt size ... what is unrelated or
unused to drop it'). Read-only on r118-r121 requests of the arms whose prompt is sb1h's way of working (sb1h, sb1hpp, sbA, sbF,
sbF2). Per run: does the event or the behaviour each prompt part teaches ever happen, and how often.
Run: python3 -I scripts/mine_bank/prompt_use.py"""
import ast, collections, glob, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARMS = {"sb1h", "sb1hpp", "sbA", "sbF", "sbF2"}
DIRS = sorted(glob.glob(str(ROOT / "data/results/2026-11-19_skill_r1[12][890]_p*")) + glob.glob(str(ROOT / "data/results/2026-11-20_skill_r121_p*")))
solved = {}
for d in DIRS:
    for l in open(f"{d}/results/gen_per_task.jsonl"):
        g = json.loads(l)
        solved[(d, g["instance_id"], g["arm"])] = g["resolved"] in (True, "True")
runs = collections.defaultdict(list)
for d in DIRS:
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        try:
            r = json.loads(l)
        except Exception:
            continue
        arm = r["job"].split("#a")[1].split(".")[0]
        if arm in ARMS and len(r["request"]["messages"]) > 1:
            runs[(d, r["job"])].append(r)

EVENTS = {
    "result: old text found 0 times": re.compile(r"old text found 0 times"),
    "result: old text found 2+ times": re.compile(r"old text found ([2-9]|\d\d+) times"),
    "result: mandatory input parameters (cut-apart)": re.compile(r"mandatory input parameters are not present"),
    "result: Tool call budget exhausted": re.compile(r"Tool call budget exhausted"),
    "result: bash unexpected EOF (fenced command)": re.compile(r"unexpected EOF while looking for matching"),
}
CMDS = {
    "ex1 co-change list (git log --full-diff / --name-only)": re.compile(r"git log [^\n]*(--full-diff|--name-only)"),
    "ex1 git log --oneline of a file": re.compile(r"git log --oneline"),
    "any git log / git show / git blame": re.compile(r"\bgit (log|show|blame)\b"),
    "ex1/step3 tests found with git grep -l ... test": re.compile(r"git grep -l[n]? [^\n]*test"),
    "ex2 reproduce heredoc (python3 - <<)": re.compile(r"python3? - <<"),
    "step7 pytest run": re.compile(r"pytest"),
    "ex6 new source file (cat > X.py <<, not .git/agent / reproduce / test)": re.compile(r"(?m)^cat > (?!\.git/agent|/tmp|reproduce|test_|tests/|repro|check|debug|scratch)\S+\.py <<"),
    "step8 git status / git diff before submit": re.compile(r"git status --short|git diff\b(?! -U1)"),
    "heredoc edit": re.compile(r"OLD_TEXT"),
}
ev = collections.Counter()
evr = collections.Counter()
cm = collections.Counter()
cmr = collections.Counter()
tools = collections.Counter()
n = len(runs)
for (d, job), rs in runs.items():
    seen_e, seen_c = set(), set()
    for r in rs:
        last = r["request"]["messages"][-1]
        if last.get("role") == "tool":
            t = str(last.get("content"))
            for k, rx in EVENTS.items():
                if rx.search(t):
                    ev[k] += 1
                    seen_e.add(k)
        try:
            cs = (ast.literal_eval(str(r["reply"])).get("message") or {}).get("tool_calls") or []
        except Exception:
            cs = []
        for c in cs:
            tools[c["function"]["name"]] += 1
            try:
                a = json.loads(c["function"]["arguments"])
            except Exception:
                continue
            cmd = a.get("command", "") if c["function"]["name"] == "run_command" else ""
            for k, rx in CMDS.items():
                if cmd and rx.search(cmd):
                    cm[k] += 1
                    seen_c.add(k)
    for k in seen_e:
        evr[k] += 1
    for k in seen_c:
        cmr[k] += 1
print(f"runs {n} (arms {sorted(ARMS)}, r118-r121) | tool calls {dict(tools)}")
print("\nevents the prompt teaches (WHEN A TOOL RESULT SAYS + its example):")
for k in EVENTS:
    print(f"  {k:52} results {ev[k]:3} | runs {evr[k]:3}/{n} ({100 * evr[k] / n:.0f}%)")
print("\nbehaviours the prompt teaches:")
for k in CMDS:
    print(f"  {k:70} calls {cm[k]:4} | runs {cmr[k]:3}/{n} ({100 * cmr[k] / n:.0f}%)")
