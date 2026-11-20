"""Sizes r128's B losses over the heredoc-edit bank (r110-r128): (1) replies whose tool call came out as text: how many, in how many
runs, how many end with the examples' ``` fence, what the next request says, and whether the run then ended without a patch;
(2) runs that wiped their own source edit (git checkout / stash / reset --hard / restore after an applied edit) and whether the final
patch kept a source change. Run: python3 -I scripts/mine_bank/b_losses.py"""
import ast, collections, glob, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TXT = re.compile(r"<\|tool_call>|call:run_command|call:read_file")
WIPE = re.compile(r"git (checkout( -f)? (HEAD|-- |\.|[\w/]+\.py)|stash|reset --hard|restore )")
tx = tx_fence = tx_runs = tx_runs_nopatch = 0
wipe_runs = wipe_lost = 0
nxt = collections.Counter()
runs = 0
for d in sorted(glob.glob(str(ROOT / "data/results/2026-11-*_skill_r1[12][0-9]_p*"))):
    f = Path(d) / "requests/requests.jsonl"
    if not f.exists():
        continue
    G = {}
    for gp in glob.glob(f"{d}/results/gen_per_task.jsonl"):
        for l in open(gp):
            g = json.loads(l); G[(g["instance_id"], g["arm"])] = g
    by = collections.defaultdict(list)
    for l in open(f, errors="replace"):
        try:
            r = json.loads(l)
        except Exception:
            continue
        if len(r["request"]["messages"]) > 1:
            by[r["job"]].append(r)
    for job, rs in by.items():
        runs += 1
        rs.sort(key=lambda r: float(r["t"]))
        iid, arm = job.split("#")[0], job.split("#a")[1].split(".")[0]
        g = G.get((iid, arm), {})
        patch = (Path(d) / f"results/gen/patches/{iid}__a{job.split('#a')[1]}.diff")
        src_in_patch = patch.exists() and any(l.startswith("diff --git") and "test" not in l and "reproduc" not in l for l in patch.read_text(errors="replace").splitlines())
        t_here = 0; edited = False; wiped = False
        for i, r in enumerate(rs):
            try:
                m = ast.literal_eval(str(r["reply"])).get("message") or {}
            except Exception:
                continue
            c = m.get("content") or ""
            if not m.get("tool_calls") and TXT.search(c):
                tx += 1; t_here += 1
                tx_fence += "```" in c[-40:]
                if i + 1 < len(rs):
                    u = str(rs[i + 1]["request"]["messages"][-1].get("content"))[:60]
                    nxt[u] += 1
            for cl in m.get("tool_calls") or []:
                try:
                    cmd = json.loads(cl["function"]["arguments"]).get("command", "")
                except Exception:
                    cmd = ""
                if edited and WIPE.search(cmd):
                    wiped = True
            if i and "EDITED " in str(r["request"]["messages"][-1].get("content")):
                edited = True
        if t_here:
            tx_runs += 1; tx_runs_nopatch += not src_in_patch
        if wiped:
            wipe_runs += 1; wipe_lost += not src_in_patch
print(f"runs {runs}")
print(f"(1) text-form tool calls: {tx} replies in {tx_runs} runs; ending with the ``` fence {tx_fence}; runs with text calls that ended with no source change in the patch {tx_runs_nopatch}")
print("    next message after a text call:", nxt.most_common(4))
print(f"(2) runs that wiped an applied source edit with git checkout / stash / reset / restore: {wipe_runs}; of them ended with no source change in the patch: {wipe_lost}")
