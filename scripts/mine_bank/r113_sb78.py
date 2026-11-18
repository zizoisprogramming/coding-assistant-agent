"""r113: sb1 vs sb7 (one-call history stage at the issue names' lines, pinned in the fixer prompt) vs sb8 (explore ->
one-call history of the chosen lines -> editor). 4 tasks x 2 passes. Checks the bars of docs/PLAN.md RUN BUILT r113.
Run: python3 -I scripts/mine_bank/r113_sb78.py   (repo root; logs only)

Stage of each request from its system prompt. Per run: outcome, end, agent time, replies, first edit (call, s), patch;
per stage: requests, model seconds. History stages: the run_command output vs the reply (copied exactly? chars), the
history pinned in the next stage's system prompt (chars, 'commit ' lines), whether the pinned lines / file are the
real-fix ones. sb8: explorer handed over (FILE / LINES / CHANGE / CHECK reply), on the warning or not, chosen lines vs
real-fix lines, editor reached, editor's calls before its first edit."""
import collections, glob, json, re, statistics as st

import sys
DIRS = sorted(glob.glob(sys.argv[1] if len(sys.argv) > 1 else "data/results/2026-11-18_skill_sb78h4_p*"))  # r114: 'data/results/2026-11-1*_skill_sb7sh4_p*'
TEST = re.compile(r"(^|/)(tests?|testing)/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$")
GOLD = {}
for f in ("data/swe_rebench/candidates.jsonl", "data/tasks.jsonl"):
    for l in open(f):
        j = json.loads(l)
        GOLD[j["instance_id"]] = j["patch"]
STAGE = [("sb7", "history", "You run one command before the engineer starts"), ("sb7", "fixer", "# HOW THIS CODE CHANGED BEFORE"),
         ("sb7f", "history", "You run two commands before the engineer starts"), ("sb7f", "fixer", "# HOW THE FUNCTIONS OF THIS ISSUE CHANGED BEFORE"),
         ("sb7s", "history", "You run one command before the engineer starts"), ("sb7s", "fixer", "# HOW THIS CODE CHANGED BEFORE"),
         ("sb8", "explore", "You are the first of two software engineers"), ("sb8", "history", "You run one command between two engineers"),
         ("sb8", "editor", "You are the second of two software engineers")]


def gold_lines(p):
    out, f, ln = collections.defaultdict(set), None, 0
    for l in p.splitlines():
        m = re.match(r"^--- a/(\S+)", l)
        if m:
            f = m.group(1) if m.group(1).endswith(".py") and not TEST.search(m.group(1)) else None
            continue
        if l.startswith(("--- ", "+++ ")):
            continue
        m = re.match(r"^@@ -(\d+)", l)
        if m:
            ln = int(m.group(1))
            continue
        if f is None:
            continue
        if l.startswith("-"):
            out[f].add(ln); ln += 1
        elif l.startswith("+"):
            out[f].update({ln - 1, ln})
        else:
            ln += 1
    return out


def stage_of(arm, sysm):
    for a, s, k in STAGE:
        if a == arm and k in sysm:
            return s
    return "main"


def tool_outputs(req):
    msgs = req["request"]["messages"]
    last = max((i for i, m in enumerate(msgs) if m.get("role") == "assistant"), default=-1)
    return [str(m.get("content")) for m in msgs[last + 1:] if m.get("role") == "tool"]


