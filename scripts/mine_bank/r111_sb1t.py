"""r111: sb1 (thinking 4096) vs sb1t (thinking 2048) on 12 tasks where runs often end without an edit, 2 passes.
Checks the bars set before the run (docs/PLAN.md RUN BUILT r111). Run: python3 -I scripts/mine_bank/r111_sb1t.py
(repo root; logs only). Per arm: solves, ends, no-patch runs, agent time, calls, seconds per reply, reply tokens
(completion = thinking + text + call), replies over 2,100 / 4,000 tokens, finish 'length', first edit call (index, s),
per-task solves; and the same 12 tasks' sb1 runs in earlier folders as a larger baseline for sb1's rates."""
import collections, glob, json, re, statistics as st

DIRS = sorted(glob.glob("data/results/2026-11-17_skill_sb1t12_p*"))
ARMS = ("sb1", "sb1t")


def load(dirs, arms):
    per, reps = {}, collections.defaultdict(list)
    for d in dirs:
        for l in open(f"{d}/results/gen_per_task.jsonl"):
            g = json.loads(l)
            if g.get("arm") in arms:
                per[f"{d[-2:]}:{g['instance_id']}#a{g['attempt']}"] = g
        for l in open(f"{d}/requests/requests.jsonl", errors="replace"):
            try:
                r = json.loads(l)
            except Exception:
                continue
            k = f"{d[-2:]}:{r.get('job')}"
            if k in per:
                rep = str(r.get("reply"))
                m = re.search(r"'completion_tokens': (\d+)", rep)
                fr = re.search(r"'finish_reason': '(\w+)'", rep)
                name = re.search(r"'name': '(\w+)'", rep)
                reps[k].append(dict(t=float(r["t"]), s=float(r.get("seconds") or 0), tok=int(m.group(1)) if m else None,
                                    fin=fr.group(1) if fr else None, call=name.group(1) if name else None))
    return per, reps


def report(per, reps, title):
    print(f"\n#### {title}")
    for arm in ARMS:
        P = {k: g for k, g in per.items() if g["arm"] == arm}
        if not P:
            continue
        R = [x for k in P for x in reps.get(k, [])]
        toks = [x["tok"] for x in R if x["tok"] is not None]
        first = []
        for k in P:
            xs = sorted(reps.get(k, []), key=lambda x: x["t"])
            for i, x in enumerate(xs):
                if x["call"] in ("edit_file", "write_file"):
                    first.append((i + 1, x["t"] - xs[0]["t"]))
                    break
        nop = sum(1 for g in P.values() if not g.get("patch_chars"))
        print(f"  {arm:5} runs {len(P):3} | solved {sum(g['resolved'] in (True, 'True') for g in P.values()):3} | no patch {nop:3}"
              f" | ends {dict(collections.Counter(g['end'] for g in P.values()))}"
              f" | agent s mean {st.mean(g['agent_s'] for g in P.values()):5.0f} | llm calls mean {st.mean(g['llm_calls'] for g in P.values()):4.1f}"
              f" | tool calls mean {st.mean(g['tool_calls'] for g in P.values()):4.1f}")
        if R:
            print(f"        replies {len(R):5} | s/reply mean {st.mean(x['s'] for x in R):5.2f} median {st.median(x['s'] for x in R):5.2f}"
                  f" | tokens mean {st.mean(toks):6.0f} median {st.median(toks):5.0f} p90 {sorted(toks)[int(.9 * len(toks))]:5}"
                  f" | >2100 {sum(t > 2100 for t in toks):3} >4000 {sum(t > 4000 for t in toks):3} | finish length {sum(x['fin'] == 'length' for x in R)}"
                  f" | share of model time in replies >1000 tok {100 * sum(x['s'] for x in R if (x['tok'] or 0) > 1000) / sum(x['s'] for x in R):3.0f}%")
            print(f"        first edit call: in {len(first)}/{len(P)} runs, median call {st.median(f[0] for f in first) if first else '-'}, "
                  f"median {st.median(f[1] for f in first) if first else 0:4.0f} s")


per, reps = load(DIRS, ARMS)
report(per, reps, "r111 (same run, both passes)")
for p in ("p1", "p2"):
    report({k: g for k, g in per.items() if k.startswith(p)}, reps, f"pass {p}")

tasks = sorted({g["instance_id"] for g in per.values()})
print("\n#### per task: solved / runs, no patch, ends, agent s mean")
for t in tasks:
    row = []
    for arm in ARMS:
        G = [g for g in per.values() if g["instance_id"] == t and g["arm"] == arm]
        row.append(f"{arm:5} {sum(g['resolved'] in (True, 'True') for g in G)}/{len(G)} nop {sum(not g.get('patch_chars') for g in G)}"
                   f" {','.join(g['end'] for g in G):12} {st.mean(g['agent_s'] for g in G):4.0f}s")
    print(f"  {t[:34]:34} | " + " | ".join(row))

# larger sb1 baseline: same 12 tasks, every earlier folder with sb1 runs
old = sorted(d for d in glob.glob("data/results/2026-11-1*") if "sb1t12" not in d and glob.glob(f"{d}/results/gen_per_task.jsonl"))
B = collections.defaultdict(list)
for d in old:
    for l in open(f"{d}/results/gen_per_task.jsonl"):
        g = json.loads(l)
        if g.get("arm") == "sb1" and g["instance_id"] in tasks:
            B[g["instance_id"]].append(g)
n = sum(len(v) for v in B.values())
if n:
    print(f"\n#### earlier sb1 runs on these tasks: {n} runs | solved {sum(g['resolved'] in (True, 'True') for v in B.values() for g in v)}"
          f" | no patch {sum(not g.get('patch_chars') for v in B.values() for g in v)} | ends time {sum(g['end'] == 'time' for v in B.values() for g in v)}"
          f" | agent s mean {st.mean(g['agent_s'] for v in B.values() for g in v):.0f}")
