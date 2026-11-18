"""r112: sb1 vs sb6 (read -> git log -L on the lines to change -> edit) small first trial, 4 tasks x 2 passes.
Run: python3 -I scripts/mine_bank/r112_sb6.py   (repo root; logs only). Context at the first edit:
python3 -I scripts/mine_bank/context_at_edit.py 'data/results/2026-11-18_skill_sb6h4_p*' sb1,sb6
Per run: outcome, end, agent time, replies, model time and the part in replies >= 30 s, tokens, first edit (call, s),
edits, git log -L calls (index). Then where time-ended runs spend model time (replies >= 60 s), what those long
replies think (chars, 'Wait / Actually' count) and what they do next."""
import collections, glob, json, re, statistics as st

DIRS = sorted(glob.glob("data/results/2026-11-18_skill_sb6h4_p*"))
WAIT = re.compile(r"\b(Wait|But wait|Actually|Hmm|Let me re)")
tot, lng, nrep, nl, after, think, waits = (collections.Counter() for _ in range(7))
arm_stats = collections.defaultdict(list)
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
        names = [m.group(1) if (m := re.search(r"'name': '(\w+)'", str(r["reply"]))) else "-" for r in R]
        toks = [int(m.group(1)) if (m := re.search(r"'completion_tokens': (\d+)", str(r["reply"]))) else 0 for r in R]
        secs = [float(r["seconds"]) for r in R]
        hist = [i + 1 for i, r in enumerate(R) if "git log -L" in str(r["reply"])]
        ed = [i for i, n in enumerate(names) if n in ("edit_file", "write_file")]
        fe = ed[0] if ed else None
        solved = g["resolved"] in (True, "True")
        arm_stats[g["arm"]].append(dict(solved=solved, end=g["end"], agent=g["agent_s"], fe=fe + 1 if fe is not None else None,
                                        nop=not g["patch_chars"], hist_before=bool(fe is not None and any(fe - 1 <= h - 1 < fe for h in hist))))
        print(f"  {g['arm']:4} {g['instance_id'][:24]:24} {'SOLVED' if solved else 'fail  '} end={g['end']:5} agent {g['agent_s']:4.0f}s replies {len(R):3}"
              f" | model {sum(secs):4.0f}s, replies>=30s {sum(s >= 30 for s in secs)} = {sum(s for s in secs if s >= 30):4.0f}s | tokens mean {st.mean(toks):4.0f} max {max(toks):5}"
              f" | first edit call {fe + 1 if fe is not None else '-'} at {float(R[fe]['t']) - t0 if fe is not None else 0:4.0f}s | edits {len(ed)} | git log -L at {hist} | patch {g['patch_chars']}")
        k = "time-ended" if g["end"] == "time" else "other"
        for r in R:
            s = float(r["seconds"])
            tot[k] += s
            nrep[k] += 1
            if s >= 60:
                rep = str(r["reply"])
                m = re.search(r"'reasoning_content': '(.*?)', 'reasoning'", rep, re.S)
                th = (m.group(1) if m else "").replace("\\n", " ")
                lng[k] += s
                nl[k] += 1
                think[k] += len(th)
                waits[k] += len(WAIT.findall(th))
                c = re.search(r"'name': '(\w+)'", rep)
                after[c.group(1) if c else "none"] += 1
print("\n#### per arm")
for arm, xs in arm_stats.items():
    fes = [x["fe"] for x in xs if x["fe"]]
    print(f"  {arm}: solved {sum(x['solved'] for x in xs)}/{len(xs)} | time ends {sum(x['end'] == 'time' for x in xs)} | no patch {sum(x['nop'] for x in xs)}"
          f" | mean agent {st.mean(x['agent'] for x in xs):.0f}s | first edit call median {st.median(fes) if fes else '-'} (runs with an edit {len(fes)})"
          f" | git log -L in the 2 calls before the first edit {sum(x['hist_before'] for x in xs)}")
print("\n#### where the time goes")
for k in tot:
    print(f"  {k}: replies {nrep[k]}, model {tot[k]:.0f}s; replies >= 60 s: {nl[k]} ({100 * nl[k] / nrep[k]:.0f}% of replies) = {lng[k]:.0f}s ({100 * lng[k] / tot[k]:.0f}% of model time)"
          f"{f', thinking {think[k] / nl[k]:.0f} chars and Wait/Actually x{waits[k] / nl[k]:.1f} per long reply' if nl[k] else ''}")
print("  what a >= 60 s reply did next:", dict(after))