A = collections.defaultdict(list)
for d in DIRS:
    per = {}
    for l in open(f"{d}/results/gen_per_task.jsonl"):
        g = json.loads(l)
        per[f"{g['instance_id']}#a{g['attempt']}"] = g
    J = collections.defaultdict(list)
    for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
        r = json.loads(l)
        if r.get("job") in per:
            J[r["job"]].append(r)
    print(f"\n## {d}")
    for job, g in sorted(per.items(), key=lambda x: (x[1]["instance_id"], x[1]["arm"])):
        R = sorted(J[job], key=lambda r: float(r["t"]))
        t0 = float(R[0]["t"])
        arm, iid = g["arm"], g["instance_id"]
        gl = gold_lines(GOLD[iid])
        stg = [stage_of(arm, r["request"]["messages"][0]["content"]) for r in R]
        names = [m.group(1) if (m := re.search(r"'name': '(\w+)'", str(r["reply"]))) else "-" for r in R]
        ed = [i for i, n in enumerate(names) if n in ("edit_file", "write_file")]
        fe = ed[0] if ed else None
        secs = collections.Counter()
        cnt = collections.Counter()
        for s, r in zip(stg, R):
            secs[s] += float(r["seconds"])
            cnt[s] += 1
        x = dict(arm=arm, iid=iid, solved=g["resolved"] in (True, "True"), end=g["end"], agent=g["agent_s"], nop=not g["patch_chars"],
                 fe=fe + 1 if fe is not None else None, fe_t=float(R[fe]["t"]) - t0 if fe is not None else None, stages=dict(cnt))
        info = ""
        if arm in ("sb7", "sb7s", "sb7f", "sb8"):
            hi = [i for i, s in enumerate(stg) if s == "history"]
            nxt = "editor" if arm == "sb8" else "fixer"
            ni = next((i for i, s in enumerate(stg) if s == nxt), None)
            pinned = ""
            if ni is not None:
                sysm = R[ni]["request"]["messages"][0]["content"]
                key = "Each commit's title says why, its diff says how:"
                pinned = re.split(r"\n\n(?:Use it when|# SOLVE IT WITH)", sysm.split(key, 1)[1], 1)[0] if key in sysm else ""
            out = ""
            for i in hi:
                for o in tool_outputs(R[i + 1]) if i + 1 < len(R) else []:
                    out = o
            files = set()
            x.update(hist=bool(hi), hist_s=secs["history"], pinned_chars=len(pinned.strip()), pinned_commits=pinned.count("commit "),
                     copied=bool(pinned.strip()) and pinned.strip()[:200] in out.replace("\\n", "\n"))
            if arm in ("sb7", "sb7s", "sb7f"):
                x["hist_requests"] = len(hi)
                hdr = [(m.group(1), int(m.group(2))) for m in re.finditer(r"^== (\S+) lines? (\d+)", pinned, re.M)]
                x.update(pin_file=any(f in gl for f, _ in hdr), pin_near=any(f in gl and any(abs(s + 2 - y) <= 5 for y in gl[f]) for f, s in hdr))
                info = f"| hist {x['hist_requests']} requests {x['hist_s']:3.0f}s pinned {x['pinned_chars']:4} chars {x['pinned_commits']} commits copied {x['copied']} real-fix file {x['pin_file']} near {x['pin_near']}"
            else:
                ex = [i for i, s in enumerate(stg) if s == "explore"]
                tgt = ""
                if ni is not None or hi:
                    sysm = R[(hi or [ni])[0]]["request"]["messages"][0]["content"]
                    tgt = sysm.split("chose the lines to change:", 1)[1].split("The command prints", 1)[0] if "chose the lines to change:" in sysm else ""
                m = re.search(r"FILE:\s*(\S+)\s*\n\s*LINES:\s*(\d+)\s*-\s*(\d+)", tgt)
                on = bool(m and m.group(1) in gl and set(range(int(m.group(2)) - 3, int(m.group(3)) + 4)) & gl[m.group(1)])
                warn = any("tool call(s) remaining" in o for i in ex for o in (tool_outputs(R[i]) if i < len(R) else []))
                ed_in = [i for i in ed if stg[i] == "editor"]
                x.update(handed=bool(m), target_file=bool(m and m.group(1) in gl), target_on=on, warned=warn, editor=ni is not None,
                         editor_edit=bool(ed_in), editor_calls_to_edit=(ed_in[0] - ni + 1) if ed_in and ni is not None else None,
                         explore_calls=cnt["explore"])
                info = (f"| explore {cnt['explore']:2} calls {secs['explore']:3.0f}s handed {x['handed']} (warning seen {warn}) file {x['target_file']} on-lines {on}"
                        f" | hist {x['hist_s']:3.0f}s pinned {x['pinned_chars']:4} chars {x['pinned_commits']} commits copied {x['copied']}"
                        f" | editor {cnt['editor']:2} calls, edit {x['editor_edit']} at editor call {x['editor_calls_to_edit']}")
        A[arm].append(x)
        print(f"  {arm:4} {iid[:22]:22} {'SOLVED' if x['solved'] else 'fail  '} end={g['end']:9} agent {g['agent_s']:4.0f}s replies {len(R):2} first edit call {x['fe'] or '-'} patch {g['patch_chars']:5} {info}")

print("\n#### per arm")
for arm, xs in A.items():
    fes = [x["fe"] for x in xs if x["fe"]]
    line = (f"  {arm}: solved {sum(x['solved'] for x in xs)}/{len(xs)} | time ends {sum(x['end'] == 'time' for x in xs)} | no patch {sum(x['nop'] for x in xs)}"
            f" | mean agent {st.mean(x['agent'] for x in xs):.0f}s | first edit call median {st.median(fes) if fes else '-'} ({len(fes)} runs)")
    if arm in ("sb7", "sb7s", "sb7f", "sb8"):
        line += f" | history ran {sum(x['hist'] for x in xs)} | pinned non-empty {sum(x['pinned_chars'] > 0 for x in xs)} | copied exactly {sum(x['copied'] for x in xs)} | history stage mean {st.mean(x['hist_s'] for x in xs if x['hist']) if any(x['hist'] for x in xs) else 0:.0f}s"
    if arm in ("sb7", "sb7s", "sb7f"):
        line += f" | history stage ended in time (<= 2 requests; sb7f: <= 3) {sum(x['hist_requests'] <= (3 if arm == 'sb7f' else 2) for x in xs)}"
    if arm == "sb8":
        line += (f" | handed over {sum(x['handed'] for x in xs)} (real-fix file {sum(x['target_file'] for x in xs)}, on lines {sum(x['target_on'] for x in xs)})"
                 f" | editor reached {sum(x['editor'] for x in xs)}, edited {sum(x['editor_edit'] for x in xs)} | explore calls median {st.median(x['explore_calls'] for x in xs)}")
    print(line)
